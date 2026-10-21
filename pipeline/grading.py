"""Grading rules. Pure functions, unit-tested in tests/test_grading.py.

Units are amount RISKED. A win at -110 pays 100/110 = +0.909u per unit, a loss is -1u, a push is 0.
Postponed, cancelled, or rescheduled-to-another-day games are void (0). DNP props are void.
"""

from __future__ import annotations

from typing import Literal

Outcome = Literal["win", "loss", "push", "void", "pending"]


def win_profit(price: int) -> float:
    """Profit per 1 unit risked at an American price."""
    if -100 < price < 100:
        raise ValueError(f"invalid American price {price}")
    return 100.0 / -price if price < 0 else price / 100.0


def profit(outcome: Outcome, price: int, units: float) -> float:
    if outcome == "win":
        return units * win_profit(price)
    if outcome == "loss":
        return -units
    return 0.0


def _cmp(x: float) -> Outcome:
    if x > 0:
        return "win"
    if x < 0:
        return "loss"
    return "push"


def spread_outcome(side_is_home: bool, line: float, home_pts: int, away_pts: int) -> Outcome:
    """`line` is from the picked side's perspective (e.g. -3.5 for a 3.5-pt favourite)."""
    diff = (home_pts - away_pts) if side_is_home else (away_pts - home_pts)
    return _cmp(diff + line)


def total_outcome(over: bool, line: float, home_pts: int, away_pts: int) -> Outcome:
    t = home_pts + away_pts
    return _cmp(t - line) if over else _cmp(line - t)


def moneyline_outcome(side_is_home: bool, home_pts: int, away_pts: int) -> Outcome:
    if home_pts == away_pts:  # cannot happen in the NBA; treat defensively as push
        return "push"
    home_won = home_pts > away_pts
    return "win" if home_won == side_is_home else "loss"


def prop_outcome(over: bool, line: float, value: float | None, dnp: bool) -> Outcome:
    if dnp or value is None:
        return "void"
    return _cmp(value - line) if over else _cmp(line - value)


def game_state(result: dict | None, original_et_date: str, played_et_date: str | None) -> Outcome | None:
    """Return 'void'/'pending' when the game itself decides it, else None (gradeable)."""
    if result is None or result.get("status") == "pending":
        return "pending"
    if result["status"] in ("postponed", "cancelled"):
        return "void"
    if played_et_date and played_et_date != original_et_date:
        return "void"  # rescheduled to another game day: books void, so do we
    return None


def clv_points(market: str, side: str, pick_line: float, closing_line: float) -> float:
    """Points of closing line value. Positive = you beat the close.

    spread: both lines from the picked side's perspective. total: side is 'over' or 'under'.
    """
    if market == "spread":
        return pick_line - closing_line
    if market == "total":
        return closing_line - pick_line if side == "over" else pick_line - closing_line
    raise ValueError(market)


def implied_prob(price: int) -> float:
    return -price / (-price + 100.0) if price < 0 else 100.0 / (price + 100.0)


def clv_prob(pick_price: int, close_side: int, close_other: int) -> float:
    """Moneyline CLV in win probability: no-vig closing probability minus the pick's implied probability."""
    a, b = implied_prob(close_side), implied_prob(close_other)
    return a / (a + b) - implied_prob(pick_price)
