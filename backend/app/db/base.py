"""Declarative base and metadata for all ORM models.

A single ``Base.metadata`` is what Alembic autogenerate compares against the live
database, so every model module must be imported before autogenerate runs. That
import wiring lives in ``app.models`` (see ``app/models/__init__.py``).
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for the whole schema."""
