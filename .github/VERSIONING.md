# Versioning

> **Purpose:** Define the semantic versioning policy for this repository.
> **Audience:** All contributors, especially anyone cutting a release.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [RELEASE_STRATEGY.md](RELEASE_STRATEGY.md), [../CONTRIBUTING.md](../CONTRIBUTING.md#commit-messages)

---

## Scheme: Semantic Versioning (SemVer)

`MAJOR.MINOR.PATCH` — e.g. `1.4.2`.

| Segment | Increment when |
|---|---|
| `MAJOR` | A breaking change — incompatible API change, breaking agent output schema change, or a breaking change to how the repository/tooling is used |
| `MINOR` | A backwards-compatible feature addition (new endpoint, new agent, new UI capability) |
| `PATCH` | A backwards-compatible bug fix |

Pre-1.0 (current phase, `0.x.y`): the project is a scaffold with no stable public contract yet — `MINOR` bumps may include changes that would be `MAJOR` once the project reaches `1.0.0`. `1.0.0` is reached when the platform has a stable, documented API contract and the core agent pipeline is functional end-to-end.

## Where version numbers live

| Location | What it versions |
|---|---|
| Git tags (`vX.Y.Z`) | The overall repository/release |
| `backend/pyproject.toml` version (once added at 1.0) / `app/main.py` FastAPI `version=` | Backend API version |
| `frontend/package.json` `version` | Frontend application version |
| Each markdown doc's `Version` header field | That document's own revision, independent of the release version |

Component versions (backend/frontend) are kept in sync with the release tag at release time; they may drift between releases during active development, which is expected.

## Conventional Commits → version bump mapping

Since we use [Conventional Commits](https://www.conventionalcommits.org/) (see [../CONTRIBUTING.md#commit-messages](../CONTRIBUTING.md#commit-messages)):

| Commit type | Typical bump |
|---|---|
| `feat` | MINOR |
| `fix` | PATCH |
| `feat!` / `fix!` / any commit with a `BREAKING CHANGE:` footer | MAJOR |
| `docs`, `chore`, `test`, `refactor`, `style`, `ci` | No version bump on their own |

This mapping is manual for now (no automated semantic-release tooling configured) — the person cutting the release reviews commits since the last tag and picks the appropriate bump per [RELEASE_STRATEGY.md](RELEASE_STRATEGY.md).
