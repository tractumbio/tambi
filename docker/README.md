# Docker

> **Purpose:** Explain how to run the full stack locally via Docker Compose.
> **Audience:** All contributors.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../architecture/DEPLOYMENT_ARCHITECTURE.md](../architecture/DEPLOYMENT_ARCHITECTURE.md), [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md)

---

## Quick start

```bash
cp ../.env.example ../.env   # if you haven't already
docker compose -f docker-compose.yml up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000/docs
- PostgreSQL (only if `DATABASE_MODE=postgres` in `.env`): localhost:5432

Ollama is **not** included in `docker-compose.yml` by default — run it on the host per [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md) so it can use host GPU/Metal acceleration. See [../architecture/DEPLOYMENT_ARCHITECTURE.md](../architecture/DEPLOYMENT_ARCHITECTURE.md) for the full service topology and rationale.

## Local development overrides

For hot-reload during development (mounting source instead of relying on the built image), copy the override template:

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
docker compose up
```

Compose automatically merges `docker-compose.override.yml` when present — it's gitignored so each developer can customise it without affecting others.

## Common commands

```bash
docker compose up --build          # start, rebuilding images
docker compose up -d               # start in the background
docker compose logs -f backend     # tail backend logs
docker compose down                # stop and remove containers
docker compose down -v             # also remove volumes (e.g. postgres data)
```

## Troubleshooting

See [../docs/TROUBLESHOOTING.md#docker](../docs/TROUBLESHOOTING.md#docker).
