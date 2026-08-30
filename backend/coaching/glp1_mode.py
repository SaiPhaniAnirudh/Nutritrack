"""
NutriTrack — GLP-1 Medication Nutrition Protocol
Provides specialized dietary safeguards for users taking GLP-1 receptor agonists
(e.g., Semaglutide / Wegovy / Ozempic / Tirzepatide / Mounjaro / Zepbound).

Clinical Safeguards:
1. Lean Muscle Preservation: Enforces high protein baseline (>= 100g/day or 1.6-2.0 g/kg).
2. GI Symptom Mitigation: Tracks hydration (>= 2500ml) and gradual fiber intake (28-35g).
3. Nutrient Density Safeguard: Flags micronutrient gaps caused by rapid appetite suppression.
"""



def evaluate_glp1_compliance(
    daily_logs: list[dict],
    water_ml: float,
    weight_kg: float
) -> dict:
    """
    Evaluate today's dietary adequacy under GLP-1 therapy guidelines.
    
    Returns:
        dict with compliance score, warnings, and clinical recommendations.
    """
    total_cal = sum(float(l.get("cal", 0)) for l in daily_logs)
    total_pro = sum(float(l.get("pro", 0)) for l in daily_logs)
    total_fiber = sum(float(l.get("fiber", 0)) for l in daily_logs)

    # Protein minimum calculation (1.6g/kg or 100g)
    protein_minimum = max(100.0, weight_kg * 1.6)
    water_minimum = 2500.0  # ml
    fiber_minimum = 28.0    # g

    alerts = []
    recommendations = []

    # 1. Protein Check
    protein_pct = min(100, round((total_pro / protein_minimum) * 100))
    if total_pro < protein_minimum * 0.7:
        alerts.append({
            "type": "protein_deficit",
            "severity": "high",
            "message": f"Protein intake ({round(total_pro)}g) is below the GLP-1 safety threshold ({round(protein_minimum)}g). Lean muscle mass may be at risk."
        })
        recommendations.append("Prioritize protein-dense snacks (Greek yogurt, whey, eggs, tofu) before other food groups.")
    elif total_pro >= protein_minimum:
        recommendations.append("💪 Excellent protein intake! Your muscle mass is well-protected.")

    # 2. Hydration Check
    water_pct = min(100, round((water_ml / water_minimum) * 100))
    if water_ml < 1500:
        alerts.append({
            "type": "dehydration_risk",
            "severity": "medium",
            "message": f"Hydration ({round(water_ml)}ml) is low. Drink at least 2500ml daily to prevent GLP-1 related nausea and constipation."
        })

    # 3. Low Calorie Starvation Guard
    if 0 < total_cal < 1000:
        alerts.append({
            "type": "severe_caloric_restriction",
            "severity": "high",
            "message": "Daily intake is under 1,000 kcal. Extreme restriction can trigger gallstone formation and nutrient depletion."
        })

    # Overall Compliance Score (0-100)
    score = round((protein_pct * 0.5) + (water_pct * 0.3) + (min(100, (total_fiber / fiber_minimum) * 100) * 0.2))

    return {
        "glp1_active": True,
        "compliance_score": score,
        "protein": {
            "current_g": round(total_pro, 1),
            "target_min_g": round(protein_minimum, 1),
            "pct": protein_pct
        },
        "hydration": {
            "current_ml": round(water_ml),
            "target_min_ml": round(water_minimum),
            "pct": water_pct
        },
        "fiber": {
            "current_g": round(total_fiber, 1),
            "target_min_g": round(fiber_minimum, 1),
            "pct": min(100, round((total_fiber / fiber_minimum) * 100))
        },
        "alerts": alerts,
        "recommendations": recommendations
    }
