# Git Workflow

> **Purpose:** Consolidated reference for branch strategy, release strategy, and semantic versioning used in this repository.
> **Audience:** All contributors.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../.github/BRANCH_STRATEGY.md](../.github/BRANCH_STRATEGY.md), [../.github/RELEASE_STRATEGY.md](../.github/RELEASE_STRATEGY.md), [../.github/VERSIONING.md](../.github/VERSIONING.md), [../CONTRIBUTING.md](../CONTRIBUTING.md)

---

This page is a short index — the authoritative detail lives in the linked `.github/` policy docs, since GitHub-specific process documentation is kept alongside the templates/workflows it governs.

## Summary

- **Branching**: trunk-based, short-lived `type/TICKET-description` branches off `main`. Full detail: [../.github/BRANCH_STRATEGY.md](../.github/BRANCH_STRATEGY.md).
- **Releases**: tagged from `main` at sprint boundaries or on-demand for hotfixes. Full detail: [../.github/RELEASE_STRATEGY.md](../.github/RELEASE_STRATEGY.md).
- **Versioning**: Semantic Versioning (`MAJOR.MINOR.PATCH`). Full detail: [../.github/VERSIONING.md](../.github/VERSIONING.md).
- **Commits**: Conventional Commits. Full detail: [../CONTRIBUTING.md](../CONTRIBUTING.md#commit-messages).
- **Beginners**: if any of this is unfamiliar, start with [DEVOPS_FOR_BEGINNERS.md](DEVOPS_FOR_BEGINNERS.md) instead — it explains the same steps assuming no prior Git experience.

## Quick reference

```bash
# Start new work
git checkout main && git pull origin main
git checkout -b feature/US-014-short-description

# Save work
git add <files>
git commit -m "feat(scope): summary"

# Share work
git push origin feature/US-014-short-description
# → open a PR on GitHub, using the PR template

# Stay current
git checkout main && git pull origin main
git checkout feature/US-014-short-description && git merge main
```
