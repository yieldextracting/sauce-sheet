"""US Eastern time helpers. The ONLY place the pipeline converts between UTC and ET.

Rules:
- Everything stored is UTC ("...Z").
- A game day is the ET calendar date of the scheduled tip.
- Never read the naive local clock; use now_utc().
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(UTC)


def parse_utc(s: str) -> datetime:
    """Parse an ISO timestamp (with Z or offset) into an aware UTC datetime."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"naive timestamp not allowed: {s}")
    return dt.astimezone(UTC)


def to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("naive datetime not allowed")
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_et(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("naive datetime not allowed")
    return dt.astimezone(ET)


def et_date(dt_or_iso: datetime | str) -> str:
    """ET calendar date (YYYY-MM-DD) of a UTC instant."""
    dt = parse_utc(dt_or_iso) if isinstance(dt_or_iso, str) else dt_or_iso
    return to_et(dt).date().isoformat()


def today_et(now: datetime | None = None) -> str:
    return et_date(now or now_utc())


def et_hour_minute(now: datetime | None = None) -> tuple[int, int]:
    t = to_et(now or now_utc())
    return t.hour, t.minute


def et_wall_to_utc(day: str, hour: int, minute: int = 0) -> datetime:
    """UTC instant for an ET wall-clock time on an ET date (DST-aware).

    For the repeated hour on the fall-back day, returns the first occurrence (EDT).
    """
    local = datetime.combine(date.fromisoformat(day), time(hour, minute), tzinfo=ET)
    return local.astimezone(UTC)


def add_days(day: str, n: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


def days_between(a: str, b: str) -> int:
    """b - a in days, for ET date strings."""
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def yyyymmdd(day: str) -> str:
    return day.replace("-", "")
