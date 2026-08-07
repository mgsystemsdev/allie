"""Age → prey-category feeding recommendations.

Uses ONLY age (months) and selected prey category. No weight, girth, or % BW.
"""

from __future__ import annotations

from typing import Any, Literal

PreyStatus = Literal[
    "recommended",
    "acceptable",
    "too_small",
    "too_large",
    "alternative",
    "unknown",
]

# Single source of truth for valid prey category values.
PREY: list[str] = [
    "Pinky mouse",
    "Fuzzy mouse",
    "Adult mouse",
    "Norwegian pinky",
    "Norwegian fuzzy",
    "Norwegian pup",
    "Norwegian weaned",
    "Norwegian small",
    "Norwegian medium",
    "Norwegian large",
    "Norwegian jumbo",
    "Day-old chick",
    "Quail",
    "Rabbit",
]

# Relative meal size for too_small / too_large when not in stage lists.
PREY_SIZE_ORDER: dict[str, int] = {
    "Pinky mouse": 10,
    "Norwegian pinky": 15,
    "Fuzzy mouse": 20,
    "Norwegian fuzzy": 25,
    "Adult mouse": 30,
    "Norwegian pup": 35,
    "Day-old chick": 40,
    "Norwegian weaned": 45,
    "Norwegian small": 55,
    "Norwegian medium": 65,
    "Quail": 70,
    "Norwegian large": 75,
    "Norwegian jumbo": 85,
    "Rabbit": 95,
}

STAGE_FEEDING_RULES: dict[str, dict[str, Any]] = {
    "Hatchling": {
        "desc": "0–3 months",
        "recommended": ["Pinky mouse", "Fuzzy mouse", "Norwegian pinky"],
        "acceptable": ["Adult mouse", "Norwegian fuzzy"],
        "alternative": ["Day-old chick"],
        "feeding_interval": {"min_days": 5, "max_days": 7, "recommended_days": 6},
    },
    "Juvenile": {
        "desc": "3–12 months",
        "recommended": [
            "Adult mouse",
            "Norwegian fuzzy",
            "Norwegian pup",
            "Norwegian weaned",
        ],
        "acceptable": ["Fuzzy mouse", "Norwegian pinky", "Norwegian small"],
        "alternative": ["Day-old chick"],
        "feeding_interval": {"min_days": 7, "max_days": 10, "recommended_days": 8},
    },
    "Sub-adult": {
        "desc": "1–3 years",
        "recommended": ["Norwegian weaned", "Norwegian small", "Norwegian medium"],
        "acceptable": ["Adult mouse", "Norwegian pup", "Norwegian large"],
        "alternative": ["Day-old chick", "Quail"],
        "feeding_interval": {"min_days": 10, "max_days": 14, "recommended_days": 12},
    },
    "Adult": {
        "desc": "3+ years",
        "recommended": ["Norwegian small", "Norwegian medium", "Norwegian large"],
        "acceptable": ["Norwegian weaned", "Norwegian jumbo"],
        "alternative": ["Quail", "Rabbit"],
        "feeding_interval": {"min_days": 14, "max_days": 21, "recommended_days": 17},
    },
}


def stage_from_months(months: int) -> dict[str, Any]:
    """Age months → life stage. Boundaries: <3, <12, <36, else Adult."""
    if months < 3:
        label = "Hatchling"
    elif months < 12:
        label = "Juvenile"
    elif months < 36:
        label = "Sub-adult"
    else:
        label = "Adult"
    rules = STAGE_FEEDING_RULES[label]
    return {
        "label": label,
        "desc": rules["desc"],
        "feed_interval_days": rules["feeding_interval"]["recommended_days"],
    }


def _classify_prey(selected: str, rules: dict[str, Any]) -> PreyStatus:
    if selected not in PREY:
        return "unknown"
    if selected in rules["recommended"]:
        return "recommended"
    if selected in rules["acceptable"]:
        return "acceptable"
    if selected in rules["alternative"]:
        return "alternative"

    rank = PREY_SIZE_ORDER.get(selected)
    if rank is None:
        return "unknown"

    band = rules["recommended"] + rules["acceptable"]
    ranks = [PREY_SIZE_ORDER[p] for p in band if p in PREY_SIZE_ORDER]
    if not ranks:
        return "unknown"
    min_ok, max_ok = min(ranks), max(ranks)
    if rank < min_ok:
        return "too_small"
    if rank > max_ok:
        return "too_large"
    return "unknown"


def recommend_feeding(age_months: int, selected_prey: str | None = None) -> dict[str, Any]:
    stage = stage_from_months(age_months)
    label = stage["label"]
    rules = STAGE_FEEDING_RULES[label]

    status_by = {p: _classify_prey(p, rules) for p in PREY}

    if selected_prey is None or selected_prey == "":
        prey_status: PreyStatus | None = None
        selected_out: str | None = None
    else:
        selected_out = selected_prey
        prey_status = _classify_prey(selected_prey, rules)

    return {
        "stage": label,
        "selected_prey": selected_out,
        "prey_status": prey_status,
        "recommended_prey": list(rules["recommended"]),
        "acceptable_prey": list(rules["acceptable"]),
        "alternative_prey": list(rules["alternative"]),
        "feeding_interval": dict(rules["feeding_interval"]),
        "prey_status_by_category": status_by,
    }


def feeding_config() -> dict[str, Any]:
    """Full config for clients: PREY list + all stage rules."""
    stages = {}
    for label, rules in STAGE_FEEDING_RULES.items():
        stages[label] = {
            "desc": rules["desc"],
            "recommended": list(rules["recommended"]),
            "acceptable": list(rules["acceptable"]),
            "alternative": list(rules["alternative"]),
            "feeding_interval": dict(rules["feeding_interval"]),
        }
    return {"prey_categories": list(PREY), "stages": stages}


def assert_config_integrity() -> None:
    """Raise AssertionError if config is invalid."""
    assert set(PREY_SIZE_ORDER.keys()) == set(PREY), "PREY_SIZE_ORDER must cover PREY exactly"
    for label, rules in STAGE_FEEDING_RULES.items():
        for key in ("recommended", "acceptable", "alternative"):
            for item in rules[key]:
                assert item in PREY, f"{label}.{key}: {item!r} not in PREY"
        sets = [set(rules["recommended"]), set(rules["acceptable"]), set(rules["alternative"])]
        assert not (sets[0] & sets[1]), f"{label}: recommended ∩ acceptable"
        assert not (sets[0] & sets[2]), f"{label}: recommended ∩ alternative"
        assert not (sets[1] & sets[2]), f"{label}: acceptable ∩ alternative"
        iv = rules["feeding_interval"]
        assert iv["min_days"] <= iv["recommended_days"] <= iv["max_days"], f"{label}: interval midpoint"


assert_config_integrity()
