# Testing Strategy

> **Purpose:** Define the testing pyramid and expectations for this project — unit, integration, AI prompt, regression, manual, and acceptance testing.
> **Audience:** All contributors; especially useful when writing or reviewing tests.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [CODING_STANDARDS.md](CODING_STANDARDS.md#testing), [../tests/README.md](../tests/README.md), [AI_DEVELOPMENT_GUIDE.md](AI_DEVELOPMENT_GUIDE.md)

---

## Testing pyramid

```
        ▲  Manual / Acceptance   (few, high-value, pre-release)
       ╱ ╲ Regression            (growing set, known-bad cases)
      ╱   ╲ Integration          (API + agent pipeline, moderate count)
     ╱     ╲ AI Prompt / Eval    (per-agent fixtures)
    ╱───────╲ Unit               (many, fast, run on every save)
```

Most tests should be unit tests. Each layer above it should have progressively fewer, more expensive tests.

## Unit tests

**What**: a single function, method, or component in isolation, with dependencies mocked.

- Backend: `pytest`, located under `tests/backend/`, mirroring `backend/app/` structure.
- Frontend: `vitest` + `React Testing Library`, colocated or under `tests/frontend/`.
- Target: fast (whole suite < 30s locally), no network/filesystem/LLM calls.

```bash
cd backend && pytest tests/backend -m unit
cd frontend && npm test
```

## Integration tests

**What**: multiple components together — e.g. an API route through to the service layer and a real (test) data store, or the Orchestrator calling real agent classes with a mocked LLM provider.

- Located under `tests/backend/integration/`.
- May use a local SQLite/temp JSON fixture in place of production PostgreSQL/JSON data.
- Should not require a real Ollama/OpenAI call by default (mock the provider) — see AI Prompt Testing below for the cases that do need a real model.

```bash
cd backend && pytest tests/backend -m integration
```

## AI prompt testing

**What**: validating that a given agent + prompt, run against representative fixture inputs, produces output that (a) is valid per the agent's JSON schema, and (b) meets basic content expectations (e.g. required fields populated, no obviously fabricated sources).

- Fixtures live under `tests/prompts/<agent-name>/`.
- Run against the local Ollama model by default — these are slower and less deterministic than unit tests, so they are not part of the fast feedback loop; run them before merging any prompt or agent change.
- Do **not** assert exact string equality on LLM output — assert schema validity, required-field presence, and value constraints (e.g. `confidence_score` within `[0, 1]`).
- When a real failure mode is found in production/dev (e.g. an agent hallucinates a contract value), add it as a regression fixture.

See [AI_DEVELOPMENT_GUIDE.md#prompt-testing-evals](AI_DEVELOPMENT_GUIDE.md#prompt-testing-evals).

## Regression testing

**What**: a growing collection of "this broke before, make sure it doesn't again" cases, spanning unit, integration, and prompt fixtures.

- Any bug fix should add a regression test that fails before the fix and passes after.
- Regression fixtures are tagged (`-m regression`) so they can be run as a full suite before a release.

## Manual testing

**What**: a human walking through the application to catch what automated tests miss — visual issues, unclear UX, edge cases not yet automated.

- Required before closing any story with a UI component — see the story's "Test Cases" section.
- Use the relevant [sprint-planning](../sprint-planning/) exit criteria as a checklist for what to manually verify before a sprint demo.

## Acceptance testing

**What**: verifying a user story meets its documented Acceptance Criteria, ideally by someone other than the author (or, where relevant, a stakeholder).

- Acceptance Criteria are written in the story itself (see [../user-stories/README.md](../user-stories/README.md)) using Given/When/Then format.
- A story is not "Done" until its acceptance criteria are verified — see [Definition of Done](../user-stories/README.md#definition-of-done).

## Coverage expectations

| Layer | Target |
|---|---|
| Backend unit | ≥ 80% line coverage on `app/services/`, `app/agents/` |
| Frontend unit | Critical components and hooks covered; 100% not required |
| Integration | Every API route has at least one happy-path + one error-path test |
| AI prompt | Every agent has ≥ 3 representative fixtures (typical, edge case, adversarial/malformed input) |

Coverage numbers are a guide, not a target to game — a meaningful test that documents behaviour beats a shallow test that only inflates the percentage.

## CI enforcement

See [../.github/workflows/ci.yml](../.github/workflows/ci.yml) — lint, type-check, and unit+integration tests run on every PR. AI prompt tests currently run on demand (they require a running Ollama instance) — see that workflow file for how to trigger them.
