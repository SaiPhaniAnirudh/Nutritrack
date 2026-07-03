"""
NutriTrack — backend/App.py
Flask REST API backend

Endpoints:
  POST /api/auth/register      — create account (requires verified OTP token)
  POST /api/auth/login         — login, get JWT
  POST /api/auth/refresh       — refresh access token
  GET  /api/auth/me            — current user info
  POST /api/auth/send-otp      — send 6-digit OTP to email for verification
  POST /api/auth/verify-otp    — verify OTP, receive short-lived verified token

  GET  /api/logs               — get logs (?date=YYYY-MM-DD or ?days=30)
  POST /api/logs               — add food log
  DELETE /api/logs/<id>        — remove log
  GET  /api/logs/summary       — daily totals (?days=30)

  POST /api/ai/analyze         — AI food photo via Ollama/llava-phi3 LLM
  POST /api/ai/chat            — AI nutritionist chatbot (proxied to LLM server)
  GET  /api/analytics/streak   — logging streak
  GET  /api/health             — health check

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

# Rate limiting — prevent abuse
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _has_limiter = True
except ImportError:
    _has_limiter = False
from flask_sqlalchemy import SQLAlchemy

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

from dotenv import load_dotenv, find_dotenv

# Load .env from project root (works whether running from root or backend/ dir)
load_dotenv(find_dotenv(usecwd=False, raise_error_if_not_found=False) or
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

# ══════════════════════════════════════════════════
#  APP SETUP
# ══════════════════════════════════════════════════

# Serve frontend from the sibling frontend/ folder
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
app = Flask(__name__, static_folder=_FRONTEND_DIR, static_url_path='')
Compress(app)

# Rate limiter setup
if _has_limiter:
    limiter = Limiter(
        get_remote_address, app=app,
        default_limits=['200 per hour'],
        storage_uri='memory://'
    )
    print("  Rate limiter active (200 req/hr default)")
else:
    from contextlib import contextmanager
    class _NoopLimiter:
        def limit(self, *a, **kw):
            def decorator(f): return f
            return decorator
    limiter = _NoopLimiter()

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

@app.route('/sw.js')
def serve_sw():
    return app.send_static_file('sw.js')

@app.route('/manifest.json')
def serve_manifest():
    return app.send_static_file('manifest.json')

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



# JWT

app.config['JWT_ACCESS_TOKEN_EXPIRES']  = timedelta(days=7)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

db  = SQLAlchemy(app)


# CORS — allow frontend from local dev and production
_cors_origins = [
    'http://localhost:3000',
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'null',            # file:// opened locally
    'https://nutritrack-k96f.onrender.com',
    'https://saiphanianirudh.github.io',
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
    password   = db.Column(db.String(200), nullable=True)    # bcrypt hash (nullable for Supabase auth)
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


with app.app_context():
    try:
        db.create_all()
        # Migration for missing columns in production
        from sqlalchemy import text
        columns_to_add = [
            "diet_type VARCHAR(20)",
            "goal_sugar FLOAT DEFAULT 50",
            "goal_sodium FLOAT DEFAULT 2300",
            "goal_chol FLOAT DEFAULT 300",
            "goal_vit_d FLOAT DEFAULT 20",
            "goal_iron FLOAT DEFAULT 18",
            "goal_folate FLOAT DEFAULT 400",
            "dob VARCHAR(20)"
        ]
        for col in columns_to_add:
            try:
                db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col};"))
                db.session.commit()
            except Exception:
                db.session.rollback()
        
        food_log_columns = [
            "fiber FLOAT DEFAULT 0",
            "sugar FLOAT DEFAULT 0",
            "sodium FLOAT DEFAULT 0",
            "chol FLOAT DEFAULT 0",
            "vit_d FLOAT DEFAULT 0",
            "iron FLOAT DEFAULT 0",
            "folate FLOAT DEFAULT 0"
        ]
        for col in food_log_columns:
            try:
                db.session.execute(text(f"ALTER TABLE food_logs ADD COLUMN {col};"))
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
        res = supabase.table('base_foods').select('*').ilike('name', f'%{name}%').limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        print("Error searching food in Supabase:", e)
    return None



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

    db.session.commit()
    return jsonify(user.to_dict())


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
        print(f"Error adding log: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/logs/<int:log_id>', methods=['DELETE'])
@jwt_required()
def delete_log(log_id):
    uid = get_jwt_identity()
    log = FoodLog.query.filter_by(id=log_id, user_id=uid).first()
    if not log:
        return jsonify({'error': 'Log not found'}), 404
    db.session.delete(log)
    db.session.commit()
    return jsonify({'deleted': True})


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
#  AI FOOD ANALYSIS
# ══════════════════════════════════════════════════

@app.route('/api/ai/analyze', methods=['POST'])
@limiter.limit('10 per minute')  # AI scans are expensive — rate-limit
@jwt_required(optional=True)
def ai_analyze():
    """
    Forward food image to the Ollama/llava-phi3 LLM inference server.
    No API key needed — LLM runs locally on port 5002.
    """
    data  = request.get_json() or {}
    image = data.get('image', '')

    if not image:
        return jsonify({'error': 'No image provided'}), 400

    llm_url = os.getenv('LLM_SERVER_URL', 'http://localhost:5002')
    try:
        resp = requests.post(
            f'{llm_url}/api/ai/analyze',
            json={'image': image},
            timeout=120   # LLM inference can take up to 90s on CPU
        )
        if resp.status_code == 200:
            result = resp.json()
            
            # Check for multiple items
            if 'items' in result and isinstance(result['items'], list) and len(result['items']) > 0:
                all_rag = True
                for item in result['items']:
                    fname = item.get('food_name', item.get('name', ''))
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
                    else:
                        all_rag = False
                        item['source'] = 'MLLM Estimation'
                        for key in ['vit_d', 'iron', 'folate']:
                            if key not in item: item[key] = 0
                if len(result['items']) == 1:
                    result['source'] = result['items'][0]['source']
                else:
                    result['source'] = 'Mixed / Multiple Items'
            else:
                food_name = result.get('food_name', result.get('name', ''))
                rag_match = _find_closest_food(food_name)
                if rag_match:
                    result['calories'] = rag_match.get('cal', 0)
                    result['protein_g'] = rag_match.get('pro', 0)
                    result['carbs_g'] = rag_match.get('carb', 0)
                    result['fat_g'] = rag_match.get('fat', 0)
                    result['fiber_g'] = rag_match.get('fiber', 0)
                    result['sugar_g'] = rag_match.get('sugar', 0)
                    result['sodium_mg'] = rag_match.get('sodium', 0)
                    result['cholesterol_mg'] = rag_match.get('chol', 0)
                    result['vit_d'] = rag_match.get('vit_d', 0.0)
                    result['iron'] = rag_match.get('iron', 0.0)
                    result['folate'] = rag_match.get('folate', 0.0)
                    result['source'] = 'Supabase RAG Database'
                    result['food_name'] = rag_match.get('name', food_name).title()
                else:
                    result['source'] = 'MLLM Estimation'
                    for key in ['vit_d', 'iron', 'folate']:
                        if key not in result: result[key] = 0
            
            return jsonify(result)
        return jsonify({'error': 'LLM server error'}), 502
    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Multimodal LLM server not running. Start it with: python llm/Llm_server.py'
        }), 503
    except requests.exceptions.Timeout:
        return jsonify({'error': 'LLM server timed out'}), 504


# ══════════════════════════════════════════════════
#  AI NUTRITIONIST CHATBOT
# ══════════════════════════════════════════════════

@app.route('/api/ai/chat', methods=['POST'])
@limiter.limit('20 per minute')
@jwt_required()
def ai_chat():
    """
    NutriBot — AI Nutritionist Chatbot.
    Fetches the user's last 7 days of food logs + their goals,
    bundles them as context, and forwards to the LLM server.
    """
    uid  = get_jwt_identity()
    user = db.session.get(User, uid)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data    = request.get_json() or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'Message is required'}), 400

    # Fetch last 7 days of logs for context
    dates = [(datetime.now(timezone.utc).date() - timedelta(days=i)).isoformat() for i in range(7)]
    logs  = FoodLog.query.filter(
        FoodLog.user_id == uid,
        FoodLog.date.in_(dates)
    ).order_by(FoodLog.date.desc(), FoodLog.logged_at.desc()).all()

    # Build a compact log summary
    log_summary = []
    for l in logs[:30]:  # cap at 30 entries to stay within context
        log_summary.append({
            'date':      l.date,
            'meal':      l.meal_type,
            'food':      l.name,
            'cal':       round(l.cal),
            'protein_g': round(l.pro, 1),
            'carbs_g':   round(l.carb, 1),
            'fat_g':     round(l.fat, 1),
        })

    context = {
        'user_name':  user.name.split()[0],
        'goals': {
            'calories': user.goal_calories,
            'protein':  user.goal_protein,
            'carbs':    user.goal_carbs,
            'fat':      user.goal_fat,
            'fiber':    user.goal_fiber,
        },
        'recent_logs': log_summary,
    }

    llm_url = os.getenv('LLM_SERVER_URL', 'http://localhost:5002')
    try:
        resp = requests.post(
            f'{llm_url}/api/ai/chat',
            json={'message': message, 'context': context},
            timeout=90
        )
        if resp.status_code == 200:
            return jsonify(resp.json())
        return jsonify({'error': 'AI server returned an error', 'reply': 'Sorry, I had trouble thinking. Please try again!'}), 502
    except requests.exceptions.ConnectionError:
        # Graceful fallback if LLM server is offline
        return jsonify({
            'reply': "I'm currently offline. Make sure the LLM server is running (`python llm/Llm_server.py`) to chat with me!",
            'offline': True
        })
    except requests.exceptions.Timeout:
        return jsonify({
            'reply': "I'm taking too long to think! The AI is busy. Please try again in a moment.",
            'timeout': True
        })


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




@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status':  'ok',
        'service': 'NutriTrack API',
        'db':      'connected'
    })


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