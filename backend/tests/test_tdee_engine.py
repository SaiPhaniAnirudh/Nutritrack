"""
Unit tests for backend/coaching/tdee_engine.py — the adaptive metabolic
coach's core math. Unlike test_app.py (which only checks the app boots),
these verify the actual formulas: energy-balance TDEE estimation and
goal-based macro target generation.

Run:
    pytest backend/tests/test_tdee_engine.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from coaching.tdee_engine import calculate_adaptive_tdee, generate_weekly_coaching_plan


# ── calculate_adaptive_tdee ──────────────────────────────────────────

def test_insufficient_data_returns_default():
    """With no logs at all, should fall back to the default TDEE, not crash."""
    result = calculate_adaptive_tdee(intake_logs=[], weight_logs=[], default_tdee=2000.0)
    assert result["status"] == "insufficient_data"
    assert result["estimated_tdee"] == 2000.0


def test_insufficient_weight_logs_returns_default():
    """A single weight check-in isn't enough to compute a trend."""
    intake_logs = [{"date": "2026-08-01", "cal": 2200}]
    weight_logs = [{"date": "2026-08-01", "weight_kg": 75.0}]
    result = calculate_adaptive_tdee(intake_logs, weight_logs)
    assert result["status"] == "insufficient_data"


def test_weight_loss_trend_lowers_estimated_tdee_below_intake():
    """
    If someone is losing weight while eating a given amount, their true
    TDEE must be higher than that intake (they're in a deficit) —
    i.e. estimated_tdee should exceed mean daily calories.
    """
    intake_logs = [
        {"date": f"2026-08-{d:02d}", "cal": 2000} for d in range(1, 15)
    ]
    weight_logs = [
        {"date": "2026-08-01", "weight_kg": 80.0},
        {"date": "2026-08-14", "weight_kg": 79.0},  # lost 1kg over 13 days
    ]
    result = calculate_adaptive_tdee(intake_logs, weight_logs)
    assert result["status"] == "calibrated"
    assert result["estimated_tdee"] > result["mean_daily_calories"]
    assert result["weight_trend_rate_kg_per_week"] < 0


def test_weight_gain_trend_raises_estimated_tdee_above_intake():
    """Mirror case: gaining weight on a given intake means true TDEE is lower than intake."""
    intake_logs = [
        {"date": f"2026-08-{d:02d}", "cal": 2500} for d in range(1, 15)
    ]
    weight_logs = [
        {"date": "2026-08-01", "weight_kg": 70.0},
        {"date": "2026-08-14", "weight_kg": 71.0},  # gained 1kg
    ]
    result = calculate_adaptive_tdee(intake_logs, weight_logs)
    assert result["estimated_tdee"] < result["mean_daily_calories"]
    assert result["weight_trend_rate_kg_per_week"] > 0


def test_tdee_is_clamped_to_physiological_range():
    """Extreme/noisy inputs shouldn't produce an unsafe TDEE outside 1200-4500 kcal."""
    intake_logs = [{"date": f"2026-08-{d:02d}", "cal": 500} for d in range(1, 15)]
    weight_logs = [
        {"date": "2026-08-01", "weight_kg": 100.0},
        {"date": "2026-08-14", "weight_kg": 70.0},  # implausible 30kg loss in 13 days
    ]
    result = calculate_adaptive_tdee(intake_logs, weight_logs)
    assert 1200.0 <= result["estimated_tdee"] <= 4500.0


def test_low_calorie_logs_are_filtered_out():
    """Logs under 200 kcal (likely a snack or logging error) shouldn't skew the mean."""
    intake_logs = (
        [{"date": f"2026-08-{d:02d}", "cal": 2000} for d in range(1, 10)]
        + [{"date": "2026-08-10", "cal": 50}]  # should be excluded
    )
    weight_logs = [
        {"date": "2026-08-01", "weight_kg": 75.0},
        {"date": "2026-08-10", "weight_kg": 75.0},
    ]
    result = calculate_adaptive_tdee(intake_logs, weight_logs)
    assert result["days_analyzed"] == 9  # the 50-kcal day excluded


# ── generate_weekly_coaching_plan ────────────────────────────────────

def test_lose_goal_targets_below_tdee():
    plan = generate_weekly_coaching_plan(tdee=2500, current_weight_kg=80, goal="lose")
    assert plan["target_calories"] < 2500


def test_gain_goal_targets_above_tdee():
    plan = generate_weekly_coaching_plan(tdee=2500, current_weight_kg=70, goal="gain")
    assert plan["target_calories"] > 2500


def test_maintain_goal_targets_equal_tdee():
    plan = generate_weekly_coaching_plan(tdee=2500, current_weight_kg=75, goal="maintain")
    assert plan["target_calories"] == 2500


def test_deficit_never_exceeds_30_percent_of_tdee():
    """Metabolic safety: even an aggressive goal_rate shouldn't create a >30% deficit."""
    plan = generate_weekly_coaching_plan(
        tdee=2000, current_weight_kg=80, goal="lose", goal_rate_kg_per_week=2.0
    )
    assert plan["target_calories"] >= 2000 * 0.70


def test_calorie_floor_is_respected():
    """Target calories should never drop below the 1200 kcal safety floor."""
    plan = generate_weekly_coaching_plan(
        tdee=1300, current_weight_kg=60, goal="lose", goal_rate_kg_per_week=1.0
    )
    assert plan["target_calories"] >= 1200


def test_glp1_mode_raises_protein_floor():
    """GLP-1 protection mode should push the protein target to >= 100g minimum."""
    plan_normal = generate_weekly_coaching_plan(
        tdee=2000, current_weight_kg=50, goal="maintain", is_glp1_active=False
    )
    plan_glp1 = generate_weekly_coaching_plan(
        tdee=2000, current_weight_kg=50, goal="maintain", is_glp1_active=True
    )
    assert plan_glp1["target_protein"] >= 100.0
    assert plan_glp1["target_protein"] > plan_normal["target_protein"]


def test_macros_add_up_to_target_calories():
    """Protein + fat + carb calories should reconcile against target_calories (within rounding)."""
    plan = generate_weekly_coaching_plan(tdee=2200, current_weight_kg=70, goal="maintain")
    reconstructed = (
        plan["target_protein"] * 4.0
        + plan["target_fat"] * 9.0
        + plan["target_carbs"] * 4.0
    )
    assert abs(reconstructed - plan["target_calories"]) < 5.0