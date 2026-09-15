# Frequently Asked Questions

> **Purpose:** Answer common questions about the project, its scope, and how to work in this repository.
> **Audience:** All contributors and stakeholders.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [../README.md](../README.md), [../architecture/SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md)

---

### What is the Defence Consulting Intelligence Hub?

An internal platform that uses a modular set of AI agents to collect, analyse, and report on defence-sector opportunities, procurement, competitor activity, and technology trends. See [../README.md](../README.md).

### Is the application built yet?

No. This repository is currently the **framework**: documentation, architecture, governance, and starter scaffolding. See [Project status](../README.md#project-status) for what exists today.

### Why JSON storage before PostgreSQL?

The prototype phase prioritises speed of iteration and easy inspection of data over scale or concurrency. JSON files under `data/` let us validate schemas and agent output quickly. PostgreSQL is the target for production — see [../architecture/DATABASE_DESIGN.md](../architecture/DATABASE_DESIGN.md).

### Why Ollama for local development instead of OpenAI?

Cost, latency, and the ability to develop and test the agent pipeline offline/without sending data to a third party during early iteration. OpenAI/Azure OpenAI are supported as a provider swap for higher-quality output later — see [../docs/AI_DEVELOPMENT_GUIDE.md](AI_DEVELOPMENT_GUIDE.md).

### Do I need an OpenAI or Azure OpenAI key to develop locally?

No. Default configuration uses Ollama. Keys are only needed if you're testing the `openai` or `azure_openai` provider path.

### What's the difference between an Epic, Feature, User Story, and Task?

- **Epic** — a large body of work delivering a major capability (e.g. "AI Agent Platform").
- **Feature** — a deliverable slice of an epic (e.g. "Opportunity Agent MVP").
- **User Story** — a specific, testable piece of user-facing value within a feature.
- **Task** — a technical unit of work needed to complete a story (may not be user-facing on its own).

See [../epics/README.md](../epics/README.md) and [../user-stories/README.md](../user-stories/README.md).

### Where do I find what to work on?

[tasks/](../tasks/) for granular work items, or the current sprint in [sprint-planning/](../sprint-planning/). If you're using an actual Azure DevOps board, these markdown files mirror it — the board is authoritative for live status.

### How do agents differ from prompts?

An **agent** ([ai-agents/](../ai-agents/)) is a documented component with a defined responsibility, inputs/outputs, and a JSON contract — it may use one or more prompts. A **prompt** ([prompts/](../prompts/)) is the actual instruction text sent to the LLM. Agents are the "who and why," prompts are the "what exactly do we say to the model."

### Can I use a different AI model/provider than what's documented?

Discuss it first — raise it as an ADR ([adr/](../adr/)) if it's a structural change, since it affects every agent's prompt and output contract.

### How is this different from a generic web scraping tool?

This project synthesises and structures already-available, legitimately sourced information (public procurement notices, news, agency programme data) into consulting-ready intelligence — it does not perform unauthorised data collection. Data sourcing rules are documented per-agent in [ai-agents/](../ai-agents/) and governed by [../SECURITY.md](../SECURITY.md).

### Who do I contact with questions not answered here?

See [Contact](../README.md#contact) in the root README.
