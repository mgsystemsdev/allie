from datetime import date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmailSendLog, Feed, Handling, Maintenance, Regurgitation
from app.services.care import build_overview, days_countdown_label, get_animal, local_now
from app.services.settings_svc import get_or_create_settings


def already_sent(db: Session, dedupe_key: str) -> bool:
    return db.scalar(select(EmailSendLog).where(EmailSendLog.dedupe_key == dedupe_key)) is not None


def record_sent(db: Session, kind: str, dedupe_key: str) -> None:
    if already_sent(db, dedupe_key):
        return
    db.add(EmailSendLog(kind=kind, dedupe_key=dedupe_key))
    db.commit()


def send_resend(to: str, subject: str, html: str, text: str) -> dict[str, Any]:
    cfg = get_settings()
    if not cfg.resend_api_key:
        return {"ok": False, "error": "RESEND_API_KEY not configured"}
    if not to:
        return {"ok": False, "error": "No reminder_email configured"}
    payload = {
        "from": cfg.resend_from,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    with httpx.Client(timeout=20.0) as client:
        res = client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {cfg.resend_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if res.status_code >= 400:
        return {"ok": False, "error": res.text, "status": res.status_code}
    return {"ok": True, "data": res.json()}


def _section(title: str, body: str) -> str:
    return f"<h2 style='color:#C4946A;font-size:14px;margin:20px 0 8px;font-family:monospace'>{title}</h2><p style='margin:0;color:#F2E8D9;line-height:1.5'>{body}</p>"


def build_digest_content(overview: dict[str, Any], cfg, recent: list[str]) -> tuple[str, str, str]:
    name = overview.get("name", "Allie")
    handle = overview["clear_to_handle"]
    feed = overview.get("next_feed")
    maint = overview.get("next_maintenance")
    shed = overview.get("shed_mode")
    last_shed = overview.get("last_shed")
    gap = overview.get("handling_gap")

    subject = f"{name} care digest — {date.today().isoformat()}"

    html_parts = [
        "<div style='background:#1a0e08;padding:24px;font-family:Lato,sans-serif;color:#F2E8D9'>",
        f"<h1 style='font-family:Georgia,serif;color:#F2E8D9'>{name} — daily care</h1>",
    ]
    text_parts = [f"{name} — daily care", ""]

    if cfg.digest_show_handle:
        h = handle["message"]
        if handle["ready"]:
            block = f"<strong style='color:#8FA669'>CLEAR TO HANDLE</strong><br/>{h}"
        else:
            block = f"<strong style='color:#D4A040'>WAIT TO HANDLE</strong><br/>{h}"
        html_parts.append(
            "<div style='border:1px solid #C4946A;border-radius:10px;padding:14px;background:#2C201A;margin:12px 0'>"
            + block
            + "</div>"
        )
        text_parts.append("CLEAR TO HANDLE" if handle["ready"] else "WAIT TO HANDLE")
        text_parts.append(h)
        text_parts.append("")

    if cfg.digest_show_feed:
        if feed:
            line = f"Next feed: {feed['due_date']} — {feed['countdown']}"
            if feed.get("prep_note"):
                line += f" · {feed['prep_note']}"
        else:
            line = "Next feed: no feeds logged yet"
        html_parts.append(_section("Next feed", line))
        text_parts.append(line)

    if cfg.digest_show_maint:
        if maint:
            line = f"{maint['label']}: {maint['due_date']} — {days_countdown_label(maint['days_until'])}"
        else:
            line = "Maintenance: —"
        html_parts.append(_section("Next maintenance", line))
        text_parts.append(line)

    if gap:
        html_parts.append(_section("Handling", gap["countdown"]))
        text_parts.append(f"Handling: {gap['countdown']}")

    if cfg.digest_show_shed:
        if shed and shed["active"]:
            line = f"In shed ({shed['status']}) — humidity {shed['humidity_target']}"
            if shed.get("dont_feed"):
                line += " · do not feed while opaque"
        elif last_shed:
            line = f"Last shed: {last_shed['date']}" + (f" ({last_shed['quality']})" if last_shed.get("quality") else "")
        else:
            line = "Last shed: none logged"
        html_parts.append(_section("Shed", line))
        text_parts.append(f"Shed: {line}")

    if cfg.digest_show_activity and recent:
        html_parts.append(_section("Since last digest", "<br/>".join(recent)))
        text_parts.append("Since last digest:")
        text_parts.extend(f"- {r}" for r in recent)

    html_parts.append("</div>")
    return subject, "\n".join(html_parts), "\n".join(text_parts)


def recent_activity(db: Session, since: datetime) -> list[str]:
    animal = get_animal(db)
    if animal is None:
        return []
    aid = animal.id
    lines: list[str] = []
    since_date = since.date() if isinstance(since, datetime) else since

    for f in db.scalars(select(Feed).where(Feed.animal_id == aid, Feed.date >= since_date).limit(10)):
        lines.append(f"Feed {f.date}: {f.prey_type} ({'accepted' if f.accepted else 'refused'})")
    for h in db.scalars(select(Handling).where(Handling.animal_id == aid, Handling.date >= since_date).limit(10)):
        lines.append(f"Handling {h.date}: {h.duration_min}min · {h.temperament.value}")
    for m in db.scalars(select(Maintenance).where(Maintenance.animal_id == aid, Maintenance.date >= since_date).limit(10)):
        lines.append(f"Maintenance {m.date}: {m.kind.value}")
    for r in db.scalars(
        select(Regurgitation).where(Regurgitation.animal_id == aid, Regurgitation.date >= since_date).limit(5)
    ):
        lines.append(f"REGURG {r.date}: {r.severity}")
    return lines[:15]


def preview_digest(db: Session) -> dict[str, Any]:
    """Same payload the digest email would send today — no send, no dedupe."""
    cfg = get_or_create_settings(db)
    now = local_now(cfg)
    overview = build_overview(db)
    recent = recent_activity(db, now - timedelta(hours=14))
    subject, html, text = build_digest_content(overview, cfg, recent)
    return {
        "ok": True,
        "date": now.date().isoformat(),
        "subject": subject,
        "html": html,
        "text": text,
        "to": cfg.reminder_email,
    }


def send_digest(db: Session, *, force: bool = False, slot: str | None = None) -> dict[str, Any]:
    cfg = get_or_create_settings(db)
    if not cfg.email_enabled and not force:
        return {"ok": False, "skipped": "email_disabled"}
    if not cfg.digest_enabled and not force:
        return {"ok": False, "skipped": "digest_disabled"}

    now = local_now(cfg)
    hhmm = now.strftime("%H:%M")
    if slot is None:
        if hhmm == cfg.digest_time_1:
            slot = "am"
        elif cfg.digest_second_enabled and hhmm == cfg.digest_time_2:
            slot = "pm"
        else:
            return {"ok": False, "skipped": "not_digest_time", "now": hhmm}

    kind = f"digest_{slot}"
    dedupe = f"digest:{now.date().isoformat()}:{cfg.digest_time_1 if slot == 'am' else cfg.digest_time_2}"
    if not force and already_sent(db, dedupe):
        return {"ok": False, "skipped": "already_sent", "dedupe_key": dedupe}

    overview = build_overview(db)
    since = now - timedelta(hours=14)
    recent = recent_activity(db, since)
    subject, html, text = build_digest_content(overview, cfg, recent)
    result = send_resend(cfg.reminder_email, subject, html, text)
    if result.get("ok"):
        record_sent(db, kind, dedupe)
    return {**result, "kind": kind, "dedupe_key": dedupe}


def send_event_email(db: Session, kind: str, subject: str, body: str, dedupe_key: str) -> dict[str, Any]:
    cfg = get_or_create_settings(db)
    if not cfg.email_enabled:
        return {"ok": False, "skipped": "email_disabled"}
    toggle = {
        "handle_cleared": cfg.event_handle_cleared,
        "feed_overdue": cfg.event_feed_overdue,
        "handling_gap": cfg.event_handling_gap,
        "shed_status": cfg.event_shed_status,
        "regurg": cfg.event_regurg,
        "maint_water": cfg.event_maint_water,
        "maint_substrate": cfg.event_maint_substrate,
        "maint_deep_clean": cfg.event_maint_deep_clean,
        "weight_due": cfg.event_weight_due,
    }.get(kind, True)
    if not toggle:
        return {"ok": False, "skipped": "event_disabled"}
    if already_sent(db, dedupe_key):
        return {"ok": False, "skipped": "already_sent"}

    html = f"<div style='background:#1a0e08;padding:20px;color:#F2E8D9;font-family:sans-serif'><h2 style='color:#C4946A'>{subject}</h2><p>{body}</p></div>"
    result = send_resend(cfg.reminder_email, subject, html, body)
    if result.get("ok"):
        record_sent(db, kind, dedupe_key)
    return result


def fire_handle_cleared(db: Session) -> dict[str, Any]:
    overview = build_overview(db)
    handle = overview["clear_to_handle"]
    last_feed = overview.get("last_feed")
    if not handle.get("ready"):
        return {"ok": False, "skipped": "not_ready"}
    if not last_feed or not last_feed.get("accepted"):
        return {"ok": False, "skipped": "no_accepted_feed"}
    if not handle.get("clear_at"):
        return {"ok": False, "skipped": "no_timer"}
    name = overview.get("name", "Allie")
    return send_event_email(
        db,
        "handle_cleared",
        f"{name}: clear to handle",
        "It is now clear to handle — post-feed wait is over.",
        f"handle_cleared:feed-{last_feed['id']}",
    )


def fire_feed_overdue(db: Session) -> dict[str, Any]:
    overview = build_overview(db)
    feed = overview.get("next_feed")
    if not feed or feed.get("days_until", 0) >= 0:
        return {"ok": False, "skipped": "not_overdue"}
    name = overview.get("name", "Allie")
    return send_event_email(
        db,
        "feed_overdue",
        f"{name}: feed overdue",
        f"Next feed was due {feed['due_date']} — {feed['countdown']}.",
        f"feed_overdue:{feed['due_date']}",
    )


def fire_handling_gap(db: Session) -> dict[str, Any]:
    overview = build_overview(db)
    gap = overview.get("handling_gap")
    handle = overview["clear_to_handle"]
    if not gap or not gap.get("overdue") or not handle.get("ready"):
        return {"ok": False, "skipped": "not_due"}
    name = overview.get("name", "Allie")
    return send_event_email(
        db,
        "handling_gap",
        f"{name}: handling due",
        gap["countdown"] + " — and it is clear to handle.",
        f"handling_gap:{date.today().isoformat()}",
    )


def fire_maint_due(db: Session, kind: str) -> dict[str, Any]:
    overview = build_overview(db)
    item = next((i for i in (overview.get("maintenance_items") or []) if i["kind"] == kind), None)
    if item is None:
        return {"ok": False, "skipped": "unknown_kind"}
    if not item.get("overdue") and not item.get("due_today"):
        return {"ok": False, "skipped": "not_due"}
    name = overview.get("name", "Allie")
    status = "overdue" if item.get("overdue") else "due today"
    event_kind = f"maint_{kind}"
    return send_event_email(
        db,
        event_kind,
        f"{name}: {item['label']} {status}",
        f"{item['label']} is {status} (due {item['due_date']}). "
        f"Interval every {item['interval_days']}d · last logged {item['last_date'] or 'never'}.",
        f"{event_kind}:{item['due_date']}",
    )


def fire_weight_due(db: Session) -> dict[str, Any]:
    overview = build_overview(db)
    weight = overview.get("weight_due")
    if not weight or not weight.get("due"):
        return {"ok": False, "skipped": "not_due"}
    name = overview.get("name", "Allie")
    return send_event_email(
        db,
        "weight_due",
        f"{name}: weight log due",
        weight["countdown"]
        + f" (every {weight['interval_days']}d · last {weight['last_date'] or 'never'}).",
        f"weight_due:{weight['due_date']}",
    )


def evaluate_time_events(db: Session) -> list[dict[str, Any]]:
    """Backup path (manual tick): fire any currently due one-shots. Deduped."""
    cfg = get_or_create_settings(db)
    if not cfg.email_enabled:
        return []
    results: list[dict[str, Any]] = []
    overview = build_overview(db)

    feed = overview.get("next_feed")
    if cfg.event_feed_overdue and feed and feed["days_until"] < 0:
        results.append(fire_feed_overdue(db))

    handle = overview["clear_to_handle"]
    last_feed = overview.get("last_feed")
    if (
        cfg.event_handle_cleared
        and handle.get("ready")
        and handle.get("clear_at")
        and last_feed
        and last_feed.get("accepted")
    ):
        results.append(fire_handle_cleared(db))

    gap = overview.get("handling_gap")
    if cfg.event_handling_gap and gap and gap.get("overdue") and handle.get("ready"):
        results.append(fire_handling_gap(db))

    for item in overview.get("maintenance_items") or []:
        toggle = {
            "water": cfg.event_maint_water,
            "substrate": cfg.event_maint_substrate,
            "deep_clean": cfg.event_maint_deep_clean,
        }.get(item["kind"], True)
        if toggle and (item.get("overdue") or item.get("due_today")):
            results.append(fire_maint_due(db, item["kind"]))

    weight = overview.get("weight_due")
    if cfg.event_weight_due and weight and weight.get("due"):
        results.append(fire_weight_due(db))

    return results


def notify_shed_status(db: Session, status: str, cycle_id: int) -> dict[str, Any]:
    if status not in ("blue", "opaque"):
        return {"ok": False, "skipped": "not_active_shed"}
    animal = get_animal(db)
    name = animal.name if animal else "Allie"
    return send_event_email(
        db,
        "shed_status",
        f"{name}: shed — {status}",
        f"Shed status is now {status}. Raise humidity to 60–70%."
        + (" Do not feed while opaque." if status == "opaque" else ""),
        f"shed_status:{cycle_id}:{status}",
    )


def notify_regurg(db: Session, regurg_id: int, notes: str) -> dict[str, Any]:
    animal = get_animal(db)
    name = animal.name if animal else "Allie"
    return send_event_email(
        db,
        "regurg",
        f"{name}: regurgitation logged",
        f"A regurgitation was logged. Notes: {notes or '—'}. Check temps and consider vet if repeated.",
        f"regurg:{regurg_id}",
    )


def run_tick(db: Session) -> dict[str, Any]:
    """Optional backup poke — digests use a 5-minute after-window; events fire if due."""
    cfg = get_or_create_settings(db)
    now = local_now(cfg)
    hhmm = now.strftime("%H:%M")
    digest: dict[str, Any] = {"ok": False, "skipped": "not_digest_time", "now": hhmm}

    def _past_within(target: str, window_min: int = 5) -> bool:
        try:
            th, tm = [int(x) for x in target[:5].split(":")]
            delta = (now.hour * 60 + now.minute) - (th * 60 + tm)
            return 0 <= delta <= window_min
        except Exception:
            return False

    if _past_within(cfg.digest_time_1):
        digest = send_digest(db, slot="am")
    elif cfg.digest_second_enabled and _past_within(cfg.digest_time_2):
        digest = send_digest(db, slot="pm")

    events = evaluate_time_events(db)
    return {"digest": digest, "events": events, "scheduler": "in-process"}
