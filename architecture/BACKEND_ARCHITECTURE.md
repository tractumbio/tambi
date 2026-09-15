# Backend Architecture

> **Purpose:** Describe the structure, layering, and conventions of the FastAPI backend.
> **Audience:** Backend engineers.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md), [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md), [DATABASE_DESIGN.md](DATABASE_DESIGN.md), [../docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md), [../backend/README.md](../backend/README.md)

---

## Stack

- **Python 3.11+**, **FastAPI**, **Pydantic v2** for schemas/validation, **Uvicorn** as the ASGI server.
- **pytest** for testing, **ruff** for lint/format, **mypy** for type checking.

## Folder layout

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          One router per domain (opportunities.py, reports.py, agents.py, health.py)
│   ├── core/                 Config, settings, logging setup
│   ├── services/              Business logic, orchestration triggers
│   ├── agents/                 AI agent implementations + provider abstraction
│   ├── models/                 Internal domain models
│   ├── schemas/                Pydantic request/response schemas (API contract)
│   ├── db/                     Data access layer (JSON repository / PostgreSQL repository)
│   └── main.py                 FastAPI app instantiation, router registration
├── requirements.txt
└── Dockerfile
```

## Layering

```
api/routes/  ──calls──▶  services/  ──calls──▶  agents/  and/or  db/
     │                        │
  schemas/ (I/O contract)   models/ (internal representation)
```

- **`api/routes/`**: parses/validates HTTP requests via `schemas/`, calls a service, returns a `response_model`. No business logic here.
- **`services/`**: orchestrates the actual work — may call one or more agents, read/write via `db/`, apply business rules.
- **`agents/`**: see [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md).
- **`db/`**: repository classes exposing domain-shaped methods (`get_opportunity(id)`, `list_contracts(filters)`) that hide whether storage is JSON or PostgreSQL underneath — see [DATABASE_DESIGN.md](DATABASE_DESIGN.md).
- **`schemas/` vs `models/`**: `schemas` are the *external* contract (what the API accepts/returns); `models` are the *internal* representation used within services/db. Keeping them distinct lets the internal representation evolve without breaking the API, and vice versa.

## Configuration

`app/core/config.py` loads settings from environment variables (via Pydantic `BaseSettings`), sourced from `.env` in development (see [.env.example](../.env.example)) and real environment variables / secrets manager in production.

## API versioning

All routes are mounted under `API_V1_PREFIX` (`/api/v1` by default). Breaking changes to a route's contract require a new version path rather than an in-place breaking change — see [../docs/CODING_STANDARDS.md#fastapi](../docs/CODING_STANDARDS.md#fastapi).

## Error handling

- Domain errors raise typed exceptions in `services/`, translated to `HTTPException` at the route boundary (not scattered `HTTPException` raises deep in business logic).
- All error responses follow a consistent shape: `{"detail": "..."}` (FastAPI default) — extended with an `error_code` field where the frontend needs to branch on error type.

## Health & readiness

`GET /api/v1/health` (see `app/api/routes/health.py`) reports service status, including whether the configured AI provider and data store are reachable — used by Docker Compose healthchecks (see [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md)).

## Background/async work

Report generation (which fans out to multiple agents) runs as an async FastAPI request today; as agent runtimes grow, this is expected to move to a background task queue — flagged as a future architecture decision, not yet implemented (see [FUTURE_CLOUD_ARCHITECTURE.md](FUTURE_CLOUD_ARCHITECTURE.md)).
