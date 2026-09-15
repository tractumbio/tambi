"""Raw landing table and the current-state contracts table."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawRelease(Base):
    """Append-only landing table for parsed-but-unflattened OCDS releases.

    Keeps every release so all downstream tables are rebuildable with one SQL pass.
    ``ocid`` is *not* unique here — one process has many releases over time.
    """

    __tablename__ = "raw_releases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ocid: Mapped[str] = mapped_column(Text, nullable=False)
    release_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_raw_releases_ocid", "ocid"),
        Index("ix_raw_releases_release_date", "release_date"),
    )


class Contract(Base):
    """Current-state contract, one row per ``ocid`` — the dashboard's main table."""

    __tablename__ = "contracts"

    ocid: Mapped[str] = mapped_column(Text, primary_key=True)
    cn_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    buyer_org_id: Mapped[int | None] = mapped_column(ForeignKey("organisations.id"), nullable=True)
    supplier_org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organisations.id"), nullable=True
    )

    value_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    value_currency: Mapped[str | None] = mapped_column(Text, nullable=True)

    date_published: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_signed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    procurement_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    unspsc_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    unspsc_title: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Buyer organisational unit (Defence branch data), from the party contactPoint.
    buyer_division: Mapped[str | None] = mapped_column(Text, nullable=True)
    buyer_branch: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_defence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Accenture-addressable service-offering classification (ported from prior analytics).
    service_offering: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_addressable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    service_offering_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_per_year: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    amendment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_release_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_contracts_cn_id", "cn_id"),
        Index("ix_contracts_supplier_org_id", "supplier_org_id"),
        Index("ix_contracts_value_amount", "value_amount"),
        Index("ix_contracts_date_published", "date_published"),
        Index("ix_contracts_period_start", "period_start"),
        Index("ix_contracts_period_end", "period_end"),
        Index("ix_contracts_procurement_method", "procurement_method"),
        Index("ix_contracts_unspsc_code", "unspsc_code"),
        Index("ix_contracts_is_defence", "is_defence"),
        Index("ix_contracts_service_offering", "service_offering"),
        Index("ix_contracts_buyer_division", "buyer_division"),
        Index("ix_contracts_buyer_branch", "buyer_branch"),
        Index("ix_contracts_is_addressable", "is_addressable"),
        Index("ix_contracts_value_per_year", "value_per_year"),
        Index("ix_contracts_addressable_offering", "is_addressable", "service_offering"),
        # Composite indexes for the actual dashboard query patterns (spec Section 6).
        Index("ix_contracts_defence_published", "is_defence", "date_published"),
        Index("ix_contracts_defence_period_end", "is_defence", "period_end"),
        Index("ix_contracts_supplier_published", "supplier_org_id", "date_published"),
        Index("ix_contracts_defence_value", "is_defence", "value_amount"),
    )
