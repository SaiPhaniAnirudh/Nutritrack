"""
Fix RLS policies on Supabase PostgreSQL directly.
Connects using DATABASE_URL from .env and executes policy fixes.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

db_url = os.getenv('DATABASE_URL', '').strip().strip('"').strip("'")
if not db_url:
    print("ERROR: DATABASE_URL not found in .env")
    sys.exit(1)

db_url = db_url.replace('postgres://', 'postgresql://')
print(f"Connecting to: {db_url[:40]}...")

try:
    from sqlalchemy import create_engine, text
    engine = create_engine(db_url, connect_args={'connect_timeout': 15})
    
    with engine.connect() as conn:
        # First, check current policies
        print("\n=== Current RLS policies on 'users' table ===")
        result = conn.execute(text("SELECT policyname, cmd, permissive, roles, qual, with_check FROM pg_policies WHERE tablename = 'users'"))
        rows = result.fetchall()
        if rows:
            for r in rows:
                print(f"  Policy: {r[0]}, Cmd: {r[1]}, Permissive: {r[2]}, Roles: {r[3]}")
                print(f"    USING: {r[4]}")
                print(f"    WITH CHECK: {r[5]}")
        else:
            print("  (no policies found)")
        
        print("\n=== Current RLS policies on 'food_logs' table ===")
        result = conn.execute(text("SELECT policyname, cmd, permissive, roles, qual, with_check FROM pg_policies WHERE tablename = 'food_logs'"))
        rows = result.fetchall()
        if rows:
            for r in rows:
                print(f"  Policy: {r[0]}, Cmd: {r[1]}, Permissive: {r[2]}, Roles: {r[3]}")
                print(f"    USING: {r[4]}")
                print(f"    WITH CHECK: {r[5]}")
        else:
            print("  (no policies found)")

        # Check if RLS is enabled on these tables
        print("\n=== RLS status ===")
        result = conn.execute(text("""
            SELECT relname, relrowsecurity, relforcerowsecurity 
            FROM pg_class 
            WHERE relname IN ('users', 'food_logs')
        """))
        for r in result.fetchall():
            print(f"  Table: {r[0]}, RLS enabled: {r[1]}, Force RLS: {r[2]}")
        
        print("\n=== Fixing RLS policies ===")
        
        # Drop all existing policies on users
        print("Dropping existing policies on users...")
        existing = conn.execute(text("SELECT policyname FROM pg_policies WHERE tablename = 'users'")).fetchall()
        for (pname,) in existing:
            conn.execute(text(f'DROP POLICY IF EXISTS "{pname}" ON public.users'))
            print(f"  Dropped: {pname}")
        
        # Drop all existing policies on food_logs
        print("Dropping existing policies on food_logs...")
        existing = conn.execute(text("SELECT policyname FROM pg_policies WHERE tablename = 'food_logs'")).fetchall()
        for (pname,) in existing:
            conn.execute(text(f'DROP POLICY IF EXISTS "{pname}" ON public.food_logs'))
            print(f"  Dropped: {pname}")
        
        # Ensure RLS is enabled
        conn.execute(text("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY"))
        conn.execute(text("ALTER TABLE public.food_logs ENABLE ROW LEVEL SECURITY"))
        print("RLS enabled on both tables.")
        
        # Create policies for 'users' table
        print("Creating policies for users table...")
        conn.execute(text("""
            CREATE POLICY "users_select_own" ON public.users
            FOR SELECT TO authenticated
            USING ((auth.uid())::text = (id)::text)
        """))
        conn.execute(text("""
            CREATE POLICY "users_insert_own" ON public.users
            FOR INSERT TO authenticated
            WITH CHECK ((auth.uid())::text = (id)::text)
        """))
        conn.execute(text("""
            CREATE POLICY "users_update_own" ON public.users
            FOR UPDATE TO authenticated
            USING ((auth.uid())::text = (id)::text)
            WITH CHECK ((auth.uid())::text = (id)::text)
        """))
        print("  Created: users_select_own, users_insert_own, users_update_own")
        
        # Create policies for 'food_logs' table
        print("Creating policies for food_logs table...")
        conn.execute(text("""
            CREATE POLICY "food_logs_select_own" ON public.food_logs
            FOR SELECT TO authenticated
            USING ((auth.uid())::text = (user_id)::text)
        """))
        conn.execute(text("""
            CREATE POLICY "food_logs_insert_own" ON public.food_logs
            FOR INSERT TO authenticated
            WITH CHECK ((auth.uid())::text = (user_id)::text)
        """))
        conn.execute(text("""
            CREATE POLICY "food_logs_update_own" ON public.food_logs
            FOR UPDATE TO authenticated
            USING ((auth.uid())::text = (user_id)::text)
            WITH CHECK ((auth.uid())::text = (user_id)::text)
        """))
        conn.execute(text("""
            CREATE POLICY "food_logs_delete_own" ON public.food_logs
            FOR DELETE TO authenticated
            USING ((auth.uid())::text = (user_id)::text)
        """))
        print("  Created: food_logs_select_own, food_logs_insert_own, food_logs_update_own, food_logs_delete_own")
        
        conn.commit()
        print("\n✅ All RLS policies fixed successfully!")
        
        # Verify
        print("\n=== Verification: Updated policies ===")
        result = conn.execute(text("SELECT tablename, policyname, cmd, roles FROM pg_policies WHERE tablename IN ('users', 'food_logs') ORDER BY tablename, policyname"))
        for r in result.fetchall():
            print(f"  {r[0]}: {r[1]} ({r[2]}) -> {r[3]}")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
