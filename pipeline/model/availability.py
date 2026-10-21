"""Availability model (v2): what a missing player costs his team, in points of margin.

Transparent pieces:
- Player value per game = (GameScore per 36 - replacement level) x expected minutes / 36.
  GameScore is Hollinger's published box-score formula, so no coefficient here is ours.
- Per-36 rate blends this season with last season (last season counts as PRIOR_MINUTES minutes).
- Expected minutes = EWMA over the team's games (0 when he sat), seeded with last season's
  minutes per game. A long-term absence decays toward 0, so it is not double-counted against
  team ratings that already reflect it.
- Replacement level and the points-per-value scale (beta) are estimated from the fit season
  (see stages/fit.py). Impact = beta x value x (1 - P(play)).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

PRIOR_MINUTES = 400.0      # last season's rate counts like 400 minutes of this season
EWMA_HALF_LIFE = 5.0       # team games
MIN_EXPECTED_MINUTES = 8.0  # below this a player is not treated as a rotation absence
ALPHA = 1 - 0.5 ** (1 / EWMA_HALF_LIFE)


def game_score(p: dict) -> float:
    """Hollinger Game Score."""
    return (p["pts"] + 0.4 * p["fgm"] - 0.7 * p["fga"] - 0.4 * (p["fta"] - p["ftm"]) + 0.7 * p["oreb"]
            + 0.3 * p["dreb"] + p["stl"] + 0.7 * p["ast"] + 0.7 * p["blk"] - 0.4 * p["pf"] - p["tov"])


@dataclass
class Prior:
    rate36: float
    mpg: float


@dataclass
class PlayerState:
    name: str
    gs: float = 0.0
    minutes: float = 0.0
    games: int = 0
    exp_min: dict[str, float] = field(default_factory=dict)  # team -> EWMA minutes


def prior_rates(rows: list[dict]) -> dict[str, Prior]:
    """Last-season per-36 GameScore and minutes per game played, by ESPN id."""
    agg: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
    for p in rows:
        if p["dnp"] or p["min"] <= 0:
            continue
        a = agg[p["espnId"]]
        a[0] += game_score(p)
        a[1] += p["min"]
        a[2] += 1
    return {pid: Prior(rate36=36 * gs / m, mpg=m / g) for pid, (gs, m, g) in agg.items() if m >= 50}


class Tracker:
    """Walks a season in order. `pre_game` gives each listed player's state before a game."""

    def __init__(self, priors: dict[str, Prior], league_rate36: float):
        self.priors = priors
        self.league = league_rate36
        self.state: dict[str, PlayerState] = {}

    def rate36(self, pid: str) -> float:
        s = self.state.get(pid)
        pr = self.priors.get(pid)
        prior_rate = pr.rate36 if pr else self.league
        gs, mins = (s.gs, s.minutes) if s else (0.0, 0.0)
        return (gs + prior_rate * PRIOR_MINUTES / 36) / ((mins + PRIOR_MINUTES) / 36)

    def expected_minutes(self, pid: str, team: str) -> float:
        s = self.state.get(pid)
        if s and team in s.exp_min:
            return s.exp_min[team]
        pr = self.priors.get(pid)
        return pr.mpg if pr else 0.0

    def value(self, pid: str, team: str, replacement36: float) -> float:
        return (self.rate36(pid) - replacement36) * self.expected_minutes(pid, team) / 36.0

    def update(self, players: list[dict]) -> None:
        """Apply one finished game's box (every listed player, DNPs included)."""
        for p in players:
            pid = p["espnId"]
            s = self.state.setdefault(pid, PlayerState(name=p["name"]))
            prev = self.expected_minutes(pid, p["team"])
            mins = 0.0 if p["dnp"] else float(p["min"])
            s.exp_min[p["team"]] = prev + ALPHA * (mins - prev)
            if not p["dnp"] and p["min"] > 0:
                s.gs += game_score(p)
                s.minutes += p["min"]
                s.games += 1


def league_rate36(rows: list[dict]) -> float:
    gs = sum(game_score(p) for p in rows if not p["dnp"])
    m = sum(p["min"] for p in rows if not p["dnp"])
    return 36 * gs / m if m else 0.0


def replacement_rate36(rows: list[dict], mpg_cutoff: float = 12.0) -> float:
    """Minutes-weighted GameScore/36 of deep-bench players (under `mpg_cutoff` minutes per game)."""
    by: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
    for p in rows:
        if p["dnp"] or p["min"] <= 0:
            continue
        a = by[p["espnId"]]
        a[0] += game_score(p)
        a[1] += p["min"]
        a[2] += 1
    gs = sum(a[0] for a in by.values() if a[1] / a[2] < mpg_cutoff)
    m = sum(a[1] for a in by.values() if a[1] / a[2] < mpg_cutoff)
    return 36 * gs / m if m else 0.0


def missing_value(players: list[dict], tracker: Tracker, team: str, replacement36: float) -> float:
    """Sum of value for rotation players listed on the box who did not play (fit-time measure)."""
    total = 0.0
    for p in players:
        if p["team"] != team or not p["dnp"]:
            continue
        if tracker.expected_minutes(p["espnId"], team) < MIN_EXPECTED_MINUTES:
            continue
        total += max(0.0, tracker.value(p["espnId"], team, replacement36))
    return total


def calibrate(records: list[dict], players_by_game: dict[str, list[dict]], prior_rows: list[dict],
              walk_rows: list[dict]) -> dict:
    """Fit beta: regress walk-forward margin errors on (away missing value - home missing value).

    Uses actual DNPs (P(play) = 0 for players who sat). No intercept, one coefficient.
    """
    import math

    season_rows = [p for ps in players_by_game.values() for p in ps]
    repl = replacement_rate36(season_rows)
    tracker = Tracker(prior_rates(prior_rows), league_rate36(season_rows))
    resid = {r["gameId"]: r["margin"] - r["predMargin"] for r in walk_rows}
    xs, ys = [], []
    games = sorted((r["game"] for r in records if r["result"] and r["result"].get("status") == "final"),
                   key=lambda g: (g["tipUtc"], g["id"]))
    for g in games:
        ps = players_by_game.get(g["id"], [])
        if g["id"] in resid:
            x = missing_value(ps, tracker, g["away"], repl) - missing_value(ps, tracker, g["home"], repl)
            xs.append(x)
            ys.append(resid[g["id"]])
        tracker.update(ps)
    sxx = sum(x * x for x in xs)
    beta = sum(x * y for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    n = len(xs)
    sse = sum((y - beta * x) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt(sse / max(n - 1, 1) / sxx) if sxx else float("nan")
    rmse_before = math.sqrt(sum(y * y for y in ys) / n) if n else float("nan")
    return {
        "replacementGameScore36": round(repl, 4),
        "leagueGameScore36": round(tracker.league, 4),
        "beta": round(float(beta), 4),
        "betaSe": round(se, 4),
        "n": n,
        "nWithAbsences": sum(1 for x in xs if x != 0),
        "rmseBefore": round(rmse_before, 4),
        "rmseAfter": round(math.sqrt(sse / n), 4) if n else None,
        "priorMinutes": PRIOR_MINUTES,
        "ewmaHalfLifeGames": EWMA_HALF_LIFE,
        "minExpectedMinutes": MIN_EXPECTED_MINUTES,
    }


def live_tracker(season_players: dict[str, list[dict]], games_in_order: list[dict],
                 prior_rows: list[dict], league36: float) -> Tracker:
    """Tracker state after every finished game of the live season."""
    tr = Tracker(prior_rates(prior_rows), league36)
    for g in games_in_order:
        if g["id"] in season_players:
            tr.update(season_players[g["id"]])
    return tr


def name_index(tr: Tracker, prior_rows: list[dict], norm) -> dict[str, str]:
    """normalized name -> ESPN id, from this season's boxes and last season's."""
    idx: dict[str, str] = {}
    for p in prior_rows:
        idx.setdefault(norm(p["name"]), p["espnId"])
    for pid, s in tr.state.items():
        idx[norm(s.name)] = pid
    return idx


def impacts_for_team(items: list[dict], team: str, tr: Tracker, idx: dict[str, str], params: dict) -> list[dict]:
    """Per listed player: expected minutes, value, and expected points lost = beta x value x (1 - pPlay)."""
    out = []
    beta, repl = params["beta"], params["replacementGameScore36"]
    for it in items:
        if it["team"] != team:
            continue
        pid = it.get("espnId") or idx.get(it["key"])
        exp_min = tr.expected_minutes(pid, team) if pid else 0.0
        value = max(0.0, tr.value(pid, team, repl)) if pid else 0.0
        counts = exp_min >= MIN_EXPECTED_MINUTES
        impact = beta * value * (1.0 - it["pPlay"]) if counts else 0.0
        out.append({"player": it["player"], "team": team, "status": it["status"], "pPlay": it["pPlay"],
                    "reason": it.get("reason"), "matched": pid is not None,
                    "expMin": round(exp_min, 1), "value": round(value, 2), "impactPts": round(impact, 2)})
    return sorted(out, key=lambda x: -x["impactPts"])
