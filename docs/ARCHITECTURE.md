# Architecture Overview

> **Purpose:** High-level orientation to the system architecture, with links to the detailed architecture documents.
> **Audience:** All contributors; especially useful for onboarding.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../architecture/SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md), [../architecture/AGENT_ARCHITECTURE.md](../architecture/AGENT_ARCHITECTURE.md), [../adr/README.md](../adr/README.md)

---

## The one-paragraph version

A React/TypeScript/MUI frontend calls a Python/FastAPI backend. The backend orchestrates a set of modular AI agents (via Ollama locally, OpenAI/Azure OpenAI in future) that each own one intelligence domain — opportunities, procurement, defence intelligence, competitors, technology trends — and an Orchestrator Agent coordinates them into a combined weekly report, summarised by an Executive Summary Agent. Data is stored as JSON in the prototype phase and PostgreSQL in production. Everything runs locally via Docker Compose today; a cloud target architecture is defined for later.

## Diagram

```
┌─────────────────────────┐        ┌──────────────────────────────┐
│   Frontend (React/MUI)   │◄──────►│   Backend (FastAPI, REST)     │
│  Dashboards · Reports    │  HTTP  │   API · Services · Agents     │
└─────────────────────────┘        └──────────────┬─────────────────┘
                                                    │
                                     ┌──────────────▼─────────────────┐
                                     │      Orchestrator Agent          │
                                     └───┬───────┬───────┬───────┬────┘
                                         │       │       │       │
                              ┌──────────▼─┐ ┌──▼────┐ ┌▼─────┐ ┌▼──────────┐
                              │ Opportunity│ │Procure-│ │Defence│ │Competitor │
                              │   Agent    │ │  ment  │ │ Intel │ │  Intel /  │
                              │            │ │ Agent  │ │ Agent │ │ Accenture │
                              └────────────┘ └────────┘ └───────┘ └───────────┘
                                         │       │       │       │
                                     ┌───▼───────▼───────▼───────▼────┐
                                     │  Executive Summary Agent          │
                                     └──────────────┬───────────────────┘
                                                    │
                                     ┌──────────────▼─────────────────┐
                                     │  Storage: JSON (proto) / Postgres │
                                     └──────────────────────────────────┘
```

## Where to go next

| I want to understand... | Read |
|---|---|
| Overall system design | [../architecture/SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md) |
| The React application | [../architecture/FRONTEND_ARCHITECTURE.md](../architecture/FRONTEND_ARCHITECTURE.md) |
| The FastAPI application | [../architecture/BACKEND_ARCHITECTURE.md](../architecture/BACKEND_ARCHITECTURE.md) |
| How AI fits together | [../architecture/AI_ARCHITECTURE.md](../architecture/AI_ARCHITECTURE.md) |
| How data flows end-to-end | [../architecture/DATA_PIPELINE.md](../architecture/DATA_PIPELINE.md) |
| Individual agent design | [../architecture/AGENT_ARCHITECTURE.md](../architecture/AGENT_ARCHITECTURE.md) and [../ai-agents/](../ai-agents/) |
| Data model / storage | [../architecture/DATABASE_DESIGN.md](../architecture/DATABASE_DESIGN.md) |
| Repository layout rationale | [../architecture/FOLDER_STRUCTURE.md](../architecture/FOLDER_STRUCTURE.md) |
| How components talk to each other | [../architecture/COMPONENT_RELATIONSHIPS.md](../architecture/COMPONENT_RELATIONSHIPS.md) |
| How we deploy today | [../architecture/DEPLOYMENT_ARCHITECTURE.md](../architecture/DEPLOYMENT_ARCHITECTURE.md) |
| Where this is headed (Azure) | [../architecture/FUTURE_CLOUD_ARCHITECTURE.md](../architecture/FUTURE_CLOUD_ARCHITECTURE.md) |
| Why a decision was made | [../adr/README.md](../adr/README.md) |

## Design principles

1. **Modular agents, single responsibility** — each agent owns one intelligence domain and one JSON output contract; the Orchestrator composes them rather than any agent reaching into another's domain.
2. **Provider-agnostic AI layer** — swapping Ollama for OpenAI/Azure OpenAI should require config changes, not rewriting agents.
3. **Storage-agnostic data layer** — the JSON-to-PostgreSQL migration should not require rewriting business logic; access goes through a repository interface (see [../architecture/DATABASE_DESIGN.md](../architecture/DATABASE_DESIGN.md)).
4. **Contract-first** — every agent and API boundary is defined by a schema before it's implemented.
5. **Local-first development** — the full stack runs on a laptop via Docker Compose; cloud is an additive future step, not a dependency for day-to-day development.
