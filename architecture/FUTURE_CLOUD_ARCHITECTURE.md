# Future Cloud Architecture

> **Purpose:** Describe the target cloud architecture direction, to be formalised via ADRs as the project matures beyond local development.
> **Audience:** Architects and technical leads planning beyond the prototype phase.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md), [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md), [DATABASE_DESIGN.md](DATABASE_DESIGN.md), [../adr/README.md](../adr/README.md)

---

## Status: directional, not committed

Nothing in this document is implemented or approved for build — it exists to give contributors a sense of where the architecture is headed so current decisions (e.g. the repository pattern in [DATABASE_DESIGN.md](DATABASE_DESIGN.md), the provider abstraction in [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)) are made compatibly. Any move toward this target requires its own ADR(s) and, given the sensitivity of defence-sector data, a security/compliance review first (see [../SECURITY.md](../SECURITY.md)).

## Target platform: Microsoft Azure

Given the stack already anticipates **Azure OpenAI** as a future AI provider, Azure is the natural cloud target — consistent tooling, identity, and (for UK/allied government-adjacent work) relevant compliance certifications.

## Indicative target architecture

```
┌────────────────────────────────────────────────────────────────┐
│                              Azure                                 │
│                                                                     │
│  Azure Front Door / App Gateway                                     │
│         │                                                           │
│  ┌──────▼───────────┐        ┌───────────────────────┐             │
│  │ Azure Static Web   │        │  Azure Container Apps    │             │
│  │ Apps (frontend)     │        │  (backend API, agents)    │             │
│  └────────────────────┘        └───────────┬───────────────┘             │
│                                              │                             │
│                     ┌────────────────────────┼─────────────────────┐     │
│                     ▼                        ▼                     ▼     │
│           Azure Database for         Azure OpenAI          Azure Key    │
│           PostgreSQL (Flexible          Service              Vault      │
│           Server)                                                       │
│                     │                                                    │
│                     ▼                                                    │
│           Azure Blob Storage (report exports, source documents)          │
│                                                                            │
│  Azure Monitor / Application Insights (observability, across all above)   │
│  Microsoft Entra ID (authentication/authorisation)                        │
└────────────────────────────────────────────────────────────────┘
```

## Component mapping

| Local/current | Cloud target |
|---|---|
| Docker Compose `frontend` | Azure Static Web Apps (or Container Apps if SSR is later needed) |
| Docker Compose `backend` | Azure Container Apps (scales to zero, container-native, fits the existing Dockerfile) |
| Ollama | Azure OpenAI Service (provider swap already supported — see [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)) |
| JSON files / local Postgres | Azure Database for PostgreSQL – Flexible Server |
| `.env` secrets | Azure Key Vault, injected via managed identity |
| No auth (current) | Microsoft Entra ID (Azure AD) — SSO for consulting staff |
| Manual report generation | Azure Container Apps Jobs / Logic Apps for scheduled ingestion + report runs |
| No observability | Azure Monitor + Application Insights |
| Source documents (news, notices) | Azure Blob Storage |

## Key changes required to get there (not yet started)

1. **Auth**: introduce authentication/authorisation (currently explicitly out of scope — see [SYSTEM_ARCHITECTURE.md#whats-explicitly-out-of-scope-today](SYSTEM_ARCHITECTURE.md#whats-explicitly-out-of-scope-today)).
2. **Async job execution**: move report generation from synchronous request-time agent calls to a background job/queue (see [BACKEND_ARCHITECTURE.md#backgroundasync-work](BACKEND_ARCHITECTURE.md#backgroundasync-work)).
3. **CI/CD**: extend [../.github/workflows/ci.yml](../.github/workflows/ci.yml) with a deployment pipeline (build → push to Azure Container Registry → deploy to Container Apps).
4. **Secrets management**: replace `.env` with Key Vault + managed identity.
5. **Observability**: structured logs shipped to Application Insights; basic dashboards for agent success rate, latency, and cost.
6. **Data residency & compliance review**: confirm region, retention, and classification handling requirements before any real defence-sector data is processed in the cloud.

## Non-goals for now

Multi-cloud portability, Kubernetes, and multi-region deployment are not targets — Azure Container Apps' simplicity is preferred over Kubernetes' operational overhead unless a concrete scaling need emerges.
