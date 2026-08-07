from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Animal,
    AppSettings,
    Feed,
    Handling,
    Maintenance,
    MaintenanceKind,
    ShedCycle,
    ShedStatus,
    Weight,
)
from app.services.feeding_rules import feeding_config, recommend_feeding, stage_from_months
from app.services.settings_svc import get_or_create_settings

HANDLE_CLEAR_HOURS = 72  # default fallback

MAINTENANCE_LABELS: dict[MaintenanceKind, str] = {
    MaintenanceKind.water: "Water",
    MaintenanceKind.substrate: "Substrate",
    MaintenanceKind.deep_clean: "Deep clean",
}


def calc_age(dob: date, now: date | None = None) -> dict[str, int]:
    now = now or date.today()
    months = (now.year - dob.year) * 12 + (now.month - dob.month)
    if now.day < dob.day:
        months -= 1
    y = dob.year + (dob.month - 1 + months) // 12
    m = (dob.month - 1 + months) % 12 + 1
    try:
        tmp = date(y, m, dob.day)
    except ValueError:
        if m == 12:
            tmp = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            tmp = date(y, m + 1, 1) - timedelta(days=1)
    days = (now - tmp).days
    total = (now - dob).days
    return {"months": max(months, 0), "days": max(days, 0), "total": max(total, 0)}


def get_animal(db: Session) -> Animal | None:
    return db.scalar(select(Animal).order_by(Animal.id).limit(1))


def feed_interval_days(stage: dict[str, str], cfg: AppSettings) -> int:
    if cfg.feed_interval_mode == "manual" and cfg.feed_interval_days:
        return int(cfg.feed_interval_days)
    return int(stage["feed_interval_days"])


def maintenance_intervals(cfg: AppSettings) -> dict[MaintenanceKind, int]:
    return {
        MaintenanceKind.water: cfg.maint_water_days,
        MaintenanceKind.substrate: cfg.maint_substrate_days,
        MaintenanceKind.deep_clean: cfg.maint_deep_clean_days,
    }


def compute_next_maintenance(
    rows: list[Maintenance],
    intervals: dict[MaintenanceKind, int] | None = None,
    today: date | None = None,
) -> dict[str, Any] | None:
    today = today or date.today()
    intervals = intervals or {
        MaintenanceKind.water: 3,
        MaintenanceKind.substrate: 30,
        MaintenanceKind.deep_clean: 90,
    }
    last_by_kind: dict[MaintenanceKind, date] = {}
    for row in rows:
        prev = last_by_kind.get(row.kind)
        if prev is None or row.date > prev:
            last_by_kind[row.kind] = row.date

    candidates: list[dict[str, Any]] = []
    for kind, interval in intervals.items():
        last = last_by_kind.get(kind)
        if last is None:
            due = today
            last_date = None
        else:
            due = last + timedelta(days=interval)
            last_date = last.isoformat()
        days_until = (due - today).days
        candidates.append(
            {
                "kind": kind.value,
                "label": MAINTENANCE_LABELS[kind],
                "due_date": due.isoformat(),
                "days_until": days_until,
                "last_date": last_date,
                "interval_days": interval,
            }
        )

    if not candidates:
        return None
    soonest = min(candidates, key=lambda c: c["days_until"])
    return {
        "kind": soonest["kind"],
        "label": soonest["label"],
        "due_date": soonest["due_date"],
        "days_until": soonest["days_until"],
        "last_date": soonest["last_date"],
        "interval_days": soonest["interval_days"],
    }


def days_countdown_label(days_until: int) -> str:
    if days_until < 0:
        return f"overdue by {abs(days_until)} day(s)"
    if days_until == 0:
        return "today"
    if days_until == 1:
        return "tomorrow"
    return f"in {days_until} days"


def feed_prep_note(days_until: int, ready_days: int) -> str | None:
    if days_until < 0:
        return "Feed overdue — offer prey when ready"
    if days_until <= ready_days:
        return "Get ready — thaw/prep prey"
    return None


def local_now(cfg: AppSettings) -> datetime:
    try:
        tz = ZoneInfo(cfg.timezone)
    except Exception:
        tz = ZoneInfo("America/Chicago")
    return datetime.now(tz)


def build_overview(db: Session) -> dict[str, Any]:
    animal = get_animal(db)
    if animal is None:
        raise ValueError("No animal seeded")

    cfg = get_or_create_settings(db)
    age = calc_age(animal.dob)
    stage = stage_from_months(age["months"])
    interval = feed_interval_days(stage, cfg)
    handle_hours = cfg.handle_clear_hours
    ready_days = cfg.feed_ready_days
    gap_max = cfg.handling_max_gap_days

    feeds = list(
        db.scalars(select(Feed).where(Feed.animal_id == animal.id).order_by(Feed.date.desc(), Feed.id.desc()))
    )
    last_feed = feeds[0] if feeds else None
    feeding_recommendation = recommend_feeding(
        age["months"], last_feed.prey_type if last_feed else None
    )
    prey_cfg = feeding_config()

    weights = list(
        db.scalars(
            select(Weight).where(Weight.animal_id == animal.id).order_by(Weight.date.desc(), Weight.id.desc())
        )
    )
    last_weight = weights[0] if weights else None

    maintenance_rows = list(
        db.scalars(
            select(Maintenance)
            .where(Maintenance.animal_id == animal.id)
            .order_by(Maintenance.date.desc(), Maintenance.id.desc())
        )
    )
    next_maintenance = compute_next_maintenance(
        maintenance_rows, intervals=maintenance_intervals(cfg)
    )

    handlings = list(
        db.scalars(
            select(Handling)
            .where(Handling.animal_id == animal.id)
            .order_by(Handling.date.desc(), Handling.id.desc())
        )
    )
    last_handling = handlings[0] if handlings else None

    active_shed = db.scalar(
        select(ShedCycle)
        .where(
            ShedCycle.animal_id == animal.id,
            ShedCycle.status.in_([ShedStatus.blue, ShedStatus.opaque]),
        )
        .order_by(ShedCycle.started_at.desc())
        .limit(1)
    )
    last_completed_shed = db.scalar(
        select(ShedCycle)
        .where(ShedCycle.animal_id == animal.id, ShedCycle.status == ShedStatus.shed)
        .order_by(ShedCycle.completed_at.desc().nulls_last(), ShedCycle.id.desc())
        .limit(1)
    )

    next_feed: dict[str, Any] | None = None
    clear_to_handle: dict[str, Any]
    reminders: list[dict[str, str]] = []
    today = date.today()

    if last_feed:
        due = last_feed.date + timedelta(days=interval)
        days_until = (due - today).days
        next_feed = {
            "due_date": due.isoformat(),
            "days_until": days_until,
            "last_feed_date": last_feed.date.isoformat(),
            "interval_days": interval,
            "countdown": days_countdown_label(days_until),
            "prep_note": feed_prep_note(days_until, ready_days),
        }
        if days_until < 0:
            reminders.append(
                {
                    "kind": "feed_overdue",
                    "message": f"Feed overdue by {abs(days_until)} day(s)",
                    "severity": "high",
                }
            )
        elif days_until <= ready_days:
            reminders.append(
                {
                    "kind": "feed_due",
                    "message": f"Feed {days_countdown_label(days_until)}"
                    + (" — thaw/prep prey" if days_until > 0 else ""),
                    "severity": "medium",
                }
            )

        feed_dt = datetime.combine(last_feed.date, datetime.min.time())
        hours_since = (datetime.now() - feed_dt).total_seconds() / 3600
        ready = (not last_feed.accepted) or hours_since >= handle_hours
        hours_left = max(0, int(handle_hours - hours_since))
        clear_to_handle = {
            "ready": ready,
            "hours_since_feed": round(hours_since, 1),
            "clear_after_hours": handle_hours,
            "hours_left": hours_left if not ready else 0,
            "message": "Clear to handle" if ready else f"Wait ~{hours_left}h more after feed",
        }
        if not ready:
            reminders.append(
                {
                    "kind": "handle_wait",
                    "message": clear_to_handle["message"],
                    "severity": "low",
                }
            )
    else:
        clear_to_handle = {
            "ready": True,
            "hours_since_feed": None,
            "clear_after_hours": handle_hours,
            "hours_left": 0,
            "message": "No feeds logged — clear to handle",
        }
        reminders.append(
            {
                "kind": "feed_none",
                "message": "No feeds logged yet",
                "severity": "low",
            }
        )

    # Handling gap
    if last_handling:
        days_since = (today - last_handling.date).days
        gap_due = days_since > gap_max
        handling_gap = {
            "last_date": last_handling.date.isoformat(),
            "days_since": days_since,
            "max_gap_days": gap_max,
            "overdue": gap_due,
            "countdown": f"{days_since} day(s) since last handling"
            + (f" — overdue (max {gap_max}d)" if gap_due else f" (max {gap_max}d)"),
        }
        if gap_due and clear_to_handle["ready"]:
            reminders.append(
                {
                    "kind": "handling_gap",
                    "message": f"No handling in {days_since} days (max {gap_max})",
                    "severity": "medium",
                }
            )
    else:
        handling_gap = {
            "last_date": None,
            "days_since": None,
            "max_gap_days": gap_max,
            "overdue": True,
            "countdown": f"Never handled — aim for every {gap_max} day(s)",
        }
        if clear_to_handle["ready"]:
            reminders.append(
                {
                    "kind": "handling_gap",
                    "message": f"No handling logged yet (target every {gap_max}d)",
                    "severity": "low",
                }
            )

    if next_maintenance and next_maintenance["days_until"] < 0:
        reminders.append(
            {
                "kind": "maintenance_overdue",
                "message": f"{next_maintenance['label']} overdue by {abs(next_maintenance['days_until'])} day(s)",
                "severity": "medium",
            }
        )
    elif next_maintenance and next_maintenance["days_until"] <= ready_days:
        reminders.append(
            {
                "kind": "maintenance_due",
                "message": f"{next_maintenance['label']} {days_countdown_label(next_maintenance['days_until'])}",
                "severity": "low",
            }
        )

    shed_mode = {
        "active": active_shed is not None,
        "status": active_shed.status.value if active_shed else "clear",
        "humidity_target": "60–70%" if active_shed else "40–60%",
        "dont_feed": active_shed is not None and active_shed.status == ShedStatus.opaque,
        "started_at": active_shed.started_at.isoformat() if active_shed else None,
    }
    if active_shed:
        reminders.append(
            {
                "kind": "shed_humidity",
                "message": f"In shed ({active_shed.status.value}) — raise humidity to 60–70%"
                + ("; do not feed while opaque" if active_shed.status == ShedStatus.opaque else ""),
                "severity": "medium",
            }
        )

    return {
        "id": animal.id,
        "name": animal.name,
        "species": animal.species,
        "common_name": animal.common_name,
        "dob": animal.dob.isoformat(),
        "sex": animal.sex,
        "owner": animal.owner,
        "status": animal.status,
        "age": age,
        "stage": stage,
        "prey_categories": prey_cfg["prey_categories"],
        "feeding_stages": prey_cfg["stages"],
        "feeding_recommendation": feeding_recommendation,
        "total_feeds": len(feeds),
        "last_feed": (
            {
                "id": last_feed.id,
                "date": last_feed.date.isoformat(),
                "prey_type": last_feed.prey_type,
                "accepted": last_feed.accepted,
            }
            if last_feed
            else None
        ),
        "next_feed": next_feed,
        "next_maintenance": next_maintenance,
        "handling_gap": handling_gap,
        "current_weight_g": last_weight.weight_g if last_weight else None,
        "current_weight_date": last_weight.date.isoformat() if last_weight else None,
        "last_shed": (
            {
                "id": last_completed_shed.id,
                "date": (last_completed_shed.completed_at or last_completed_shed.started_at).isoformat(),
                "quality": last_completed_shed.quality,
            }
            if last_completed_shed
            else None
        ),
        "clear_to_handle": clear_to_handle,
        "shed_mode": shed_mode,
        "reminders": reminders,
        "settings_snapshot": {
            "feed_ready_days": ready_days,
            "handle_clear_hours": handle_hours,
            "handling_max_gap_days": gap_max,
        },
    }
