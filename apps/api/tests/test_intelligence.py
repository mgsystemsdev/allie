"""Tests for deterministic care intelligence."""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.intelligence import (
    ENV_HOT_MAX,
    ENV_HOT_MIN,
    env_alerts,
    resolve_feed_interval,
    shed_prediction,
    suggest_prey,
    weight_alerts,
)


def _feed(d: date, prey: str, accepted: bool = True, fid: int = 1):
    return SimpleNamespace(id=fid, date=d, prey_type=prey, accepted=accepted)


def test_resolve_manual():
    out = resolve_feed_interval(
        feeds=[],
        regurg_dates=[],
        stage_label="Juvenile",
        mode="manual",
        manual_days=9,
        last_feed_accepted=True,
    )
    assert out["interval_days"] == 9
    assert out["interval_source"] == "manual"


def test_resolve_stage_only():
    out = resolve_feed_interval(
        feeds=[],
        regurg_dates=[],
        stage_label="Juvenile",
        mode="stage",
        manual_days=None,
        last_feed_accepted=True,
    )
    assert out["interval_days"] == 8
    assert out["interval_source"] == "stage"


def test_adaptive_median_clamped():
    # Juvenile band 7–10; gaps 14,14,14 → median 14 → clamp to 10
    base = date(2026, 1, 1)
    feeds = [
        _feed(base, "Norwegian pup", True, 1),
        _feed(base + timedelta(days=14), "Norwegian pup", True, 2),
        _feed(base + timedelta(days=28), "Norwegian pup", True, 3),
        _feed(base + timedelta(days=42), "Norwegian pup", True, 4),
    ]
    out = resolve_feed_interval(
        feeds=feeds,
        regurg_dates=[],
        stage_label="Juvenile",
        mode="auto",
        manual_days=None,
        last_feed_accepted=True,
    )
    assert out["interval_source"] == "adaptive"
    assert out["interval_days"] == 10  # clamped to max


def test_adaptive_refuse_extends():
    base = date(2026, 1, 1)
    feeds = [
        _feed(base + timedelta(days=i * 8), "Norwegian pup", True, i)
        for i in range(1, 5)
    ]
    out = resolve_feed_interval(
        feeds=feeds,
        regurg_dates=[],
        stage_label="Juvenile",
        mode="auto",
        manual_days=None,
        last_feed_accepted=False,
    )
    assert out["interval_days"] == min(10, 8 + 2)
    assert "refused" in out["why"].lower()


def test_adaptive_insufficient_falls_back():
    feeds = [_feed(date(2026, 1, 1), "Norwegian pup", True, 1)]
    out = resolve_feed_interval(
        feeds=feeds,
        regurg_dates=[],
        stage_label="Juvenile",
        mode="auto",
        manual_days=None,
        last_feed_accepted=True,
    )
    assert out["interval_source"] == "stage"
    assert out["interval_days"] == 8


def test_suggest_prey_prefers_accepted():
    today = date.today()
    feeds = [
        _feed(today - timedelta(days=10), "Norwegian weaned", True, 1),
        _feed(today - timedelta(days=20), "Norwegian weaned", True, 2),
        _feed(today - timedelta(days=30), "Norwegian fuzzy", True, 3),
    ]
    # Juvenile (~6 mo): Norwegian weaned is recommended
    out = suggest_prey(age_months=6, feeds=feeds, last_prey="Norwegian fuzzy")
    assert out["suggested_prey"] == "Norwegian weaned"
    assert out["prey_accept_counts"].get("Norwegian weaned", 0) >= 2


def test_suggest_prey_demotes_double_refuse():
    today = date.today()
    feeds = [
        _feed(today - timedelta(days=1), "Norwegian pup", False, 2),
        _feed(today - timedelta(days=8), "Norwegian pup", False, 1),
        _feed(today - timedelta(days=20), "Norwegian fuzzy", True, 0),
    ]
    out = suggest_prey(age_months=6, feeds=feeds, last_prey="Norwegian pup")
    assert "Norwegian pup" in out["demoted_prey"]
    assert out["suggested_prey"] != "Norwegian pup"


def test_weight_drop():
    today = date(2026, 8, 1)
    weights = [
        SimpleNamespace(id=1, date=today - timedelta(days=20), weight_g=200),
        SimpleNamespace(id=2, date=today - timedelta(days=10), weight_g=210),
        SimpleNamespace(id=3, date=today, weight_g=180),
    ]
    alerts = weight_alerts(weights, "Juvenile", today=today)
    kinds = [a["kind"] for a in alerts]
    assert "weight_drop" in kinds


def test_weight_stall_juvenile():
    today = date(2026, 8, 30)
    weights = [
        SimpleNamespace(id=1, date=today - timedelta(days=28), weight_g=200),
        SimpleNamespace(id=2, date=today - timedelta(days=14), weight_g=201),
        SimpleNamespace(id=3, date=today, weight_g=202),
    ]
    alerts = weight_alerts(weights, "Juvenile", today=today)
    assert any(a["kind"] == "weight_stall" for a in alerts)


def test_weight_no_stall_adult():
    today = date(2026, 8, 30)
    weights = [
        SimpleNamespace(id=1, date=today - timedelta(days=28), weight_g=800),
        SimpleNamespace(id=2, date=today - timedelta(days=14), weight_g=801),
        SimpleNamespace(id=3, date=today, weight_g=802),
    ]
    alerts = weight_alerts(weights, "Adult", today=today)
    assert not any(a["kind"] == "weight_stall" for a in alerts)


def test_shed_prediction_median():
    today = date(2026, 8, 1)
    sheds = [
        SimpleNamespace(started_at=date(2026, 1, 1), completed_at=date(2026, 1, 10)),
        SimpleNamespace(started_at=date(2026, 2, 15), completed_at=date(2026, 2, 25)),  # 45d
        SimpleNamespace(started_at=date(2026, 4, 1), completed_at=date(2026, 4, 12)),  # 45d
    ]
    pred = shed_prediction(sheds, today=today)
    assert pred is not None
    assert pred["median_days"] == 45
    assert pred["estimate_date"] == (date(2026, 4, 1) + timedelta(days=45)).isoformat()


def test_shed_prediction_insufficient():
    pred = shed_prediction(
        [SimpleNamespace(started_at=date(2026, 1, 1), completed_at=date(2026, 1, 10))],
        today=date(2026, 8, 1),
    )
    assert pred["estimate_date"] is None


def test_env_hot_out_of_band():
    now = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    reading = SimpleNamespace(
        recorded_at=now - timedelta(hours=1),
        temp_hot_f=ENV_HOT_MAX + 5,
        temp_cool_f=77,
        temp_night_f=72,
        humidity_pct=50,
    )
    alerts = env_alerts(reading, in_shed=False, now=now)
    assert any(a["kind"] == "env_hot" for a in alerts)
    assert ENV_HOT_MIN <= 90


def test_env_humidity_shed_band():
    now = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    reading = SimpleNamespace(
        recorded_at=now,
        temp_hot_f=92,
        temp_cool_f=77,
        temp_night_f=72,
        humidity_pct=45,  # too low for shed
    )
    alerts = env_alerts(reading, in_shed=True, now=now)
    assert any(a["kind"] == "env_humidity" for a in alerts)


def test_env_stale_none():
    alerts = env_alerts(None, in_shed=False)
    assert alerts[0]["kind"] == "env_stale"
