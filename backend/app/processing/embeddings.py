"""Embedding client with in-process caching and graceful degradation.

Provides text embeddings for the capability-match scorer. Two backends:

  * "local"  — a sentence-transformers model (default BAAI/bge-small-en-v1.5) run in the
    venv. No API key, no per-call cost, works offline. First call loads the model (~lazy).
  * "voyage" — Voyage AI's hosted embeddings (needs VOYAGE_API_KEY).

Selected via ``settings.embedding_backend``. Embeddings are cached by exact text so the
repetitive contract descriptions ("Spare parts", "Professional Services") are embedded
once. If the active backend can't initialise, the module reports itself unavailable and
the caller falls back to TF-IDF matching.
"""

from __future__ import annotations

import math
import threading

from app.core.config import get_settings

_lock = threading.Lock()
_voyage_client = None
_openai_client = None
_azure_openai_client = None
_local_model = None
_cache: dict[str, list[float]] = {}
_MAX_BATCH = 128

# BGE retrieval models want this instruction prepended to *queries* only.
_BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def _backend() -> str:
    return get_settings().embedding_backend


def is_available() -> bool:
    backend = _backend()
    if backend == "openai":
        return bool(get_settings().openai_api_key)
    if backend == "azure_openai":
        return bool(get_settings().azure_openai_embeddings_endpoint)
    if backend == "voyage":
        return bool(get_settings().voyage_api_key)
    if backend == "local":
        try:
            _get_local_model()
            return True
        except Exception:
            return False
    return False


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        import openai

        _openai_client = openai.OpenAI(api_key=get_settings().openai_api_key)
    return _openai_client


def _get_azure_openai_client():
    global _azure_openai_client
    if _azure_openai_client is None:
        import openai
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        s = get_settings()
        if s.azure_openai_embeddings_key:
            _azure_openai_client = openai.AzureOpenAI(
                azure_endpoint=s.azure_openai_embeddings_endpoint,
                api_key=s.azure_openai_embeddings_key,
                api_version="2024-06-01",
            )
        else:
            # Managed identity — no key stored anywhere.
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )
            _azure_openai_client = openai.AzureOpenAI(
                azure_endpoint=s.azure_openai_embeddings_endpoint,
                azure_ad_token_provider=token_provider,
                api_version="2024-06-01",
            )
    return _azure_openai_client


def _get_voyage_client():
    global _voyage_client
    if _voyage_client is None:
        import voyageai

        _voyage_client = voyageai.Client(api_key=get_settings().voyage_api_key)
    return _voyage_client


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer

        _local_model = SentenceTransformer(get_settings().local_embedding_model)
    return _local_model


def _model_tag() -> str:
    s = get_settings()
    backend = _backend()
    if backend == "voyage":
        return s.voyage_model
    if backend == "openai":
        return s.openai_embedding_model
    if backend == "azure_openai":
        return f"azure:{s.azure_openai_embeddings_deployment}"
    return s.local_embedding_model


def embed_texts(texts: list[str], *, input_type: str) -> list[list[float]]:
    """Embed a list of texts, using and populating the exact-text cache.

    ``input_type`` is "document" (firm corpus) or "query" (the ATM being scored). Voyage
    uses it to asymmetrically tune embeddings; the local BGE path prepends its query
    instruction for "query" inputs.
    """
    tag = _model_tag()

    def _key(t: str) -> str:
        return f"{tag}|{input_type}|{t}"

    missing = [t for t in texts if _key(t) not in _cache]
    if missing:
        with _lock:
            still = [t for t in missing if _key(t) not in _cache]
            if still:
                vecs = _embed_backend(still, input_type)
                for txt, vec in zip(still, vecs):
                    _cache[_key(txt)] = vec

    return [_cache[_key(t)] for t in texts]


def _embed_backend(texts: list[str], input_type: str) -> list[list[float]]:
    backend = _backend()
    if backend == "voyage":
        client = _get_voyage_client()
        out: list[list[float]] = []
        for i in range(0, len(texts), _MAX_BATCH):
            batch = texts[i : i + _MAX_BATCH]
            resp = client.embed(batch, model=get_settings().voyage_model, input_type=input_type)
            out.extend(resp.embeddings)
        return out

    if backend == "openai":
        client = _get_openai_client()
        model = get_settings().openai_embedding_model
        out2: list[list[float]] = []
        for i in range(0, len(texts), _MAX_BATCH):
            batch = texts[i : i + _MAX_BATCH]
            resp = client.embeddings.create(model=model, input=batch)
            out2.extend(d.embedding for d in resp.data)
        return out2

    if backend == "azure_openai":
        client = _get_azure_openai_client()
        deployment = get_settings().azure_openai_embeddings_deployment
        out3: list[list[float]] = []
        for i in range(0, len(texts), _MAX_BATCH):
            batch = texts[i : i + _MAX_BATCH]
            resp = client.embeddings.create(model=deployment, input=batch)
            out3.extend(d.embedding for d in resp.data)
        return out3

    # local sentence-transformers
    model = _get_local_model()
    payload = (
        [_BGE_QUERY_INSTRUCTION + t for t in texts] if input_type == "query" else texts
    )
    arr = model.encode(payload, normalize_embeddings=True, batch_size=_MAX_BATCH, show_progress_bar=False)
    return [v.tolist() for v in arr]


def embed_one(text: str, *, input_type: str) -> list[float]:
    return embed_texts([text], input_type=input_type)[0]


def calibrate_similarity(cos: float) -> float:
    """Map a raw cosine to a 0–1 capability signal using the active backend's typical band.

    Different models occupy different similarity ranges for 'related' short texts, so the
    stretch band is backend-specific (calibrated empirically). Below the low end → 0,
    above the high end → 1.
    """
    backend = _backend()
    if backend in ("openai", "azure_openai"):
        lo, hi = 0.25, 0.60   # text-embedding-3 cosines sit lower
    elif backend == "voyage":
        lo, hi = 0.35, 0.75
    else:  # BGE / local sentence-transformers sit higher
        lo, hi = 0.45, 0.80
    return max(0.0, min(1.0, (cos - lo) / (hi - lo)))


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def weighted_centroid(vectors: list[list[float]], weights: list[float]) -> list[float]:
    """Frequency-weighted, L2-normalised mean of a set of embedding vectors."""
    if not vectors:
        return []
    dim = len(vectors[0])
    acc = [0.0] * dim
    total = 0.0
    for vec, w in zip(vectors, weights):
        total += w
        for i in range(dim):
            acc[i] += vec[i] * w
    if total == 0:
        return []
    acc = [x / total for x in acc]
    norm = math.sqrt(sum(x * x for x in acc))
    if norm == 0:
        return acc
    return [x / norm for x in acc]
