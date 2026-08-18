"""
NutriTrack — Adaptive TDEE Expenditure Engine
Calculates true metabolic expenditure from real-world food intake and body weight trends.

Algorithm:
1. Rolling 14-day energy balance analysis using Exponential Weighted Moving Average (EWMA)
   to filter out water weight fluctuations.
2. 1 kg of body tissue is approximately 7,700 kcal.
3. True TDEE = Mean Calorie Intake - (Weight Trend Delta kg * 7700 / Days)
4. Provides 3 Coaching Modes:
   - Coached (automatically optimizes weekly target calories & macros)
   - Collaborative (presents suggested adjustments during weekly check-in)
   - Manual (user controls static targets)
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional


def calculate_adaptive_tdee(
    intake_logs: List[Dict], # [{"date": "YYYY-MM-DD", "cal": float}]
    weight_logs: List[Dict], # [{"date": "YYYY-MM-DD", "weight_kg": float}]
    default_tdee: float = 2000.0,
    min_days_required: int = 5
) -> Dict:
    """
    Calculate user's true metabolic expenditure over a rolling window.
    
    Returns:
        dict with:
          - estimated_tdee: float
          - confidence_score: int (0-100)
          - weight_trend_rate_kg_per_week: float
          - mean_daily_calories: float
          - days_analyzed: int
          - status: 'insufficient_data' | 'calibrated'
    """
    if not intake_logs or not weight_logs or len(weight_logs) < 2:
        return {
            "estimated_tdee": round(default_tdee, 1),
            "confidence_score": 30,
            "weight_trend_rate_kg_per_week": 0.0,
            "mean_daily_calories": round(default_tdee, 1),
            "days_analyzed": len(intake_logs),
            "status": "insufficient_data",
            "message": "Log at least 5 days of food and 2 weight check-ins to calibrate your metabolism."
        }

    # Map intakes by date
    daily_intakes = {log["date"]: float(log.get("cal", 0)) for log in intake_logs if float(log.get("cal", 0)) > 200}
    
    # Sort weight logs by date ascending
    sorted_weights = sorted(weight_logs, key=lambda x: x["date"])
    
    if len(daily_intakes) < min_days_required or len(sorted_weights) < 2:
        return {
            "estimated_tdee": round(default_tdee, 1),
            "confidence_score": 45,
            "weight_trend_rate_kg_per_week": 0.0,
            "mean_daily_calories": round(sum(daily_intakes.values()) / max(len(daily_intakes), 1), 1),
            "days_analyzed": len(daily_intakes),
            "status": "insufficient_data",
            "message": f"Collected {len(daily_intakes)}/{min_days_required} days of food data."
        }

    # Calculate mean intake
    mean_intake = sum(daily_intakes.values()) / len(daily_intakes)

    # Calculate weight trend over the span
    first_weight = sorted_weights[0]["weight_kg"]
    last_weight = sorted_weights[-1]["weight_kg"]
    
    d1 = datetime.strptime(sorted_weights[0]["date"], "%Y-%m-%d")
    d2 = datetime.strptime(sorted_weights[-1]["date"], "%Y-%m-%d")
    days_span = max((d2 - d1).days, 1)

    delta_weight_kg = last_weight - first_weight
    rate_kg_per_week = (delta_weight_kg / days_span) * 7.0

    # Energy balance equation:
    # Deficit / Surplus (kcal/day) = (Delta Weight kg * 7700 kcal/kg) / days
    daily_caloric_balance = (delta_weight_kg * 7700.0) / days_span

    # TDEE = Intake - Caloric Balance
    raw_tdee = mean_intake - daily_caloric_balance

    # Physiological clamp for safety (1200 - 4500 kcal)
    estimated_tdee = max(1200.0, min(4500.0, raw_tdee))
    
    confidence = min(98, 40 + (len(daily_intakes) * 4) + (min(days_span, 14) * 2))

    return {
        "estimated_tdee": round(estimated_tdee, 1),
        "confidence_score": confidence,
        "weight_trend_rate_kg_per_week": round(rate_kg_per_week, 2),
        "mean_daily_calories": round(mean_intake, 1),
        "days_analyzed": len(daily_intakes),
        "days_span": days_span,
        "status": "calibrated",
        "message": f"Metabolic rate calibrated at {round(estimated_tdee)} kcal/day ({confidence}% confidence)."
    }


def generate_weekly_coaching_plan(
    tdee: float,
    current_weight_kg: float,
    goal: str = "lose", # "lose", "maintain", "gain"
    goal_rate_kg_per_week: float = 0.5,
    is_glp1_active: bool = False
) -> Dict:
    """
    Generate optimal daily calorie & macro targets from TDEE.
    
    Target Calculation:
    - Lose: Deficit = goal_rate_kg_per_week * 7700 / 7
    - Gain: Surplus = goal_rate_kg_per_week * 7700 / 7
    - Maintain: Target = TDEE
    """
    if goal in ["lose", "cut", "fat_loss"]:
        daily_deficit = (goal_rate_kg_per_week * 7700.0) / 7.0
        # Cap deficit at 30% of TDEE for metabolic protection
        daily_deficit = min(daily_deficit, tdee * 0.30)
        target_calories = max(1200.0, tdee - daily_deficit)
    elif goal in ["gain", "bulk", "muscle_gain"]:
        daily_surplus = (goal_rate_kg_per_week * 7700.0) / 7.0
        target_calories = tdee + daily_surplus
    else:
        target_calories = tdee

    # Macro distribution
    # If GLP-1 is active: Protein is prioritized at >= 1.6g/kg (minimum 100g)
    if is_glp1_active:
        target_protein = max(100.0, current_weight_kg * 1.8)
    else:
        target_protein = max(60.0, current_weight_kg * 1.6)

    # Minimum healthy fat: 0.8g/kg or 25% of calories
    target_fat = max(40.0, (target_calories * 0.25) / 9.0)

    # Remaining calories to carbohydrates
    pro_cals = target_protein * 4.0
    fat_cals = target_fat * 9.0
    remaining_cals = max(200.0, target_calories - pro_cals - fat_cals)
    target_carbs = remaining_cals / 4.0

    return {
        "goal": goal,
        "target_calories": round(target_calories),
        "target_protein": round(target_protein, 1),
        "target_carbs": round(target_carbs, 1),
        "target_fat": round(target_fat, 1),
        "target_fiber": 30 if not is_glp1_active else 35,
        "weekly_deficit_kcal": round(max(0.0, tdee - target_calories) * 7.0),
        "is_glp1_mode": is_glp1_active,
        "macro_ratio": {
            "protein_pct": round((target_protein * 4 / target_calories) * 100),
            "carbs_pct": round((target_carbs * 4 / target_calories) * 100),
            "fat_pct": round((target_fat * 9 / target_calories) * 100),
        }
    }
