"""Fetch final scores + box scores for games that should be over."""

from __future__ import annotations

from datetime import timedelta

from .. import store
from ..et import now_utc, parse_utc, to_utc_iso
from ..io import write_json
from ..paths import results_dir, schedule_path
from ..sources import espn

# A regulation NBA game takes ~2h15m. Check after that, keep checking until final.
CHECK_AFTER = timedelta(hours=2, minutes=15)


def pending_games(now=None) -> list[dict]:
    now = now or now_utc()
    have = store.results()
    out = []
    for g in store.schedule():
        if g["status"] in ("postponed", "cancelled"):
            continue
        if parse_utc(g["tipUtc"]) + CHECK_AFTER > now:
            continue
        r = have.get(g["id"])
        if r and r["status"] == "final":
            continue
        out.append(g)
    return out


def run() -> int:
    now = now_utc()
    todo = pending_games(now)
    sched_changed = False
    games = store.schedule()
    by_id = {g["id"]: g for g in games}
    new_finals = 0
    for g in todo:
        res = espn.parse_summary(espn.summary(g["espnId"]), g["id"], to_utc_iso(now))
        if res["status"] == "final":
            write_json(results_dir(store.season()) / f"{g['id']}.json", res)
            new_finals += 1
        if res["status"] in ("final", "postponed", "cancelled") and by_id[g["id"]]["status"] != res["status"]:
            by_id[g["id"]]["status"] = res["status"]
            sched_changed = True
    if sched_changed:
        from ..io import read_json
        d = read_json(schedule_path(store.season()))
        d["games"] = games
        write_json(schedule_path(store.season()), d)
    print(f"results: checked {len(todo)}, new finals {new_finals}")
    return new_finals
