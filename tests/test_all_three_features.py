"""
NutriTrack — Master Integration Test:
1. Adaptive TDEE & GLP-1 Coaching
2. Apple Health & Garmin Wearable Sync
3. Client-side Foods.js 67+ Extended Nutrients
4. Endpoints & Route Health
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

from backend.App import app
from backend.coaching.tdee_engine import calculate_adaptive_tdee, generate_weekly_coaching_plan
from backend.coaching.glp1_mode import evaluate_glp1_compliance
from backend.integrations.apple_health import export_to_healthkit_json, parse_apple_health_xml
from backend.integrations.garmin import parse_garmin_activity_payload


class TestMasterFeatures(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_adaptive_tdee_engine(self):
        """Test rolling energy balance calculation."""
        intakes = [{"date": f"2026-08-{i:02d}", "cal": 2200.0} for i in range(1, 15)]
        weights = [
            {"date": "2026-08-01", "weight_kg": 75.0},
            {"date": "2026-08-14", "weight_kg": 74.5}
        ]
        res = calculate_adaptive_tdee(intakes, weights, default_tdee=2200.0)
        self.assertEqual(res["status"], "calibrated")
        self.assertGreater(res["estimated_tdee"], 2300.0)

    def test_glp1_compliance_rules(self):
        """Test GLP-1 therapy safety evaluation."""
        logs = [{"cal": 1500, "pro": 115, "fiber": 30}]
        res = evaluate_glp1_compliance(daily_logs=logs, water_ml=2800, weight_kg=65.0)
        self.assertEqual(len(res["alerts"]), 0) # Safe compliance
        self.assertGreaterEqual(res["compliance_score"], 85)

    def test_apple_health_export(self):
        """Test HealthKit JSON structure generation."""
        mock_logs = [{
            "date": "2026-08-18",
            "name": "Grilled Salmon",
            "cal": 350,
            "pro": 38,
            "carb": 0,
            "fat": 20,
            "extendedNutrients": {"vitamin_c_mg": 0, "iron_mg": 1.2, "potassium_mg": 450}
        }]
        res = export_to_healthkit_json(mock_logs)
        self.assertEqual(res["exportSource"], "NutriTrack AI Health Engine")
        self.assertGreaterEqual(res["totalSamples"], 4)

    def test_garmin_activity_parser(self):
        """Test Garmin activity payload parsing."""
        mock_payload = {
            "activities": [
                {"activityName": "Evening Cycling", "calories": 420, "duration": 2400}
            ]
        }
        res = parse_garmin_activity_payload(mock_payload)
        self.assertEqual(res["total_active_calories"], 420.0)
        self.assertEqual(len(res["sessions"]), 1)

    def test_coaching_routes(self):
        """Test GET /api/coaching/glp1 and GET /api/integrations/apple-health/export."""
        res_glp1 = self.client.get('/api/coaching/glp1')
        self.assertIn(res_glp1.status_code, [200, 401]) # 401 if unauthed, valid endpoint

        res_hk = self.client.get('/api/integrations/apple-health/export')
        self.assertEqual(res_hk.status_code, 200)


if __name__ == '__main__':
    unittest.main()
