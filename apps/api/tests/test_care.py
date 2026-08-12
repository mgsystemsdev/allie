from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

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


def test_clear_to_handle_today_uses_created_at():
    tz = ZoneInfo("UTC")
    started = datetime(2026, 8, 6, 14, 0, 0, tzinfo=tz)
    now = started + timedelta(hours=4)
    feed = SimpleNamespace(accepted=True, created_at=started, date=date(2026, 8, 6))
    out = compute_clear_to_handle(feed, 72, now=now, tz=tz)
    assert out["ready"] is False
    assert out["seconds_left"] == 68 * 3600
    assert out["countdown"] == "2d 20h 0m"
    assert out["timer_started_at"] == started.isoformat()
    assert "timer" in out["message"]


def test_clear_to_handle_backdated_starts_at_10pm():
    tz = ZoneInfo("America/Chicago")
    feed_date = date(2026, 8, 5)
    now = datetime(2026, 8, 6, 12, 0, 0, tzinfo=tz)
    feed = SimpleNamespace(accepted=True, created_at=now, date=feed_date)
    out = compute_clear_to_handle(feed, 72, now=now, tz=tz)
    expected_start = datetime(2026, 8, 5, 22, 0, 0, tzinfo=tz)
    assert out["timer_started_at"] == expected_start.isoformat()
    assert out["ready"] is False
    clear_at = expected_start + timedelta(hours=72)
    assert out["seconds_left"] == int((clear_at - now).total_seconds())


def test_clear_to_handle_backdated_already_clear():
    tz = ZoneInfo("UTC")
    now = datetime(2026, 8, 8, 12, 0, 0, tzinfo=tz)
    feed = SimpleNamespace(
        accepted=True,
        created_at=now,
        date=date(2026, 8, 1),
    )
    out = compute_clear_to_handle(feed, 72, now=now, tz=tz)
    assert out["ready"] is True
    assert out["seconds_left"] == 0
    assert out["message"] == "Clear to handle"
    assert out["timer_started_at"] == datetime(2026, 8, 1, 22, 0, 0, tzinfo=tz).isoformat()


def test_clear_to_handle_ready_after_72h_from_live():
    tz = ZoneInfo("UTC")
    now = datetime(2026, 8, 4, 12, 1, 0, tzinfo=tz)
    feed = SimpleNamespace(
        accepted=True,
        created_at=now - timedelta(hours=72, minutes=1),
        date=now.date(),
    )
    out = compute_clear_to_handle(feed, 72, now=now, tz=tz)
    assert out["ready"] is True
    assert out["seconds_left"] == 0
    assert out["message"] == "Clear to handle"


def test_clear_to_handle_refused_skips_timer():
    tz = ZoneInfo("UTC")
    started = datetime(2026, 8, 6, 22, 0, 0, tzinfo=tz)
    feed = SimpleNamespace(accepted=False, created_at=started, date=date(2026, 8, 6))
    out = compute_clear_to_handle(feed, 72, now=started, tz=tz)
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


# --- hero photo ---

from datetime import date as _date

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import require_auth
from app.db import Base, get_db
from app.models import Animal, Photo, PhotoKind
from app.routers import core, extras


def _hero_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


def _hero_client(engine):
    TestingSession = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

    def _get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(core.router)
    app.include_router(extras.router)
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[require_auth] = lambda: None
    return TestClient(app), TestingSession


def _seed_allie(session, *, with_photo=True):
    animal = Animal(
        name="Allie",
        species="Morelia spilota",
        common_name="Carpet python",
        dob=_date(2025, 8, 21),
        sex="female",
        owner="Miguel",
        status="Active & Healthy",
    )
    session.add(animal)
    session.commit()
    session.refresh(animal)
    photo = None
    if with_photo:
        photo = Photo(
            animal_id=animal.id,
            taken_at=_date(2026, 8, 1),
            kind=PhotoKind.growth,
            file_path="/tmp/allie-hero.jpg",
            caption="",
        )
        session.add(photo)
        session.commit()
        session.refresh(photo)
    return animal, photo


def test_overview_includes_hero_fields_null():
    engine = _hero_engine()
    Base.metadata.create_all(engine)
    client, Session = _hero_client(engine)
    db = Session()
    _seed_allie(db, with_photo=False)
    db.close()

    res = client.get("/api/animal")
    assert res.status_code == 200
    body = res.json()
    assert body["hero_photo_id"] is None
    assert body["hero_photo_url"] is None


def test_patch_hero_set_and_clear():
    engine = _hero_engine()
    Base.metadata.create_all(engine)
    client, Session = _hero_client(engine)
    db = Session()
    _animal, photo = _seed_allie(db)
    photo_id = photo.id
    db.close()

    res = client.patch("/api/animal", json={"hero_photo_id": photo_id})
    assert res.status_code == 200
    body = res.json()
    assert body["hero_photo_id"] == photo_id
    assert body["hero_photo_url"] == "/uploads/allie-hero.jpg"

    res = client.patch("/api/animal", json={"hero_photo_id": None})
    assert res.status_code == 200
    body = res.json()
    assert body["hero_photo_id"] is None
    assert body["hero_photo_url"] is None


def test_patch_hero_missing_photo_404():
    engine = _hero_engine()
    Base.metadata.create_all(engine)
    client, Session = _hero_client(engine)
    db = Session()
    _seed_allie(db, with_photo=False)
    db.close()

    res = client.patch("/api/animal", json={"hero_photo_id": 999})
    assert res.status_code == 404


def test_delete_photo_clears_hero():
    engine = _hero_engine()
    Base.metadata.create_all(engine)
    client, Session = _hero_client(engine)
    db = Session()
    _animal, photo = _seed_allie(db)
    photo_id = photo.id
    db.close()

    assert client.patch("/api/animal", json={"hero_photo_id": photo_id}).status_code == 200
    assert client.delete(f"/api/photos/{photo_id}").status_code == 200
    res = client.get("/api/animal")
    assert res.status_code == 200
    assert res.json()["hero_photo_id"] is None
    assert res.json()["hero_photo_url"] is None
