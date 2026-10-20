"""Lock the first line ever seen for each game, and the model's pick against it. Write-once.

The first-seen line comes from the EARLIEST snapshot containing the game (scanned in order), so a
crash between pull_odds and lock can never promote a later line to "first seen".
The model pick uses the projection that existed at lock time. If none existed, the pick is
recorded as "none" rather than filled in later with newer information.
"""

from __future__ import annotations

from .. import config, store
from ..et import now_utc, to_utc_iso
from ..io import read_json, write_once
from ..paths import ROOT


def model_pick(gid: str, lines: dict, proj: dict | None, locked_at: str) -> dict:
    mc = config.model()
    market = lines["consensus"]["spreadHome"]
    base = {"gameId": gid, "lockedAt": locked_at, "modelVersion": mc.version,
            "marketSpreadHome": market, "marketTotal": lines["consensus"].get("total"),
            "price": mc.modelPickPrice}
    if proj is None or market is None:
        return {**base, "side": "none", "line": None, "edge": None, "modelSpreadHome": None,
                "modelTotal": None, "reason": "no projection at lock" if proj is None else "no spread at lock"}
    edge = round(proj["spreadHome"] - market, 2)  # model line minus market line, home perspective
    if edge < 0:
        side, line = "home", market  # model likes home more than the market does
    elif edge > 0:
        side, line = "away", -market
    else:
        side, line = "none", None
    return {**base, "side": side, "line": line, "edge": edge, "modelSpreadHome": proj["spreadHome"],
            "modelTotal": proj["total"], "reason": None if side != "none" else "model equals market"}


def run() -> int:
    games = store.games_by_id()
    n = 0
    for snap in store.snapshot_files():
        d = read_json(snap)
        for lines in d["games"]:
            gid = lines["gameId"]
            if gid not in games:
                continue
            fs_path, pick_path = store.first_seen_path(gid), store.model_pick_path(gid)
            locked_at = to_utc_iso(now_utc())
            if not fs_path.exists():
                write_once(fs_path, {**lines, "seenAt": d["takenAt"], "provider": d["provider"],
                                     "snapshot": str(snap.relative_to(ROOT))})
                proj = store.projection(gid, games[gid]["etDate"])
                write_once(pick_path, model_pick(gid, lines, proj, locked_at))
                n += 1
            elif not pick_path.exists():
                # first-seen was written but the pick was not (crash). Never back-fill with newer info.
                write_once(pick_path, model_pick(gid, read_json(fs_path), None, locked_at)
                           | {"reason": "pick not recorded at lock"})
    print(f"lock: {n} new games locked")
    return n
