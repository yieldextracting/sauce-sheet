"""Grade model picks (vs first-seen) and My Card picks (vs the logged line/price).

Output is fully regenerated from immutable inputs each run, so it can never drift.
CLV is measured against the closing consensus line (last pre-tip snapshot).
"""

from __future__ import annotations

from .. import cards, config, store
from ..et import now_utc, to_utc_iso
from ..grading import (clv_points, game_state, moneyline_outcome, profit, prop_outcome,
                       spread_outcome, total_outcome)
from ..io import read_json, write_json
from ..paths import GRADES_DIR, MODEL_PICKS_DIR


def _closing(gid: str) -> dict | None:
    return read_json(store.closing_path(gid))


def _original_date(gid: str) -> str:
    d = gid[:8]
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


def grade_model() -> list[dict]:
    games = store.games_by_id()
    out = []
    for p in sorted(MODEL_PICKS_DIR.glob("*.json")):
        pick = read_json(p)
        if pick["side"] == "none":
            continue
        gid = pick["gameId"]
        g = games.get(gid)
        res = store.result(gid)
        state = game_state(res, _original_date(gid), g["etDate"] if g else None)
        if g and g["status"] in ("postponed", "cancelled"):
            state = "void"
        side_home = pick["side"] == "home"
        outcome = state or spread_outcome(side_home, pick["line"], res["homePts"], res["awayPts"])
        close = _closing(gid)
        close_line = None
        if close and close["consensus"]["spreadHome"] is not None:
            ch = close["consensus"]["spreadHome"]
            close_line = ch if side_home else -ch
        out.append({
            "source": "model", "gameId": gid, "etDate": g["etDate"] if g else _original_date(gid),
            "pickId": "model", "market": "spread", "side": g[pick["side"]] if g else pick["side"],
            "line": pick["line"], "price": pick["price"], "units": 1.0,
            "result": outcome, "profitU": round(profit(outcome, pick["price"], 1.0), 4),
            "edge": abs(pick["edge"]) if pick["edge"] is not None else None,
            "closingLine": close_line,
            "clvPts": clv_points("spread", "", pick["line"], close_line) if close_line is not None else None,
            "finalScore": f"{res['awayPts']}-{res['homePts']}" if res and res["status"] == "final" else None,
        })
    return out


def _player_value(res: dict, name: str, stat: str) -> tuple[float | None, bool]:
    key = name.strip().lower()
    for pl in res.get("players", []):
        if pl["name"].strip().lower() == key:
            if pl["dnp"]:
                return None, True
            if stat == "pra":
                return float(pl["pts"] + pl["reb"] + pl["ast"]), False
            return float(pl[stat]), False
    return None, True  # not on the box score at all -> treat as DNP (void)


def grade_card() -> list[dict]:
    games = store.games_by_id()
    out = []
    for card in cards.load_all():
        amended = {a.pickId: a.note for a in card.amendments}
        for pk in card.picks:
            g = games.get(pk.game)
            if g is None:
                raise ValueError(f"card {card.date} pick {pk.id}: unknown game {pk.game}")
            res = store.result(pk.game)
            state = game_state(res, _original_date(pk.game), g["etDate"])
            if g["status"] in ("postponed", "cancelled"):
                state = "void"
            close = _closing(pk.game)
            close_line, clv = None, None
            if state:
                outcome = state
            elif pk.market == "spread":
                side_home = pk.side == g["home"]
                outcome = spread_outcome(side_home, pk.line, res["homePts"], res["awayPts"])
            elif pk.market == "total":
                outcome = total_outcome(pk.side == "over", pk.line, res["homePts"], res["awayPts"])
            elif pk.market == "moneyline":
                outcome = moneyline_outcome(pk.side == g["home"], res["homePts"], res["awayPts"])
            else:
                val, dnp = _player_value(res, pk.player or "", pk.stat or "pts")
                outcome = prop_outcome(pk.side == "over", pk.line, val, dnp)
            if close and pk.market == "spread" and close["consensus"]["spreadHome"] is not None:
                ch = close["consensus"]["spreadHome"]
                close_line = ch if pk.side == g["home"] else -ch
                clv = clv_points("spread", "", pk.line, close_line)
            elif close and pk.market == "total" and close["consensus"]["total"] is not None:
                close_line = close["consensus"]["total"]
                clv = clv_points("total", pk.side, pk.line, close_line)
            out.append({
                "source": "card", "gameId": pk.game, "etDate": card.date, "pickId": pk.id,
                "market": pk.market, "side": pk.side, "player": pk.player, "stat": pk.stat,
                "line": pk.line, "price": pk.odds, "units": pk.units, "confidence": pk.confidence,
                "result": outcome, "profitU": round(profit(outcome, pk.odds, pk.units), 4),
                "edge": None, "closingLine": close_line, "clvPts": clv,
                "finalScore": f"{res['awayPts']}-{res['homePts']}" if res and res["status"] == "final" else None,
                "amendment": amended.get(pk.id),
            })
    return out


def summarize(rows: list[dict]) -> dict:
    done = [r for r in rows if r["result"] in ("win", "loss", "push")]
    risked = sum(r["units"] for r in done if r["result"] != "push")
    units = sum(r["profitU"] for r in done)
    clv = [r["clvPts"] for r in done if r["clvPts"] is not None]
    return {
        "w": sum(r["result"] == "win" for r in done),
        "l": sum(r["result"] == "loss" for r in done),
        "p": sum(r["result"] == "push" for r in done),
        "pending": sum(r["result"] == "pending" for r in rows),
        "units": round(units, 3),
        "risked": round(risked, 3),
        "roi": round(units / risked, 4) if risked else None,
        "clvPtsAvg": round(sum(clv) / len(clv), 3) if clv else None,
        "beatClosePct": round(sum(c > 0 for c in clv) / len(clv), 4) if clv else None,
        "clvN": len(clv),
    }


def run() -> None:
    tiers = config.model().edgeTiers
    store.write_closing_for_tipped(to_utc_iso(now_utc()))
    model_rows = grade_model()
    card_rows = grade_card()
    model_summary = {"all": summarize(model_rows)}
    for t in tiers:
        model_summary[f"edge{t:g}"] = summarize([r for r in model_rows if (r["edge"] or 0) >= t])
    card_summary = {"all": summarize(card_rows)}
    for m in ("spread", "total", "moneyline", "prop"):
        card_summary[m] = summarize([r for r in card_rows if r["market"] == m])
    # generatedAt only moves when grades change, so quiet runs don't commit
    for name, rows, summ in (("model", model_rows, model_summary), ("card", card_rows, card_summary)):
        path = GRADES_DIR / f"{name}.json"
        prev = read_json(path) or {}
        body = {"grades": rows, "summary": summ}
        if {k: prev.get(k) for k in body} != body:
            write_json(path, {"generatedAt": to_utc_iso(now_utc()), **body})
    print(f"grade: model {model_summary['all']}, card {card_summary['all']}")
