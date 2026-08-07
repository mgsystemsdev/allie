"""Deterministic care intelligence from logged history.

Pure functions — no DB. Clamp adaptive advice to stage bands; never invent prey
outside recommended/acceptable. Degrade gracefully when history is thin.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import median
from typing import Any, Protocol

from app.services.feeding_rules import STAGE_FEEDING_RULES, recommend_feeding

# --- Habitat targets (must match HabitatTab copy) ---
ENV_HOT_MIN, ENV_HOT_MAX = 90.0, 95.0
ENV_COOL_MIN, ENV_COOL_MAX = 75.0, 79.0
ENV_NIGHT_MIN, ENV_NIGHT_MAX = 70.0, 74.0
ENV_RH_NORMAL = (40.0, 60.0)
ENV_RH_SHED = (60.0, 70.0)
ENV_STALE_DAYS = 7

ADAPTIVE_MIN_INTERVALS = 3
ADAPTIVE_LOOKBACK_ACCEPTS = 8
REFUSE_EXTRA_DAYS = 2
REGURG_LOOKAHEAD_DAYS = 2
WEIGHT_DROP_PCT = 0.05
WEIGHT_DROP_ABS_G = 10.0
WEIGHT_STALL_DAYS = 30
WEIGHT_STALL_MIN_GAIN_PCT = 0.02
WEIGHT_MIN_POINTS = 3
WEIGHT_MIN_SPAN_DAYS = 14
SHED_PREDICT_MIN_CYCLES = 2
SHED_WINDOW_DAYS = 7


class _FeedLike(Protocol):
    date: date
    accepted: bool
    prey_type: str


class _WeightLike(Protocol):
    date: date
    weight_g: float


class _ShedLike(Protocol):
    started_at: date
    completed_at: date | None


class _EnvLike(Protocol):
    recorded_at: datetime
    temp_hot_f: float
    temp_cool_f: float
    temp_night_f: float | None
    humidity_pct: float


def _alert(
    kind: str,
    message: str,
    severity: str,
    why: str,
) -> dict[str, str]:
    return {"kind": kind, "message": message, "severity": severity, "why": why}


def resolve_feed_interval(
    *,
    feeds: list[_FeedLike],
    regurg_dates: list[date],
    stage_label: str,
    mode: str,
    manual_days: int | None,
    last_feed_accepted: bool | None,
) -> dict[str, Any]:
    """Pick interval days: manual > adaptive (when auto) > stage recommended.

    mode:
      - manual: fixed manual_days
      - stage: life-stage recommended only
      - auto / adaptive: median accepted intervals clamped to stage band
    """
    rules = STAGE_FEEDING_RULES[stage_label]
    band = rules["feeding_interval"]
    stage_rec = int(band["recommended_days"])
    min_d = int(band["min_days"])
    max_d = int(band["max_days"])

    if mode == "manual" and manual_days:
        days = int(manual_days)
        return {
            "interval_days": days,
            "interval_source": "manual",
            "why": f"Manual setting: every {days}d",
            "band": {"min_days": min_d, "max_days": max_d, "recommended_days": stage_rec},
        }

    use_adaptive = mode in ("auto", "adaptive")
    if mode == "stage":
        use_adaptive = False

    adaptive = _adaptive_from_feeds(feeds, regurg_dates, min_d, max_d) if use_adaptive else None

    if adaptive is not None:
        days = adaptive["days"]
        why = adaptive["why"]
        if last_feed_accepted is False:
            days = min(max_d, days + REFUSE_EXTRA_DAYS)
            why += f"; last feed refused → +{REFUSE_EXTRA_DAYS}d"
        # Recent regurg: stretch toward max
        if _recent_regurg(regurg_dates):
            days = max_d
            why += f"; recent regurg → use stage max {max_d}d"
        return {
            "interval_days": days,
            "interval_source": "adaptive",
            "why": why,
            "band": {"min_days": min_d, "max_days": max_d, "recommended_days": stage_rec},
        }

    days = stage_rec
    why = f"Stage {stage_label} recommended {stage_rec}d (band {min_d}–{max_d})"
    if last_feed_accepted is False:
        days = min(max_d, days + REFUSE_EXTRA_DAYS)
        why += f"; last feed refused → +{REFUSE_EXTRA_DAYS}d"
    if _recent_regurg(regurg_dates):
        days = max_d
        why += f"; recent regurg → use stage max {max_d}d"
    return {
        "interval_days": days,
        "interval_source": "stage",
        "why": why,
        "band": {"min_days": min_d, "max_days": max_d, "recommended_days": stage_rec},
    }


def _recent_regurg(regurg_dates: list[date], today: date | None = None, within_days: int = 14) -> bool:
    today = today or date.today()
    return any((today - d).days <= within_days for d in regurg_dates)


def _adaptive_from_feeds(
    feeds: list[_FeedLike],
    regurg_dates: list[date],
    min_d: int,
    max_d: int,
) -> dict[str, Any] | None:
    """Median gap between consecutive accepted feeds, excluding regurg-tainted ones."""
    accepted = sorted(
        [f for f in feeds if f.accepted],
        key=lambda f: (f.date, getattr(f, "id", 0)),
    )
    if len(accepted) < ADAPTIVE_MIN_INTERVALS + 1:
        return None

    # Use most recent accepts only
    window = accepted[-(ADAPTIVE_LOOKBACK_ACCEPTS + 1) :]
    intervals: list[int] = []
    for prev, cur in zip(window, window[1:]):
        gap = (cur.date - prev.date).days
        if gap <= 0:
            continue
        # Skip if regurg shortly after previous accepted feed
        if any(0 <= (r - prev.date).days <= REGURG_LOOKAHEAD_DAYS for r in regurg_dates):
            continue
        intervals.append(gap)

    if len(intervals) < ADAPTIVE_MIN_INTERVALS:
        return None

    raw = int(round(median(intervals)))
    clamped = max(min_d, min(max_d, raw))
    why = (
        f"Median of last {len(intervals)} accepted intervals = {raw}d"
        f" (clamped to {min_d}–{max_d} → {clamped}d)"
    )
    return {"days": clamped, "why": why, "raw_median": raw, "sample_size": len(intervals)}


def suggest_prey(
    *,
    age_months: int,
    feeds: list[_FeedLike],
    last_prey: str | None,
) -> dict[str, Any]:
    """Rank prey by accept history within stage band; demote double refuses."""
    base = recommend_feeding(age_months, last_prey)
    stage = base["stage"]
    preferred = list(base["recommended_prey"]) + list(base["acceptable_prey"])
    preferred_set = set(preferred)

    # Stage-window: feeds while animal was in this stage is hard without DOB;
    # use last 90 days instead.
    cutoff = date.today() - timedelta(days=90)
    recent = [f for f in feeds if f.date >= cutoff]

    accept_counts: dict[str, int] = {}
    for f in recent:
        if f.accepted and f.prey_type in preferred_set:
            accept_counts[f.prey_type] = accept_counts.get(f.prey_type, 0) + 1

    # Double refuse demotion: last two feeds same prey, both refused
    demoted: set[str] = set()
    ordered = sorted(recent, key=lambda f: (f.date, getattr(f, "id", 0)), reverse=True)
    if len(ordered) >= 2:
        a, b = ordered[0], ordered[1]
        if (
            a.prey_type == b.prey_type
            and not a.accepted
            and not b.accepted
            and a.prey_type in preferred_set
        ):
            demoted.add(a.prey_type)

    ranked = sorted(
        preferred,
        key=lambda p: (
            0 if p in demoted else 1,
            accept_counts.get(p, 0),
            -preferred.index(p),  # stable: earlier in stage list wins ties
        ),
        reverse=True,
    )

    suggested = ranked[0] if ranked else (base["recommended_prey"][0] if base["recommended_prey"] else None)
    if suggested and accept_counts.get(suggested, 0) > 0:
        why = f"Most accepted in last 90d within stage band: {suggested} ({accept_counts[suggested]}×)"
    elif suggested and suggested in demoted:
        # Shouldn't happen given sort, but keep safe
        why = f"Stage default after demoting refused prey: {suggested}"
    elif demoted:
        why = f"Demoted {', '.join(sorted(demoted))} after 2 refuses; suggesting {suggested}"
    else:
        why = f"Stage default (no accept history in band): {suggested}"

    return {
        **base,
        "suggested_prey": suggested,
        "suggestion_why": why,
        "prey_accept_counts": accept_counts,
        "demoted_prey": sorted(demoted),
    }


def weight_alerts(
    weights: list[_WeightLike],
    stage_label: str,
    today: date | None = None,
) -> list[dict[str, str]]:
    today = today or date.today()
    if len(weights) < WEIGHT_MIN_POINTS:
        return []

    ordered = sorted(weights, key=lambda w: (w.date, getattr(w, "id", 0)))
    span = (ordered[-1].date - ordered[0].date).days
    if span < WEIGHT_MIN_SPAN_DAYS:
        return []

    alerts: list[dict[str, str]] = []
    latest, prev = ordered[-1], ordered[-2]
    if prev.weight_g > 0:
        drop = (prev.weight_g - latest.weight_g) / prev.weight_g
        abs_drop = prev.weight_g - latest.weight_g
        if drop >= WEIGHT_DROP_PCT or abs_drop >= WEIGHT_DROP_ABS_G:
            if latest.weight_g < prev.weight_g:
                pct = round(drop * 100, 1)
                alerts.append(
                    _alert(
                        "weight_drop",
                        f"Weight drop: {prev.weight_g:g}g → {latest.weight_g:g}g (−{pct}%)",
                        "high",
                        f"Latest vs prior reading; threshold ≥{int(WEIGHT_DROP_PCT * 100)}% or ≥{WEIGHT_DROP_ABS_G:g}g",
                    )
                )

    # Stall only for growing stages
    if stage_label in ("Hatchling", "Juvenile", "Sub-adult"):
        window_start = today - timedelta(days=WEIGHT_STALL_DAYS)
        in_window = [w for w in ordered if w.date >= window_start]
        if len(in_window) >= 2:
            first, last = in_window[0], in_window[-1]
            if first.weight_g > 0:
                gain = (last.weight_g - first.weight_g) / first.weight_g
                if gain < WEIGHT_STALL_MIN_GAIN_PCT:
                    alerts.append(
                        _alert(
                            "weight_stall",
                            f"Growth stall: {gain * 100:.1f}% over {WEIGHT_STALL_DAYS}d "
                            f"({first.weight_g:g}g → {last.weight_g:g}g)",
                            "medium",
                            f"{stage_label} expected ≥{int(WEIGHT_STALL_MIN_GAIN_PCT * 100)}% gain / {WEIGHT_STALL_DAYS}d",
                        )
                    )
    return alerts


def shed_prediction(
    completed: list[_ShedLike],
    today: date | None = None,
) -> dict[str, Any] | None:
    """Estimate next shed start from median inter-start gaps."""
    today = today or date.today()
    starts = sorted(
        {s.started_at for s in completed if s.started_at is not None},
    )
    if len(starts) < SHED_PREDICT_MIN_CYCLES:
        return {
            "estimate_date": None,
            "median_days": None,
            "days_until": None,
            "in_window": False,
            "why": f"Need ≥{SHED_PREDICT_MIN_CYCLES} completed shed starts (have {len(starts)})",
        }

    gaps = [(b - a).days for a, b in zip(starts, starts[1:]) if (b - a).days > 0]
    if len(gaps) < 1:
        return {
            "estimate_date": None,
            "median_days": None,
            "days_until": None,
            "in_window": False,
            "why": "Insufficient positive gaps between shed starts",
        }

    med = int(round(median(gaps)))
    last = starts[-1]
    estimate = last + timedelta(days=med)
    days_until = (estimate - today).days
    in_window = 0 <= days_until <= SHED_WINDOW_DAYS
    return {
        "estimate_date": estimate.isoformat(),
        "median_days": med,
        "days_until": days_until,
        "last_started": last.isoformat(),
        "sample_cycles": len(gaps),
        "in_window": in_window,
        "why": f"Median {med}d between {len(gaps) + 1} shed starts; next ~{estimate.isoformat()}",
    }


def shed_alerts(prediction: dict[str, Any] | None, active_shed: bool) -> list[dict[str, str]]:
    if active_shed or not prediction or not prediction.get("in_window"):
        return []
    days = prediction["days_until"]
    return [
        _alert(
            "shed_window",
            f"Shed window opening — estimate in {days} day(s) ({prediction['estimate_date']})",
            "low",
            prediction["why"],
        )
    ]


def env_alerts(
    reading: _EnvLike | None,
    *,
    in_shed: bool,
    now: datetime | None = None,
) -> list[dict[str, str]]:
    now = now or datetime.now().astimezone()
    if reading is None:
        return [
            _alert(
                "env_stale",
                "No habitat readings logged yet",
                "low",
                "Log hot/cool/humidity on Habitat tab",
            )
        ]

    recorded = reading.recorded_at
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=now.tzinfo)
    age_days = (now - recorded).total_seconds() / 86400
    alerts: list[dict[str, str]] = []
    if age_days > ENV_STALE_DAYS:
        alerts.append(
            _alert(
                "env_stale",
                f"Last env reading {int(age_days)}d ago",
                "low",
                f"Stale after {ENV_STALE_DAYS}d — log a fresh Habitat reading",
            )
        )

    rh_lo, rh_hi = ENV_RH_SHED if in_shed else ENV_RH_NORMAL
    rh_label = "shed" if in_shed else "normal"

    if not (ENV_HOT_MIN <= reading.temp_hot_f <= ENV_HOT_MAX):
        alerts.append(
            _alert(
                "env_hot",
                f"Hot spot {reading.temp_hot_f:g}°F outside {ENV_HOT_MIN:g}–{ENV_HOT_MAX:g}°F",
                "medium",
                "Basking target 90–95°F",
            )
        )
    if not (ENV_COOL_MIN <= reading.temp_cool_f <= ENV_COOL_MAX):
        alerts.append(
            _alert(
                "env_cool",
                f"Cool end {reading.temp_cool_f:g}°F outside {ENV_COOL_MIN:g}–{ENV_COOL_MAX:g}°F",
                "medium",
                "Cool-end target 75–79°F",
            )
        )
    if reading.temp_night_f is not None and not (
        ENV_NIGHT_MIN <= reading.temp_night_f <= ENV_NIGHT_MAX
    ):
        alerts.append(
            _alert(
                "env_night",
                f"Night {reading.temp_night_f:g}°F outside {ENV_NIGHT_MIN:g}–{ENV_NIGHT_MAX:g}°F",
                "low",
                "Night drop target 70–74°F",
            )
        )
    if not (rh_lo <= reading.humidity_pct <= rh_hi):
        alerts.append(
            _alert(
                "env_humidity",
                f"Humidity {reading.humidity_pct:g}% outside {rh_lo:g}–{rh_hi:g}% ({rh_label})",
                "medium",
                f"{'Shed' if in_shed else 'Normal'} humidity target {rh_lo:g}–{rh_hi:g}%",
            )
        )
    return alerts
