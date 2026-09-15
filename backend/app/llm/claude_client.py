"""Minimal Claude API client for on-demand ATM capability analysis."""

from __future__ import annotations

import json

import anthropic

from app.core.config import get_settings


def analyse_atm(
    *,
    atm_title: str | None,
    atm_description: str | None,
    atm_agency: str | None,
    atm_unspsc_title: str | None,
    atm_unspsc_code: str | None,
    atm_type: str | None,
    days_to_close: int | None,
    accenture_unspsc_profile: list[dict],   # [{code, title, count}]
    accenture_agency_profile: list[dict],   # [{name, count}]
    accenture_offering_profile: list[dict], # [{offering, count}]
    accenture_contract_count: int,
) -> dict:
    """Call claude-haiku for a structured fit analysis of one ATM.

    Returns a dict matching the AiScoreResult schema.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    capability_lines = []
    if accenture_offering_profile:
        offerings = ", ".join(f"{o['offering']} ({o['count']} contracts)" for o in accenture_offering_profile[:5])
        capability_lines.append(f"Service offerings: {offerings}")
    if accenture_unspsc_profile:
        cats = ", ".join(f"{u.get('title') or u['code']}" for u in accenture_unspsc_profile[:6])
        capability_lines.append(f"UNSPSC categories: {cats}")
    if accenture_agency_profile:
        agencies = ", ".join(f"{a['name']} ({a['count']})" for a in accenture_agency_profile[:5])
        capability_lines.append(f"Key agency relationships: {agencies}")
    capability_lines.append(f"Total Defence contracts (5yr): {accenture_contract_count}")

    prompt = f"""You are a strategic advisor helping Accenture ANZ assess Defence procurement opportunities.

ACCENTURE CAPABILITY PROFILE (from historical Defence contracts):
{chr(10).join(capability_lines)}

OPPORTUNITY:
- Title: {atm_title or 'N/A'}
- Agency: {atm_agency or 'N/A'}
- Category: {atm_unspsc_title or atm_unspsc_code or 'N/A'}
- Type: {atm_type or 'N/A'}
- Days to close: {days_to_close if days_to_close is not None else 'unknown'}
- Description: {(atm_description or '')[:600] or 'N/A'}

Score Accenture's fit for this opportunity and identify the top 3 likely competitor threats. \
Respond ONLY with valid JSON matching this exact schema (no markdown, no explanation):

{{
  "accenture_score": <integer 0-100>,
  "grade": <"A"|"B"|"C"|"D">,
  "recommendation": <"pursue"|"watch"|"monitor"|"pass">,
  "rationale": "<2-3 sentences>",
  "win_factors": ["<factor>", "<factor>"],
  "capability_gaps": ["<gap>"],
  "competitor_threats": [
    {{"slug": "<slug>", "label": "<name>", "score": <int 0-100>, "reason": "<one sentence>"}}
  ]
}}

Use these slugs for known competitors: accenture, deloitte, ey, kpmg, pwc, mckinsey, bcg, bain,
jacobs, kbr, babcock, bae-systems, boeing-defence, lockheed-martin, thales, dxc, ibm, leidos, nova-systems."""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = msg.content[0].text.strip()
    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)
