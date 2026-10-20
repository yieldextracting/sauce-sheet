"""Provider-agnostic odds types. Swap providers by implementing OddsProvider."""

from __future__ import annotations

import statistics
from typing import Protocol


class OddsProvider(Protocol):
    name: str

    def featured(self, games: list[dict]) -> list[dict]:
        """Return GameLines dicts (spreads/totals/moneylines, every book) for the given games.

        Only games that have not tipped should be passed in.
        """
        ...


def round_half(x: float) -> float:
    """Round to the nearest 0.5 (ties away from zero) so consensus lines are bettable numbers."""
    sign = -1 if x < 0 else 1
    return sign * (int(abs(x) * 2 + 0.5) / 2)


def consensus(books: list[dict]) -> dict:
    spreads = [b["spreadHome"] for b in books if b.get("spreadHome") is not None]
    totals = [b["total"] for b in books if b.get("total") is not None]
    return {
        "spreadHome": round_half(statistics.median(spreads)) if spreads else None,
        "total": round_half(statistics.median(totals)) if totals else None,
        "nBooks": len(books),
    }


def parse_american(s: str | int | None) -> int | None:
    if s is None:
        return None
    if isinstance(s, int):
        return s
    s = s.strip().upper()
    if s in ("", "-", "OFF", "N/A"):
        return None
    if s == "EVEN":
        return 100
    return int(s.replace("+", ""))


def parse_line(s: str | float | None) -> float | None:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = s.strip().lower().lstrip("ou")
    if s in ("pk", "pick", "even"):
        return 0.0
    if s in ("", "-", "off"):
        return None
    return float(s)


def empty_book(book: str, last_update: str) -> dict:
    return {"book": book, "spreadHome": None, "spreadHomePrice": None, "spreadAwayPrice": None,
            "total": None, "overPrice": None, "underPrice": None, "mlHome": None, "mlAway": None,
            "lastUpdate": last_update}
