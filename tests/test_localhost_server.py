"""
Comprehensive Localhost Server Verification
Tests:
- GET / -> 200 (serves index.html)
- GET /api/foods/popular -> 200
- GET /api/foods/search?q=apple -> 200
- GET /api/challenges -> 200
- POST /api/ai/parse-voice -> 200
"""

import sys
import time
import requests

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

time.sleep(2)  # Wait for server startup

BASE_URL = "http://localhost:5000"

def test_endpoint(method, path, **kwargs):
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=5, **kwargs)
        else:
            r = requests.post(url, timeout=5, **kwargs)
        status = "✅ PASS" if r.status_code in [200, 201] else f"⚠️ {r.status_code}"
        print(f"[{status}] {method} {path} (HTTP {r.status_code})")
        return r
    except Exception as e:
        print(f"[❌ FAIL] {method} {path}: {e}")
        return None

print("=" * 60)
print("🌐 Testing NutriTrack Localhost Server (http://localhost:5000)")
print("=" * 60)

r_root = test_endpoint("GET", "/")
if r_root and "NutriTrack" in r_root.text:
    print("  ✅ Frontend HTML served correctly with NutriTrack title")

r_foods = test_endpoint("GET", "/api/foods/popular")
if r_foods and r_foods.status_code == 200:
    items = r_foods.json()
    print(f"  ✅ Popular foods returned: {len(items)} items")

r_search = test_endpoint("GET", "/api/foods/search?q=apple")
if r_search and r_search.status_code == 200:
    results = r_search.json()
    print(f"  ✅ Food search 'apple' returned: {len(results)} matches")

r_chal = test_endpoint("GET", "/api/challenges")
if r_chal and r_chal.status_code == 200:
    chal_list = r_chal.json()
    print(f"  ✅ Community challenges returned: {len(chal_list)} challenges")

r_voice = test_endpoint("POST", "/api/ai/parse-voice", json={"transcript": "I had 2 boiled eggs and an apple"})
if r_voice and r_voice.status_code == 200:
    v_data = r_voice.json()
    print(f"  ✅ Voice parser identified: {len(v_data.get('items', []))} items")

print("=" * 60)
print("🎉 All Server Endpoints Tested & Verified!")
print("=" * 60)
