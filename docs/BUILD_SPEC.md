# BUILD SPEC — Defence Contract Intelligence Platform

**Audience for this document:** Claude Code, operating in this repo.
**Audience for the product:** Accenture Managing Directors (Defence portfolio).

Read this whole file before writing code. Work in the phase order given. Do not skip
Phase 0. Stop at the end of each phase and report what was built plus anything that
contradicted this spec.

---

## 1. Purpose

A web application that ingests Australian Government Defence procurement data from
AusTender, stores it in Postgres, and presents it to Accenture MDs as:

1. A **dashboard** — competitor performance, market share, opportunity pipeline.
2. An **LLM query layer** — open-ended natural-language questions answered via
   generated SQL against the same tables.

The core commercial questions the product must answer:
- Is Accenture gaining or losing share of Defence spend, and against whom?
- Which Defence themes have the most contract value, and where is Accenture absent?
- Which competitor-held contracts expire soon (i.e. what is recompetable)?

---

## 2. Locked technical decisions

Do not substitute these without asking.

| Layer | Choice |
|---|---|
| Database | PostgreSQL (with `pgvector` extension, Phase 9) |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic |
| Dependency mgmt | `uv` (fall back to `venv` + `pip` if `uv` unavailable) |
| Frontend | React 18 + TypeScript, built with Vite |
| Data fetching (FE) | TanStack Query |
| Charts | Recharts |
| Styling | Tailwind CSS |
| HTTP client (BE) | `httpx` |
| LLM | Anthropic API (Claude), via `anthropic` Python SDK |
| Target deploy | Azure (App Service + Azure Database for PostgreSQL + Static Web Apps) |

**Cloud-portability rule, applies to every phase:** no hardcoded URLs, hostnames,
ports, credentials or connection strings anywhere in the codebase. Everything comes
from environment variables with local defaults. This is non-negotiable — it is the
single thing that determines whether the Azure migration is a day or a fortnight.

---

## 3. Target repo structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory, CORS, router mounting
│   │   ├── config.py               # pydantic-settings, all env vars
│   │   ├── db.py                   # engine, session factory
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── schemas/                # Pydantic request/response models
│   │   ├── api/
│   │   │   ├── metrics.py          # dashboard aggregate endpoints
│   │   │   ├── contracts.py        # list/filter/detail endpoints
│   │   │   └── ask.py              # LLM text-to-SQL endpoint
│   │   ├── ingest/
│   │   │   ├── client.py           # AusTender API client
│   │   │   ├── backfill.py         # historical load
│   │   │   ├── incremental.py      # scheduled delta load
│   │   │   └── transform.py        # OCDS JSON -> relational rows
│   │   ├── processing/
│   │   │   ├── themes.py           # Defence theme classification
│   │   │   └── competitors.py      # supplier -> competitor group mapping
│   │   ├── intelligence/
│   │   │   ├── sources.yaml        # news source registry
│   │   │   ├── documents.yaml      # document corpus targets
│   │   │   ├── document_licences.md # per-source licence determinations
│   │   │   ├── feeds.py            # RSS/Atom ingestion
│   │   │   ├── extract.py          # entity + event extraction
│   │   │   ├── dedupe.py           # cross-outlet story clustering
│   │   │   ├── linkage.py          # news item -> AusTender contract matching
│   │   │   ├── documents.py        # document fetch, extract, version, diff
│   │   │   ├── chunking.py         # structure-aware chunking
│   │   │   ├── embeddings.py       # embedding generation + pgvector writes
│   │   │   └── weekly_report.py    # report compilation
│   │   └── llm/
│   │       ├── sql_agent.py        # NL -> SQL generation
│   │       ├── guardrails.py       # SQL validation
│   │       └── schema_context.md   # curated schema description for the prompt
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                    # typed API client + TanStack Query hooks
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   ├── layout/
│   │   │   └── ask/                # LLM query interface
│   │   ├── pages/
│   │   └── types/                  # TS types mirroring backend Pydantic schemas
│   ├── index.html
│   ├── tailwind.config.js
│   └── package.json
├── data/
│   └── raw/                        # raw JSON archive (gitignored)
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. PHASE 0 — Verify before you build

Do this first and report findings. Do not write the client until this is done.

1. Fetch and read the official AusTender OCDS API documentation:
   `https://github.com/austender/austender-ocds-api`
2. Establish and record in `backend/app/ingest/README.md`:
   - Base URL and exact endpoint paths
   - Authentication requirement (if any) — expected: none
   - Query parameters for date-range filtering and for fetching by contract notice ID
   - Pagination mechanism (cursor, offset, or page token) and page size limits
   - Rate limits, documented or observed
   - Whether responses are OCDS **release packages** or **record packages**
3. Pull one small real response and save it to `data/raw/sample_response.json`.
4. Write a short field inventory: for the sample, list every JSON path present, its
   type, and its fill rate. Do not assume the OCDS spec's optional fields are
   populated — AusTender populates a subset.

**Build the schema in Phase 2 against the real sample, not against the OCDS spec
in the abstract.** If the sample contradicts anything in Section 5 below, flag it
and propose the corrected schema rather than silently adapting.

---

## 5. PHASE 1 — AusTender API client

`backend/app/ingest/client.py`

Requirements:
- Async `httpx` client, injectable base URL from config.
- Method for date-window queries: `fetch_releases(date_from, date_to, cursor=None)`.
- Method for single notice by ID: `fetch_by_cn_id(cn_id)`.
- **Pagination handled internally** via an async generator that yields releases so
  callers never deal with page tokens.
- Retry with exponential backoff on 429 and 5xx. Respect `Retry-After` if present.
- Configurable politeness delay between requests (default 250ms). This is a
  government API; do not hammer it.
- Structured logging of every request: URL, params, status, record count, duration.
- **Persist every raw response to `data/raw/` before any parsing**, named
  `{date_from}_{date_to}_{page}.json`. This archive is the audit trail — if
  transform logic is later found to be wrong, reprocessing must not require
  re-hitting the API.

Storage note for production: `data/raw/` is a local stand-in for Azure Blob Storage.
Write the persistence layer behind a small interface (`RawStore.put(key, bytes)`)
with a local-filesystem implementation now, so a Blob implementation can be dropped
in later without touching ingestion logic.

---

## 6. PHASE 2 — Database schema

OCDS is deeply nested; the dashboard needs flat, indexed, aggregatable tables.
Normalise on load. Key structural facts driving this design:

- Each contracting process has a stable `ocid`.
- Each `ocid` can have **multiple releases** over time (original + amendments).
  AusTender does not edit releases in place.
- Therefore: `ocid` is **not** a primary key on a releases table, but **is** the
  natural key for the current-state contract view.

Create via Alembic migrations. Suggested tables:

### `raw_releases`
Append-only landing table for parsed-but-unflattened releases.
| column | type | notes |
|---|---|---|
| `id` | bigserial PK | |
| `ocid` | text, indexed | |
| `release_id` | text, unique | OCDS release `id` |
| `release_date` | timestamptz, indexed | OCDS release `date` |
| `tags` | text[] | OCDS `tag` array |
| `payload` | jsonb | full release JSON |
| `ingested_at` | timestamptz default now() | |
| `source_file` | text | pointer into raw archive |

Keep this. It makes every downstream table rebuildable with a single SQL pass and
costs almost nothing at this data volume.

### `organisations`
Deduplicated agencies and suppliers, from OCDS `parties`.
| column | type | notes |
|---|---|---|
| `id` | serial PK | |
| `abn` | text, unique nullable, indexed | primary dedup key where present |
| `name` | text | |
| `name_normalised` | text, indexed | lowercased, punctuation/suffix-stripped |
| `roles` | text[] | e.g. buyer, supplier |
| `competitor_group_id` | int FK nullable | set by Phase 3 |

Dedup strategy: ABN first, `name_normalised` second. Supplier names in AusTender are
inconsistently entered — expect the same entity under several spellings.

### `contracts`
Current-state, one row per `ocid` — this is what the dashboard queries.
| column | type | notes |
|---|---|---|
| `ocid` | text PK | |
| `cn_id` | text, indexed | AusTender contract notice ID |
| `title` | text | |
| `description` | text | |
| `buyer_org_id` | int FK -> organisations | |
| `supplier_org_id` | int FK -> organisations, indexed | |
| `value_amount` | numeric(18,2), indexed | |
| `value_currency` | text | |
| `date_published` | timestamptz, indexed | |
| `date_signed` | timestamptz | |
| `period_start` | date, indexed | |
| `period_end` | date, indexed | **critical for the expiry/recompete view** |
| `procurement_method` | text, indexed | |
| `unspsc_code` | text, indexed | |
| `unspsc_title` | text | |
| `is_defence` | boolean, indexed | derived, see Phase 3 |
| `amendment_count` | int default 0 | |
| `first_seen_at` | timestamptz | |
| `last_updated_at` | timestamptz | |
| `latest_release_id` | text | provenance |

### `contract_themes`
Many-to-many — a contract can hit multiple themes.
| column | type |
|---|---|
| `ocid` | text FK, indexed |
| `theme_id` | int FK |
| `confidence` | numeric(4,3) |
| `method` | text — `keyword` \| `unspsc` \| `llm` \| `manual` |

### `themes`
Seed with the five Defence themes: **nuclear submarines**, **workforce**,
**defensive cyber**, **decision advantage**, **digital engineering**. Include
`slug`, `label`, `description`, `display_order`.

### `competitor_groups`
Rolls messy supplier entities into MD-meaningful competitors.
`id`, `slug`, `label`, `category` (`accenture` | `big4` | `consulting` |
`sys_integrator` | `defence_prime` | `sme` | `other`), `display_order`.

### `ingest_state`
Single-row-per-job watermark table so restarts don't reprocess everything.
`job_name` PK, `last_release_date`, `last_run_at`, `last_run_status`,
`records_processed`, `error_message`.

### Indexing
Add composite indexes for the actual dashboard query patterns, not just single
columns:
- `(is_defence, date_published DESC)`
- `(is_defence, period_end)` — drives the expiry view
- `(supplier_org_id, date_published DESC)`
- `(is_defence, value_amount DESC)`

Missing indexes on these will not error — they will just make the dashboard slow as
the table grows. Add them now.

---

## 7. PHASE 3 — Processing and enrichment

### 7.1 Defence scoping (`is_defence`)
Do not rely on a single signal. Combine:
1. Buyer organisation matching Defence portfolio entities (Department of Defence,
   ASD, DSTG, ASC/ANI, CASG and successors).
2. UNSPSC category codes in defence-relevant ranges.
3. Keyword signals in title/description.

Write this as an explicit, testable, **auditable** rule set in
`processing/themes.py` — not a black box. An MD will eventually ask why a contract
is or isn't in scope, and the answer must be inspectable. Log which rule fired.

### 7.2 Theme classification
Two-tier, deliberately:
- **Tier 1 — deterministic.** Keyword and UNSPSC rules per theme, defined in a YAML
  file at `backend/app/processing/theme_rules.yaml`. Cheap, fast, reproducible,
  re-runnable over the whole corpus for free.
- **Tier 2 — LLM fallback.** Only for contracts Tier 1 leaves unclassified and whose
  value exceeds a configurable threshold. Batch these. Record `method='llm'` and the
  confidence so LLM-derived classifications are always distinguishable from rules.

Rationale: the corpus is large and mostly repetitive. Classifying everything by LLM
is wasteful and non-reproducible; classifying nothing by LLM leaves a long tail
uncovered. Threshold the spend.

### 7.3 Competitor mapping
A YAML mapping file from supplier name patterns / ABNs to `competitor_groups`.
Must cover at minimum: Accenture, Deloitte, PwC, KPMG, EY, IBM, Leidos, Lockheed
Martin, BAE Systems, Thales, Boeing Defence, Babcock, KBR, Jacobs, Nova Systems,
DXC. Everything unmatched falls to `other` — and the pipeline must emit a report of
the highest-value unmatched suppliers after each run so the mapping can be improved.

### 7.4 Idempotency requirement
Every processing step must be safely re-runnable over the full corpus. Classification
rules will change. If a re-run produces duplicates or requires a manual truncate, the
design is wrong.

---

## 8. PHASE 4 — Ingestion pipelines

### 8.1 Backfill (`ingest/backfill.py`)
- CLI: `python -m app.ingest.backfill --from 2019-01-01 --to 2026-09-01`
- Chunk the window (monthly) and process chunk by chunk.
- Checkpoint to `ingest_state` after each chunk. A crash mid-backfill must resume,
  not restart.
- Log progress: chunk, records fetched, records loaded, elapsed.

### 8.2 Incremental (`ingest/incremental.py`)
- CLI: `python -m app.ingest.incremental`
- Reads `last_release_date` from `ingest_state`, requests everything published since,
  with a configurable overlap window (default 3 days) to absorb late-arriving or
  back-dated releases.
- **Upsert on `ocid`, never plain insert.** Amendments arrive as new releases under
  an existing `ocid`; they must update the `contracts` row, increment
  `amendment_count`, and append to `raw_releases` — not create a duplicate contract.
- Advance the watermark only on success.

### 8.3 Cadence
Daily, weekday mornings, is sufficient. Two reasons, both structural:
the AusTender feed moves on business days, and agencies have up to 42 days from
contract signature to report under the Commonwealth Procurement Rules. Polling more
often buys nothing. Implement as a cron-style scheduled job; on Azure this becomes a
scheduled App Service job or Container App job. Do not build a heavy orchestrator
now — a single idempotent CLI entrypoint is the right unit.

---

## 9. PHASE 5 — Backend API

All endpoints return typed Pydantic responses. Generate matching TS types for the
frontend (`frontend/src/types/`) and keep them in sync.

### Dashboard endpoints (`api/metrics.py`)
| Endpoint | Returns |
|---|---|
| `GET /api/metrics/summary` | Headline KPIs: total Defence contract value (period), contract count, Accenture value + share of total, period-on-period deltas |
| `GET /api/metrics/share-over-time` | Time series of Defence contract value by `competitor_group`, bucketed monthly/quarterly |
| `GET /api/metrics/by-theme` | Value + count per theme, with Accenture vs field split per theme |
| `GET /api/metrics/competitor-momentum` | Rolling 12-month value and count per competitor group, with trend direction |
| `GET /api/metrics/expiring` | Contracts with `period_end` in a forward window, filterable by theme and competitor — the recompete pipeline |
| `GET /api/metrics/by-agency` | Value + count per buyer organisation |

### Data endpoints (`api/contracts.py`)
| Endpoint | Returns |
|---|---|
| `GET /api/contracts` | Paginated, filterable list (theme, competitor, agency, value range, date range, expiry window), sortable |
| `GET /api/contracts/{ocid}` | Full detail incl. amendment history from `raw_releases` |
| `GET /api/filters` | Filter option sets for populating dashboard controls |

All aggregate endpoints accept a common filter param set. Implement the filters once
as a shared dependency, not repeated per endpoint.

### Non-negotiables
- Env-driven CORS allowlist. Local default permits the Vite dev origin.
- `/health` endpoint returning DB connectivity status.
- Structured JSON logging, correlation ID per request.
- No secrets in code. `config.py` uses `pydantic-settings`; `.env.example` documents
  every variable with a comment.

---

## 10. PHASE 6 — LLM query layer

`api/ask.py`, `llm/sql_agent.py`, `llm/guardrails.py`

### Flow
1. MD submits a natural-language question to `POST /api/ask`.
2. Backend sends the question plus **curated** schema context
   (`llm/schema_context.md`) to Claude, requesting a single SQL `SELECT`.
3. Generated SQL goes through `guardrails.validate()` before touching the database.
4. Execute on a **read-only connection**.
5. Return a structured response: the rows, the executed SQL, a suggested
   visualisation type, and an LLM-written plain-language summary of the result.

### Security — implement all of these, they are not alternatives
- **Separate read-only Postgres role.** Grant `SELECT` only, on only the tables the
  agent is allowed to see. Configure as a distinct connection string
  (`DATABASE_URL_READONLY`). Prompting the model to "only read" is not a control;
  database permissions are the control.
- **SQL AST validation** using `sqlglot`. Reject: anything that is not a single
  `SELECT`; multiple statements; DDL/DML keywords; references to tables outside an
  explicit allowlist; `pg_*` / `information_schema` access.
- **Hard `LIMIT` injection** — cap returned rows (default 1000) regardless of what
  the model generates.
- **Statement timeout** on the read-only connection (default 10s).
- **Log every question, generated SQL, validation outcome and row count** to an
  `llm_query_log` table. This is both an audit trail and the dataset for improving
  the prompt.

### Accuracy and honesty requirements
- `schema_context.md` must be hand-written and curated: table and column
  descriptions, business meaning of `competitor_group` and `theme`, the fact that
  `contracts` is current-state keyed by `ocid`, units and currency, and **5–10
  worked example question→SQL pairs** covering the common patterns. Curated context
  beats a raw schema dump by a wide margin.
- **Always return the underlying rows alongside any prose summary.** The table or
  chart is the artifact; the summary is a convenience. An MD will quote a number in
  a meeting — it must be traceable to a query and a row set.
- **Surface ambiguity rather than guessing.** If the question is underspecified
  ("how are we doing"), either return a clarifying question or state the assumptions
  made explicitly in the response payload. Silent assumption is the failure mode that
  matters here.
- Expose the generated SQL in the UI, collapsed by default. Trust in this feature is
  built by inspectability.
- Cache results by normalised question hash with a short TTL.

---

## 11. PHASE 7 — Frontend

### Design direction
Editorial, institutional, restrained. This is being shown to Managing Directors —
it should read like a briefing document, not a SaaS product.

- **Typeface:** IBM Plex Sans for UI and labels, IBM Plex Mono for figures and
  tabular numerals. Self-host the fonts; no CDN dependency.
- **Palette:** deep navy ground, warm off-white surfaces, restrained gold/brass
  accent used only for Accenture's own series and for the single most important
  number on screen. Muted desaturated tones for competitor series.
- **Explicitly avoid** gradient-heavy, rounded, purple "AI startup" styling. No
  glassmorphism, no neon, no emoji in the UI.
- Generous whitespace, clear typographic hierarchy, thin rules for separation rather
  than heavy card borders and shadows.
- Charts: direct labelling over legends where it fits, no chart junk, no 3D, no
  unnecessary colour. Consistent colour assignment per competitor group across every
  chart in the app.
- Currency displayed in AUD with sensible magnitude formatting ($1.2B, $340M).
  Tabular numerals everywhere figures are compared vertically.

### Layout — landing view
The landing view answers two questions only: *how are we doing* and *what should we
chase next*. Everything else is one click deeper.

1. **KPI strip** (full width, 4 tiles): total Defence contract value for period;
   contract count; Accenture value and share of total; period-on-period delta.
2. **Competitor share of wallet** (primary chart, largest element): stacked area or
   grouped bar over time, by competitor group, Accenture visually distinguished.
3. **Expiring contracts / recompete pipeline** (table, right or below): contracts
   with `period_end` in the next 6–12 months, competitor-held, in target themes,
   sorted by value. This is the lead list — make it scannable and exportable.

### Secondary views
4. **Theme breakdown** — value by theme with Accenture-vs-field split; treemap or
   horizontal bar. Surfaces where Accenture is absent from high-value themes.
5. **Competitor momentum** — small multiples, one sparkline per competitor group,
   rolling 12-month value.
6. **Agency breakdown** — spend by Defence buyer entity.
7. **Contract explorer** — the filterable table over everything, with detail drawer.
8. **Ask** — the LLM query interface.

### Ask interface behaviour
- Single prominent input, a few suggested starter questions.
- Streaming or clear staged loading state: generating query → running → summarising.
- Result renders as chart where the shape suits it, table otherwise, with a toggle.
- Collapsed "view SQL" disclosure.
- One-click "add to dashboard" is out of scope for v1 — do not build it.

### Frontend engineering rules
- API base URL from `import.meta.env.VITE_API_BASE_URL`. Never a hardcoded
  `localhost`.
- TanStack Query for all server state — no `useEffect` fetch patterns.
- Every request state handled explicitly: loading skeletons, error states with retry,
  and genuine empty states. Empty states matter here; filter combinations will
  legitimately return nothing.
- Shared chart theme object; no per-chart colour literals.
- Components typed against generated backend types, no `any`.

---

## 12. PHASE 8 — External intelligence and weekly market reports

### 12.1 Purpose

AusTender tells you what was *signed*. It does not tell you what is *happening* —
leadership moves, acquisitions, strategy shifts, policy changes, firms being frozen
out of government work, capability announcements. Those show up in trade media weeks
or months before they show up in a contract notice, and they are what MDs actually
talk about.

This capability ingests reputable Defence and consulting-market media, extracts
events, links them where possible to contract data already in the database, and
compiles a **weekly market report** covering key events and Accenture's positioning.

Read Section 12.3 before writing any fetching code. It constrains the design.

### 12.2 Source registry

All sources live in `backend/app/intelligence/sources.yaml`. No hardcoded URLs in
code. Each entry carries:

```yaml
- slug: defence-connect
  name: Defence Connect
  domain: defenceconnect.com.au
  category: defence_industry        # defence_industry | consulting_market | policy | official | financial
  access: rss                       # rss | html | official_api
  feed_url: ""                      # populate in Phase 8.0 after verification
  tier: 1                           # 1 = high trust, weight heavily in reports
  paywalled: partial
  robots_checked: false
  notes: ""
```

**Seed the registry with these. All have been confirmed to exist and are relevant:**

| Source | Domain | Category | Why it matters |
|---|---|---|---|
| Defence Connect | `defenceconnect.com.au` | defence_industry | Market intelligence platform for Australia's defence industry; strong on industry/procurement movement. RSS feed available. |
| Australian Defence Magazine | `australiandefence.com.au` | defence_industry | Focused specifically on defence capability planning and procurement — closest editorial match to this product's purpose. |
| Consultancy.com.au | `consultancy.com.au` | consulting_market | The platform for Australia's consulting industry. Covers competitor leadership moves, acquisitions, government consulting spend, and firm-level strategy — including Accenture directly. |
| Asia Pacific Defence Reporter | `asiapacificdefencereporter.com` | defence_industry | Long-established regional defence analysis; useful for strategic context. |
| The Mandarin | `themandarin.com.au` | policy | Commonwealth public sector — machinery of government, procurement policy, APS reform. Verify access model. |
| InnovationAus | `innovationaus.com` | policy | Government tech and digital policy; relevant to digital engineering and decision advantage themes. |
| Department of Defence | `defence.gov.au` | official | Media releases, ministerial announcements, Integrated Investment Program and strategic review documents. Primary source — weight highest. |
| ANAO | `anao.gov.au` | official | Audit reports on procurement and consultant spend. Primary source, high signal. |

Do not add sources outside the registry without asking. Do not add aggregators,
forums, blogs, or social media.

### 12.3 Legal, licensing and compliance constraints — read first

These are hard design constraints, not preferences. The output of this feature will
circulate inside Accenture with Accenture's name on it.

1. **Do not persist full article text.** Store: URL, headline, publication date,
   outlet, author where available, and a **short extract (max ~40 words)** for
   context. Fetch full text transiently in memory for extraction and summarisation,
   then discard it. Do not build a full-text archive of third-party journalism.
2. **All generated report prose must be original synthesis**, written in the
   platform's own words. Do not reproduce source sentences or closely paraphrase
   source structure. Where a specific form of words genuinely matters (a
   ministerial statement, an audit finding), use a short quotation under 15 words,
   attributed, and no more than one quotation per source.
3. **Always attribute and always link.** Every claim in a weekly report must carry
   an inline source reference resolving to the original URL. An MD must be one click
   from the primary source.
4. **Respect `robots.txt` and terms of service.** Check and record compliance per
   source in the registry. Prefer RSS/Atom feeds. Where no feed exists, fetch only
   what robots permits.
5. **Never bypass a paywall or authentication.** Several of these outlets have
   subscription tiers. If content is gated, ingest the metadata and headline only,
   mark the item `access_restricted`, and surface the link. Do not attempt
   workarounds, cached copies, or archive mirrors.
6. **Rate-limit politely.** Minimum 1 request per 2 seconds per domain, identifying
   User-Agent, exponential backoff on errors.
7. **No personal data beyond what is professionally published.** Named executives in
   their professional capacity are in scope. Nothing further.

Implement 1–3 as enforced code paths, not as prompt instructions. Specifically:
truncate extracts at the storage layer, and make the report generator physically
unable to emit an unattributed claim (see 12.7).

### 12.4 Phase 8.0 — Verification gate

Before writing the ingestion pipeline:
1. For each registry source, locate the RSS/Atom feed URL if one exists, or confirm
   none does. Record in `sources.yaml`.
2. Fetch and record each source's `robots.txt`; set `robots_checked` and note any
   disallowed paths.
3. Record the access model: open, partial paywall, hard paywall.
4. Save one sample feed response per source to `data/raw/feeds/`.
5. Report a table: source, feed availability, robots status, access model, and a
   recommendation to include or exclude.

Exclude any source where compliant automated access isn't clearly available. A
smaller compliant source set is worth more than a large one that creates risk.

### 12.5 Database additions

### `sources`
Mirror of the registry, loaded from YAML. `id`, `slug`, `name`, `domain`,
`category`, `tier`, `access`, `feed_url`, `active`.

### `news_items`
| column | type | notes |
|---|---|---|
| `id` | bigserial PK | |
| `source_id` | int FK, indexed | |
| `url` | text unique, indexed | canonicalised — strip tracking params |
| `url_hash` | text unique | dedup key |
| `headline` | text | |
| `extract` | text | **enforce max 40 words at write time** |
| `author` | text nullable | |
| `published_at` | timestamptz, indexed | |
| `fetched_at` | timestamptz | |
| `access_restricted` | boolean | true if paywalled/gated |
| `relevance_score` | numeric(4,3), indexed | see 12.6 |
| `story_cluster_id` | int FK nullable, indexed | cross-outlet dedup |
| `processed_at` | timestamptz nullable | extraction watermark |

There is deliberately **no `full_text` column.** Do not add one.

### `story_clusters`
Groups the same underlying event reported by multiple outlets.
`id`, `canonical_headline`, `first_published_at`, `item_count`,
`max_source_tier`, `event_type`.

### `news_entities`
| column | type | notes |
|---|---|---|
| `news_item_id` | bigint FK, indexed | |
| `entity_type` | text | `competitor` \| `agency` \| `person` \| `program` \| `theme` |
| `entity_value` | text | surface form as it appeared |
| `competitor_group_id` | int FK nullable | resolved where possible |
| `theme_id` | int FK nullable | |
| `confidence` | numeric(4,3) | |

### `news_events`
Structured events extracted from clusters — this is what the weekly report is built
from, not raw articles.
| column | type | notes |
|---|---|---|
| `id` | bigserial PK | |
| `story_cluster_id` | int FK | |
| `event_type` | text, indexed | see taxonomy below |
| `summary` | text | **original synthesis, ≤ 2 sentences** |
| `occurred_at` | date | |
| `competitor_group_id` | int FK nullable, indexed | |
| `agency_org_id` | int FK nullable | |
| `theme_id` | int FK nullable, indexed | |
| `value_mentioned` | numeric(18,2) nullable | contract/deal value if stated |
| `materiality` | text | `high` \| `medium` \| `low` |
| `confidence` | numeric(4,3) | |
| `linked_ocid` | text FK nullable, indexed | link to `contracts`, see 12.6.4 |

**Event type taxonomy** (closed list — extend only by asking):
`contract_award`, `contract_loss`, `acquisition`, `divestment`,
`leadership_change`, `capability_launch`, `office_opening`, `partnership`,
`policy_change`, `procurement_reform`, `audit_finding`, `reputational_event`,
`workforce_change`, `program_milestone`, `program_delay`, `budget_announcement`.

### `weekly_reports`
`id`, `period_start`, `period_end`, `generated_at`, `status`
(`draft` | `published`), `executive_summary`, `positioning_assessment`,
`payload` jsonb (full structured report), `model_version`, `event_count`,
`source_count`.

### `report_feedback`
Lets MDs mark items useful or not — this becomes your relevance training signal.
`report_id`, `event_id`, `rating`, `comment`, `created_at`.

### 12.6 Processing pipeline

Run as a single idempotent CLI: `python -m app.intelligence.ingest`.

**12.6.1 Fetch.** Pull each active source's feed. Canonicalise URLs (strip UTM and
tracking params) before hashing, so the same article from different referrers
dedupes. Skip anything already stored by `url_hash`. Persist raw feed responses to
`data/raw/feeds/` via the same `RawStore` interface as Phase 1.

**12.6.2 Relevance filter — cheap before expensive.** Two tiers, same rationale as
theme classification:
- **Tier 1, deterministic:** keyword and entity matching against competitor names,
  Defence agency names, theme keywords, and program names (AUKUS, Hunter, Mogami,
  SEA/LAND/AIR project numbers, JP-series). Score and discard anything below a
  configurable floor. This will reject the large majority of items for free.
- **Tier 2, LLM:** only items passing Tier 1 go to the model for event extraction.

Never send the whole feed to the LLM. Most defence trade media is about platforms
and hardware, which is irrelevant to a consulting-services view of the market.

**12.6.3 Extraction.** For each surviving item, one LLM call returning strict JSON:
event type from the closed taxonomy, a ≤2-sentence original-synthesis summary,
entities, theme, materiality, confidence. Validate the JSON against a Pydantic
schema and reject non-conforming responses rather than coercing them. Record
`model_version` for reproducibility.

**12.6.4 Contract linkage — the feature that makes this more than a news reader.**
Attempt to match each `contract_award` or `contract_loss` event to an actual row in
`contracts`:
- Match on supplier + agency + approximate value + date proximity.
- Require a configurable confidence threshold; leave `linked_ocid` null rather than
  guessing. A wrong link is worse than no link.
- Surface both directions in the UI: from a contract, show related news; from a news
  event, show the underlying contract notice.

This is where the two data sources compound. A Consultancy.com.au item about a
competitor winning federal work, matched to the actual AusTender notice with its
real value and expiry date, is materially more useful than either alone.

**12.6.5 Clustering.** Group items reporting the same event using headline and
entity similarity within a rolling window. Keep the highest-tier source as
canonical. Report the event once, cite all outlets.

### 12.7 Weekly report generation

CLI: `python -m app.intelligence.weekly_report --week-ending YYYY-MM-DD`.
Schedule: Monday morning, covering the preceding week.

**Report structure:**

1. **Executive summary** — 3–5 sentences. What changed in the market this week that
   an MD needs to know. Written last, from the sections below.
2. **Contract activity** — new Defence awards from AusTender in the period, by
   competitor group and theme, with values. This section comes from the database,
   not from news. Quantified, not narrative.
3. **Key market events** — ranked by materiality. Each entry: original-synthesis
   summary, event type, competitor/agency involved, and source attribution with
   link. Group by event type.
4. **Competitor movements** — per competitor group, what happened this week and how
   it reads against their trailing 12-month contract trajectory from AusTender. This
   is where news and contract data are explicitly combined.
5. **Accenture positioning** — see 12.8.
6. **Watch items** — contracts expiring in the next 90 days in themes where events
   occurred this week. Connects market news to actionable pipeline.
7. **Sources** — full list of every source cited, with links.

**Generation constraints, enforced in code:**
- The report is assembled from `news_events` and SQL aggregates, **not** by handing
  the LLM a pile of articles and asking for a report. The LLM writes connective
  prose over structured inputs it cannot invent.
- Every factual claim must carry an `event_id` or a SQL-derived figure. Implement a
  validation pass that rejects a generated report containing any claim without a
  resolvable source reference. If the validator can't trace it, the report doesn't
  publish.
- Numbers in the report come from the database, never from the model. Pass figures
  in as pre-computed values and instruct the model to use them verbatim.
- Output as structured JSON first, render to HTML/PDF second. Never generate
  presentation markup directly from the model.

### 12.8 Accenture positioning assessment

This section is the most valuable and the most dangerous. It is **inference**, and
it must be presented as such.

**Generate:**
- **Share position** — Accenture's share of Defence contract value over trailing 4,
  12 and 24 months, with direction. Pure SQL, no inference.
- **Theme coverage** — themes where Accenture holds contracts vs themes with
  significant value where Accenture is absent. Pure SQL.
- **Competitive pressure signals** — competitor events this week that plausibly bear
  on Accenture's position, each tied to a specific event and a specific contract or
  theme.
- **Opportunity signals** — expiring competitor-held contracts, new programs
  announced, agencies increasing spend in Accenture-capable themes.
- **Assessed implications** — the LLM's reading of what the week means for
  positioning. **Maximum 5 bullets.**

**Mandatory honesty requirements:**
- Render inferred content in a visually distinct block, explicitly labelled as
  assessment rather than fact. Do not blend it with the quantified sections.
- Every inference must name the evidence it rests on. "Deloitte is gaining ground in
  workforce" is unacceptable without the contract figures and the events behind it.
- The model must be instructed to state when evidence is thin, and the prompt must
  make "insufficient signal this week" an acceptable and expected output. A weekly
  cadence over a data source with a 42-day reporting lag will produce genuinely
  quiet weeks. Manufactured insight on a quiet week is the failure mode that will
  destroy MD trust in this product — design against it deliberately.
- Never assert a competitor's strategy, intent, or internal state. Report what they
  did and what was published. Anything beyond that is speculation being laundered
  through a dashboard.
- No commentary on named individuals beyond their published professional moves.

### 12.9 Backend endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/intel/reports` | Paginated list of weekly reports |
| `GET /api/intel/reports/{id}` | Full structured report |
| `GET /api/intel/reports/latest` | Most recent published report |
| `GET /api/intel/events` | Filterable event feed (type, competitor, theme, date, materiality) |
| `GET /api/intel/events/{id}` | Event detail incl. all source items and linked contract |
| `GET /api/contracts/{ocid}/news` | News events linked to a contract |
| `POST /api/intel/reports/{id}/feedback` | MD marks an item useful / not useful |
| `POST /api/intel/reports/generate` | Trigger generation (admin, rate-limited) |

Extend the Phase 6 LLM query layer to cover `news_events`, `story_clusters` and
`sources` — add them to the table allowlist and document them in
`llm/schema_context.md` with worked examples, so MDs can ask questions spanning both
contract and market-event data.

### 12.10 Frontend additions

**Weekly report view** — the primary surface for this capability. Design it as a
briefing document, not a feed: single column, generous measure, strong typographic
hierarchy, IBM Plex, print-legible. An MD will read this on a phone at 7am or forward
it to a colleague.

- Sticky section nav.
- Quantified sections use the same chart theme and competitor colours as the main
  dashboard — consistency matters for recognition.
- Inferred positioning content in a visually distinct, clearly labelled block.
- Inline source citations as superscript links to the source list.
- **Export to PDF** and **copy-as-email** actions. This content will be forwarded;
  make that clean rather than making people screenshot it.
- Thumbs up/down per event, wired to `report_feedback`.

**Event feed view** — filterable chronological event stream between weekly reports,
for MDs who want to check in mid-week.

**Contract detail integration** — a "related market activity" panel on the contract
detail drawer showing linked news events.

### 12.11 Testing

- Extract truncation: assert no stored `extract` exceeds the word cap, for
  adversarial inputs.
- Attribution validator: assert a report containing an unsourced claim fails to
  publish. This is the most important test in Phase 8.
- Relevance filter: fixture set of clearly relevant and clearly irrelevant articles,
  assert correct tiering.
- Linkage: fixture news events and contracts, assert correct matches and — equally
  important — assert near-miss cases produce a null link rather than a wrong one.
- Dedupe: same story from three outlets clusters into one event.
- Quiet-week behaviour: generate a report from a near-empty event set and assert the
  output says so rather than padding.

---

## 13. PHASE 9 — Historical document corpus

### 13.1 Purpose

News gives you this week. Contracts give you what was signed. Neither gives you the
**standing reference layer**: the strategy documents, investment programs, audit
reports and procurement policy that explain *why* the market looks the way it does
and where it is going.

This phase builds a versioned, searchable corpus of primary source documents so that:
- Weekly reports can ground market events in stated government policy and program
  intent rather than in the model's priors.
- MDs can ask questions spanning contracts, market events, and policy documents in
  one place.
- Changes between document versions are detectable — a shift in an investment
  program or a procurement policy revision is a market event in itself.

**Reuse the pattern, don't reinvent it.** This is structurally the same problem as
the AEMC regulatory document pipeline already built elsewhere: extraction,
version-tracking, and publishing into Blob Storage plus Postgres. Lift that
architecture. The differences are the source set, the licence model in 13.2, and the
embedding layer in 13.6.

### 13.2 Licensing — determine per source, do not assume

This is the section to get right before any code. I initially assumed Commonwealth
material is uniformly openly licensed. **It is not.** Verified position:

- Many Commonwealth agencies do publish under **Creative Commons Attribution 4.0**,
  with attribution required — DFAT, the APS Commission and IP Australia all state
  this, and the APSC's own guidance notes that alternative licences apply to some
  documents.
- **The Department of Defence is more restrictive.** Defence's copyright notice
  states that material from its website must not be used in advertising, displays,
  other websites, or any public or mass media context other than reporting news,
  without specific written authorisation. Related Defence sites reserve all rights
  beyond permitted statutory use and require Commonwealth copyright and Defence
  origin to be acknowledged.

Therefore:
1. **No blanket assumption.** Licence is determined and recorded **per document**,
   not per source and not per tier of government.
2. Store the licence determination, its source URL, and the date checked, on the
   document row. A document with `licence_status = 'unknown'` is metadata-only until
   resolved.
3. **Internal-use-only by default.** Nothing in this corpus gets redistributed
   outside Accenture, republished, or surfaced in any externally-facing artefact
   unless the licence clearly permits it.
4. **Attribution is mandatory** on every quotation, extract and derived figure —
   agency, document title, and link.
5. **Get Accenture Legal / IP sign-off on the corpus scope before building the
   full-text store.** Do not treat this spec as legal advice; it is an engineering
   design that assumes that sign-off exists. Flag this explicitly in the Phase 9.0
   report and do not proceed past metadata-only ingestion without it.

### 13.3 Storage tiers — enforced in code

Every document is assigned a tier at ingestion. The tier controls what may be
stored. Implement as an enum with the storage layer refusing writes that exceed the
tier.

| Tier | Applies to | May store |
|---|---|---|
| `open_licensed` | Documents with a clear CC BY (or equivalent) licence | Full text, full PDF, embeddings, unlimited extracts |
| `permitted_internal` | Commonwealth documents without an open licence, where internal reference use is covered by sign-off | Full text and embeddings for internal retrieval; **no redistribution, no external rendering**; extracts capped at 50 words in any output |
| `metadata_only` | Third-party commercial publications, paywalled reports, anything with `licence_status = 'unknown'` | Title, author, publisher, date, URL, ≤40-word extract. **No full text, no embeddings.** |

Third-party trade publications from Phase 8 — Defence Connect, Australian Defence
Magazine, Consultancy.com.au, Asia Pacific Defence Reporter and the like — are
`metadata_only`. Phase 8's constraints are unchanged by this phase. This phase does
not create a licence to archive journalism.

### 13.4 Phase 9.0 — Verification gate

Before any ingestion code:
1. For each target document source, locate and record the copyright/licensing page
   URL and its stated terms verbatim in `intelligence/document_licences.md`.
2. Assign each source a default tier, with the evidence for that assignment.
3. Confirm `robots.txt` permits automated retrieval of the document paths.
4. Produce a one-page summary for Legal review: sources, licences, proposed tiers,
   proposed use. **Stop and report. Do not proceed to 13.6 without sign-off.**
5. Ingest metadata only for anything unresolved.

### 13.5 Target document set

Seed `intelligence/documents.yaml` with these targets. Priority reflects value to
the product's actual questions, not comprehensiveness.

**Priority 1 — policy and program (explains the market)**
- National Defence Strategy / Defence Strategic Review, and predecessors
- Integrated Investment Program, all published editions
- Defence Industry Development Strategy
- Commonwealth Procurement Rules, all versions
- APS Strategic Commissioning Framework — directly governs Commonwealth use of
  external consultants, and is the single most consequential policy document for
  this product's thesis
- Defence Annual Reports
- Portfolio Budget Statements, Defence portfolio

**Priority 2 — audit and oversight (explains constraint and risk)**
- ANAO performance audits on Defence procurement, contract management, and
  consultant/contractor spend
- Senate inquiry reports into the conduct of consulting firms
- Parliamentary Joint Committee reports touching Defence procurement

**Priority 3 — market structure**
- Consultancy.org / Consultancy.com.au "Top Consulting Firms in Australia" editions
  — `metadata_only`, referenced not archived
- Australian Defence Magazine Top 40 defence contractors listings — `metadata_only`

For each target record: title, publisher, expected URL or landing page, cadence
(one-off / annual / revised), tier, and whether superseding versions are expected.

### 13.6 Schema

### `documents`
Logical document, stable across versions.
| column | type | notes |
|---|---|---|
| `id` | bigserial PK | |
| `slug` | text unique | |
| `title` | text | |
| `publisher_org_id` | int FK nullable -> organisations | |
| `doc_type` | text, indexed | `strategy` \| `investment_program` \| `policy` \| `audit` \| `annual_report` \| `budget` \| `inquiry` \| `market_report` |
| `storage_tier` | text, indexed | enum from 13.3 |
| `licence_status` | text | `cc_by` \| `cc_by_nc` \| `crown_reserved` \| `commercial` \| `unknown` |
| `licence_source_url` | text | where the determination came from |
| `licence_checked_at` | date | |
| `attribution_string` | text | pre-composed, used verbatim in all outputs |
| `is_superseded` | boolean | |
| `created_at` / `updated_at` | timestamptz | |

### `document_versions`
| column | type | notes |
|---|---|---|
| `id` | bigserial PK | |
| `document_id` | bigint FK, indexed | |
| `version_label` | text | e.g. "2024", "Rev 3" |
| `published_date` | date, indexed | |
| `source_url` | text | |
| `content_hash` | text, indexed | detects silent republication |
| `raw_object_key` | text | pointer into `RawStore` |
| `page_count` | int | |
| `full_text` | text nullable | **null unless tier permits** |
| `extraction_method` | text | `pdf_text` \| `ocr` \| `html` |
| `extraction_quality` | numeric(4,3) | flag poor extractions rather than trusting them |
| `ingested_at` | timestamptz | |
| `supersedes_version_id` | bigint FK nullable | |

### `document_chunks`
Retrieval units. Only populated for tiers permitting full text.
| column | type | notes |
|---|---|---|
| `id` | bigserial PK | |
| `document_version_id` | bigint FK, indexed | |
| `chunk_index` | int | |
| `heading_path` | text | e.g. "Ch 4 > Integrated Force > Undersea" — keeps citations precise |
| `page_from` / `page_to` | int | enables page-level citation |
| `content` | text | |
| `token_count` | int | |
| `embedding` | vector(1024) | **pgvector** |

Add an HNSW index on `embedding`. Enable the `pgvector` extension via Alembic —
Azure Database for PostgreSQL Flexible Server supports it.

### `document_entities`
Links documents to the existing dimension tables so policy connects to contracts.
`document_version_id`, `entity_type` (`theme` | `agency` | `program` |
`competitor`), `theme_id`, `competitor_group_id`, `mention_count`, `confidence`.

### `document_diffs`
Version-to-version change detection — this is where the analytical value is.
`id`, `document_id`, `from_version_id`, `to_version_id`, `section_heading`,
`change_type` (`added` | `removed` | `modified`), `summary` (original synthesis,
≤2 sentences), `materiality`, `detected_at`.

### 13.7 Ingestion pipeline

CLI: `python -m app.intelligence.documents --target <slug>` and `--all`.

1. **Fetch.** Retrieve the document, persist the original bytes to `RawStore`
   unchanged. Compute `content_hash`.
2. **Tier gate.** If `metadata_only`, stop here — record the row and exit. Do not
   extract, do not embed. Enforce this with an assertion, not a comment.
3. **Extract.** PDF text extraction first; OCR fallback for scanned documents.
   Score extraction quality and flag anything poor for manual review rather than
   silently indexing garbage. Government PDFs are frequently multi-column with
   tables — verify the extraction reads correctly before trusting it.
4. **Version resolution.** If `content_hash` matches an existing version, no-op.
   If the document is a new edition of an existing logical document, link
   `supersedes_version_id` and set `is_superseded` on the prior version. Never
   overwrite a prior version — the history is the asset.
5. **Chunk.** Structure-aware, not fixed-window: split on headings, keep
   `heading_path` and page range on every chunk so retrieval can cite
   document, version, section and page. Target 400–800 tokens with modest overlap.
6. **Embed.** Batch embeddings, store in `document_chunks.embedding`. Record the
   embedding model and dimension in config so a model change triggers a deliberate
   re-embed rather than silent mixing of vector spaces.
7. **Entity tagging.** Reuse the Phase 3 theme and competitor rules over document
   text, so a policy document is discoverable by the same themes as contracts.
8. **Diff.** On a superseding version, section-level diff against the prior version;
   summarise material changes into `document_diffs`.

Idempotent throughout. Re-running over the full target set must produce no
duplicates and no re-embedding of unchanged content.

### 13.8 Retrieval and LLM integration

This is where the earlier position changes, and the change is deliberate: for
contracts alone, text-to-SQL was sufficient and a vector store would have been
overhead. With a document corpus in scope, semantic retrieval now genuinely earns
its place. `pgvector` keeps it in the same Postgres instance — no separate vector
database.

Extend the Phase 6 `/api/ask` layer to a **router** with three retrieval paths:

| Question shape | Path |
|---|---|
| Quantitative — values, counts, shares, trends, expiries | SQL over `contracts` and aggregates. Unchanged from Phase 6. |
| Market events — what happened, who moved | SQL over `news_events`. From Phase 8. |
| Policy and context — what does the strategy say, what changed, why | Vector retrieval over `document_chunks`, tier-filtered |
| Mixed | Run the relevant paths and synthesise, keeping each claim attributed to its own path |

**Hard requirements:**
- **Never let the model answer a numeric question from document retrieval.** Figures
  come from SQL. A number pulled out of a PDF chunk by an LLM is exactly how a
  wrong figure ends up in an MD's board pack. Route numerics to SQL, always.
- **Filter retrieval by `storage_tier` at query time.** `metadata_only` chunks do
  not exist, so they cannot leak; but assert it anyway.
- **Cite to page level.** Every document-derived statement returns document title,
  version, section heading, page, attribution string and link. If a citation can't
  be constructed, the claim is dropped.
- Cap total document context per request; prefer fewer, higher-scoring chunks over
  volume.
- Extend `llm/schema_context.md` to describe the document tables and add worked
  examples for each routing path.

### 13.9 Weekly report integration

Two additions to Phase 8's report:
- **Policy context** — where a market event relates to a policy or program the
  corpus covers, cite it. A competitor's Defence win reads differently against the
  stated investment priorities for that domain.
- **Document changes this period** — any `document_diffs` with `materiality = high`
  detected in the period. A revision to the Commonwealth Procurement Rules or the
  Strategic Commissioning Framework is a genuine market event, and it will not
  appear in any news feed with the significance it deserves.

The same attribution validator from 12.7 applies: document-derived claims need a
resolvable `document_version_id` plus page reference, or the report does not publish.

### 13.10 Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/docs` | Filterable document list (type, publisher, theme, tier) |
| `GET /api/docs/{slug}` | Document with version history |
| `GET /api/docs/{slug}/versions/{id}` | Version metadata; full text only where tier permits |
| `GET /api/docs/{slug}/diffs` | Material changes between versions |
| `GET /api/docs/search?q=` | Semantic search across permitted chunks, returns cited passages |
| `GET /api/themes/{slug}/documents` | Documents relevant to a theme |

### 13.11 Frontend

- **Document library** — filterable table by type, publisher, theme, date, with
  version history and a clear licence/attribution line on every entry.
- **Passage search** — semantic search returning cited passages with document,
  version, section, page, and a link to the source. Not a chat interface; a research
  tool.
- **Version comparison** — side-by-side material changes between two editions, using
  `document_diffs`.
- **Theme pages** — for each of the five Defence themes, a combined view: contract
  value trend, competitor positions, recent market events, and the governing policy
  documents. This is the view that makes the three data sources into one product.
- Attribution string rendered on every document surface. Not optional, not a
  tooltip.

### 13.12 Testing

- Tier enforcement: attempt a full-text write against a `metadata_only` document and
  assert it is refused at the storage layer. Most important test in this phase.
- Retrieval tier filter: assert no `metadata_only` content can be returned by
  semantic search under any query.
- Citation completeness: assert every retrieved chunk can produce a full citation
  (document, version, heading, page, attribution, URL).
- Version handling: ingest v1, then v2; assert both retained, supersession set
  correctly, diffs generated, and re-ingesting v2 is a no-op.
- Extraction quality: fixture set including a multi-column PDF and a scanned
  document; assert poor extractions are flagged rather than indexed.
- Numeric routing: assert a quantitative question routes to SQL and never answers
  from document chunks.

---

## 14. Cross-cutting requirements

### Configuration
`.env.example` must document every variable:
```
DATABASE_URL=
DATABASE_URL_READONLY=
AUSTENDER_API_BASE_URL=
RAW_STORE_PATH=./data/raw
ANTHROPIC_API_KEY=
CORS_ALLOWED_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
LLM_MAX_ROWS=1000
LLM_STATEMENT_TIMEOUT_MS=10000
THEME_LLM_VALUE_THRESHOLD=
NEWS_FETCH_USER_AGENT=
NEWS_MIN_REQUEST_INTERVAL_MS=2000
NEWS_EXTRACT_MAX_WORDS=40
NEWS_RELEVANCE_FLOOR=0.35
NEWS_LINKAGE_CONFIDENCE_FLOOR=0.75
REPORT_TIMEZONE=Australia/Sydney
EMBEDDING_MODEL=
EMBEDDING_DIMENSION=1024
DOC_CHUNK_TARGET_TOKENS=600
DOC_RETRIEVAL_MAX_CHUNKS=12
```
`.gitignore` must cover `.env`, `data/raw/`, `__pycache__/`, `node_modules/`,
`dist/`, `.venv/`.

### Testing
- Unit tests for `transform.py` against the real saved sample response — this is the
  highest-value test surface in the project, because a transform bug corrupts
  everything downstream silently.
- Unit tests for `guardrails.validate()` with an explicit battery of malicious and
  malformed SQL inputs. Every rejection rule needs a test.
- Unit tests for theme and competitor classification against fixture contracts.
- Integration test: backfill a small date window against a test database, assert row
  counts and that re-running is idempotent.

### Azure portability checklist — verify before declaring done
- [ ] Zero hardcoded hosts, ports, URLs or credentials in either codebase
- [ ] Backend has a working `Dockerfile`
- [ ] Frontend builds to static assets via `npm run build`
- [ ] CORS origins env-driven
- [ ] `RawStore` is behind an interface, ready for a Blob Storage implementation
- [ ] Alembic migrations run cleanly against an empty database
- [ ] Ingestion runs as a standalone CLI process, independent of the web app

---

## 15. Build order and reporting

Work in this order. Report at each boundary; do not run ahead.

| Phase | Deliverable | Done when |
|---|---|---|
| 0 | API verification + field inventory + sample response | Real endpoint documented, sample saved, schema deltas flagged |
| 1 | API client | Can fetch and archive a date window with pagination and retries |
| 2 | Schema + migrations | Alembic up/down clean; seed data for themes and competitor groups loaded |
| 3 | Transform + processing | Sample response loads into normalised tables; re-run is idempotent |
| 4 | Backfill + incremental | Small window backfilled; incremental correctly upserts an amendment |
| 5 | Backend API | All endpoints return real data; `/health` green |
| 6 | LLM layer | Read-only role enforced; guardrail test battery passing |
| 7 | Frontend | Landing view live against real API; Ask interface functional |
| 8.0 | Source verification | Feed URLs, robots and access model recorded per source; include/exclude recommendation made |
| 8.1 | Feed ingestion + relevance filter | Items stored with capped extracts; irrelevant items rejected before LLM |
| 8.2 | Extraction + clustering + linkage | Structured events produced; near-miss links correctly null |
| 8.3 | Weekly report | Attribution validator passing; quiet-week case handled honestly |
| 8.4 | Report + event frontend | Report view renders, exports clean, feedback wired |
| 9.0 | Licence determination | Per-source licences recorded with evidence; tiers assigned; Legal summary produced. **Hard stop pending sign-off.** |
| 9.1 | Document ingestion + versioning | Targets fetched and archived; tier gate enforced; supersession correct; re-run is a no-op |
| 9.2 | Chunking + embeddings | pgvector populated for permitted tiers only; citations resolve to page level |
| 9.3 | Retrieval routing | Numeric questions route to SQL; policy questions route to vector; mixed synthesised with per-claim attribution |
| 9.4 | Diffs + report integration | Material version changes detected and surfaced in weekly report |
| 9.5 | Document frontend | Library, passage search, version comparison, theme pages live |

At each boundary report: what was built, what deviated from this spec and why, what
is stubbed, and what the next phase is blocked on.

### Standing instructions
- Ask before installing a dependency not listed in Section 2.
- Flag contradictions between this spec and reality rather than quietly working
  around them.
- Never commit secrets, real credentials, or raw data files.
- Prefer explicit, auditable, inspectable logic over clever abstraction — the
  classification and scoping rules in particular will be questioned by people who
  need to see how they work.
