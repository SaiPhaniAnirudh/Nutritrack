"""Add RLS policy for postgres role (used by backend via SQLAlchemy)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

db_url = os.getenv('DATABASE_URL', '').strip().strip('"').strip("'")
db_url = db_url.replace('postgres://', 'postgresql://')

from sqlalchemy import create_engine, text
engine = create_engine(db_url, connect_args={'connect_timeout': 15})

with engine.connect() as conn:
    print("Adding ALL policy for postgres role on users table...")
    conn.execute(text('DROP POLICY IF EXISTS "postgres_all_users" ON public.users'))
    conn.execute(text("""
        CREATE POLICY "postgres_all_users" ON public.users
        FOR ALL TO postgres
        USING (true)
        WITH CHECK (true)
    """))
    print("  Done.")

    print("Adding ALL policy for postgres role on food_logs table...")
    conn.execute(text('DROP POLICY IF EXISTS "postgres_all_food_logs" ON public.food_logs'))
    conn.execute(text("""
        CREATE POLICY "postgres_all_food_logs" ON public.food_logs
        FOR ALL TO postgres
        USING (true)
        WITH CHECK (true)
    """))
    print("  Done.")

    conn.commit()

    # Verify
    print("\n=== All policies now ===")
    result = conn.execute(text("""
        SELECT tablename, policyname, cmd, roles
        FROM pg_policies 
        WHERE tablename IN ('users', 'food_logs')
        ORDER BY tablename, policyname
    """))
    for r in result.fetchall():
        print(f"  [{r[0]}] {r[1]} | cmd={r[2]} | roles={r[3]}")

    # Quick test: can we read users now?
    print("\n=== Test: reading users ===")
    result = conn.execute(text("SELECT count(*) FROM public.users"))
    print(f"  User count: {result.fetchone()[0]}")

    print("\nAll fixed!")
