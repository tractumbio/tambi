"""Database engine and session factory.

Sync SQLAlchemy 2.0 over psycopg 3. The ingestion CLI and the (Phase 5) API both
use this. The connection string comes entirely from ``settings.database_url`` — no
host, port or credential is hardcoded here.

A second, least-privilege engine is exposed for the Phase 6 LLM query layer via
``settings.database_url_readonly``; it is created lazily so the app runs without a
read-only role configured until Phase 6 needs one.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _normalise_driver(url: str) -> str:
    """Force the psycopg (v3) driver so a bare ``postgresql://`` URL still works."""
    parsed = make_url(url)
    if parsed.drivername == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


def _require_url() -> str:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Configure it in .env before using the database."
        )
    return _normalise_driver(settings.database_url)


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(_require_url(), pool_pre_ping=True, future=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yield a session and always close it."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


# --- Read-only engine for the LLM query layer (Pillar II / Phase 6) ---

_ro_engine: Engine | None = None
_ROSessionLocal: sessionmaker[Session] | None = None


def get_readonly_engine() -> Engine:
    """Least-privilege engine bound to the ``dcih_readonly`` role.

    Falls back to the primary URL only if no read-only URL is configured — but the
    SQL guardrails in the query layer are the real safety net, this is defence in depth.
    """
    global _ro_engine
    if _ro_engine is None:
        settings = get_settings()
        url = settings.database_url_readonly or settings.database_url
        if not url:
            raise RuntimeError("No DATABASE_URL_READONLY or DATABASE_URL configured.")
        _ro_engine = create_engine(_normalise_driver(url), pool_pre_ping=True, future=True)
    return _ro_engine


def get_readonly_session_factory() -> sessionmaker[Session]:
    global _ROSessionLocal
    if _ROSessionLocal is None:
        _ROSessionLocal = sessionmaker(
            bind=get_readonly_engine(), autoflush=False, expire_on_commit=False
        )
    return _ROSessionLocal
