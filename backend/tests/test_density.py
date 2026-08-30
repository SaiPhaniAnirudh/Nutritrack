"""
NutriTrack — Tests for 3D Food Density & Volumetric Mass Engine
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from nutrition.density import calculate_3d_volumetric_mass, get_density_for_food


def test_salad_low_density():
    d = get_density_for_food("Greek Salad with Spinach")
    assert d == 0.25  # Aerated leafy greens have low bulk density


def test_cooked_rice_volumetric_mass():
    # 10cm diameter circular mound (~78.5 cm²), 4cm height
    res = calculate_3d_volumetric_mass("Steamed Basmati Rice", surface_area_cm2=78.5, height_cm=4.0, shape_type="mound")
    assert res["volume_cm3"] > 180.0
    assert 140.0 <= res["estimated_mass_g"] <= 200.0


def test_curry_high_density():
    # 60 cm² surface area, 3cm deep curry layer
    res = calculate_3d_volumetric_mass("Chicken Tikka Masala Curry", surface_area_cm2=60.0, height_cm=3.0, shape_type="layer")
    assert res["density_g_cm3"] >= 0.95
    assert res["estimated_mass_g"] > 140.0
