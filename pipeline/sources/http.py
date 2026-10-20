"""Shared HTTP client: polite user agent, retries, and a log line for every pull."""

from __future__ import annotations

import time
from typing import Any

import httpx

from ..et import now_utc, to_utc_iso
from ..io import append_jsonl
from ..paths import PULL_LOG

UA = "SauceSheet/1.0 (+https://github.com/yieldextracting/sauce-sheet; data pipeline)"

_client: httpx.Client | None = None


def client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=30.0, headers={"User-Agent": UA}, follow_redirects=True)
    return _client


class FetchError(Exception):
    pass


def get(url: str, params: dict[str, Any] | None = None, *, source: str, log: bool = True,
        retries: int = 3, backoff: float = 2.0) -> httpx.Response:
    """GET with retries on network errors and 5xx/429. Raises FetchError on final failure."""
    last: str = ""
    for attempt in range(retries):
        try:
            r = client().get(url, params=params)
            if r.status_code == 200:
                if log:
                    _log(source, url, 200, None)
                return r
            last = f"HTTP {r.status_code}"
            if r.status_code not in (429, 500, 502, 503, 504):
                break
        except httpx.HTTPError as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(backoff * (attempt + 1))
    if log:
        _log(source, url, None, last)
    raise FetchError(f"{source}: {url} failed: {last}")


def get_json(url: str, params: dict[str, Any] | None = None, *, source: str, log: bool = True) -> Any:
    return get(url, params, source=source, log=log).json()


def _log(source: str, url: str, status: int | None, error: str | None) -> None:
    append_jsonl(PULL_LOG, {"at": to_utc_iso(now_utc()), "source": source, "url": _redact(url),
                            "ok": error is None, "status": status, "error": error})


def _redact(url: str) -> str:
    # never write API keys into the repo
    import re
    return re.sub(r"(apiKey=)[^&]+", r"\1REDACTED", url)
