from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSettings

DEFAULTS = {
    "email_enabled": True,
    "reminder_email": "allie.carpet.python@gmail.com",
    "timezone": "America/Chicago",
    "digest_enabled": True,
    "digest_time_1": "08:00",
    "digest_time_2": "20:00",
    "digest_second_enabled": True,
    "feed_ready_days": 2,
    "handle_clear_hours": 72,
    "handling_max_gap_days": 2,
    "maint_water_days": 3,
    "maint_substrate_days": 30,
    "maint_deep_clean_days": 90,
    "feed_interval_mode": "auto",
    "feed_interval_days": None,
    "event_handle_cleared": True,
    "event_feed_overdue": True,
    "event_handling_gap": True,
    "event_shed_status": True,
    "event_regurg": True,
    "digest_show_feed": True,
    "digest_show_maint": True,
    "digest_show_shed": True,
    "digest_show_handle": True,
    "digest_show_activity": True,
}


def get_or_create_settings(db: Session) -> AppSettings:
    row = db.get(AppSettings, 1)
    if row is None:
        row = AppSettings(id=1, **DEFAULTS)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def settings_to_dict(row: AppSettings) -> dict:
    return {k: getattr(row, k) for k in DEFAULTS}


def update_settings(db: Session, data: dict) -> AppSettings:
    row = get_or_create_settings(db)
    for key in DEFAULTS:
        if key in data:
            val = data[key]
            if key in ("digest_time_1", "digest_time_2") and isinstance(val, str) and len(val) >= 5:
                val = val[:5]
            setattr(row, key, val)
    db.commit()
    db.refresh(row)
    return row
