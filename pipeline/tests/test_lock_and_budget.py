import json

import pytest

from pipeline.config import Budget
from pipeline.io import ImmutableFileError, write_once
from pipeline.sources.odds.base import consensus, parse_american, parse_line, round_half
from pipeline.sources.odds.budget import BudgetExceeded, BudgetGuard
from pipeline.stages.lock import model_pick


def lines(spread, total=220.5):
    return {"consensus": {"spreadHome": spread, "total": total}}


def test_model_pick_sides_and_edge_sign():
    # market home -3, model home -5 -> model likes home more -> home -3, edge -2
    p = model_pick("20261020-BOS-DET", lines(-3), {"spreadHome": -5.0, "total": 221.0}, "2026-10-20T14:00:00Z")
    assert (p["side"], p["line"], p["edge"]) == ("home", -3, -2.0)
    # market home -3, model home -1 -> away +3
    p = model_pick("x", lines(-3), {"spreadHome": -1.0, "total": 221.0}, "t")
    assert (p["side"], p["line"], p["edge"]) == ("away", 3, 2.0)
    p = model_pick("x", lines(-3), {"spreadHome": -3.0, "total": 221.0}, "t")
    assert p["side"] == "none"


def test_model_pick_without_projection_is_none_not_backfilled():
    p = model_pick("x", lines(-3), None, "t")
    assert p["side"] == "none" and p["reason"] == "no projection at lock"


def test_first_seen_is_write_once(tmp_path):
    path = tmp_path / "first-seen" / "g.json"
    write_once(path, {"consensus": {"spreadHome": -3}})
    with pytest.raises(ImmutableFileError):
        write_once(path, {"consensus": {"spreadHome": -4}})
    assert json.loads(path.read_text())["consensus"]["spreadHome"] == -3


def test_consensus_median_rounded_to_half():
    books = [{"spreadHome": -3.0, "total": 220.0}, {"spreadHome": -3.5, "total": 221.0},
             {"spreadHome": -4.0, "total": 221.5}, {"spreadHome": -3.5, "total": 220.5}]
    c = consensus(books)
    assert c["spreadHome"] == -3.5 and c["total"] == 221.0 and c["nBooks"] == 4
    assert round_half(-3.25) == -3.5 and round_half(3.25) == 3.5 and round_half(3.2) == 3.0


def test_parsers():
    assert parse_american("+102") == 102 and parse_american("-110") == -110 and parse_american("EVEN") == 100
    assert parse_line("+1.5") == 1.5 and parse_line("o219.5") == 219.5 and parse_line("u219.5") == 219.5
    assert parse_line("PK") == 0.0


def _guard(tmp_path, rows):
    log = tmp_path / "credits.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return BudgetGuard(Budget(monthlyCap=15000, reserve=1500, dailyCap=250), log)


def test_budget_allows_normal_call(tmp_path):
    _guard(tmp_path, [{"at": "2020-01-01T00:00:00Z", "endpoint": "x", "cost": 3, "remaining": 19000, "used": 1000}]).check(3, "x")


def test_budget_stops_at_reserve(tmp_path):
    g = _guard(tmp_path, [{"at": "2020-01-01T00:00:00Z", "endpoint": "x", "cost": 3, "remaining": 1501, "used": 18499}])
    with pytest.raises(BudgetExceeded):
        g.check(3, "x")


def test_budget_stops_at_monthly_cap(tmp_path):
    g = _guard(tmp_path, [{"at": "2020-01-01T00:00:00Z", "endpoint": "x", "cost": 3, "remaining": 5000, "used": 14999}])
    with pytest.raises(BudgetExceeded):
        g.check(3, "x")


def test_budget_stops_at_daily_cap(tmp_path):
    from pipeline.et import now_utc, to_utc_iso
    now = to_utc_iso(now_utc())
    g = _guard(tmp_path, [{"at": now, "endpoint": "x", "cost": 249, "remaining": 18000, "used": 2000}])
    with pytest.raises(BudgetExceeded):
        g.check(3, "x")
