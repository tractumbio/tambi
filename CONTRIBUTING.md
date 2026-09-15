# Contributing Guide

> **Purpose:** Explain how to propose changes, the branching model, commit conventions, and the pull request lifecycle.
> **Audience:** All contributors, including first-time open-source contributors.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md), [.github/BRANCH_STRATEGY.md](.github/BRANCH_STRATEGY.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

---

## Before you start

1. Read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
2. Read [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) and complete environment setup.
3. Check [epics/](epics/), [user-stories/](user-stories/), and [tasks/](tasks/) (or the linked Azure DevOps board) to see if the work is already tracked. If not, create a work item before starting non-trivial changes.

## Ways to contribute

- **Code**: backend (FastAPI), frontend (React/TypeScript), AI agents, prompts.
- **Documentation**: architecture, guides, ADRs.
- **Testing**: unit, integration, prompt regression tests.
- **Review**: pull request reviews are a first-class contribution.

## Branching model

We use **trunk-based development with short-lived feature branches**. See [.github/BRANCH_STRATEGY.md](.github/BRANCH_STRATEGY.md) for full detail. Summary:

```
main                    protected, always deployable
 └─ feature/<ticket>-short-description
 └─ fix/<ticket>-short-description
 └─ chore/<ticket>-short-description
 └─ docs/<ticket>-short-description
```

- Branch from `main`.
- Keep branches short-lived (target: merged within a few days).
- Rebase or merge `main` into your branch regularly to avoid large conflicts.

## Commit messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<optional body>

<optional footer, e.g. Refs #US-014>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`.

Example:

```
feat(agents): add JSON schema validation to Opportunity Agent output

Validates agent output against schema before persisting to prevent
malformed records reaching the API layer.

Refs #US-014
```

See [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md#git-commits) for more.

## Pull requests

1. Open a PR against `main` using the [PR template](.github/PULL_REQUEST_TEMPLATE.md).
2. Link the related user story / task.
3. Ensure CI is green (lint, type-check, tests).
4. Request review from at least one other contributor (two for backend/data model changes).
5. Squash-merge once approved, using a Conventional Commit summary as the merge message.

See [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md#pull-requests) for review expectations.

## Definition of Ready / Definition of Done

Before starting work, a story should meet the [Definition of Ready](user-stories/README.md#definition-of-ready). Before closing work, it must meet the [Definition of Done](user-stories/README.md#definition-of-done).

## Reporting issues

Use the [issue templates](.github/ISSUE_TEMPLATE/) — bug report or feature request. Search existing issues first to avoid duplicates.

## Getting help

- Beginners: [docs/DEVOPS_FOR_BEGINNERS.md](docs/DEVOPS_FOR_BEGINNERS.md) and [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- General questions: [docs/FAQ.md](docs/FAQ.md)
- Still stuck: open a Discussion or ping the core team.

Thank you for contributing.
