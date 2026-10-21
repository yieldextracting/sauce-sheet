"""DST-safe scheduler logic. GitHub cron runs every 30 min in UTC; this decides what is due in ET.

Each job is "due and not yet done for this ET game day", never "is it exactly hour X", so the
Nov 1 clock change, delayed cron runs and dropped runs are all harmless.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from . import config, store
from .et import add_days, et_hour_minute, now_utc, parse_utc, to_utc_iso, today_et
from .io import read_json, write_json
from .paths import STATE

INJURY_START_ET_HOUR = 9  # pull the injury report every run from 09:00 ET until the last tip


def load_state() -> dict:
    return read_json(STATE, {"days": {}, "lastUpdatedAt": None})


def due(now: datetime | None = None, state: dict | None = None, games: list[dict] | None = None) -> list[str]:
    """Pure decision function (unit-tested). Returns job names."""
    now = now or now_utc()
    state = state if state is not None else load_state()
    games = games if games is not None else store.schedule()
    snap = config.odds().snapshots
    today = today_et(now)
    day = state["days"].get(today, {})
    hour, _ = et_hour_minute(now)
    jobs: list[str] = []

    if "schedule" not in day:
        jobs.append("schedule")
    if "ratings" not in day:
        jobs.append("ratings")

    todays = [g for g in games if g["etDate"] == today and g["status"] not in ("postponed", "cancelled")]
    upcoming = [g for g in todays if parse_utc(g["tipUtc"]) > now]
    if upcoming:
        if hour >= INJURY_START_ET_HOUR:
            jobs.append("injuries")
        first_tip = min(parse_utc(g["tipUtc"]) for g in todays)
        if hour >= snap.morningEtHour and "odds_morning" not in day:
            jobs.append("odds_morning")
        if hour >= snap.afternoonEtHour and "odds_afternoon" not in day:
            jobs.append("odds_afternoon")
        if now >= first_tip - timedelta(minutes=snap.preTipMinutesBeforeFirstTip) and "odds_pretip" not in day:
            jobs.append("odds_pretip")
        window = timedelta(minutes=snap.closingWindowMinutes)
        closing_done = set(day.get("closing", []))
        soon = [g["id"] for g in upcoming if parse_utc(g["tipUtc"]) - now <= window and g["id"] not in closing_done]
        if soon:
            jobs.append("odds_closing")
    return jobs


def busy(now: datetime | None = None, games: list[dict] | None = None, horizon_hours: float = 6.0) -> bool:
    """Is there pipeline work in the next few hours? (A game tipping soon, or one not yet final.)

    The Actions job keeps looping while this is true, so sparse GitHub cron triggers still give
    continuous coverage on game nights.
    """
    now = now or now_utc()
    games = games if games is not None else store.schedule()
    today = today_et(now)
    recent = {today, add_days(today, -1)}
    for g in games:
        if g["status"] in ("final", "postponed", "cancelled"):
            continue
        tip = parse_utc(g["tipUtc"])
        if g["etDate"] in recent and tip <= now:
            return True  # in progress or awaiting its final score
        if timedelta(0) < tip - now <= timedelta(hours=horizon_hours):
            return True
    return False


def closing_targets(now: datetime, games: list[dict], done: set[str]) -> list[str]:
    window = timedelta(minutes=config.odds().snapshots.closingWindowMinutes)
    return [g["id"] for g in games
            if g["status"] == "scheduled" and timedelta(0) < parse_utc(g["tipUtc"]) - now <= window
            and g["id"] not in done]


def auto() -> None:
    """Run whatever is due. Called by GitHub Actions every 30 minutes."""
    from .stages import (build_ratings, grade, lock, project_games, pull_injuries, pull_odds,
                         pull_results, pull_schedule)

    now = now_utc()
    today = today_et(now)
    state = load_state()
    day = state["days"].setdefault(today, {})
    jobs = due(now, state)
    print(f"auto @ {to_utc_iso(now)} (ET day {today}): due = {jobs or 'nothing scheduled'}")
    stamp = to_utc_iso(now)

    if "schedule" in jobs:
        pull_schedule.run()
        day["schedule"] = stamp

    new_finals = pull_results.run()  # cheap: only calls ESPN for games that should be over

    injuries_changed = False
    if "injuries" in jobs:
        try:
            injuries_changed = pull_injuries.run()["changed"]
        except SystemExit as e:  # an injury outage must not block odds, locks or grading
            print(f"auto: {e}")

    if new_finals or "ratings" in jobs:
        build_ratings.run()
        day["ratings"] = stamp
    if new_finals or "ratings" in jobs or injuries_changed:
        project_games.run()  # before any odds pull, so a lock uses the freshest projection

    odds_jobs = [j for j in jobs if j.startswith("odds_")]
    if odds_jobs:
        closing_before = closing_targets(now, store.schedule(), set(day.get("closing", [])))
        pull_odds.run()
        lock.run()
        for j in odds_jobs:
            if j != "odds_closing":
                day[j] = stamp
        day["closing"] = sorted(set(day.get("closing", [])) | set(closing_before))

    grade.run()

    # keep a week of state; only bump lastUpdatedAt when a job actually ran
    keep = {add_days(today, -i) for i in range(8)}
    state["days"] = {k: v for k, v in state["days"].items() if k in keep}
    if [j for j in jobs if j != "injuries"] or new_finals or injuries_changed:
        state["lastUpdatedAt"] = stamp
    write_json(STATE, state)
