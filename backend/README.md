# Backend

> **Purpose:** Explain how to run and navigate the FastAPI backend application.
> **Audience:** Backend engineers.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../architecture/BACKEND_ARCHITECTURE.md](../architecture/BACKEND_ARCHITECTURE.md), [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md), [../docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md)

---

## Status

Starter scaffold only — no business functionality implemented yet. `GET /api/v1/health` is the only working endpoint, to prove the application boots and to serve as the Docker Compose healthcheck target. See [../README.md#project-status](../README.md#project-status).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive API docs.

## Run tests

```bash
pytest
```

## Layout

See [../architecture/BACKEND_ARCHITECTURE.md](../architecture/BACKEND_ARCHITECTURE.md) for full rationale.

```
app/
├── api/routes/     HTTP route handlers (thin — parse, call service, return)
├── core/            Config and logging setup
├── services/         Business logic (empty — not yet implemented)
├── agents/            AI agent implementations + provider abstraction (skeleton only)
├── models/            Internal domain models (empty — not yet implemented)
├── schemas/           Pydantic request/response schemas
├── db/                 Data access layer (empty — not yet implemented)
└── main.py             App entrypoint, router registration
```

## Adding a new route

1. Add a Pydantic schema in `app/schemas/`.
2. Add a router file in `app/api/routes/` and register it in `main.py`.
3. Add business logic in `app/services/`, not in the route handler.
4. Add a test under `../tests/backend/`.

See [../docs/CODING_STANDARDS.md#fastapi](../docs/CODING_STANDARDS.md#fastapi).
