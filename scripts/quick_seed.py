#!/usr/bin/env python3
"""
NutriTrack — quick_seed.py
Quick seed script: fetches the FIRST PAGE of SR Legacy (200 foods) and uploads
immediately to verify your Supabase connection is working, then tells you
how to run the full fetch.

Usage:  python scripts/quick_seed.py
"""

import os, sys, time, json, logging
from pathlib import Path
import requests, psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger()

DATABASE_URL = os.environ.get("DATABASE_URL")
USDA_KEY     = os.environ.get("USDA_API_KEY") or "DEMO_KEY"
USDA_BASE    = "https://api.nal.usda.gov/fdc/v1"

NUTRIENT_MAP = {
    1008: "calories", 2047: "calories",
    1003: "protein",  1005: "carbs",
    1004: "fat",      1079: "fiber",
    2000: "sugar",    1063: "sugar",
    1093: "sodium",   1253: "chol",
}

CATEGORY_MAP = {
    "Fruits and Fruit Juices":           "fruit",
    "Vegetables and Vegetable Products": "veg",
    "Beef Products":                     "protein",
    "Pork Products":                     "protein",
    "Poultry Products":                  "protein",
    "Finfish and Shellfish Products":    "protein",
    "Dairy and Egg Products":            "dairy",
    "Legumes and Legume Products":       "legume",
    "Cereal Grains and Pasta":           "grain",
    "Baked Products":                    "grain",
    "Snacks":                            "snack",
    "Nut and Seed Products":             "snack",
    "Beverages":                         "drink",
    "Fats and Oils":                     "fat",
    "Fast Foods":                        "fastfood",
}

def extract_nutrients(food_nutrients):
    result = {k: None for k in ["calories","protein","carbs","fat","fiber","sugar","sodium","chol"]}
    for n in food_nutrients:
        nid = n.get("nutrientId")
        val = n.get("value")
        if nid in NUTRIENT_MAP and val is not None:
            f = NUTRIENT_MAP[nid]
            if result[f] is None:
                result[f] = round(float(val), 2)
    return result

def main():
    print("\n" + "="*60)
    print("  NutriTrack Quick Seed — USDA SR Legacy (first 200 foods)")
    print("="*60)

    if USDA_KEY == "DEMO_KEY":
        print("  Note: Using DEMO_KEY. Add USDA_API_KEY to .env for full run.")

    if not DATABASE_URL:
        print("  ERROR: DATABASE_URL not set in .env")
        sys.exit(1)

    # 1. Fetch first page of SR Legacy
    print("\n  Fetching from USDA FoodData Central...")
    resp = requests.get(f"{USDA_BASE}/foods/search", params={
        "dataType":   "SR Legacy",
        "query":      "",
        "pageSize":   200,
        "pageNumber": 1,
        "api_key":    USDA_KEY,
    }, timeout=30)

    if resp.status_code != 200:
        print(f"  ERROR: USDA API returned {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)

    data = resp.json()
    total_hits = data.get("totalHits", 0)
    raw_foods  = data.get("foods", [])
    print(f"  Total USDA SR Legacy foods: {total_hits:,}")
    print(f"  Fetched first page: {len(raw_foods)} foods")

    # 2. Parse
    foods = []
    for f in raw_foods:
        name      = (f.get("description") or "").strip()
        nutrients = extract_nutrients(f.get("foodNutrients", []))
        if not name or nutrients["calories"] is None:
            continue
        category = CATEGORY_MAP.get(f.get("foodCategory", ""), "other")
        foods.append({
            "name":        name[:255],
            "category":    category,
            "data_source": "usda_sr_legacy",
            "fdc_id":      f.get("fdcId"),
            **nutrients,
        })

    print(f"  Parsed {len(foods)} valid foods")

    # 3. Upload to Supabase
    print(f"\n  Uploading to Supabase...")
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS base_foods (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(255) UNIQUE NOT NULL,
            category    VARCHAR(100),
            calories    FLOAT, protein FLOAT, carbs FLOAT, fat FLOAT,
            fiber FLOAT, sugar FLOAT, sodium FLOAT, chol FLOAT,
            data_source VARCHAR(50) DEFAULT 'unknown',
            fdc_id      INTEGER
        );
    """)
    for col, dtype in [("data_source","VARCHAR(50)"), ("fdc_id","INTEGER")]:
        cur.execute(f"ALTER TABLE base_foods ADD COLUMN IF NOT EXISTS {col} {dtype};")
    conn.commit()

    rows = [
        (r["name"], r["category"], r.get("calories"), r.get("protein"),
         r.get("carbs"), r.get("fat"), r.get("fiber"), r.get("sugar"),
         r.get("sodium"), r.get("chol"), r["data_source"], r.get("fdc_id"))
        for r in foods
    ]

    execute_values(cur, """
        INSERT INTO base_foods
            (name, category, calories, protein, carbs, fat,
             fiber, sugar, sodium, chol, data_source, fdc_id)
        VALUES %s
        ON CONFLICT (name) DO UPDATE SET
            category=EXCLUDED.category, calories=EXCLUDED.calories,
            protein=EXCLUDED.protein, carbs=EXCLUDED.carbs,
            fat=EXCLUDED.fat, fiber=EXCLUDED.fiber,
            sugar=EXCLUDED.sugar, sodium=EXCLUDED.sodium,
            chol=EXCLUDED.chol, data_source=EXCLUDED.data_source,
            fdc_id=EXCLUDED.fdc_id
    """, rows)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM base_foods;")
    db_total = cur.fetchone()[0]
    cur.close()
    conn.close()

    print(f"\n  Uploaded {len(foods)} foods successfully!")
    print(f"  Total in Supabase now: {db_total:,}")
    print()
    print("  Sample foods uploaded:")
    for f in foods[:5]:
        print(f"    {f['name'][:50]:<50}  {f['calories']} kcal | "
              f"P:{f['protein']}g C:{f['carbs']}g F:{f['fat']}g")

    print()
    print("="*60)
    print("  Quick seed DONE! Connection verified.")
    print()
    print("  To fetch ALL 17,000+ foods (full dataset):")
    print()
    print("  OPTION A — With personal API key (recommended, ~5 min):")
    print("    1. Get free key: https://fdc.nal.usda.gov/api-key-signup.html")
    print("    2. Add to .env:  USDA_API_KEY=your_key_here")
    print("    3. Run:  python scripts/fetch_usda_foods.py --upload")
    print()
    print("  OPTION B — With DEMO_KEY (slow, split over days):")
    print("    Run:  python scripts/fetch_usda_foods.py --sr-only --upload")
    print("    Then: python scripts/fetch_usda_foods.py --upload")
    print("          (resumes automatically from checkpoint each time)")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
