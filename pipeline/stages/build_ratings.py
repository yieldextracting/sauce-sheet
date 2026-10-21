"""Current-season ratings: ridge toward last season's regressed ratings, frozen hyperparameters."""

from __future__ import annotations

import numpy as np

from .. import config, store
from ..et import now_utc, to_utc_iso, today_et
from ..io import read_json, write_json
from ..model.ratings import FEATURES, fit, team_poss
from ..model.season import inputs
from ..paths import DATA, MODEL_PARAMS, RATINGS_DIR
from .fit import prior_season_label


def load_params() -> dict:
    p = read_json(MODEL_PARAMS)
    if p is None:
        raise SystemExit("no data/model/params.json; run `python -m pipeline fit` locally first")
    return p


def current_records() -> list[dict]:
    res = store.results()
    return [{"game": g, "result": res.get(g["id"])} for g in store.schedule()]


def records_wl(records: list[dict]) -> dict[str, dict]:
    wl: dict[str, dict] = {}
    for r in records:
        res = r["result"]
        if not res or res["status"] != "final":
            continue
        g = r["game"]
        home_won = res["homePts"] > res["awayPts"]
        for team, won in ((g["home"], home_won), (g["away"], not home_won)):
            x = wl.setdefault(team, {"w": 0, "l": 0})
            x["w" if won else "l"] += 1
    return wl


def four_factors(records: list[dict]) -> dict[str, dict]:
    """Raw (not opponent-adjusted) four factors per team, offense and defense, from team boxes."""
    acc: dict[str, dict[str, dict[str, float]]] = {}
    for r in records:
        res = r["result"]
        if not res or res.get("status") != "final" or not res.get("box"):
            continue
        g = r["game"]
        for side, opp in (("home", "away"), ("away", "home")):
            t, b, o = g[side], res["box"][side], res["box"][opp]
            a = acc.setdefault(t, {"off": {}, "def": {}, "gp": {"n": 0}})
            a["gp"]["n"] += 1
            for key, mine, theirs in (("off", b, o), ("def", o, b)):
                d = a[key]
                for k, v in (("fgm", mine["fgm"]), ("fg3m", mine["fg3m"]), ("fga", mine["fga"]), ("ftm", mine["ftm"]),
                             ("tov", mine["tov"]), ("poss", team_poss(mine)), ("oreb", mine["oreb"]),
                             ("oppdreb", theirs["dreb"])):
                    d[k] = d.get(k, 0.0) + v
    out = {}
    for t, a in acc.items():
        out[t] = {"gp": a["gp"]["n"]}
        for key in ("off", "def"):
            d = a[key]
            out[t][key] = {"efg": round((d["fgm"] + 0.5 * d["fg3m"]) / d["fga"], 4),
                           "tov": round(d["tov"] / d["poss"], 4),
                           "orb": round(d["oreb"] / (d["oreb"] + d["oppdreb"]), 4),
                           "ftr": round(d["ftm"] / d["fga"], 4)}
    return out


def compute() -> dict:
    params = load_params()
    season = config.site().season
    priors = read_json(DATA / "model" / f"priors-{season}.json")
    if priors is None:
        raise SystemExit(f"no priors for {season}; run `python -m pipeline fit`")
    teams = store.team_abbrs()
    records = current_records()
    _, _, obs = inputs(records)
    betas = np.array([params["betas"][f] for f in FEATURES])
    r = fit(obs, teams, priors, params["k"], betas)
    wl = records_wl(records)
    ff_now = four_factors(records)
    ff_last = four_factors(store.history_records(prior_season_label(season)))
    return {
        "season": season,
        "asOf": to_utc_iso(now_utc()),
        "etDate": today_et(),
        "modelVersion": params["modelVersion"],
        "gamesUsed": len(obs),
        "mu": round(r["mu"], 3),
        "muPace": round(r["muPace"], 3),
        "k": params["k"],
        "sigma": params["sigma"],
        "betas": params["betas"],
        "teams": {t: {"off": round(v["off"], 3), "def": round(v["def"], 3), "pace": round(v["pace"], 3),
                      "ortg": round(r["mu"] + v["off"], 2), "drtg": round(r["mu"] - v["def"], 2),
                      "net": round(v["off"] + v["def"], 3), "gp": v["gp"],
                      "priorWeight": round(v["priorWeight"], 4),
                      "w": wl.get(t, {}).get("w", 0), "l": wl.get(t, {}).get("l", 0),
                      "fourFactors": ff_now.get(t) or None,
                      "fourFactorsLastSeason": ff_last.get(t)}
                  for t, v in r["teams"].items()},
    }


def run() -> None:
    out = compute()
    write_json(RATINGS_DIR / f"{out['etDate']}.json", out)
    write_json(RATINGS_DIR / "latest.json", out)
    print(f"ratings: {out['gamesUsed']} games used, as of {out['etDate']}")
