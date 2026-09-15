"""AusTender OCDS API client (Phase 1).

Verified against the live API in Phase 0 (see ``README.md``). Two findings shape
this client:

1. **No cursor pagination.** The API exposes no page token, offset or ``links.next``.
   A date-window query returns *all* matching releases in one release package.
   The pagination unit is therefore the **date window itself**: to bound response
   size, this client subdivides a requested range into daily sub-windows and yields
   releases across them. The spec's ``cursor`` parameter is accepted for signature
   compatibility but is a no-op — there is nothing to page.
2. **Dates are path parameters**, ISO-8601 UTC (``yyyy-mm-ddThh:mm:ssZ``), under
   ``findByDates/{dateType}/{from}/{to}``. Single notices come from
   ``findById/{cn_id}``.

Every raw response is archived to the ``RawStore`` before parsing. Nothing about
the host, port or credentials is hardcoded — the base URL is injected from config.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.core.config import get_settings
from app.ingest.raw_store import LocalRawStore, RawStore

logger = logging.getLogger("app.ingest.client")

# Date types accepted by the findByDates endpoint.
DateType = str  # "contractPublished" | "contractStart" | "contractEnd" | "contractLastModified"

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _to_utc_datetime(value: str | date | datetime) -> datetime:
    """Normalise a date/datetime/ISO string to a UTC ``datetime``.

    Bare ``date`` and ``YYYY-MM-DD`` strings anchor at 00:00:00Z.
    """
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    text = value.strip()
    if len(text) == 10:  # YYYY-MM-DD
        parsed = datetime.strptime(text, "%Y-%m-%d")
        return parsed.replace(tzinfo=UTC)
    # Full ISO-8601; tolerate a trailing Z.
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _fmt_api(dt: datetime) -> str:
    """Format a UTC datetime as the API's path parameter form."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_key(dt: datetime) -> str:
    """Filesystem-safe date stamp for archive key names."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H%M%SZ")


def _day_windows(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Split ``[start, end)`` into consecutive one-day windows.

    If ``end <= start`` a single window ``[start, end)`` is returned so callers can
    still make one bounded request. The final window is clamped to ``end``.
    """
    if end <= start:
        return [(start, end)]
    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    while cursor < end:
        nxt = min(cursor + timedelta(days=1), end)
        windows.append((cursor, nxt))
        cursor = nxt
    return windows


class AusTenderError(RuntimeError):
    """Raised when the API cannot be reached after exhausting retries."""


class AusTenderClient:
    """Async client for the AusTender OCDS API.

    Usage::

        async with AusTenderClient() as client:
            async for release in client.fetch_releases("2026-08-01", "2026-08-07"):
                ...

    All tuning (base URL, politeness delay, retry budget) comes from config with
    local defaults; nothing is hardcoded.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        raw_store: RawStore | None = None,
        politeness_delay_ms: int | None = None,
        max_retries: int | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.austender_api_base_url).rstrip("/") + "/"
        self._raw_store = raw_store or LocalRawStore()
        self._politeness_delay_ms = (
            politeness_delay_ms
            if politeness_delay_ms is not None
            else settings.austender_politeness_delay_ms
        )
        self._max_retries = (
            max_retries if max_retries is not None else settings.austender_max_retries
        )
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout_s,
            headers={"Accept": "application/json"},
        )

    async def __aenter__(self) -> AusTenderClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # -- Public API ---------------------------------------------------------

    async def fetch_by_cn_id(self, cn_id: str) -> dict[str, Any] | None:
        """Fetch a single contract notice by its ``CN…`` id.

        Returns the first release in the package, or ``None`` if the notice is not
        found (empty package).
        """
        path = f"findById/{cn_id}"
        key = f"findById/{cn_id}.json"
        package = await self._get_and_archive(path, key, params=None)
        releases = package.get("releases", [])
        return releases[0] if releases else None

    async def fetch_releases(
        self,
        date_from: str | date | datetime,
        date_to: str | date | datetime,
        *,
        date_type: DateType = "contractPublished",
        cursor: object = None,  # noqa: ARG002 - accepted for spec compatibility; the API has no pagination
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield every release in ``[date_from, date_to)`` for ``date_type``.

        The range is walked one day at a time (the real pagination unit). Each
        sub-window is a single request whose raw payload is archived before
        parsing. Callers see a flat stream of releases and never touch page tokens.
        """
        start = _to_utc_datetime(date_from)
        end = _to_utc_datetime(date_to)
        windows = _day_windows(start, end)
        total = 0
        for page, (w_from, w_to) in enumerate(windows):
            path = f"findByDates/{date_type}/{_fmt_api(w_from)}/{_fmt_api(w_to)}"
            key = f"{date_type}/{_fmt_key(w_from)}_{_fmt_key(w_to)}_{page}.json"
            package = await self._get_and_archive(path, key, params=None)
            releases = package.get("releases", [])
            total += len(releases)
            for release in releases:
                yield release
        logger.info(
            "fetch_releases complete",
            extra={"date_type": date_type, "windows": len(windows), "releases_total": total},
        )

    # -- Internals ----------------------------------------------------------

    async def _get_and_archive(
        self, path: str, key: str, params: dict[str, Any] | None
    ) -> dict[str, Any]:
        response = await self._request_with_retry(path, params)
        raw = response.content
        locator = self._raw_store.put(key, raw)
        try:
            package: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AusTenderError(f"non-JSON response for {path} (archived at {locator})") from exc
        logger.info(
            "archived raw response",
            extra={"path": path, "key": key, "bytes": len(raw), "locator": locator},
        )
        return package

    async def _request_with_retry(
        self, path: str, params: dict[str, Any] | None
    ) -> httpx.Response:
        attempt = 0
        while True:
            await self._politeness_pause()
            started = time.perf_counter()
            try:
                response = await self._client.get(path, params=params)
                duration_ms = round((time.perf_counter() - started) * 1000, 1)
            except httpx.RequestError as exc:
                if attempt >= self._max_retries:
                    raise AusTenderError(f"request error for {path}: {exc}") from exc
                await self._backoff_pause(attempt, retry_after=None)
                attempt += 1
                logger.warning(
                    "request error, retrying",
                    extra={"path": path, "attempt": attempt, "error": str(exc)},
                )
                continue

            logger.info(
                "request",
                extra={
                    "path": path,
                    "params": params,
                    "status": response.status_code,
                    "bytes": len(response.content),
                    "duration_ms": duration_ms,
                    "attempt": attempt,
                },
            )

            if response.status_code in _RETRYABLE_STATUS:
                if attempt >= self._max_retries:
                    raise AusTenderError(
                        f"{path} failed with {response.status_code} after {attempt} retries"
                    )
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                await self._backoff_pause(attempt, retry_after)
                attempt += 1
                continue

            # The API returns 400 (errorCode 100, "No Records found") for any window
            # with zero releases — e.g. weekends and public holidays. That is a normal
            # empty result, not an error, so return it and let the caller see no
            # releases. The body is still archived for audit by the caller.
            if _is_no_records(response):
                logger.info("empty window (no records)", extra={"path": path})
                return response

            response.raise_for_status()
            return response

    async def _politeness_pause(self) -> None:
        if self._politeness_delay_ms > 0:
            await asyncio.sleep(self._politeness_delay_ms / 1000)

    async def _backoff_pause(self, attempt: int, retry_after: float | None) -> None:
        if retry_after is not None:
            delay = retry_after
        else:
            # Exponential backoff: 0.5s, 1s, 2s, 4s, ... capped at 30s.
            delay = min(0.5 * (2 ** attempt), 30.0)
        await asyncio.sleep(delay)


def _is_no_records(response: httpx.Response) -> bool:
    """True if a 400 is the API's "no records for date range" empty-window signal."""
    if response.status_code != 400:
        return False
    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError):
        return False
    return body.get("errorCode") == 100 or "No Records found" in (body.get("message") or "")


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header. Supports delta-seconds; ignores HTTP-date."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None  # HTTP-date form not handled; fall back to exponential backoff


async def _main() -> None:
    import argparse

    from app.core.logging import configure_logging

    configure_logging()
    parser = argparse.ArgumentParser(description="Fetch and archive an AusTender date window.")
    parser.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD (exclusive)")
    parser.add_argument("--date-type", default="contractPublished")
    args = parser.parse_args()

    count = 0
    async with AusTenderClient() as client:
        async for _release in client.fetch_releases(
            args.date_from, args.date_to, date_type=args.date_type
        ):
            count += 1
    print(f"Fetched and archived {count} releases from {args.date_from} to {args.date_to}.")


if __name__ == "__main__":
    asyncio.run(_main())
