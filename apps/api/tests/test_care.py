from datetime import date, timedelta
from types import SimpleNamespace

from app.models import MaintenanceKind
from app.services.care import (
    HANDLE_CLEAR_HOURS,
    calc_age,
    compute_next_maintenance,
    days_countdown_label,
    feed_prep_note,
)
from app.services.email_svc import already_sent
from app.services.feeding_rules import stage_from_months
from app.services.settings_svc import DEFAULTS


def test_calc_age_basic():
    dob = date(2025, 8, 21)
    now = date(2026, 5, 21)
    age = calc_age(dob, now)
    assert age["months"] == 9
    assert age["total"] == (now - dob).days


def test_stage_juvenile():
    stage = stage_from_months(9)
    assert stage["label"] == "Juvenile"
    assert stage["feed_interval_days"] == 8


def test_stage_hatchling():
    assert stage_from_months(1)["label"] == "Hatchling"


def test_stage_adult():
    assert stage_from_months(40)["label"] == "Adult"
    assert stage_from_months(40)["feed_interval_days"] == 17


def test_handle_clear_constant():
    assert HANDLE_CLEAR_HOURS == 72


def test_next_feed_math():
    last = date(2026, 8, 1)
    due = last + timedelta(days=8)
    assert due == date(2026, 8, 9)


def test_next_maintenance_never_logged():
    today = date(2026, 8, 6)
    result = compute_next_maintenance([], today=today)
    assert result is not None
    assert result["days_until"] == 0
    assert result["due_date"] == today.isoformat()


def test_next_maintenance_picks_soonest():
    today = date(2026, 8, 10)
    rows = [
        SimpleNamespace(kind=MaintenanceKind.water, date=date(2026, 8, 8)),
        SimpleNamespace(kind=MaintenanceKind.substrate, date=date(2026, 7, 1)),
        SimpleNamespace(kind=MaintenanceKind.deep_clean, date=date(2026, 6, 1)),
    ]
    result = compute_next_maintenance(rows, today=today)
    assert result["kind"] == "substrate"
    assert result["days_until"] < 0


def test_days_countdown_label():
    assert days_countdown_label(-2) == "overdue by 2 day(s)"
    assert days_countdown_label(0) == "today"
    assert days_countdown_label(1) == "tomorrow"
    assert days_countdown_label(5) == "in 5 days"


def test_feed_prep_note_window():
    assert feed_prep_note(5, 2) is None
    assert feed_prep_note(2, 2) is not None
    assert feed_prep_note(0, 2) is not None
    assert "overdue" in (feed_prep_note(-1, 2) or "").lower()


def test_settings_defaults():
    assert DEFAULTS["digest_time_1"] == "08:00"
    assert DEFAULTS["handling_max_gap_days"] == 2
    assert DEFAULTS["feed_ready_days"] == 2


def test_already_sent_helper_signature():
    # smoke: function exists and is callable
    assert callable(already_sent)
