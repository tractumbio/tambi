# AI Architecture

> **Purpose:** Describe how AI/LLM capability is integrated into the system — provider abstraction, configuration, and design principles.
> **Audience:** Engineers building or integrating with the AI layer.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md), [../docs/AI_DEVELOPMENT_GUIDE.md](../docs/AI_DEVELOPMENT_GUIDE.md), [../ai-agents/README.md](../ai-agents/README.md), [../prompts/README.md](../prompts/README.md)

---

## Goals

1. Let every agent work identically regardless of which LLM provider is behind it.
2. Make local development free and offline-capable (Ollama).
3. Make the path to production-grade output (OpenAI/Azure OpenAI) a configuration change, not a rewrite.
4. Treat prompts and schemas as first-class, versioned, reviewable artefacts.

## Provider abstraction

```
backend/app/agents/
├── providers/
│   ├── base.py            AIProvider protocol: complete(prompt, schema) -> dict
│   ├── ollama_provider.py
│   ├── openai_provider.py
│   └── azure_openai_provider.py
├── base_agent.py           Shared agent behaviour (schema validation, retry, logging)
├── orchestrator_agent.py
├── opportunity_agent.py
├── procurement_agent.py
├── defence_intelligence_agent.py
├── competitor_intelligence_agent.py
├── accenture_intelligence_agent.py
├── technology_trends_agent.py
├── executive_summary_agent.py
└── research_agent.py
```

All providers implement the same interface:

```python
class AIProvider(Protocol):
    async def complete(self, prompt: str, *, response_schema: type[BaseModel], temperature: float = 0.2) -> BaseModel: ...
```

Selection is driven by `AI_PROVIDER` in `.env` (`ollama` | `openai` | `azure_openai`) via a factory in `app/core/config.py` — see [.env.example](../.env.example).

## Structured output

Every agent call requests output constrained to a Pydantic schema (via JSON-mode/function-calling where the provider supports it, or via schema-in-prompt + validation-and-retry where it doesn't). Invalid output is retried once with an error-correction hint, then treated as a failure — see each agent's "Failure Handling" section in [../ai-agents/](../ai-agents/).

## Prompt management

Prompts are versioned markdown files in [prompts/](../prompts/), not inline Python strings. `app/agents/base_agent.py` loads the relevant prompt file(s) at call time and interpolates structured input. This keeps prompts reviewable in PRs and testable independently of code changes — see [../docs/AI_DEVELOPMENT_GUIDE.md](../docs/AI_DEVELOPMENT_GUIDE.md).

## Model selection guidance

| Task type | Recommended temperature | Notes |
|---|---|---|
| Extraction/classification (Opportunity, Procurement, Defence Intelligence agents) | 0.0–0.2 | Favour determinism and schema adherence |
| Synthesis/comparison (Competitor Intelligence, Technology Trends agents) | 0.2–0.4 | Some latitude for connecting information |
| Prose generation (Executive Summary Agent) | 0.4–0.6 | Needs natural language quality; still schema-constrained at the top level |

## Cost & latency (future providers)

Once OpenAI/Azure OpenAI are enabled, track token usage per agent run (logged, not yet dashboarded) to inform model tier selection (e.g. a smaller model for extraction, a larger one for the Executive Summary Agent). This is a future optimisation, not a current requirement.

## Security

See [../docs/AI_DEVELOPMENT_GUIDE.md#security-considerations](../docs/AI_DEVELOPMENT_GUIDE.md#security-considerations) and [../SECURITY.md](../SECURITY.md) — prompt injection from ingested content, data minimisation, and no autonomous external actions are treated as architectural constraints, not just guidelines.
