import re

path = r'c:\Users\pc\OneDrive\Desktop\nutritrack\backend\App.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace User.id and FoodLog.user_id to be Strings
content = content.replace("id         = db.Column(db.Integer, primary_key=True)", "id         = db.Column(db.String(36), primary_key=True)")
content = content.replace("user_id = db.Column(db.Integer, db.ForeignKey('users.id')", "user_id = db.Column(db.String(36), db.ForeignKey('users.id')")
content = content.replace("id      = db.Column(db.Integer, primary_key=True)", "id      = db.Column(db.Integer, primary_key=True, autoincrement=True)")

# 2. Add Supabase JWT logic
supabase_jwt_logic = """
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
"""

# Replace flask_jwt_extended imports with our mock
content = re.sub(r'from flask_jwt_extended import.*?\n(\s+.*?)*', supabase_jwt_logic, content, count=1)
content = re.sub(r'from flask_jwt_extended import.*?\n', '', content)

# Remove old setup
content = re.sub(r'jwt = JWTManager\(app\)', '', content)
content = re.sub(r"jwt_secret = os.getenv\('JWT_SECRET_KEY'.*?app\.config\['JWT_SECRET_KEY'\]\s*=\s*jwt_secret", "", content, flags=re.DOTALL)

# 3. Remove old auth endpoints (send-otp, verify-otp, register, login, refresh)
# Since the python file is huge, we can just patch out the routes by replacing `@app.route('/api/auth/...` with `@app.route('/api/auth/disabled_...`
content = content.replace("@app.route('/api/auth/send-otp'", "@app.route('/api/auth/disabled_send-otp'")
content = content.replace("@app.route('/api/auth/verify-otp'", "@app.route('/api/auth/disabled_verify-otp'")
content = content.replace("@app.route('/api/auth/register'", "@app.route('/api/auth/disabled_register'")
content = content.replace("@app.route('/api/auth/login'", "@app.route('/api/auth/disabled_login'")
content = content.replace("@app.route('/api/auth/refresh'", "@app.route('/api/auth/disabled_refresh'")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.py patched for Supabase UUID and JWTs!")
