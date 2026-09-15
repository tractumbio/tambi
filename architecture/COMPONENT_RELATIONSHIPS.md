# Component Relationships

> **Purpose:** Show how the major components depend on and communicate with each other.
> **Audience:** Engineers working across frontend/backend/AI boundaries.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md), [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md), [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md), [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md)

---

## Dependency diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                          Frontend (React)                            │
│  pages/  ──▶  components/                                             │
│    │                                                                   │
│    ▼                                                                   │
│  api/  (typed HTTP client)                                             │
└───────────────────────────────┬───────────────────────────────────┘
                                  │  REST (JSON over HTTP)
┌───────────────────────────────▼───────────────────────────────────┐
│                        Backend (FastAPI)                              │
│  api/routes/  ──▶  services/  ──▶  agents/  ──▶  providers/           │
│                        │                              │                │
│                        ▼                              ▼                │
│                      db/  (repository)          Ollama / OpenAI /     │
│                        │                          Azure OpenAI         │
└───────────────────────┼───────────────────────────────────────────┘
                          ▼
                 JSON files / PostgreSQL
```

## Communication rules

1. **Frontend never talks to the AI provider or database directly** — everything goes through the backend REST API. This keeps API keys and data access server-side only.
2. **`api/routes/` never talks to `agents/` or `db/` directly** — always via `services/`, so business logic has one home and routes stay thin.
3. **Domain agents never call each other** — coordination is centralised in the Orchestrator Agent (see [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md)), keeping the dependency graph shallow and each agent independently testable.
4. **`services/` never imports a specific `AIProvider` implementation** — only the `AIProvider` protocol, resolved via config. Same principle for `db/` repositories (interface, not concrete JSON/Postgres class).

## Chart library choice by component

| Component type | Library | Why |
|---|---|---|
| Dashboard KPI tiles, trend lines | Recharts | Lightweight, composes naturally as React components |
| Multi-dimensional report visualisations (e.g. opportunity value vs. probability vs. agency) | Plotly | Richer chart types, built-in export, better for dense analytical views |

See [FRONTEND_ARCHITECTURE.md#visualisation](FRONTEND_ARCHITECTURE.md#visualisation).

## Cross-cutting concerns

| Concern | Owned by |
|---|---|
| Input validation | `schemas/` (backend), TypeScript types (frontend) |
| Logging | `app/core/` logging config, consumed via `logging.getLogger(__name__)` everywhere |
| Configuration | `app/core/config.py` (backend), `import.meta.env` (frontend, Vite) |
| Error surfacing | `HTTPException` → consistent JSON shape → frontend `api/` layer maps to UI state |

## Example: a single user action traced across components

**User clicks "Refresh Opportunities"**

1. `frontend/src/pages/OpportunitiesPage.tsx` calls `frontend/src/api/opportunities.ts::refreshOpportunities()`.
2. That calls `POST /api/v1/opportunities/refresh`.
3. `backend/app/api/routes/opportunities.py` validates the request, calls `OpportunityService.refresh()`.
4. `OpportunityService` calls the `OpportunityAgent` (via the Orchestrator or directly, depending on scope) and, on success, writes results via `OpportunityRepository`.
5. Response flows back up; the frontend updates its local state and re-renders `components/OpportunityCard.tsx` instances via `pages/OpportunitiesPage.tsx`.

This trace is the pattern to follow when adding any new feature that spans the stack.
