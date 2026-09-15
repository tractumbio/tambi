"""Ingestion watermark table so restarts don't reprocess everything."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestState(Base):
    """One row per named job (e.g. ``backfill``, ``incremental``)."""

    __tablename__ = "ingest_state"

    job_name: Mapped[str] = mapped_column(Text, primary_key=True)
    last_release_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
