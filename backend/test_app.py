"""
Minimal smoke tests for the NutriTrack backend.

These don't test business logic yet — they verify the app boots cleanly
and the health endpoint responds, which is enough to catch import errors,
syntax errors, and broken dependencies in CI before they reach Render.

Run locally:
    pip install -r requirements.txt
    pip install pytest
    pytest backend/test_app.py -v

No environment variables are required to run these tests: SUPABASE_URL
is left unset, so the app falls back to its "Supabase not configured"
path, and DATABASE_URL defaults to a local SQLite file.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import pytest

try:
    from App import app, db
except ImportError:
    from backend.App import app, db


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        yield client


def test_app_boots():
    """The Flask app object should exist and be importable without crashing."""
    assert app is not None


def test_health_check_returns_ok(client):
    """GET /api/health should return 200 with status 'ok'."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'


def test_unknown_api_route_returns_404(client):
    """Unknown /api/* routes should 404, not fall through to the SPA handler."""
    response = client.get('/api/this-route-does-not-exist')
    assert response.status_code == 404


def test_protected_route_requires_auth(client):
    """Auth-gated routes should reject requests with no Authorization header."""
    response = client.get('/api/auth/me')
    assert response.status_code in (401, 500)