"""Natural-language → SQL query layer for Pillar II ("Ask the Market").

Pipeline: (1) Claude generates a single SELECT from the question + schema; (2) the SQL
is guarded (SELECT-only, single statement, forbidden-keyword scan, enforced LIMIT);
(3) it runs inside a READ ONLY transaction with a statement timeout; (4) Claude narrates
the result rows into a plain-English answer and cites the source CN ids.

Defence in depth against a bad/hostile generation:
  * string guardrails reject anything that isn't a lone SELECT/WITH,
  * the query runs in a READ ONLY transaction (Postgres blocks all writes/DDL), and
  * a statement_timeout caps runaway queries.
A dedicated least-privilege DB role is the preferred hardening; the READ ONLY transaction
holds the line until one is provisioned.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine

_SCHEMA_DOC = """\
Postgres database of Australian Defence procurement. Only the Defence portfolio is loaded
(so is_defence is almost always true). Tables (schema public):

contracts — one row per awarded contract (or amendment).
  ocid TEXT PK, cn_id TEXT (AusTender Contract Notice id — use this to cite),
  title TEXT, description TEXT,
  buyer_org_id INT -> organisations.id (the buying agency),
  supplier_org_id INT -> organisations.id (the winning supplier),
  value_amount NUMERIC (AUD, may be NULL), value_currency TEXT,
  value_per_year NUMERIC (annualised value),
  date_published DATE, date_signed DATE, period_start DATE, period_end DATE,
  procurement_method TEXT, unspsc_code TEXT, unspsc_title TEXT,
  is_defence BOOL, amendment_count INT,
  service_offering TEXT (one of 5 Accenture-addressable offerings, else NULL),
  is_addressable BOOL, buyer_division TEXT, buyer_branch TEXT.

organisations — both buyers (agencies) and suppliers.
  id INT PK, name TEXT, name_normalised TEXT, abn TEXT,
  competitor_group_id INT -> competitor_groups.id.

competitor_groups — maps suppliers to meaningful firms.
  id INT PK, slug TEXT (e.g. 'accenture','deloitte','thales'),
  label TEXT (display name), category TEXT
  (accenture | big4 | mbb | sys_integrator | defence_prime | consulting | sme | other).

themes — capability themes. id INT PK, slug TEXT, label TEXT, description TEXT.
contract_themes — link table. id, ocid -> contracts.ocid, theme_id -> themes.id, confidence, method.

Join tips:
  - Supplier firm:  JOIN organisations s ON c.supplier_org_id=s.id
                    JOIN competitor_groups cg ON s.competitor_group_id=cg.id   (cg.slug='accenture' = Accenture)
  - Buying agency:  JOIN organisations b ON c.buyer_org_id=b.id                (b.name is the agency)
  - Themes:         JOIN contract_themes ct ON ct.ocid=c.ocid JOIN themes t ON t.id=ct.theme_id
  - Value is value_amount (AUD, may be NULL — use COALESCE for sums).
  - Australian financial year starts 1 July: FY2025 = 2024-07-01 .. 2025-06-30. Use date_published.
  - When listing individual contracts, ALWAYS select cn_id and a human-readable column so the answer can cite sources.
"""

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|copy|vacuum|"
    r"comment|reindex|refresh|call|do|merge|lock|set|reset|begin|commit|rollback)\b",
    re.IGNORECASE,
)


class SqlGuardError(ValueError):
    """Raised when generated SQL fails the safety guardrails."""


@dataclass
class AskResult:
    question: str
    answer: str
    sql: str
    sources: list[str]
    row_count: int
    columns: list[str]
    rows: list[dict]


def _client():
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.lower().startswith("sql"):
            s = s[3:]
    return s.strip()


def generate_sql(question: str) -> str:
    msg = _client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": f"""{_SCHEMA_DOC}

Write ONE PostgreSQL SELECT query that answers this question. Output ONLY the SQL — no
markdown, no explanation. It must be a single read-only SELECT (or WITH ... SELECT). Do
not modify data. Prefer clear column aliases. If listing contracts, include cn_id. Keep
the query reasonably compact so it fits in one response.

Question: {question}"""}],
    )
    # A truncated response would yield invalid SQL — reject rather than run a partial query.
    if msg.stop_reason == "max_tokens":
        raise SqlGuardError("The query was too complex to generate reliably.")
    return _strip_fences(msg.content[0].text)


def guard_sql(sql: str) -> str:
    """Validate and normalise generated SQL; raise SqlGuardError if unsafe."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise SqlGuardError("Empty query.")

    # single statement only
    if ";" in cleaned:
        raise SqlGuardError("Only a single statement is allowed.")

    # no SQL comments (could smuggle payloads past the keyword scan)
    if "--" in cleaned or "/*" in cleaned:
        raise SqlGuardError("Comments are not allowed in generated SQL.")

    lowered = cleaned.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise SqlGuardError("Only SELECT / WITH queries are allowed.")

    if _FORBIDDEN.search(cleaned):
        raise SqlGuardError("Query contains a forbidden keyword.")

    # enforce a row cap
    max_rows = get_settings().llm_max_rows
    if not re.search(r"\blimit\b", lowered):
        cleaned = f"{cleaned}\nLIMIT {max_rows}"
    return cleaned


def run_sql(sql: str) -> tuple[list[str], list[dict]]:
    """Execute the guarded SQL in a READ ONLY transaction with a statement timeout."""
    timeout_ms = get_settings().llm_statement_timeout_ms
    engine = get_engine()
    with engine.connect() as conn:
        # Read-only transaction + timeout: blocks writes/DDL at the DB level regardless
        # of the connecting role.
        conn.execute(text("SET TRANSACTION READ ONLY"))
        conn.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(r._mapping) for r in result.fetchall()]
        conn.rollback()
    return columns, rows


def _jsonable(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append({k: (str(v) if not isinstance(v, (int, float, bool, type(None), str)) else v)
                    for k, v in r.items()})
    return out


def narrate(question: str, columns: list[str], rows: list[dict]) -> tuple[str, list[str]]:
    """Turn result rows into a plain-English answer + a list of source CN ids."""
    preview = _jsonable(rows[:40])
    msg = _client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        messages=[{"role": "user", "content": f"""A user asked: "{question}"

The query returned {len(rows)} row(s). Columns: {columns}. Rows (first 40):
{json.dumps(preview, default=str)}

Write a concise, direct analyst's answer (2–5 sentences, or a short bulleted list for
rankings). Use AUD magnitudes ($1.2B, $340M). Do not invent numbers not in the data. If
the result is empty, say so plainly.

Then output a JSON object on the FINAL line only, no fences:
{{"answer": "<your answer text>", "sources": ["<cn_id>", ...]}}
where sources are up to 8 cn_id values from the rows (empty list if none)."""}],
    )
    raw = msg.content[0].text.strip()
    # The model may emit prose then JSON; take the last JSON object.
    match = re.search(r"\{.*\}\s*$", raw, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            return obj.get("answer", raw), [str(s) for s in obj.get("sources", [])][:8]
        except json.JSONDecodeError:
            pass
    return raw, []


def answer_question(question: str) -> AskResult:
    sql = guard_sql(generate_sql(question))
    columns, rows = run_sql(sql)
    answer, sources = narrate(question, columns, rows)
    return AskResult(
        question=question, answer=answer, sql=sql, sources=sources,
        row_count=len(rows), columns=columns, rows=_jsonable(rows[:100]),
    )
