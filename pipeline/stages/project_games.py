"""Project every upcoming game in the horizon. Projections for tipped games are frozen."""

from __future__ import annotations

from .. import config, store
from ..et import add_days, now_utc, parse_utc, to_utc_iso, today_et
from ..io import read_json, write_json
from ..model.projection import project
from ..model.rest import flags_for
from ..model.season import inputs
from ..paths import PROJECTIONS_DIR, RATINGS_DIR
from .build_ratings import current_records


def run() -> None:
    mc = config.model()
    ratings = read_json(RATINGS_DIR / "latest.json")
    if ratings is None:
        raise SystemExit("no ratings; run build_ratings first")
    now = now_utc()
    today = today_et(now)
    horizon = {add_days(today, i) for i in range(mc.projectionHorizonDays + 1)}
    records = current_records()
    games, rf, _ = inputs(records)
    by_day: dict[str, list[dict]] = {}
    for g in games:
        if g["etDate"] in horizon and g["status"] not in ("postponed", "cancelled"):
            by_day.setdefault(g["etDate"], []).append(g)

    written = 0
    for day, day_games in sorted(by_day.items()):
        path = PROJECTIONS_DIR / f"{day}.json"
        prev = {p["gameId"]: p for p in (read_json(path) or {"games": []})["games"]}
        out = []
        for g in sorted(day_games, key=lambda x: (x["tipUtc"], x["id"])):
            if parse_utc(g["tipUtc"]) <= now and g["id"] in prev:
                out.append(prev[g["id"]])  # frozen at tip
                continue
            p = project(g, ratings, rf, ratings["sigma"])
            assert abs(p.pop("_exactMargin") - p.pop("_exactContribSum")) < 1e-9
            th, ta = ratings["teams"][g["home"]], ratings["teams"][g["away"]]
            out.append({
                "gameId": g["id"],
                "generatedAt": to_utc_iso(now),
                "ratingsAsOf": ratings["asOf"],
                "modelVersion": ratings["modelVersion"],
                **p,
                "sample": {"awayGP": ta["gp"], "homeGP": th["gp"],
                           "priorWeight": round((ta["priorWeight"] + th["priorWeight"]) / 2, 4)},
                "flags": flags_for(g, rf),
            })
        if out != list(prev.values()):
            written += write_json(path, {"etDate": day, "games": out})
    print(f"projections: {sum(len(v) for v in by_day.values())} games over {len(by_day)} days, {written} files changed")
