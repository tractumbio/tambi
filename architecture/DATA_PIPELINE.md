# Data Pipeline

> **Purpose:** Describe how data moves through the system, from raw source ingestion to a finished report.
> **Audience:** Backend and AI engineers.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md), [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md), [DATABASE_DESIGN.md](DATABASE_DESIGN.md), [../data/README.md](../data/README.md)

---

## Pipeline stages

```
1. Ingestion   →  2. Normalisation  →  3. Agent Analysis  →  4. Synthesis  →  5. Storage  →  6. Presentation
```

### 1. Ingestion

Raw source material (procurement notices, news articles, agency programme updates) enters the system. In the current prototype phase, ingestion is manual/sample-data-driven — see [../data/](../data/) for the placeholder shapes (`news-article.json`, `contract.json`, etc.). Automated ingestion connectors are a future epic (see [../epics/README.md](../epics/README.md)).

### 2. Normalisation

Raw source data is mapped into the platform's canonical entity shapes (`Opportunity`, `Contract`, `Agency`, `Programme`, `Organisation`, `NewsArticle`) — see [DATABASE_DESIGN.md](DATABASE_DESIGN.md) for field definitions. Normalisation is deterministic code, not an LLM step — LLMs are reserved for analysis/synthesis, not for exact field mapping.

### 3. Agent analysis

Normalised entities are passed to the relevant domain agent(s):

| Input entity | Primary agent |
|---|---|
| Opportunity | Opportunity Agent |
| Contract / procurement notice | Procurement Agent |
| Agency / programme | Defence Intelligence Agent |
| Competitor activity, incl. Accenture | Competitor Intelligence Agent, Accenture Intelligence Agent |
| News / technology signal | Technology Trends Agent, Research Agent |

Each agent returns schema-validated structured output — see [../ai-agents/](../ai-agents/) for each agent's exact contract.

### 4. Synthesis

The **Orchestrator Agent** combines domain agent outputs; the **Executive Summary Agent** produces the human-readable narrative layer on top. See [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md).

### 5. Storage

Combined results (weekly report, updated opportunity/contract records) are persisted via the data access layer — JSON files in the prototype, PostgreSQL in production. See [DATABASE_DESIGN.md](DATABASE_DESIGN.md).

### 6. Presentation

The frontend fetches stored reports/entities via the REST API and renders them using tables, Recharts, and Plotly visualisations. See [../architecture/FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md).

## Data lineage & traceability

Every derived record (an agent's output) retains a reference to its source input(s) — e.g. an `Opportunity` produced from a `NewsArticle` keeps the article's ID/URL. This is required so a consultant reading a report can trace a claim back to its source; treat "no traceable source" as equivalent to "unverified" in any agent output (see each agent's "Constraints" section in [../ai-agents/](../ai-agents/)).

## Data quality

- Schema validation at every stage boundary (ingestion → normalisation → agent → storage) — a record that fails validation does not silently proceed to the next stage.
- Confidence scoring: agents that infer/classify (rather than extract verbatim) attach a `confidence_score` field, surfaced in the UI so consultants can weight agent output appropriately.

## Future automation

Scheduled ingestion (polling public procurement portals, news feeds) and a message-queue-based pipeline (rather than synchronous request-time agent calls) are targeted for the cloud phase — see [FUTURE_CLOUD_ARCHITECTURE.md](FUTURE_CLOUD_ARCHITECTURE.md).
