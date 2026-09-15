# Prompt / Agent Fixtures

> **Purpose:** Explain the fixture format used to test AI agent prompts against representative inputs.
> **Audience:** AI/backend engineers editing prompts or agents.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../../docs/TESTING_STRATEGY.md#ai-prompt-testing](../../docs/TESTING_STRATEGY.md#ai-prompt-testing), [../../docs/AI_DEVELOPMENT_GUIDE.md#prompt-testing-evals](../../docs/AI_DEVELOPMENT_GUIDE.md#prompt-testing-evals), [../../ai-agents/README.md](../../ai-agents/README.md)

---

## Format

Each agent has a subfolder named after it (e.g. `opportunity-agent/`), containing one JSON file per fixture case: `fixture-<NN>-<short-description>.json`, with this shape:

```json
{
  "description": "What this fixture is testing",
  "input": { "...": "matches the agent's documented Input schema" },
  "expectations": {
    "schema_valid": true,
    "min_items": 1,
    "required_fields_present": ["source_references"],
    "notes": "Any other assertion to check by hand until automated assertions cover it"
  }
}
```

Fixtures assert **shape and constraints**, not exact output text — LLM output varies run to run even at low temperature. See [../../docs/TESTING_STRATEGY.md#ai-prompt-testing](../../docs/TESTING_STRATEGY.md#ai-prompt-testing) for why.

## Minimum fixture set per agent

Every agent should have at least:

1. A **typical** case — realistic, clean source input.
2. An **edge case** — sparse/ambiguous source input (tests confidence scoring / null handling).
3. An **adversarial case** — source input containing something resembling an embedded instruction (tests the grounding/source-integrity rules in [../../prompts/system.md](../../prompts/system.md)).

## Running fixtures

Fixture execution requires a running Ollama instance (`ollama serve`, with the model from `.env`'s `OLLAMA_MODEL` pulled). Once agent implementations exist under `backend/app/agents/`, these fixtures are run via `pytest ../tests/prompts -m prompt_eval` (see [../README.md](../README.md)) — not part of the default fast test run.

## Current status

One example fixture (`opportunity-agent/fixture-01-typical.json`) is included as a template. Add fixtures alongside each agent's implementation, per [../../docs/AI_DEVELOPMENT_GUIDE.md#adding-a-new-agent](../../docs/AI_DEVELOPMENT_GUIDE.md#adding-a-new-agent).
