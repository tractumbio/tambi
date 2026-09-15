# Agent Architecture

> **Purpose:** Describe how the AI agents are structured, coordinated, and how they communicate.
> **Audience:** Engineers building or extending agents.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md), [DATA_PIPELINE.md](DATA_PIPELINE.md), [../ai-agents/README.md](../ai-agents/README.md), [../prompts/README.md](../prompts/README.md)

---

## Agent roster

| Agent | Role |
|---|---|
| [Orchestrator Agent](../ai-agents/orchestrator-agent.md) | Coordinates all other agents, assembles the final report |
| [Opportunity Agent](../ai-agents/opportunity-agent.md) | Identifies and structures business opportunities |
| [Procurement Agent](../ai-agents/procurement-agent.md) | Analyses procurement notices and contract data |
| [Defence Intelligence Agent](../ai-agents/defence-intelligence-agent.md) | Tracks defence agency/programme activity |
| [Competitor Intelligence Agent](../ai-agents/competitor-intelligence-agent.md) | Tracks competitor positioning and wins generally |
| [Accenture Intelligence Agent](../ai-agents/accenture-intelligence-agent.md) | Specialised tracking of Accenture Federal/Defence activity |
| [Technology Trends Agent](../ai-agents/technology-trends-agent.md) | Identifies emerging technology signals relevant to defence |
| [Executive Summary Agent](../ai-agents/executive-summary-agent.md) | Synthesises all agent output into a narrative summary |
| [Research Agent](../ai-agents/research-agent.md) | General-purpose research support for ad hoc queries |

## Coordination pattern

The **Orchestrator Agent** uses a **fan-out / fan-in** pattern:

```
                 ┌─────────────┐
   request  ───▶ │ Orchestrator │
                 └──────┬──────┘
                        │ fan-out (parallel)
        ┌───────┬───────┼───────┬────────────┐
        ▼       ▼       ▼       ▼            ▼
   Opportunity Procure- Defence Competitor  Technology
     Agent      ment    Intel    Intel /    Trends
               Agent    Agent   Accenture    Agent
        │       │       │       │            │
        └───────┴───────┼───────┴────────────┘
                        │ fan-in
                        ▼
              ┌───────────────────┐
              │ Executive Summary   │
              │       Agent          │
              └─────────┬───────────┘
                        ▼
                 final report (JSON)
```

Domain agents do not call each other directly — all coordination flows through the Orchestrator. This keeps each agent independently testable and keeps the dependency graph a shallow two levels deep (Orchestrator → domain agent, Orchestrator → Executive Summary Agent).

## Shared agent contract

Every agent (documented individually in [../ai-agents/](../ai-agents/)) defines:

- **Purpose** — the one thing it's responsible for.
- **Responsibilities** — what it does and explicitly does not do.
- **Inputs** — what it's given (typed).
- **Outputs** — its JSON schema.
- **Prompt** — reference to its file in [../prompts/](../prompts/).
- **Constraints** — hard rules (e.g. "never fabricate a source").
- **Success metrics** — how we know it's working.
- **Failure handling** — what happens when it fails or returns invalid output.

## Base agent behaviour

Implemented once in `backend/app/agents/base_agent.py` and reused by every agent:

- Loads the agent's prompt from [../prompts/](../prompts/).
- Calls the configured `AIProvider` (see [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)).
- Validates the response against the agent's Pydantic schema; retries once on validation failure with an error-correction hint.
- Logs run metadata (agent name, duration, success/failure, token usage where available) — never the raw prompt/response at `INFO` level if it may contain sensitive content (see [../docs/CODING_STANDARDS.md#logging](../docs/CODING_STANDARDS.md#logging)).
- Attaches source/lineage references to output (see [DATA_PIPELINE.md#data-lineage--traceability](DATA_PIPELINE.md#data-lineage--traceability)).

## Extensibility

Adding a new agent means: write its spec doc, write its prompt, implement it against `base_agent.py`, register it with the Orchestrator's fan-out list, add prompt fixtures. See [../docs/AI_DEVELOPMENT_GUIDE.md#adding-a-new-agent](../docs/AI_DEVELOPMENT_GUIDE.md#adding-a-new-agent).

## Why not a general-purpose single agent?

A single large-context "do everything" agent was considered and rejected (see [../adr/0003-modular-ai-agent-architecture.md](../adr/0003-modular-ai-agent-architecture.md)) — modular agents are independently testable, independently improvable, and produce more auditable, schema-constrained output per domain.
