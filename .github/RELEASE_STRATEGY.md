# Release Strategy

> **Purpose:** Define how and when releases are cut and tagged.
> **Audience:** All contributors, especially those merging to `main`.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [BRANCH_STRATEGY.md](BRANCH_STRATEGY.md), [VERSIONING.md](VERSIONING.md), [../SECURITY.md](../SECURITY.md)

---

## Current phase: no formal releases yet

This repository is currently a framework/scaffold with no deployed application — see [../README.md#project-status](../README.md#project-status). This document defines the process to use once the backend/frontend have real functionality to release.

## Release cadence (once active)

- **Sprint-end releases**: tag `main` at the end of each sprint (see [../sprint-planning/](../sprint-planning/)) once its exit criteria are met.
- **On-demand releases**: for urgent fixes, a release may be cut outside the sprint cadence.

## Process

1. Confirm `main` is green (CI passing) and the intended scope is merged.
2. Update version per [VERSIONING.md](VERSIONING.md).
3. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"` and `git push origin vX.Y.Z`.
4. Draft release notes summarising notable changes (grouped by Conventional Commit type — feat/fix/etc.), linking closed user stories.
5. (Once cloud deployment exists) trigger the deployment pipeline for the tagged commit — see [../architecture/FUTURE_CLOUD_ARCHITECTURE.md](../architecture/FUTURE_CLOUD_ARCHITECTURE.md).

## Supported versions

See [../SECURITY.md#supported-versions](../SECURITY.md#supported-versions) — only `main`/latest tag receives active support during the prototype phase.

## Rollback

Until a real deployment pipeline exists, "rollback" means reverting the relevant commit(s) on `main` via a new PR (never force-pushing or rewriting `main` history) and re-tagging if a release had already been cut from the bad state.
