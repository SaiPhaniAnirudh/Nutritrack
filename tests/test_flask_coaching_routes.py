"""
Flask Test Client Route Verification for Coaching & AI Endpoints
"""

import os
import sys
import json
import unittest
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.App import app

class TestCoachingRoutes(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_ai_chat_route(self):
        """Test POST /api/ai/chat with live Groq / Gemini response."""
        res = self.client.post('/api/ai/chat', json={'message': 'Give me a healthy 300 kcal snack with high protein'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('reply', data)
        self.assertGreater(len(data['reply']), 20)
        print(f"\n💬 NutriBot Response: {data['reply'][:120]}... (Source: {data.get('source')})")

    def test_ai_corrections_route(self):
        """Test POST /api/ai/corrections."""
        res = self.client.post('/api/ai/corrections', json={
            'original_food': 'Brown Rice',
            'corrected_food': 'Steamed White Rice',
            'original_cal': 150,
            'corrected_cal': 210
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data.get('saved'))

if __name__ == '__main__':
    unittest.main()
