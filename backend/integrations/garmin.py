"""
NutriTrack — Garmin Connect & Oura Ring Integration Adapter
Parses activity summaries, steps, and active calories burned to feed into the Adaptive TDEE engine.
"""

from datetime import datetime
from typing import Dict, List, Any


def parse_garmin_activity_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a Garmin Connect activity webhook or JSON export.
    """
    activities = payload.get("activities", [])
    total_active_calories = 0.0
    synced_sessions = []
    
    for act in activities:
        act_name = act.get("activityName") or act.get("activityType", "Workout")
        cals = float(act.get("calories", act.get("activeKilocalories", 0)))
        duration_min = round(float(act.get("duration", act.get("durationInSeconds", 0))) / 60.0)
        
        total_active_calories += cals
        synced_sessions.append({
            "name": act_name,
            "cal_burned": cals,
            "duration_min": duration_min,
            "source": "Garmin Connect"
        })

    return {
        "source": "Garmin Connect",
        "total_active_calories": round(total_active_calories, 1),
        "sessions_count": len(synced_sessions),
        "sessions": synced_sessions
    }
