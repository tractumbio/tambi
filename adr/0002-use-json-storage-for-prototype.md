# ADR-0002: Use JSON storage for the prototype phase

> **Purpose:** Record the decision to use flat JSON files for storage during the prototype phase, with PostgreSQL planned for production.
> **Audience:** All contributors, especially anyone touching the data layer.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../architecture/DATABASE_DESIGN.md](../architecture/DATABASE_DESIGN.md), [../data/README.md](../data/README.md)

---

## Status

Accepted

## Context

Entity shapes (`Opportunity`, `Contract`, `Agency`, etc.) are still being defined and are likely to change frequently while the AI agents and UI are built out. The team needs to iterate quickly, inspect data by hand, and avoid the overhead of running and migrating a database during early, fast-changing development. Production use will eventually require proper querying, concurrency, and integrity — needs a relational database does solve well.

## Decision

Use **JSON files** as the storage mechanism during the prototype phase, accessed through a repository interface (see [../architecture/DATABASE_DESIGN.md](../architecture/DATABASE_DESIGN.md)) so the eventual move to **PostgreSQL** in production requires implementing a new repository, not rewriting service-layer logic.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| JSON files (chosen, prototype only) | Zero setup, human-readable/diffable, fast to change shape, easy to hand-craft sample/test data | No concurrency safety, no real querying, doesn't scale |
| SQLite | Real SQL, zero setup, file-based | Still requires schema migrations while shapes are unstable; less human-readable for quick inspection than plain JSON |
| PostgreSQL from day one | Production-grade from the start, no migration needed later | Migration/ops overhead too early, slows down entity shape iteration, requires a running DB for every contributor from day one |

## Consequences

- All data access goes through a repository interface from the start (`OpportunityRepository`, etc.) — this is the key discipline that makes the later swap to PostgreSQL low-risk. Any code that bypasses the repository and reads JSON files directly violates this ADR.
- Sample JSON shapes in [data/](../data/) double as both documentation and prototype fixtures.
- No concurrent-write safety exists in the prototype phase — acceptable since it's single-developer/local use during this phase, but must be resolved before any shared/production deployment.
- A follow-up ADR is required before implementing the PostgreSQL repository (schema design, migration tool choice — Alembic is anticipated, see [../architecture/DATABASE_DESIGN.md](../architecture/DATABASE_DESIGN.md)).

## Related decisions

Builds on [ADR-0001](0001-use-fastapi-for-backend.md). Migration to PostgreSQL is tracked as future work in [../architecture/FUTURE_CLOUD_ARCHITECTURE.md](../architecture/FUTURE_CLOUD_ARCHITECTURE.md) and will warrant its own ADR when scheduled.
