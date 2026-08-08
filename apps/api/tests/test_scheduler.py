"""Tests for in-process scheduler helpers."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.scheduler import next_wall_datetime, parse_hhmm, wall_on_date


def test_parse_hhmm():
    assert parse_hhmm("08:00") == (8, 0)
    assert parse_hhmm("20:30") == (20, 30)
    assert parse_hhmm("8:00:00") == (8, 0)


def test_next_wall_datetime_same_day():
    tz = ZoneInfo("America/Chicago")
    now = datetime(2026, 8, 8, 7, 0, tzinfo=tz)
    nxt = next_wall_datetime(now, "08:00")
    assert nxt == datetime(2026, 8, 8, 8, 0, tzinfo=tz)


def test_next_wall_datetime_tomorrow():
    tz = ZoneInfo("America/Chicago")
    now = datetime(2026, 8, 8, 8, 1, tzinfo=tz)
    nxt = next_wall_datetime(now, "08:00")
    assert nxt == datetime(2026, 8, 9, 8, 0, tzinfo=tz)


def test_wall_on_date():
    tz = ZoneInfo("America/Chicago")
    when = wall_on_date(tz, datetime(2026, 8, 15).date(), "08:00")
    assert when.hour == 8
    assert when.day == 15
    assert when.tzinfo == tz
