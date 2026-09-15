# TAMBI 2026 — Defence Contract Intelligence Platform

**Accenture Australia · Defence & National Security**

> The defence contract landscape, *finally legible*.

TAMBI 2026 turns Australia's public procurement record into a living intelligence capability — a platform where Accenture leadership can see the market at a glance, interrogate it in plain English, and commission research-grade analysis on demand.

| | |
|---|---|
| **Primary source** | AusTender — Commonwealth contract notices |
| **Audience** | Accenture ANZ leadership & Defence practice |
| **Architecture** | Three pillars, one data spine |
| **Status** | Vision — pre-build |

---

## The case for building this

**The data is public. The insight is not.**

Every Commonwealth defence contract above the reporting threshold is published on AusTender. The information advantage was never about access — it is about the distance between a raw notice and a decision. Today that distance is measured in analyst-weeks.

**01 — The record is fragmented**
Contract notices, amendments, standing offers and panel arrangements live in separate views with inconsistent supplier naming. Reconstructing a single vendor's true position across the portfolio is manual, slow, and rarely repeated.

**02 — Questions outpace analysis**
Leadership questions arrive faster than they can be answered. By the time an analyst returns a deck, the question has moved on — so most questions are simply never asked.

**03 — Signals expire quietly**
A contract approaching expiry is a re-bid opportunity with a clock on it. Without systematic monitoring, those windows are noticed late or missed entirely.

---

## The vision

**One platform. Three levels of depth.**

The architecture follows how leaders actually consume intelligence — a glance, a question, and occasionally a genuine investigation. Each pillar serves one of those modes, and each draws on the same governed data spine underneath.

> **Pillar I answers what you already knew to ask.** Pillar II answers what occurred to you in the meeting. Pillar III answers what nobody had time to investigate.
>
> Most analytics products only build the first. The compounding value of TAMBI is that the questions asked in Pillar II become the saved views of Pillar I, and the patterns surfaced in Pillar III become the questions worth asking next.

---

## The three pillars

### Pillar I — The Intelligence Dashboard

*Curated, always-on, shaped by what leadership needs to see right now*

The front door. A deliberately opinionated view of the defence contract market — not every metric that could be shown, but the handful that drive decisions this quarter. Views are configuration, not code, so the dashboard evolves at the speed of leadership's attention rather than the speed of a release cycle.

**What leadership sees**
- **Market shape** — total addressable defence spend by agency, capability area and financial year
- **Supplier league tables** — who holds what, ranked and trended over time
- **Expiry pipeline** — contracts reaching end-of-term in the next 6–18 months
- **Category drilldown** — ICT, professional services, sustainment, engineering, logistics
- **Accenture position** — where we hold work, where competitors hold it, where nobody does

**Design commitments**
- **Fast** — pre-computed metrics; no model call sits in the render path
- **Configurable** — new views defined as saved configurations, promoted from real questions
- **Honest** — every figure traceable to its source notices, with coverage gaps stated plainly
- **Presentable** — built to be projected in a leadership meeting without apology

> Deliberate constraint: the dashboard does not attempt to answer everything. Its job is to be instantly readable and always current. Depth belongs to Pillars II and III.

---

### Pillar II — The Conversational Layer

*Natural language interrogation of the full dataset — powered by Claude*

The dashboard shows the questions we anticipated. This pillar handles every question we did not. A leader asks in plain English; the system translates that into queries against the contract warehouse, runs them, and returns a narrated answer with the underlying figures and a chart — in seconds, not days.

**How it works**
- **Claude with tool access**, not document retrieval — the data is structured, so the model queries it directly rather than guessing from embedded text
- **A governed tool surface** — schema inspection, read-only query, supplier lookup, chart rendering
- **Reasoning enabled** — real questions require multi-step analysis, not single lookups
- **Streamed responses** so the answer builds visibly as it is composed

**What it unlocks**
- **Follow-up thinking** — conversation, not one-shot search; each answer invites the next question
- **Zero training burden** — no query language, no filter syntax, no onboarding deck
- **A demand signal** — the question log becomes the roadmap for what Pillar I should show next
- **Self-service depth** — analyst time is freed for work that actually needs judgement

**Illustrative interaction:**
> "Which suppliers have grown their sustainment work fastest over the last three years, and where are we absent?"

The system inspects the schema, composes and runs the necessary queries, resolves supplier entities to their true parent organisations, computes the growth trend, and returns a narrated answer with a ranked table and a trend chart — plus the contract notices behind every number, so the finding can be checked.

> Non-negotiable guardrail: the query tool runs against a read-only replica, with enforced row caps and statement timeouts. The conversational layer can never reach a writable connection.

---

### Pillar III — Deep Research & Autonomous Briefings

*Commissioned investigation, and a standing intelligence rhythm*

The most ambitious pillar. A leader poses a genuine research brief — not a question with a lookup answer, but the kind of request that would normally consume an analyst for a fortnight. An AI research agent plans the work, draws on AusTender alongside other relevant public sources, performs its own analysis, and produces a finished report.

**On demand**
- **Open-ended briefs** — "Assess the competitive landscape for defence ICT sustainment and where we are structurally disadvantaged"
- **Multi-source** — contract data combined with public defence strategy, industry policy and open reporting
- **Genuine analysis** — the agent runs its own computation and builds its own exhibits, rather than summarising
- **Real deliverables** — formatted documents and decks, not a wall of chat text

**On a rhythm**
- **A standing fortnightly briefing** — generated automatically on schedule
- **What changed, and why it matters** — new awards, notable movements, expiring windows
- **Reviewed before it reaches anyone** — every briefing passes a named human owner
- **Distributed to decision makers** once released, in a format built to be read

**The review gate is part of the design, not a limitation of it**

An agent that emails unreviewed competitive analysis to senior leadership every fortnight is a reputational risk that compounds quietly — errors reach the most senior audience with the least context to catch them.

So the pipeline is deliberate: **the agent generates → the briefing enters a review queue → a named owner approves → it sends.** The automation earns trust before it earns autonomy. The gate can loosen once the output has a track record — but it is where we start.

---

## Underneath the pillars

**One data spine carries all three.**

The pillars are three faces of a single foundation. None of them work if the spine is weak — which is why the unglamorous middle step below is the one that determines whether this succeeds.

| Step | Name | Description |
|------|------|-------------|
| 01 | **Ingest** | Scheduled collection of Commonwealth contract notices, amendments and standing offers from AusTender |
| 02 | **Resolve** | The hard part. Supplier entity resolution — collapsing naming variants and subsidiaries into true parent organisations |
| 03 | **Model** | A governed warehouse with a documented schema, a business glossary, and pre-computed metric tables |
| 04 | **Serve** | One read-only interface consumed by all three pillars — dashboard, conversation and research agent alike |

**Step 02 is where this project is won or lost.** "Boeing Defence Australia", "BOEING DEFENCE AUSTRALIA LTD" and a subsidiary trading name are one competitor to a leader and three rows to a database. Every supplier league table, every market share figure and every competitive finding in all three pillars inherits the quality of this step.

---

## Roadmap

**Build the spine first. Earn the automation last.**

The order is deliberate — each phase produces something usable, and each de-risks the next. Autonomous distribution comes last, once there is enough output to judge whether it deserves trust.

| Phase | Focus | Description |
|-------|-------|-------------|
| **01** Foundation | The data spine | Ingestion, supplier entity resolution, warehouse and schema. No user-facing feature ships in this phase — and everything that follows depends entirely on it being done properly. |
| **02** Pillar I | The dashboard | Core views in front of a real leader as early as possible. Their reaction reshapes the roadmap more usefully than any amount of internal planning. |
| **03** Pillar II | Conversational analytics | Natural language querying to a small pilot group. Every question asked is logged — that log becomes the specification for the next round of dashboard views. |
| **04** Pillar III | Deep research, on demand | The research agent, commissioned manually. Output quality is assessed on real briefs before any automated distribution is switched on. |
| **05** Pillar III | The standing briefing | Scheduled fortnightly generation, review queue, and distribution to decision makers — enabled only once Phase 04 has demonstrated the quality bar is consistently met. |

---

## Principles

**What this platform will and will not do.**

**Commitments**
- **Public sources only** — built on the published procurement record, with provenance retained end to end
- **Traceable by default** — every figure can be walked back to the notices that produced it
- **Honest about gaps** — coverage limits and data quality caveats stated, never quietly smoothed over
- **Human in the loop** where output leaves the building

**Explicit non-goals**
- **Not a forecasting oracle** — it describes the market and surfaces signals; it does not pretend to predict awards
- **Not a replacement for judgement** — it removes the research burden that precedes a decision, not the decision
- **Not an unattended broadcaster** — nothing reaches leadership without a named owner having released it
- **Not a dashboard graveyard** — views must earn their place or be retired
