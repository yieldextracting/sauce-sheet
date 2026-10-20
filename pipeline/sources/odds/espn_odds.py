"""Fallback odds provider: the single book ESPN shows on its scoreboard (free, no key).

Used when ODDS_API_KEY is not set. It is one book, not a consensus, and snapshots say so.
ESPN's "close" field is the current pre-game number until tip. Live-odds providers are skipped,
and ESPN's embedded sportsbook links are never read.
"""

from __future__ import annotations

from ...et import now_utc, to_utc_iso
from .. import espn
from .base import consensus, empty_book, parse_american, parse_line


class EspnOdds:
    name = "espn"

    def featured(self, games: list[dict]) -> list[dict]:
        wanted = {g["espnId"]: g for g in games}
        out = []
        for day in sorted({g["etDate"] for g in games}):
            sb = espn.scoreboard(day)
            for ev in sb.get("events", []):
                g = wanted.get(str(ev["id"]))
                if g is None:
                    continue
                books = []
                for o in ev["competitions"][0].get("odds") or []:
                    book = self._book(o)
                    if book:
                        books.append(book)
                if books:
                    out.append({"gameId": g["id"], "oddsEventId": None, "books": books,
                                "consensus": consensus(books)})
        return out

    @staticmethod
    def _book(o: dict) -> dict | None:
        name = (o.get("provider") or {}).get("name", "ESPN")
        if "live" in name.lower():
            return None
        row = empty_book(name.replace("Draft Kings", "DraftKings"), to_utc_iso(now_utc()))
        ps = o.get("pointSpread") or {}
        home_cur = (ps.get("home") or {}).get("close") or {}
        away_cur = (ps.get("away") or {}).get("close") or {}
        row["spreadHome"] = parse_line(home_cur.get("line"))
        row["spreadHomePrice"] = parse_american(home_cur.get("odds"))
        row["spreadAwayPrice"] = parse_american(away_cur.get("odds"))
        tot = o.get("total") or {}
        over = (tot.get("over") or {}).get("close") or {}
        under = (tot.get("under") or {}).get("close") or {}
        row["total"] = parse_line(over.get("line")) if over.get("line") else (
            float(o["overUnder"]) if o.get("overUnder") is not None else None)
        row["overPrice"] = parse_american(over.get("odds"))
        row["underPrice"] = parse_american(under.get("odds"))
        ml = o.get("moneyline") or {}
        row["mlHome"] = parse_american(((ml.get("home") or {}).get("close") or {}).get("odds"))
        row["mlAway"] = parse_american(((ml.get("away") or {}).get("close") or {}).get("odds"))
        if row["spreadHome"] is None and row["total"] is None:
            return None
        return row
