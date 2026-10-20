"""ET date logic around midnight and the 2026-11-01 / 2027-03-14 DST changes."""

from datetime import datetime, timezone
from pathlib import Path

from pipeline.et import et_date, et_hour_minute, et_wall_to_utc, parse_utc, to_utc_iso

UTC = timezone.utc


def test_late_west_coast_game_belongs_to_tip_date():
    # 10:30 PM EDT Oct 20 tip = 02:30Z Oct 21. Game day is Oct 20.
    assert et_date("2026-10-21T02:30:00Z") == "2026-10-20"
    # 11:59 PM EDT is still Oct 20; 12:00 AM is Oct 21
    assert et_date("2026-10-21T03:59:00Z") == "2026-10-20"
    assert et_date("2026-10-21T04:00:00Z") == "2026-10-21"


def test_midnight_boundary_in_winter_uses_est_offset():
    # After the change ET = UTC-5, so midnight is 05:00Z
    assert et_date("2026-12-02T04:59:00Z") == "2026-12-01"
    assert et_date("2026-12-02T05:00:00Z") == "2026-12-02"


def test_fall_back_repeated_hour_maps_to_same_day():
    # 2026-11-01 01:30 happens twice: 05:30Z (EDT) and 06:30Z (EST)
    assert et_date("2026-11-01T05:30:00Z") == "2026-11-01"
    assert et_date("2026-11-01T06:30:00Z") == "2026-11-01"
    assert et_hour_minute(parse_utc("2026-11-01T05:30:00Z")) == (1, 30)
    assert et_hour_minute(parse_utc("2026-11-01T06:30:00Z")) == (1, 30)


def test_halloween_late_tip_ending_after_change():
    # 10:30 PM EDT Oct 31 = 02:30Z Nov 1. Ends ~01:00 EST Nov 1 (06:00Z). Game day Oct 31.
    assert et_date("2026-11-01T02:30:00Z") == "2026-10-31"


def test_wall_clock_to_utc_shifts_with_dst():
    assert to_utc_iso(et_wall_to_utc("2026-10-30", 10)) == "2026-10-30T14:00:00Z"  # EDT
    assert to_utc_iso(et_wall_to_utc("2026-11-02", 10)) == "2026-11-02T15:00:00Z"  # EST
    assert to_utc_iso(et_wall_to_utc("2027-03-15", 10)) == "2027-03-15T14:00:00Z"  # EDT again


def test_spring_forward_day():
    # 2027-03-14 02:00 -> 03:00. 06:59Z is 01:59 EST, 07:00Z is 03:00 EDT.
    assert et_hour_minute(parse_utc("2027-03-14T06:59:00Z")) == (1, 59)
    assert et_hour_minute(parse_utc("2027-03-14T07:00:00Z")) == (3, 0)
    assert et_date("2027-03-14T07:00:00Z") == "2027-03-14"


def test_no_naive_now_in_pipeline():
    root = Path(__file__).resolve().parent.parent
    offenders = []
    for p in root.rglob("*.py"):
        if "tests" in p.parts:
            continue
        text = p.read_text()
        for bad in ("datetime.now()", "datetime.utcnow(", "date.today(", "time.localtime("):
            if bad in text:
                offenders.append(f"{p.name}: {bad}")
    assert not offenders, offenders


def test_parse_rejects_naive():
    import pytest
    with pytest.raises(ValueError):
        parse_utc("2026-10-20T19:00:00")
    assert parse_utc("2026-10-20T19:00Z") == datetime(2026, 10, 20, 19, 0, tzinfo=UTC)
