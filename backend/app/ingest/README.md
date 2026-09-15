# AusTender OCDS API — Phase 0 verification

Documented against a **real** sample response, not the OCDS spec in the abstract.
Sample saved to `data/raw/sample_response.json` (fetched 2026-09-01, the
`contractPublished` window `2026-09-01T00:00:00Z` → `2026-09-02T00:00:00Z`,
99 releases, 182 KB).

## Endpoint reference

| Property | Finding |
|---|---|
| **Base URL** | `https://api.tenders.gov.au/ocds/` (from `AUSTENDER_API_BASE_URL`, never hardcode) |
| **Authentication** | None. Public, open endpoint. |
| **Historical range** | Data available from 2013-01-01 onward. |
| **License** | `CC BY 3.0 AU` (stated in every package's `license` field). Attribution required. |
| **Publisher** | Department of Finance. |
| **OCDS version** | `1.1` |
| **Package type** | **Release package** — top-level `releases[]` array. **Not** a record package. |

### Endpoints

| Purpose | Path |
|---|---|
| Single notice by CN ID | `findById/{cn_id}` e.g. `findById/CN4273499` |
| By published date | `findByDates/contractPublished/{from}/{to}` |
| By contract start date | `findByDates/contractStart/{from}/{to}` |
| By contract end date | `findByDates/contractEnd/{from}/{to}` |
| By last-modified date | `findByDates/contractLastModified/{from}/{to}` |

- **Dates are path parameters** (not query strings), ISO-8601 UTC: `yyyy-mm-ddThh:mm:ssZ`.
- `contractLastModified` is the right endpoint for **incremental** delta loads (Phase 4.2).
- `contractPublished` is the right endpoint for the **backfill** (Phase 4.1).

## Pagination — IMPORTANT DEVIATION FROM SPEC

The spec (Section 5) assumes a cursor/offset/page-token pagination mechanism.
**The real API has none.** The response has no top-level `links.next`, no cursor,
no page token. A date-window query returns **all** matching releases in a single
package.

**Consequence for the client (Phase 1):** the pagination unit is the **date window
itself**. To bound response size, the client must **narrow the date window** rather
than page through a cursor. The `fetch_releases` async generator will therefore
subdivide a large window into smaller sub-windows (e.g. daily) and yield releases
across them. The `cursor` parameter in the planned signature is not applicable —
replace it with internal date-window chunking.

- Observed: 99 releases for a single day, returned whole. No documented hard cap on
  releases per window; mitigate by keeping windows small (daily) during backfill.

## Empty windows return HTTP 400 — IMPORTANT DEVIATION

A date window containing **zero** releases (weekends, public holidays, quiet days)
does **not** return `200` with an empty `releases[]`. It returns:

```
HTTP 400
{"errorCode": 100, "message": "No Records found for Date Range ['…'-'…']"}
```

This was not visible in the Phase 0 sample (a busy weekday). Over a 5-year backfill
it fires on ~1 day in 3. The client (`client.py`, `_is_no_records`) therefore treats
a `400` carrying `errorCode 100` / "No Records found" as a normal **empty result** —
it archives the body for audit and yields no releases — rather than raising. Only
*other* 400s propagate as errors.

## What the API actually returns vs what needs other methods

Full field inventory over 3,000 stored releases (2026-09-15). The API returns more than
the Phase 0 sample suggested.

**Retrievable via the OCDS API and now extracted:**
- `contracts[]` core (id/cn_id, title, description, value, period, status, dateSigned).
- `parties[]` supplier + procuringEntity (name, ABN, address locality/region/postcode).
- UNSPSC **code** (`contracts[].items[].classification.id`).
- **Buyer organisational unit** — `parties[].contactPoint.division` and `.branch`. AusTender
  attaches the buyer's procurement-officer contact (with the buyer's `division` e.g. `CASG`,
  `ARMY`, `DSTG`, `CIOG`, and `branch` e.g. `JCG - Joint Logistics Command`) to a party's
  contactPoint — **in practice the _supplier_ party**, not the procuringEntity. 100% filled
  for Department of Defence. This is the real Defence-branch data; see
  `transform._extract_buyer_unit`.

**Retrievable via the API but not yet extracted (available in the raw payload):**
- `contracts[].amendments[]` (amendment id / releaseID / amendsReleaseID) — 14% of releases.
- `tender.procurementMethodDetails`, `limitedTenderReason`, `exemption`, `exemptionCode`.
- Party `address` (already parsed into contactPoint region/locality).

**NOT in the OCDS API — needs another method:**
- **UNSPSC title / "Category" text** — the feed carries only the code, no
  `classification.description`. Fill via an external UNSPSC code→title reference dataset.
- **"Category Type" (Goods/Services)** — not in the feed. Approximate from UNSPSC segment,
  or take from AusTender's CSV export / CN detail page.
- **Consultancy flag, SON/panel id, ATM id, confidentiality** — only on the AusTender CN
  detail HTML page / CSV export, not in OCDS.

## Phase 0.4.1 — publication-type discovery (opportunity side)

Verified 2026-09-15. The OCDS API is **award/contract only** — no ATM/tender-stage
releases (every `atm*`/`tenderPublished` date endpoint returns 400; contract releases
carry only the `contract` tag). Opportunities come from the AusTender website instead.

| Type | Working route | Endpoint | Format | robots | Fields |
|---|---|---|---|---|---|
| **ATMs** (open approaches to market) | RSS list + detail page | `GET /public_data/rss/rss.xml` (current ATM list), then `GET /Atm/Show/{uuid}` per item | RSS XML + HTML w/ embedded JSON | **allowed** (`/public_data/*`, `/Atm/Show` not in Disallow) | title, ATM ref, description, link (RSS); agency, `atmCategoryCode` (**UNSPSC**), `atmCategoryTitle` (**category text!**), `atmType`, publish/close dates (detail) |
| Planned Procurements (APP) | not yet resolved | — | — | — | needs discovery (no OCID; not in OCDS) |
| Standing Offers (SONs) | blocked | `/Son/List*` is **Disallowed** in robots | — | disallowed | needs an allowed route |
| Consultancy-flagged | via contracts | derivable from contract data | — | n/a | not a separate feed |

**ATM ingestion (integrated):** `ingest/atms.py` fetches the RSS (robots-allowed),
archives it raw, then enriches each ATM from its `/Atm/Show/{uuid}` page (embedded JSON
+ HTML close/publish dates), rate-limited with a descriptive User-Agent. Upsert on
`atm_id`; ATMs that drop out of the current feed are marked `closed`, never deleted.
Note the ATM feed gives us the **UNSPSC title** the contract feed lacks.

## Rate limits

Not documented. Apply the spec's politeness controls regardless: default 250 ms
delay between requests, exponential backoff on 429/5xx, respect `Retry-After`.

## Response shape (release package)

```
{
  "uri": "...", "publisher": {"name": "Department of Finance"},
  "publishedDate": "2026-09-01T23:46:49Z",
  "license": "https://creativecommons.org/licenses/by/3.0/au/",
  "version": "1.1",
  "extensions": ["http://cdn.tenders.gov.au/ocds/schema/extension.json"],
  "releases": [ { ...release... }, ... ]
}
```

## Field inventory (fill rates over 99-release sample)

Per-release paths and how reliably they are populated:

| JSON path | Type | Fill rate | Notes |
|---|---|---|---|
| `ocid` | string | 100% | Stable process id, e.g. `prod-d512…`. Natural key for current-state contract. |
| `id` | string | 100% | Release id = `{ocid}-{hash}`. Unique per release. → `raw_releases.release_id`. |
| `date` | string (ISO dt) | 100% | Release date → `contracts.date_published`. |
| `tag` | string[] | 100% | All `["contract"]` in this sample. |
| `initiationType` | string | 100% | `"tender"`. |
| `parties[]` | array | 100% | Contains supplier + procuringEntity. |
| `parties[].roles` | string[] | 100% | Values seen: **`supplier`**, **`procuringEntity`**. |
| `parties[].additionalIdentifiers[].scheme=AU-ABN` | string | 91% (181/198) | ABN. Primary dedup key. ~9% of parties have no ABN. |
| `parties[].address` | object | partial | Sometimes empty `{}`. |
| `awards[]` | array | 100% | `awards[].suppliers[]`, `status`, `date`. |
| `contracts[]` | array | 100% | The core object. |
| `contracts[].id` | string | 100% | **This is the AusTender CN id**, e.g. `CN4273499` → `contracts.cn_id`. |
| `contracts[].title` | string | 100% | Often an internal ref code (e.g. `26CPU143`), not descriptive. |
| `contracts[].description` | string | 100% | Descriptive text. |
| `contracts[].dateSigned` | string (ISO dt) | 100% | → `contracts.date_signed`. |
| `contracts[].value.amount` | **string** | 100% | e.g. `"976800.00"` — **string, not number. Cast in transform.** |
| `contracts[].value.currency` | string | 100% | `"AUD"`. |
| `contracts[].period.startDate` | string (ISO dt) | 100% | → `contracts.period_start`. |
| `contracts[].period.endDate` | string (ISO dt) | 100% | → `contracts.period_end`. Critical for expiry view. |
| `contracts[].status` | string | 100% | `"active"`. |
| `contracts[].items[].classification.scheme` | string | 100% | `"UNSPSC"`. |
| `contracts[].items[].classification.id` | string | 100% | UNSPSC **code** e.g. `80101507` → `contracts.unspsc_code`. |
| `tender.procurementMethod` | string | 100% | `open` / `limited` → `contracts.procurement_method`. |
| `tender.procurementMethodDetails` | string | 100% | Human-readable method. |

## Schema deltas to apply in Phase 2 (flagged per spec instruction)

The Section 6 schema assumes fields the real data names differently or omits:

1. **Buyer role is `procuringEntity`, not `buyer`.** The transform must map the
   party whose `roles` contains `procuringEntity` to `contracts.buyer_org_id`.
2. **`contracts.cn_id` comes from `contracts[].id`** (the `CN…` string), not from a
   separate field. `ocid` and `cn_id` are distinct — keep both.
3. **`value_amount` arrives as a string.** Cast to `numeric(18,2)` at transform time;
   do not trust it to arrive numeric.
4. **`unspsc_title` is NOT in the source** — only the UNSPSC code. The spec's
   `contracts.unspsc_title` column can only be filled via a separate UNSPSC code→title
   lookup table. Leave nullable; populate later from a reference table, not from the
   feed.
5. **No `procurement_method` on the contract object** — it lives on `tender.procurementMethod`.
6. **`date_published`** should come from the release `date` (per-release) rather than
   the package-level `publishedDate`.
7. **ABN is ~91% populated**, confirming the spec's dual dedup strategy
   (ABN first, `name_normalised` fallback) is necessary, not optional.

None of these contradict the *intent* of the Section 6 schema — they refine the
transform mapping. No column changes needed beyond treating `unspsc_title` as
reference-derived and nullable.
