"""Organisations and the competitor groups they roll up into."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CompetitorGroup(Base):
    """MD-meaningful competitor, rolling up messy supplier spellings."""

    __tablename__ = "competitor_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    # accenture | big4 | consulting | sys_integrator | defence_prime | sme | other
    category: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    organisations: Mapped[list[Organisation]] = relationship(back_populates="competitor_group")


class Organisation(Base):
    """Deduplicated agency or supplier, from OCDS ``parties``.

    Dedup strategy (Phase 3): ABN first where present, ``name_normalised`` second.
    """

    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    abn: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_normalised: Mapped[str] = mapped_column(Text, nullable=False)
    roles: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    competitor_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("competitor_groups.id"), nullable=True
    )

    competitor_group: Mapped[CompetitorGroup | None] = relationship(back_populates="organisations")

    __table_args__ = (
        Index("ix_organisations_name_normalised", "name_normalised"),
        Index("ix_organisations_abn", "abn"),
    )
