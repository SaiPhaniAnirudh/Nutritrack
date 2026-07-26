#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   NutriTrack — fetch_usda_foods.py                                         ║
║   Fetches scientifically verified food data from USDA FoodData Central     ║
║   Sources:                                                                  ║
║     • SR Legacy   (~7,793 foods) — Lab-analyzed    ⭐⭐⭐⭐⭐             ║
║     • Foundation  (~2,000 foods) — Analytically verified ⭐⭐⭐⭐⭐       ║
║     • Survey/FNDDS (~7,000+ dishes) — Recipe-calculated ⭐⭐⭐⭐         ║
║     • Branded     (filtered top items) — Manufacturer-reported ⭐⭐⭐    ║
║                                                                             ║
║   Usage:                                                                    ║
║     python scripts/fetch_usda_foods.py                  (fetch + save)     ║
║     python scripts/fetch_usda_foods.py --upload         (fetch + upload)   ║
║     python scripts/fetch_usda_foods.py --upload-only    (upload cached)    ║
║     python scripts/fetch_usda_foods.py --resume         (continue from checkpoint)  ║
║     python scripts/fetch_usda_foods.py --stats          (show DB counts)   ║
║     python scripts/fetch_usda_foods.py --sr-only --upload  (fastest run)  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Rate limits:
  DEMO_KEY      -> 30 req/hour, 50 req/day  (script handles pacing automatically)
  Personal key  -> 1,000 req/hour           (fast mode, ~5 min total)

Get a free personal key (takes 2 min): https://fdc.nal.usda.gov/api-key-signup.html
Add to .env: USDA_API_KEY=your_key_here
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path

import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# ─── Setup ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("usda_fetch")

# Cache dir — stores downloaded food data so you don't re-fetch
CACHE_DIR = ROOT / "scripts" / ".usda_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

FOODS_JSON = CACHE_DIR / "all_foods.json"
CHECKPOINT = CACHE_DIR / "checkpoint.json"

# ─── Config ───────────────────────────────────────────────────────────────────

USDA_API_KEY = (
    os.environ.get("USDA_API_KEY") or
    os.environ.get("USDA_KEY") or
    "DEMO_KEY"
)
IS_DEMO_KEY = (USDA_API_KEY == "DEMO_KEY")

USDA_BASE = "https://api.nal.usda.gov/fdc/v1"
PAGE_SIZE = 200   # maximum allowed by USDA API

# Rate limiting:
# DEMO_KEY  = 30 req/hour = need 2+ seconds between requests to be safe
# Personal  = 1000 req/hour = 1 second between requests
REQ_DELAY   = 4.0 if IS_DEMO_KEY else 1.0   # seconds between requests
BATCH_PAUSE = 70  if IS_DEMO_KEY else 5      # seconds after every 25 requests

DATABASE_URL = os.environ.get("DATABASE_URL")

# ─── USDA Nutrient ID -> our schema field ────────────────────────────────────
#
# Official USDA nutrient IDs from FoodData Central data dictionary.
# Reference: https://fdc.nal.usda.gov/docs/apiGuide.pdf
# All values are per 100g for SR Legacy / Foundation / Survey foods.

NUTRIENT_MAP = {
    1008: "calories",   # Energy (kcal)   <- primary
    2047: "calories",   # Energy Atwater General Factors (kcal) <- fallback
    1003: "protein",    # Protein (g)
    1005: "carbs",      # Carbohydrate, by difference (g)
    1004: "fat",        # Total lipid / fat (g)
    1079: "fiber",      # Fiber, total dietary (g)
    2000: "sugar",      # Total Sugars (g)    <- primary
    1063: "sugar",      # Sugars, Total (g)   <- fallback alternate ID
    1093: "sodium",     # Sodium, Na (mg)
    1253: "chol",       # Cholesterol (mg)
}

# ─── USDA Food Category -> our app category ──────────────────────────────────

CATEGORY_MAP = {
    "Fruits and Fruit Juices":            "fruit",
    "Vegetables and Vegetable Products":  "veg",
    "Beef Products":                      "protein",
    "Pork Products":                      "protein",
    "Poultry Products":                   "protein",
    "Lamb, Veal, and Game Products":      "protein",
    "Sausages and Luncheon Meats":        "protein",
    "Finfish and Shellfish Products":     "protein",
    "Dairy and Egg Products":             "dairy",
    "Legumes and Legume Products":        "legume",
    "Cereal Grains and Pasta":            "grain",
    "Baked Products":                     "grain",
    "Breakfast Cereals":                  "grain",
    "Snacks":                             "snack",
    "Nut and Seed Products":              "snack",
    "Sweets":                             "snack",
    "Candies":                            "snack",
    "Beverages":                          "drink",
    "Coffee and Tea":                     "drink",
    "Alcoholic Beverages":                "drink",
    "Fats and Oils":                      "fat",
    "Spices and Herbs":                   "spice",
    "Soups, Sauces, and Gravies":         "soup",
    "Fast Foods":                         "fastfood",
    "Meals, Entrees, and Side Dishes":    "meal",
    "Restaurant Foods":                   "fastfood",
    "American Indian/Alaska Native Foods":"american",
    "Baby Foods":                         "other",
    "Ethnic Foods":                       "meal",
}

# Keyword-based category inference (name matching fallback)
KEYWORD_CATEGORY = [
    (["chicken", "turkey", "duck", "goose", "quail",
      "beef", "steak", "ground beef", "pork", "ham", "bacon",
      "lamb", "veal", "venison", "bison", "rabbit", "game",
      "fish", "salmon", "tuna", "tilapia", "cod", "halibut", "sardine",
      "shrimp", "crab", "lobster", "clam", "oyster", "mussel", "scallop"],
     "protein"),
    (["apple", "banana", "orange", "grape", "mango", "strawberry",
      "blueberry", "raspberry", "blackberry", "peach", "pear",
      "cherry", "kiwi", "papaya", "pineapple", "watermelon",
      "cantaloupe", "melon", "plum", "fig", "date", "lychee",
      "guava", "pomegranate", "avocado", "coconut", "lemon", "lime",
      "grapefruit", "tangerine", "mandarin", "nectarine", "apricot",
      "quince", "persimmon", "jackfruit", "durian", "passion fruit",
      "dragon fruit", "star fruit", "longan", "rambutan"],
     "fruit"),
    (["broccoli", "spinach", "carrot", "tomato", "potato", "cucumber",
      "lettuce", "kale", "cabbage", "celery", "onion", "garlic",
      "pepper", "capsicum", "zucchini", "eggplant", "cauliflower",
      "beet", "beetroot", "asparagus", "artichoke", "pumpkin",
      "squash", "sweet potato", "yam", "mushroom", "bean sprout",
      "bok choy", "leek", "shallot", "radish", "turnip", "parsnip",
      "rutabaga", "fennel", "kohlrabi", "endive", "arugula",
      "watercress", "okra", "bitter gourd", "bottle gourd", "lauki",
      "ridge gourd", "drumstick", "ivy gourd", "colocasia"],
     "veg"),
    (["rice", "pasta", "bread", "wheat", "oat", "oatmeal",
      "cereal", "quinoa", "barley", "rye", "corn", "maize",
      "flour", "noodle", "tortilla", "cracker", "bagel", "muffin",
      "roll", "croissant", "sourdough", "whole grain", "bulgur",
      "amaranth", "millet", "sorghum", "buckwheat", "semolina",
      "couscous", "grits", "polenta", "chapati", "roti", "naan",
      "pita", "lavash", "injera", "teff"],
     "grain"),
    (["milk", "cheese", "yogurt", "curd", "butter", "cream",
      "ice cream", "whey", "dairy", "paneer", "ghee", "kefir",
      "quark", "ricotta", "mozzarella", "cheddar", "parmesan",
      "brie", "camembert", "feta", "gouda", "cottage cheese",
      "sour cream", "half and half", "condensed milk", "evaporated"],
     "dairy"),
    (["lentil", "bean", "chickpea", "pea", "dal", "dhal",
      "tofu", "tempeh", "edamame", "soy", "soybean",
      "black bean", "kidney bean", "pinto bean", "navy bean",
      "cannellini", "adzuki", "mung bean", "split pea",
      "black-eyed pea", "fava", "broad bean", "lupini"],
     "legume"),
    (["almond", "walnut", "cashew", "peanut", "pistachio", "pecan",
      "macadamia", "hazelnut", "pine nut", "chia", "flax", "flaxseed",
      "sunflower seed", "pumpkin seed", "hemp seed", "sesame", "tahini",
      "coconut flake", "brazil nut", "chestnut"],
     "snack"),
    (["coffee", "espresso", "tea", "green tea", "matcha", "chai",
      "juice", "soda", "cola", "water", "sparkling", "beer", "ale",
      "wine", "whiskey", "vodka", "rum", "gin", "tequila",
      "smoothie", "shake", "energy drink", "lemonade", "kombucha",
      "coconut water", "sports drink", "protein drink"],
     "drink"),
    (["burger", "pizza", "hot dog", "fries", "french fry",
      "nugget", "sandwich", "sub", "burrito", "taco", "wrap",
      "kebab", "gyro", "fried chicken", "onion ring", "nachos",
      "quesadilla", "waffle fries", "cheeseburger", "mcnugget"],
     "fastfood"),
    (["chip", "pretzel", "popcorn", "cookie", "cake", "candy",
      "chocolate", "brownie", "donut", "doughnut", "muffin",
      "granola bar", "energy bar", "protein bar", "gummy",
      "lollipop", "caramel", "toffee", "fudge", "marshmallow",
      "rice cake", "pork rind", "beef jerky", "fruit snack"],
     "snack"),
    # World cuisine keywords
    (["sushi", "ramen", "udon", "soba", "miso", "tempura",
      "teriyaki", "katsu", "matcha", "onigiri", "edamame",
      "yakitori", "gyoza", "takoyaki", "okonomiyaki", "tonkatsu",
      "yakisoba", "sukiyaki", "shabu", "teppanyaki"],
     "japanese"),
    (["biryani", "curry", "dal", "roti", "naan", "idli", "dosa",
      "sambar", "paneer", "tandoori", "masala", "chutney",
      "paratha", "sabzi", "khichdi", "upma", "poha", "rajma",
      "chole", "pav bhaji", "vada", "uttapam", "rasam",
      "halwa", "kheer", "gulab jamun", "ladoo", "jalebi",
      "samosa", "pakora", "bhaji", "dhokla", "kachori",
      "pulao", "korma", "saag", "aloo", "gobi", "palak"],
     "indian"),
    (["pad thai", "tom yum", "green curry", "massaman", "satay",
      "som tum", "larb", "khao", "pad see ew", "gang",
      "kai", "moo", "tod mun", "spring roll thai", "thai"],
     "thai"),
    (["kimchi", "bulgogi", "bibimbap", "tteok", "japchae",
      "doenjang", "sundubu", "galbi", "pajeon", "gimbap",
      "samgyeopsal", "dakgalbi", "jajangmyeon", "naengmyeon",
      "tteokbokki", "haemul", "buchimgae", "jeon"],
     "korean"),
    (["pho", "banh mi", "bun cha", "goi cuon", "com tam",
      "banh xeo", "bo luc lac", "cao lau", "mi quang",
      "bun bo hue", "che", "banh flan", "ca phe"],
     "vietnamese"),
    (["pasta", "pizza", "risotto", "lasagna", "gnocchi",
      "ossobuco", "tiramisu", "gelato", "bruschetta",
      "minestrone", "carbonara", "bolognese", "arrabbiata",
      "penne", "tagliatelle", "fettuccine", "linguine",
      "spaghetti", "pappardelle", "pesto", "focaccia",
      "ciabatta", "cannoli", "panna cotta", "affogato"],
     "italian"),
    (["taco", "burrito", "quesadilla", "enchilada", "tamale",
      "guacamole", "salsa", "mole", "churro", "pozole",
      "fajita", "carnitas", "ceviche", "elote", "chiles rellenos",
      "huevos rancheros", "torta", "sope", "tlayuda"],
     "mexican"),
    (["hummus", "falafel", "shawarma", "baba ganoush",
      "tabouleh", "pita", "labneh", "fattoush", "kibbeh",
      "za'atar", "muhamara", "dolma", "moussaka", "shakshuka",
      "mansaf", "kabsa", "mandi", "maqluba", "fatteh",
      "kanafeh", "baklava", "halva", "muhallebi"],
     "middle_eastern"),
    (["croissant", "baguette", "crepe", "ratatouille",
      "bouillabaisse", "coq au vin", "quiche", "macaron",
      "eclair", "souffle", "vichyssoise", "nicoise",
      "boeuf bourguignon", "cassoulet", "foie gras",
      "confit", "creme brulee", "tarte", "madeleine"],
     "french"),
    (["paella", "gazpacho", "tortilla espanola", "patatas bravas",
      "croquetas", "jamon", "pimentos", "fabada", "cocido",
      "pisto", "escalivada", "gambas", "pulpo", "sangria"],
     "spanish"),
    (["moussaka", "souvlaki", "gyros", "tzatziki", "spanakopita",
      "feta", "horiatiki", "dolmades", "loukoumades",
      "kleftiko", "stifado", "pastitsio", "revithia",
      "skordalia", "tirokafteri"],
     "greek"),
    (["jollof", "egusi", "injera", "berbere", "peri-peri",
      "suya", "fufu", "pap", "bobotie", "bunny chow",
      "ugali", "nyama choma", "tilapia east african",
      "groundnut soup", "biltong", "boerewors",
      "tagine", "couscous north african", "harira",
      "ras el hanout", "chermoula", "shakshuka"],
     "african"),
    (["feijoada", "churrasco", "coxinha", "pao de queijo",
      "brigadeiro", "acai", "moqueca", "caipirinha",
      "empada", "pastel", "acaraje", "vatapa",
      "stroganoff brazilian", "picanha"],
     "brazilian"),
    (["nasi goreng", "rendang", "gado-gado", "laksa",
      "satay", "mie goreng", "pempek", "soto",
      "beef rendang", "nasi lemak", "char kway teow",
      "hainanese", "laksa", "rojak", "chilli crab",
      "pad krapow", "massaman", "khao soi"],
     "se_asian"),
    (["doner", "borek", "kofte", "lahmacun", "manti",
      "ayran", "pide", "iskender", "adana", "cig kofte",
      "imam bayildi", "dolma", "simit", "pogaca",
      "baklava turkish", "kunefe", "kazandibi"],
     "turkish"),
]


# ─── Helper functions ─────────────────────────────────────────────────────────

def extract_nutrients(food_nutrients):
    """
    Extract our 8 target nutrients from USDA foodNutrients list.
    All USDA SR Legacy / Foundation values are per 100g — no conversion needed.
    FNDDS Survey values are also per 100g.
    """
    result = {
        "calories": None,
        "protein":  None,
        "carbs":    None,
        "fat":      None,
        "fiber":    None,
        "sugar":    None,
        "sodium":   None,
        "chol":     None,
    }

    for n in food_nutrients:
        nid = n.get("nutrientId") or (n.get("nutrient") or {}).get("id")
        val = n.get("value") if n.get("value") is not None else n.get("amount")
        if nid is None or val is None:
            continue
        if nid not in NUTRIENT_MAP:
            continue

        field = NUTRIENT_MAP[nid]

        # Priority rules to avoid overwriting with lower-priority IDs
        if field == "calories" and result["calories"] is not None:
            if nid == 1008:  # always prefer primary energy field
                result["calories"] = round(float(val), 2)
            continue
        if field == "sugar" and result["sugar"] is not None:
            if nid == 2000:  # prefer 2000 over 1063
                result["sugar"] = round(float(val), 2)
            continue

        result[field] = round(float(val), 2)

    return result


def infer_category(name, usda_category=None):
    """Infer our app category from USDA food category string + name keywords."""
    if usda_category:
        cat = CATEGORY_MAP.get(usda_category)
        if cat:
            return cat

    name_lower = (name or "").lower()
    for keywords, cat in KEYWORD_CATEGORY:
        if any(kw in name_lower for kw in keywords):
            return cat

    return "other"


def has_required_nutrients(nutrients, min_fields=4):
    """Return True only if the 4 core macros are present."""
    required = ["calories", "protein", "carbs", "fat"]
    return all(nutrients.get(f) is not None for f in required)


# ─── Checkpoint helpers ────────────────────────────────────────────────────────

def save_checkpoint(data):
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_checkpoint():
    if CHECKPOINT.exists():
        with open(CHECKPOINT, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_cached_foods():
    if FOODS_JSON.exists():
        with open(FOODS_JSON, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_cached_foods(foods):
    with open(FOODS_JSON, "w", encoding="utf-8") as f:
        json.dump(foods, f, indent=2, ensure_ascii=False)
    log.info(f"  Saved {len(foods):,} foods -> {FOODS_JSON}")


# ─── USDA Fetcher class ────────────────────────────────────────────────────────

class USDAFetcher:
    def __init__(self, api_key):
        self.api_key   = api_key
        self.session   = requests.Session()
        self.req_count = 0
        self.is_demo   = (api_key == "DEMO_KEY")

    def _get(self, endpoint, params):
        """Single GET request with rate limiting and retry logic."""
        params["api_key"] = self.api_key
        url = f"{USDA_BASE}/{endpoint}"

        # Rate limiting
        self.req_count += 1
        if self.req_count % 25 == 0 and self.is_demo:
            log.info(f"  [Pause {BATCH_PAUSE}s — DEMO_KEY rate limit, req #{self.req_count}]")
            time.sleep(BATCH_PAUSE)
        else:
            time.sleep(REQ_DELAY)

        for attempt in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=30)

                if resp.status_code == 429:
                    wait = 70 if self.is_demo else 10
                    log.warning(f"  Rate limited (429). Waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code != 200:
                    log.error(f"  HTTP {resp.status_code} for {url}")
                    return None

                return resp.json()

            except requests.RequestException as e:
                log.warning(f"  Request error (attempt {attempt+1}/3): {e}")
                time.sleep(5 * (attempt + 1))

        return None

    def fetch_data_type(self, data_type, label, source_tag, existing_names, checkpoint):
        """
        Fetch all foods of a given USDA dataType using paginated search.
        Saves checkpoint after each page so runs can be resumed.
        """
        ck_key     = f"page_{data_type.replace(' ', '_')}"
        start_page = checkpoint.get(ck_key, 1)
        foods      = []

        # Probe total count
        q = "*" if data_type == "Survey (FNDDS)" else ""
        probe = self._get("foods/search", {
            "dataType": data_type,
            "query":    q,
            "pageSize": 1,
            "pageNumber": 1,
        })
        if not probe:
            log.error(f"Could not reach USDA API for {data_type}")
            return []

        total_hits  = probe.get("totalHits", 0)
        total_pages = (total_hits + PAGE_SIZE - 1) // PAGE_SIZE

        log.info(f"\n{'─'*60}")
        log.info(f"  {label}")
        log.info(f"  Total: {total_hits:,} foods  |  Pages: {total_pages}  |  "
                 f"Resuming from page {start_page}")

        if self.is_demo:
            eta = (total_pages - start_page + 1) * (REQ_DELAY + BATCH_PAUSE / 25)
            log.info(f"  ETA with DEMO_KEY: ~{eta/3600:.1f} hours")

        for page in range(start_page, total_pages + 1):
            log.info(f"  -> Page {page}/{total_pages}  "
                     f"({len(foods):,} new collected)...")

            # USDA API requires a non-empty query for some dataTypes
            # Using '*' works as a wildcard for all foods
            q = "*" if data_type == "Survey (FNDDS)" else ""
            data = self._get("foods/search", {
                "dataType":   data_type,
                "query":      q,
                "pageSize":   PAGE_SIZE,
                "pageNumber": page,
            })
            if not data:
                log.warning(f"  Empty response page {page}, skipping")
                continue

            for f in data.get("foods", []):
                name = (f.get("description") or "").strip()
                if not name or name in existing_names:
                    continue

                nutrients = extract_nutrients(f.get("foodNutrients", []))
                if not has_required_nutrients(nutrients):
                    continue

                # Get USDA category
                usda_cat = f.get("foodCategory")
                if not usda_cat and isinstance(f.get("wweiaFoodCategory"), dict):
                    usda_cat = f["wweiaFoodCategory"].get(
                        "wweiaFoodCategoryDescription"
                    )

                category = infer_category(name, usda_cat)

                record = {
                    "name":        name[:255],
                    "category":    category,
                    "data_source": source_tag,
                    "fdc_id":      f.get("fdcId"),
                    **nutrients,
                }
                foods.append(record)
                existing_names.add(name)

            # Save checkpoint and running cache after every page
            checkpoint[ck_key] = page + 1
            save_checkpoint(checkpoint)

        log.info(f"  DONE: {label} -> {len(foods):,} new foods")
        return foods


# ─── Supabase Upload ──────────────────────────────────────────────────────────

def upload_to_supabase(foods):
    """
    Upload all foods to Supabase base_foods table using direct PostgreSQL.
    Uses INSERT ... ON CONFLICT (name) DO UPDATE so re-runs are idempotent.
    """
    if not DATABASE_URL:
        log.error("DATABASE_URL not set in .env — cannot upload")
        sys.exit(1)

    log.info(f"\n{'─'*60}")
    log.info(f"Uploading {len(foods):,} foods to Supabase...")

    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    # Ensure table exists with all columns
    cur.execute("""
        CREATE TABLE IF NOT EXISTS base_foods (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(255) UNIQUE NOT NULL,
            category    VARCHAR(100),
            calories    FLOAT,
            protein     FLOAT,
            carbs       FLOAT,
            fat         FLOAT,
            fiber       FLOAT,
            sugar       FLOAT,
            sodium      FLOAT,
            chol        FLOAT,
            data_source VARCHAR(50) DEFAULT 'unknown',
            fdc_id      INTEGER
        );
    """)

    # Add new columns if upgrading from old schema
    for col, dtype in [("data_source", "VARCHAR(50)"), ("fdc_id", "INTEGER")]:
        cur.execute(f"""
            ALTER TABLE base_foods
            ADD COLUMN IF NOT EXISTS {col} {dtype};
        """)

    conn.commit()

    # Batch upsert in chunks of 500
    BATCH = 500
    for i in range(0, len(foods), BATCH):
        batch = foods[i : i + BATCH]

        rows = [
            (
                r["name"],
                r.get("category", "other"),
                r.get("calories"),
                r.get("protein"),
                r.get("carbs"),
                r.get("fat"),
                r.get("fiber"),
                r.get("sugar"),
                r.get("sodium"),
                r.get("chol"),
                r.get("data_source", "unknown"),
                r.get("fdc_id"),
            )
            for r in batch
        ]

        execute_values(
            cur,
            """
            INSERT INTO base_foods
                (name, category, calories, protein, carbs, fat,
                 fiber, sugar, sodium, chol, data_source, fdc_id)
            VALUES %s
            ON CONFLICT (name) DO UPDATE SET
                category    = EXCLUDED.category,
                calories    = EXCLUDED.calories,
                protein     = EXCLUDED.protein,
                carbs       = EXCLUDED.carbs,
                fat         = EXCLUDED.fat,
                fiber       = EXCLUDED.fiber,
                sugar       = EXCLUDED.sugar,
                sodium      = EXCLUDED.sodium,
                chol        = EXCLUDED.chol,
                data_source = EXCLUDED.data_source,
                fdc_id      = EXCLUDED.fdc_id
            """,
            rows,
            page_size=500,
        )
        conn.commit()

        pct = (i + len(batch)) / len(foods) * 100
        log.info(f"  Batch {i//BATCH + 1}: "
                 f"{i + len(batch):,}/{len(foods):,} ({pct:.0f}%)")

    # Report final state
    cur.execute("SELECT COUNT(*) FROM base_foods;")
    db_total = cur.fetchone()[0]

    cur.execute("""
        SELECT data_source, COUNT(*) as n
        FROM base_foods
        GROUP BY data_source
        ORDER BY n DESC;
    """)
    source_counts = cur.fetchall()

    cur.execute("""
        SELECT category, COUNT(*) as n
        FROM base_foods
        GROUP BY category
        ORDER BY n DESC
        LIMIT 15;
    """)
    cat_counts = cur.fetchall()

    cur.close()
    conn.close()

    log.info(f"\n{'='*60}")
    log.info(f"  Upload complete!")
    log.info(f"  Total rows in base_foods: {db_total:,}")
    log.info(f"\n  By data source (accuracy tier):")
    for source, count in source_counts:
        src_label = source or "unknown"
        stars = {
            "usda_sr_legacy":   "Lab-analyzed      *****",
            "usda_foundation":  "Analytically verified *****",
            "usda_fndds":       "Recipe-calculated ****",
            "usda_branded":     "Manufacturer-reported ***",
        }.get(src_label, "")
        log.info(f"    {src_label:<25} {count:>6,}  {stars}")
    log.info(f"\n  Top categories:")
    for cat, count in cat_counts:
        log.info(f"    {cat:<20} {count:>6,}")
    log.info(f"{'='*60}\n")


# ─── Stats command ─────────────────────────────────────────────────────────────

def show_stats():
    if not DATABASE_URL:
        log.error("DATABASE_URL not set")
        return
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM base_foods;")
    log.info(f"Total foods in Supabase: {cur.fetchone()[0]:,}")
    cur.execute("""
        SELECT data_source, COUNT(*) FROM base_foods
        GROUP BY data_source ORDER BY 2 DESC;
    """)
    for row in cur.fetchall():
        log.info(f"  {row[0]:<25} {row[1]:>6,}")
    cur.close()
    conn.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NutriTrack USDA food fetcher")
    parser.add_argument("--upload",      action="store_true",
                        help="Fetch AND upload to Supabase")
    parser.add_argument("--upload-only", action="store_true",
                        help="Skip fetch, upload cached data only")
    parser.add_argument("--fresh",       action="store_true",
                        help="Ignore checkpoint, restart from scratch")
    parser.add_argument("--stats",       action="store_true",
                        help="Show Supabase stats and exit")
    parser.add_argument("--sr-only",     action="store_true",
                        help="Only fetch SR Legacy (7,793 foods, fastest)")
    parser.add_argument("--no-branded",  action="store_true",
                        help="Skip branded foods")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.upload_only:
        foods = load_cached_foods()
        if not foods:
            log.error("No cached foods. Run without --upload-only first.")
            sys.exit(1)
        log.info(f"Loaded {len(foods):,} cached foods")
        upload_to_supabase(foods)
        return

    # ── Warn about DEMO_KEY ────────────────────────────────────────────────
    if IS_DEMO_KEY:
        print("\n" + "=" * 60)
        print("  WARNING: Using DEMO_KEY (limited to 30 req/hour)")
        print()
        print("  For MUCH faster results, get a free personal API key:")
        print("  https://fdc.nal.usda.gov/api-key-signup.html")
        print("  Then add to .env: USDA_API_KEY=your_key_here")
        print()
        print("  With DEMO_KEY:")
        print("    SR Legacy only  ~3 hours")
        print("    All sources     ~18 hours (split across days)")
        print()
        print("  With personal key (1000 req/hr):")
        print("    All sources     ~5 minutes")
        print("=" * 60 + "\n")
        time.sleep(3)
    else:
        log.info(f"Using personal USDA API key — fast mode")

    checkpoint   = {} if args.fresh else load_checkpoint()
    all_foods    = load_cached_foods() if not args.fresh else []
    known_names  = {f["name"] for f in all_foods}

    log.info(f"\n{'='*60}")
    log.info(f"  NutriTrack USDA Food Fetcher")
    log.info(f"  API Key: {'DEMO_KEY (slow)' if IS_DEMO_KEY else 'Personal key (fast)'}")
    log.info(f"  Cached:  {len(all_foods):,} foods already downloaded")
    log.info(f"{'='*60}")

    fetcher = USDAFetcher(USDA_API_KEY)

    # 1. SR Legacy — 7,793 lab-analyzed foods *****
    sr = fetcher.fetch_data_type(
        data_type      = "SR Legacy",
        label          = "SR Legacy  ~7,793 lab-analyzed foods  *****",
        source_tag     = "usda_sr_legacy",
        existing_names = known_names,
        checkpoint     = checkpoint,
    )
    all_foods.extend(sr)
    known_names.update(f["name"] for f in sr)
    save_cached_foods(all_foods)

    if not args.sr_only:
        # 2. Foundation Foods — ~2,000 analytically verified *****
        found = fetcher.fetch_data_type(
            data_type      = "Foundation",
            label          = "Foundation Foods  ~2,000 analytically verified  *****",
            source_tag     = "usda_foundation",
            existing_names = known_names,
            checkpoint     = checkpoint,
        )
        all_foods.extend(found)
        known_names.update(f["name"] for f in found)
        save_cached_foods(all_foods)

        # 3. Survey / FNDDS — 7,000+ prepared dishes ****
        survey = fetcher.fetch_data_type(
            data_type      = "Survey (FNDDS)",
            label          = "Survey/FNDDS  ~7,000 prepared dishes  ****",
            source_tag     = "usda_fndds",
            existing_names = known_names,
            checkpoint     = checkpoint,
        )
        all_foods.extend(survey)
        known_names.update(f["name"] for f in survey)
        save_cached_foods(all_foods)

        # 4. Branded — curated popular items ***
        if not args.no_branded:
            branded_queries = [
                # Global packaged foods
                "yogurt", "protein powder", "whey protein", "energy bar",
                "granola", "peanut butter", "almond butter", "oat milk",
                "almond milk", "soy milk", "protein shake", "trail mix",
                "olive oil", "coconut oil", "pasta sauce", "soup canned",
                "whole grain bread", "cheese slice", "frozen meal",
                "plant based meat", "tofu brand", "tempeh",
                # Snacks
                "chips potato", "popcorn", "crackers whole grain",
                "protein bar", "granola bar", "dark chocolate",
                # Global cereals
                "muesli", "cornflakes", "bran cereal",
                # Beverages
                "kombucha", "cold brew coffee", "green tea bottled",
                "coconut water", "sports drink electrolyte",
                # International branded foods (USDA has these too)
                "basmati rice", "whole wheat flour", "chickpea pasta",
                "black bean", "lentil soup", "bone broth",
                "ghee brand", "paneer brand",
            ]

            branded_all = []
            for query in branded_queries:
                ck = f"branded_{query.replace(' ', '_')}"
                if ck in checkpoint:
                    continue
                log.info(f"  -> Branded: {query}")
                data = fetcher._get("foods/search", {
                    "dataType":   "Branded",
                    "query":      query,
                    "pageSize":   100,
                    "pageNumber": 1,
                })
                if data:
                    for f in data.get("foods", []):
                        name = (f.get("description") or "").strip()
                        if not name or name in known_names:
                            continue
                        nutrients = extract_nutrients(f.get("foodNutrients", []))
                        if not has_required_nutrients(nutrients):
                            continue
                        brand    = f.get("brandOwner", "")
                        fullname = f"{name} ({brand})" if brand else name
                        record   = {
                            "name":        fullname[:255],
                            "category":    infer_category(fullname, f.get("foodCategory")),
                            "data_source": "usda_branded",
                            "fdc_id":      f.get("fdcId"),
                            **nutrients,
                        }
                        branded_all.append(record)
                        known_names.add(name)
                checkpoint[ck] = True
                save_checkpoint(checkpoint)

            all_foods.extend(branded_all)
            save_cached_foods(all_foods)
            log.info(f"  Branded: {len(branded_all):,} new foods collected")

    # Summary
    log.info(f"\n{'='*60}")
    log.info(f"  Fetch complete! Total: {len(all_foods):,} foods")
    source_counts = {}
    for f in all_foods:
        s = f.get("data_source", "unknown")
        source_counts[s] = source_counts.get(s, 0) + 1
    for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        log.info(f"    {source:<25} {count:>6,}")
    log.info(f"{'='*60}")

    if args.upload:
        upload_to_supabase(all_foods)
    else:
        log.info("\nFoods saved to cache. To upload:")
        log.info("  python scripts/fetch_usda_foods.py --upload-only")


if __name__ == "__main__":
    main()
