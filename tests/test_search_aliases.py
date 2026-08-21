#!/usr/bin/env python3
"""
NutriTrack — Integration Test Suite for Food Search & Alias Table

Verifies that common food queries (including Indian regional dishes and standard staples)
return valid, non-zero macro & calorie results from the backend search API.

Usage:
    python tests/test_search_aliases.py
    python tests/test_search_aliases.py --base-url http://localhost:5000
"""

import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import time
import argparse
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

TEST_QUERIES = [
    # Indian Regional Cuisine
    "biryani",
    "chicken biryani",
    "dosa",
    "masala dosa",
    "dal",
    "dal tadka",
    "paneer tikka",
    "palak paneer",
    "chole",
    "rajma",
    "samosa",
    "poha",
    "upma",
    "idli",
    "roti",
    "chapati",
    "naan",
    "butter chicken",
    "gulab jamun",

    # Global Staples
    "banana",
    "apple",
    "chicken breast",
    "boiled egg",
    "white rice cooked",
    "whole milk",
    "almonds",
    "broccoli",
    "salmon",
    "avocado",
    "oatmeal cooked",
    "cottage cheese",
    "sweet potato",
]


def test_search_api(base_url: str = None):
    print("=" * 70)
    print("  NutriTrack Integration Test: Food Search & Alias Table")
    if base_url:
        print(f"  Target Mode: Remote HTTP ({base_url}/api/foods/search)")
    else:
        print("  Target Mode: In-Process Flask Search Engine (app.test_client)")
    print("=" * 70)

    passed = 0
    failed = 0
    results = []

    # If in-process mode or fallback
    client = None
    if not base_url:
        from backend.App import app
        app.config['TESTING'] = True
        client = app.test_client()

    for query in TEST_QUERIES:
        try:
            if client:
                resp = client.get(f'/api/foods/search?q={query}&limit=1')
                if resp.status_code != 200:
                    print(f"  [FAIL] {query:<22} -> HTTP {resp.status_code}")
                    failed += 1
                    continue
                data = resp.get_json()
            else:
                url = f"{base_url}/api/foods/search"
                r = requests.get(url, params={"q": query, "limit": 1}, timeout=10)
                if r.status_code != 200:
                    print(f"  [FAIL] {query:<22} -> HTTP {r.status_code}")
                    failed += 1
                    continue
                data = r.json()

            if not data or len(data) == 0:
                print(f"  [FAIL] {query:<22} -> NO RESULT RETURNED")
                failed += 1
                results.append((query, False, "No result returned"))
                continue

            item = data[0]
            name = item.get("name", "Unknown")
            cal = float(item.get("cal") or item.get("calories") or 0)
            pro = float(item.get("pro") or item.get("protein") or 0)
            carb = float(item.get("carb") or item.get("carbs") or 0)
            fat = float(item.get("fat") or 0)

            # Check that valid nutritional data exists
            if cal > 0:
                print(f"  [PASS] {query:<22} -> {name[:28]:<28} {cal:>5.1f} kcal (P:{pro}g C:{carb}g F:{fat}g)")
                passed += 1
                results.append((query, True, f"{name} ({cal} kcal)"))
            else:
                print(f"  [FAIL] {query:<22} -> {name[:28]:<28} ZERO CALORIES")
                failed += 1
                results.append((query, False, f"Zero calories: {name}"))

        except Exception as e:
            print(f"  [FAIL] {query:<22} -> ERROR: {e}")
            failed += 1
            results.append((query, False, str(e)))

        time.sleep(0.02)

    print("=" * 70)
    print(f"  SUMMARY: {passed}/{len(TEST_QUERIES)} queries passed successfully ({passed/len(TEST_QUERIES)*100:.0f}%)")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=None, help="Base URL of Flask API (optional)")
    args = parser.parse_args()

    success = test_search_api(args.base_url)
    sys.exit(0 if success else 1)

