# ADR-0001: Use FastAPI for the backend

> **Purpose:** Record the decision to use FastAPI as the backend web framework.
> **Audience:** All contributors.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../architecture/BACKEND_ARCHITECTURE.md](../architecture/BACKEND_ARCHITECTURE.md)

---

## Status

Accepted

## Context

The backend needs to expose a REST API to the React frontend, orchestrate calls to AI agents/LLM providers, and validate structured data flowing in and out of those agents. The team's primary backend language is Python (matching the AI/data-science ecosystem the agents rely on — LLM SDKs, JSON schema tooling).

## Decision

Use **FastAPI** as the backend web framework, with **Pydantic v2** for request/response and agent I/O schema validation, served by **Uvicorn**.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| FastAPI (chosen) | Native async support (needed for concurrent agent calls); Pydantic integration gives schema validation "for free" at API and agent boundaries; automatic OpenAPI docs; strong typing story | Younger ecosystem than Flask/Django; some third-party libraries lag behind |
| Flask | Mature, huge ecosystem, simple | No native async, no built-in validation/schema layer — would need to bolt on Marshmallow/Pydantic and an async extension separately |
| Django (+ DRF) | Batteries-included, admin panel, ORM | Heavier than needed for an API-only service; ORM assumes a relational model from day one, conflicting with the JSON-first prototype phase (see [ADR-0002](0002-use-json-storage-for-prototype.md)) |

## Consequences

- Pydantic schemas double as both the API contract and the AI agent output contract, reducing duplicate validation logic (see [../architecture/AI_ARCHITECTURE.md](../architecture/AI_ARCHITECTURE.md)).
- Async-first design fits the fan-out/fan-in agent orchestration pattern (see [../architecture/AGENT_ARCHITECTURE.md](../architecture/AGENT_ARCHITECTURE.md)) without extra plumbing.
- Automatic OpenAPI/Swagger docs (`/docs`) reduce the documentation burden for the API surface.
- The team takes on FastAPI-specific idioms (dependency injection via `Depends()`, async route handlers) — documented in [../docs/CODING_STANDARDS.md#fastapi](../docs/CODING_STANDARDS.md#fastapi).

## Related decisions

[ADR-0002](0002-use-json-storage-for-prototype.md) (storage), [ADR-0003](0003-modular-ai-agent-architecture.md) (agent architecture) both build on this choice.
