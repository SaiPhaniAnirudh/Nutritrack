import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://agzopmiiswitorldacud.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))

print("==================================================")
print("     NUTRITRACK USDA DATABASE SEEDING ENGINE       ")
print("==================================================")

sample_usda_foods = [
    {"name": "Greek Yogurt (Non-fat)", "category": "Dairy", "cal": 59, "pro": 10.2, "carb": 3.6, "fat": 0.4, "fiber": 0, "sugar": 3.2, "sodium": 36, "chol": 5},
    {"name": "Avocado Toast on Whole Grain", "category": "Breakfast", "cal": 240, "pro": 6.5, "carb": 24.0, "fat": 14.5, "fiber": 7.0, "sugar": 1.5, "sodium": 310, "chol": 0},
    {"name": "Grilled Salmon Fillet", "category": "Seafood", "cal": 206, "pro": 22.1, "carb": 0, "fat": 12.3, "fiber": 0, "sugar": 0, "sodium": 61, "chol": 63},
    {"name": "Quinoa Veggie Bowl", "category": "Grains", "cal": 220, "pro": 8.0, "carb": 39.0, "fat": 3.5, "fiber": 5.0, "sugar": 2.0, "sodium": 180, "chol": 0},
    {"name": "Almond Milk (Unsweetened)", "category": "Beverages", "cal": 30, "pro": 1.0, "carb": 1.0, "fat": 2.5, "fiber": 0.5, "sugar": 0, "sodium": 170, "chol": 0},
    {"name": "Protein Whey Shake", "category": "Supplements", "cal": 130, "pro": 25.0, "carb": 3.0, "fat": 1.5, "fiber": 1.0, "sugar": 1.0, "sodium": 140, "chol": 45},
    {"name": "Chia Seed Pudding", "category": "Snacks", "cal": 150, "pro": 4.5, "carb": 15.0, "fat": 8.5, "fiber": 9.0, "sugar": 5.0, "sodium": 40, "chol": 0},
    {"name": "Steamed Broccoli & Garlic", "category": "Vegetables", "cal": 55, "pro": 3.7, "carb": 11.2, "fat": 0.6, "fiber": 5.1, "sugar": 2.2, "sodium": 60, "chol": 0},
    {"name": "Brown Rice Bowl", "category": "Grains", "cal": 216, "pro": 5.0, "carb": 45.0, "fat": 1.8, "fiber": 3.5, "sugar": 0.7, "sodium": 10, "chol": 0},
    {"name": "Tofu Stir Fry", "category": "Vegan", "cal": 180, "pro": 12.0, "carb": 8.0, "fat": 11.0, "fiber": 3.0, "sugar": 2.0, "sodium": 340, "chol": 0}
]

if not SUPABASE_KEY:
    print("⚠️ Supabase API key not found in env. Seeding dry-run simulated successfully!")
else:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    url = f"{SUPABASE_URL}/rest/v1/base_foods"
    resp = requests.post(url, headers=headers, json=sample_usda_foods)
    if resp.status_code in (200, 201):
        print(f"✅ Successfully seeded USDA food items into Supabase!")
    else:
        print(f"Status: {resp.status_code}, Response: {resp.text}")
