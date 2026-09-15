# Development Guide

> **Purpose:** Describe the day-to-day workflow for developing features in this repository.
> **Audience:** Active contributors (backend, frontend, AI agent engineers).
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [CODING_STANDARDS.md](CODING_STANDARDS.md), [../CONTRIBUTING.md](../CONTRIBUTING.md), [TESTING_STRATEGY.md](TESTING_STRATEGY.md), [../architecture/SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md)

---

## Daily workflow

1. **Sync with `main`**
   ```bash
   git checkout main
   git pull origin main
   ```
2. **Pick up a work item** from [tasks/](../tasks/) or the linked Azure DevOps board. Confirm it meets the [Definition of Ready](../user-stories/README.md#definition-of-ready).
3. **Create a branch** (see [../.github/BRANCH_STRATEGY.md](../.github/BRANCH_STRATEGY.md)):
   ```bash
   git checkout -b feature/US-014-opportunity-agent-schema
   ```
4. **Start the relevant services** (backend / frontend / Ollama) per [GETTING_STARTED.md](GETTING_STARTED.md), or run the full stack via `docker compose -f docker/docker-compose.yml up`.
5. **Write code + tests together.** No PR should add logic without corresponding tests — see [TESTING_STRATEGY.md](TESTING_STRATEGY.md).
6. **Run checks locally before pushing:**
   ```bash
   # Backend
   cd backend && ruff check . && mypy app && pytest

   # Frontend
   cd frontend && npm run lint && npm run type-check && npm test
   ```
7. **Commit** using Conventional Commits (see [CODING_STANDARDS.md](CODING_STANDARDS.md#git-commits)).
8. **Push and open a PR** using the [PR template](../.github/PULL_REQUEST_TEMPLATE.md). Link the user story/task.
9. **Address review feedback**, keep the branch up to date with `main`, and squash-merge once approved.

## Working across the stack

| I'm working on... | Start here |
|---|---|
| A new API endpoint | [../architecture/BACKEND_ARCHITECTURE.md](../architecture/BACKEND_ARCHITECTURE.md), `backend/app/api/routes/` |
| A new UI screen | [../architecture/FRONTEND_ARCHITECTURE.md](../architecture/FRONTEND_ARCHITECTURE.md), `frontend/src/pages/` |
| A new/updated AI agent | [../ai-agents/README.md](../ai-agents/README.md), [../architecture/AGENT_ARCHITECTURE.md](../architecture/AGENT_ARCHITECTURE.md) |
| A new/updated prompt | [../prompts/README.md](../prompts/README.md) |
| A data model change | [../architecture/DATABASE_DESIGN.md](../architecture/DATABASE_DESIGN.md), `data/` sample schemas |
| Reports/visualisation | [../architecture/COMPONENT_RELATIONSHIPS.md](../architecture/COMPONENT_RELATIONSHIPS.md) |

## Local environments

| Service | URL | Notes |
|---|---|---|
| Frontend (Vite dev server) | http://localhost:5173 | Hot reload |
| Backend (FastAPI) | http://localhost:8000 | Swagger UI at `/docs` |
| Ollama | http://localhost:11434 | Local LLM runtime |
| PostgreSQL (optional, Docker) | localhost:5432 | Only used when `DATABASE_MODE=postgres` |

## Code review expectations

- Small, focused PRs (target < 400 lines changed, excluding generated/lockfiles).
- Every PR includes or updates tests.
- Every PR that changes architecture or adds a dependency links an [ADR](../adr/) or explains why one isn't needed.
- Reviewers check correctness, security (see [../SECURITY.md](../SECURITY.md)), and adherence to [CODING_STANDARDS.md](CODING_STANDARDS.md) — not just "does it run."

## Keeping documentation current

If your change affects architecture, an agent's contract, a prompt, or the API surface, update the relevant doc in the same PR. Documentation drift is treated as a bug.

## When you're blocked

- Technical setup issue → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- General question → [FAQ.md](FAQ.md)
- Process/planning question → check the current [sprint-planning/](../sprint-planning/) doc, then ask the core team.
