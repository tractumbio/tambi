# Security Policy

> **Purpose:** Describe supported versions, data-handling rules, and how to report security issues.
> **Audience:** Contributors, security reviewers, and anyone reporting a vulnerability.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [architecture/SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md)

---

## Data sensitivity

This platform processes defence-sector procurement, competitor, and agency intelligence. Some of that data — even in later production use — may be commercially sensitive or subject to client confidentiality and government contracting rules (e.g. export control, OFFICIAL/OFFICIAL-SENSITIVE handling in a UK MOD context, or equivalent classifications elsewhere).

Rules for this repository:

- **Never commit real client, contract, or personal data.** Use the placeholder schemas in [data/](data/).
- **Never commit secrets** — API keys, database credentials, OpenAI/Azure OpenAI keys, tokens. Use `.env` files (gitignored) based on [.env.example](.env.example).
- Treat all sample data in `data/` as fictional, even where it resembles real agencies or organisations.
- Production deployment must use a secrets manager (Azure Key Vault or equivalent) — see [architecture/FUTURE_CLOUD_ARCHITECTURE.md](architecture/FUTURE_CLOUD_ARCHITECTURE.md).

## Supported versions

| Version | Supported |
|---|---|
| `main` (current) | ✅ |
| Tagged releases < latest major | ⚠️ Security fixes only |

See [.github/RELEASE_STRATEGY.md](.github/RELEASE_STRATEGY.md) for the versioning policy.

## Reporting a vulnerability

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Email the maintainer listed in [README.md](README.md) with:
   - A description of the issue and its potential impact.
   - Steps to reproduce (if applicable).
   - Any suggested remediation.
3. You will receive an acknowledgement within 2 business days.
4. Once resolved, the fix will be released and — where appropriate — the reporter credited.

## Security practices in this repository

- **Dependency scanning**: CI runs dependency and lint checks on every PR (see [.github/workflows/ci.yml](.github/workflows/ci.yml)).
- **Least privilege**: service accounts and API keys should be scoped to the minimum required.
- **Input validation**: all API boundaries validate input via Pydantic schemas (backend) and TypeScript types (frontend); see [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md).
- **AI-specific risks**: prompt injection, data leakage via LLM context, and unvalidated agent output are treated as security concerns, not just quality concerns — see [docs/AI_DEVELOPMENT_GUIDE.md](docs/AI_DEVELOPMENT_GUIDE.md#security-considerations) and each agent's "Constraints" section in [ai-agents/](ai-agents/).
- **Authentication/authorisation**: out of scope for the current prototype phase; required before any production or externally-accessible deployment (tracked as a future epic).

## Out of scope (for now)

This is a documentation/framework-only repository at this stage — no deployed environment exists yet. Security review of the running application will be required before any non-local deployment.
