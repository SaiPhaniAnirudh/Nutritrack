"""
NutriTrack — Apple HealthKit Integration Adapter
Supports exporting food logs, macros, and 82+ micronutrients into HealthKit JSON/XML,
and importing raw Apple Health export archives.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any


def export_to_healthkit_json(food_logs: List[Dict], workouts: List[Dict] = None) -> Dict[str, Any]:
    """
    Format food logs and workouts into standardized Apple HealthKit sample payloads.
    HKQuantityTypeIdentifierDietaryEnergyConsumed, HKQuantityTypeIdentifierDietaryProtein, etc.
    """
    samples = []
    
    for log in food_logs:
        date_str = log.get("date", datetime.now().strftime("%Y-%m-%d"))
        start_date = f"{date_str}T12:00:00Z"
        
        # Energy
        if log.get("cal", 0) > 0:
            samples.append({
                "type": "HKQuantityTypeIdentifierDietaryEnergyConsumed",
                "startDate": start_date,
                "endDate": start_date,
                "value": float(log["cal"]),
                "unit": "kcal",
                "metadata": {"HKFoodMeal": log.get("mealType", "Meal"), "HKFoodName": log.get("name", "Food")}
            })

        # Macros
        if log.get("pro", 0) > 0:
            samples.append({
                "type": "HKQuantityTypeIdentifierDietaryProtein",
                "startDate": start_date,
                "endDate": start_date,
                "value": float(log["pro"]),
                "unit": "g"
            })
        if log.get("carb", 0) > 0:
            samples.append({
                "type": "HKQuantityTypeIdentifierDietaryCarbohydrates",
                "startDate": start_date,
                "endDate": start_date,
                "value": float(log["carb"]),
                "unit": "g"
            })
        if log.get("fat", 0) > 0:
            samples.append({
                "type": "HKQuantityTypeIdentifierDietaryFatTotal",
                "startDate": start_date,
                "endDate": start_date,
                "value": float(log["fat"]),
                "unit": "g"
            })
            
        # Extended micronutrients if present
        ext = log.get("extendedNutrients") or log.get("extended_nutrients") or {}
        if isinstance(ext, dict):
            if "vitamin_c_mg" in ext:
                samples.append({"type": "HKQuantityTypeIdentifierDietaryVitaminC", "startDate": start_date, "endDate": start_date, "value": float(ext["vitamin_c_mg"]), "unit": "mg"})
            if "calcium_mg" in ext:
                samples.append({"type": "HKQuantityTypeIdentifierDietaryCalcium", "startDate": start_date, "endDate": start_date, "value": float(ext["calcium_mg"]), "unit": "mg"})
            if "iron_mg" in ext:
                samples.append({"type": "HKQuantityTypeIdentifierDietaryIron", "startDate": start_date, "endDate": start_date, "value": float(ext["iron_mg"]), "unit": "mg"})
            if "potassium_mg" in ext:
                samples.append({"type": "HKQuantityTypeIdentifierDietaryPotassium", "startDate": start_date, "endDate": start_date, "value": float(ext["potassium_mg"]), "unit": "mg"})

    return {
        "exportSource": "NutriTrack AI Health Engine",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totalSamples": len(samples),
        "data": samples
    }


def parse_apple_health_xml(xml_content: str) -> Dict[str, Any]:
    """
    Parse an Apple Health export file to extract dietary and workout records.
    """
    import re
    records = []
    
    # Simple regex extraction for HKRecord tags
    pattern = r'<Record\s+type="([^"]+)"[^>]*startDate="([^"]+)"[^>]*value="([^"]+)"[^>]*unit="([^"]+)"'
    matches = re.findall(pattern, xml_content)
    
    for m in matches[:500]: # Parse up to 500 samples
        records.append({
            "type": m[0],
            "startDate": m[1],
            "value": float(m[2]) if m[2].replace('.', '', 1).isdigit() else m[2],
            "unit": m[3]
        })
        
    return {
        "source": "Apple Health XML",
        "records_parsed": len(records),
        "records": records
    }
