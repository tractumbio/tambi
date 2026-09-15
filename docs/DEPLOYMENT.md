# Deployment (dev)

TAMBI deploys to **Azure Container Apps** with a **Postgres Flexible Server**, built from
the `backend/` and `frontend/` Dockerfiles. This is a *dev* target — single region, no HA,
burstable Postgres.

## Architecture

```
Frontend (nginx, static SPA)  ──▶  Backend (FastAPI/uvicorn)  ──▶  Postgres Flexible Server
        Container App                    Container App                  (dcih database)
                         both images in Azure Container Registry
```

The backend container runs `alembic upgrade head` on start (see `backend/docker-entrypoint.sh`),
so schema is applied automatically on deploy.

## One-shot deploy (az CLI)

```bash
az login
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export PG_ADMIN_PASSWORD='<a-strong-password>'
RG=tambi-dev-rg LOCATION=australiaeast ./scripts/deploy-dev.sh
```

The script: creates the resource group + ACR, builds the backend image in ACR, deploys the
Bicep (`infra/main.bicep`), then rebuilds the frontend pointing at the backend's public URL
and redeploys. It prints the backend health URL and the frontend URL at the end.

## CI/CD (GitHub Actions)

`.github/workflows/deploy-dev.yml` runs the same flow on push to `deploy-dev` (or manual
dispatch). Configure repo secrets:

| Secret | Purpose |
|---|---|
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | OIDC federated login |
| `PG_ADMIN_PASSWORD` | Postgres admin password |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | AI providers |

Set up the OIDC app registration + federated credential per
[azure/login OIDC docs](https://github.com/Azure/login#configure-a-federated-credential-to-use-oidc).

## First-run data load

The DB starts empty. Run the ingestion + seeds as one-off Container App jobs (or exec into
the backend revision):

```bash
python -m app.ingest.backfill --from 2021-09-15 --to 2026-09-16   # Defence contracts
python -m app.processing.reprocess                                # themes/offerings/competitors
python -m app.processing.load_reference_projects                  # capability corpus
python -m app.ingest.atms                                         # live opportunities
python -m app.intelligence.harvest_news --effort standard         # news knowledge base
```

## Local (docker-compose)

```bash
cd docker && docker compose --profile postgres up --build
# frontend :5173, backend :8000, postgres :5432
```

## Notes / dev caveats

- The Postgres firewall rule opens `0.0.0.0` (Azure services) — **dev only**; lock down with
  VNet integration + private endpoint before any non-dev use.
- Secrets are passed as Container App secrets from CLI/Actions params. For anything beyond
  dev, source them from **Azure Key Vault** instead.
- `EMBEDDING_BACKEND=openai` keeps the image lean (no torch). Switch to `local` only if you
  add `sentence-transformers` to `requirements.txt`.
