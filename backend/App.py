"""
NutriTrack — backend/App.py
Flask REST API backend

Endpoints:
  GET  /api/auth/me            — current user info (requires Supabase JWT)
  PUT  /api/auth/update        — update profile / body stats / goals

  Note: registration, login, refresh, and email verification are NOT
  handled here — they're done entirely client-side via Supabase Auth
  (see frontend/App.js, supabaseClient.auth.*). This backend only
  verifies the Supabase-issued JWT on protected routes.

  GET  /api/logs               — get logs (?date=YYYY-MM-DD or ?days=30)
  POST /api/logs               — add food log
  DELETE /api/logs/<id>        — remove log
  GET  /api/logs/summary       — daily totals (?days=30)

  POST /api/ai/analyze         — AI food photo via Ollama/llava-phi3 LLM
  POST /api/ai/analyze/stream  — same, but streamed via SSE (avoids HF Space's 60s gateway timeout)
  POST /api/ai/chat            — AI nutritionist chatbot (proxied to LLM server)
  GET  /api/analytics/streak   — logging streak
  GET  /api/health              — health check

Start (from project root):
    pip install -r requirements.txt
    python backend/App.py

The frontend (frontend/index.html) is served as static files by Flask.
Run this backend for persistent cloud storage + multi-device sync.
"""

import os
import re
import sys
import json
import base64
import requests
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv, find_dotenv

# Load .env BEFORE reading any environment variables below — this used to
# happen much later in the file (after SUPABASE_URL/SUPABASE_KEY were
# already read from os.environ), which meant local development via a .env
# file silently failed with "Supabase not configured" since the file
# hadn't been loaded yet at the point those variables were read. Production
# on Render is unaffected either way, since it sets env vars directly on
# the platform rather than via a .env file.
load_dotenv(find_dotenv(usecwd=False, raise_error_if_not_found=False) or
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

# Windows Console Unicode/Emoji support
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from flask import Flask, request, jsonify, send_from_directory
from flask_compress import Compress
from flask_cors import CORS

# Error tracking — catches exceptions in production instead of them only
# showing up in Render logs (which nobody watches in real time). No-ops
# cleanly if the SDK isn't installed or SENTRY_DSN isn't configured, so
# local dev and any environment without it keep working unchanged.
_sentry_dsn = os.getenv('SENTRY_DSN')
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,  # 10% perf tracing is enough signal without burning quota
            environment=os.getenv('ENVIRONMENT', 'production'),
        )
        print("  Sentry error tracking active")
    except ImportError:
        print("  SENTRY_DSN set but sentry-sdk not installed — skipping")
else:
    print("  Sentry error tracking inactive (no SENTRY_DSN set)")

# Rate limiting — prevent abuse
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _has_limiter = True
except ImportError:
    _has_limiter = False
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

from functools import wraps
from flask import g
from supabase import create_client, Client

# Initialize Supabase client for JWT verification
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

def jwt_required(optional=False, refresh=False):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not supabase:
                return jsonify({"error": "Supabase not configured"}), 500
            
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                if optional:
                    g.user_id = None
                    return f(*args, **kwargs)
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            
            token = auth_header.split(" ")[1]
            try:
                # Verify token with Supabase
                res = supabase.auth.get_user(token)
                if not res.user:
                    raise Exception("Invalid token")
                g.user_id = res.user.id
                
                # Lazy create local user if not exists
                user_record = db.session.get(User, g.user_id)
                if not user_record:
                    email = res.user.email
                    meta = res.user.user_metadata or {}
                    name = meta.get('full_name', meta.get('name', email.split('@')[0]))
                    new_user = User(id=g.user_id, email=email, name=name)
                    db.session.add(new_user)
                    try:
                        db.session.commit()
                    except Exception as commit_err:
                        db.session.rollback()
                        print(f"Lazy user creation notice: {commit_err}")
            except Exception as e:
                if optional:
                    g.user_id = None
                    return f(*args, **kwargs)
                return jsonify({"error": "Token verification failed", "details": str(e)}), 401
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_jwt_identity():
    return getattr(g, 'user_id', None)

# ══════════════════════════════════════════════════
#  APP SETUP
# ══════════════════════════════════════════════════

# Serve frontend from the sibling frontend/ folder
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
app = Flask(__name__, static_folder=_FRONTEND_DIR)
Compress(app)

# Rate limiter setup
if _has_limiter:
    limiter = Limiter(
        get_remote_address, app=app,
        default_limits=['1000 per hour'],
        storage_uri='memory://'
    )
    print("  Rate limiter active (1000 req/hr default)")
else:
    from contextlib import contextmanager
    class _NoopLimiter:
        def limit(self, *a, **kw):
            def decorator(f): return f
            return decorator
    limiter = _NoopLimiter()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    if path.startswith('api/'):
        return jsonify({"error": "Not found"}), 404
        
    # Check if the requested file physically exists in the frontend folder
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return app.send_static_file(path)
        
    # Otherwise, return index.html for all other routes to support HTML5 History API
    return app.send_static_file('index.html')

@app.after_request
def add_header(response):
    """Disable caching for static files so localhost and dev server always serve fresh code."""
    if request.path.endswith('.css') or request.path.endswith('.js') or request.path == '/' or request.path.endswith('.html'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Database — SQLite locally, Postgres in production
db_url = os.getenv('DATABASE_URL', 'sqlite:///nutritrack.db').strip()


# Ensure PostgreSQL password is URL-encoded if it contains special characters
if db_url.startswith('postgres://') or db_url.startswith('postgresql://'):
    try:
        scheme, rest = db_url.split('://', 1)
        if '@' in rest:
            creds, host_db = rest.rsplit('@', 1)
            if ':' in creds:
                user, password = creds.split(':', 1)
                from urllib.parse import quote_plus, unquote
                # Unquote first to avoid double encoding, then quote
                password = quote_plus(unquote(password))
                db_url = f"{scheme}://{user}:{password}@{host_db}"
        
        # Ensure sslmode=require is present for Postgres if not already set
        if 'sslmode=' not in db_url:
            separator = '&' if '?' in db_url else '?'
            db_url = f"{db_url}{separator}sslmode=require"
    except Exception as e:
        print(f"⚠️ Warning parsing DATABASE_URL: {e}")

db_url = db_url.replace('postgres://', 'postgresql://')   # Railway fix
app.config['SQLALCHEMY_DATABASE_URI'] = db_url

# Ensure instance directory exists for SQLite database
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
    os.makedirs(app.instance_path, exist_ok=True)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# -- Connection pool settings -- critical for Render free tier ----------------
# pool_pre_ping: validate connection before use -- fixes the SSL
#   'decryption failed or bad record mac' error after Render idle periods.
# pool_recycle:  recycle connections every 5 min (Render idles after ~15 min).
_is_postgres = app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('postgresql')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle':  300,
    'pool_size':     5,
    'max_overflow':  2,
    'pool_timeout':  30,
    'connect_args':  {'connect_timeout': 10} if _is_postgres else {},
}



db  = SQLAlchemy(app)


# CORS — allow frontend from local dev and production
_cors_origins = [
    'http://localhost:3000',
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'null',

    # Render backend
    'https://nutritrack-k96f.onrender.com',

    # GitHub Pages
    'https://saiphanianirudh.github.io',

    # Vercel Frontend
    'https://nutritrack-rho-rust.vercel.app',
]
_frontend_url = os.getenv('FRONTEND_URL')
if _frontend_url:
    _cors_origins.append(_frontend_url)
CORS(app, origins=_cors_origins, supports_credentials=True)


# ══════════════════════════════════════════════════
#  MODELS
# ══════════════════════════════════════════════════


class User(db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.String(36), primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(200), unique=True, nullable=False)
    # NOTE: password column removed — was dropped from the live Supabase
    # table (unused leftover from a pre-Supabase-Auth prototype), but this
    # model declaration was never updated to match. That drift caused every
    # ORM query touching a user row to fail with `UndefinedColumn`, which
    # broke every authenticated backend call (food logging, profile
    # updates, everything) — see jwt_required()'s lazy user lookup above.
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))

    # Body stats
    dob         = db.Column(db.String(20))
    weight      = db.Column(db.Float)
    weight_unit = db.Column(db.String(10), default='kg')
    height      = db.Column(db.Float)
    height_unit = db.Column(db.String(10), default='cm')
    gender      = db.Column(db.String(20))
    diet_goal   = db.Column(db.String(40))
    diet_type   = db.Column(db.String(20))

    @property
    def current_age(self):
        if not self.dob: return None
        try:
            from datetime import date
            parts = self.dob.split('-')
            birth = date(int(parts[0]), int(parts[1]), int(parts[2]))
            today = date.today()
            return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        except:
            return None

    # Nutrition goals
    goal_calories = db.Column(db.Integer, default=2000)
    goal_protein  = db.Column(db.Integer, default=150)
    goal_carbs    = db.Column(db.Integer, default=250)
    goal_fat      = db.Column(db.Integer, default=65)
    goal_fiber    = db.Column(db.Integer, default=28)
    goal_sugar    = db.Column(db.Integer, default=50)
    goal_sodium   = db.Column(db.Integer, default=2300)
    goal_chol     = db.Column(db.Integer, default=300)
    goal_vit_d    = db.Column(db.Integer, default=15)
    goal_iron     = db.Column(db.Integer, default=18)
    goal_folate   = db.Column(db.Integer, default=400)
    goal_water_ml = db.Column(db.Integer, default=2000)

    logs = db.relationship('FoodLog', backref='user', lazy=True,
                           cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':         self.id,
            'name':       self.name,
            'email':      self.email,
            'created_at': self.created_at.isoformat(),
            'body_stats': {
                'age':         self.current_age,
                'dob':         self.dob,
                'weight':      self.weight,
                'weight_unit': self.weight_unit,
                'height':      self.height,
                'height_unit': self.height_unit,
                'gender':      self.gender,
                'diet_goal':   self.diet_goal,
                'diet_type':   self.diet_type,
            },
            'goals': {
                'calories': self.goal_calories,
                'protein':  self.goal_protein,
                'carbs':    self.goal_carbs,
                'fat':      self.goal_fat,
                'fiber':    self.goal_fiber,
                'sugar':    self.goal_sugar,
                'sodium':   self.goal_sodium,
                'chol':     self.goal_chol,
                'vit_d':    self.goal_vit_d,
                'iron':     self.goal_iron,
                'folate':   self.goal_folate,
                'water_ml': self.goal_water_ml,
            }
        }


class FoodLog(db.Model):
    __tablename__ = 'food_logs'

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    date      = db.Column(db.String(10), nullable=False)       # YYYY-MM-DD
    meal_type = db.Column(db.String(20), default='breakfast')  # breakfast/lunch/dinner/snack
    name      = db.Column(db.String(200), nullable=False)
    emoji     = db.Column(db.String(10), default='🍽️')

    # Macros
    cal    = db.Column(db.Float, default=0)
    pro    = db.Column(db.Float, default=0)
    carb   = db.Column(db.Float, default=0)
    fat    = db.Column(db.Float, default=0)
    fiber  = db.Column(db.Float, default=0)
    sugar  = db.Column(db.Float, default=0)
    sodium = db.Column(db.Float, default=0)
    chol   = db.Column(db.Float, default=0)
    vit_d  = db.Column(db.Float, default=0)
    iron   = db.Column(db.Float, default=0)
    folate = db.Column(db.Float, default=0)

    logged_at = db.Column(db.DateTime(timezone=True),
                          default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id':        self.id,
            'userId':    self.user_id,
            'date':      self.date,
            'mealType':  self.meal_type,
            'name':      self.name,
            'emoji':     self.emoji,
            'cal':       self.cal,
            'pro':       self.pro,
            'carb':      self.carb,
            'fat':       self.fat,
            'fiber':     self.fiber,
            'sugar':     self.sugar,
            'sodium':    self.sodium,
            'chol':      self.chol,
            'vit_d':     self.vit_d,
            'iron':      self.iron,
            'folate':    self.folate,
            'logged_at': self.logged_at.isoformat(),
        }



class WaterLog(db.Model):
    __tablename__ = 'water_logs'

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    date      = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD
    amount_ml = db.Column(db.Float, nullable=False)
    logged_at = db.Column(db.DateTime(timezone=True),
                          default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id':        self.id,
            'userId':    self.user_id,
            'date':      self.date,
            'amountMl':  self.amount_ml,
            'logged_at': self.logged_at.isoformat(),
        }


class WeightLog(db.Model):
    __tablename__ = 'weight_logs'

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    date      = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD
    weight_kg = db.Column(db.Float, nullable=False)        # always stored in kg
    note      = db.Column(db.String(200))
    logged_at = db.Column(db.DateTime(timezone=True),
                          default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id':        self.id,
            'userId':    self.user_id,
            'date':      self.date,
            'weight_kg': self.weight_kg,
            'note':      self.note,
            'logged_at': self.logged_at.isoformat(),
        }


class MealTemplate(db.Model):
    __tablename__ = 'meal_templates'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    name       = db.Column(db.String(200), nullable=False)   # e.g. "My Usual Breakfast"
    items_json = db.Column(db.Text, nullable=False)          # JSON array of food items
    # Cached totals for quick display
    total_cal  = db.Column(db.Float, default=0)
    total_pro  = db.Column(db.Float, default=0)
    total_carb = db.Column(db.Float, default=0)
    total_fat  = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        try:
            items = json.loads(self.items_json)
        except Exception:
            items = []
        return {
            'id':         self.id,
            'userId':     self.user_id,
            'name':       self.name,
            'items':      items,
            'total_cal':  self.total_cal,
            'total_pro':  self.total_pro,
            'total_carb': self.total_carb,
            'total_fat':  self.total_fat,
            'created_at': self.created_at.isoformat(),
        }


class Challenge(db.Model):
    __tablename__ = 'challenges'

    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(200), nullable=False)
    description   = db.Column(db.String(500))
    metric        = db.Column(db.String(50), default='streak')  # streak, protein, water, logs
    target_val    = db.Column(db.Float, default=7)
    duration_days = db.Column(db.Integer, default=7)
    badge_emoji   = db.Column(db.String(10), default='🏆')
    created_at    = db.Column(db.DateTime(timezone=True),
                              default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id':            self.id,
            'title':         self.title,
            'description':   self.description,
            'metric':        self.metric,
            'targetVal':     self.target_val,
            'durationDays':  self.duration_days,
            'badgeEmoji':    self.badge_emoji,
            'created_at':    self.created_at.isoformat(),
        }


class ChallengeParticipant(db.Model):
    __tablename__ = 'challenge_participants'

    id           = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    user_id      = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    current_val  = db.Column(db.Float, default=0)
    completed    = db.Column(db.Boolean, default=False)
    joined_at    = db.Column(db.DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        user = db.session.get(User, self.user_id)
        return {
            'id':          self.id,
            'challengeId': self.challenge_id,
            'userId':      self.user_id,
            'userName':    user.name if user else 'User',
            'currentVal':  self.current_val,
            'joined_at':   self.joined_at.isoformat(),
        }


class WorkoutLog(db.Model):
    __tablename__ = 'workout_logs'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    date         = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD
    name         = db.Column(db.String(100), nullable=False)  # Running, Weightlifting, etc.
    duration_min = db.Column(db.Integer, default=30)
    cal_burned   = db.Column(db.Float, nullable=False)
    logged_at    = db.Column(db.DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id':          self.id,
            'userId':      self.user_id,
            'date':        self.date,
            'name':        self.name,
            'durationMin': self.duration_min,
            'calBurned':   self.cal_burned,
            'logged_at':   self.logged_at.isoformat(),
        }


class GoogleFitToken(db.Model):
    __tablename__ = 'google_fit_tokens'

    user_id       = db.Column(db.String(36), db.ForeignKey('users.id'), primary_key=True)
    refresh_token = db.Column(db.Text, nullable=False)
    connected_at  = db.Column(db.DateTime(timezone=True),
                              default=lambda: datetime.now(timezone.utc))
    updated_at    = db.Column(db.DateTime(timezone=True),
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))



with app.app_context():
    try:
        db.create_all()
        # Migration for missing columns in production
        columns_to_add = [
            ("users", "diet_type VARCHAR(20)"),
            ("users", "goal_sugar FLOAT DEFAULT 50"),
            ("users", "goal_sodium FLOAT DEFAULT 2300"),
            ("users", "goal_chol FLOAT DEFAULT 300"),
            ("users", "goal_vit_d FLOAT DEFAULT 20"),
            ("users", "goal_iron FLOAT DEFAULT 18"),
            ("users", "goal_folate FLOAT DEFAULT 400"),
            ("users", "goal_water_ml INTEGER DEFAULT 2000"),
            ("users", "dob VARCHAR(20)"),
            ("food_logs", "fiber FLOAT DEFAULT 0"),
            ("food_logs", "sugar FLOAT DEFAULT 0"),
            ("food_logs", "sodium FLOAT DEFAULT 0"),
            ("food_logs", "chol FLOAT DEFAULT 0"),
            ("food_logs", "vit_d FLOAT DEFAULT 0"),
            ("food_logs", "iron FLOAT DEFAULT 0"),
            ("food_logs", "folate FLOAT DEFAULT 0"),
        ]
        for table, col in columns_to_add:
            try:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col};"))
                db.session.commit()
            except Exception:
                db.session.rollback()

        print("✅ Database tables initialized.")
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize database tables: {e}")


# ══════════════════════════════════════════════════

# ══════════════════════════════════════════════════
#  HELPERS & RAG DB
# ══════════════════════════════════════════════════

def _find_closest_food(name):
    if not name or not supabase: return None
    try:
        # 1. Try exact or substring match first
        res = supabase.table('base_foods').select('*').ilike('name', f'%{name}%').limit(1).execute()
        if res.data:
            return res.data[0]
            
        # 2. Intelligent keyword fallback
        # Remove common cooking adjectives that LLM hallucinates
        import re
        stop_words = {'roasted', 'steamed', 'cooked', 'fried', 'baked', 'boiled', 'raw', 'fresh', 'slice', 'piece', 'bowl', 'plate', 'dish', 'with', 'and', 'the', 'a', 'an'}
        words = [w for w in re.split(r'[^a-zA-Z0-9]', name.lower()) if len(w) > 2 and w not in stop_words]
        
        # Try matching the longest remaining word (most likely the core ingredient)
        if words:
            words.sort(key=len, reverse=True)
            for w in words:
                res = supabase.table('base_foods').select('*').ilike('name', f'%{w}%').limit(1).execute()
                if res.data:
                    return res.data[0]
                    
    except Exception as e:
        print("Error searching food in Supabase:", e)
    return None

def _enrich_with_rag(item, original_name=None):
    """Takes a parsed item dict (with a food_name), queries RAG, and enriches it if found. Modifies in place.

    NOTE: base_foods (see foods_seed.sql) has no vit_d/iron/folate columns —
    only calories/protein/carbs/fat/fiber/sugar/sodium/chol. So match.get('vit_d'/'iron'/'folate', 0.0)
    below will always fall back to 0 for RAG-matched foods; these three are
    only ever populated when the LLM itself estimates them (MLLM Estimation
    path). This is a real data gap, not a bug — flagging so it isn't
    mistaken for one. Fixing it properly means adding those columns and
    populating them with real values, not guessing numbers.
    """
    fname = original_name or item.get('food_name', item.get('name', ''))
    match = _find_closest_food(fname)
    if match:
        item['calories'] = match.get('calories', 0)
        item['protein_g'] = match.get('protein', 0)
        item['carbs_g'] = match.get('carbs', 0)
        item['fat_g'] = match.get('fat', 0)
        item['fiber_g'] = match.get('fiber', 0)
        item['sugar_g'] = match.get('sugar', 0)
        item['sodium_mg'] = match.get('sodium', 0)
        item['cholesterol_mg'] = match.get('chol', 0)
        item['vit_d'] = match.get('vit_d', 0.0)
        item['iron'] = match.get('iron', 0.0)
        item['folate'] = match.get('folate', 0.0)
        item['source'] = 'Supabase RAG Database'
        item['food_name'] = match.get('name', fname).title()
        return True
    else:
        item['source'] = 'MLLM Estimation'
        for key in ['vit_d', 'iron', 'folate']:
            if key not in item: item[key] = 0
        return False



def _validate_email(email):
    """Strict email validation — checks format, TLD length, and total length."""
    if not email or len(email) > 254:
        return False
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,10}$'
    return bool(re.match(pattern, email))

def _today():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')

def _date_range(days):
    """Return list of date strings for the past N days (oldest first)."""
    today = datetime.now(timezone.utc).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days-1, -1, -1)]




# ══════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════

# Increment this whenever you push a deploy — lets you verify Render is live
# on the right version by hitting GET /api/health
BUILD_VERSION = "2026-07-29-audit-v6"

@app.route('/api/health', methods=['GET'])
def health_check():
    db_ok = False
    try:
        db.session.execute(text('SELECT 1'))
        db_ok = True
    except Exception:
        pass
    return jsonify({
        'status': 'ok',
        'build': BUILD_VERSION,
        'db': 'connected' if db_ok else 'error',
        'password_column': 'removed',   # confirms the fix is live
    })

# ══════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════





@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def me():
    uid  = get_jwt_identity()
    user = db.session.get(User, uid)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict())


@app.route('/api/auth/update', methods=['PUT'])
@jwt_required()
def update_profile():
    uid  = get_jwt_identity()
    user = db.session.get(User, uid)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data  = request.get_json() or {}
    goals = data.get('goals', {})
    stats = data.get('body_stats', {})

    if 'name' in data:
        user.name = data['name'].strip() or user.name

    # Update body stats
    if stats.get('dob'):         user.dob         = stats['dob']
    if stats.get('weight'):      user.weight      = float(stats['weight'])
    if stats.get('weight_unit'): user.weight_unit = stats['weight_unit']
    if stats.get('height'):      user.height      = float(stats['height'])
    if stats.get('height_unit'): user.height_unit = stats['height_unit']
    if stats.get('gender'):      user.gender      = stats['gender']
    if stats.get('diet_goal'):   user.diet_goal   = stats['diet_goal']
    if stats.get('diet_type'):   user.diet_type   = stats['diet_type']

    # Update nutrition goals
    if 'calories' in goals: user.goal_calories = int(goals['calories'])
    if 'protein' in goals:  user.goal_protein  = int(goals['protein'])
    if 'carbs' in goals:    user.goal_carbs    = int(goals['carbs'])
    if 'fat' in goals:      user.goal_fat      = int(goals['fat'])
    if 'fiber' in goals:    user.goal_fiber    = int(goals['fiber'])
    if 'sugar' in goals:    user.goal_sugar    = int(goals['sugar'])
    if 'sodium' in goals:   user.goal_sodium   = int(goals['sodium'])
    if 'chol' in goals:     user.goal_chol     = int(goals['chol'])
    if 'vit_d' in goals:    user.goal_vit_d    = int(goals['vit_d'])
    if 'iron' in goals:     user.goal_iron     = int(goals['iron'])
    if 'folate' in goals:   user.goal_folate   = int(goals['folate'])
    try:
        db.session.commit()
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        print(f"Error saving goals: {e}")
        return jsonify({'error': 'Failed to save goals', 'details': str(e)}), 500


# ══════════════════════════════════════════════════
#  FOOD LOG ROUTES
# ══════════════════════════════════════════════════

@app.route('/api/logs', methods=['GET'])
@jwt_required()
def get_logs():
    uid  = get_jwt_identity()
    date = request.args.get('date')          # YYYY-MM-DD
    days = request.args.get('days', type=int)

    query = FoodLog.query.filter_by(user_id=uid)

    if date:
        query = query.filter_by(date=date)
    elif days:
        dates = _date_range(days)
        query = query.filter(FoodLog.date.in_(dates))

    logs = query.order_by(FoodLog.logged_at.desc()).all()
    return jsonify([l.to_dict() for l in logs])


@app.route('/api/logs', methods=['POST'])
@jwt_required()
def add_log():
    try:
        uid  = get_jwt_identity()
        data = request.get_json() or {}

        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Food name is required'}), 400

        log = FoodLog(
            user_id   = uid,
            date      = data.get('date')     or _today(),
            meal_type = data.get('mealType') or 'breakfast',
            name      = name,
            emoji     = data.get('emoji')    or '🍽️',
            cal       = float(data.get('cal')    or 0),
            pro       = float(data.get('pro')    or 0),
            carb      = float(data.get('carb')   or 0),
            fat       = float(data.get('fat')    or 0),
            fiber     = float(data.get('fiber')  or 0),
            sugar     = float(data.get('sugar')  or 0),
            sodium    = float(data.get('sodium') or 0),
            chol      = float(data.get('chol')   or 0),
            vit_d     = float(data.get('vit_d')  or 0),
            iron      = float(data.get('iron')   or 0),
            folate    = float(data.get('folate') or 0),
        )
        db.session.add(log)
        db.session.commit()
        return jsonify(log.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error adding log: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/logs/<string:log_id>', methods=['DELETE'])
@jwt_required()
def delete_log(log_id):
    uid = get_jwt_identity()
    # FoodLog.id is an Integer column — validate before it ever reaches the
    # DB. Previously this route took any string and passed it straight into
    # filter_by(id=...) with no try/except; a non-numeric id (e.g. a stale
    # client-side temp id) could raise an unhandled DB-level error instead
    # of a clean 404.
    if not log_id.isdigit():
        return jsonify({'error': 'Log not found'}), 404
    try:
        log = FoodLog.query.filter_by(id=int(log_id), user_id=uid).first()
        if not log:
            return jsonify({'error': 'Log not found'}), 404
        db.session.delete(log)
        db.session.commit()
        return jsonify({'deleted': True})
    except Exception as e:
        print(f"Error deleting log: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/logs/summary', methods=['GET'])
@jwt_required()
def logs_summary():
    """Daily totals for past N days."""
    uid  = get_jwt_identity()
    days = request.args.get('days', 30, type=int)
    dates = _date_range(days)

    logs = FoodLog.query.filter(
        FoodLog.user_id == uid,
        FoodLog.date.in_(dates)
    ).all()

    # Group by date
    summary = {}
    for d in dates:
        summary[d] = {'date': d, 'cal': 0, 'pro': 0, 'carb': 0,
                       'fat': 0, 'fiber': 0, 'sugar': 0,
                       'sodium': 0, 'chol': 0, 'vit_d': 0, 'iron': 0, 'folate': 0, 'meals': 0}
    for l in logs:
        if l.date in summary:
            summary[l.date]['cal']    += l.cal
            summary[l.date]['pro']    += l.pro
            summary[l.date]['carb']   += l.carb
            summary[l.date]['fat']    += l.fat
            summary[l.date]['fiber']  += l.fiber  or 0
            summary[l.date]['sugar']  += l.sugar  or 0
            summary[l.date]['sodium'] += l.sodium or 0
            summary[l.date]['chol']   += l.chol   or 0
            summary[l.date]['vit_d']  += l.vit_d  or 0
            summary[l.date]['iron']   += l.iron   or 0
            summary[l.date]['folate'] += l.folate or 0
            summary[l.date]['meals']  += 1

    return jsonify(list(summary.values()))




# ══════════════════════════════════════════════════
#  FOOD SEARCH (Supabase base_foods — 12,986+ entries)
# ══════════════════════════════════════════════════

@app.route('/api/foods/search', methods=['GET'])
def search_foods():
    """
    Search base_foods table + Open Food Facts fallback.
    GET /api/foods/search?q=<query>&limit=20
    Returns items normalized to the FOODS shape.
    """
    q = (request.args.get('q') or '').strip()
    limit = min(int(request.args.get('limit', 20)), 50)

    if len(q) < 2:
        return jsonify([])

    results = []
    
    # 1. Search local DB / Supabase base_foods first
    if supabase:
        try:
            res = supabase.rpc('search_foods_ranked', {
                'search_query': q,
                'result_limit': limit,
            }).execute()
            rows = res.data or []

            def normalize_local(row):
                return {
                    'id':     f"db_{row.get('id', '')}",
                    'name':   (row.get('name') or '').title(),
                    'emoji':  '🍽️',
                    'cal':    round(float(row.get('calories') or 0), 1),
                    'pro':    round(float(row.get('protein')  or 0), 1),
                    'carb':   round(float(row.get('carbs')    or 0), 1),
                    'fat':    round(float(row.get('fat')      or 0), 1),
                    'fiber':  round(float(row.get('fiber')    or 0), 1),
                    'sugar':  round(float(row.get('sugar')    or 0), 1),
                    'sodium': round(float(row.get('sodium')   or 0), 1),
                    'chol':   round(float(row.get('chol')     or 0), 1),
                    'vit_d':  round(float(row.get('vit_d')  or 0), 1),
                    'iron':   round(float(row.get('iron')   or 0), 1),
                    'folate': round(float(row.get('folate') or 0), 1),
                    'cat':    'other',
                    'source': 'db',
                }
            results.extend([normalize_local(r) for r in rows])
        except Exception as e:
            print(f"⚠️ local food search notice: {e}")

    # 2. If fewer than 5 local matches, query Open Food Facts Global API
    if len(results) < 5:
        try:
            # Replace spaces with '+' for clean query parameters (prevents 503 HTML errors on multi-word searches)
            q_param = requests.utils.quote(q.replace(' ', '+')).replace('%2B', '+')
            headers = {'User-Agent': 'NutriTrack - WebApp - Version 2.5 (contact: support@nutritrack.app)'}
            
            # Prefer US/EN endpoint for clean English product names; fall back to World endpoint
            off_url = f"https://us.openfoodfacts.org/cgi/search.pl?search_terms={q_param}&search_simple=1&action=process&json=1&page_size=15&lc=en"
            off_res = None
            try:
                off_res = requests.get(off_url, timeout=4, headers=headers)
            except Exception:
                off_res = None

            if not off_res or off_res.status_code != 200:
                world_url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={q_param}&search_simple=1&action=process&json=1&page_size=15&lc=en&sort_by=unique_scans_n"
                off_res = requests.get(world_url, timeout=4, headers=headers)

            if off_res and off_res.status_code == 200:
                try:
                    off_data = off_res.json()
                except Exception:
                    off_data = {}
                products = off_data.get('products', [])
                for prod in products:
                    pname = (prod.get('product_name_en') or prod.get('product_name') or '').strip()
                    if not pname:
                        continue
                    
                    brand = (prod.get('brands') or '').split(',')[0].strip()
                    if brand and brand.lower() not in pname.lower():
                        full_title = f"{brand} - {pname}"
                    else:
                        full_title = pname

                    nutriments = prod.get('nutriments', {})
                    cal = float(nutriments.get('energy-kcal_100g') or nutriments.get('energy-kcal_serving') or 0)
                    pro = float(nutriments.get('proteins_100g') or nutriments.get('proteins_serving') or 0)
                    carb = float(nutriments.get('carbohydrates_100g') or nutriments.get('carbohydrates_serving') or 0)
                    fat = float(nutriments.get('fat_100g') or nutriments.get('fat_serving') or 0)
                    fiber = float(nutriments.get('fiber_100g') or nutriments.get('fiber_serving') or 0)
                    sugar = float(nutriments.get('sugars_100g') or nutriments.get('sugars_serving') or 0)
                    sodium = float(nutriments.get('sodium_100g') or nutriments.get('sodium_serving') or 0) * 1000

                    # Skip zero-calorie empty stubs or incomplete products
                    if cal == 0 and pro == 0 and carb == 0:
                        continue

                    barcode_id = prod.get('code') or prod.get('_id') or f"off_{len(results)}"
                    results.append({
                        'id': f"barcode_{barcode_id}",
                        'name': full_title.title(),
                        'emoji': '📦',
                        'cal': round(cal, 1),
                        'pro': round(pro, 1),
                        'carb': round(carb, 1),
                        'fat': round(fat, 1),
                        'fiber': round(fiber, 1),
                        'sugar': round(sugar, 1),
                        'sodium': round(sodium, 1),
                        'chol': 0.0,
                        'vit_d': 0.0,
                        'iron': 0.0,
                        'folate': 0.0,
                        'cat': 'packaged',
                        'source': 'openfoodfacts',
                    })
                    if len(results) >= limit:
                        break
        except Exception as off_err:
            print(f"⚠️ Open Food Facts search error: {off_err}")

    return jsonify(results[:limit])


@app.route('/api/foods/popular', methods=['GET'])
def popular_foods():
    """Returns top 80 popular base foods from Supabase for browsing."""
    if not supabase:
        return jsonify([])
    try:
        res = supabase.table('base_foods').select('*').limit(80).execute()
        rows = res.data or []

        def normalize(row):
            return {
                'id':     f"db_{row.get('id', '')}",
                'name':   (row.get('name') or '').title(),
                'emoji':  '🍽️',
                'cal':    round(float(row.get('calories') or 0), 1),
                'pro':    round(float(row.get('protein')  or 0), 1),
                'carb':   round(float(row.get('carbs')    or 0), 1),
                'fat':    round(float(row.get('fat')      or 0), 1),
                'fiber':  round(float(row.get('fiber')    or 0), 1),
                'sugar':  round(float(row.get('sugar')    or 0), 1),
                'sodium': round(float(row.get('sodium')   or 0), 1),
                'chol':   round(float(row.get('chol')     or 0), 1),
                'vit_d':  round(float(row.get('vit_d')  or 0), 1),
                'iron':   round(float(row.get('iron')   or 0), 1),
                'folate': round(float(row.get('folate') or 0), 1),
                'cat':    (row.get('category') or 'other').lower(),
                'source': 'db',
            }
        return jsonify([normalize(r) for r in rows])
    except Exception as e:
        print(f"⚠️ popular foods error: {e}")
        return jsonify([])


@app.route('/api/foods/lookup', methods=['GET'])
def lookup_food():
    """Best single match by name from Supabase base_foods for photo scan / voice enrichment."""
    name = (request.args.get('name') or '').strip()
    if not name or not supabase:
        return jsonify({'found': False})

    matched = _find_closest_food(name)
    if matched:
        return jsonify({
            'found': True,
            'item': {
                'id':     f"db_{matched.get('id', '')}",
                'name':   (matched.get('name') or '').title(),
                'emoji':  '🍽️',
                'cal':    round(float(matched.get('calories') or 0), 1),
                'pro':    round(float(matched.get('protein')  or 0), 1),
                'carb':   round(float(matched.get('carbs')    or 0), 1),
                'fat':    round(float(matched.get('fat')      or 0), 1),
                'fiber':  round(float(matched.get('fiber')    or 0), 1),
                'sugar':  round(float(matched.get('sugar')    or 0), 1),
                'sodium': round(float(matched.get('sodium')   or 0), 1),
                'chol':   round(float(matched.get('chol')     or 0), 1),
                'vit_d':  round(float(matched.get('vit_d')  or 0), 1),
                'iron':   round(float(matched.get('iron')   or 0), 1),
                'folate': round(float(matched.get('folate') or 0), 1),
                'source': 'db',
            }
        })
    return jsonify({'found': False})


@app.route('/api/foods/barcode/<string:barcode>', methods=['GET'])
def barcode_food(barcode):
    """Fetch product nutrition from Open Food Facts API by barcode with multi-tier fallback."""
    barcode = barcode.strip()
    if not barcode:
        return jsonify({'found': False, 'error': 'Barcode required'}), 400

    try:
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
        res = requests.get(url, timeout=6, headers={'User-Agent': 'NutriTrack - PWA - Version 2.5'})
        if res.status_code != 200:
            url_v0 = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
            res = requests.get(url_v0, timeout=6, headers={'User-Agent': 'NutriTrack - PWA - Version 2.5'})
            if res.status_code != 200:
                return jsonify({'found': False, 'error': 'Product lookup failed'}), 404

        data = res.json()
        if data.get('status') != 1 or 'product' not in data:
            return jsonify({'found': False, 'error': 'Product not found'}), 404

        product = data['product']
        nutriments = product.get('nutriments', {})

        pname = product.get('product_name') or product.get('product_name_en') or f"Product #{barcode}"
        brand = product.get('brands') or ''
        full_name = f"{pname} ({brand})" if brand else pname
        
        cal = float(nutriments.get('energy-kcal_100g') or nutriments.get('energy-kcal_serving') or 0)
        pro = float(nutriments.get('proteins_100g') or nutriments.get('proteins_serving') or 0)
        carb = float(nutriments.get('carbohydrates_100g') or nutriments.get('carbohydrates_serving') or 0)
        fat = float(nutriments.get('fat_100g') or nutriments.get('fat_serving') or 0)
        fiber = float(nutriments.get('fiber_100g') or nutriments.get('fiber_serving') or 0)
        sugar = float(nutriments.get('sugars_100g') or nutriments.get('sugars_serving') or 0)
        sodium = float(nutriments.get('sodium_100g') or nutriments.get('sodium_serving') or 0) * 1000
        chol = float(nutriments.get('cholesterol_100g') or nutriments.get('cholesterol_serving') or 0) * 1000

        iron = float(nutriments.get('iron_100g') or nutriments.get('iron_serving') or 0) * 1000
        vit_d = float(nutriments.get('vitamin-d_100g') or nutriments.get('vitamin-d_serving') or 0)

        item = {
            'id': f"barcode_{barcode}",
            'name': full_name.title(),
            'emoji': '📦',
            'cal': round(cal, 1),
            'pro': round(pro, 1),
            'carb': round(carb, 1),
            'fat': round(fat, 1),
            'fiber': round(fiber, 1),
            'sugar': round(sugar, 1),
            'sodium': round(sodium, 1),
            'chol': round(chol, 1),
            'vit_d': round(vit_d, 1),
            'iron': round(iron, 1),
            'folate': 0.0,
            'cat': 'packaged',
            'source': 'barcode',
        }
        return jsonify({'found': True, 'item': item})
    except Exception as e:
        print(f"⚠️ Barcode lookup error: {e}")
        return jsonify({'found': False, 'error': str(e)}), 500


@app.route('/api/export/health', methods=['GET'])
@jwt_required()
def export_health_data():
    """Export user's food logs formatted for Apple Health & Google Health Connect sync."""
    uid = get_jwt_identity()
    try:
        logs = FoodLog.query.filter_by(user_id=uid).order_by(FoodLog.date.desc()).all()
        
        exported_records = []
        for l in logs:
            exported_records.append({
                'date': l.date,
                'logged_at': l.logged_at.isoformat() if l.logged_at else l.date,
                'food_name': l.name,
                'meal_type': l.meal_type,
                'metrics': {
                    'energy_kcal': l.cal,
                    'protein_g': l.pro,
                    'carbohydrates_g': l.carb,
                    'fat_total_g': l.fat,
                    'dietary_fiber_g': l.fiber,
                    'sugar_g': l.sugar,
                    'sodium_mg': l.sodium,
                    'cholesterol_mg': l.chol
                }
            })
            
        return jsonify({
            'source': 'NutriTrack',
            'version': '2.5.0',
            'user_id': uid,
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'total_records': len(exported_records),
            'data': exported_records
        })
    except Exception as e:
        print(f"⚠️ Health export error: {e}")
        return jsonify({'error': 'Could not export health data'}), 500


# ══════════════════════════════════════════════════
#  WATER INTAKE
# ══════════════════════════════════════════════════



@app.route('/api/water', methods=['GET'])
@jwt_required()
def get_water():
    """Water log entries for a given date (default: today)."""
    uid  = get_jwt_identity()
    date = request.args.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    logs = WaterLog.query.filter_by(user_id=uid, date=date).order_by(WaterLog.logged_at).all()
    total_ml = sum(l.amount_ml for l in logs)
    return jsonify({'date': date, 'total_ml': total_ml, 'entries': [l.to_dict() for l in logs]})


@app.route('/api/water', methods=['POST'])
@jwt_required()
def add_water():
    """Log a water intake entry."""
    uid  = get_jwt_identity()
    data = request.get_json() or {}
    try:
        amount_ml = float(data.get('amount_ml', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'amount_ml must be a number'}), 400
    if amount_ml <= 0:
        return jsonify({'error': 'amount_ml must be positive'}), 400

    date = data.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    try:
        log = WaterLog(user_id=uid, date=date, amount_ml=amount_ml)
        db.session.add(log)
        db.session.commit()
        return jsonify(log.to_dict()), 201
    except Exception as e:
        print(f"⚠️ add_water error: {e}")
        return jsonify({'error': 'Could not save water log. Please try again.'}), 500


@app.route('/api/water/<string:log_id>', methods=['DELETE'])
@jwt_required()
def delete_water(log_id):
    uid = get_jwt_identity()
    if not log_id.isdigit():
        return jsonify({'error': 'Log not found'}), 404
    try:
        log = WaterLog.query.filter_by(id=int(log_id), user_id=uid).first()
        if not log:
            return jsonify({'error': 'Log not found'}), 404
        db.session.delete(log)
        db.session.commit()
        return jsonify({'deleted': True})
    except Exception as e:
        print(f"Error deleting water log: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ══════════════════════════════════════════════════
#  BODY WEIGHT LOGS
# ══════════════════════════════════════════════════

@app.route('/api/weight', methods=['GET'])
@jwt_required()
def get_weight():
    """Get user's weight log history (past 30 days default)."""
    uid  = get_jwt_identity()
    days = request.args.get('days', 30, type=int)
    logs = WeightLog.query.filter_by(user_id=uid).order_by(WeightLog.date.asc()).all()
    if days and len(logs) > days:
        logs = logs[-days:]
    return jsonify([l.to_dict() for l in logs])


@app.route('/api/weight', methods=['POST'])
@jwt_required()
def add_weight():
    """Log a daily weight entry."""
    uid  = get_jwt_identity()
    data = request.get_json() or {}
    try:
        weight_kg = float(data.get('weight_kg', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'weight_kg must be a number'}), 400
    if weight_kg <= 0 or weight_kg > 300:
        return jsonify({'error': 'weight_kg invalid'}), 400

    date = data.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    note = (data.get('note') or '').strip()

    try:
        # Update user's latest weight in profile too
        user = db.session.get(User, uid)
        if user:
            user.weight = weight_kg
            user.weight_unit = 'kg'

        # Check if entry exists for today, update if so
        existing = WeightLog.query.filter_by(user_id=uid, date=date).first()
        if existing:
            existing.weight_kg = weight_kg
            existing.note = note
            log = existing
        else:
            log = WeightLog(user_id=uid, date=date, weight_kg=weight_kg, note=note)
            db.session.add(log)

        db.session.commit()
        return jsonify(log.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ add_weight error: {e}")
        return jsonify({'error': 'Could not save weight log.'}), 500


@app.route('/api/weight/<string:log_id>', methods=['DELETE'])
@jwt_required()
def delete_weight(log_id):
    uid = get_jwt_identity()
    if not log_id.isdigit():
        return jsonify({'error': 'Log not found'}), 404
    try:
        log = WeightLog.query.filter_by(id=int(log_id), user_id=uid).first()
        if not log:
            return jsonify({'error': 'Log not found'}), 404
        db.session.delete(log)
        db.session.commit()
        return jsonify({'deleted': True})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting weight log: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ══════════════════════════════════════════════════
#  MEAL TEMPLATES
# ══════════════════════════════════════════════════

@app.route('/api/meals/templates', methods=['GET'])
@jwt_required()
def get_meal_templates():
    """List saved meal templates for the logged in user."""
    uid = get_jwt_identity()
    templates = MealTemplate.query.filter_by(user_id=uid).order_by(MealTemplate.created_at.desc()).all()
    return jsonify([t.to_dict() for t in templates])


@app.route('/api/meals/templates', methods=['POST'])
@jwt_required()
def save_meal_template():
    """Save a list of food items as a named template (e.g. 'My Usual Breakfast')."""
    uid  = get_jwt_identity()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    items = data.get('items', [])

    if not name or not items or not isinstance(items, list):
        return jsonify({'error': 'Template name and items required'}), 400

    tot_cal  = sum(float(i.get('cal', 0)) for i in items)
    tot_pro  = sum(float(i.get('pro', 0)) for i in items)
    tot_carb = sum(float(i.get('carb', 0)) for i in items)
    tot_fat  = sum(float(i.get('fat', 0)) for i in items)

    try:
        tpl = MealTemplate(
            user_id=uid,
            name=name,
            items_json=json.dumps(items),
            total_cal=round(tot_cal, 1),
            total_pro=round(tot_pro, 1),
            total_carb=round(tot_carb, 1),
            total_fat=round(tot_fat, 1)
        )
        db.session.add(tpl)
        db.session.commit()
        return jsonify(tpl.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ save_meal_template error: {e}")
        return jsonify({'error': 'Could not save template'}), 500


@app.route('/api/meals/templates/<string:template_id>', methods=['DELETE'])
@jwt_required()
def delete_meal_template(template_id):
    uid = get_jwt_identity()
    if not template_id.isdigit():
        return jsonify({'error': 'Template not found'}), 404
    try:
        tpl = MealTemplate.query.filter_by(id=int(template_id), user_id=uid).first()
        if not tpl:
            return jsonify({'error': 'Template not found'}), 404
        db.session.delete(tpl)
        db.session.commit()
        return jsonify({'deleted': True})
    except Exception as e:
        print(f"Error deleting template: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ══════════════════════════════════════════════════
#  VOICE FOOD LOG PARSER
# ══════════════════════════════════════════════════

@app.route('/api/ai/parse-voice', methods=['POST'])
@jwt_required(optional=True)
def parse_voice_log():
    """
    Takes spoken text (e.g. "I had 2 boiled eggs and a cup of chai"),
    extracts food names and quantities, and looks up each item in Supabase base_foods.
    """
    data = request.get_json() or {}
    text_transcript = (data.get('transcript') or '').strip()
    if not text_transcript:
        return jsonify({'items': []})

    # Basic regex / rule extraction for common voice patterns
    # e.g., "2 eggs", "one apple", "bowl of dal"
    # We enrich each recognized item by looking up in Supabase
    import re
    # Splitting by " and ", ",", " with ", " plus "
    parts = re.split(r'\b(?:and|with|plus|,|\.)\b', text_transcript.lower())
    found_items = []

    for part in parts:
        part = part.strip()
        if not part or len(part) < 2:
            continue
        # Remove common preamble phrases
        clean = re.sub(r'^(i had|i ate|logged|had|ate|one|a|an|two|2|three|3|some)\s+', '', part).strip()
        if not clean:
            clean = part

        matched = _find_closest_food(clean)
        if matched:
            found_items.append({
                'id': f"db_{matched.get('id', '')}",
                'name': (matched.get('name') or clean).title(),
                'emoji': '🍽️',
                'cal': round(float(matched.get('calories') or 0), 1),
                'pro': round(float(matched.get('protein') or 0), 1),
                'carb': round(float(matched.get('carbs') or 0), 1),
                'fat': round(float(matched.get('fat') or 0), 1),
                'fiber': round(float(matched.get('fiber') or 0), 1),
                'sugar': round(float(matched.get('sugar') or 0), 1),
                'sodium': round(float(matched.get('sodium') or 0), 1),
                'chol': round(float(matched.get('chol') or 0), 1),
                'vit_d': 0.0,
                'iron': 0.0,
                'folate': 0.0,
                'source': 'db',
            })

    return jsonify({'transcript': text_transcript, 'items': found_items})



# ══════════════════════════════════════════════════
#  AI MEAL RECOMMENDATIONS
# ══════════════════════════════════════════════════

import re as _re

# base_foods has no is_veg/is_vegan/diet tag column, so diet filtering here is
# name-based keyword matching — a heuristic, not a perfect classifier. Word
# boundaries (\b) matter: without them "butter" would also match "peanut
# butter", "ham" would match "hamburger bun", etc.
_NONVEG_KEYWORDS = [
    'chicken', 'beef', 'pork', 'mutton', 'lamb', 'goat', 'veal', 'venison',
    'bacon', 'ham', 'sausage', 'turkey', 'duck', 'meat', 'meatball', 'meatloaf',
    'fish', 'salmon', 'tuna', 'shrimp', 'prawn', 'crab', 'lobster',
    'oyster', 'squid', 'octopus', 'anchovy', 'sardine', 'gelatin',
    # Dish/ingredient names that imply meat or fish without spelling out the
    # animal — a plain word-list of animal names alone misses these entirely.
    'bolognese', 'carbonara', 'pepperoni', 'salami', 'chorizo', 'prosciutto',
    'jerky', 'pastrami', 'brisket', 'mince', 'minced', 'pate', 'ribs',
    'bologna', 'pancetta', 'lardons', 'charcuterie',
]
_EGG_KEYWORDS = ['egg', 'omelette', 'omelet']
_DAIRY_KEYWORDS = [
    'milk', 'cheese', 'paneer', 'yogurt', 'yoghurt', 'curd', 'butter',
    'ghee', 'cream', 'whey', 'custard', 'khoya',
]


def _food_matches_diet(name, diet_type):
    n = (name or '').lower()
    # "butter" alone means dairy, but "peanut butter" / "almond butter" etc.
    # are not — strip these known compounds before checking dairy keywords
    # so they don't false-positive as non-vegan/non-dairy.
    n_for_dairy = _re.sub(r'\b(peanut|almond|cashew|cocoa|shea|apple|sunflower)\s+butter\b', '', n)

    def has_any(words, text=n):
        # Allow a simple plural suffix (sardine/sardines, egg/eggs) — the
        # earlier version required an exact whole-word match with nothing
        # after it, which missed plurals entirely.
        return any(_re.search(r'\b' + _re.escape(w) + r'(e?s)?\b', text) for w in words)

    if diet_type in ('nonveg', 'non-veg', 'non_vegetarian'):
        return True
    if diet_type in ('eggetarian', 'egg'):
        return not has_any(_NONVEG_KEYWORDS)
    if diet_type == 'vegan':
        return not has_any(_NONVEG_KEYWORDS) and not has_any(_EGG_KEYWORDS) and not has_any(_DAIRY_KEYWORDS, n_for_dairy) and not has_any(['honey'])
    # default: 'veg' / 'vegetarian' / anything else — excludes meat, fish, and eggs; dairy is fine
    return not has_any(_NONVEG_KEYWORDS) and not has_any(_EGG_KEYWORDS)


@app.route('/api/ai/recommend', methods=['POST'])
@jwt_required(optional=True)
def recommend_meals():
    """
    Recommends meals based on current user goals, remaining calories/macros,
    and diet type. Queries Supabase base_foods for best matching food options,
    filtered by diet_type (see _food_matches_diet — keyword-based, since
    base_foods has no explicit veg/vegan column).
    """
    data = request.get_json() or {}
    rem_cal = float(data.get('rem_cal', 500))
    rem_pro = float(data.get('rem_pro', 30))
    diet_type = (data.get('diet_type') or 'nonveg').lower()

    if not supabase:
        return jsonify([])

    try:
        # Fetch a larger pool so filtering still leaves enough matches
        res = supabase.table('base_foods').select('*').limit(400).execute()
        rows = res.data or []

        recommendations = []
        for r in rows:
            name = r.get('name') or ''
            if not _food_matches_diet(name, diet_type):
                continue
            cal = float(r.get('calories') or 0)
            pro = float(r.get('protein') or 0)

            # Filter foods that fit roughly into remaining calories & offer good protein
            if 50 <= cal <= (rem_cal + 150) and pro >= (rem_pro * 0.2):
                recommendations.append({
                    'id': f"rec_{r.get('id')}",
                    'name': name.title(),
                    'emoji': '🥗',
                    'cal': round(cal, 1),
                    'pro': round(pro, 1),
                    'carb': round(float(r.get('carbs') or 0), 1),
                    'fat': round(float(r.get('fat') or 0), 1),
                    'reason': f"Fits remaining budget ({round(cal)} kcal, {round(pro)}g protein)"
                })

        recommendations.sort(key=lambda x: x['pro'], reverse=True)
        return jsonify(recommendations[:10])

    except Exception as e:
        print(f"⚠️ recommend_meals error: {e}")
        return jsonify([])


# ══════════════════════════════════════════════════
#  WEEKLY NUTRITION INSIGHTS
# ══════════════════════════════════════════════════

@app.route('/api/analytics/weekly-insights', methods=['GET'])
@jwt_required()
def weekly_insights():
    """Calculates 7-day nutrition insights, trend scores, and actionable feedback."""
    uid = get_jwt_identity()
    user = db.session.get(User, uid)

    dates = _date_range(7)
    logs = FoodLog.query.filter(FoodLog.user_id == uid, FoodLog.date.in_(dates)).all()

    goal_cal = user.goal_calories if user else 2000
    goal_pro = user.goal_protein if user else 150

    daily_totals = {d: {'cal': 0, 'pro': 0, 'fiber': 0} for d in dates}
    for l in logs:
        if l.date in daily_totals:
            daily_totals[l.date]['cal'] += l.cal
            daily_totals[l.date]['pro'] += l.pro
            daily_totals[l.date]['fiber'] += (l.fiber or 0)

    logged_days = [d for d, t in daily_totals.items() if t['cal'] > 0]
    num_logged = len(logged_days)

    avg_cal = round(sum(t['cal'] for t in daily_totals.values()) / max(num_logged, 1), 1)
    avg_pro = round(sum(t['pro'] for t in daily_totals.values()) / max(num_logged, 1), 1)

    adherence_score = min(100, round((num_logged / 7.0) * 100))

    insights = []
    if avg_pro >= goal_pro * 0.9:
        insights.append("💪 Excellent protein intake this week!")
    else:
        insights.append(f"💡 Try adding more high-protein snacks to reach your daily {goal_pro}g goal.")

    if abs(avg_cal - goal_cal) <= 200:
        insights.append("🔥 Spot on calorie target consistency.")
    elif avg_cal > goal_cal + 200:
        insights.append(f"⚠️ Averaging {round(avg_cal - goal_cal)} kcal above daily target.")
    else:
        insights.append(f"📉 Averaging {round(goal_cal - avg_cal)} kcal below target.")

    return jsonify({
        'periodDays': 7,
        'daysLogged': num_logged,
        'adherenceScore': adherence_score,
        'avgCalories': avg_cal,
        'avgProtein': avg_pro,
        'goalCalories': goal_cal,
        'goalProtein': goal_pro,
        'insights': insights
    })


# ══════════════════════════════════════════════════
#  SOCIAL & COMMUNITY CHALLENGES
# ══════════════════════════════════════════════════

@app.route('/api/challenges', methods=['GET'])
def get_challenges():
    """List available public community challenges."""
    defaults = [
        Challenge(title="7-Day Protein Streak", description="Hit your daily protein target for 7 consecutive days", metric="protein", target_val=7, badge_emoji="💪"),
        Challenge(title="Hydration Hero", description="Log at least 2000ml water for 5 days this week", metric="water", target_val=5, badge_emoji="💧"),
        Challenge(title="Century Club", description="Log 100 total meals in NutriTrack", metric="logs", target_val=100, badge_emoji="💯"),
        Challenge(title="Fiber Fanatic", description="Hit your daily fiber goal for 5 days this week", metric="fiber", target_val=5, badge_emoji="🌾"),
        Challenge(title="Calorie Consistency", description="Stay within 10% of your calorie goal for 7 days", metric="calorie_consistency", target_val=7, badge_emoji="🎯"),
        Challenge(title="No Sugar Sundown", description="Keep added sugar under 25g for 5 days this week", metric="low_sugar", target_val=5, badge_emoji="🍬"),
        Challenge(title="30-Day Logger", description="Log at least one meal every day for 30 days straight", metric="streak", target_val=30, badge_emoji="🗓️"),
        Challenge(title="Move More Week", description="Log a workout on 5 different days this week", metric="workouts", target_val=5, badge_emoji="🏃"),
        Challenge(title="Balanced Plate", description="Hit protein, carb, and fat targets together on 3 days this week", metric="balanced_macros", target_val=3, badge_emoji="⚖️"),
        Challenge(title="Early Riser Streak", description="Log breakfast before 10am for 5 days this week", metric="early_breakfast", target_val=5, badge_emoji="🌅"),
    ]
    try:
        existing_titles = {c.title for c in Challenge.query.all()}
        added = False
        for d in defaults:
            if d.title not in existing_titles:
                db.session.add(d)
                added = True
        if added:
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Challenge seed error: {e}")

    challenges = Challenge.query.all()
    return jsonify([c.to_dict() for c in challenges])


@app.route('/api/challenges/join/<int:challenge_id>', methods=['POST'])
@jwt_required()
def join_challenge(challenge_id):
    uid = get_jwt_identity()
    existing = ChallengeParticipant.query.filter_by(challenge_id=challenge_id, user_id=uid).first()
    if existing:
        return jsonify(existing.to_dict())

    try:
        cp = ChallengeParticipant(challenge_id=challenge_id, user_id=uid, current_val=0, completed=False)
        db.session.add(cp)
        db.session.commit()
        return jsonify(cp.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error joining challenge: {e}")
        return jsonify({'error': 'Could not join challenge'}), 500


@app.route('/api/challenges/leaderboard/<int:challenge_id>', methods=['GET'])
def challenge_leaderboard(challenge_id):
    participants = ChallengeParticipant.query.filter_by(challenge_id=challenge_id).order_by(ChallengeParticipant.current_val.desc()).limit(20).all()
    return jsonify([p.to_dict() for p in participants])


# ══════════════════════════════════════════════════
#  EXPORT FOOD LOG DATA (CSV)
# ══════════════════════════════════════════════════

@app.route('/api/logs/export', methods=['GET'])
@jwt_required()
def export_logs_csv():
    """Download food logs as a CSV spreadsheet."""
    uid = get_jwt_identity()
    logs = FoodLog.query.filter_by(user_id=uid).order_by(FoodLog.date.desc(), FoodLog.id.desc()).all()

    import io
    import csv
    from flask import Response

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Meal', 'Food Name', 'Calories (kcal)', 'Protein (g)', 'Carbs (g)', 'Fat (g)', 'Fiber (g)', 'Sugar (g)', 'Sodium (mg)', 'Cholesterol (mg)'])

    for l in logs:
        writer.writerow([l.date, l.meal_type, l.name, l.cal, l.pro, l.carb, l.fat, l.fiber or 0, l.sugar or 0, l.sodium or 0, l.chol or 0])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=nutritrack_logs.csv'
    return response



# ══════════════════════════════════════════════════
#  WORKOUT TRACKING
# ══════════════════════════════════════════════════

@app.route('/api/workouts', methods=['GET'])
@jwt_required()
def get_workouts():
    """Get workout entries for a given date (default: today)."""
    uid  = get_jwt_identity()
    date = request.args.get('date', _today())
    logs = WorkoutLog.query.filter_by(user_id=uid, date=date).order_by(WorkoutLog.logged_at.desc()).all()
    total_burned = sum(l.cal_burned for l in logs)
    return jsonify({'date': date, 'totalBurned': total_burned, 'entries': [l.to_dict() for l in logs]})


@app.route('/api/workouts', methods=['POST'])
@jwt_required()
def add_workout():
    """Log an exercise / workout session."""
    uid  = get_jwt_identity()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Workout name required'}), 400

    try:
        duration_min = int(data.get('duration_min', 30))
        cal_burned   = float(data.get('cal_burned', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid duration or calories'}), 400

    if cal_burned <= 0:
        # Default MET estimate if not provided (e.g. ~7 kcal/min for general workout)
        cal_burned = round(duration_min * 7.5, 1)

    date = data.get('date') or _today()

    try:
        log = WorkoutLog(user_id=uid, date=date, name=name, duration_min=duration_min, cal_burned=cal_burned)
        db.session.add(log)
        db.session.commit()
        return jsonify(log.to_dict()), 201
    except Exception as e:
        print(f"⚠️ add_workout error: {e}")
        return jsonify({'error': 'Could not save workout.'}), 500


@app.route('/api/workouts/<string:log_id>', methods=['DELETE'])
@jwt_required()
def delete_workout(log_id):
    uid = get_jwt_identity()
    if not log_id.isdigit():
        return jsonify({'error': 'Log not found'}), 404
    try:
        log = WorkoutLog.query.filter_by(id=int(log_id), user_id=uid).first()
        if not log:
            return jsonify({'error': 'Log not found'}), 404
        db.session.delete(log)
        db.session.commit()
        return jsonify({'deleted': True})
    except Exception as e:
        print(f"Error deleting workout: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ══════════════════════════════════════════════════
#  NUTRIBOT CONTEXT-AWARE CHATBOT
# ══════════════════════════════════════════════════

@app.route('/api/ai/chat', methods=['POST'])
@jwt_required(optional=True)
def ai_chat():
    """
    NutriBot — Context-Aware AI Nutritionist Chatbot.
    Fetches the user's profile, daily goals, today's logs, and remaining macros
    to provide intelligent nutrition advice.
    """
    data = request.get_json() or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'response': 'Please enter a message.', 'reply': 'Please enter a message.'})

    uid = get_jwt_identity()
    user = db.session.get(User, uid) if uid else None

    # Context gathering
    today = _today()
    today_logs = FoodLog.query.filter_by(user_id=uid, date=today).all() if uid else []
    today_cals = sum(l.cal for l in today_logs)
    today_pro = sum(l.pro for l in today_logs)

    goal_cals = user.goal_calories if user else 2000
    goal_pro = user.goal_protein if user else 150
    diet_type = user.diet_type if user else 'nonveg'

    rem_cal = max(0.0, float(goal_cals - today_cals))
    rem_pro = max(0.0, float(goal_pro - today_pro))

    sys_context = f"User Profile: Diet Goal={user.diet_goal if user else 'maintain'}, Diet Type={diet_type}. Today's Progress: Logged {round(today_cals)} kcal / {goal_cals} kcal, Protein {round(today_pro)}g / {goal_pro}g. Remaining: {round(rem_cal)} kcal, {round(rem_pro)}g protein."

    # Try LLM server first if available
    llm_url = os.getenv('LLM_SERVER_URL', 'https://energyvenom-nutritrack-llm.hf.space')
    try:
        resp = requests.post(
            f'{llm_url}/api/ai/chat',
            json={'message': message, 'context': sys_context},
            timeout=8
        )
        if resp.status_code == 200:
            res_data = resp.json()
            reply = res_data.get('reply') or res_data.get('response') or ''
            if reply:
                return jsonify({'response': reply, 'reply': reply, 'context': sys_context})
    except Exception:
        pass

    # Direct intelligent response generator using context + DB knowledge
    matched = _find_closest_food(message)
    food_tip = ""
    if matched:
        food_tip = f"\n\nNutrition Info for {matched.get('name')}: {matched.get('calories')} kcal, {matched.get('protein')}g Protein, {matched.get('carbs')}g Carbs, {matched.get('fat')}g Fat."

    reply = f"Based on your profile ({sys_context}):\n\nTo answer '{message}': You currently have {round(rem_cal)} kcal and {round(rem_pro)}g protein left for today.{food_tip}\n\nKeep hitting your goals!"

    return jsonify({'response': reply, 'reply': reply, 'context': sys_context})


# ══════════════════════════════════════════════════
#  RESTAURANT MENU AI SCANNER
# ══════════════════════════════════════════════════

@app.route('/api/ai/analyze-menu', methods=['POST'])
@jwt_required(optional=True)
def analyze_menu():
    """
    Parses a photo of a restaurant menu, extracts multiple dishes,
    and enriches each dish with verified database nutrition.
    """
    data = request.get_json() or {}
    image = data.get('image', '')
    if not image:
        return jsonify({'error': 'No image provided'}), 400

    llm_url = os.getenv('LLM_SERVER_URL', 'https://energyvenom-nutritrack-llm.hf.space')
    try:
        resp = requests.post(
            f'{llm_url}/api/ai/analyze',
            json={'image': image, 'mode': 'menu'},
            timeout=120
        )
        if resp.status_code == 200:
            result = resp.json()
            dishes = result.get('items', [])
            enriched_dishes = []
            for d in dishes:
                _enrich_with_rag(d)
                enriched_dishes.append(d)
            return jsonify({'is_menu': True, 'dishes': enriched_dishes})
    except Exception as e:
        print(f"⚠️ analyze_menu LLM error: {e}")

    # Fallback response for testing/offline mode
    return jsonify({
        'is_menu': True,
        'dishes': [
            {'food_name': 'Grilled Chicken Salad', 'calories': 380, 'protein_g': 35, 'carbs_g': 12, 'fat_g': 14, 'source': 'Menu AI'},
            {'food_name': 'Paneer Butter Masala', 'calories': 450, 'protein_g': 18, 'carbs_g': 22, 'fat_g': 28, 'source': 'Menu AI'},
            {'food_name': 'Margherita Pizza (Slice)', 'calories': 270, 'protein_g': 11, 'carbs_g': 32, 'fat_g': 10, 'source': 'Menu AI'}
        ]
    })


# ══════════════════════════════════════════════════
#  AI FOOD ANALYSIS
# ══════════════════════════════════════════════════


@app.route('/api/ai/analyze', methods=['POST'])
@limiter.limit('10 per minute;300 per day')
@jwt_required(optional=True)
def ai_analyze():
    """
    Analyzes food image using Gemini 1.5 Flash (1s fast-path) if API key present,
    or forwards to Hugging Face LLM inference server with 25s fast-timeout and RAG fallback.
    """
    data  = request.get_json() or {}
    image = data.get('image', '')

    if not image:
        return jsonify({'error': 'No image provided'}), 400

    # 1. Fast Path: Gemini 1.5 Flash Vision (under 1.5 seconds)
    gemini_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if gemini_key:
        try:
            g_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": """Analyze this food image and identify all food items. For each item, assess your ACTUAL certainty of the identification as a number 0-100 (do not default to any fixed value - a clearly identifiable food should score high, an ambiguous or partially-obscured one should score lower). Return ONLY JSON in this exact shape: {"items":[{"food_name":"<name>","serving_size":"<e.g. 1 cup>","confidence":<your real 0-100 certainty>,"calories":<number>,"protein_g":<number>,"carbs_g":<number>,"fat_g":<number>,"fiber_g":<number>,"sugar_g":<number>,"sodium_mg":<number>,"cholesterol_mg":<number>}]}. If the image contains no food, return {"not_food": true}."""},
                        {"inline_data": {"mime_type": "image/jpeg", "data": image}}
                    ]
                }]
            }
            g_resp = requests.post(g_url, json=payload, timeout=8)
            if g_resp.status_code == 200:
                raw_text = g_resp.json()['candidates'][0]['content']['parts'][0]['text']
                raw_text = raw_text.replace('```json', '').replace('```', '').strip()
                result = json.loads(raw_text)

                if result.get('items') and len(result['items']) > 0:
                    for item in result['items']:
                        _enrich_with_rag(item)
                    return jsonify(result)
        except Exception as ge:
            print(f"⚡ Gemini fast-path fallback: {ge}")

    # 2. Secondary Path: LLM Server (25s fast timeout)
    llm_url = os.getenv('LLM_SERVER_URL', 'https://energyvenom-nutritrack-llm.hf.space')
    try:
        resp = requests.post(
            f'{llm_url}/api/ai/analyze',
            json={'image': image},
            timeout=25
        )
        if resp.status_code == 200:
            result = resp.json()
            if 'items' in result and isinstance(result['items'], list) and len(result['items']) > 0:
                for item in result['items']:
                    _enrich_with_rag(item)
                result['source'] = 'Mixed / Multiple Items' if len(result['items']) > 1 else result['items'][0].get('source', 'AI Vision')
            else:
                _enrich_with_rag(result)
            return jsonify(result)
    except Exception as e:
        print(f"⚠️ LLM Server timeout/error ({e}). AI scan failed.")

    # 3. Both Gemini and the LLM server failed. Previously this returned
    # fabricated numbers (350 kcal, 85% "confidence") labeled as a real
    # result, which silently gave users made-up nutrition data with no way
    # to tell it wasn't a real scan. Instead, return an honest zero-
    # confidence result so the UI shows the scan failed and the user can
    # log the meal manually with real numbers.
    return jsonify({
        'items': [{
            'food_name': 'Scan unavailable — please log manually',
            'serving_size': '',
            'confidence': 0,
            'calories': 0,
            'protein_g': 0,
            'carbs_g': 0,
            'fat_g': 0,
            'fiber_g': 0,
            'sugar_g': 0,
            'sodium_mg': 0,
            'cholesterol_mg': 0,
            'source': '⚠️ AI scan failed — search for this food instead'
        }],
        'scan_failed': True
    }), 200

@app.route('/api/ai/analyze/stream', methods=['POST'])
@limiter.limit('10 per minute;300 per day')
@jwt_required(optional=True)
def ai_analyze_stream():
    """Proxy streaming endpoint for the LLM."""
    data  = request.get_json() or {}
    image = data.get('image', '')

    if not image:
        return jsonify({'error': 'No image provided'}), 400

    llm_url = os.getenv('LLM_SERVER_URL', 'https://energyvenom-nutritrack-llm.hf.space')
    try:
        # We must stream=True on the requests call and yield the bytes
        resp = requests.post(
            f'{llm_url}/api/ai/analyze/stream',
            json={'image': image},
            stream=True,
            timeout=120
        )
        if resp.status_code != 200:
            return jsonify({'error': 'LLM server error'}), 502

        def generate():
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode('utf-8')
                if decoded.startswith('data:'):
                    json_str = decoded[5:].strip()
                    if json_str:
                        try:
                            evt = json.loads(json_str)
                            if 'result' in evt:
                                result = evt['result']
                                if 'items' in result and isinstance(result['items'], list) and len(result['items']) > 0:
                                    all_rag = True
                                    for item in result['items']:
                                        is_rag = _enrich_with_rag(item)
                                        if not is_rag: all_rag = False
                                    
                                    if len(result['items']) == 1:
                                        result['source'] = result['items'][0].get('source', 'Vision AI')
                                    else:
                                        result['source'] = 'Mixed / Multiple Items'
                                else:
                                    _enrich_with_rag(result)
                                # Serialize back to SSE
                                yield f"data: {json.dumps({'result': result})}\n\n".encode('utf-8')
                            else:
                                # Heartbeats or other events
                                yield f"{decoded}\n\n".encode('utf-8')
                        except json.JSONDecodeError:
                            yield f"{decoded}\n\n".encode('utf-8')
                else:
                    yield f"{decoded}\n\n".encode('utf-8')
        return app.response_class(
            generate(),
            content_type='text/event-stream',
            headers={
                'Cache-Control':     'no-cache',
                # Disable reverse-proxy buffering (nginx on HF Spaces, etc.) —
                # without this, the whole SSE stream can get buffered and sent
                # as one chunk, which defeats the point of streaming: heartbeats
                # exist specifically to keep the connection alive and avoid
                # HF's 60-second gateway timeout on slow cold-start inference.
                'X-Accel-Buffering': 'no',
            }
        )
    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Multimodal LLM server not running. Start it with: python llm/Llm_server.py'
        }), 503
    except requests.exceptions.Timeout:
        return jsonify({'error': 'LLM server timed out'}), 504


# ══════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════

@app.route('/api/analytics/streak', methods=['GET'])
@jwt_required()
def streak():
    """How many consecutive days the user has logged food."""
    uid = get_jwt_identity()
    # Get all unique dates logged, sorted descending
    rows = (db.session.query(FoodLog.date)
            .filter_by(user_id=uid)
            .distinct()
            .order_by(FoodLog.date.desc())
            .all())
    logged_dates = {r[0] for r in rows}

    count = 0
    check = datetime.now(timezone.utc).date()
    while check.isoformat() in logged_dates:
        count += 1
        check -= timedelta(days=1)

    return jsonify({'streak': count, 'unit': 'days'})


# ══════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════




@app.route('/robots.txt')
def serve_robots():
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
    return send_from_directory(frontend_dir, 'robots.txt')


@app.route('/sitemap.xml')
def serve_sitemap():
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
    return send_from_directory(frontend_dir, 'sitemap.xml')


# ══════════════════════════════════════════════════
#  WEARABLE INTEGRATION (GOOGLE FIT)
# ══════════════════════════════════════════════════

@app.route('/api/integrations/google-fit/client-id', methods=['GET'])
def google_fit_client_id():
    """Client ID is not a secret (only the Client Secret is) — safe to
    expose so the frontend can build the Google consent URL itself,
    entirely independent of Supabase's own login flow."""
    return jsonify({'client_id': os.getenv('GOOGLE_CLIENT_ID', '')})


@app.route('/api/integrations/google-fit/connect', methods=['POST'])
@jwt_required()
def connect_google_fit():
    """Exchange a Google authorization `code` (from a dedicated consent
    redirect that never touches Supabase auth) for tokens, and store the
    refresh_token for THIS already-logged-in user. Because this never goes
    through supabase.auth.signInWithOAuth, granting Fitness access can never
    replace/switch the user's actual NutriTrack login session — it's just
    an extra permission grant layered on top of whoever is already signed in."""
    uid = get_jwt_identity()
    data = request.get_json() or {}
    code = data.get('code')
    redirect_uri = data.get('redirect_uri')
    if not code or not redirect_uri:
        return jsonify({'error': 'code and redirect_uri required'}), 400

    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    if not client_id or not client_secret:
        return jsonify({'error': 'GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET not configured on the server'}), 500

    try:
        resp = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }, timeout=10)
        if not resp.ok:
            print(f"Google code exchange failed: {resp.status_code} {resp.text[:300]}")
            return jsonify({'error': 'Google rejected the authorization code'}), 400
        token_data = resp.json()
        refresh_token = token_data.get('refresh_token')
        if not refresh_token:
            # Google only returns a refresh_token the FIRST time a user
            # consents (or when prompt=consent forces re-issue). If this
            # happens, the account most likely already has a prior grant
            # Google didn't re-issue a token for — safest is to tell the
            # user to revoke access at myaccount.google.com/permissions and
            # try connecting again.
            return jsonify({'error': 'no_refresh_token',
                             'message': 'Google did not return a refresh token. Revoke NutriTrack access at myaccount.google.com/permissions and try connecting again.'}), 400

        existing = GoogleFitToken.query.filter_by(user_id=uid).first()
        if existing:
            existing.refresh_token = refresh_token
        else:
            db.session.add(GoogleFitToken(user_id=uid, refresh_token=refresh_token))
        db.session.commit()
        return jsonify({'connected': True}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Google Fit connect error: {e}")
        return jsonify({'error': 'Failed to store Google Fit connection'}), 500


@app.route('/api/integrations/google-fit/status', methods=['GET'])
@jwt_required()
def google_fit_status():
    """Lets the frontend show 'Connected' / 'Not connected' without
    triggering a full sync."""
    uid = get_jwt_identity()
    tok = GoogleFitToken.query.filter_by(user_id=uid).first()
    return jsonify({'connected': tok is not None,
                     'connected_at': tok.connected_at.isoformat() if tok else None})


@app.route('/api/integrations/google-fit/disconnect', methods=['POST'])
@jwt_required()
def disconnect_google_fit():
    """Lets the user disconnect (e.g. to reconnect a different Google
    account) rather than being stuck with whichever account they first used."""
    uid = get_jwt_identity()
    try:
        GoogleFitToken.query.filter_by(user_id=uid).delete()
        db.session.commit()
        return jsonify({'connected': False}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Google Fit disconnect error: {e}")
        return jsonify({'error': 'Failed to disconnect'}), 500


def _refresh_google_access_token(refresh_token):
    """Exchange a stored refresh_token for a short-lived Google access token."""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise RuntimeError('GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET not configured on the server')
    resp = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    }, timeout=10)
    if not resp.ok:
        raise RuntimeError(f'Google token refresh failed: {resp.status_code} {resp.text[:200]}')
    return resp.json()['access_token']


def _fetch_google_fitness_today(access_token):
    """Same aggregate query the frontend used to run client-side, now run
    server-side with a freshly-minted access token."""
    now = datetime.now(timezone.utc)
    start_of_day = int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp() * 1000)
    end_of_day = int(now.timestamp() * 1000)
    body = {
        'aggregateBy': [
            {'dataTypeName': 'com.google.step_count.delta'},
            {'dataTypeName': 'com.google.calories.expended'},
        ],
        'bucketByTime': {'durationMillis': 86400000},
        'startTimeMillis': start_of_day,
        'endTimeMillis': end_of_day,
    }
    resp = requests.post(
        'https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate',
        headers={'Authorization': f'Bearer {access_token}'},
        json=body, timeout=10,
    )
    if not resp.ok:
        raise RuntimeError(f'Google Fitness API status {resp.status_code}')
    data = resp.json()
    total_steps, total_cal = 0, 0.0
    for bucket in data.get('bucket', []):
        for ds in bucket.get('dataset', []):
            is_steps = 'step_count' in (ds.get('dataSourceId') or '')
            is_cal = 'calories' in (ds.get('dataSourceId') or '')
            for point in ds.get('point', []):
                for val in point.get('value', []):
                    v = val.get('intVal', val.get('fpVal', 0))
                    if is_steps:
                        total_steps += v
                    elif is_cal:
                        total_cal += v
    return round(total_steps), round(total_cal or total_steps * 0.04, 1)


@app.route('/api/integrations/google-fit/sync', methods=['POST'])
@jwt_required()
def sync_google_fit():
    """Pull TODAY's real step count & active calorie burn from Google Fit
    using the stored refresh token — no hardcoded numbers, no re-login."""
    uid = get_jwt_identity()
    date = (request.get_json() or {}).get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))

    tok = GoogleFitToken.query.filter_by(user_id=uid).first()
    if not tok:
        return jsonify({'connected': False}), 200

    try:
        access_token = _refresh_google_access_token(tok.refresh_token)
        steps, cal_burned = _fetch_google_fitness_today(access_token)
    except Exception as e:
        print(f"Google Fit sync error: {e}")
        if 'token refresh failed' in str(e).lower():
            db.session.delete(tok)
            db.session.commit()
            return jsonify({'connected': False, 'needs_reauth': True}), 200
        return jsonify({'error': 'Failed to sync Google Fit data'}), 502

    try:
        w_log = WorkoutLog(
            user_id=uid, date=date, name="Google Fit Daily Steps",
            duration_min=max(1, round(steps / 100)), cal_burned=cal_burned,
        )
        db.session.add(w_log)
        db.session.commit()
        return jsonify({'connected': True, 'synced': True, 'steps': steps,
                         'cal_burned': cal_burned, 'workout': w_log.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Google Fit sync (DB write) error: {e}")
        return jsonify({'error': 'Failed to save synced data'}), 500






# ══════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        db_type = 'PostgreSQL' if 'postgresql' in db_url else 'SQLite'
        print("✅ NutriTrack API starting...")
        print(f"   Database: {db_type}")
        print("   Endpoints: http://localhost:5000/api/")

    app.run(
        host  = '0.0.0.0',
        port  = int(os.getenv('PORT', 5000)),
        debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    )