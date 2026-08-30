"""
Unit tests for backend/nutrition/nutrients.py — the USDA nutrient
ID mapping and parsing logic behind the 82+ micronutrient tracking claim.

Run:
    pytest backend/tests/test_nutrients.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from nutrition.nutrients import (
    parse_usda_nutrients,
    get_rda_percentage,
    get_nutrient_display,
    get_nutrients_by_group,
    nutrient_count,
)


def test_parses_basic_usda_nutrient_list():
    """A typical USDA FDC response should map nutrient IDs to internal field names."""
    usda_response = [
        {"nutrientId": 1008, "value": 165.0},   # energy_kcal
        {"nutrientId": 1003, "value": 31.0},    # protein_g
        {"nutrientId": 1004, "value": 3.6},     # total_fat_g
    ]
    result = parse_usda_nutrients(usda_response)
    assert result["energy_kcal"] == 165.0
    assert result["protein_g"] == 31.0
    assert result["total_fat_g"] == 3.6


def test_handles_alternate_field_names_amount_and_nested_id():
    """USDA sometimes nests the ID and uses 'amount' instead of 'value' — both should parse."""
    usda_response = [
        {"nutrient": {"id": 1003}, "amount": 25.0},
    ]
    result = parse_usda_nutrients(usda_response)
    assert result["protein_g"] == 25.0


def test_duplicate_nutrient_ids_keep_first_nonzero_value():
    """Energy has two USDA IDs (1008, 2047); a zero value shouldn't overwrite a real one."""
    usda_response = [
        {"nutrientId": 1008, "value": 200.0},
        {"nutrientId": 2047, "value": 0.0},
    ]
    result = parse_usda_nutrients(usda_response)
    assert result["energy_kcal"] == 200.0


def test_unmapped_nutrient_ids_are_ignored():
    """A nutrient ID not in USDA_NUTRIENT_MAP should be silently skipped, not crash."""
    usda_response = [
        {"nutrientId": 999999, "value": 42.0},
        {"nutrientId": 1003, "value": 10.0},
    ]
    result = parse_usda_nutrients(usda_response)
    assert "protein_g" in result
    assert len(result) == 1


def test_missing_or_null_values_are_skipped():
    usda_response = [
        {"nutrientId": 1003, "value": None},
        {"nutrientId": 1004, "value": 5.0},
    ]
    result = parse_usda_nutrients(usda_response)
    assert "protein_g" not in result
    assert result["total_fat_g"] == 5.0


def test_non_numeric_value_does_not_crash():
    usda_response = [{"nutrientId": 1003, "value": "not-a-number"}]
    result = parse_usda_nutrients(usda_response)
    assert result == {}


def test_empty_list_returns_empty_dict():
    assert parse_usda_nutrients([]) == {}


def test_rda_percentage_calculation():
    """RDA % should be (value / rda) * 100, rounded to 1 decimal."""
    pct = get_rda_percentage("vitamin_c_mg", 45.0)
    display = get_nutrient_display("vitamin_c_mg")
    if display and display["rda"]:
        expected = round((45.0 / display["rda"]) * 100, 1)
        assert pct == expected


def test_rda_percentage_returns_none_for_unknown_field():
    assert get_rda_percentage("not_a_real_nutrient", 10.0) is None


def test_get_nutrient_display_returns_none_for_unknown_field():
    assert get_nutrient_display("not_a_real_nutrient") is None


def test_nutrient_count_regression_guard():
    """
    Pins the actual nutrient count so future edits can't silently drop
    coverage. NOTE: as of this writing NUTRIENT_META tracks 67 nutrients,
    not the 82+ advertised in the frontend UI (App.js) and README — see
    the discrepancy noted in nutrient-count-discrepancy.txt. Update this
    assertion (and the marketing copy, in one direction or the other)
    together when that gap is resolved.
    """
    assert nutrient_count() >= 67


def test_get_nutrients_by_group_returns_a_list():
    vitamins = get_nutrients_by_group("vitamins")
    assert isinstance(vitamins, list)