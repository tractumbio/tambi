# Coding Standards

> **Purpose:** Define consistent conventions for Python, React/TypeScript, FastAPI, naming, structure, testing, logging, documentation, comments, commits, and pull requests.
> **Audience:** All engineering contributors.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../CONTRIBUTING.md](../CONTRIBUTING.md), [TESTING_STRATEGY.md](TESTING_STRATEGY.md), [../architecture/FOLDER_STRUCTURE.md](../architecture/FOLDER_STRUCTURE.md)

---

## Python

- **Version**: 3.11+. **Formatter/linter**: `ruff` (format + lint). **Type checker**: `mypy` in strict-ish mode (`disallow_untyped_defs = true`).
- Type-hint all public function signatures. Use `pydantic` models for any data crossing a boundary (API request/response, agent input/output).
- Prefer `pathlib.Path` over `os.path`. Prefer f-strings over `.format()`/`%`.
- One class/major concept per file where practical; keep modules under ~300 lines — split by responsibility rather than growing a file indefinitely.
- No bare `except:`; catch specific exceptions. Never silently swallow an exception — log or re-raise.
- Dependency injection via FastAPI's `Depends()` rather than global singletons, except for stateless config.

```python
# Good
async def get_opportunity(opportunity_id: str, repo: OpportunityRepository = Depends(get_opportunity_repo)) -> OpportunityRead:
    opportunity = await repo.get(opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return OpportunityRead.model_validate(opportunity)
```

## FastAPI

- Group endpoints by domain under `backend/app/api/routes/` (e.g. `opportunities.py`, `reports.py`, `agents.py`); one `APIRouter` per file, included in `app/main.py`.
- Every route has a `response_model`; every request body is a Pydantic model — no raw `dict` payloads.
- Use `status_code` explicitly for non-200 responses (`201` on create, `204` on delete).
- Business logic lives in `app/services/`, not in route handlers — route handlers should stay thin (parse → call service → return).
- Version the API under `/api/v1` (see `.env.example`'s `API_V1_PREFIX`); breaking changes get a new version, not a silent change.

## React / TypeScript

- **Strict mode**: `"strict": true` in `tsconfig.json`. No `any` without a `// eslint-disable-next-line` and a comment explaining why.
- Functional components + hooks only; no class components.
- Component files: one component per file, named `PascalCase.tsx`, colocated with its styles/tests if any.
- Props typed with an explicit `interface Props { ... }`; no implicit `any` props.
- Data fetching goes through `frontend/src/api/` (typed client functions), not inline `fetch` calls in components.
- Prefer composition over prop-drilling more than 2 levels — use context or a small state library once it gets past that.
- Material UI: use theme tokens (`sx`, theme palette/spacing) rather than hardcoded colours/pixel values — see `frontend/src/theme/`.

```tsx
// Good
interface OpportunityCardProps {
  opportunity: Opportunity;
  onSelect: (id: string) => void;
}

export function OpportunityCard({ opportunity, onSelect }: OpportunityCardProps) {
  return (
    <Card onClick={() => onSelect(opportunity.id)} sx={{ p: 2 }}>
      <Typography variant="h6">{opportunity.title}</Typography>
    </Card>
  );
}
```

## Naming

| Item | Convention | Example |
|---|---|---|
| Python files/modules | `snake_case` | `opportunity_service.py` |
| Python classes | `PascalCase` | `OpportunityRepository` |
| Python functions/vars | `snake_case` | `get_active_opportunities()` |
| TS/React files (components) | `PascalCase.tsx` | `OpportunityCard.tsx` |
| TS files (non-component) | `camelCase.ts` | `formatCurrency.ts` |
| TS interfaces/types | `PascalCase` | `interface Opportunity` |
| TS variables/functions | `camelCase` | `fetchOpportunities()` |
| REST endpoints | `kebab-case`, plural nouns | `/api/v1/opportunities` |
| JSON schema fields | `snake_case` (matches Python/Pydantic) | `submitted_at` |
| Branches | `type/TICKET-short-description` | `feature/US-014-agent-schema` |
| Env vars | `SCREAMING_SNAKE_CASE` | `OLLAMA_BASE_URL` |

## Folder structure

See [../architecture/FOLDER_STRUCTURE.md](../architecture/FOLDER_STRUCTURE.md) for the full rationale. Rule of thumb: organise backend and AI-agent code by **domain/responsibility** (`services/`, `agents/`, `api/routes/`), and frontend by **UI concern** (`pages/`, `components/`, `api/`).

## Testing

- Every new function/endpoint/component with logic gets a test in the same PR. See [TESTING_STRATEGY.md](TESTING_STRATEGY.md) for the full pyramid (unit, integration, prompt, regression, manual, acceptance).
- Backend: `pytest`, tests mirror the module path (`app/services/opportunity_service.py` → `tests/backend/services/test_opportunity_service.py`).
- Frontend: `vitest` + `React Testing Library`; test user-visible behaviour, not implementation details.
- Mock external calls (LLM providers, network) in unit tests; integration tests may hit a local Ollama instance.

## Logging

- Python: use the standard `logging` module via a configured logger per module (`logger = logging.getLogger(__name__)`), never bare `print()`.
- Structured where possible — include `request_id`/`agent_name`/`opportunity_id` as extra context, not string-concatenated into the message.
- Log levels: `DEBUG` (verbose dev detail), `INFO` (normal operation milestones — e.g. "agent run completed"), `WARNING` (recoverable issue), `ERROR` (failed operation), `CRITICAL` (service-level failure).
- Never log secrets, API keys, or full LLM prompts/responses containing sensitive data at `INFO` or above — use `DEBUG` and ensure it's disabled in production.
- Frontend: use `console.error`/`console.warn` sparingly in production code; prefer surfacing errors via UI state. No `console.log` left in committed code.

## Documentation

- Every markdown file in this repository follows the standard header block (Purpose, Audience, Last Updated, Related Documents, Version, Author) — see any file in [docs/](.) for the pattern.
- Public functions/classes in Python get a one-line docstring if their behaviour isn't obvious from the name and signature; skip docstrings that just restate the function name.
- API changes are documented via FastAPI's OpenAPI (automatic from route + Pydantic model definitions) — keep response models accurate rather than writing parallel documentation.

## Comments

- Default to no comments. Well-named code should explain *what*.
- Write a comment only to explain *why*: a non-obvious constraint, a workaround for a specific bug/API quirk, or an invariant that isn't visible locally.
- Do not leave commented-out code in commits — delete it; Git history preserves it.
- Do not write comments that reference a ticket number or "fixes issue X" — that belongs in the commit message/PR description.

## Git commits

Conventional Commits — see [../CONTRIBUTING.md](../CONTRIBUTING.md#commit-messages) for format and types. Keep the summary line ≤ 72 characters, imperative mood ("add", not "added"/"adds").

## Pull requests

- One logical change per PR. If you find yourself writing "and also" in the description, consider splitting it.
- Fill in the full [PR template](../.github/PULL_REQUEST_TEMPLATE.md) — link the story/task, describe the change, list how it was tested.
- CI (lint, type-check, tests) must pass before requesting review.
- Reviewers should respond within 1 business day; author addresses feedback or explains disagreement — don't silently dismiss comments.
- Squash-merge with a Conventional Commit-style summary.
