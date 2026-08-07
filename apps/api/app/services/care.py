from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Animal,
    AppSettings,
    EnvReading,
    Feed,
    Handling,
    Maintenance,
    MaintenanceKind,
    Regurgitation,
    ShedCycle,
    ShedStatus,
    Weight,
)
from app.services.feeding_rules import feeding_config, stage_from_months
from app.services.intelligence import (
    env_alerts,
    resolve_feed_interval,
    shed_alerts,
    shed_prediction,
    suggest_prey,
    weight_alerts,
)
from app.services.settings_svc import get_or_create_settings

HANDLE_CLEAR_HOURS = 72  # default fallback

MAINTENANCE_LABELS: dict[MaintenanceKind, str] = {
    MaintenanceKind.water: "Water",
    MaintenanceKind.substrate: "Sub tray",
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


def maintenance_intervals(cfg: AppSettings) -> dict[MaintenanceKind, int]:
    return {
        MaintenanceKind.water: cfg.maint_water_days,
        MaintenanceKind.substrate: cfg.maint_substrate_days,
        MaintenanceKind.deep_clean: cfg.maint_deep_clean_days,
    }


def compute_all_maintenance(
    rows: list[Maintenance],
    intervals: dict[MaintenanceKind, int] | None = None,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Due status for every maintenance kind (water, sub tray, deep clean)."""
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
                "overdue": days_until < 0,
                "due_today": days_until == 0,
            }
        )
    return sorted(candidates, key=lambda c: c["days_until"])


def compute_next_maintenance(
    rows: list[Maintenance],
    intervals: dict[MaintenanceKind, int] | None = None,
    today: date | None = None,
) -> dict[str, Any] | None:
    candidates = compute_all_maintenance(rows, intervals=intervals, today=today)
    if not candidates:
        return None
    soonest = candidates[0]
    return {
        "kind": soonest["kind"],
        "label": soonest["label"],
        "due_date": soonest["due_date"],
        "days_until": soonest["days_until"],
        "last_date": soonest["last_date"],
        "interval_days": soonest["interval_days"],
    }


def weight_log_status(
    last_weight_date: date | None,
    interval_days: int,
    today: date | None = None,
) -> dict[str, Any]:
    """When the next weight log is due based on settings interval."""
    today = today or date.today()
    interval = max(1, int(interval_days))
    if last_weight_date is None:
        return {
            "due": True,
            "overdue": True,
            "days_since": None,
            "days_until": 0,
            "due_date": today.isoformat(),
            "last_date": None,
            "interval_days": interval,
            "countdown": f"No weight logged — log every {interval}d",
        }
    due = last_weight_date + timedelta(days=interval)
    days_until = (due - today).days
    days_since = (today - last_weight_date).days
    return {
        "due": days_until <= 0,
        "overdue": days_until < 0,
        "days_since": days_since,
        "days_until": days_until,
        "due_date": due.isoformat(),
        "last_date": last_weight_date.isoformat(),
        "interval_days": interval,
        "countdown": (
            f"Weight overdue by {abs(days_until)} day(s)"
            if days_until < 0
            else ("Weight log due today" if days_until == 0 else f"Next weight {days_countdown_label(days_until)}")
        ),
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


def format_duration(seconds: float) -> str:
    """Human countdown like 2d 20h 15m / 68h 12m / 45m."""
    total = max(0, int(seconds))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def compute_clear_to_handle(
    last_feed: Feed | None,
    handle_hours: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """72h (configurable) post-feed wait. Timer starts at feed.created_at."""
    now = now or datetime.now(tz=ZoneInfo("UTC"))
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("UTC"))

    if last_feed is None:
        return {
            "ready": True,
            "hours_since_feed": None,
            "clear_after_hours": handle_hours,
            "hours_left": 0,
            "seconds_left": 0,
            "clear_at": None,
            "timer_started_at": None,
            "countdown": None,
            "message": "No feeds logged — clear to handle",
        }

    if not last_feed.accepted:
        started = last_feed.created_at
        if started is not None and started.tzinfo is None:
            started = started.replace(tzinfo=ZoneInfo("UTC"))
        return {
            "ready": True,
            "hours_since_feed": None,
            "clear_after_hours": handle_hours,
            "hours_left": 0,
            "seconds_left": 0,
            "clear_at": None,
            "timer_started_at": started.isoformat() if started else None,
            "countdown": None,
            "message": "Last feed refused — clear to handle",
        }

    started = last_feed.created_at
    if started is None:
        # Legacy fallback: midnight on feed date (UTC)
        started = datetime.combine(last_feed.date, datetime.min.time(), tzinfo=ZoneInfo("UTC"))
    elif started.tzinfo is None:
        started = started.replace(tzinfo=ZoneInfo("UTC"))

    clear_at = started + timedelta(hours=handle_hours)
    seconds_left = (clear_at - now).total_seconds()
    hours_since = (now - started).total_seconds() / 3600
    ready = seconds_left <= 0
    seconds_left_pos = max(0, seconds_left)
    hours_left = seconds_left_pos / 3600
    countdown = format_duration(seconds_left_pos) if not ready else None

    if ready:
        message = "Clear to handle"
    else:
        message = f"Wait {countdown} more after feed (72h timer)" if handle_hours == 72 else (
            f"Wait {countdown} more after feed ({handle_hours}h timer)"
        )

    return {
        "ready": ready,
        "hours_since_feed": round(hours_since, 1),
        "clear_after_hours": handle_hours,
        "hours_left": round(hours_left, 2) if not ready else 0,
        "seconds_left": int(seconds_left_pos) if not ready else 0,
        "clear_at": clear_at.isoformat(),
        "timer_started_at": started.isoformat(),
        "countdown": countdown,
        "message": message,
    }


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
    handle_hours = cfg.handle_clear_hours
    ready_days = cfg.feed_ready_days
    gap_max = cfg.handling_max_gap_days

    feeds = list(
        db.scalars(select(Feed).where(Feed.animal_id == animal.id).order_by(Feed.date.desc(), Feed.id.desc()))
    )
    last_feed = feeds[0] if feeds else None

    regurg_rows = list(
        db.scalars(
            select(Regurgitation)
            .where(Regurgitation.animal_id == animal.id)
            .order_by(Regurgitation.date.desc(), Regurgitation.id.desc())
        )
    )
    regurg_dates = [r.date for r in regurg_rows]

    interval_info = resolve_feed_interval(
        feeds=feeds,
        regurg_dates=regurg_dates,
        stage_label=stage["label"],
        mode=cfg.feed_interval_mode,
        manual_days=cfg.feed_interval_days,
        last_feed_accepted=last_feed.accepted if last_feed else None,
    )
    interval = int(interval_info["interval_days"])

    feeding_recommendation = suggest_prey(
        age_months=age["months"],
        feeds=feeds,
        last_prey=last_feed.prey_type if last_feed else None,
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
    maintenance_items = compute_all_maintenance(
        maintenance_rows, intervals=maintenance_intervals(cfg), today=date.today()
    )
    weight_due = weight_log_status(
        last_weight.date if last_weight else None,
        cfg.weight_log_interval_days,
        today=date.today(),
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
    completed_sheds = list(
        db.scalars(
            select(ShedCycle)
            .where(ShedCycle.animal_id == animal.id, ShedCycle.status == ShedStatus.shed)
            .order_by(ShedCycle.started_at.asc())
        )
    )
    latest_env = db.scalar(
        select(EnvReading)
        .where(EnvReading.animal_id == animal.id)
        .order_by(EnvReading.recorded_at.desc(), EnvReading.id.desc())
        .limit(1)
    )

    next_feed: dict[str, Any] | None = None
    reminders: list[dict[str, str]] = []
    today = date.today()
    now = local_now(cfg)

    if last_feed:
        due = last_feed.date + timedelta(days=interval)
        days_until = (due - today).days
        next_feed = {
            "due_date": due.isoformat(),
            "days_until": days_until,
            "last_feed_date": last_feed.date.isoformat(),
            "interval_days": interval,
            "interval_source": interval_info["interval_source"],
            "interval_why": interval_info["why"],
            "countdown": days_countdown_label(days_until),
            "prep_note": feed_prep_note(days_until, ready_days),
        }
        if days_until < 0:
            band = interval_info["band"]
            reminders.append(
                {
                    "kind": "feed_overdue",
                    "message": f"Feed overdue by {abs(days_until)} day(s) — offer prey when ready",
                    "severity": "high",
                    "why": (
                        f"After this feed, resume normal {interval}d schedule "
                        f"(safe band {band['min_days']}–{band['max_days']}d). "
                        "Don't stretch the next gap just because this one was late."
                    ),
                }
            )
        elif days_until <= ready_days:
            band = interval_info["band"]
            reminders.append(
                {
                    "kind": "feed_due",
                    "message": f"Feed {days_countdown_label(days_until)}"
                    + (" — thaw/prep prey" if days_until > 0 else ""),
                    "severity": "medium",
                    "why": (
                        f"Scheduled every {interval}d "
                        f"(safe {band['min_days']}–{band['max_days']}d). {interval_info['why']}"
                    ),
                }
            )

    clear_to_handle = compute_clear_to_handle(last_feed, handle_hours, now=now)
    if last_feed is None:
        reminders.append(
            {
                "kind": "feed_none",
                "message": "No feeds logged yet",
                "severity": "low",
            }
        )
    elif not clear_to_handle["ready"]:
        reminders.append(
            {
                "kind": "handle_wait",
                "message": clear_to_handle["message"],
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
                "why": f"Interval {next_maintenance['interval_days']}d · last {next_maintenance['last_date'] or 'never'}",
            }
        )
    elif next_maintenance and next_maintenance["days_until"] <= ready_days:
        reminders.append(
            {
                "kind": "maintenance_due",
                "message": f"{next_maintenance['label']} {days_countdown_label(next_maintenance['days_until'])}",
                "severity": "low",
                "why": f"Interval {next_maintenance['interval_days']}d · last {next_maintenance['last_date'] or 'never'}",
            }
        )

    # Per-kind overdue reminders (water / sub tray / deep clean)
    for item in maintenance_items:
        if item["overdue"] and item["kind"] != (next_maintenance or {}).get("kind"):
            reminders.append(
                {
                    "kind": f"maint_{item['kind']}",
                    "message": f"{item['label']} overdue by {abs(item['days_until'])} day(s)",
                    "severity": "medium",
                    "why": f"Every {item['interval_days']}d · last {item['last_date'] or 'never'}",
                }
            )

    if weight_due["due"]:
        reminders.append(
            {
                "kind": "weight_due",
                "message": weight_due["countdown"],
                "severity": "medium" if weight_due["overdue"] else "low",
                "why": f"Weight log every {weight_due['interval_days']}d · last {weight_due['last_date'] or 'never'}",
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
                "why": "Active shed cycle — humidity target 60–70%",
            }
        )

    shed_pred = shed_prediction(completed_sheds, today=today)
    reminders.extend(shed_alerts(shed_pred, active_shed=active_shed is not None))
    reminders.extend(weight_alerts(weights, stage["label"], today=today))
    reminders.extend(
        env_alerts(latest_env, in_shed=active_shed is not None, now=now)
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
        "maintenance_items": maintenance_items,
        "weight_due": weight_due,
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
        "shed_prediction": shed_pred,
        "clear_to_handle": clear_to_handle,
        "shed_mode": shed_mode,
        "reminders": reminders,
        "settings_snapshot": {
            "feed_ready_days": ready_days,
            "handle_clear_hours": handle_hours,
            "handling_max_gap_days": gap_max,
            "feed_interval_mode": cfg.feed_interval_mode,
            "weight_log_interval_days": cfg.weight_log_interval_days,
        },
    }
