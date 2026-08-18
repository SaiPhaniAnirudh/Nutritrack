"""
NutriTrack — Unit & Integration Tests: Adaptive TDEE, GLP-1 Mode, AI Corrections & NutriBot
"""

import os
import sys
import unittest
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.coaching.tdee_engine import calculate_adaptive_tdee, generate_weekly_coaching_plan
from backend.coaching.glp1_mode import evaluate_glp1_compliance
from backend.ai.user_corrections import record_scan_correction, get_user_portion_multiplier
from backend.ai import chatbot_engine


class TestCoachingAndTDEE(unittest.TestCase):
    def test_adaptive_tdee_calculation(self):
        """Test metabolic calibration when losing 0.5kg over 14 days on 2000 kcal intake."""
        intakes = [{"date": f"2026-08-{i:02d}", "cal": 2000.0} for i in range(1, 15)]
        weights = [
            {"date": "2026-08-01", "weight_kg": 80.0},
            {"date": "2026-08-14", "weight_kg": 79.5} # Lost 0.5kg in 13 days
        ]
        res = calculate_adaptive_tdee(intakes, weights, default_tdee=2000.0)
        self.assertEqual(res["status"], "calibrated")
        # Deficit was ~0.5kg * 7700 / 13 = 296 kcal/day -> True TDEE ~ 2296 kcal
        self.assertGreater(res["estimated_tdee"], 2200.0)
        self.assertLess(res["estimated_tdee"], 2400.0)

    def test_weekly_coaching_plan_glp1(self):
        """Verify GLP-1 mode enforces >= 100g protein baseline."""
        plan = generate_weekly_coaching_plan(tdee=2200.0, current_weight_kg=60.0, goal="lose", is_glp1_active=True)
        self.assertGreaterEqual(plan["target_protein"], 100.0)
        self.assertTrue(plan["is_glp1_mode"])

    def test_glp1_compliance_evaluation(self):
        """Test protein deficit warning when intake is low under GLP-1."""
        logs = [{"cal": 900, "pro": 35, "fiber": 10}] # Dangerously low protein
        res = evaluate_glp1_compliance(daily_logs=logs, water_ml=1200, weight_kg=70.0)
        self.assertTrue(any(a["type"] == "protein_deficit" for a in res["alerts"]))
        self.assertTrue(any(a["type"] == "dehydration_risk" for a in res["alerts"]))


class TestUserCorrectionsAndChatbot(unittest.TestCase):
    def test_scan_correction_multiplier(self):
        """Test portion multiplier calculation on user edits."""
        rec = record_scan_correction(
            user_id="test_user",
            original_food="Rice",
            corrected_food="Basmati Rice",
            original_cal=150.0,
            corrected_cal=225.0
        )
        self.assertEqual(rec["portion_multiplier"], 1.5)

    def test_nutribot_chat_response(self):
        """Test that NutriBot returns structured clinical response."""
        context = {
            "diet_goal": "fat_loss",
            "diet_type": "high_protein",
            "goal_calories": 2000,
            "goal_protein": 160,
            "consumed_calories": 1400,
            "consumed_protein": 110,
            "rem_calories": 600,
            "rem_protein": 50,
            "is_glp1": False,
            "nutrient_gaps": "Iron (Fe), Vitamin D"
        }
        res = chatbot_engine.generate_nutrition_advice(
            message="What high protein dinner can I eat for my remaining calories?",
            user_context=context
        )
        self.assertTrue(res.get("success"))
        self.assertIn("reply", res)
        self.assertGreater(len(res["reply"]), 10)


if __name__ == "__main__":
    unittest.main()
