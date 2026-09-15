"""Opportunity-side tables (spec §6.1). ATMs are built first — the only publication
type with a verified, robots-allowed route (see ingest/README.md Phase 0.4.1)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Atm(Base):
    """An AusTender Approach to Market (open opportunity).

    Kept deliberately separate from ``contracts`` — an ATM is a live opportunity, not an
    awarded contract; conflating them would let speculative data contaminate value
    figures. Natural key is ``atm_id``; ``status`` tracks lifecycle (disappearance from
    the feed marks it ``closed``, never deletes it).
    """

    __tablename__ = "atms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    atm_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    atm_uuid: Mapped[str | None] = mapped_column(Text, nullable=True)  # /Atm/Show/{uuid}

    agency_org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organisations.id"), nullable=True
    )
    agency_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    atm_type: Mapped[str | None] = mapped_column(Text, nullable=True)  # RFT/RFQ/EOI/RFI/RFP/…

    unspsc_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    unspsc_title: Mapped[str | None] = mapped_column(Text, nullable=True)  # category text

    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    close_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_value: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    is_defence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")  # open|closed|…
    resulting_ocid: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)  # RSS guid/link
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_atms_atm_id", "atm_id"),
        Index("ix_atms_close_date", "close_date"),
        Index("ix_atms_unspsc_code", "unspsc_code"),
        Index("ix_atms_defence_close", "is_defence", "close_date"),
        Index("ix_atms_status", "status"),
    )
