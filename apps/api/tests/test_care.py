from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from app.models import MaintenanceKind
from app.services.care import (
    HANDLE_CLEAR_HOURS,
    calc_age,
    compute_clear_to_handle,
    compute_next_maintenance,
    days_countdown_label,
    feed_prep_note,
    format_duration,
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


def test_format_duration():
    assert format_duration(68 * 3600) == "2d 20h 0m"
    assert format_duration(2 * 86400 + 3 * 3600 + 5 * 60) == "2d 3h 5m"
    assert format_duration(45 * 60) == "45m"
    assert format_duration(5 * 3600 + 12 * 60) == "5h 12m"


def test_clear_to_handle_starts_at_created_at():
    started = datetime(2026, 8, 6, 22, 0, 0, tzinfo=timezone.utc)
    now = started + timedelta(hours=4)
    feed = SimpleNamespace(accepted=True, created_at=started, date=date(2026, 8, 6))
    out = compute_clear_to_handle(feed, 72, now=now)
    assert out["ready"] is False
    assert out["seconds_left"] == 68 * 3600
    assert out["countdown"] == "2d 20h 0m"
    assert out["clear_at"] is not None
    assert out["timer_started_at"] == started.isoformat()
    assert "timer" in out["message"]


def test_clear_to_handle_ready_after_72h():
    started = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    now = started + timedelta(hours=72, minutes=1)
    feed = SimpleNamespace(accepted=True, created_at=started, date=date(2026, 8, 1))
    out = compute_clear_to_handle(feed, 72, now=now)
    assert out["ready"] is True
    assert out["seconds_left"] == 0
    assert out["message"] == "Clear to handle"


def test_clear_to_handle_refused_skips_timer():
    started = datetime(2026, 8, 6, 22, 0, 0, tzinfo=timezone.utc)
    feed = SimpleNamespace(accepted=False, created_at=started, date=date(2026, 8, 6))
    out = compute_clear_to_handle(feed, 72, now=started)
    assert out["ready"] is True
    assert "refused" in out["message"].lower()


def test_clear_to_handle_no_feed():
    out = compute_clear_to_handle(None, 72)
    assert out["ready"] is True
    assert out["timer_started_at"] is None


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
    assert result["label"] == "Sub tray"
    assert result["days_until"] < 0


def test_all_maintenance_kinds():
    from app.services.care import compute_all_maintenance

    today = date(2026, 8, 10)
    rows = [
        SimpleNamespace(kind=MaintenanceKind.water, date=date(2026, 8, 9)),
        SimpleNamespace(kind=MaintenanceKind.substrate, date=date(2026, 8, 1)),
        SimpleNamespace(kind=MaintenanceKind.deep_clean, date=date(2026, 5, 1)),
    ]
    items = compute_all_maintenance(rows, today=today)
    assert len(items) == 3
    kinds = {i["kind"] for i in items}
    assert kinds == {"water", "substrate", "deep_clean"}
    deep = next(i for i in items if i["kind"] == "deep_clean")
    assert deep["overdue"] is True
    assert deep["label"] == "Deep clean"


def test_weight_log_status():
    from app.services.care import weight_log_status

    today = date(2026, 8, 10)
    none = weight_log_status(None, 7, today=today)
    assert none["due"] is True
    assert none["overdue"] is True

    fresh = weight_log_status(date(2026, 8, 8), 7, today=today)
    assert fresh["due"] is False
    assert fresh["days_until"] == 5

    due = weight_log_status(date(2026, 8, 3), 7, today=today)
    assert due["due"] is True
    assert due["days_until"] == 0

    overdue = weight_log_status(date(2026, 7, 1), 7, today=today)
    assert overdue["overdue"] is True


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
    assert DEFAULTS["handle_clear_hours"] == 72
    assert DEFAULTS["weight_log_interval_days"] == 7
    assert DEFAULTS["event_maint_water"] is True
    assert DEFAULTS["event_weight_due"] is True


def test_already_sent_helper_signature():
    assert callable(already_sent)
