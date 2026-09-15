# System Architecture

> **Purpose:** Describe the overall system design — major components, data flow, and how they interact.
> **Audience:** Engineers, architects, and technical stakeholders.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md), [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md), [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md), [../adr/README.md](../adr/README.md)

---

## Overview

The system is a three-tier application plus an AI agent layer:

1. **Presentation tier** — React/TypeScript/MUI SPA.
2. **Application tier** — FastAPI backend exposing a REST API, hosting business logic and the AI agent orchestration.
3. **Data tier** — JSON files (prototype) or PostgreSQL (production).
4. **AI layer** — a set of modular agents coordinated by an Orchestrator, using a swappable LLM provider (Ollama / OpenAI / Azure OpenAI).

## Components

| Component | Responsibility | Location |
|---|---|---|
| Frontend SPA | Dashboards, report views, opportunity/agent management UI | `frontend/` |
| API layer | HTTP interface, request validation, auth (future) | `backend/app/api/` |
| Service layer | Business logic, orchestration triggers | `backend/app/services/` |
| Agent layer | AI agent implementations | `backend/app/agents/` |
| Data access layer | Repository abstraction over JSON/PostgreSQL | `backend/app/db/` |
| Storage | JSON files or PostgreSQL | `data/` (samples), production DB |

## Request flow (example: generate weekly report)

1. User triggers "Generate Report" in the frontend.
2. Frontend calls `POST /api/v1/reports/weekly`.
3. Route handler validates the request, calls `ReportService`.
4. `ReportService` invokes the **Orchestrator Agent**.
5. Orchestrator fans out to domain agents (Opportunity, Procurement, Defence Intelligence, Competitor Intelligence, Technology Trends) in parallel.
6. Each domain agent returns schema-validated JSON.
7. Orchestrator passes combined output to the **Executive Summary Agent**.
8. `ReportService` persists the final report via the data access layer.
9. API returns the report; frontend renders it (tables, Plotly/Recharts visualisations).

See [DATA_PIPELINE.md](DATA_PIPELINE.md) for the detailed data flow and [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) for agent coordination.

## Non-functional priorities (current phase)

| Concern | Current approach |
|---|---|
| Scalability | Not a priority in prototype phase; single-instance local/dev deployment |
| Availability | Not a priority; no SLA in prototype phase |
| Security | Data-handling discipline (see [../SECURITY.md](../SECURITY.md)); auth deferred to a future epic |
| Observability | Structured logging (see [../docs/CODING_STANDARDS.md#logging](../docs/CODING_STANDARDS.md#logging)); metrics/tracing deferred |
| Portability | Docker-first, so the same containers run on a laptop or in the cloud unchanged |

## What's explicitly out of scope today

- Authentication/authorisation
- Multi-tenant support
- Horizontal scaling / load balancing
- Cloud deployment (see [FUTURE_CLOUD_ARCHITECTURE.md](FUTURE_CLOUD_ARCHITECTURE.md) for the target, not the current state)

## Related decisions

See [../adr/](../adr/) for the record of why FastAPI, JSON-then-PostgreSQL, and the modular agent approach were chosen.
