# AI Development Guide

> **Purpose:** Explain how to develop, test, and reason about the AI agent layer — providers, prompts, schemas, and evaluation.
> **Audience:** Contributors building or modifying AI agents and prompts.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../architecture/AI_ARCHITECTURE.md](../architecture/AI_ARCHITECTURE.md), [../architecture/AGENT_ARCHITECTURE.md](../architecture/AGENT_ARCHITECTURE.md), [../ai-agents/README.md](../ai-agents/README.md), [../prompts/README.md](../prompts/README.md)

---

## Mental model

An **agent** is a Python component with:

1. A **defined responsibility** (one intelligence domain).
2. A **prompt** (from [prompts/](../prompts/)) that instructs the LLM.
3. A **structured input contract** (what it's given).
4. A **structured output contract** (a JSON schema it must satisfy).
5. **Constraints** (what it must not do — e.g. fabricate a source).
6. **Success metrics** and **failure handling**.

All of this is documented per-agent in [ai-agents/](../ai-agents/) before implementation. Treat the JSON schema as the actual interface — implementation should validate against it, not just aim for it.

## Provider abstraction

Agents call an `AIProvider` interface (`backend/app/agents/`), not a specific SDK. Supported providers:

| Provider | Use | Config |
|---|---|---|
| `ollama` | Local development (default) | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| `openai` | Future / higher-quality output | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `azure_openai` | Future / enterprise deployment | `AZURE_OPENAI_*` vars |

Switching provider should be a config change (`AI_PROVIDER` in `.env`), not a code change in the agent itself. See [../architecture/AI_ARCHITECTURE.md](../architecture/AI_ARCHITECTURE.md).

## Working with prompts

- Prompts live in [prompts/](../prompts/) as versioned markdown, not inline strings in Python — this keeps them reviewable and diffable.
- Every prompt change is a PR, reviewed like code — a prompt change can silently break an agent's output contract.
- Use the `system.md` prompt as the shared baseline (tone, constraints, output-format rules); domain prompts extend it.
- When editing a prompt, re-run that agent's test cases (see [../tests/prompts/](../tests/prompts/)) before merging.

## Output validation

Every agent output is validated against its Pydantic/JSON schema before it's persisted or passed to the next agent. An agent that returns invalid JSON, or JSON that fails schema validation, is treated as a **failure**, not a best-effort partial success — see each agent's "Failure Handling" section in [ai-agents/](../ai-agents/).

## Prompt testing (evals)

- Maintain a small set of representative input fixtures per agent under `tests/prompts/`.
- A prompt/model change should not be merged without running its fixtures and comparing output against expected schema shape and, where feasible, expected content characteristics (not exact-string matching — LLM output varies).
- Track known-failure patterns (hallucinated sources, missed fields) as regression fixtures once found.
- See [TESTING_STRATEGY.md](TESTING_STRATEGY.md#ai-prompt-testing).

## Security considerations

- **Prompt injection**: content ingested from external sources (news articles, procurement notices) is untrusted input. Never let ingested text be interpreted as instructions — pass it as clearly delimited data within the prompt, and treat any embedded "ignore previous instructions"-style content as a signal to flag, not obey.
- **Data leakage**: do not include more context than an agent needs. Don't pass full raw source documents to a model if only specific fields are required.
- **No autonomous external actions**: agents produce structured intelligence output; they do not take actions (sending emails, making purchases, modifying records) without a human in the loop, at least through the current phase.
- **Determinism where it matters**: use low temperature for extraction/classification tasks; reserve higher temperature for the Executive Summary Agent's prose generation.

See also [../SECURITY.md](../SECURITY.md).

## Adding a new agent

1. Write its spec in [ai-agents/](../ai-agents/) following the existing template (Purpose, Responsibilities, Inputs, Outputs, JSON schema, Prompt, Constraints, Success Metrics, Failure Handling).
2. Add its prompt to [prompts/](../prompts/).
3. Register it with the Orchestrator ([../architecture/AGENT_ARCHITECTURE.md](../architecture/AGENT_ARCHITECTURE.md)).
4. Add fixtures under `tests/prompts/`.
5. Open an ADR if it changes the orchestration model or introduces a new provider/dependency.

## Local model recommendations

For local development via Ollama, `llama3.1:8b` balances speed and quality on typical laptop hardware. Use a larger model only if you have the VRAM/RAM to spare and need to validate output quality closer to what OpenAI/Azure OpenAI would produce.
