"""
NutriTrack — USDA Food Density & Volumetric Mass Engine
Converts 3D geometric volume (cm³ / ml) into clinical mass (grams) using
empirical food bulk densities from USDA Agricultural Handbook No. 102 and
peer-reviewed food physics benchmarks.
"""

from typing import Dict, Any, Optional

# Empirical Bulk Densities (g/cm³ or g/ml)
FOOD_BULK_DENSITIES = {
    # Grains & Cereals
    "cooked_rice": 0.78,
    "cooked_pasta": 0.65,
    "cooked_oats": 0.85,
    "bread": 0.45,
    "roti_flatbread": 0.52,
    
    # Cooked Proteins
    "chicken_breast": 0.95,
    "beef_steak": 1.05,
    "fish_fillet": 0.88,
    "tofu_paneer": 0.92,
    "whole_egg": 1.02,
    
    # Liquids, Soups & Curries
    "curry_dal_stew": 1.02,
    "soup_broth": 1.00,
    "milk_yogurt": 1.03,
    "smoothie": 0.98,
    
    # Fruits & Vegetables
    "leafy_salad": 0.25,     # Highly porous/aerated
    "steamed_broccoli": 0.42,
    "cut_fruits": 0.68,
    "mashed_potato": 0.92,
    
    # Fats & Condiments
    "butter_oil_ghee": 0.91,
    "nut_butter": 1.10,
    "nuts_seeds": 0.62,
    
    # Default for unmapped mixed dishes
    "default_mixed": 0.85,
}


def get_density_for_food(food_name: str) -> float:
    """Find the closest matching empirical bulk density (g/cm³) for a given food name."""
    n = (food_name or "").lower()
    
    if any(k in n for k in ["salad", "spinach", "lettuce", "greens", "kale"]):
        return FOOD_BULK_DENSITIES["leafy_salad"]
    if any(k in n for k in ["rice", "biryani", "pulao", "quinoa", "grain"]):
        return FOOD_BULK_DENSITIES["cooked_rice"]
    if any(k in n for k in ["dal", "curry", "stew", "gravy", "soup", "sambhar"]):
        return FOOD_BULK_DENSITIES["curry_dal_stew"]
    if any(k in n for k in ["chicken", "meat", "beef", "steak", "mutton", "fish", "salmon"]):
        return FOOD_BULK_DENSITIES["chicken_breast"]
    if any(k in n for k in ["paneer", "tofu", "cheese"]):
        return FOOD_BULK_DENSITIES["tofu_paneer"]
    if any(k in n for k in ["roti", "naan", "bread", "toast", "paratha", "tortilla"]):
        return FOOD_BULK_DENSITIES["roti_flatbread"]
    if any(k in n for k in ["pasta", "noodle", "spaghetti", "macaroni"]):
        return FOOD_BULK_DENSITIES["cooked_pasta"]
    if any(k in n for k in ["fruit", "apple", "banana", "berry", "melon", "orange"]):
        return FOOD_BULK_DENSITIES["cut_fruits"]
    if any(k in n for k in ["nut", "seed", "almond", "peanut", "cashew"]):
        return FOOD_BULK_DENSITIES["nuts_seeds"]
    if any(k in n for k in ["oil", "butter", "ghee"]):
        return FOOD_BULK_DENSITIES["butter_oil_ghee"]
        
    return FOOD_BULK_DENSITIES["default_mixed"]


def calculate_3d_volumetric_mass(
    food_name: str,
    surface_area_cm2: float,
    height_cm: float,
    shape_type: str = "mound"
) -> Dict[str, Any]:
    """
    Calculate 3D volume in cm³ and calibrated physical mass in grams.
    
    Args:
        food_name: String name of the food
        surface_area_cm2: Estimated 2D top-down surface area in cm²
        height_cm: Estimated vertical depth/height in cm
        shape_type: "mound" (hemispherical ~0.67), "layer" (flat ~0.90), "piece" (~0.80)
        
    Returns:
        Dict with volume_cm3, density_g_cm3, estimated_mass_g
    """
    shape_factors = {
        "mound": 0.67,       # e.g. rice or salad mound (paraboloid/hemisphere)
        "layer": 0.90,       # e.g. curry or soup in a bowl
        "piece": 0.78,       # e.g. chicken breast or steak
        "cylinder": 0.785,   # e.g. cylindrical stack
    }
    
    factor = shape_factors.get(shape_type, 0.75)
    volume_cm3 = round(surface_area_cm2 * height_cm * factor, 1)
    
    density = get_density_for_food(food_name)
    estimated_mass_g = round(volume_cm3 * density, 1)
    
    return {
        "food_name": food_name,
        "surface_area_cm2": surface_area_cm2,
        "height_cm": height_cm,
        "shape_factor": factor,
        "volume_cm3": volume_cm3,
        "density_g_cm3": density,
        "estimated_mass_g": estimated_mass_g
    }
