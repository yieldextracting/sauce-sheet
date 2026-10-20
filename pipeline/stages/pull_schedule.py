"""Refresh teams and the current season schedule from ESPN.

Game IDs are stable: once a game (by ESPN id) has an ID, a reschedule changes its etDate/tipUtc
but never its ID, so locked lines and picks keep pointing at it.
"""

from __future__ import annotations

from .. import config, store
from ..et import now_utc, to_utc_iso
from ..io import write_json
from ..paths import TEAMS, schedule_path
from ..sources import espn, geo
from .backfill import season_games


def run() -> None:
    site = config.site()
    teams = espn.teams()
    write_json(TEAMS, teams)
    fresh = season_games(site.espnSeasonYear, site.season, teams, log=True)
    existing = {g["espnId"]: g for g in store.schedule()}
    games = []
    for g in fresh:
        old = existing.get(g["espnId"])
        if old and old["id"] != g["id"]:
            g = {**g, "id": old["id"], "rescheduledFrom": old.get("rescheduledFrom") or old["etDate"]}
        games.append(g)
    # keep games ESPN dropped (e.g. cancelled) so locked picks still resolve
    fresh_ids = {g["espnId"] for g in games}
    for espn_id, old in existing.items():
        if espn_id not in fresh_ids:
            games.append({**old, "status": "cancelled" if old["status"] != "final" else "final"})
    games.sort(key=lambda g: (g["tipUtc"], g["id"]))
    geo.ensure({g["venueKey"] for g in games if g.get("venueKey")})
    write_json(schedule_path(site.season), {"season": site.season, "pulledAt": to_utc_iso(now_utc()),
                                            "source": "ESPN site API", "games": games})
    print(f"schedule: {len(games)} games")
