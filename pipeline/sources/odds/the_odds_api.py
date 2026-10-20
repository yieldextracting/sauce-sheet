"""The Odds API v4 (https://the-odds-api.com/liveapi/guides/v4/).

Cost (verified in docs 2026-10-20): /odds = markets x regions per call, covering every game.
/sports and /events are free. Quota headers: x-requests-remaining / -used / -last.
"""

from __future__ import annotations

from ...config import OddsConfig
from ...et import et_date, parse_utc, to_utc_iso
from ...paths import CREDIT_LOG
from ..http import get
from .base import consensus, empty_book
from .budget import BudgetGuard

BASE = "https://api.the-odds-api.com/v4"


class TheOddsApi:
    name = "the-odds-api"

    def __init__(self, api_key: str, cfg: OddsConfig, team_names: dict[str, str]):
        self.key = api_key
        self.cfg = cfg
        self.names = team_names  # full name -> abbr
        self.guard = BudgetGuard(cfg.budget, CREDIT_LOG)

    def featured(self, games: list[dict]) -> list[dict]:
        markets = self.cfg.featuredMarkets
        est = len(markets) * len(self.cfg.regions)
        endpoint = f"/sports/{self.cfg.sport}/odds"
        self.guard.check(est, endpoint)
        r = get(f"{BASE}{endpoint}", {
            "apiKey": self.key, "regions": ",".join(self.cfg.regions), "markets": ",".join(markets),
            "oddsFormat": "american", "dateFormat": "iso"}, source="the-odds-api")
        self.guard.record(endpoint, dict(r.headers))
        by_key = {(g["etDate"], g["away"], g["home"]): g for g in games}
        out = []
        for ev in r.json():
            home = self.names.get(ev["home_team"])
            away = self.names.get(ev["away_team"])
            day = et_date(to_utc_iso(parse_utc(ev["commence_time"])))
            g = by_key.get((day, away, home))
            if g is None:
                continue
            books = [self._book(b, ev["home_team"], ev["away_team"]) for b in ev.get("bookmakers", [])]
            books = [b for b in books if b["spreadHome"] is not None or b["total"] is not None]
            if not books:
                continue
            out.append({"gameId": g["id"], "oddsEventId": ev["id"], "books": books,
                        "consensus": consensus(books)})
        return out

    @staticmethod
    def _book(b: dict, home_name: str, away_name: str) -> dict:
        row = empty_book(b["title"], to_utc_iso(parse_utc(b["last_update"])))
        for m in b.get("markets", []):
            oc = {o["name"]: o for o in m.get("outcomes", [])}
            if m["key"] == "spreads" and home_name in oc and away_name in oc:
                row["spreadHome"] = float(oc[home_name]["point"])
                row["spreadHomePrice"] = int(oc[home_name]["price"])
                row["spreadAwayPrice"] = int(oc[away_name]["price"])
            elif m["key"] == "totals" and "Over" in oc and "Under" in oc:
                row["total"] = float(oc["Over"]["point"])
                row["overPrice"] = int(oc["Over"]["price"])
                row["underPrice"] = int(oc["Under"]["price"])
            elif m["key"] == "h2h" and home_name in oc and away_name in oc:
                row["mlHome"] = int(oc[home_name]["price"])
                row["mlAway"] = int(oc[away_name]["price"])
        return row
