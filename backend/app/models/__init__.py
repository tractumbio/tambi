"""ORM models.

Importing this package imports every model so that ``Base.metadata`` is fully
populated — Alembic autogenerate and ``create_all`` both rely on that.
"""

from app.db.base import Base
from app.models.contract import Contract, RawRelease
from app.models.ingest import IngestState
from app.models.knowledge import KnowledgeItem, NewsDomain
from app.models.opportunity import Atm
from app.models.organisation import CompetitorGroup, Organisation
from app.models.reference import ReferenceProject
from app.models.report import MonthlyReport
from app.models.theme import ContractTheme, Theme

__all__ = [
    "Atm",
    "Base",
    "CompetitorGroup",
    "Contract",
    "ContractTheme",
    "IngestState",
    "KnowledgeItem",
    "MonthlyReport",
    "NewsDomain",
    "Organisation",
    "RawRelease",
    "ReferenceProject",
    "Theme",
]
