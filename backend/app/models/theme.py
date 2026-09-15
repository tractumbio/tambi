"""Defence themes and the contract↔theme classification join."""

from sqlalchemy import ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Theme(Base):
    """A Defence theme (e.g. nuclear submarines, defensive cyber)."""

    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ContractTheme(Base):
    """Many-to-many: a contract can match multiple themes, each with provenance."""

    __tablename__ = "contract_themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ocid: Mapped[str] = mapped_column(
        ForeignKey("contracts.ocid", ondelete="CASCADE"), nullable=False
    )
    theme_id: Mapped[int] = mapped_column(ForeignKey("themes.id"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    # keyword | unspsc | llm | manual
    method: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_contract_themes_ocid", "ocid"),
        Index("uq_contract_themes_ocid_theme", "ocid", "theme_id", unique=True),
    )
