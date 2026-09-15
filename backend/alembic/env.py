"""Alembic migration environment.

The database URL comes from ``app.core.config`` (which reads ``.env``), never from
``alembic.ini`` — this keeps credentials out of version control and makes the same
migrations run unchanged against a local or cloud database.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

# Import every model so target_metadata is fully populated for autogenerate.
import app.models  # noqa: F401
from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import _normalise_driver  # reuse the psycopg-driver coercion

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set; configure it in .env before running Alembic.")
    return _normalise_driver(settings.database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
