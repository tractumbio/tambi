"""Raw response archive.

Every AusTender response is persisted verbatim *before* any parsing. This archive
is the audit trail: if transform logic is later found wrong, reprocessing must not
require re-hitting the government API.

The store sits behind a minimal `RawStore` interface so the local-filesystem
implementation used now can be swapped for an Azure Blob Storage implementation
later without touching ingestion logic. No hosts, paths or credentials are
hardcoded — the local root comes from ``settings.raw_store_path``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from app.core.config import get_settings


@runtime_checkable
class RawStore(Protocol):
    """Minimal key/bytes archive. Implementations: local FS now, Blob later."""

    def put(self, key: str, data: bytes) -> str:
        """Persist ``data`` under ``key``. Return a locator (path or URI)."""
        ...

    def exists(self, key: str) -> bool:
        """True if ``key`` has already been archived."""
        ...


class LocalRawStore:
    """Writes raw payloads to a local directory tree rooted at ``root``.

    Keys may contain forward slashes to form subdirectories (e.g.
    ``contractPublished/2026-09-01_2026-09-02_0.json``). Parent directories are
    created on demand. Writes are atomic (temp file + rename) so a crashed run
    never leaves a half-written payload that later looks like a valid archive.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        if root is None:
            root = get_settings().raw_store_path
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, key: str) -> Path:
        # Guard against path traversal escaping the archive root.
        target = (self._root / key).resolve()
        if self._root not in target.parents and target != self._root:
            raise ValueError(f"key {key!r} escapes raw store root")
        return target

    def put(self, key: str, data: bytes) -> str:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(target)
        return str(target)

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()
