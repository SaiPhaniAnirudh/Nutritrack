"""
NutriTrack — Protein Quality & DIAAS Completeness Engine
Calculates Digestible Indispensable Amino Acid Score (DIAAS) and Amino Acid
completeness based on the WHO/FAO/UNU 2007 standard adult reference pattern.

Reference:
- WHO Technical Report Series 935: Protein and amino acid requirements in human nutrition.
- FAO Food and Nutrition Paper 92: Dietary protein quality evaluation in human nutrition.
"""

from typing import Dict, Any

# WHO/FAO 2007 Reference amino acid scoring pattern for adults (mg amino acid per g protein)
WHO_ADULT_EAA_PATTERN = {
    "histidine": 15.0,
    "isoleucine": 30.0,
    "leucine": 59.0,
    "lysine": 45.0,
    "methionine_cysteine": 22.0,  # SAA (Sulfur amino acids)
    "phenylalanine_tyrosine": 38.0,  # AAA (Aromatic amino acids)
    "threonine": 23.0,
    "tryptophan": 6.0,
    "valine": 39.0,
}


def calculate_protein_quality(
    extended_nutrients: Dict[str, Any],
    total_protein_g: float
) -> Dict[str, Any]:
    """
    Calculate amino acid completeness score, DIAAS ratio, and limiting amino acid
    for a logged meal or daily total.

    Args:
        extended_nutrients: Dict of tracked nutrient keys to values (grams)
        total_protein_g: Total crude protein in grams

    Returns:
        Dict containing:
        - diaas_score: float (0.0 - 100.0+)
        - completeness_tier: "Complete (High Quality)", "Good Quality", or "Incomplete (Needs Pairing)"
        - limiting_amino_acid: str or None
        - bcaa_total_g: float (Leucine + Isoleucine + Valine in grams)
        - eaa_total_g: float (Total Essential Amino Acids in grams)
        - ratios: Dict of amino acid to % of reference standard
    """
    if not total_protein_g or total_protein_g <= 0.5:
        return {
            "diaas_score": 0.0,
            "completeness_tier": "Insufficient Protein",
            "limiting_amino_acid": None,
            "bcaa_total_g": 0.0,
            "eaa_total_g": 0.0,
            "ratios": {}
        }

    # Extract amino acids (grams)
    trp = float(extended_nutrients.get("tryptophan_g") or 0.0)
    thr = float(extended_nutrients.get("threonine_g") or 0.0)
    ile = float(extended_nutrients.get("isoleucine_g") or 0.0)
    leu = float(extended_nutrients.get("leucine_g") or 0.0)
    lys = float(extended_nutrients.get("lysine_g") or 0.0)
    met = float(extended_nutrients.get("methionine_g") or 0.0)
    cys = float(extended_nutrients.get("cystine_g") or 0.0)
    phe = float(extended_nutrients.get("phenylalanine_g") or 0.0)
    tyr = float(extended_nutrients.get("tyrosine_g") or 0.0)
    val = float(extended_nutrients.get("valine_g") or 0.0)
    his = float(extended_nutrients.get("histidine_g") or 0.0)

    # Calculate BCAAs and Total EAAs
    bcaa_total_g = round(leu + ile + val, 2)
    eaa_total_g = round(trp + thr + ile + leu + lys + met + cys + phe + tyr + val + his, 2)

    # If amino acid data is missing from the record, return estimated defaults based on protein
    if eaa_total_g == 0:
        return {
            "diaas_score": 85.0,  # Standard mixed-diet baseline
            "completeness_tier": "Estimated (Standard Mixed)",
            "limiting_amino_acid": None,
            "bcaa_total_g": round(total_protein_g * 0.18, 2),
            "eaa_total_g": round(total_protein_g * 0.40, 2),
            "ratios": {}
        }

    # Convert g AA / g protein to mg AA / g protein: (g_aa / total_protein_g) * 1000
    mg_per_g = {
        "histidine": (his / total_protein_g) * 1000.0,
        "isoleucine": (ile / total_protein_g) * 1000.0,
        "leucine": (leu / total_protein_g) * 1000.0,
        "lysine": (lys / total_protein_g) * 1000.0,
        "methionine_cysteine": ((met + cys) / total_protein_g) * 1000.0,
        "phenylalanine_tyrosine": ((phe + tyr) / total_protein_g) * 1000.0,
        "threonine": (thr / total_protein_g) * 1000.0,
        "tryptophan": (trp / total_protein_g) * 1000.0,
        "valine": (val / total_protein_g) * 1000.0,
    }

    # Calculate individual amino acid scores relative to WHO standard
    ratios = {}
    min_ratio = 999.0
    limiting_aa = None

    for aa, ref_val in WHO_ADULT_EAA_PATTERN.items():
        actual_val = mg_per_g.get(aa, 0.0)
        score_pct = (actual_val / ref_val) * 100.0
        ratios[aa] = round(score_pct, 1)

        if score_pct < min_ratio:
            min_ratio = score_pct
            limiting_aa = aa.replace("_", " ").title()

    # DIAAS is defined by the lowest scoring indispensable amino acid ratio
    diaas_score = min(round(min_ratio, 1), 100.0)

    if diaas_score >= 90.0:
        completeness_tier = "Complete (High Quality)"
        limiting_aa = None  # No deficiency
    elif diaas_score >= 75.0:
        completeness_tier = "Good Quality"
    else:
        completeness_tier = f"Incomplete (Low {limiting_aa})"

    return {
        "diaas_score": diaas_score,
        "completeness_tier": completeness_tier,
        "limiting_amino_acid": limiting_aa,
        "bcaa_total_g": bcaa_total_g,
        "eaa_total_g": eaa_total_g,
        "ratios": ratios
    }
