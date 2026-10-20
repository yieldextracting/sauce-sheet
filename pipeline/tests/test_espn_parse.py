"""Parser test on a recorded ESPN box score: HOU at OKC, 2025-10-21 (OKC won 125-124 in 2OT)."""

import json
from pathlib import Path

from pipeline.model.ratings import team_poss
from pipeline.sources.espn import parse_summary

FIX = Path(__file__).parent / "fixtures" / "espn_summary_20251021-HOU-OKC.json"


def test_parse_final_box_score():
    r = parse_summary(json.loads(FIX.read_text()), "20251021-HOU-OKC", "2026-10-20T00:00:00Z")
    assert r["status"] == "final"
    assert (r["awayPts"], r["homePts"]) == (124, 125)
    assert r["periods"] == 6  # double overtime
    assert set(r["box"]) == {"home", "away"}
    assert 90 < team_poss(r["box"]["home"]) < 140
    teams = {p["team"] for p in r["players"]}
    assert teams == {"HOU", "OKC"}
    played = [p for p in r["players"] if not p["dnp"]]
    for side, abbr in (("home", "OKC"), ("away", "HOU")):
        assert sum(p["pts"] for p in played if p["team"] == abbr) == r[f"{side}Pts"]
    assert all(p["min"] == 0 for p in r["players"] if p["dnp"])
