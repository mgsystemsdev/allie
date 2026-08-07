"""Tests for age → prey category feeding recommendations."""

from app.services.feeding_rules import (
    PREY,
    STAGE_FEEDING_RULES,
    assert_config_integrity,
    recommend_feeding,
    stage_from_months,
)


def test_config_integrity():
    assert_config_integrity()


def test_stage_boundaries():
    assert stage_from_months(0)["label"] == "Hatchling"
    assert stage_from_months(2)["label"] == "Hatchling"
    assert stage_from_months(3)["label"] == "Juvenile"
    assert stage_from_months(11)["label"] == "Juvenile"
    assert stage_from_months(12)["label"] == "Sub-adult"
    assert stage_from_months(35)["label"] == "Sub-adult"
    assert stage_from_months(36)["label"] == "Adult"


def test_stage_interval_midpoints():
    assert stage_from_months(1)["feed_interval_days"] == 6
    assert stage_from_months(9)["feed_interval_days"] == 8
    assert stage_from_months(20)["feed_interval_days"] == 12
    assert stage_from_months(40)["feed_interval_days"] == 17


def test_recommended_items_per_stage():
    for months, label in [(1, "Hatchling"), (6, "Juvenile"), (18, "Sub-adult"), (40, "Adult")]:
        rules = STAGE_FEEDING_RULES[label]
        rec = recommend_feeding(months, rules["recommended"][0])
        assert rec["stage"] == label
        assert rec["prey_status"] == "recommended"
        for item in rules["recommended"]:
            assert recommend_feeding(months, item)["prey_status"] == "recommended"


def test_acceptable_and_alternative():
    juv = recommend_feeding(6, "Norwegian small")
    assert juv["prey_status"] == "acceptable"
    juv_alt = recommend_feeding(6, "Day-old chick")
    assert juv_alt["prey_status"] == "alternative"
    adult_alt = recommend_feeding(40, "Rabbit")
    assert adult_alt["prey_status"] == "alternative"


def test_too_small_and_too_large():
    assert recommend_feeding(6, "Pinky mouse")["prey_status"] == "too_small"
    assert recommend_feeding(6, "Norwegian jumbo")["prey_status"] == "too_large"
    assert recommend_feeding(1, "Rabbit")["prey_status"] == "too_large"
    assert recommend_feeding(40, "Pinky mouse")["prey_status"] == "too_small"


def test_unknown_prey():
    out = recommend_feeding(6, "Small rat")
    assert out["prey_status"] == "unknown"
    assert out["selected_prey"] == "Small rat"


def test_null_selected_prey():
    out = recommend_feeding(6, None)
    assert out["selected_prey"] is None
    assert out["prey_status"] is None
    assert out["recommended_prey"] == STAGE_FEEDING_RULES["Juvenile"]["recommended"]
    assert out["feeding_interval"]["recommended_days"] == 8


def test_stage_transition_same_prey():
    """Norwegian pup: recommended at 11 mo, acceptable at 12 mo."""
    assert recommend_feeding(11, "Norwegian pup")["stage"] == "Juvenile"
    assert recommend_feeding(11, "Norwegian pup")["prey_status"] == "recommended"
    assert recommend_feeding(12, "Norwegian pup")["stage"] == "Sub-adult"
    assert recommend_feeding(12, "Norwegian pup")["prey_status"] == "acceptable"


def test_interval_shape():
    out = recommend_feeding(6, "Adult mouse")
    iv = out["feeding_interval"]
    assert iv == {"min_days": 7, "max_days": 10, "recommended_days": 8}


def test_prey_status_by_category_covers_prey():
    out = recommend_feeding(6, None)
    assert set(out["prey_status_by_category"].keys()) == set(PREY)
    assert out["prey_status_by_category"]["Adult mouse"] == "recommended"
    assert out["prey_status_by_category"]["Pinky mouse"] == "too_small"


def test_return_lists_present():
    out = recommend_feeding(18, "Norwegian small")
    assert "acceptable_prey" in out
    assert "alternative_prey" in out
    assert "Norwegian small" in out["recommended_prey"]
