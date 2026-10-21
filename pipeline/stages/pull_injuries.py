"""Pull the injury report. Official NBA PDF first, ESPN as fallback. Every pull is logged.

INJURY_SOURCES (env) overrides the order, e.g. "espn" in GitHub Actions, where the official
report returns 403 (verified 2026-10-20).
"""

from __future__ import annotations

import os
import re

from .. import config, store
from ..et import add_days, now_utc, parse_utc, to_utc_iso, today_et
from ..io import append_jsonl, read_json, write_json
from ..paths import DATA, PULL_LOG
from ..sources.injury_report import fetch_espn, fetch_official

INJ_DIR = DATA / "injuries"
DEFAULT_SOURCES = ["nba_official", "espn"]


def next_game_ids(now) -> dict[str, str]:
    """team -> id of its next untipped game within today/tomorrow (ET)."""
    today = today_et(now)
    window = {today, add_days(today, 1)}
    out: dict[str, str] = {}
    for g in sorted(store.schedule(), key=lambda g: g["tipUtc"]):
        if g["etDate"] not in window or g["status"] != "scheduled" or parse_utc(g["tipUtc"]) <= now:
            continue
        for t in (g["home"], g["away"]):
            out.setdefault(t, g["id"])
    return out


def run() -> dict:
    now = now_utc()
    p_play = config.model().availability.pPlay
    team_idx = {re.sub(r"[^a-z0-9]", "", t["name"].lower()): t["abbr"] for t in store.teams()}
    team_idx["laclippers"] = "LAC"
    sources = [s.strip() for s in os.environ.get("INJURY_SOURCES", ",".join(DEFAULT_SOURCES)).split(",") if s.strip()]

    items, used, stamp, errors = None, None, None, []
    for src in sources:
        try:
            if src == "nba_official":
                items, stamp = fetch_official(team_idx)
            elif src == "espn":
                items = fetch_espn()
            else:
                raise ValueError(f"unknown injury source {src}")
            if not items:
                raise RuntimeError("parsed zero rows")
            used = src
            break
        except Exception as e:  # try the next source, but record why
            errors.append(f"{src}: {type(e).__name__}: {e}")
            items = None

    games = next_game_ids(now)
    pulled = to_utc_iso(now)
    pull = {"pulledAt": pulled, "source": used, "reportStamp": stamp, "ok": items is not None,
            "errors": errors, "items": []}
    for it in items or []:
        pull["items"].append({
            "player": it["player"], "key": it["key"], "team": it["team"], "status": it["status"],
            "pPlay": p_play[it["status"]], "reason": it.get("reason"), "espnId": it.get("espnId"),
            "gameId": games.get(it["team"]), "source": it["source"]})
    append_jsonl(PULL_LOG, {"at": pulled, "source": "injuries", "url": used or "none", "ok": pull["ok"],
                            "status": None, "error": "; ".join(errors) or None, "rows": len(pull["items"])})
    stamp_name = pulled.replace("-", "").replace(":", "")[:13] + "Z"
    if pull["ok"]:
        prev = read_json(INJ_DIR / "latest.json") or {}
        changed = prev.get("items") != pull["items"] or prev.get("source") != used
        if changed:  # snapshots only when the report changes; every pull is still in pulls.jsonl
            write_json(INJ_DIR / today_et(now) / f"{stamp_name}.json", pull)
            write_json(INJ_DIR / "latest.json", pull)
        print(f"injuries: {len(pull['items'])} rows from {used}, {'changed' if changed else 'unchanged'}"
              + (f" (fallback after: {errors})" if errors else ""))
    else:
        print(f"injuries: ALL SOURCES FAILED: {errors}")
        raise SystemExit("injury pull failed on every source")
    pull["changed"] = changed
    return pull
