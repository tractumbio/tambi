# Database Design

> **Purpose:** Describe the data model, the JSON-prototype-to-PostgreSQL-production strategy, and core entity definitions.
> **Audience:** Backend engineers, anyone touching data models.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [DATA_PIPELINE.md](DATA_PIPELINE.md), [../data/README.md](../data/README.md), [../adr/0002-use-json-storage-for-prototype.md](../adr/0002-use-json-storage-for-prototype.md)

---

## Strategy: JSON prototype → PostgreSQL production

The prototype phase stores data as JSON files under `data/` (sample shapes) and, once implemented, a `backend/app/db/json_store/` runtime equivalent. This favours iteration speed and human-readable inspection while entity shapes are still changing. Production moves to PostgreSQL for concurrency, querying, and integrity guarantees.

**The migration path is designed in from day one**: all data access goes through a repository interface (`app/db/repositories/`), so services never read/write JSON or SQL directly.

```python
class OpportunityRepository(Protocol):
    async def get(self, opportunity_id: str) -> Opportunity | None: ...
    async def list(self, filters: OpportunityFilters) -> list[Opportunity]: ...
    async def upsert(self, opportunity: Opportunity) -> Opportunity: ...
```

`JSONOpportunityRepository` and (later) `PostgresOpportunityRepository` both implement this — swapped via `DATABASE_MODE` in `.env`.

## Core entities

| Entity | Description | Sample file |
|---|---|---|
| `Opportunity` | A tracked business opportunity | [../data/opportunity.json](../data/opportunity.json) |
| `Contract` | A procurement contract record | [../data/contract.json](../data/contract.json) |
| `Agency` | A government/defence agency | [../data/agency.json](../data/agency.json) |
| `Programme` | A defence programme within an agency | [../data/programme.json](../data/programme.json) |
| `Organisation` | A company (competitor, partner, client) | [../data/organisation.json](../data/organisation.json) |
| `NewsArticle` | A source news/press item | [../data/news-article.json](../data/news-article.json) |
| `WeeklyReport` | A generated, combined report | [../data/weekly-report.json](../data/weekly-report.json) |
| `UserPreferences` | Per-user display/notification settings | [../data/user-preferences.json](../data/user-preferences.json) |
| `Configuration` | Application/runtime configuration | [../data/configuration.json](../data/configuration.json) |

Field-level detail lives in the sample JSON files themselves (self-describing) and in each entity's Pydantic schema in `backend/app/schemas/` once implemented.

## Entity relationships

```
Agency 1───* Programme 1───* Contract *───1 Organisation
  │                              │
  └──────────────*  Opportunity ─┘
                       │
                       *
                 NewsArticle (source references)

WeeklyReport *───* Opportunity, Contract, Organisation  (report aggregates references, not copies)
```

- `Opportunity` may reference a `Programme`, an `Agency`, and one or more `Organisation`s (competitors involved).
- `Contract` belongs to a `Programme` (which belongs to an `Agency`) and is awarded to an `Organisation`.
- `NewsArticle` is a source document referenced by other entities for lineage (see [DATA_PIPELINE.md#data-lineage--traceability](DATA_PIPELINE.md#data-lineage--traceability)) — not itself a "business" entity.
- `WeeklyReport` aggregates *references* to other entities (by ID) rather than duplicating their data, so a report always reflects the latest known state when re-rendered.

## PostgreSQL target schema notes (production)

- Each entity above becomes a table; foreign keys enforce the relationships shown.
- `Opportunity.confidence_score` and similar agent-derived fields are stored alongside the entity, not in a separate audit table, for the prototype — revisit if audit/versioning requirements grow (candidate ADR).
- JSONB columns are acceptable for agent-derived, loosely-structured sub-fields (e.g. an agent's raw structured output before/alongside normalisation) rather than forcing everything into rigid columns immediately.
- Migrations managed via **Alembic** once PostgreSQL is introduced (not yet present in `backend/`).

## Indexing (production)

Anticipated indexes: `Opportunity(agency_id)`, `Contract(programme_id)`, `Contract(organisation_id)`, `NewsArticle(published_at)` — to be confirmed against real query patterns once the API's filtering needs are concrete; not prematurely defined here.

## Data retention

Sample/placeholder data in `data/` is fictional and retained indefinitely as documentation. Production data retention policy (especially for any data touching client-confidential information) is a decision for a future ADR informed by [../SECURITY.md](../SECURITY.md) and client contractual terms.
