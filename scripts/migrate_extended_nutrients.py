#!/usr/bin/env python3
"""
NutriTrack — Database Migration: Extended Nutrients & Clinical Schema
Adds `extended_nutrients`, `nutrient_source`, and `serving_size` columns
to `food_logs` table (PostgreSQL & SQLite compatible), and backfills existing rows.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT / "backend"))
from nutrition.nutrients import CORE_TO_EXTENDED


def run_migration():
    print("🔄 Starting NutriTrack Extended Nutrients Database Migration...")

    database_url = os.environ.get("DATABASE_URL")
    
    if database_url and database_url.startswith("postgres"):
        import psycopg2
        print("📊 Connecting to PostgreSQL (Supabase)...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # 1. Add columns to food_logs
        cur.execute("""
            ALTER TABLE food_logs 
            ADD COLUMN IF NOT EXISTS extended_nutrients JSONB DEFAULT '{}'::jsonb,
            ADD COLUMN IF NOT EXISTS nutrient_source VARCHAR(100) DEFAULT 'manual',
            ADD COLUMN IF NOT EXISTS serving_size VARCHAR(100) DEFAULT '1 serving';
        """)

        # 2. Add scan_corrections table for AI personalization loop
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scan_corrections (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                original_food VARCHAR(200),
                corrected_food VARCHAR(200),
                original_cal NUMERIC(7,1) DEFAULT 0,
                corrected_cal NUMERIC(7,1) DEFAULT 0,
                portion_multiplier NUMERIC(4,2) DEFAULT 1.0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Add columns to base_foods if base_foods table exists
        cur.execute("""
            DO $$
            BEGIN
                IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'base_foods') THEN
                    ALTER TABLE base_foods 
                    ADD COLUMN IF NOT EXISTS extended_nutrients JSONB DEFAULT '{}'::jsonb;
                END IF;
            END $$;
        """)

        conn.commit()
        print("✅ PostgreSQL columns and scan_corrections table verified and added.")

        # 3. Backfill existing food_logs rows that have empty extended_nutrients
        cur.execute("SELECT id, cal, pro, carb, fat, fiber, sugar, sodium, chol, vit_d, iron, folate FROM food_logs WHERE extended_nutrients IS NULL OR extended_nutrients = '{}'::jsonb")
        rows = cur.fetchall()
        print(f"📝 Backfilling {len(rows)} existing food log entries...")

        for r in rows:
            lid = r[0]
            ext = {
                "energy_kcal": r[1] or 0,
                "protein_g": r[2] or 0,
                "carbohydrate_g": r[3] or 0,
                "total_fat_g": r[4] or 0,
                "fiber_g": r[5] or 0,
                "total_sugars_g": r[6] or 0,
                "sodium_mg": r[7] or 0,
                "cholesterol_mg": r[8] or 0,
                "vitamin_d_mcg": r[9] or 0,
                "iron_mg": r[10] or 0,
                "folate_mcg": r[11] or 0,
            }
            cur.execute("UPDATE food_logs SET extended_nutrients = %s WHERE id = %s", (json.dumps(ext), lid))

        conn.commit()
        cur.close()
        conn.close()
        print("🎉 PostgreSQL migration completed successfully!")

    else:
        # SQLite fallback for local test instances
        import sqlite3
        db_path = ROOT / "instance" / "nutritrack.db"
        if not db_path.exists():
            db_path = ROOT / "nutritrack.db"
            
        if db_path.exists():
            print(f"📊 Connecting to SQLite: {db_path}...")
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()

            cols = [c[1] for c in cur.execute("PRAGMA table_info(food_logs)").fetchall()]
            
            if "extended_nutrients" not in cols:
                cur.execute("ALTER TABLE food_logs ADD COLUMN extended_nutrients TEXT DEFAULT '{}'")
            if "nutrient_source" not in cols:
                cur.execute("ALTER TABLE food_logs ADD COLUMN nutrient_source TEXT DEFAULT 'manual'")
            if "serving_size" not in cols:
                cur.execute("ALTER TABLE food_logs ADD COLUMN serving_size TEXT DEFAULT '1 serving'")

            conn.commit()
            conn.close()
            print("✅ SQLite columns verified and added.")
        else:
            print("ℹ️ No local SQLite database file found — schema will be auto-created on startup via SQLAlchemy.")


if __name__ == "__main__":
    run_migration()
