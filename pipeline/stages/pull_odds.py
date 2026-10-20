"""Take a featured-markets snapshot (spreads, totals, moneylines) for upcoming games."""

from __future__ import annotations

import os

from .. import config, store
from ..et import add_days, now_utc, parse_utc, to_utc_iso, today_et
from ..io import write_json
from ..paths import CURRENT_LINES, ROOT, SNAPSHOTS_DIR
from ..sources.odds.base import OddsProvider
from ..sources.odds.espn_odds import EspnOdds
from ..sources.odds.the_odds_api import TheOddsApi
from ..teams import name_index


def provider() -> OddsProvider:
    cfg = config.odds()
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if cfg.provider == "espn" or (cfg.provider == "auto" and not key):
        return EspnOdds()
    if not key:
        raise SystemExit("ODDS_API_KEY not set and provider is the_odds_api")
    return TheOddsApi(key, cfg, name_index(store.teams()))


def run(days_ahead: int = 1) -> list[str]:
    now = now_utc()
    today = today_et(now)
    window = {add_days(today, i) for i in range(days_ahead + 1)}
    targets = [g for g in store.schedule()
               if g["etDate"] in window and g["status"] == "scheduled" and parse_utc(g["tipUtc"]) > now]
    if not targets:
        print("odds: no upcoming games in window")
        return []
    prov = provider()
    lines = prov.featured(targets)
    tip = {g["id"]: parse_utc(g["tipUtc"]) for g in targets}
    taken = to_utc_iso(now)
    lines = [l for l in lines if l["gameId"] in tip and tip[l["gameId"]] > now]
    snap_name = taken.replace("-", "").replace(":", "")[:13] + "Z"  # 20261020T1405Z
    snap_path = SNAPSHOTS_DIR / today / f"{snap_name}.json"
    write_json(snap_path, {"takenAt": taken, "provider": prov.name, "games": lines})
    cur = store.current_lines()
    rel = str(snap_path.relative_to(ROOT))
    for l in lines:
        cur[l["gameId"]] = {"takenAt": taken, "provider": prov.name, "snapshot": rel, **l}
    write_json(CURRENT_LINES, dict(sorted(cur.items())))
    store.write_closing_for_tipped(taken)
    print(f"odds: {prov.name} snapshot with {len(lines)} games -> {rel}")
    return [l["gameId"] for l in lines]
