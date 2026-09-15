# Deployment Architecture

> **Purpose:** Describe how the system is deployed today — local, Docker Compose-based deployment.
> **Audience:** Engineers running or deploying the stack.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [FUTURE_CLOUD_ARCHITECTURE.md](FUTURE_CLOUD_ARCHITECTURE.md), [../docker/README.md](../docker/README.md), [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md)

---

## Current deployment target: local, via Docker Compose

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker host (laptop)                   │
│                                                                 │
│  ┌───────────────┐   ┌───────────────┐   ┌──────────────────┐│
│  │   frontend      │   │    backend      │   │   postgres        ││
│  │  (nginx, static │   │  (uvicorn,      │   │  (optional,        ││
│  │   build, :5173/ │◄──┤   :8000)        │◄──┤   :5432, only when ││
│  │   :80 in prod)  │   │                  │   │   DATABASE_MODE=  ││
│  └───────────────┘   └───────┬─────────┘   │   postgres)        ││
│                                │             └──────────────────┘│
│                                ▼                                 │
│                        ┌───────────────┐                          │
│                        │ ollama (host   │                          │
│                        │ process or     │                          │
│                        │ container)     │                          │
│                        └───────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

See [docker/docker-compose.yml](../docker/docker-compose.yml) for the authoritative service definitions.

## Services

| Service | Image/build | Port | Notes |
|---|---|---|---|
| `frontend` | `docker/frontend.Dockerfile` (multi-stage: Node build → Nginx serve) | 5173 (dev) / 80 (container) | Static SPA build |
| `backend` | `docker/backend.Dockerfile` | 8000 | Uvicorn, `--reload` in dev override |
| `postgres` | `postgres:16` | 5432 | Only started when `DATABASE_MODE=postgres`; optional in prototype phase |
| `ollama` | Runs on host or as its own container, not managed by this repo's Compose file by default | 11434 | See [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md) |

## Environments

| Environment | How it runs | Data store |
|---|---|---|
| Local dev (no Docker) | `uvicorn --reload` + `npm run dev` directly on host | JSON |
| Local dev (Docker Compose) | `docker compose up` | JSON (default) or Postgres |
| Staging/Production | Not yet defined — see [FUTURE_CLOUD_ARCHITECTURE.md](FUTURE_CLOUD_ARCHITECTURE.md) | PostgreSQL |

## Networking

Compose creates a default bridge network; services reach each other by service name (`http://backend:8000`, not `localhost`) — see [../docs/TROUBLESHOOTING.md#docker](../docs/TROUBLESHOOTING.md#docker).

## Configuration & secrets

Environment variables are injected via `.env` (see [.env.example](../.env.example)), loaded by Docker Compose automatically when present in the same directory as `docker-compose.yml`, or passed via `--env-file`. No secrets are baked into images.

## Health checks

Each container defines a healthcheck (backend: `GET /api/v1/health`; frontend: HTTP 200 on `/`; postgres: `pg_isready`) so `docker compose up` reports readiness accurately and dependent services (e.g. backend waiting on postgres) start in the right order.

## Build vs. runtime images

- **Frontend**: multi-stage build — Node stage builds static assets, Nginx stage serves them. No Node runtime in the final image.
- **Backend**: single-stage Python image with dependencies installed; `--reload` only enabled via a Compose *override* file for local dev, not in the base image.

## What's not yet defined

CI/CD deployment pipeline, staging/production hosting, container registry, and orchestration beyond Compose (e.g. Kubernetes, Azure Container Apps) are intentionally undefined at this stage — see [FUTURE_CLOUD_ARCHITECTURE.md](FUTURE_CLOUD_ARCHITECTURE.md) for the direction, to be formalised via ADR when the project is ready to deploy beyond a laptop.
