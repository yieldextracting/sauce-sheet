"""The gate fires at the right ET times on both sides of the 2026-11-01 DST change."""

from pipeline.et import parse_utc
from pipeline.gate import busy, due


def g(gid, et_date, tip, status="scheduled"):
    return {"id": gid, "etDate": et_date, "tipUtc": tip, "status": status}


def run(now_iso, games, days=None):
    return due(parse_utc(now_iso), {"days": days or {}, "lastUpdatedAt": None}, games)


DONE_DAILY = {"schedule": "x", "ratings": "x"}


def test_morning_snapshot_edt_and_est():
    # Before the change: 10:00 EDT = 14:00Z. After: 10:00 EST = 15:00Z.
    before = [g("a", "2026-10-30", "2026-10-30T23:00:00Z")]
    assert "odds_morning" not in run("2026-10-30T13:37:00Z", before, {"2026-10-30": DONE_DAILY})
    assert "odds_morning" in run("2026-10-30T14:07:00Z", before, {"2026-10-30": DONE_DAILY})
    after = [g("b", "2026-11-02", "2026-11-03T00:00:00Z")]
    assert "odds_morning" not in run("2026-11-02T14:37:00Z", after, {"2026-11-02": DONE_DAILY})  # 9:37 EST
    assert "odds_morning" in run("2026-11-02T15:07:00Z", after, {"2026-11-02": DONE_DAILY})      # 10:07 EST


def test_morning_snapshot_not_repeated():
    games = [g("a", "2026-10-30", "2026-10-30T23:00:00Z")]
    days = {"2026-10-30": {**DONE_DAILY, "odds_morning": "x"}}
    assert "odds_morning" not in run("2026-10-30T15:07:00Z", games, days)


def test_late_cron_still_catches_up():
    # cron delayed: first run of the day at 12:40 ET still takes the morning snapshot
    games = [g("a", "2026-10-30", "2026-10-30T23:00:00Z")]
    assert "odds_morning" in run("2026-10-30T16:40:00Z", games, {"2026-10-30": DONE_DAILY})


def test_pretip_120_minutes_before_first_tip():
    games = [g("a", "2026-11-02", "2026-11-03T00:00:00Z"), g("b", "2026-11-02", "2026-11-03T03:00:00Z")]
    days = {"2026-11-02": DONE_DAILY}
    assert "odds_pretip" not in run("2026-11-02T21:50:00Z", games, days)
    assert "odds_pretip" in run("2026-11-02T22:07:00Z", games, days)


def test_closing_window():
    games = [g("a", "2026-11-02", "2026-11-03T00:30:00Z")]
    days = {"2026-11-02": {**DONE_DAILY, "odds_morning": 1, "odds_afternoon": 1, "odds_pretip": 1}}
    assert "odds_closing" not in run("2026-11-02T23:37:00Z", games, days)  # 53 min before
    assert "odds_closing" in run("2026-11-03T00:07:00Z", games, days)      # 23 min before
    days["2026-11-02"]["closing"] = ["a"]
    assert "odds_closing" not in run("2026-11-03T00:07:00Z", games, days)


def test_no_odds_after_all_games_tipped():
    games = [g("a", "2026-11-02", "2026-11-03T00:00:00Z")]
    assert not [j for j in run("2026-11-03T02:07:00Z", games, {"2026-11-02": DONE_DAILY}) if j.startswith("odds")]


def test_late_night_run_is_previous_game_day_until_midnight_et():
    # 11:37 PM EST Nov 2 = 04:37Z Nov 3: still the Nov 2 game day
    out = run("2026-11-03T04:37:00Z", [], {"2026-11-02": DONE_DAILY})  # no games -> nothing
    assert out == []
    # 12:07 AM EST Nov 3 = 05:07Z: new day -> daily jobs due
    assert run("2026-11-03T05:07:00Z", [], {"2026-11-02": DONE_DAILY}) == ["schedule", "ratings"]


def test_injuries_every_run_from_9am_et_until_last_tip():
    games = [g("a", "2026-11-02", "2026-11-03T00:30:00Z")]
    days = {"2026-11-02": DONE_DAILY}
    assert "injuries" not in run("2026-11-02T13:37:00Z", games, days)  # 8:37 EST
    assert "injuries" in run("2026-11-02T14:07:00Z", games, days)      # 9:07 EST
    assert "injuries" in run("2026-11-03T00:07:00Z", games, days)      # 7:07 PM, still before tip
    assert "injuries" not in run("2026-11-03T01:07:00Z", games, days)  # all tipped


def test_postponed_games_ignored():
    games = [g("a", "2026-11-02", "2026-11-03T00:00:00Z", status="postponed")]
    assert not [j for j in run("2026-11-02T16:07:00Z", games, {"2026-11-02": DONE_DAILY}) if j.startswith("odds")]


def test_busy_keeps_the_job_alive_on_game_nights():
    games = [g("a", "2026-11-02", "2026-11-03T00:30:00Z"), g("b", "2026-11-02", "2026-11-03T03:00:00Z")]
    assert busy(parse_utc("2026-11-02T20:00:00Z"), games)        # first tip in 4.5h
    assert not busy(parse_utc("2026-11-02T14:00:00Z"), games)    # 10.5h away -> idle
    assert busy(parse_utc("2026-11-03T05:30:00Z"), games)        # after midnight ET, game b not final yet
    games = [{**x, "status": "final"} for x in games]
    assert not busy(parse_utc("2026-11-03T05:30:00Z"), games)
