"""
NutriTrack — Tests for Protein Quality & DIAAS Engine
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from nutrition.protein_quality import calculate_protein_quality


def test_complete_protein_high_diaas():
    # Complete protein sample (like egg or whey with high EAAs)
    egg_nutrients = {
        "histidine_g": 0.35,
        "isoleucine_g": 0.70,
        "leucine_g": 1.10,
        "lysine_g": 0.90,
        "methionine_g": 0.40,
        "cystine_g": 0.30,
        "phenylalanine_g": 0.70,
        "tyrosine_g": 0.50,
        "threonine_g": 0.60,
        "tryptophan_g": 0.20,
        "valine_g": 0.85,
    }
    result = calculate_protein_quality(egg_nutrients, total_protein_g=13.0)
    assert result["diaas_score"] >= 90.0
    assert "Complete" in result["completeness_tier"]
    assert result["bcaa_total_g"] > 2.0
    assert result["eaa_total_g"] > 5.0


def test_incomplete_protein_detects_limiting_amino_acid():
    # Incomplete plant protein low in lysine (like wheat or grain)
    wheat_nutrients = {
        "histidine_g": 0.20,
        "isoleucine_g": 0.35,
        "leucine_g": 0.70,
        "lysine_g": 0.15,  # Artificially low lysine
        "methionine_g": 0.20,
        "cystine_g": 0.25,
        "phenylalanine_g": 0.50,
        "tyrosine_g": 0.35,
        "threonine_g": 0.30,
        "tryptophan_g": 0.12,
        "valine_g": 0.45,
    }
    result = calculate_protein_quality(wheat_nutrients, total_protein_g=10.0)
    assert result["diaas_score"] < 75.0
    assert result["limiting_amino_acid"] == "Lysine"


def test_zero_protein_returns_safe_zero():
    result = calculate_protein_quality({}, total_protein_g=0.0)
    assert result["diaas_score"] == 0.0
    assert result["bcaa_total_g"] == 0.0
