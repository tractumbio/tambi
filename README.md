<!-- This comment was added by Claude via CLI -->

# Defence Consulting Intelligence Hub

> **Purpose:** Entry point for the repository — explains what this project is, how it is organised, and where to go next.
> **Audience:** All contributors (engineers, analysts, project leads), new joiners, and stakeholders.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [GETTING_STARTED.md](docs/GETTING_STARTED.md), [ARCHITECTURE.md](docs/ARCHITECTURE.md), [CONTRIBUTING.md](CONTRIBUTING.md)

---
I edited this sentence
## What is this?

The **Defence Consulting Intelligence Hub** is an internal platform that aggregates, analyses, and reports on defence-sector opportunities, procurement activity, competitor positioning, and technology trends for a consulting practice. It combines a modular AI agent pipeline with a React/FastAPI application to produce structured intelligence — weekly reports, opportunity trackers, and executive summaries — for consultants and leadership.

This repository is currently a **framework-first scaffold**. It establishes documentation, architecture, governance, coding standards, and Azure DevOps-style work management so that multiple contributors can begin building the actual application in parallel, with a shared understanding of design and process. **No business functionality has been implemented yet.**

## Why it exists

Defence consulting teams need to track a high volume of fast-moving, multi-source information: procurement notices, competitor wins, agency programmes, and emerging technology signals. Doing this manually does not scale. This platform is designed to automate the collection and synthesis of that intelligence using a modular set of AI agents, while keeping a human in the loop for review and decision-making.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Material UI |
| Backend | Python, FastAPI |
| AI | Ollama (local dev), OpenAI / Azure OpenAI (future), modular agent architecture |
| Database | JSON (prototype), PostgreSQL (production) |
| Visualisation | Plotly, Recharts |
| Deployment | Docker, Docker Compose |
| IDE | VS Code (+ Continue.dev for local AI assistance) |
| Version Control | Git |

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) and the [architecture/](architecture/) folder for full details.

## Repository structure

```
/
├── docs/              Project-wide documentation and guides
├── architecture/       System, agent, and deployment architecture
├── adr/                Architecture Decision Records
├── epics/              Azure DevOps-style epics
├── user-stories/       Azure DevOps-style user stories
├── tasks/              Azure DevOps-style tasks
├── sprint-planning/     Sprint 0–4 plans
├── backend/            FastAPI application
├── frontend/           React + TypeScript + MUI application
├── ai-agents/          AI agent specifications
├── prompts/            Production prompt library
├── data/               Sample/placeholder JSON data
├── reports/            Generated report output (gitignored contents)
├── scripts/            Setup and developer scripts
├── tests/              Test suites and testing documentation
├── docker/             Docker Compose and container configuration
├── .github/            Issue/PR templates, workflows, repo policy docs
├── .continue/          Continue.dev local AI assistant configuration
├── .vscode/            Shared VS Code workspace settings
└── README.md           This file
```

## Getting started

**New to software development entirely?** Start with [docs/DEVOPS_FOR_BEGINNERS.md](docs/DEVOPS_FOR_BEGINNERS.md) — it assumes no prior experience with Git, GitHub, Docker, or any of the tools used here.

**Experienced developer, new to this repo?** Start with [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md), then pick your OS-specific setup guide:

- [docs/SETUP_WINDOWS.md](docs/SETUP_WINDOWS.md)
- [docs/SETUP_MAC.md](docs/SETUP_MAC.md)
- [docs/SETUP_LINUX.md](docs/SETUP_LINUX.md)

## Key documents

| Document | Description |
|---|---|
| [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) | Day-to-day development workflow |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture overview |
| [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) | Language and process standards |
| [docs/AI_DEVELOPMENT_GUIDE.md](docs/AI_DEVELOPMENT_GUIDE.md) | Working with the AI agent layer |
| [SECURITY.md](SECURITY.md) | Security policy and responsible disclosure |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community standards |

## Project status

| Area | Status |
|---|---|
| Repository framework, docs, governance | ✅ Complete |
| Backend application logic | 🔲 Not started |
| Frontend application logic | 🔲 Not started |
| AI agent implementation | 🔲 Not started |
| Production database (PostgreSQL) | 🔲 Not started |

## License

See [LICENSE](LICENSE). This repository and its contents are confidential and proprietary.

## Contact

Maintained by the Defence Consulting Intelligence Hub core team. For questions, open a [GitHub Discussion or Issue](.github/ISSUE_TEMPLATE/), or see [docs/FAQ.md](docs/FAQ.md).
