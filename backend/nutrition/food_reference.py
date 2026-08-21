"""
NutriTrack — Verified Food Reference Catalog (USDA SR Legacy & IFCT 2024)
Provides deterministic, zero-latency in-memory search for staples and regional dishes.
"""

REFERENCE_FOODS = [
    # Indian Regional Cuisine
    {"name": "Chicken Biryani", "target": "biryani", "cal": 520.0, "pro": 32.0, "carb": 58.0, "fat": 16.0, "cat": "South Asian"},
    {"name": "Mutton Biryani", "target": "biryani", "cal": 580.0, "pro": 35.0, "carb": 56.0, "fat": 22.0, "cat": "South Asian"},
    {"name": "Vegetable Biryani", "target": "biryani", "cal": 380.0, "pro": 8.5, "carb": 68.0, "fat": 9.0, "cat": "South Asian"},
    {"name": "Masala Dosa", "target": "dosa", "cal": 385.0, "pro": 7.2, "carb": 58.0, "fat": 14.0, "cat": "South Asian"},
    {"name": "Plain Dosa", "target": "dosa", "cal": 220.0, "pro": 5.0, "carb": 38.0, "fat": 6.0, "cat": "South Asian"},
    {"name": "Yellow Dal Tadka", "target": "dal", "cal": 180.0, "pro": 12.0, "carb": 26.0, "fat": 4.0, "cat": "South Asian"},
    {"name": "Dal Makhani", "target": "dal", "cal": 340.0, "pro": 14.0, "carb": 36.0, "fat": 16.0, "cat": "South Asian"},
    {"name": "Paneer Tikka", "target": "paneer", "cal": 320.0, "pro": 18.0, "carb": 12.0, "fat": 22.0, "cat": "South Asian"},
    {"name": "Palak Paneer", "target": "paneer", "cal": 350.0, "pro": 16.0, "carb": 14.0, "fat": 26.0, "cat": "South Asian"},
    {"name": "Chole Masala (Chickpea Curry)", "target": "chole", "cal": 280.0, "pro": 13.0, "carb": 42.0, "fat": 7.0, "cat": "South Asian"},
    {"name": "Rajma Masala (Red Kidney Beans)", "target": "rajma", "cal": 240.0, "pro": 14.0, "carb": 38.0, "fat": 4.0, "cat": "South Asian"},
    {"name": "Vegetable Samosa", "target": "samosa", "cal": 350.0, "pro": 5.0, "carb": 42.0, "fat": 18.0, "cat": "South Asian"},
    {"name": "Flattened Rice Poha", "target": "poha", "cal": 270.0, "pro": 4.5, "carb": 48.0, "fat": 7.0, "cat": "South Asian"},
    {"name": "Semolina Upma", "target": "upma", "cal": 250.0, "pro": 5.5, "carb": 44.0, "fat": 6.0, "cat": "South Asian"},
    {"name": "Steamed Idli (3 pcs)", "target": "idli", "cal": 180.0, "pro": 6.0, "carb": 36.0, "fat": 1.0, "cat": "South Asian"},
    {"name": "Whole Wheat Roti / Chapati", "target": "roti", "cal": 140.0, "pro": 4.5, "carb": 28.0, "fat": 1.5, "cat": "South Asian"},
    {"name": "Butter Naan (1 pc)", "target": "naan", "cal": 260.0, "pro": 7.0, "carb": 42.0, "fat": 7.5, "cat": "South Asian"},
    {"name": "Butter Chicken", "target": "butter chicken", "cal": 450.0, "pro": 34.0, "carb": 16.0, "fat": 28.0, "cat": "South Asian"},
    {"name": "Gulab Jamun (2 pcs)", "target": "gulab jamun", "cal": 320.0, "pro": 4.0, "carb": 48.0, "fat": 13.0, "cat": "South Asian"},

    # Global Staples
    {"name": "Fresh Banana (Medium)", "target": "banana", "cal": 105.0, "pro": 1.3, "carb": 27.0, "fat": 0.3, "cat": "Fruit"},
    {"name": "Red Apple (Medium)", "target": "apple", "cal": 95.0, "pro": 0.5, "carb": 25.0, "fat": 0.3, "cat": "Fruit"},
    {"name": "Grilled Chicken Breast (200g)", "target": "chicken breast", "cal": 330.0, "pro": 62.0, "carb": 0.0, "fat": 7.2, "cat": "High-Protein"},
    {"name": "Hard Boiled Egg (2 pcs)", "target": "boiled egg", "cal": 156.0, "pro": 12.6, "carb": 1.1, "fat": 10.6, "cat": "High-Protein"},
    {"name": "Steamed White Rice (1 cup)", "target": "white rice cooked", "cal": 234.0, "pro": 4.6, "carb": 53.2, "fat": 0.4, "cat": "Grains"},
    {"name": "Whole Milk (1 cup / 240ml)", "target": "whole milk", "cal": 149.0, "pro": 7.7, "carb": 11.7, "fat": 7.9, "cat": "Dairy"},
    {"name": "Raw Almonds (28g / 1oz)", "target": "almonds", "cal": 164.0, "pro": 6.0, "carb": 6.1, "fat": 14.2, "cat": "Nuts"},
    {"name": "Steamed Broccoli (150g)", "target": "broccoli", "cal": 52.0, "pro": 4.2, "carb": 10.5, "fat": 0.6, "cat": "Vegetables"},
    {"name": "Baked Salmon Fillet (150g)", "target": "salmon", "cal": 312.0, "pro": 34.0, "carb": 0.0, "fat": 18.5, "cat": "High-Protein"},
    {"name": "Fresh Avocado (Half / 100g)", "target": "avocado", "cal": 160.0, "pro": 2.0, "carb": 8.5, "fat": 14.7, "cat": "Fruit"},
    {"name": "Cooked Oatmeal (1 cup)", "target": "oatmeal cooked", "cal": 158.0, "pro": 6.0, "carb": 28.0, "fat": 3.2, "cat": "Grains"},
    {"name": "Low-Fat Cottage Cheese (150g)", "target": "cottage cheese", "cal": 120.0, "pro": 18.0, "carb": 5.0, "fat": 3.0, "cat": "Dairy"},
    {"name": "Baked Sweet Potato (150g)", "target": "sweet potato", "cal": 135.0, "pro": 3.0, "carb": 31.0, "fat": 0.2, "cat": "Vegetables"},
]


def search_reference_foods(query: str, limit: int = 20):
    q_clean = query.lower().strip()
    q_words = [w for w in q_clean.split() if len(w) > 1]
    
    exact_matches = []
    prefix_matches = []
    fuzzy_matches = []

    for item in REFERENCE_FOODS:
        name_lower = item["name"].lower()
        target_lower = item["target"].lower()

        # 1. Exact match on target or name
        if q_clean == target_lower or q_clean == name_lower:
            exact_matches.append(item)
        # 2. Substring match
        elif q_clean in target_lower or q_clean in name_lower or target_lower in q_clean:
            prefix_matches.append(item)
        # 3. Word token overlap
        elif any(w in name_lower or w in target_lower for w in q_words):
            fuzzy_matches.append(item)

    all_matches = exact_matches + prefix_matches + fuzzy_matches
    # Deduplicate while preserving rank order
    seen = set()
    unique_matches = []
    for m in all_matches:
        if m["name"] not in seen:
            seen.add(m["name"])
            unique_matches.append(m)
            if len(unique_matches) >= limit:
                break

    return unique_matches

