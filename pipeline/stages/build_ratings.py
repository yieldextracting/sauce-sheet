"""Current-season ratings: ridge toward last season's regressed ratings, frozen hyperparameters."""

from __future__ import annotations

import numpy as np

from .. import config, store
from ..et import now_utc, to_utc_iso, today_et
from ..io import read_json, write_json
from ..model.ratings import FEATURES, fit
from ..model.season import inputs
from ..paths import DATA, MODEL_PARAMS, RATINGS_DIR


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
                      "w": wl.get(t, {}).get("w", 0), "l": wl.get(t, {}).get("l", 0)}
                  for t, v in r["teams"].items()},
    }


def run() -> None:
    out = compute()
    write_json(RATINGS_DIR / f"{out['etDate']}.json", out)
    write_json(RATINGS_DIR / "latest.json", out)
    print(f"ratings: {out['gamesUsed']} games used, as of {out['etDate']}")
