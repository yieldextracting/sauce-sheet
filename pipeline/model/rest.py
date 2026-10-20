"""Schedule-spot features, computed on ET game dates.

For each (game, team): rest days since the previous game, back-to-back, 3-in-4,
travel distance from the previous game's venue, and whether the venue is at altitude.
"""

from __future__ import annotations

from collections import defaultdict

from ..et import add_days, days_between
from ..sources.geo import haversine_km

REST_CAP = 3  # "3+ days" is treated the same as 3


def rest_features(games: list[dict], venues: dict[str, dict], altitude_m: float) -> dict[tuple[str, str], dict]:
    played = [g for g in games if g["status"] not in ("postponed", "cancelled")]
    played.sort(key=lambda g: g["tipUtc"])
    by_team: dict[str, list[dict]] = defaultdict(list)
    for g in played:
        by_team[g["home"]].append(g)
        by_team[g["away"]].append(g)

    out: dict[tuple[str, str], dict] = {}
    for team, tg in by_team.items():
        for i, g in enumerate(tg):
            prev = tg[i - 1] if i > 0 else None
            rest = days_between(prev["etDate"], g["etDate"]) - 1 if prev else None
            window_start = add_days(g["etDate"], -3)
            n_in_4 = sum(1 for x in tg[max(0, i - 3):i + 1] if x["etDate"] >= window_start)
            here = venues.get(g.get("venueKey") or "")
            there = venues.get(prev.get("venueKey") or "") if prev else None
            travel = haversine_km(there, here) if (here and there) else 0.0
            out[(g["id"], team)] = {
                "restDays": rest,
                "b2b": rest == 0,
                "threeInFour": n_in_4 >= 3,
                "travelKm": round(travel, 1),
                "atAltitude": bool(here and here["elevationM"] >= altitude_m),
            }
    return out


def flags_for(game: dict, rf: dict[tuple[str, str], dict], long_travel_km: float = 1500.0) -> list[str]:
    flags: list[str] = []
    for side in ("away", "home"):
        f = rf.get((game["id"], game[side]))
        if not f:
            continue
        if f["b2b"]:
            flags.append(f"b2b_{side}")
        if f["threeInFour"]:
            flags.append(f"3in4_{side}")
        if f["travelKm"] >= long_travel_km:
            flags.append(f"long_travel_{side}")
    h = rf.get((game["id"], game["home"]))
    if h and h["atAltitude"] and not game.get("neutralSite"):
        flags.append("altitude")
    return flags
