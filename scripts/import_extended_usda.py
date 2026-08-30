#!/usr/bin/env python3
"""
NutriTrack — Extended USDA FoodData Central Importer (67+ Nutrients)
Downloads and imports SR Legacy + Foundation food datasets with full
micronutrient, vitamin, mineral, fatty acid, and amino acid profiles.

Usage:
  python scripts/import_extended_usda.py --limit 500
  python scripts/import_extended_usda.py --category veg
  python scripts/import_extended_usda.py --full
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT / "backend"))
from nutrition.nutrients import parse_usda_nutrients, USDA_NUTRIENT_MAP

import requests
import psycopg2
from psycopg2.extras import execute_values

USDA_API_KEY = os.environ.get("USDA_API_KEY") or "DEMO_KEY"
DATABASE_URL = os.environ.get("DATABASE_URL")
BASE_URL = "https://api.nal.usda.gov/fdc/v1"


def fetch_foods_page(page_number=1, page_size=50, data_type="SR Legacy"):
    url = f"{BASE_URL}/foods/list"
    params = {
        "api_key": USDA_API_KEY,
        "dataType": data_type,
        "pageSize": page_size,
        "pageNumber": page_number,
    }
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"⚠️ USDA API request failed (status {resp.status_code}): {resp.text[:200]}")
        return []


def import_extended_foods(max_items=100):
    print(f"🚀 Starting Extended USDA Import (Target: up to {max_items} foods)...")
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set in environment.")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    imported_count = 0
    page = 1
    page_size = min(max_items, 50)

    while imported_count < max_items:
        print(f"📥 Fetching page {page} ({page_size} foods/page)...")
        foods = fetch_foods_page(page_number=page, page_size=page_size)
        if not foods:
            break

        records_to_insert = []
        for food in foods:
            description = (food.get("description") or "").strip()
            if not description:
                continue

            nutrients = food.get("foodNutrients", [])
            ext_nutrients = parse_usda_nutrients(nutrients)

            # Core fields
            cal = ext_nutrients.get("energy_kcal", 0.0)
            pro = ext_nutrients.get("protein_g", 0.0)
            carb = ext_nutrients.get("carbohydrate_g", 0.0)
            fat = ext_nutrients.get("total_fat_g", 0.0)
            fiber = ext_nutrients.get("fiber_g", 0.0)
            sugar = ext_nutrients.get("total_sugars_g", 0.0)
            sodium = ext_nutrients.get("sodium_mg", 0.0)
            chol = ext_nutrients.get("cholesterol_mg", 0.0)
            vit_d = ext_nutrients.get("vitamin_d_mcg", 0.0)
            iron = ext_nutrients.get("iron_mg", 0.0)
            folate = ext_nutrients.get("folate_mcg", 0.0)
            category = (food.get("foodCategory") or "other").lower()

            records_to_insert.append((
                description,
                category,
                cal, pro, carb, fat, fiber, sugar, sodium, chol, vit_d, iron, folate,
                json.dumps(ext_nutrients)
            ))

        if records_to_insert:
            execute_values(cur, """
                INSERT INTO base_foods (
                    name, category, calories, protein, carbs, fat,
                    fiber, sugar, sodium, chol, vit_d, iron, folate, extended_nutrients
                ) VALUES %s
                ON CONFLICT (name) DO UPDATE SET
                    calories = EXCLUDED.calories,
                    protein = EXCLUDED.protein,
                    carbs = EXCLUDED.carbs,
                    fat = EXCLUDED.fat,
                    fiber = EXCLUDED.fiber,
                    sugar = EXCLUDED.sugar,
                    sodium = EXCLUDED.sodium,
                    chol = EXCLUDED.chol,
                    vit_d = EXCLUDED.vit_d,
                    iron = EXCLUDED.iron,
                    folate = EXCLUDED.folate,
                    extended_nutrients = EXCLUDED.extended_nutrients
            """, records_to_insert)
            conn.commit()
            imported_count += len(records_to_insert)
            print(f"  ✅ Saved {len(records_to_insert)} foods with 67+ nutrient profiles (Total: {imported_count})")

        page += 1
        time.sleep(1.0)  # USDA rate limiting guard

    cur.close()
    conn.close()
    print(f"🎉 Extended USDA Import finished! Total processed: {imported_count} foods.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="USDA Extended Nutrient Importer")
    parser.add_argument("--limit", type=int, default=100, help="Max foods to fetch")
    args = parser.parse_args()
    import_extended_foods(max_items=args.limit)
