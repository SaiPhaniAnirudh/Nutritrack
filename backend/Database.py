"""
NutriTrack — Database.py
Database management script

Commands:
    python Database.py init      — create all tables
    python Database.py seed      — add a demo user with sample logs
    python Database.py reset     — drop and recreate all tables (DESTRUCTIVE)
    python Database.py stats     — show user count, log count, recent activity
    python Database.py export    — backup all data to nutritrack_backup.json
    python Database.py list      — list all registered users

Usage:
    python Database.py init      ← run this first after installing
"""

import sys
import os
import json
from datetime import datetime, timezone, timedelta

# Load .env before importing App so DATABASE_URL is set
from dotenv import load_dotenv
load_dotenv()

from App import app, db, User, FoodLog, _hash_password


# ══════════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════════

def cmd_init():
    """Create all database tables."""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created.")
        print("   Tables: users, food_logs")
        print("   Location: nutritrack.db (SQLite)")


def cmd_seed():
    """Add a demo user with a week of sample food logs."""
    with app.app_context():
        # Check if demo user already exists
        existing = User.query.filter_by(email='demo@nutritrack.app').first()
        if existing:
            print("⚠️  Demo user already exists. Skipping seed.")
            print(f"   Email: demo@nutritrack.app  |  Password: Demo1234!")
            return

        # Create demo user
        user = User(
            name        = 'Demo User',
            email       = 'demo@nutritrack.app',
            password    = _hash_password('Demo1234!'),
            age         = 25,
            weight      = 70.0,
            weight_unit = 'kg',
            height      = 175.0,
            height_unit = 'cm',
            gender      = 'male',
            diet_goal   = 'maintain',
            goal_calories = 2000,
            goal_protein  = 150,
            goal_carbs    = 250,
            goal_fat      = 65,
            goal_fiber    = 28,
            goal_sugar    = 50,
            goal_sodium   = 2300,
            goal_chol     = 300,
        )
        db.session.add(user)
        db.session.flush()   # get user.id without committing

        # Sample logs for the past 7 days
        today   = datetime.now(timezone.utc).date()
        samples = [
            # (days_ago, meal, name, emoji, cal, pro, carb, fat, fiber, sugar, sodium, chol)
            (0, 'breakfast', 'Oats with banana',      '🥣', 320, 10, 58, 6,  4, 18, 120, 0),
            (0, 'lunch',     'Dal + rice',             '🍛', 450, 16, 80, 8,  6,  3, 380, 0),
            (0, 'dinner',    'Grilled chicken',        '🍗', 310, 36, 0,  7,  0,  0, 340, 95),
            (0, 'snack',     'Apple',                  '🍎',  95,  0, 25, 0,  4, 19,   2, 0),
            (1, 'breakfast', 'Boiled eggs × 2',        '🥚', 140, 12,  1, 10, 0,  0, 124, 424),
            (1, 'lunch',     'Paneer tikka',           '🧀', 290, 18,  8, 20, 1,  3, 480, 55),
            (1, 'dinner',    'Roti × 2 + sabzi',      '🫓', 300, 10, 52,  6, 5,  2, 220, 0),
            (1, 'snack',     'Mixed nuts',             '🥜', 180,  5,  8, 16, 2,  1,   5, 0),
            (2, 'breakfast', 'Idli × 3 + sambar',     '🫓', 220,  8, 42,  2, 3,  2, 420, 0),
            (2, 'lunch',     'Biryani',                '🍲', 420, 18, 62, 12, 2,  3, 580, 45),
            (2, 'dinner',    'Salad + grilled fish',   '🥗', 260, 28, 14,  8, 5,  6, 280, 60),
            (3, 'breakfast', 'Dosa + coconut chutney', '🫓', 250,  5, 44,  7, 2,  2, 350, 0),
            (3, 'lunch',     'Chole + 1 bhatura',     '🍛', 480, 16, 72, 18, 9,  4, 540, 0),
            (3, 'snack',     'Mango (1 cup)',          '🥭',  99,  1, 25,  1, 3, 22,   2, 0),
            (3, 'dinner',    'Chicken curry + rice',  '🍗', 480, 30, 55, 14, 2,  5, 620, 70),
            (4, 'breakfast', 'Banana + peanut butter','🍌', 250,  7, 38,  9, 3, 18,  70, 0),
            (4, 'lunch',     'Veg fried rice',        '🍳', 380, 10, 62,  9, 3,  3, 520, 30),
            (4, 'dinner',    'Paneer + roti × 2',     '🧀', 420, 20, 48, 16, 4,  3, 440, 45),
            (5, 'breakfast', 'Upma + chai',           '☕', 300,  7, 52,  8, 3,  6, 480, 0),
            (5, 'lunch',     'Palak dal + rice',      '🍛', 380, 15, 65,  7, 6,  3, 350, 0),
            (5, 'snack',     'Banana',                '🍌', 105,  1, 27,  0, 3, 14,   1, 0),
            (5, 'dinner',    'Pav bhaji',             '🍞', 440, 12, 68, 14, 5,  8, 620, 0),
            (6, 'breakfast', 'Paratha × 2 + curd',   '🫓', 380, 11, 52, 15, 4,  3, 320, 10),
            (6, 'lunch',     'Rajma + rice',          '🍛', 430, 18, 72,  7, 9,  4, 480, 0),
            (6, 'dinner',    'Grilled paneer salad',  '🥗', 320, 20, 16, 18, 4,  5, 380, 40),
        ]

        for days_ago, meal, name, emoji, cal, pro, carb, fat, fiber, sugar, sodium, chol in samples:
            log_date = (today - timedelta(days=days_ago)).isoformat()
            log = FoodLog(
                user_id   = user.id,
                date      = log_date,
                meal_type = meal,
                name      = name,
                emoji     = emoji,
                cal       = cal,
                pro       = pro,
                carb      = carb,
                fat       = fat,
                fiber     = fiber,
                sugar     = sugar,
                sodium    = sodium,
                chol      = chol,
                logged_at = datetime.now(timezone.utc),
            )
            db.session.add(log)

        db.session.commit()
        print("✅ Demo user created with 7 days of sample data.")
        print()
        print("   Email:    demo@nutritrack.app")
        print("   Password: Demo1234!")
        print(f"   Logs:     {len(samples)} entries across 7 days")


def cmd_reset():
    """Drop all tables and recreate them (DESTRUCTIVE)."""
    confirm = input("⚠️  This will DELETE all data. Type 'yes' to confirm: ")
    if confirm.strip().lower() != 'yes':
        print("Cancelled.")
        return
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ Database reset. All tables recreated (empty).")


def cmd_stats():
    """Show database statistics."""
    with app.app_context():
        # SQLAlchemy places SQLite inside instance/ relative to App.py
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'nutritrack.db')
        if not os.path.exists(db_path) and \
           'sqlite' in (os.getenv('DATABASE_URL', 'sqlite:///')):
            print("❌ No database found. Run: python Database.py init")
            return

        user_count = User.query.count()
        log_count  = FoodLog.query.count()

        print("══════════════════════════════")
        print("  NutriTrack — Database Stats")
        print("══════════════════════════════")
        print(f"  Users:      {user_count}")
        print(f"  Food logs:  {log_count}")
        print()

        if user_count > 0:
            print("  Recent users:")
            users = User.query.order_by(User.created_at.desc()).limit(5).all()
            for u in users:
                n_logs = FoodLog.query.filter_by(user_id=u.id).count()
                print(f"  • {u.name} ({u.email}) — {n_logs} logs")

        if log_count > 0:
            print()
            print("  Recent logs:")
            logs = FoodLog.query.order_by(FoodLog.logged_at.desc()).limit(5).all()
            for l in logs:
                print(f"  • [{l.date}] {l.name} — {l.cal} kcal ({l.meal_type})")


def cmd_export():
    """Export all data to JSON backup file."""
    with app.app_context():
        users = User.query.all()
        logs  = FoodLog.query.all()

        data = {
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'users': [u.to_dict() for u in users],
            'logs':  [l.to_dict() for l in logs],
        }

        filename = f"nutritrack_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Exported {len(users)} users and {len(logs)} logs → {filename}")


def cmd_list():
    """List all registered users."""
    with app.app_context():
        users = User.query.order_by(User.created_at).all()
        if not users:
            print("No users registered yet.")
            return
        print(f"{'ID':<6} {'Name':<20} {'Email':<30} {'Logs':<6} {'Joined'}")
        print("─" * 80)
        for u in users:
            n_logs = FoodLog.query.filter_by(user_id=u.id).count()
            joined = u.created_at.strftime('%Y-%m-%d')
            print(f"{u.id:<6} {u.name:<20} {u.email:<30} {n_logs:<6} {joined}")


# ══════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════

COMMANDS = {
    'init':   (cmd_init,   'Create all database tables'),
    'seed':   (cmd_seed,   'Add demo user with sample data'),
    'reset':  (cmd_reset,  'Drop and recreate all tables (DESTRUCTIVE)'),
    'stats':  (cmd_stats,  'Show user and log counts'),
    'export': (cmd_export, 'Export all data to JSON'),
    'list':   (cmd_list,   'List all registered users'),
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("NutriTrack Database Manager")
        print()
        print("Usage:  python Database.py <command>")
        print()
        print("Commands:")
        for cmd, (_, desc) in COMMANDS.items():
            print(f"  {cmd:<10} {desc}")
        sys.exit(1)

    COMMANDS[sys.argv[1]][0]()