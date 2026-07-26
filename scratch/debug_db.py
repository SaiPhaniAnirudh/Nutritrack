"""Debug: check if user exists in the DB and test inserting a food log."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

db_url = os.getenv('DATABASE_URL', '').strip().strip('"').strip("'")
db_url = db_url.replace('postgres://', 'postgresql://')

from sqlalchemy import create_engine, text
engine = create_engine(db_url, connect_args={'connect_timeout': 15})

with engine.connect() as conn:
    # Check all users
    print("=== Users in DB ===")
    result = conn.execute(text("SELECT id, name, email, created_at FROM public.users ORDER BY created_at DESC LIMIT 15"))
    rows = result.fetchall()
    for r in rows:
        print(f"  id={r[0][:12]}... name={r[1]}, email={r[2]}, created={r[3]}")
    print(f"  Total: {len(rows)} users shown")
    
    # Check food_logs table
    print("\n=== Recent food_logs ===")
    result = conn.execute(text("SELECT id, user_id, date, name, cal FROM public.food_logs ORDER BY id DESC LIMIT 5"))
    rows = result.fetchall()
    if rows:
        for r in rows:
            print(f"  id={r[0]}, user_id={r[1][:12]}..., date={r[2]}, food={r[3]}, cal={r[4]}")
    else:
        print("  (no food logs)")
    
    # Check the current role the connection uses
    print("\n=== Current DB role ===")
    result = conn.execute(text("SELECT current_user, current_setting('role')"))
    r = result.fetchone()
    print(f"  current_user: {r[0]}, role setting: {r[1]}")
    
    # Check if the postgres user is superuser
    print("\n=== Superuser check ===")
    result = conn.execute(text("SELECT rolname, rolsuper FROM pg_roles WHERE rolname = current_user"))
    r = result.fetchone()
    if r:
        print(f"  Role: {r[0]}, is_superuser: {r[1]}")
    
    # Check food_logs foreign key constraint
    print("\n=== food_logs FK constraints ===")
    result = conn.execute(text("""
        SELECT tc.constraint_name, ccu.table_name AS foreign_table, ccu.column_name AS foreign_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'food_logs' AND tc.constraint_type = 'FOREIGN KEY'
    """))
    for r in result.fetchall():
        print(f"  {r[0]}: references {r[1]}.{r[2]}")

    # Check if user with email like 'sai' or matching the screenshot exists
    print("\n=== Looking for Sai's user record ===")
    result = conn.execute(text("SELECT id, name, email FROM public.users WHERE name ILIKE '%sai%' OR email ILIKE '%sai%' OR email ILIKE '%anirudh%'"))
    rows = result.fetchall()
    for r in rows:
        print(f"  id={r[0]}, name={r[1]}, email={r[2]}")
    if not rows:
        print("  NOT FOUND - this is the problem!")

    # Check auth.users to find the authenticated user
    print("\n=== auth.users (Supabase auth) ===")
    result = conn.execute(text("SELECT id, email, created_at FROM auth.users ORDER BY created_at DESC LIMIT 5"))
    rows = result.fetchall()
    for r in rows:
        print(f"  id={r[0]}, email={r[1]}, created={r[2]}")
