# ADR-0003: Modular AI agent architecture over a single general-purpose agent

> **Purpose:** Record the decision to use multiple single-responsibility agents coordinated by an orchestrator, rather than one large general-purpose agent.
> **Audience:** All contributors building or extending the AI layer.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../architecture/AGENT_ARCHITECTURE.md](../architecture/AGENT_ARCHITECTURE.md), [../ai-agents/README.md](../ai-agents/README.md)

---

## Status

Accepted

## Context

The platform needs to analyse several distinct intelligence domains (opportunities, procurement, agency/programme activity, competitor positioning, technology trends) and combine them into a coherent report. A single large prompt asking one model call to "do everything" was the simplest initial idea, but raises concerns about output reliability, testability, and auditability — especially given the output feeds consulting deliverables where traceability to source matters.

## Decision

Use a **modular multi-agent architecture**: one agent per intelligence domain, each with a narrow responsibility, its own prompt, and its own JSON output schema, coordinated by an **Orchestrator Agent** using a fan-out/fan-in pattern, with a dedicated **Executive Summary Agent** for final narrative synthesis. See [../architecture/AGENT_ARCHITECTURE.md](../architecture/AGENT_ARCHITECTURE.md) for the full design.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| Modular agents + orchestrator (chosen) | Each agent independently testable/improvable; narrow prompts are easier to keep reliable and schema-constrained; failures are isolated (one domain failing doesn't block others); matches how a human analyst team would divide the work | More moving parts; requires an orchestration layer; more prompts/schemas to maintain |
| Single general-purpose agent | Simple to start; one prompt, one call | Harder to keep reliable as scope grows; a single schema covering every domain becomes unwieldy; a failure in one part of the output can invalidate the whole response; hard to unit-test in isolation; harder to audit which part of a claim came from where |
| Modular agents, no orchestrator (services call agents directly) | Simpler than adding an orchestrator | Coordination logic (fan-out, combining results, ordering) leaks into `services/`, duplicated across every place that needs a combined view; violates single-responsibility for services |

## Consequences

- Every agent must be documented to the same standard (Purpose, Responsibilities, Inputs, Outputs, JSON schema, Prompt, Constraints, Success Metrics, Failure Handling) — see [../ai-agents/README.md](../ai-agents/README.md) — so the pattern stays consistent as agents are added.
- The Orchestrator becomes a single, important point of coordination — its own reliability and error handling (partial failures — what happens if one domain agent fails but others succeed) needs explicit design, documented in the Orchestrator's own spec ([../ai-agents/orchestrator-agent.md](../ai-agents/orchestrator-agent.md)).
- Adding a new intelligence domain (e.g. a future "Regulatory Change Agent") is additive — a new agent registered with the Orchestrator — rather than a rewrite of a monolithic prompt.
- More total LLM calls per report generation than a single-call approach, with corresponding latency/cost — acceptable for the current use case (a periodic report, not a real-time chat interface) but worth monitoring once non-Ollama providers are enabled (see [../architecture/AI_ARCHITECTURE.md#cost--latency-future-providers](../architecture/AI_ARCHITECTURE.md#cost--latency-future-providers)).

## Related decisions

Builds on [ADR-0001](0001-use-fastapi-for-backend.md) (async support needed for fan-out) and [ADR-0002](0002-use-json-storage-for-prototype.md) (each agent's output persists through the same repository pattern).
