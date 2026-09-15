# Architecture Decision Records (ADRs)

> **Purpose:** Explain what an ADR is, when to write one, and index the existing records.
> **Audience:** All contributors, especially anyone proposing a structural change.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../architecture/SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md), [template.md](template.md)

---

## What is an ADR?

A short document capturing a single significant architectural decision: the context, the options considered, the decision, and the consequences. ADRs are immutable once accepted — if a decision changes later, write a new ADR that supersedes the old one rather than editing history.

## When to write one

Write an ADR when a change:
- Introduces a new dependency, framework, or external service.
- Changes a cross-cutting pattern (e.g. how agents are coordinated, how data is stored).
- Is expensive to reverse.
- Contributors are likely to ask "why did we do it this way?" in six months.

Small, local, easily-reversible decisions do not need an ADR — use judgement, and ask in a PR if unsure.

## Process

1. Copy [template.md](template.md) to `NNNN-short-title.md` (next sequential number).
2. Fill it in; status starts as `Proposed`.
3. Open a PR — the ADR itself is reviewed like code.
4. On merge, set status to `Accepted` (or `Rejected` if the team decides against it — rejected ADRs are still kept, as the reasoning has future value).
5. If later superseded, set the old ADR's status to `Superseded by ADR-NNNN` and link forward.

## Index

| # | Title | Status |
|---|---|---|
| [0001](0001-use-fastapi-for-backend.md) | Use FastAPI for the backend | Accepted |
| [0002](0002-use-json-storage-for-prototype.md) | Use JSON storage for the prototype phase | Accepted |
| [0003](0003-modular-ai-agent-architecture.md) | Modular AI agent architecture over a single general-purpose agent | Accepted |
