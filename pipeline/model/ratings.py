"""Opponent-adjusted team ratings (SRS-style), solved by ridge regression toward priors.

Efficiency model, one row per team per game (team t on offense vs opponent o):
    100 * pts_t / poss = mu + off_t - def_o + beta . x(t, o) + noise
Pace model, one row per game:
    poss_per_48 = mu_p + pace_home + pace_away + noise

Positive `def` = good defence (it lowers the opponent's efficiency).
Priors enter as K pseudo-games per team. Their weight decays as K / (K + games played).
"""

from __future__ import annotations

import numpy as np

FEATURES = ["home", "altitude", "b2b", "rest", "threeInFour", "travel"]
HOME_KEYS = {"home"}  # everything else counts as rest/travel in the margin breakdown

TINY = 1e-6


def team_poss(b: dict) -> float:
    return b["fga"] - b["oreb"] + b["tov"] + 0.44 * b["fta"]


def features(game: dict, offense: str, defense: str, rf: dict) -> np.ndarray:
    neutral = bool(game.get("neutralSite"))
    is_home = offense == game["home"]
    sign = 1.0 if is_home else -1.0
    ft = rf.get((game["id"], offense), {})
    fo = rf.get((game["id"], defense), {})
    home_alt = rf.get((game["id"], game["home"]), {}).get("atAltitude", False)

    def rest(f: dict) -> float:
        r = f.get("restDays")
        return 3.0 if r is None else float(min(r, 3))

    return np.array([
        0.0 if neutral else sign,
        sign if (home_alt and not neutral) else 0.0,
        float(ft.get("b2b", False)) - float(fo.get("b2b", False)),
        rest(ft) - rest(fo),
        float(ft.get("threeInFour", False)) - float(fo.get("threeInFour", False)),
        (ft.get("travelKm", 0.0) - fo.get("travelKm", 0.0)) / 1000.0,
    ])


def observations(records: list[dict], rf: dict) -> list[dict]:
    """records: [{"game": Game, "result": Result}] with final status and a team box."""
    obs = []
    for r in records:
        g, res = r["game"], r["result"]
        if not res or res.get("status") != "final" or not res.get("box"):
            continue
        bh, ba = res["box"]["home"], res["box"]["away"]
        poss = (team_poss(bh) + team_poss(ba)) / 2.0
        if poss <= 0:
            continue
        minutes = 48 + 5 * max(0, (res.get("periods") or 4) - 4)
        obs.append({
            "id": g["id"], "etDate": g["etDate"], "home": g["home"], "away": g["away"],
            "poss": poss, "pace48": poss * 48.0 / minutes,
            "effHome": 100.0 * res["homePts"] / poss, "effAway": 100.0 * res["awayPts"] / poss,
            "xHome": features(g, g["home"], g["away"], rf),
            "xAway": features(g, g["away"], g["home"], rf),
            "margin": res["homePts"] - res["awayPts"], "total": res["homePts"] + res["awayPts"],
        })
    return obs


def fit(obs: list[dict], teams: list[str], priors: dict | None, k: float,
        betas: np.ndarray | None = None) -> dict:
    """Solve ratings. If `betas` is None the schedule-spot coefficients are estimated too.

    priors: {"mu", "muPace", "teams": {abbr: {"off","def","pace"}}} or None (shrink to 0, tiny).
    """
    n = len(teams)
    ix = {t: i for i, t in enumerate(teams)}
    est_beta = betas is None
    nb = len(FEATURES) if est_beta else 0
    ncol = 1 + 2 * n + nb

    rows, ys = [], []
    for o in obs:
        for off, dfn, eff, x in ((o["home"], o["away"], o["effHome"], o["xHome"]),
                                 (o["away"], o["home"], o["effAway"], o["xAway"])):
            row = np.zeros(ncol)
            row[0] = 1.0
            row[1 + ix[off]] = 1.0
            row[1 + n + ix[dfn]] = -1.0
            y = eff
            if est_beta:
                row[1 + 2 * n:] = x
            else:
                y -= float(x @ betas)
            rows.append(row)
            ys.append(y)

    w = np.sqrt(k) if (priors and k > 0) else np.sqrt(TINY)
    for t in teams:
        p = priors["teams"].get(t, {}) if priors else {}
        for col, key in ((1 + ix[t], "off"), (1 + n + ix[t], "def")):
            row = np.zeros(ncol)
            row[col] = w
            rows.append(row)
            ys.append(w * p.get(key, 0.0))
    if priors:
        row = np.zeros(ncol)
        row[0] = w
        rows.append(row)
        ys.append(w * priors["mu"])
    if est_beta:
        for j in range(nb):
            row = np.zeros(ncol)
            row[1 + 2 * n + j] = np.sqrt(TINY)
            rows.append(row)
            ys.append(0.0)

    theta, *_ = np.linalg.lstsq(np.array(rows), np.array(ys), rcond=None)
    mu = float(theta[0])
    off = theta[1:1 + n].copy()
    dfn = theta[1 + n:1 + 2 * n].copy()
    mo, md = off.mean(), dfn.mean()
    off -= mo
    dfn -= md
    mu += mo - md
    beta_out = theta[1 + 2 * n:] if est_beta else betas

    # pace
    prow, pys = [], []
    for o in obs:
        row = np.zeros(1 + n)
        row[0] = 1.0
        row[1 + ix[o["home"]]] += 1.0
        row[1 + ix[o["away"]]] += 1.0
        prow.append(row)
        pys.append(o["pace48"])
    for t in teams:
        row = np.zeros(1 + n)
        row[1 + ix[t]] = w
        prow.append(row)
        pys.append(w * (priors["teams"].get(t, {}).get("pace", 0.0) if priors else 0.0))
    if priors:
        row = np.zeros(1 + n)
        row[0] = w
        prow.append(row)
        pys.append(w * priors["muPace"])
    ptheta, *_ = np.linalg.lstsq(np.array(prow), np.array(pys), rcond=None)
    mup = float(ptheta[0])
    pace = ptheta[1:].copy()
    mp = pace.mean()
    pace -= mp
    mup += 2 * mp

    gp = {t: 0 for t in teams}
    for o in obs:
        gp[o["home"]] += 1
        gp[o["away"]] += 1

    return {
        "mu": mu, "muPace": mup,
        "betas": {f: float(b) for f, b in zip(FEATURES, beta_out)},
        "k": k,
        "teams": {t: {"off": float(off[ix[t]]), "def": float(dfn[ix[t]]), "pace": float(pace[ix[t]]),
                      "gp": gp[t], "priorWeight": (k / (k + gp[t])) if (priors and k > 0) else 0.0}
                  for t in teams},
    }


def regress_to_priors(final: dict, r: float) -> dict:
    """Last season's ratings pulled a fraction r of the way back to league average."""
    return {"mu": final["mu"], "muPace": final["muPace"],
            "teams": {t: {"off": (1 - r) * v["off"], "def": (1 - r) * v["def"], "pace": (1 - r) * v["pace"]}
                      for t, v in final["teams"].items()}}
