"""Backfill past seasons from ESPN into data/history/{season}/ (run once, locally).

~1,230 box scores per season. Network-bound and polite (3 workers). Resumable via a local
.cache/ folder that is git-ignored. Only compact extracts are committed.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from .. import config
from ..et import now_utc, to_utc_iso
from ..io import read_json, write_json, write_table
from ..paths import HISTORY_DIR, TEAMS
from ..sources import espn, geo

WORKERS = 3


def season_games(espn_year: int, season: str, teams: list[dict], log: bool = False) -> list[dict]:
    seen: dict[str, dict] = {}
    for t in teams:
        for e in espn.team_schedule(t["espnId"], espn_year, log=log):
            if str(e["id"]) not in seen:
                seen[str(e["id"])] = espn.parse_event(e, season)
    return sorted(seen.values(), key=lambda g: (g["tipUtc"], g["id"]))


def run(espn_years: list[int]) -> None:
    teams = read_json(TEAMS) or espn.teams()
    if not TEAMS.exists():
        write_json(TEAMS, teams)
    for year in espn_years:
        season = config.season_label(year)
        out_dir = HISTORY_DIR / season
        cache = out_dir / ".cache"
        cache.mkdir(parents=True, exist_ok=True)
        games = season_games(year, season, teams)
        geo.ensure({g["venueKey"] for g in games if g["venueKey"]})
        finals = [g for g in games if g["status"] == "final"]
        print(f"{season}: {len(games)} games, {len(finals)} final", flush=True)

        def fetch(g: dict) -> None:
            p = cache / f"{g['espnId']}.json"
            if p.exists():
                return
            res = espn.parse_summary(espn.summary(g["espnId"], log=False), g["id"], to_utc_iso(now_utc()))
            p.write_text(json.dumps(res))

        done, failed = 0, []
        with ThreadPoolExecutor(WORKERS) as ex:
            futs = {ex.submit(fetch, g): g for g in finals}
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception as e:  # report, don't abort the season
                    failed.append(f"{futs[f]['id']} ({futs[f]['espnId']}): {type(e).__name__}: {e}")
                done += 1
                if done % 100 == 0:
                    print(f"  {season}: {done}/{len(finals)}", flush=True)

        if failed:
            print(f"  {season}: {len(failed)} games FAILED and are excluded:", *failed, sep="\n    ", flush=True)

        records, players = [], []
        for g in games:
            p = cache / f"{g['espnId']}.json"
            res = json.loads(p.read_text()) if p.exists() else None
            if res:
                players.extend({"gameId": g["id"], **pl} for pl in res.pop("players"))
            records.append({"game": g, "result": res})
        write_json(out_dir / "games.json", {"season": season, "builtAt": to_utc_iso(now_utc()),
                                             "source": "ESPN site API", "records": records})
        cols = list(players[0].keys()) if players else []
        write_table(out_dir / "players.json", {"season": season}, cols, [[p[c] for c in cols] for p in players])
        print(f"{season}: wrote {len(records)} games, {len(players)} player rows", flush=True)
