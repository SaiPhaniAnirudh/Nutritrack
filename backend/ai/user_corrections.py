"""
NutriTrack — AI User Correction Learning Loop
Learns from user edits and personal portion habits to continuously improve scan accuracy.

How it works:
1. When a user edits a food scan (e.g. adjusting 150g -> 220g), we record the delta in `scan_corrections`.
2. Over time (10+ corrections), we compute per-user portion bias multipliers for common food categories.
3. The Three-Way Fusion engine queries this module before returning results to scale portions to the user's personal eating habits.
"""



def record_scan_correction(
    user_id: str,
    original_food: str,
    corrected_food: str,
    original_cal: float,
    corrected_cal: float,
    db_session=None
) -> dict:
    """
    Record a user correction to fine-tune the personal vision model.
    """
    multiplier = (corrected_cal / max(original_cal, 1.0)) if original_cal > 0 else 1.0
    # Clamp multiplier for statistical stability
    multiplier = max(0.4, min(3.0, multiplier))

    record = {
        "user_id": user_id,
        "original_food": (original_food or "").strip().lower(),
        "corrected_food": (corrected_food or "").strip().lower(),
        "original_cal": round(original_cal, 1),
        "corrected_cal": round(corrected_cal, 1),
        "portion_multiplier": round(multiplier, 2),
    }

    # Save to scan_corrections table if database is available
    if db_session:
        try:
            from sqlalchemy import text
            db_session.execute(text("""
                INSERT INTO scan_corrections (user_id, original_food, corrected_food, original_cal, corrected_cal, portion_multiplier)
                VALUES (:user_id, :original_food, :corrected_food, :original_cal, :corrected_cal, :portion_multiplier)
            """), record)
            db_session.commit()
        except Exception as e:
            if db_session:
                db_session.rollback()
            print(f"⚠️ scan_corrections record notice: {e}")

    return record


def get_user_portion_multiplier(user_id: str, food_name: str, db_session=None) -> float:
    """
    Get the learned portion scaling multiplier for a user and food item.
    Defaults to 1.0 if insufficient history.
    """
    if not user_id or not db_session:
        return 1.0

    try:
        from sqlalchemy import text
        res = db_session.execute(text("""
            SELECT AVG(portion_multiplier) as avg_mult
            FROM scan_corrections
            WHERE user_id = :uid AND (original_food ILIKE :fn OR corrected_food ILIKE :fn)
        """), {"uid": user_id, "fn": f"%{food_name.strip()}%"}).fetchone()

        if res and res[0] is not None:
            return round(float(res[0]), 2)
    except Exception as e:
        print(f"⚠️ portion multiplier lookup notice: {e}")

    return 1.0
