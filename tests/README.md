# Tests

> **Purpose:** Index the test suites in this repository and point to the full testing strategy.
> **Audience:** All contributors.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../docs/TESTING_STRATEGY.md](../docs/TESTING_STRATEGY.md), [../docs/CODING_STANDARDS.md#testing](../docs/CODING_STANDARDS.md#testing)

---

## Full strategy

See [../docs/TESTING_STRATEGY.md](../docs/TESTING_STRATEGY.md) for the complete testing pyramid (unit, integration, AI prompt, regression, manual, acceptance) and coverage expectations. This folder holds the actual test code/fixtures; the strategy document explains the *why* and *how much*.

## Layout

```
tests/
├── backend/     pytest — unit + integration tests for the FastAPI app (mirrors backend/app/ structure)
├── frontend/     vitest + React Testing Library — tests that aren't colocated with a component
└── prompts/      Fixtures + expected-shape assertions for AI agent prompt/eval testing
```

Frontend unit tests may also be colocated next to the component they test (e.g. `frontend/src/components/OpportunityCard.test.tsx`) — use `tests/frontend/` for tests that span multiple components/pages or don't have an obvious single colocation point.

## Running everything

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test

# AI prompt fixtures (requires Ollama running — see docs/GETTING_STARTED.md)
cd backend && pytest ../tests/prompts -m prompt_eval
```

## Status

Only a health-check placeholder test exists today (`tests/backend/test_health.py`) — this repository is a framework scaffold, not yet the built application. See [../README.md#project-status](../README.md#project-status). Real test coverage grows alongside real implementation, per the Definition of Done in [../user-stories/README.md](../user-stories/README.md#definition-of-done).
