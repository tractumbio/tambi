# Branch Strategy

> **Purpose:** Define the branching model used in this repository.
> **Audience:** All contributors.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../CONTRIBUTING.md](../CONTRIBUTING.md), [RELEASE_STRATEGY.md](RELEASE_STRATEGY.md), [../docs/DEVOPS_FOR_BEGINNERS.md](../docs/DEVOPS_FOR_BEGINNERS.md)

---

## Model: trunk-based development

```
main                    protected, always deployable
 └─ feature/<ticket>-short-description
 └─ fix/<ticket>-short-description
 └─ chore/<ticket>-short-description
 └─ docs/<ticket>-short-description
```

- `main` is the only long-lived branch. It is protected: no direct pushes, PR + passing CI + review required.
- All work happens on short-lived branches created from `main`, merged back via PR.
- No `develop` branch, no long-lived release branches — releases are tags on `main` (see [RELEASE_STRATEGY.md](RELEASE_STRATEGY.md)).

## Branch naming

`type/TICKET-short-kebab-case-description`

| Type | Use for |
|---|---|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `chore/` | Tooling, deps, config, non-functional cleanup |
| `docs/` | Documentation-only changes |

Example: `feature/US-014-opportunity-agent-schema`

## Branch protection rules (main)

- Require pull request before merging.
- Require status checks to pass (CI — see [workflows/ci.yml](workflows/ci.yml)).
- Require at least 1 approving review (2 for changes touching `backend/app/db/` or `architecture/DATABASE_DESIGN.md`).
- No force-pushes to `main`.

## Keeping branches current

Merge (or rebase, if you're comfortable with it) `main` into your branch regularly — see [../docs/DEVOPS_FOR_BEGINNERS.md#19-how-to-update-from-main](../docs/DEVOPS_FOR_BEGINNERS.md#19-how-to-update-from-main). Long-lived branches accumulate conflict risk; aim to merge within a few days of opening.

## Hotfixes

For an urgent production fix (once a production environment exists — see [../architecture/FUTURE_CLOUD_ARCHITECTURE.md](../architecture/FUTURE_CLOUD_ARCHITECTURE.md)), branch `fix/` directly from the latest release tag, PR into `main`, and tag a patch release immediately after merge — no separate hotfix branch model is needed at this project's current scale.
