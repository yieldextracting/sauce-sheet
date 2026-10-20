"""Read/write helpers for the repo-as-database layout."""

from __future__ import annotations

from pathlib import Path

from . import config
from .et import parse_utc
from .io import read_json, write_json
from .paths import (CLOSING_DIR, CURRENT_LINES, FIRST_SEEN_DIR, HISTORY_DIR, MODEL_PICKS_DIR,
                    PROJECTIONS_DIR, SNAPSHOTS_DIR, TEAMS, results_dir, schedule_path)


def season() -> str:
    return config.site().season


def teams() -> list[dict]:
    return read_json(TEAMS, [])


def team_abbrs() -> list[str]:
    return [t["abbr"] for t in teams()]


def schedule(s: str | None = None) -> list[dict]:
    d = read_json(schedule_path(s or season()), {"games": []})
    return d["games"]


def games_by_id(s: str | None = None) -> dict[str, dict]:
    return {g["id"]: g for g in schedule(s)}


def result(gid: str, s: str | None = None) -> dict | None:
    return read_json(results_dir(s or season()) / f"{gid}.json")


def results(s: str | None = None) -> dict[str, dict]:
    d = results_dir(s or season())
    if not d.exists():
        return {}
    return {p.stem: read_json(p) for p in sorted(d.glob("*.json"))}


def history_records(s: str) -> list[dict]:
    d = read_json(HISTORY_DIR / s / "games.json")
    if d is None:
        raise FileNotFoundError(f"no history for {s}; run: python -m pipeline backfill --seasons ...")
    return d["records"]


def projections_for(day: str) -> dict:
    return read_json(PROJECTIONS_DIR / f"{day}.json", {"games": []})


def projection(gid: str, day: str) -> dict | None:
    for p in projections_for(day)["games"]:
        if p["gameId"] == gid:
            return p
    return None


def current_lines() -> dict[str, dict]:
    return read_json(CURRENT_LINES, {})


def snapshot_files() -> list[Path]:
    """All featured-market snapshots, oldest first (filenames are UTC stamps)."""
    if not SNAPSHOTS_DIR.exists():
        return []
    return sorted(SNAPSHOTS_DIR.glob("*/*.json"), key=lambda p: p.name)


def first_seen_path(gid: str) -> Path:
    return FIRST_SEEN_DIR / f"{gid}.json"


def model_pick_path(gid: str) -> Path:
    return MODEL_PICKS_DIR / f"{gid}.json"


def closing_path(gid: str) -> Path:
    return CLOSING_DIR / f"{gid}.json"


def write_closing_for_tipped(now_iso: str) -> int:
    """Closing line = the last pre-tip snapshot we have for a game. Written once the game tips."""
    now = parse_utc(now_iso)
    games = games_by_id()
    cur = current_lines()
    n = 0
    for gid, entry in cur.items():
        g = games.get(gid)
        if not g or parse_utc(g["tipUtc"]) > now:
            continue
        p = closing_path(gid)
        if p.exists():
            continue
        write_json(p, entry)
        n += 1
    return n
