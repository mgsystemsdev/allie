"""In-process care scheduler (MGOS-style digests + event/due timers).

No Railway cron required. On API startup we arm wall-clock digests and due-date
one-shots from DB state. Care writes call request_reschedule() to rebuild.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

log = logging.getLogger("allie.scheduler")

# Jobs that re-arm themselves for the next day after firing
DIGEST_JOBS = frozenset({"digest_am", "digest_pm"})


def parse_hhmm(hhmm: str) -> tuple[int, int]:
    parts = (hhmm or "08:00")[:5].split(":")
    return int(parts[0]), int(parts[1])


def next_wall_datetime(now: datetime, hhmm: str) -> datetime:
    """Next occurrence of HH:MM in now's timezone (today if still ahead, else tomorrow)."""
    hour, minute = parse_hhmm(hhmm)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def wall_on_date(tz: ZoneInfo, day: date, hhmm: str) -> datetime:
    hour, minute = parse_hhmm(hhmm)
    return datetime(day.year, day.month, day.day, hour, minute, 0, 0, tzinfo=tz)


def _as_aware(dt: datetime, fallback_tz: ZoneInfo) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=fallback_tz)
    return dt


class CareScheduler:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._rebuild_lock = asyncio.Lock()

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        log.info("care scheduler starting")
        await self.rebuild()

    def stop(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        self._loop = None
        log.info("care scheduler stopped")

    def request_reschedule(self) -> None:
        """Safe to call from sync request handlers."""
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(self.rebuild(), loop)

    async def rebuild(self) -> None:
        async with self._rebuild_lock:
            for key, task in list(self._tasks.items()):
                if not task.done():
                    task.cancel()
            self._tasks.clear()

            try:
                plan = await asyncio.to_thread(self._compute_plan)
            except Exception:
                log.exception("scheduler plan failed")
                return

            now_utc = datetime.now().astimezone()
            for key, when, job in plan:
                when_aware = _as_aware(when, now_utc.tzinfo or ZoneInfo("UTC"))
                self._arm(key, when_aware, job)
            log.info("scheduler armed %d job(s): %s", len(plan), ", ".join(k for k, _, _ in plan) or "(none)")

    def _arm(self, key: str, when: datetime, job: str) -> None:
        async def runner() -> None:
            delay = (when - datetime.now().astimezone()).total_seconds()
            if delay > 0:
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    return
            else:
                # Already due — slight stagger so startup settles
                try:
                    await asyncio.sleep(3)
                except asyncio.CancelledError:
                    return
            try:
                await asyncio.to_thread(self._dispatch, job)
            except asyncio.CancelledError:
                return
            except Exception:
                log.exception("scheduler job %s failed", job)
            if job in DIGEST_JOBS:
                await self.rebuild()

        self._tasks[key] = asyncio.create_task(runner(), name=f"allie:{key}")

    def _compute_plan(self) -> list[tuple[str, datetime, str]]:
        from app.db import SessionLocal
        from app.services.care import build_overview, local_now
        from app.services.settings_svc import get_or_create_settings

        db = SessionLocal()
        plan: list[tuple[str, datetime, str]] = []
        try:
            cfg = get_or_create_settings(db)
            if not cfg.email_enabled:
                return plan

            now = local_now(cfg)
            try:
                tz = ZoneInfo(cfg.timezone)
            except Exception:
                tz = ZoneInfo("America/Chicago")

            overview = build_overview(db)
            alert_hhmm = cfg.digest_time_1 or "08:00"

            if cfg.digest_enabled:
                plan.append(("digest_am", next_wall_datetime(now, cfg.digest_time_1), "digest_am"))
                if cfg.digest_second_enabled:
                    plan.append(("digest_pm", next_wall_datetime(now, cfg.digest_time_2), "digest_pm"))

            # Clear-to-handle: fire at clear_at (or ASAP if already ready)
            handle = overview.get("clear_to_handle") or {}
            last_feed = overview.get("last_feed")
            if cfg.event_handle_cleared and last_feed and last_feed.get("accepted"):
                clear_raw = handle.get("clear_at")
                if clear_raw:
                    clear_at = _as_aware(datetime.fromisoformat(clear_raw), tz)
                    if handle.get("ready"):
                        plan.append(("handle_cleared", now, "handle_cleared"))
                    else:
                        plan.append(("handle_cleared", clear_at, "handle_cleared"))

            # Feed overdue: morning of due date (or ASAP if already overdue)
            feed = overview.get("next_feed")
            if cfg.event_feed_overdue and feed:
                due_day = date.fromisoformat(feed["due_date"])
                when = wall_on_date(tz, due_day, alert_hhmm)
                if feed.get("days_until", 0) < 0:
                    when = now
                elif when < now and feed.get("days_until", 0) == 0:
                    when = now
                plan.append(("feed_overdue", when, "feed_overdue"))

            # Maintenance due
            for item in overview.get("maintenance_items") or []:
                kind = item["kind"]
                toggle = {
                    "water": cfg.event_maint_water,
                    "substrate": cfg.event_maint_substrate,
                    "deep_clean": cfg.event_maint_deep_clean,
                }.get(kind, True)
                if not toggle:
                    continue
                due_day = date.fromisoformat(item["due_date"])
                when = wall_on_date(tz, due_day, alert_hhmm)
                if item.get("overdue"):
                    when = now
                elif item.get("due_today") and when < now:
                    when = now
                plan.append((f"maint_{kind}", when, f"maint_{kind}"))

            # Weight due
            weight = overview.get("weight_due")
            if cfg.event_weight_due and weight:
                due_day = date.fromisoformat(weight["due_date"])
                when = wall_on_date(tz, due_day, alert_hhmm)
                if weight.get("overdue") or (weight.get("due") and when <= now):
                    when = now
                plan.append(("weight_due", when, "weight_due"))

            # Handling gap — optional (default off)
            gap = overview.get("handling_gap")
            if cfg.event_handling_gap and gap and handle.get("ready"):
                max_gap = int(gap.get("max_gap_days") or cfg.handling_max_gap_days)
                last = gap.get("last_date")
                if last:
                    due_day = date.fromisoformat(last) + timedelta(days=max_gap + 1)
                else:
                    due_day = now.date()
                when = wall_on_date(tz, due_day, alert_hhmm)
                if gap.get("overdue"):
                    when = now
                plan.append(("handling_gap", when, "handling_gap"))

        finally:
            db.close()
        return plan

    def _dispatch(self, job: str) -> None:
        from app.db import SessionLocal
        from app.services import email_svc

        db = SessionLocal()
        try:
            if job == "digest_am":
                result = email_svc.send_digest(db, slot="am")
            elif job == "digest_pm":
                result = email_svc.send_digest(db, slot="pm")
            elif job == "handle_cleared":
                result = email_svc.fire_handle_cleared(db)
            elif job == "feed_overdue":
                result = email_svc.fire_feed_overdue(db)
            elif job == "handling_gap":
                result = email_svc.fire_handling_gap(db)
            elif job == "weight_due":
                result = email_svc.fire_weight_due(db)
            elif job.startswith("maint_"):
                result = email_svc.fire_maint_due(db, job.removeprefix("maint_"))
            else:
                log.warning("unknown job %s", job)
                return
            log.info("job %s → %s", job, result)
        finally:
            db.close()


_scheduler: CareScheduler | None = None


def get_scheduler() -> CareScheduler | None:
    return _scheduler


def set_scheduler(sched: CareScheduler | None) -> None:
    global _scheduler
    _scheduler = sched


def request_reschedule() -> None:
    if _scheduler is not None:
        _scheduler.request_reschedule()
