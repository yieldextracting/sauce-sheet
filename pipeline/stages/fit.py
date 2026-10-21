"""Fit model hyperparameters on past seasons only, then freeze them. Local only.

1. Full-season fit of the prior season (2022-23) -> end-of-season ratings.
2. Schedule-spot coefficients (home, altitude, rest, b2b, 3-in-4, travel): estimated in full-season
   fits of BOTH the prior season and the fit season, averaged by games. One season alone is too noisy
   for terms like altitude, which only two teams drive.
3. Walk forward through the fit season for each (K, regression) in the grid, priors from step 1.
   Pick the pair with the lowest margin RMSE; sigma = that RMSE.
4. Build this season's priors from last season's (2025-26) end-of-season ratings.

2024-25 and 2025-26 are never used to choose anything; they stay out-of-sample for the backtest.
"""

from __future__ import annotations

import numpy as np

from .. import config, store
from ..et import now_utc, to_utc_iso
from ..io import write_json
from ..model.availability import calibrate
from ..model.ratings import FEATURES, fit, regress_to_priors
from ..model.season import inputs, rmse, walk_forward
from ..paths import DATA, MODEL_PARAMS


def prior_season_label(season: str) -> str:
    y = int(season[:4])
    return f"{y - 1}-{str(y)[-2:]}"


def run() -> None:
    mc = config.model()
    teams = store.team_abbrs()
    prior_season, fit_season = mc.fit.priorSeasonForFit, mc.fit.fitSeason

    _, _, obs_prior = inputs(store.history_records(prior_season))
    final_prior = fit(obs_prior, teams, None, 0.0, None)

    fit_records = store.history_records(fit_season)
    _, _, obs_fit = inputs(fit_records)
    full_fit = fit(obs_fit, teams, None, 0.0, None)
    n1, n2 = len(obs_prior), len(obs_fit)
    betas = {f: (final_prior["betas"][f] * n1 + full_fit["betas"][f] * n2) / (n1 + n2) for f in FEATURES}
    print("betas", prior_season, {k: round(v, 3) for k, v in final_prior["betas"].items()})
    print("betas", fit_season, {k: round(v, 3) for k, v in full_fit["betas"].items()})
    print("betas (per 100 poss, per team-side):", {k: round(v, 3) for k, v in betas.items()})

    grid = []
    for r in mc.fit.regressionGrid:
        priors = regress_to_priors(final_prior, r)
        for k in mc.fit.kGrid:
            rows = walk_forward(fit_records, teams, priors, k, betas)
            e = rmse([x["predMargin"] - x["margin"] for x in rows])
            grid.append({"regression": r, "k": k, "marginRmse": round(e, 4), "n": len(rows)})
            print(f"  r={r} K={k}: margin RMSE {e:.3f} (n={len(rows)})", flush=True)
    best = min(grid, key=lambda g: g["marginRmse"])

    rows = walk_forward(fit_records, teams, regress_to_priors(final_prior, best["regression"]), best["k"], betas)
    sigma = rmse([x["predMargin"] - x["margin"] for x in rows])
    bias = float(np.mean([x["predMargin"] - x["margin"] for x in rows]))

    prior_players = [p for ps in store.history_players(prior_season).values() for p in ps]
    avail = calibrate(fit_records, store.history_players(fit_season), prior_players, rows)
    avail["pPlay"] = mc.availability.pPlay
    print("availability:", avail)

    params = {
        "modelVersion": mc.version,
        "fittedAt": to_utc_iso(now_utc()),
        "fitSeason": fit_season,
        "priorSeasonForFit": prior_season,
        "k": best["k"],
        "regression": best["regression"],
        "sigma": round(sigma, 4),
        "fitSeasonMeanError": round(bias, 4),
        "betas": {f: round(betas[f], 5) for f in FEATURES},
        "betasFrom": [prior_season, fit_season],
        "grid": grid,
        "availability": avail,
        "note": "Chosen by walk-forward margin RMSE on the fit season only. Not tuned on later seasons.",
    }
    write_json(MODEL_PARAMS, params)
    print("chosen:", {k: params[k] for k in ("k", "regression", "sigma")})

    # Priors for the live season from last season's end-of-season ratings.
    live = config.site().season
    last = prior_season_label(live)
    _, _, obs_last = inputs(store.history_records(last))
    final_last = fit(obs_last, teams, None, 0.0, np.array([betas[f] for f in FEATURES]))
    pri = regress_to_priors(final_last, best["regression"])
    write_json(DATA / "model" / f"priors-{live}.json", {
        "season": live, "fromSeason": last, "regression": best["regression"], "builtAt": to_utc_iso(now_utc()),
        "mu": round(pri["mu"], 4), "muPace": round(pri["muPace"], 4),
        "teams": {t: {k: round(v, 4) for k, v in x.items()} for t, x in pri["teams"].items()}})
    print(f"wrote priors for {live} from {last}")
