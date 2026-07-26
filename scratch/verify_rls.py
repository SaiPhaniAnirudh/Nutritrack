"""Verify RLS policies are correct after fix."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

db_url = os.getenv('DATABASE_URL', '').strip().strip('"').strip("'")
db_url = db_url.replace('postgres://', 'postgresql://')

from sqlalchemy import create_engine, text
engine = create_engine(db_url, connect_args={'connect_timeout': 15})

with engine.connect() as conn:
    print("=== RLS Status ===")
    result = conn.execute(text("""
        SELECT n.nspname, c.relname, c.relrowsecurity, c.relforcerowsecurity 
        FROM pg_class c JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE c.relname IN ('users', 'food_logs')
    """))
    for r in result.fetchall():
        print(f"  {r[0]}.{r[1]}: RLS={r[2]}, Force={r[3]}")

    print("\n=== All Policies ===")
    result = conn.execute(text("""
        SELECT tablename, policyname, cmd, permissive, roles
        FROM pg_policies 
        WHERE tablename IN ('users', 'food_logs')
        ORDER BY tablename, policyname
    """))
    for r in result.fetchall():
        print(f"  [{r[0]}] {r[1]} | cmd={r[2]} | roles={r[4]}")
    
    print("\nDone.")
