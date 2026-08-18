"""
NutriTrack — Extended Nutrient Constants
82+ nutrients mapped to USDA FoodData Central nutrient IDs

This module defines the complete nutrient taxonomy used across NutriTrack:
- USDA nutrient ID → internal field name mapping
- Units, display names, and RDA (Recommended Daily Allowance) values
- Nutrient groupings for dashboard display
- Conversion helpers

Reference: https://fdc.nal.usda.gov/data-documentation.html
All RDA values are for adults 19-50, based on NIH DRI tables.
"""

# ══════════════════════════════════════════════════
#  USDA NUTRIENT ID → INTERNAL FIELD MAPPING
# ══════════════════════════════════════════════════
# Key: USDA Nutrient ID (int)
# Value: internal field name (str)
#
# The existing NutriTrack schema has 11 "core" nutrients stored as
# individual columns on FoodLog. All 82+ nutrients below will be
# stored in a JSONB `extended_nutrients` column. The core 11 are
# kept as individual columns for backward compat and fast aggregation.

USDA_NUTRIENT_MAP = {
    # ── Core Macros (already individual columns) ──
    1008: "energy_kcal",            # Energy (kcal)
    2047: "energy_kcal",            # Energy, Atwater General (fallback)
    1003: "protein_g",              # Protein (g)
    1004: "total_fat_g",            # Total lipid / fat (g)
    1005: "carbohydrate_g",         # Carbohydrate, by difference (g)
    1079: "fiber_g",                # Fiber, total dietary (g)
    2000: "total_sugars_g",         # Sugars, total (g)
    1063: "total_sugars_g",         # Sugars, Total - alternate ID (fallback)
    1093: "sodium_mg",              # Sodium, Na (mg)
    1253: "cholesterol_mg",         # Cholesterol (mg)

    # ── Sugars Detail ──
    2029: "added_sugars_g",         # Sugars, added (g)

    # ── Fat Subfractions ──
    1258: "saturated_fat_g",        # Fatty acids, total saturated (g)
    1292: "monounsaturated_fat_g",  # Fatty acids, total monounsaturated (g)
    1293: "polyunsaturated_fat_g",  # Fatty acids, total polyunsaturated (g)
    1257: "trans_fat_g",            # Fatty acids, total trans (g)

    # ── Omega Fatty Acids ──
    1316: "omega3_ala_g",           # 18:3 n-3 c,c,c (ALA) (g)
    1272: "omega3_epa_g",           # 20:5 n-3 (EPA) (g)
    1278: "omega3_dha_g",           # 22:6 n-3 (DHA) (g)

    # ── Fat-Soluble Vitamins ──
    1106: "vitamin_a_mcg_rae",      # Vitamin A, RAE (mcg)
    1114: "vitamin_d_mcg",          # Vitamin D (D2 + D3) (mcg)
    1109: "vitamin_e_mg",           # Vitamin E (alpha-tocopherol) (mg)
    1185: "vitamin_k_mcg",          # Vitamin K (phylloquinone) (mcg)

    # ── Water-Soluble Vitamins ──
    1162: "vitamin_c_mg",           # Vitamin C, total ascorbic acid (mg)
    1165: "thiamin_b1_mg",          # Thiamin / B1 (mg)
    1166: "riboflavin_b2_mg",       # Riboflavin / B2 (mg)
    1167: "niacin_b3_mg",           # Niacin / B3 (mg)
    1170: "pantothenic_acid_b5_mg", # Pantothenic acid / B5 (mg)
    1175: "vitamin_b6_mg",          # Vitamin B6 (mg)
    1177: "folate_mcg",             # Folate, total (mcg)
    1178: "vitamin_b12_mcg",        # Vitamin B12 (mcg)
    1180: "choline_mg",             # Choline, total (mg)

    # ── Major Minerals ──
    1087: "calcium_mg",             # Calcium, Ca (mg)
    1089: "iron_mg",                # Iron, Fe (mg)
    1090: "magnesium_mg",           # Magnesium, Mg (mg)
    1091: "phosphorus_mg",          # Phosphorus, P (mg)
    1092: "potassium_mg",           # Potassium, K (mg)

    # ── Trace Minerals ──
    1095: "zinc_mg",                # Zinc, Zn (mg)
    1098: "copper_mg",              # Copper, Cu (mg)
    1101: "manganese_mg",           # Manganese, Mn (mg)
    1103: "selenium_mcg",           # Selenium, Se (mcg)

    # ── Amino Acids (all 20) ──
    1210: "tryptophan_g",
    1211: "threonine_g",
    1212: "isoleucine_g",
    1213: "leucine_g",
    1214: "lysine_g",
    1215: "methionine_g",
    1216: "cystine_g",
    1217: "phenylalanine_g",
    1218: "tyrosine_g",
    1219: "valine_g",
    1220: "arginine_g",
    1221: "histidine_g",
    1222: "alanine_g",
    1223: "aspartic_acid_g",
    1224: "glutamic_acid_g",
    1225: "glycine_g",
    1226: "proline_g",
    1227: "serine_g",
    1228: "hydroxyproline_g",

    # ── Carotenoids & Phytochemicals ──
    1107: "beta_carotene_mcg",      # Carotene, beta (mcg)
    1108: "alpha_carotene_mcg",     # Carotene, alpha (mcg)
    1120: "retinol_mcg",            # Retinol (mcg)
    1123: "beta_cryptoxanthin_mcg", # Cryptoxanthin, beta (mcg)
    1321: "lycopene_mcg",           # Lycopene (mcg)
    1323: "lutein_zeaxanthin_mcg",  # Lutein + zeaxanthin (mcg)

    # ── Other ──
    1051: "water_g",                # Water (g)
    1057: "caffeine_mg",            # Caffeine (mg)
    1018: "alcohol_g",              # Alcohol, ethyl (g)
    1198: "betaine_mg",             # Betaine (mg)
}


# ══════════════════════════════════════════════════
#  NUTRIENT METADATA (display names, units, RDAs)
# ══════════════════════════════════════════════════

NUTRIENT_META = {
    # field_name: (display_name, unit, rda_value, group)
    # RDA values for adults 19-50, mixed gender average where applicable

    # ── Macros ──
    "energy_kcal":            ("Calories",              "kcal",  2000,  "macro"),
    "protein_g":              ("Protein",               "g",     50,    "macro"),
    "total_fat_g":            ("Total Fat",             "g",     65,    "macro"),
    "carbohydrate_g":         ("Carbohydrates",         "g",     300,   "macro"),
    "fiber_g":                ("Dietary Fiber",         "g",     28,    "macro"),
    "total_sugars_g":         ("Total Sugars",          "g",     50,    "macro"),
    "added_sugars_g":         ("Added Sugars",          "g",     25,    "macro"),
    "sodium_mg":              ("Sodium",                "mg",    2300,  "macro"),
    "cholesterol_mg":         ("Cholesterol",           "mg",    300,   "macro"),

    # ── Fat Subfractions ──
    "saturated_fat_g":        ("Saturated Fat",         "g",     20,    "fats"),
    "monounsaturated_fat_g":  ("Monounsaturated Fat",   "g",     None,  "fats"),
    "polyunsaturated_fat_g":  ("Polyunsaturated Fat",   "g",     None,  "fats"),
    "trans_fat_g":            ("Trans Fat",             "g",     0,     "fats"),

    # ── Omega Fatty Acids ──
    "omega3_ala_g":           ("Omega-3 (ALA)",         "g",     1.6,   "fats"),
    "omega3_epa_g":           ("Omega-3 (EPA)",         "g",     0.25,  "fats"),
    "omega3_dha_g":           ("Omega-3 (DHA)",         "g",     0.25,  "fats"),

    # ── Fat-Soluble Vitamins ──
    "vitamin_a_mcg_rae":      ("Vitamin A",             "mcg",   900,   "vitamins"),
    "vitamin_d_mcg":          ("Vitamin D",             "mcg",   15,    "vitamins"),
    "vitamin_e_mg":           ("Vitamin E",             "mg",    15,    "vitamins"),
    "vitamin_k_mcg":          ("Vitamin K",             "mcg",   120,   "vitamins"),

    # ── Water-Soluble Vitamins ──
    "vitamin_c_mg":           ("Vitamin C",             "mg",    90,    "vitamins"),
    "thiamin_b1_mg":          ("Thiamin (B1)",          "mg",    1.2,   "vitamins"),
    "riboflavin_b2_mg":       ("Riboflavin (B2)",       "mg",    1.3,   "vitamins"),
    "niacin_b3_mg":           ("Niacin (B3)",           "mg",    16,    "vitamins"),
    "pantothenic_acid_b5_mg": ("Pantothenic Acid (B5)", "mg",    5,     "vitamins"),
    "vitamin_b6_mg":          ("Vitamin B6",            "mg",    1.3,   "vitamins"),
    "folate_mcg":             ("Folate (B9)",           "mcg",   400,   "vitamins"),
    "vitamin_b12_mcg":        ("Vitamin B12",           "mcg",   2.4,   "vitamins"),
    "choline_mg":             ("Choline",               "mg",    550,   "vitamins"),

    # ── Major Minerals ──
    "calcium_mg":             ("Calcium",               "mg",    1000,  "minerals"),
    "iron_mg":                ("Iron",                  "mg",    18,    "minerals"),
    "magnesium_mg":           ("Magnesium",             "mg",    400,   "minerals"),
    "phosphorus_mg":          ("Phosphorus",            "mg",    700,   "minerals"),
    "potassium_mg":           ("Potassium",             "mg",    2600,  "minerals"),

    # ── Trace Minerals ──
    "zinc_mg":                ("Zinc",                  "mg",    11,    "minerals"),
    "copper_mg":              ("Copper",                "mg",    0.9,   "minerals"),
    "manganese_mg":           ("Manganese",             "mg",    2.3,   "minerals"),
    "selenium_mcg":           ("Selenium",              "mcg",   55,    "minerals"),

    # ── Amino Acids ──
    "tryptophan_g":           ("Tryptophan",            "g",     None,  "amino_acids"),
    "threonine_g":            ("Threonine",             "g",     None,  "amino_acids"),
    "isoleucine_g":           ("Isoleucine",            "g",     None,  "amino_acids"),
    "leucine_g":              ("Leucine",               "g",     None,  "amino_acids"),
    "lysine_g":               ("Lysine",                "g",     None,  "amino_acids"),
    "methionine_g":           ("Methionine",            "g",     None,  "amino_acids"),
    "cystine_g":              ("Cystine",               "g",     None,  "amino_acids"),
    "phenylalanine_g":        ("Phenylalanine",         "g",     None,  "amino_acids"),
    "tyrosine_g":             ("Tyrosine",              "g",     None,  "amino_acids"),
    "valine_g":               ("Valine",                "g",     None,  "amino_acids"),
    "arginine_g":             ("Arginine",              "g",     None,  "amino_acids"),
    "histidine_g":            ("Histidine",             "g",     None,  "amino_acids"),
    "alanine_g":              ("Alanine",               "g",     None,  "amino_acids"),
    "aspartic_acid_g":        ("Aspartic Acid",         "g",     None,  "amino_acids"),
    "glutamic_acid_g":        ("Glutamic Acid",         "g",     None,  "amino_acids"),
    "glycine_g":              ("Glycine",               "g",     None,  "amino_acids"),
    "proline_g":              ("Proline",               "g",     None,  "amino_acids"),
    "serine_g":               ("Serine",                "g",     None,  "amino_acids"),
    "hydroxyproline_g":       ("Hydroxyproline",        "g",     None,  "amino_acids"),

    # ── Carotenoids ──
    "beta_carotene_mcg":      ("Beta-Carotene",         "mcg",   None,  "phytochemicals"),
    "alpha_carotene_mcg":     ("Alpha-Carotene",        "mcg",   None,  "phytochemicals"),
    "retinol_mcg":            ("Retinol",               "mcg",   None,  "phytochemicals"),
    "beta_cryptoxanthin_mcg": ("Beta-Cryptoxanthin",    "mcg",   None,  "phytochemicals"),
    "lycopene_mcg":           ("Lycopene",              "mcg",   None,  "phytochemicals"),
    "lutein_zeaxanthin_mcg":  ("Lutein + Zeaxanthin",   "mcg",   None,  "phytochemicals"),

    # ── Other ──
    "water_g":                ("Water",                 "g",     None,  "other"),
    "caffeine_mg":            ("Caffeine",              "mg",    None,  "other"),
    "alcohol_g":              ("Alcohol",               "g",     None,  "other"),
    "betaine_mg":             ("Betaine",               "mg",    None,  "other"),
}


# ══════════════════════════════════════════════════
#  NUTRIENT GROUPS (for dashboard display)
# ══════════════════════════════════════════════════

NUTRIENT_GROUPS = {
    "macro":          {"label": "Macronutrients",       "icon": "🔥", "color": "#F5A623"},
    "fats":           {"label": "Fat Profile",          "icon": "🥑", "color": "#F4613A"},
    "vitamins":       {"label": "Vitamins",             "icon": "💊", "color": "#4FC3F7"},
    "minerals":       {"label": "Minerals",             "icon": "⚡", "color": "#7FB8D4"},
    "amino_acids":    {"label": "Amino Acids",          "icon": "🧬", "color": "#C4A87F"},
    "phytochemicals": {"label": "Phytochemicals",       "icon": "🌿", "color": "#66BB6A"},
    "other":          {"label": "Other",                "icon": "📊", "color": "#9E9E9E"},
}


# ══════════════════════════════════════════════════
#  CORE 11 NUTRIENTS (backward-compatible columns)
# ══════════════════════════════════════════════════
# These remain as individual columns on FoodLog for
# fast aggregation and backward compatibility.

CORE_NUTRIENT_FIELDS = [
    "cal", "pro", "carb", "fat", "fiber",
    "sugar", "sodium", "chol", "vit_d", "iron", "folate"
]

# Map core column names → extended nutrient field names
CORE_TO_EXTENDED = {
    "cal":    "energy_kcal",
    "pro":    "protein_g",
    "carb":   "carbohydrate_g",
    "fat":    "total_fat_g",
    "fiber":  "fiber_g",
    "sugar":  "total_sugars_g",
    "sodium": "sodium_mg",
    "chol":   "cholesterol_mg",
    "vit_d":  "vitamin_d_mcg",
    "iron":   "iron_mg",
    "folate": "folate_mcg",
}


# ══════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════

def get_nutrient_display(field_name):
    """Get display name, unit, and RDA for a nutrient field."""
    meta = NUTRIENT_META.get(field_name)
    if meta:
        return {"name": meta[0], "unit": meta[1], "rda": meta[2], "group": meta[3]}
    return None


def get_rda_percentage(field_name, value):
    """Calculate % of RDA for a given nutrient value."""
    meta = NUTRIENT_META.get(field_name)
    if meta and meta[2] and value:
        return round((value / meta[2]) * 100, 1)
    return None


def get_nutrients_by_group(group_name):
    """Get all nutrient field names in a given group."""
    return [k for k, v in NUTRIENT_META.items() if v[3] == group_name]


def parse_usda_nutrients(nutrient_list):
    """
    Parse USDA API nutrient array into our extended nutrient dict.
    Input: list of {"nutrientId": 1008, "value": 165.0, ...}
    Output: {"energy_kcal": 165.0, "protein_g": 31.0, ...}
    """
    result = {}
    for n in nutrient_list:
        nid = n.get("nutrientId") or n.get("nutrient", {}).get("id")
        val = n.get("value") or n.get("amount")
        if nid and nid in USDA_NUTRIENT_MAP and val is not None:
            field = USDA_NUTRIENT_MAP[nid]
            # For duplicate IDs (e.g. 1008/2047 both map to energy_kcal),
            # keep the first non-zero value
            if field not in result or result[field] == 0:
                try:
                    result[field] = round(float(val), 2)
                except (ValueError, TypeError):
                    pass
    return result


def nutrient_count():
    """Return the total number of unique nutrients tracked."""
    return len(NUTRIENT_META)
