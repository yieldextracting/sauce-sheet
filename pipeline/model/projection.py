"""Game projection from ratings: scores, spread, total, win probability, margin breakdown."""

from __future__ import annotations

import math

import numpy as np

from .ratings import FEATURES, HOME_KEYS, features


def norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def fair_american(p: float) -> int:
    p = min(max(p, 1e-4), 1 - 1e-4)
    if p >= 0.5:
        return int(round(-100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


def project(game: dict, ratings: dict, rf: dict, sigma: float, injury_pts: dict[str, float] | None = None) -> dict:
    """injury_pts: expected points each side loses to absences, e.g. {"home": 1.2, "away": 0.0}."""
    inj = injury_pts or {"home": 0.0, "away": 0.0}
    t = ratings["teams"]
    h, a = t[game["home"]], t[game["away"]]
    beta = np.array([ratings["betas"][f] for f in FEATURES])
    xh = features(game, game["home"], game["away"], rf)
    xa = features(game, game["away"], game["home"], rf)

    mu, mup = ratings["mu"], ratings["muPace"]
    poss = mup + h["pace"] + a["pace"]
    eff_h = mu + h["off"] - a["def"] + float(xh @ beta)
    eff_a = mu + a["off"] - h["def"] + float(xa @ beta)
    pts_h = poss * eff_h / 100.0 - inj["home"]
    pts_a = poss * eff_a / 100.0 - inj["away"]
    margin = pts_h - pts_a

    # Linear breakdown of the margin (home minus away). Sums exactly to `margin`.
    base = mup / 100.0
    dx = xh - xa
    home_part = sum(beta[i] * dx[i] for i, f in enumerate(FEATURES) if f in HOME_KEYS)
    rest_part = sum(beta[i] * dx[i] for i, f in enumerate(FEATURES) if f not in HOME_KEYS)
    contributions = [
        {"key": "offense", "pts": base * (h["off"] - a["off"])},
        {"key": "defense", "pts": base * (h["def"] - a["def"])},
        {"key": "pace", "pts": (poss - mup) / 100.0 * (eff_h - eff_a)},
        {"key": "home", "pts": base * home_part},
        {"key": "rest_travel", "pts": base * rest_part},
        {"key": "injuries", "pts": inj["away"] - inj["home"]},
    ]

    p_home = norm_cdf(margin / sigma)
    return {
        "awayPts": round(pts_a, 1),
        "homePts": round(pts_h, 1),
        "margin": round(margin, 2),
        "spreadHome": round(-margin, 1),
        "total": round(pts_h + pts_a, 1),
        "pace": round(poss, 1),
        "homeWinProb": round(p_home, 4),
        "fairMlHome": fair_american(p_home),
        "fairMlAway": fair_american(1 - p_home),
        "contributions": [{"key": c["key"], "pts": round(c["pts"], 2)} for c in contributions],
        "_exactMargin": margin,
        "_exactContribSum": sum(c["pts"] for c in contributions),
    }
