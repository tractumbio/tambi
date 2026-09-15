from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Resolve .env at the repo root from this file's location, so config loads the same
# way regardless of the current working directory (backend/ CLI, repo-root pytest,
# or a container). Env vars set in the real environment still take precedence.
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore"
    )

    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    api_v1_prefix: str = "/api/v1"
    # Accept a comma-separated string (e.g. CORS_ORIGINS=http://a,http://b) rather than
    # JSON. NoDecode disables pydantic-settings' JSON parsing so the validator below runs.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    database_mode: Literal["json", "postgres"] = "json"
    database_url: str | None = None
    # Separate least-privilege role for the LLM query layer (Phase 6 guardrail).
    database_url_readonly: str | None = None

    # --- AusTender ingestion (Phase 1+) ---
    austender_api_base_url: str = "https://api.tenders.gov.au/ocds/"
    raw_store_path: str = "./data/raw"
    # Politeness controls for the government API.
    austender_politeness_delay_ms: int = 250
    austender_max_retries: int = 5

    # --- LLM query layer (Phase 6) ---
    anthropic_api_key: str | None = None
    llm_max_rows: int = 1000
    llm_statement_timeout_ms: int = 10000
    theme_llm_value_threshold: float | None = None

    # --- External intelligence / news (Phase 8) ---
    news_fetch_user_agent: str | None = None
    news_min_request_interval_ms: int = 2000
    news_extract_max_words: int = 40
    news_relevance_floor: float = 0.35
    news_linkage_confidence_floor: float = 0.75
    report_timezone: str = "Australia/Sydney"

    # --- Document corpus / embeddings (Phase 9) ---
    embedding_model: str | None = None
    embedding_dimension: int = 1024
    doc_chunk_target_tokens: int = 600
    doc_retrieval_max_chunks: int = 12

    # Capability-match embeddings. Backend: "openai" (needs OPENAI_API_KEY) |
    # "local" (sentence-transformers, no key) | "voyage" (needs key) | "none" (TF-IDF).
    embedding_backend: Literal["openai", "local", "voyage", "none"] = "openai"
    openai_embedding_model: str = "text-embedding-3-small"
    local_embedding_model: str = "BAAI/bge-small-en-v1.5"
    voyage_api_key: str | None = None
    voyage_model: str = "voyage-3"

    ai_provider: Literal["ollama", "openai", "azure_openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = "2024-06-01"


@lru_cache
def get_settings() -> Settings:
    return Settings()
