"""Parser test on a real official injury report (2026-10-20 07:45 PM ET, 5 pages)."""

import re
from collections import Counter
from pathlib import Path

from pipeline.sources.injury_report import norm_name, parse_official_pdf

FIX = Path(__file__).parent / "fixtures" / "injury_report_sample.pdf"
TEAMS = {"Boston Celtics": "BOS", "Detroit Pistons": "DET", "Philadelphia 76ers": "PHI", "New York Knicks": "NYK",
         "Oklahoma City Thunder": "OKC", "San Antonio Spurs": "SAS", "Atlanta Hawks": "ATL", "Orlando Magic": "ORL",
         "Milwaukee Bucks": "MIL", "Washington Wizards": "WAS", "Charlotte Hornets": "CHA", "Brooklyn Nets": "BKN",
         "Chicago Bulls": "CHI", "Toronto Raptors": "TOR", "Dallas Mavericks": "DAL", "Houston Rockets": "HOU",
         "Golden State Warriors": "GSW", "Los Angeles Lakers": "LAL", "Indiana Pacers": "IND",
         "New Orleans Pelicans": "NOP", "Minnesota Timberwolves": "MIN", "Miami Heat": "MIA", "Phoenix Suns": "PHX",
         "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "LA Clippers": "LAC", "Utah Jazz": "UTA",
         "Memphis Grizzlies": "MEM"}
IDX = {re.sub(r"[^a-z0-9]", "", k.lower()): v for k, v in TEAMS.items()}


def rows():
    return parse_official_pdf(FIX.read_bytes(), IDX)


def test_parses_every_page_and_status():
    r = rows()
    assert len(r) == 78
    assert Counter(x["status"] for x in r) == {"out": 52, "questionable": 10, "probable": 8, "available": 4, "doubtful": 4}


def test_team_always_in_matchup():
    for x in rows():
        assert x["team"] in x["matchup"].split("@"), x


def test_known_rows_and_wrapped_reasons():
    by = {(x["team"], x["player"]): x for x in rows()}
    assert by[("BOS", "Devin Carter")]["status"] == "out"
    assert by[("PHI", "Ariel Hukporti")]["reason"] == "Injury/Illness - Right Achilles Tendon Rupture / Tear"
    assert by[("PHI", "Dominick Barlow")]["reason"] == "Injury/Illness - Low Back Stress Reaction"
    assert by[("SAC", "Malik Monk")]["status"] == "questionable"
    assert "SUBMITTED" not in (by[("SAC", "Ben Simmons")]["reason"] or "")


def test_name_keys_match_across_sources():
    assert norm_name("Carter,Devin") == norm_name("Devin Carter")
    assert norm_name("Jackson Jr.,Jaren") == norm_name("Jaren Jackson Jr.")
    assert norm_name("VanVleet,Fred") == norm_name("Fred VanVleet")
