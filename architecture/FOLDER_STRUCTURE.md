# Folder Structure

> **Purpose:** Explain the rationale behind the repository's top-level and key subfolder layout.
> **Audience:** All contributors, especially during onboarding.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../README.md](../README.md), [../docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md), [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md), [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md)

---

## Top-level layout

```
/
├── docs/              Cross-cutting documentation (setup, standards, guides)
├── architecture/       This folder — system design documents
├── adr/                Architecture Decision Records
├── epics/              Azure DevOps-style epics
├── user-stories/       Azure DevOps-style user stories
├── tasks/              Azure DevOps-style tasks
├── sprint-planning/     Sprint plans (Sprint 0–4)
├── backend/            FastAPI application
├── frontend/           React/TypeScript/MUI application
├── ai-agents/          Per-agent specification documents
├── prompts/            Production prompt library
├── data/               Sample/placeholder JSON entity data
├── reports/             Generated report output (gitignored)
├── scripts/             Developer setup/utility scripts
├── tests/               Test suites and testing documentation
├── docker/              Docker Compose and container config
├── .github/             Issue/PR templates, CI workflows, repo policy docs
├── .continue/           Continue.dev local AI assistant config
├── .vscode/             Shared VS Code workspace settings
└── README.md
```

## Rationale

**Documentation and work management are top-level, not buried in `docs/`.** `epics/`, `user-stories/`, `tasks/`, `sprint-planning/`, `adr/`, and `ai-agents/` are each promoted to the root rather than nested under `docs/`, because they represent distinct artefact types with their own lifecycle and audience (project management vs. engineering reference vs. architecture record) — flattening them makes each easy to find and link to directly, matching how they'd appear as separate work item types in Azure DevOps.

**Code is split by application, not by layer, at the top level.** `backend/` and `frontend/` are separate top-level folders (rather than a single `src/` with subfolders) because they are separately deployable, separately versioned (different dependency ecosystems — pip vs. npm), and often worked on by different people. Within each, layering follows the conventions in [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) and [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md).

**AI concerns are split into three folders by concern, not bundled into `backend/`:**
- `ai-agents/` — *specification* (what an agent does, its contract) — documentation, read by anyone.
- `prompts/` — *instruction text* sent to the LLM — reviewable independently of code.
- `backend/app/agents/` — *implementation* — code that uses the above two.

This separation lets a non-engineer (e.g. an analyst refining a prompt) contribute without touching Python, and lets prompt changes be reviewed as their own diff.

**`data/` holds sample/placeholder data only** — it is documentation-by-example for entity shapes, not a runtime data store. Runtime JSON storage (prototype phase) lives under `backend/app/db/json_store/` (gitignored contents) once implemented, keeping committed sample data separate from working data.

**`reports/` is an output folder, not a source folder** — its contents are generated, not authored, and are gitignored aside from a `README.md`/`.gitkeep`.

**`docker/` centralises all container orchestration**, even though `backend/` and `frontend/` each have their own `Dockerfile` — this keeps `docker-compose.yml` and cross-cutting container config (networks, volumes) in one discoverable place rather than scattered.

**Dotfolders (`.github/`, `.continue/`, `.vscode/`) are versioned deliberately.** Unlike typical personal-preference dotfolders, these carry shared team configuration (CI, local AI assistant setup, editor settings) and are treated as first-class parts of the framework — see [.vscode/README](../.vscode/) settings and [.continue/config.json](../.continue/config.json).

## Where does X go?

| I have a... | It goes in... |
|---|---|
| New API endpoint | `backend/app/api/routes/` |
| New business rule | `backend/app/services/` |
| New AI agent implementation | `backend/app/agents/` |
| New agent specification | `ai-agents/` |
| New prompt | `prompts/` |
| New UI page | `frontend/src/pages/` |
| New reusable UI component | `frontend/src/components/` |
| New architecture decision | `adr/` |
| New planned feature (project management) | `epics/` → `user-stories/` → `tasks/` |
| New sample data shape | `data/` |
