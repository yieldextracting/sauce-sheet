"""ESPN public JSON (site.api.espn.com). Primary source for schedule, scores and box scores.

Verified reachable 2026-10-20. nba.com (cdn + stats) returns 403 from the maintainer's IP, so we
do not depend on it. Sportsbook links that ESPN embeds are never read or stored.
"""

from __future__ import annotations

from typing import Any

from ..et import et_date, parse_utc, to_utc_iso, yyyymmdd
from ..teams import norm_abbr
from .http import get_json

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
CORE = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
SRC = "espn"

REGULAR_SEASON = 2


def teams() -> list[dict]:
    d = get_json(f"{BASE}/teams", source=SRC)
    out = []
    for x in d["sports"][0]["leagues"][0]["teams"]:
        t = x["team"]
        out.append({
            "abbr": norm_abbr(t["abbreviation"]),
            "espnId": t["id"],
            "name": t["displayName"],
            "shortName": t["shortDisplayName"],
            "color": t.get("color", "777777").lower(),
            "altColor": t.get("alternateColor", "cccccc").lower(),
        })
    return sorted(out, key=lambda t: t["abbr"])


def team_schedule(espn_team_id: str, espn_season_year: int, *, log: bool = True) -> list[dict]:
    d = get_json(f"{BASE}/teams/{espn_team_id}/schedule",
                 {"season": espn_season_year, "seasontype": REGULAR_SEASON}, source=SRC, log=log)
    return d.get("events", [])


def scoreboard(day_et: str) -> dict:
    return get_json(f"{BASE}/scoreboard", {"dates": yyyymmdd(day_et), "limit": 100}, source=SRC)


def summary(espn_event_id: str, *, log: bool = True) -> dict:
    return get_json(f"{BASE}/summary", {"event": espn_event_id}, source=SRC, log=log)


# ---------- parsing ----------

def _status(status_type: dict) -> str:
    name = status_type.get("name", "")
    if name == "STATUS_POSTPONED":
        return "postponed"
    if name in ("STATUS_CANCELED", "STATUS_CANCELLED"):
        return "cancelled"
    if status_type.get("completed"):
        return "final"
    if status_type.get("state") == "in":
        return "live"
    return "scheduled"


def venue_key(venue: dict | None) -> str | None:
    if not venue:
        return None
    a = venue.get("address") or {}
    city = a.get("city")
    region = a.get("state") or a.get("country")
    if not city:
        return None
    return f"{city}, {region}" if region else city


def game_id(day_et: str, away: str, home: str) -> str:
    return f"{yyyymmdd(day_et)}-{away}-{home}"


def parse_event(e: dict, season: str) -> dict:
    """ESPN schedule/scoreboard event -> our Game dict."""
    c = e["competitions"][0]
    tip = to_utc_iso(parse_utc(e["date"]))
    day = et_date(tip)
    teams = {x["homeAway"]: norm_abbr(x["team"]["abbreviation"]) for x in c["competitors"]}
    venue = c.get("venue") or {}
    return {
        "id": game_id(day, teams["away"], teams["home"]),
        "season": season,
        "etDate": day,
        "tipUtc": tip,
        "away": teams["away"],
        "home": teams["home"],
        "espnId": str(e["id"]),
        "oddsEventId": None,
        "status": _status(c.get("status", {}).get("type", {})),
        "neutralSite": bool(c.get("neutralSite", False)),
        "venue": venue.get("fullName"),
        "venueKey": venue_key(venue),
    }


def _split(made_att: str) -> tuple[int, int]:
    m, a = made_att.split("-")
    return int(m), int(a)


def _team_box(stats: list[dict]) -> dict:
    s = {x["name"]: x["displayValue"] for x in stats}
    fgm, fga = _split(s["fieldGoalsMade-fieldGoalsAttempted"])
    fg3m, fg3a = _split(s["threePointFieldGoalsMade-threePointFieldGoalsAttempted"])
    ftm, fta = _split(s["freeThrowsMade-freeThrowsAttempted"])
    return {
        "fgm": fgm, "fga": fga, "fg3m": fg3m, "fg3a": fg3a, "ftm": ftm, "fta": fta,
        "oreb": int(s["offensiveRebounds"]), "dreb": int(s["defensiveRebounds"]),
        "ast": int(s["assists"]), "stl": int(s["steals"]), "blk": int(s["blocks"]),
        "tov": int(s.get("totalTurnovers", s["turnovers"])), "pf": int(s["fouls"]),
    }


def _player_rows(group: dict, team: str) -> list[dict]:
    out = []
    for block in group["statistics"]:
        keys = block["keys"]
        for a in block["athletes"]:
            ath = a["athlete"]
            name = ath.get("displayName") or ath.get("fullName") or ath.get("shortName") or f"#{ath.get('id')}"
            base = {"name": name, "espnId": str(ath.get("id", "")), "team": team,
                    "starter": bool(a.get("starter")), "dnp": bool(a.get("didNotPlay")) or not a.get("stats"),
                    "dnpReason": a.get("reason") if a.get("didNotPlay") else None}
            if base["dnp"]:
                out.append({**base, "min": 0, "pts": 0, "reb": 0, "ast": 0, "fg3m": 0, "fgm": 0, "fga": 0,
                            "fg3a": 0, "ftm": 0, "fta": 0, "oreb": 0, "dreb": 0, "stl": 0, "blk": 0,
                            "tov": 0, "pf": 0, "pm": 0})
                continue
            v = dict(zip(keys, a["stats"]))
            fgm, fga = _split(v["fieldGoalsMade-fieldGoalsAttempted"])
            fg3m, fg3a = _split(v["threePointFieldGoalsMade-threePointFieldGoalsAttempted"])
            ftm, fta = _split(v["freeThrowsMade-freeThrowsAttempted"])
            mins = v.get("minutes") or "0"
            out.append({**base, "min": int(mins) if mins.isdigit() else 0, "pts": int(v["points"]),
                        "reb": int(v["rebounds"]), "ast": int(v["assists"]), "fg3m": fg3m, "fgm": fgm,
                        "fga": fga, "fg3a": fg3a, "ftm": ftm, "fta": fta,
                        "oreb": int(v["offensiveRebounds"]), "dreb": int(v["defensiveRebounds"]),
                        "stl": int(v["steals"]), "blk": int(v["blocks"]), "tov": int(v["turnovers"]),
                        "pf": int(v["fouls"]), "pm": int(v["plusMinus"].replace("+", "") or 0)})
    return out


def parse_summary(d: dict, gid: str, finalized_at: str) -> dict:
    """ESPN summary -> our Result dict (final score, team box, player box)."""
    comp = d["header"]["competitions"][0]
    status = _status(comp["status"]["type"])
    by_side: dict[str, dict] = {}
    for c in comp["competitors"]:
        by_side[c["homeAway"]] = {"abbr": norm_abbr(c["team"]["abbreviation"]),
                                  "pts": int(c["score"]) if c.get("score") not in (None, "") else None,
                                  "periods": len(c.get("linescores") or [])}
    result: dict[str, Any] = {
        "gameId": gid,
        "status": status if status in ("final", "postponed", "cancelled") else "pending",
        "awayPts": by_side["away"]["pts"] if status == "final" else None,
        "homePts": by_side["home"]["pts"] if status == "final" else None,
        "periods": max(by_side["away"]["periods"], by_side["home"]["periods"]) if status == "final" else None,
        "finalizedAt": finalized_at,
        "box": None,
        "players": [],
    }
    if status != "final":
        return result
    box = d.get("boxscore") or {}
    teams_box = {}
    for t in box.get("teams", []):
        teams_box[t["homeAway"]] = _team_box(t["statistics"])
    if set(teams_box) == {"home", "away"}:
        result["box"] = teams_box
    players = []
    for g in box.get("players", []):
        players.extend(_player_rows(g, norm_abbr(g["team"]["abbreviation"])))
    result["players"] = players
    return result
