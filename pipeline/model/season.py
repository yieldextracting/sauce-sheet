"""Glue: turn a season's games + results into model observations, and walk forward through it."""

from __future__ import annotations

import math

import numpy as np

from .. import config
from ..sources import geo
from .projection import project
from .ratings import FEATURES, fit, observations
from .rest import rest_features


def inputs(records: list[dict]) -> tuple[list[dict], dict, list[dict]]:
    games = [r["game"] for r in records]
    rf = rest_features(games, geo.load(), config.model().altitudeThresholdM)
    return games, rf, observations(records, rf)


def walk_forward(records: list[dict], teams: list[str], priors: dict, k: float,
                 betas: dict[str, float], sigma: float = 12.0) -> list[dict]:
    """Project every final game using only games from earlier ET dates. Returns per-game rows."""
    games, rf, obs = inputs(records)
    beta_arr = np.array([betas[f] for f in FEATURES])
    finals = {o["id"]: o for o in obs}
    by_day: dict[str, list[dict]] = {}
    for g in games:
        if g["id"] in finals:
            by_day.setdefault(g["etDate"], []).append(g)
    rows = []
    for day in sorted(by_day):
        train = [o for o in obs if o["etDate"] < day]
        ratings = fit(train, teams, priors, k, beta_arr)
        for g in by_day[day]:
            p = project(g, ratings, rf, sigma)
            o = finals[g["id"]]
            rows.append({"gameId": g["id"], "etDate": day, "predMargin": p["_exactMargin"],
                         "margin": o["margin"], "predTotal": p["total"], "total": o["total"],
                         "minGP": min(ratings["teams"][g["home"]]["gp"], ratings["teams"][g["away"]]["gp"])})
    return rows


def rmse(xs: list[float]) -> float:
    return math.sqrt(sum(x * x for x in xs) / len(xs)) if xs else float("nan")
