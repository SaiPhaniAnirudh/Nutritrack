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
import time
import argparse
import requests

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


def test_search_api(base_url: str):
    print("=" * 70)
    print(f"  NutriTrack Integration Test: Food Search & Alias Table")
    print(f"  Endpoint: {base_url}/api/foods/search")
    print("=" * 70)

    passed = 0
    failed = 0
    results = []

    for query in TEST_QUERIES:
        url = f"{base_url}/api/foods/search"
        try:
            r = requests.get(url, params={"q": query, "limit": 1}, timeout=10)
            r.raise_for_status()
            data = r.json()

            if not data or len(data) == 0:
                print(f"  [FAIL] {query:<25} -> NO RESULT")
                failed += 1
                results.append((query, False, "No result returned"))
                continue

            item = data[0]
            name = item.get("name", "Unknown")
            cal = item.get("cal", 0)
            pro = item.get("pro", 0)
            carb = item.get("carb", 0)
            fat = item.get("fat", 0)

            # Check that valid nutritional data exists
            if cal > 0 and (pro >= 0 and carb >= 0 and fat >= 0):
                print(f"  [PASS] {query:<22} -> {name[:30]:<30} {cal:>5.1f} kcal (P:{pro}g C:{carb}g F:{fat}g)")
                passed += 1
                results.append((query, True, f"{name} ({cal} kcal)"))
            else:
                print(f"  [FAIL] {query:<22} -> {name[:30]:<30} INVALID MACROS (cal={cal})")
                failed += 1
                results.append((query, False, f"Invalid macros: cal={cal}"))

        except Exception as e:
            print(f"  [FAIL] {query:<22} -> ERROR: {e}")
            failed += 1
            results.append((query, False, str(e)))

        time.sleep(0.05)

    print("=" * 70)
    print(f"  SUMMARY: {passed}/{len(TEST_QUERIES)} queries passed successfully ({passed/len(TEST_QUERIES)*100:.0f}%)")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:5000", help="Base URL of Flask API")
    args = parser.parse_args()

    success = test_search_api(args.base_url)
    sys.exit(0 if success else 1)
