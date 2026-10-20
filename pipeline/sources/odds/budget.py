"""Credit budget guard for The Odds API.

Every call is logged to data/logs/odds-credits.jsonl with the quota headers the API returns.
Before a call we estimate its cost and refuse if it would breach the reserve, the daily cap or
the monthly cap. Refusal raises, so the workflow run goes red instead of silently overspending.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...config import Budget
from ...et import et_date, now_utc, to_utc_iso, today_et
from ...io import append_jsonl, read_jsonl


class BudgetExceeded(Exception):
    pass


@dataclass
class BudgetGuard:
    budget: Budget
    log_path: Path

    def _rows(self) -> list[dict]:
        return read_jsonl(self.log_path)

    def status(self) -> dict:
        rows = self._rows()
        last = rows[-1] if rows else None
        today = today_et()
        spent_today = sum(r["cost"] for r in rows if et_date(r["at"]) == today)
        return {"remaining": last["remaining"] if last else None,
                "used": last["used"] if last else None,
                "spentToday": spent_today}

    def check(self, est_cost: int, endpoint: str) -> None:
        s = self.status()
        b = self.budget
        if s["remaining"] is not None and s["remaining"] - est_cost < b.reserve:
            raise BudgetExceeded(f"{endpoint}: est {est_cost} would leave {s['remaining'] - est_cost} "
                                 f"< reserve {b.reserve}")
        if s["spentToday"] + est_cost > b.dailyCap:
            raise BudgetExceeded(f"{endpoint}: est {est_cost} + spent today {s['spentToday']} "
                                 f"> daily cap {b.dailyCap}")
        if s["used"] is not None and s["used"] + est_cost > b.monthlyCap:
            raise BudgetExceeded(f"{endpoint}: est {est_cost} + used this month {s['used']} "
                                 f"> monthly cap {b.monthlyCap}")

    def record(self, endpoint: str, headers: dict[str, str]) -> dict:
        row = {"at": to_utc_iso(now_utc()), "endpoint": endpoint,
               "cost": int(float(headers.get("x-requests-last", 0))),
               "remaining": int(float(headers.get("x-requests-remaining", 0))),
               "used": int(float(headers.get("x-requests-used", 0)))}
        append_jsonl(self.log_path, row)
        return row
