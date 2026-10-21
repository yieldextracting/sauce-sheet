import pytest

from pipeline.grading import (clv_points, clv_prob, implied_prob, game_state, moneyline_outcome, profit, prop_outcome,
                              spread_outcome, total_outcome, win_profit)


def test_minus_110_payouts():
    assert round(profit("win", -110, 1), 3) == 0.909
    assert profit("loss", -110, 1) == -1
    assert profit("push", -110, 1) == 0
    assert profit("void", -110, 1) == 0


def test_plus_and_minus_prices():
    assert win_profit(150) == 1.5
    assert win_profit(-200) == 0.5
    assert win_profit(100) == 1.0
    assert profit("win", -150, 2) == pytest.approx(1.3333, abs=1e-4)
    with pytest.raises(ValueError):
        win_profit(-99)


def test_half_point_spreads_never_push():
    # home -3.5, wins by 4 -> win; wins by 3 -> loss
    assert spread_outcome(True, -3.5, 110, 106) == "win"
    assert spread_outcome(True, -3.5, 110, 107) == "loss"
    # away +3.5, loses by 3 -> win
    assert spread_outcome(False, 3.5, 110, 107) == "win"


def test_whole_number_spreads_push():
    assert spread_outcome(True, -3, 110, 107) == "push"
    assert spread_outcome(False, 3, 110, 107) == "push"
    assert spread_outcome(True, -3, 110, 106) == "win"
    assert spread_outcome(False, 3, 110, 106) == "loss"


def test_pick_em():
    assert spread_outcome(True, 0, 100, 99) == "win"
    assert spread_outcome(False, 0, 100, 99) == "loss"


def test_totals():
    assert total_outcome(True, 220.5, 111, 110) == "win"
    assert total_outcome(True, 220.5, 110, 110) == "loss"
    assert total_outcome(False, 220.5, 110, 110) == "win"
    assert total_outcome(True, 220, 110, 110) == "push"
    assert total_outcome(False, 220, 110, 110) == "push"


def test_moneyline():
    assert moneyline_outcome(True, 101, 99) == "win"
    assert moneyline_outcome(False, 101, 99) == "loss"


def test_props_and_dnp_void():
    assert prop_outcome(True, 24.5, 25, False) == "win"
    assert prop_outcome(False, 24.5, 25, False) == "loss"
    assert prop_outcome(True, 25, 25, False) == "push"
    assert prop_outcome(True, 24.5, None, True) == "void"
    assert prop_outcome(True, 24.5, 0, True) == "void"


def test_game_state_void_and_pending():
    assert game_state(None, "2026-11-01", None) == "pending"
    assert game_state({"status": "pending"}, "2026-11-01", None) == "pending"
    assert game_state({"status": "postponed"}, "2026-11-01", None) == "void"
    assert game_state({"status": "cancelled"}, "2026-11-01", None) == "void"
    assert game_state({"status": "final"}, "2026-11-01", "2026-11-03") == "void"
    assert game_state({"status": "final"}, "2026-11-01", "2026-11-01") is None


def test_clv():
    # took -3.5, closed -4.5: beat the close by a point
    assert clv_points("spread", "home", -3.5, -4.5) == 1.0
    # took +5, closed +3.5: beat the close by 1.5
    assert clv_points("spread", "away", 5, 3.5) == 1.5
    assert clv_points("total", "over", 220, 222) == 2
    assert clv_points("total", "under", 220, 222) == -2


def test_moneyline_clv_in_probability():
    assert round(implied_prob(-110), 4) == 0.5238
    assert implied_prob(100) == 0.5
    # took +120 (45.5%), close -130/+110 -> no-vig 54.3% for our side: +8.8 points of probability
    assert round(clv_prob(120, -130, 110), 3) == 0.088
    assert clv_prob(-200, 150, -170) < 0
