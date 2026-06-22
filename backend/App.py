"""
NutriTrack — backend/App.py
Flask REST API backend

Endpoints:
  POST /api/auth/register      — create account
  POST /api/auth/login         — login, get JWT
  POST /api/auth/refresh       — refresh access token
  GET  /api/auth/me            — current user info

  GET  /api/logs               — get logs (?date=YYYY-MM-DD or ?days=30)
  POST /api/logs               — add food log
  DELETE /api/logs/<id>        — remove log
  GET  /api/logs/summary       — daily totals (?days=30)

  POST /api/ai/analyze         — AI food photo via Ollama/llava-phi3 LLM
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
import json
import base64
import requests
from datetime import datetime, timezone, timedelta

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
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'sqlite:///nutritrack.db'
).replace('postgres://', 'postgresql://')   # Railway fix
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT
jwt_secret = os.getenv('JWT_SECRET_KEY', 'change-me-in-production')
if jwt_secret == 'change-me-in-production':
    print("⚠️  WARNING: Using default JWT_SECRET_KEY. Set a real one in .env!")
app.config['JWT_SECRET_KEY']           = jwt_secret
app.config['JWT_ACCESS_TOKEN_EXPIRES']  = timedelta(days=7)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

db  = SQLAlchemy(app)
jwt = JWTManager(app)

# CORS — allow frontend from local dev
_cors_origins = [
    'http://localhost:3000',
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'null',            # file:// opened locally
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

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(200), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)   # bcrypt hash
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))

    # Body stats
    age         = db.Column(db.Integer)
    weight      = db.Column(db.Float)
    weight_unit = db.Column(db.String(10), default='kg')
    height      = db.Column(db.Float)
    height_unit = db.Column(db.String(10), default='cm')
    gender      = db.Column(db.String(20))
    diet_goal   = db.Column(db.String(40))

    # Nutrition goals
    goal_calories = db.Column(db.Integer, default=2000)
    goal_protein  = db.Column(db.Integer, default=150)
    goal_carbs    = db.Column(db.Integer, default=250)
    goal_fat      = db.Column(db.Integer, default=65)
    goal_fiber    = db.Column(db.Integer, default=28)
    goal_sugar    = db.Column(db.Integer, default=50)
    goal_sodium   = db.Column(db.Integer, default=2300)
    goal_chol     = db.Column(db.Integer, default=300)

    logs = db.relationship('FoodLog', backref='user', lazy=True,
                           cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':         self.id,
            'name':       self.name,
            'email':      self.email,
            'created_at': self.created_at.isoformat(),
            'body_stats': {
                'age':         self.age,
                'weight':      self.weight,
                'weight_unit': self.weight_unit,
                'height':      self.height,
                'height_unit': self.height_unit,
                'gender':      self.gender,
                'diet_goal':   self.diet_goal,
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
            }
        }


class FoodLog(db.Model):
    __tablename__ = 'food_logs'

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
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
            'logged_at': self.logged_at.isoformat(),
        }


# ══════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════

def _hash_password(pw):
    try:
        import bcrypt
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(12)).decode()
    except ImportError:
        # Fallback if bcrypt not installed (dev only — NOT for production)
        import hashlib
        return 'sha256:' + hashlib.sha256(pw.encode()).hexdigest()

def _check_password(pw, hashed):
    try:
        import bcrypt
        if hashed.startswith('sha256:'):
            import hashlib
            return 'sha256:' + hashlib.sha256(pw.encode()).hexdigest() == hashed
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ImportError:
        import hashlib
        return 'sha256:' + hashlib.sha256(pw.encode()).hexdigest() == hashed

def _validate_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

def _today():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')

def _date_range(days):
    """Return list of date strings for the past N days (oldest first)."""
    today = datetime.now(timezone.utc).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days-1, -1, -1)]


# ══════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit('20 per minute')
def register():
    data = request.get_json() or {}

    name  = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    pw    = data.get('password') or ''

    if not name:
        return jsonify({'error': 'Name is required'}), 400
    if not email or not _validate_email(email):
        return jsonify({'error': 'Valid email is required'}), 400
    if len(pw) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    # Body stats (optional)
    stats = data.get('body_stats', {})
    goals = data.get('goals', {})

    user = User(
        name        = name,
        email       = email,
        password    = _hash_password(pw),
        age         = stats.get('age'),
        weight      = stats.get('weight'),
        weight_unit = stats.get('weight_unit', 'kg'),
        height      = stats.get('height'),
        height_unit = stats.get('height_unit', 'cm'),
        gender      = stats.get('gender'),
        diet_goal   = stats.get('diet_goal'),

        goal_calories = goals.get('calories', 2000),
        goal_protein  = goals.get('protein',  150),
        goal_carbs    = goals.get('carbs',    250),
        goal_fat      = goals.get('fat',       65),
        goal_fiber    = goals.get('fiber',     28),
        goal_sugar    = goals.get('sugar',     50),
        goal_sodium   = goals.get('sodium',  2300),
        goal_chol     = goals.get('chol',     300),
    )
    db.session.add(user)
    db.session.commit()

    access  = create_access_token(identity=str(user.id))
    refresh = create_refresh_token(identity=str(user.id))
    return jsonify({
        'access_token':  access,
        'refresh_token': refresh,
        'user':          user.to_dict()
    }), 201


@app.route('/api/auth/login', methods=['POST'])
@limiter.limit('20 per minute')
def login():
    data  = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    pw    = data.get('password') or ''

    user = User.query.filter_by(email=email).first()
    if not user or not _check_password(pw, user.password):
        return jsonify({'error': 'Invalid email or password'}), 401

    access  = create_access_token(identity=str(user.id))
    refresh = create_refresh_token(identity=str(user.id))
    return jsonify({
        'access_token':  access,
        'refresh_token': refresh,
        'user':          user.to_dict()
    })


@app.route('/api/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    uid    = get_jwt_identity()
    access = create_access_token(identity=uid)
    return jsonify({'access_token': access})


@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def me():
    uid  = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict())


@app.route('/api/auth/update', methods=['PUT'])
@jwt_required()
def update_profile():
    uid  = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data  = request.get_json() or {}
    goals = data.get('goals', {})
    stats = data.get('body_stats', {})

    if 'name' in data:
        user.name = data['name'].strip() or user.name

    # Update body stats
    if stats.get('age'):         user.age         = int(stats['age'])
    if stats.get('weight'):      user.weight      = float(stats['weight'])
    if stats.get('weight_unit'): user.weight_unit = stats['weight_unit']
    if stats.get('height'):      user.height      = float(stats['height'])
    if stats.get('height_unit'): user.height_unit = stats['height_unit']
    if stats.get('gender'):      user.gender      = stats['gender']
    if stats.get('diet_goal'):   user.diet_goal   = stats['diet_goal']

    # Update nutrition goals
    if goals.get('calories'): user.goal_calories = int(goals['calories'])
    if goals.get('protein'):  user.goal_protein  = int(goals['protein'])
    if goals.get('carbs'):    user.goal_carbs     = int(goals['carbs'])
    if goals.get('fat'):      user.goal_fat       = int(goals['fat'])
    if goals.get('fiber'):    user.goal_fiber     = int(goals['fiber'])
    if goals.get('sugar'):    user.goal_sugar     = int(goals['sugar'])
    if goals.get('sodium'):   user.goal_sodium    = int(goals['sodium'])
    if goals.get('chol'):     user.goal_chol      = int(goals['chol'])

    db.session.commit()
    return jsonify(user.to_dict())


# ══════════════════════════════════════════════════
#  FOOD LOG ROUTES
# ══════════════════════════════════════════════════

@app.route('/api/logs', methods=['GET'])
@jwt_required()
def get_logs():
    uid  = int(get_jwt_identity())
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
    uid  = int(get_jwt_identity())
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
        cal       = float(data.get('cal',    0)),
        pro       = float(data.get('pro',    0)),
        carb      = float(data.get('carb',   0)),
        fat       = float(data.get('fat',    0)),
        fiber     = float(data.get('fiber',  0)),
        sugar     = float(data.get('sugar',  0)),
        sodium    = float(data.get('sodium', 0)),
        chol      = float(data.get('chol',   0)),
    )
    db.session.add(log)
    db.session.commit()
    return jsonify(log.to_dict()), 201


@app.route('/api/logs/<int:log_id>', methods=['DELETE'])
@jwt_required()
def delete_log(log_id):
    uid = int(get_jwt_identity())
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
    uid  = int(get_jwt_identity())
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
                       'sodium': 0, 'chol': 0, 'meals': 0}
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
            return jsonify(resp.json())
        return jsonify({'error': 'LLM server error'}), 502
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
    uid = int(get_jwt_identity())
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