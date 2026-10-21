"""Project every upcoming game in the horizon. Projections for tipped games are frozen."""

from __future__ import annotations

from .. import config, store
from ..et import add_days, now_utc, parse_utc, to_utc_iso, today_et
from ..io import read_json, write_json
from ..model.availability import impacts_for_team, live_tracker, name_index
from ..model.projection import project
from ..model.rest import flags_for
from ..model.season import inputs
from ..paths import DATA, MODEL_PARAMS, PROJECTIONS_DIR, RATINGS_DIR
from ..sources.injury_report import norm_name
from .build_ratings import current_records
from .fit import prior_season_label

INJURY_MAX_AGE_HOURS = 30  # older reports are ignored rather than trusted


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

    # availability: tracker state after every finished game, plus the latest injury report
    params = read_json(MODEL_PARAMS) or {}
    av = params.get("availability")
    inj = read_json(DATA / "injuries" / "latest.json")
    inj_ok = bool(av and inj and (now - parse_utc(inj["pulledAt"])).total_seconds() < INJURY_MAX_AGE_HOURS * 3600)
    tr = idx = None
    if av:
        prior_rows = [p for ps in store.history_players(prior_season_label(config.site().season)).values() for p in ps]
        finals = sorted((g for g in games if g["status"] == "final"), key=lambda g: (g["tipUtc"], g["id"]))
        tr = live_tracker(store.season_players(), finals, prior_rows, av["leagueGameScore36"])
        idx = name_index(tr, prior_rows, norm_name)

    written = 0
    for day, day_games in sorted(by_day.items()):
        path = PROJECTIONS_DIR / f"{day}.json"
        prev = {p["gameId"]: p for p in (read_json(path) or {"games": []})["games"]}
        out = []
        for g in sorted(day_games, key=lambda x: (x["tipUtc"], x["id"])):
            if parse_utc(g["tipUtc"]) <= now and g["id"] in prev:
                out.append(prev[g["id"]])  # frozen at tip
                continue
            avail = {"home": [], "away": []}
            if inj_ok and tr is not None:
                # a listing applies to the team's next game; "out" also carries to later games
                items = [i for i in inj["items"] if i["gameId"] == g["id"] or i["status"] == "out"]
                for side in ("home", "away"):
                    avail[side] = impacts_for_team(items, g[side], tr, idx, av)
            inj_pts = {side: sum(x["impactPts"] for x in avail[side]) for side in ("home", "away")}
            p = project(g, ratings, rf, ratings["sigma"], inj_pts)
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
                "spots": {side: rf.get((g["id"], g[side])) for side in ("away", "home")},
                "availability": {"reportPulledAt": inj["pulledAt"] if inj_ok else None,
                                 "source": inj["source"] if inj_ok else None,
                                 "away": avail["away"], "home": avail["home"]},
            })
        if out != list(prev.values()):
            written += write_json(path, {"etDate": day, "games": out})
    print(f"projections: {sum(len(v) for v in by_day.values())} games over {len(by_day)} days, {written} files changed")
