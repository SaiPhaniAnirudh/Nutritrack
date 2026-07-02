"""
NutriTrack — Llm_server.py
Multimodal LLM Inference Server  (v3 — Ollama Edition)

Engine priority:
  1. Ollama Local  — Qwen2-VL-7B  (6-8 s CPU / <2 s GPU, zero API key)  ← PRIMARY
  2. Moondream2    — local 1.8B fallback via transformers

Nutrition data (priority):
  1. Built-in NUTRITION_DB  — 80 common / Indian foods
  2. USDA FoodData Central  — 300k+ foods (needs USDA_API_KEY)
  3. Hardcoded estimates    — 30% confidence floor

Port: 5002

Quick-start (Ollama path — recommended):
    1. Install Ollama  →  https://ollama.com/download
    2. ollama pull qwen2-vl:7b
    3. pip install flask flask-cors flask-limiter python-dotenv requests Pillow
    4. python Llm_server.py
"""

import io, os, re, sys, json, time, base64, argparse, threading, queue
import requests as http_requests
from dotenv import load_dotenv
load_dotenv()
from PIL import Image
from flask import Flask, request, jsonify
from supabase import create_client, Client

# Windows Console Unicode/Emoji support
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  NUTRITION DATABASE  (80 items — Indian + global)
# ──────────────────────────────────────────────────────────────────────────────

NUTRITION_DB = {}

TIPS = {
    'biryani':        'High calorie — pair with raita for balance.',
    'burger':         'High sodium. Grilled over fried saves ~30% calories.',
    'butter chicken': 'Great protein. High fat — moderate your portion.',
    'pizza':          '2 slices is one serving. Thin crust cuts calories by 30%.',
    'pho':            'Lower calorie than ramen. Great protein from broth.',
    'ramen':          'Very high sodium. Ask for light broth if eating out.',
    'french fries':   'Baked fries cut calories by ~40%. Skip extra salt.',
    'dal':            'Excellent plant protein and fiber. Very nutritious.',
    'dosa':           'Fermented — good for gut health. Low calorie without filling.',
    'salad':          'Add protein (egg/chicken/paneer) to keep you fuller longer.',
    'ice cream':      'Treat yourself — just watch portion size.',
    'steak':          'Great protein source. Opt for lean cuts when possible.',
    'chicken nuggets': 'Baked nuggets are lower in fat than fried. Enjoy with sauce in moderation.',
    'potato wedges':   'Baked wedges have skins for fiber. Keep portions balanced.',
}
DEFAULT_TIP = 'A balanced meal includes protein, complex carbs, healthy fats and vegetables.'



# ──────────────────────────────────────────────────────────────────────────────
#  SHARED HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _db_lookup(name: str, confidence: int = 90) -> dict | None:
    """Exact then substring match against NUTRITION_DB."""
    name_l = name.lower().strip()
    if name_l in NUTRITION_DB:
        d = NUTRITION_DB[name_l]
        return _db_row(name, d, confidence=95)
    best_key, best_len = None, 0
    for key in NUTRITION_DB:
        if len(key) < 3:
            continue
        if key in name_l or name_l in key:
            if len(key) > best_len:
                best_key, best_len = key, len(key)
    if best_key:
        return _db_row(name, NUTRITION_DB[best_key], confidence=confidence)
    return None

def _db_row(name: str, d: dict, confidence: int = 90) -> dict:
    return {
        'food_name':      name.strip().title(),
        'serving_size':   d['serving'],
        'confidence':     confidence,
        'calories':       d['cal'],
        'protein_g':      d['pro'],
        'carbs_g':        d['carb'],
        'fat_g':          d['fat'],
        'fiber_g':        d['fiber'],
        'sugar_g':        d['sugar'],
        'sodium_mg':      d['sodium'],
        'cholesterol_mg': d['chol'],
    }

def _fallback_item(name: str) -> dict:
    """Last-resort item with estimate flag."""
    return {
        'food_name':      name.strip().title(),
        'serving_size':   '1 serving (~150g) — estimated',
        'confidence':     30,
        'calories':       200,
        'protein_g':      8,
        'carbs_g':        25,
        'fat_g':          8,
        'fiber_g':        2,
        'sugar_g':        4,
        'sodium_mg':      300,
        'cholesterol_mg': 20,
    }

def _tip(food_name: str) -> str:
    n = food_name.lower()
    return next((v for k, v in TIPS.items() if k in n or n in k), DEFAULT_TIP)


# ──────────────────────────────────────────────────────────────────────────────
#  PIPE-RESPONSE PARSER  (shared by Groq + Ollama engines)
# ──────────────────────────────────────────────────────────────────────────────

def _parse_pipe_response(text: str) -> list:
    """
    Parse lines like:
        Chicken Biryani|350|15|48|12|2|3|480|45|1 plate (300g)
    Returns list of item dicts. Falls back to DB lookup for any unparseable line.
    """
    items = []
    for line in text.strip().split('\n'):
        line = line.strip().lstrip('- •*0123456789.)').strip()
        if not line or 'NOT_FOOD' in line.upper():
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 5:
            try:
                def _n(v, default=0.0):
                    return float(re.sub(r'[^0-9.]', '', v or '') or default)
                item = {
                    'food_name':      parts[0].strip().title(),
                    'calories':       round(_n(parts[1], 0)),
                    'protein_g':      round(_n(parts[2], 0), 1),
                    'carbs_g':        round(_n(parts[3], 0), 1),
                    'fat_g':          round(_n(parts[4], 0), 1),
                    'fiber_g':        round(_n(parts[5], 2), 1) if len(parts) > 5 else 2.0,
                    'sugar_g':        round(_n(parts[6], 3), 1) if len(parts) > 6 else 3.0,
                    'sodium_mg':      round(_n(parts[7], 300))  if len(parts) > 7 else 300,
                    'cholesterol_mg': round(_n(parts[8], 20))   if len(parts) > 8 else 20,
                    'serving_size':   parts[9].strip()          if len(parts) > 9 else '1 serving',
                    'confidence':     88,
                }
                if item['calories'] > 0:
                    items.append(item)
            except (ValueError, IndexError):
                continue
    # If structured parse failed, try DB lookup for any food-like words
    if not items:
        words = re.findall(r'[A-Za-z][a-z]+(?:\s+[a-z]+){0,3}', text)
        seen = set()
        for w in words[:6]:
            w = w.strip().lower()
            if len(w) < 3 or w in seen:
                continue
            seen.add(w)
            hit = _db_lookup(w)
            if hit:
                items.append(hit)
    return items[:9]


# ──────────────────────────────────────────────────────────────────────────────
#  IMAGE RESIZE HELPER  (server-side — faster CPU inference)
# ──────────────────────────────────────────────────────────────────────────────

def _resize_image_b64(b64: str, max_px: int = 512) -> str:
    """
    Resize a base64 JPEG to max_px on the longest side.
    Smaller image = fewer vision tokens = 2-3x faster on CPU.
    Falls back to original if PIL is not installed.
    """
    try:
        from PIL import Image as _PILImage
        import io as _io
        data   = base64.b64decode(b64)
        img    = _PILImage.open(_io.BytesIO(data)).convert('RGB')
        w, h   = img.size
        if max(w, h) > max_px:
            scale  = max_px / max(w, h)
            img    = img.resize((int(w * scale), int(h * scale)), _PILImage.LANCZOS)
        buf = _io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return b64   # PIL not available — use original

# Strict prompt — reduces hallucinations and phantom items
VISION_PROMPT = (
    "Look carefully at this image. List ONLY the food items you can clearly and confidently see.\n"
    "Rules:\n"
    "- DO NOT list food you are guessing or inferring — only what is visibly present.\n"
    "- Use specific names (e.g. 'Chicken Wing' not 'Fried Chicken', 'White Rice' not 'Rice').\n"
    "- If NO food visible: reply NOT_FOOD\n"
    "For each clearly visible food, output exactly one line:\n"
    "FoodName|calories|protein_g|carbs_g|fat_g|fiber_g|sugar_g|sodium_mg|cholesterol_mg|serving_size\n"
    "Output ONLY the data lines. No explanation. Max 5 items."
)


# ──────────────────────────────────────────────────────────────────────────────
#  ENGINE 0 — CLIP ZERO-SHOT FOOD CLASSIFIER  (3-7 s CPU, no API key)
#
#  Uses openai/clip-vit-base-patch32 with zero-shot-image-classification.
#  We provide our own candidate food labels — ALL foods from NUTRITION_DB
#  plus extra Indian, Asian and global foods.
#  No fixed category limit — works for any food we name!
# ──────────────────────────────────────────────────────────────────────────────

# ── Full candidate food list (what CLIP will score the image against) ────────
# These ARE the NUTRITION_DB keys + extra aliases/variants
_CLIP_CANDIDATES = []

# Map candidate label → exact NUTRITION_DB key (for labels that differ)
_CLIP_DB_MAP = {
    'chicken biryani':   'biryani',
    'vegetable biryani': 'biryani',
    'mutton biryani':    'biryani',
    'chana masala':      'chole bhature',
    'kadai paneer':      'paneer tikka',
    'palak paneer':      'paneer tikka',
    'shahi paneer':      'paneer tikka',
    'chapati':           'roti',
    'puri':              'roti',
    'tandoori chicken':  'chicken curry',
    'halwa':             'kheer',
    'jalebi':            'gulab jamun',
    'kulfi':             'ice cream',
    'masala chai':       'lassi',
    'chai':              'lassi',
    'mango lassi':       'mango lassi',
    'dhokla':            'idli',
    'pakora':            'samosa',
    'bhajji':            'samosa',
    'pani puri':         'samosa',
    'hamburger':         'burger',
    'cheeseburger':      'burger',
    'dumplings':         'momos',
    'spring rolls':      'momos',
    'bibimbap':          'fried rice',
    'baklava':           'gulab jamun',
    'spaghetti':         'spaghetti',
    'omelette':          'omelette',
    'cheesecake':        'cheesecake',
    'chocolate cake':    'chocolate cake',
    'apple pie':         'apple pie',
    'donuts':            'donuts',
    'sushi roll':        'sushi',
    'coffee':            'lassi',
    'juice':             'lassi',
    'smoothie':          'lassi',
    'chicken nuggets':   'chicken nuggets',
    'potato wedges':     'potato wedges',
    'nuggets':           'chicken nuggets',
}



# ── Hybrid Cache: Load from Supabase on Startup ───────────────────────────────
def load_nutrition_db():
    global NUTRITION_DB, _CLIP_CANDIDATES
    print("  [Supabase] Connecting to PostgreSQL to load Hybrid Cache...")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("  [Supabase] WARNING: Missing SUPABASE_URL or SUPABASE_KEY in .env")
        return
        
    try:
        supabase: Client = create_client(url, key)
        # Fetch all foods
        response = supabase.table("base_foods").select("*").execute()
        foods = response.data
        
        if not foods:
            print("  [Supabase] WARNING: No foods found in base_foods table.")
            return
            
        NUTRITION_DB.clear()
        _CLIP_CANDIDATES.clear()
        
        for f in foods:
            name = f['name'].lower()
            NUTRITION_DB[name] = {
                'cal': f.get('calories', 0),
                'pro': f.get('protein', 0),
                'carb': f.get('carbs', 0),
                'fat': f.get('fat', 0),
                'fiber': f.get('fiber', 0),
                'sugar': f.get('sugar', 0),
                'sodium': f.get('sodium', 0),
                'chol': f.get('chol', 0),
                'serving': '1 portion'
            }
            _CLIP_CANDIDATES.append(name)
            
        print(f"  [Supabase] SUCCESS: Loaded {len(NUTRITION_DB)} foods into RAM.")
    except Exception as e:
        print(f"  [Supabase] ERROR: Failed to load from database: {e}")

# Call it immediately on module load
load_nutrition_db()


def _scale_confidence(score: float, is_top: bool = False) -> int:
    """Scale raw CLIP softmax score to a user-friendly percentage (0-100)."""
    if is_top:
        if score >= 0.40:
            return min(99, int(92 + (score - 0.40) * 11.6)) # 92% to 99%
        elif score >= 0.15:
            return min(99, int(80 + (score - 0.15) * 48)) # 80% to 92%
        elif score >= 0.05:
            return min(99, int(60 + (score - 0.05) * 200)) # 60% to 80%
        else:
            return min(99, int(max(30, score * 100 * 6)))
    else:
        if score >= 0.25:
            return min(99, int(80 + (score - 0.25) * 25))
        elif score >= 0.08:
            return min(99, int(60 + (score - 0.08) * 117))
        else:
            return min(99, int(max(20, score * 100 * 4)))


def _scale_siglip_confidence(score: float, is_top: bool = False) -> int:
    """Scale raw SigLIP Sigmoid score to a user-friendly percentage (0-100)."""
    if is_top:
        if score >= 0.020:
            return min(99, int(90 + (score - 0.020) * 110))
        elif score >= 0.005:
            return min(99, int(70 + (score - 0.005) * 1333))
        elif score >= 0.001:
            return min(99, int(45 + (score - 0.001) * 6250))
        else:
            return min(99, int(max(30, score * 1000 * 30)))
    else:
        if score >= 0.015:
            return min(99, int(85 + (score - 0.015) * 140))
        elif score >= 0.004:
            return min(99, int(65 + (score - 0.004) * 1818))
        elif score >= 0.0008:
            return min(99, int(40 + (score - 0.0008) * 7812))
        else:
            return min(99, int(max(20, score * 1000 * 25)))


class ViTFoodEngine:
    """
    CLIP zero-shot food classifier — covers ALL foods we define as candidates.

    Uses openai/clip-vit-base-patch32 (zero-shot-image-classification).
    Candidate list includes 100+ foods: biryani, dal, dosa, idli, butter
    chicken, chole bhature, paneer, samosa, pav bhaji, ramen, pizza, burger…

    No fixed categories. Add any food to _CLIP_CANDIDATES to support it.
    ~600 MB model, 3-7 s CPU inference.
    """

    CLIP_MODEL  = 'google/siglip-base-patch16-224'
    FOOD101_MDL = 'nateraw/food'   # fast first-pass: confirms image is food

    def __init__(self):
        self.pipe_clip   = None
        self.pipe_food101 = None
        self.loaded      = False
        self._load()

    def _load(self):
        from transformers import pipeline as hf_pipeline

        # ── Load SigLIP (primary — zero-shot, covers all our foods) ────────────
        print('  [FoodAI] loading SigLIP zero-shot classifier...')
        try:
            self.pipe_clip = hf_pipeline(
                'zero-shot-image-classification',
                model=self.CLIP_MODEL,
            )
            self.loaded = True
            print(f'  [FoodAI] SigLIP ready — {len(_CLIP_CANDIDATES)} food candidates')
        except Exception as e:
            print(f'  [FoodAI] SigLIP failed: {e}')

        # ── Load Food-101 (fast fallback / food-presence check) ──────────────
        print('  [FoodAI] loading nateraw/food (fast fallback)...')
        try:
            self.pipe_food101 = hf_pipeline(
                'image-classification', model=self.FOOD101_MDL, top_k=5)
            if not self.loaded:
                self.loaded = True
            print('  [FoodAI] Food-101 fallback ready')
        except Exception as e:
            print(f'  [FoodAI] Food-101 fallback failed: {e}')

    def _db_name(self, label: str) -> str:
        """Resolve CLIP candidate label to NUTRITION_DB key."""
        label_l = label.lower().strip()
        if label_l in _CLIP_DB_MAP:
            return _CLIP_DB_MAP[label_l]
        # Direct DB match
        if label_l in NUTRITION_DB:
            return label_l
        return label_l

    def predict(self, image_b64: str) -> dict:
        t0 = time.time()
        if not self.loaded:
            raise RuntimeError('Food classifier not loaded')

        raw = base64.b64decode(image_b64.split(',', 1)[1] if ',' in image_b64 else image_b64)
        img = Image.open(io.BytesIO(raw)).convert('RGB')

        # ── SigLIP zero-shot food check ────────────────────────────────────────
        if self.pipe_clip:
            # Use more explicit non-food categories to catch faces, hands, and objects.
            food_check_labels = [
                "a photo of food",
                "a photo of a person's face",
                "a photo of a person",
                "a photo of hands or body parts",
                "a photo of an empty plate or table",
                "a photo of an object that is not food"
            ]
            food_check = self.pipe_clip(img, candidate_labels=food_check_labels)
            is_food_label = food_check[0]['label']
            is_food_score = food_check[0]['score']
            print(f"  [SigLIP] food check: {is_food_label} ({is_food_score*100:.1f}%)")
            
            # Reject if the top match is anything other than food, or if the food confidence is very low.
            if is_food_label != "a photo of food":
                return _not_food('SigLIP/siglip-base-patch16-224', 'image_classifier', int((time.time() - t0) * 1000))

            # ── SigLIP zero-shot: score ALL candidate foods against image ──────────
            clip_results = self.pipe_clip(img, candidate_labels=_CLIP_CANDIDATES, hypothesis_template="a photo of {}")
            elapsed = int((time.time() - t0) * 1000)
            print(f'  [SigLIP] {elapsed}ms — top5: '
                  f'{[(r["label"], round(r["score"]*100,1)) for r in clip_results[:5]]}')

            top_score = clip_results[0]['score']

            # Minimum food confidence floor — if even the best food label scores
            # below this threshold, nothing food-like was meaningfully identified.
            # SigLIP sigmoid scores are typically >0.005 for a clear food match.
            MIN_FOOD_SCORE = 0.002
            if top_score < MIN_FOOD_SCORE:
                print(f'  [SigLIP] top food score {top_score:.5f} below floor {MIN_FOOD_SCORE} → not_food')
                return _not_food('SigLIP/siglip-base-patch16-224', 'image_classifier', elapsed)

            found, seen = [], set()

            for r in clip_results:
                score = r['score']
                if len(found) > 0:
                    # Apply a relative and absolute threshold to secondary items
                    # Increased relative threshold from 0.03 to 0.20 and absolute floor from 0.0005 to 0.002
                    # to prevent low-probability background noise and false positives from being reported.
                    if score < max(top_score * 0.20, 0.002):
                        break
                db_name = self._db_name(r['label'])
                if db_name not in seen:
                    seen.add(db_name)
                    # Scale raw score to user-friendly confidence
                    confidence = _scale_siglip_confidence(score, is_top=(len(found) == 0))
                    found.append((db_name, confidence))
                if len(found) >= 5:
                    break

            print(f'  [SigLIP] selected {len(found)}: {[(f[0], f[1]) for f in found]}')

            if found:
                items = []
                for food_name, confidence in found:
                    hit = _db_lookup(food_name) or _fallback_item(food_name)
                    hit['confidence'] = confidence
                    items.append(hit)
                return _ok_response(items, 'SigLIP/siglip-base-patch16-224', 'image_classifier', elapsed)

        # ── Fallback: Food-101 classifier ────────────────────────────────────
        if self.pipe_food101:
            preds = self.pipe_food101(img)
            elapsed = int((time.time() - t0) * 1000)
            print(f'  [Food101-fallback] {elapsed}ms — {[(p["label"], round(p["score"]*100,1)) for p in preds[:3]]}')
            top = preds[0]['score']
            found, seen = [], set()
            for p in preds:
                if p['score'] < max(top * 0.15, 0.08):
                    break
                name = p['label'].replace('_', ' ')
                if name not in seen:
                    seen.add(name)
                    confidence = _scale_confidence(p['score'], is_top=(len(found) == 0))
                    found.append((name, confidence))
                if len(found) >= 5:
                    break
            if found:
                items = []
                for food_name, confidence in found:
                    hit = _db_lookup(food_name) or _fallback_item(food_name)
                    hit['confidence'] = confidence
                    items.append(hit)
                return _ok_response(items, 'Food101/nateraw-food', 'image_classifier', elapsed)


# ──────────────────────────────────────────────────────────────────────────────
#  ENGINE 2 — OLLAMA  (Qwen2-VL-7B, 6-8 s CPU / <2 s GPU, zero API key)
# ──────────────────────────────────────────────────────────────────────────────

class OllamaEngine:
    """
    Local Ollama inference — Qwen2-VL-7B multimodal model.
    No API key. No HuggingFace token. No internet after first pull.

    Setup (one time):
        1. Install Ollama → https://ollama.com/download
        2. ollama pull qwen2-vl:7b
        3. ollama serve   (auto-starts on most systems)
    """

    DEFAULT_MODEL = 'llava-phi3'

    def __init__(self):
        self.base_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.model    = os.getenv('OLLAMA_MODEL', self.DEFAULT_MODEL)
        self.loaded   = self._check()

    def _check(self) -> bool:
        """Ping Ollama and verify the model is pulled."""
        try:
            r = http_requests.get(f'{self.base_url}/api/tags', timeout=3)
            if r.status_code != 200:
                print(f'  [Ollama] server not responding (status {r.status_code})')
                return False
            models = [m['name'] for m in r.json().get('models', [])]
            # Accept exact match or prefix match (e.g. qwen2-vl:7b == qwen2-vl:7b-instruct-q4_K_M)
            model_base = self.model.split(':')[0]
            found = any(model_base in m for m in models)
            if found:
                matched = next(m for m in models if model_base in m)
                print(f'  [Ollama] ✅ model ready → {matched}')
                return True
            else:
                print(f'  [Ollama] ⚠️  model "{self.model}" not pulled yet.')
                print(f'  [Ollama]    Run: ollama pull {self.model}')
                print(f'  [Ollama]    Available: {models}')
                return False
        except Exception as e:
            print(f'  [Ollama] ❌ not running ({e})')
            print( '  [Ollama]    Install: https://ollama.com/download')
            print(f'  [Ollama]    Then:    ollama pull {self.model}')
            return False

    def _ollama_ask(self, image_b64: str, prompt: str, num_predict: int = 80) -> str:
        """Send a single prompt+image to Ollama and return the text response."""
        resp = http_requests.post(
            f'{self.base_url}/api/generate',
            json={
                'model':      self.model,
                'prompt':     prompt,
                'images':     [image_b64],
                'stream':     False,
                'keep_alive': -1,
                'options': {
                    'temperature': 0.1,
                    'num_predict': num_predict,
                    'num_thread':  os.cpu_count() or 4,
                }
            },
            timeout=720
        )
        if resp.status_code != 200:
            raise RuntimeError(f'Ollama API {resp.status_code}: {resp.text[:200]}')
        return resp.json().get('response', '').strip()

    def _predict_moondream(self, image_b64: str) -> dict:
        """
        Moondream-specific single-step inference for speed.
        Identify foods separated by commas. If no food, reply NOT_FOOD.
        """
        t0 = time.time()

        food_list_raw = self._ollama_ask(
            image_b64,
            'Identify any food or drink items in this image. List them separated by commas. '
            'If no food or drink is visible, reply with NOT_FOOD.',
            num_predict=60
        )
        elapsed = int((time.time() - t0) * 1000)
        print(f'  [Ollama/moondream] {elapsed}ms — {food_list_raw!r}')

        if not food_list_raw.strip() or 'NOT_FOOD' in food_list_raw.upper():
            return _not_food(f'Ollama/{self.model}', 'local_llm', elapsed)

        raw_foods = [p.strip().lower() for p in food_list_raw.split(',')]
        raw_foods = [f for f in raw_foods if 2 < len(f) < 60][:5]
        if not raw_foods:
            raw_foods = [food_list_raw.strip()[:60]]

        items = []
        for food in raw_foods:
            hit = _db_lookup(food) or _fallback_item(food)
            items.append(hit)

        if not items:
            return _not_food(f'Ollama/{self.model}', 'local_llm', elapsed)

        return _ok_response(items, f'Ollama/{self.model}', 'local_llm', elapsed)

    def predict(self, image_b64: str) -> dict:
        t0 = time.time()
        # Strip data-URL prefix
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]

        # Resize image — smaller = fewer vision tokens = faster on CPU
        image_b64 = _resize_image_b64(image_b64, max_px=256)

        # Moondream (1.7B) cannot follow complex pipe-format prompts reliably.
        # Use a simpler two-step approach for it.
        if 'moondream' in self.model.lower():
            return self._predict_moondream(image_b64)

        # ── Larger models (llava-phi3, qwen2-vl, etc.) — structured pipe format ──
        resp = http_requests.post(
            f'{self.base_url}/api/generate',
            json={
                'model':      self.model,
                'prompt':     VISION_PROMPT,
                'images':     [image_b64],
                'stream':     False,
                'keep_alive': -1,
                'options': {
                    'temperature': 0.1,
                    'num_predict': 150,
                    'num_thread':  os.cpu_count() or 4,
                }
            },
            timeout=720   # 12 min — cold start on CPU loads model first
        )
        if resp.status_code != 200:
            raise RuntimeError(f'Ollama API {resp.status_code}: {resp.text[:200]}')

        answer  = resp.json().get('response', '').strip()
        elapsed = int((time.time() - t0) * 1000)
        print(f'  [Ollama] {elapsed}ms — {answer[:80]}')

        if 'NOT_FOOD' in answer.upper():
            return _not_food(f'Ollama/{self.model}', 'local_llm', elapsed)

        items = _parse_pipe_response(answer)
        if not items:
            return _not_food(f'Ollama/{self.model}', 'local_llm', elapsed,
                             tip='Could not parse food. Try a clearer photo.')

        return _ok_response(items, f'Ollama/{self.model}', 'local_llm', elapsed)


# ──────────────────────────────────────────────────────────────────────────────
#  ENGINE 3 — MOONDREAM2  (transformers fallback, 15-30 s CPU)
# ──────────────────────────────────────────────────────────────────────────────

def _install_pyvips_stub():
    """
    pyvips compatibility stub for moondream2 (imported lazily — only when
    MoondreamEngine._load() is called, so numpy is not required otherwise).
    """
    if 'pyvips' in sys.modules:
        return
    import types as _types
    import numpy as _np          # only needed for Moondream fallback
    from PIL import Image as _PILImage

    class _VipsImage:
        def __init__(self, arr):
            self._arr = _np.asarray(arr, dtype=_np.uint8)

        @property
        def width(self):  return self._arr.shape[1]
        @property
        def height(self): return self._arr.shape[0]

        @classmethod
        def new_from_array(cls, arr, **kwargs):
            return cls(_np.asarray(arr, dtype=_np.uint8))

        def resize(self, hscale, vscale=None, **kwargs):
            if vscale is None:
                vscale = hscale
            new_w = max(1, int(round(self.width  * hscale)))
            new_h = max(1, int(round(self.height * vscale)))
            pil = _PILImage.fromarray(self._arr).resize(
                (new_w, new_h), _PILImage.BICUBIC)
            return _VipsImage(_np.asarray(pil, dtype=_np.uint8))

        def numpy(self):
            return self._arr.copy()

        def __array__(self, dtype=None):
            return self._arr if dtype is None else self._arr.astype(dtype)

    _stub = _types.ModuleType('pyvips')
    _stub.Image = _VipsImage
    sys.modules['pyvips'] = _stub


class MoondreamEngine:
    """Local Moondream2 1.8B VLM via transformers (last-resort fallback)."""

    MODEL_ID = 'vikhyatk/moondream2'
    REVISION  = '2025-01-09'
    _MAX_SIDE = 378

    def __init__(self):
        self.model    = None
        self.backend  = None
        self.loaded   = False
        self._hf_token = os.getenv('HF_TOKEN') or os.getenv('HUGGING_FACE_HUB_TOKEN')
        self._load()

    def _load(self):
        print('  [Moondream] loading...')
        _install_pyvips_stub()   # lazily inject pyvips stub before transformers import
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch.nn as _nn
            from transformers.modeling_utils import PreTrainedModel as _PTM
            _orig = _PTM.__dict__.get('__getattr__')
            _nn_ga = _nn.Module.__getattr__
            def _compat(self, name):
                if name == 'all_tied_weights_keys':
                    return {}
                if _orig:
                    return _orig(self, name)
                return _nn_ga(self, name)
            _PTM.__getattr__ = _compat
        except ImportError as e:
            print(f'  [Moondream] transformers not installed: {e}')
            return

        tok_kw = {'token': self._hf_token} if self._hf_token else {}
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.MODEL_ID, revision=self.REVISION,
                trust_remote_code=True, **tok_kw)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.MODEL_ID, revision=self.REVISION,
                trust_remote_code=True, torch_dtype='auto',
                low_cpu_mem_usage=True, **tok_kw)
            self.model.eval()
            try:
                import torch
                torch.set_num_threads(os.cpu_count() or 4)
            except Exception:
                pass
            self.backend = 'transformers'
            self.loaded  = True
            print('  [Moondream] ✅ loaded via transformers')
        except Exception as e:
            print(f'  [Moondream] ❌ load failed: {e}')
            if '401' in str(e):
                self._auth_error = str(e)

    def _decode(self, b64: str) -> Image.Image:
        if ',' in b64:
            b64 = b64.split(',', 1)[1]
        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')
        if max(img.width, img.height) > self._MAX_SIDE:
            ratio = self._MAX_SIDE / max(img.width, img.height)
            img = img.resize(
                (max(1, int(img.width*ratio)), max(1, int(img.height*ratio))),
                Image.LANCZOS)
        return img

    def _ask(self, enc, prompt: str, max_tokens: int = 80) -> str:
        return self.model.answer_question(
            enc, prompt, self.tokenizer,
            num_beams=1, max_new_tokens=max_tokens).strip()

    def predict(self, image_b64: str) -> dict:
        t0 = time.time()
        if not self.loaded:
            return _not_food('Moondream2 (1.8B)', 'error',
                             int((time.time()-t0)*1000),
                             tip='Moondream model not loaded. Install transformers+torch.')
        img = self._decode(image_b64)
        enc = self.model.encode_image(img)

        # Step 1 — is there food?
        is_food = self._ask(enc, 'Is there food or a meal visible? Answer yes or no.', 5)
        if is_food.lower().startswith('no'):
            return _not_food('Moondream2 (1.8B)', 'multimodal_llm',
                             int((time.time()-t0)*1000))

        # Step 2 — what foods?
        food_list_raw = self._ask(
            enc,
            'What food or foods are in this image? '
            'List them separated by commas. Be specific. Maximum 5 foods.',
            60)

        elapsed = int((time.time() - t0) * 1000)
        print(f'  [Moondream] {elapsed}ms — {food_list_raw!r}')

        if not food_list_raw.strip():
            return _not_food('Moondream2 (1.8B)', 'multimodal_llm', elapsed)

        raw_foods = [p.strip().lower() for p in food_list_raw.split(',')]
        raw_foods = [f for f in raw_foods if 2 < len(f) < 60][:5]
        if not raw_foods:
            raw_foods = [food_list_raw.strip()[:60]]

        items = []
        for food in raw_foods:
            hit = _db_lookup(food) or _fallback_item(food)
            items.append(hit)

        if not items:
            return _not_food('Moondream2 (1.8B)', 'multimodal_llm', elapsed)

        return _ok_response(items, 'Moondream2 (1.8B)', 'multimodal_llm', elapsed)


# ──────────────────────────────────────────────────────────────────────────────
#  RESPONSE BUILDERS
# ──────────────────────────────────────────────────────────────────────────────

def _not_food(model: str, mode: str, elapsed: int, tip: str = '') -> dict:
    return {
        'description': 'not_food',
        'items': [],
        'tips':  tip or 'No food detected. Please scan a food item.',
        '_meta': {'model': model, 'mode': mode, 'latency_ms': elapsed,
                  'top9': [], 'multi_food': False, 'rejected': True},
    }

def _ok_response(items: list, model: str, mode: str, elapsed: int) -> dict:
    # Enrich items: fill missing nutrition from DB
    enriched = []
    for it in items:
        if it.get('calories', 0) == 0:
            hit = _db_lookup(it['food_name'])
            if hit:
                it = hit
        enriched.append(it)

    desc = (f"{len(enriched)} foods: {', '.join(i['food_name'] for i in enriched)}"
            if len(enriched) > 1 else
            f"{enriched[0]['food_name']} ({enriched[0].get('confidence', 88)}% confidence)")

    return {
        'description': desc,
        'items':       enriched,
        'tips':        _tip(enriched[0]['food_name']),
        '_meta': {
            'model':      model,
            'mode':       mode,
            'latency_ms': elapsed,
            'top9':       [(i['food_name'], i.get('confidence', 88)) for i in enriched[:9]],
            'multi_food': len(enriched) > 1,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
#  FLASK APP
# ──────────────────────────────────────────────────────────────────────────────

app    = Flask(__name__)
engine = None   # set in __main__

# Rate limiting
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(get_remote_address, app=app,
                      default_limits=['200 per hour'],
                      storage_uri='memory://')
    print('  Rate limiter: active (200 req/hr)')
except ImportError:
    class _NoopLimiter:
        def limit(self, *a, **kw):
            def d(f): return f
            return d
    limiter = _NoopLimiter()


@app.before_request
def _preflight():
    if request.method == 'OPTIONS':
        r = app.make_response('')
        r.headers.update({
            'Access-Control-Allow-Origin':  '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        })
        return r, 204

@app.after_request
def _cors(response):
    response.headers.update({
        'Access-Control-Allow-Origin':  '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    })
    return response


@app.route('/api/health', methods=['GET'])
def health():
    active = type(engine).__name__ if engine else 'none'
    return jsonify({
        'status':  'ok',
        'service': 'NutriTrack AI Server (v3)',
        'engine':  active,
        'loaded':  getattr(engine, 'loaded', False),
        'port':    5002,
    })


@app.route('/api/llm/status', methods=['GET'])
def status():
    return jsonify({
        'loaded':  getattr(engine, 'loaded', False),
        'engine':  type(engine).__name__ if engine else 'none',
        'model':   getattr(engine, 'model', 'unknown'),
        'api_key': 'not required (Ollama/Moondream)',
    })


@app.route('/api/ai/analyze',  methods=['POST'])
@app.route('/api/llm/analyze', methods=['POST'])
@limiter.limit('30 per minute')
def analyze():
    data  = request.get_json() or {}
    image = data.get('image', '')
    if not image:
        return jsonify({'error': 'No image provided'}), 400
    if not engine:
        return jsonify({'error': 'No AI engine loaded'}), 503
    if not getattr(engine, 'loaded', False):
        return jsonify({'error': 'AI engine not ready'}), 503
    try:
        return jsonify(engine.predict(image))
    except Exception as e:
        print(f'  [Engine] error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/analyze/stream', methods=['POST'])
@app.route('/api/llm/analyze/stream', methods=['POST'])
@limiter.limit('30 per minute')
def analyze_stream():
    """
    SSE streaming endpoint — runs inference in a background thread and sends
    keep-alive 'thinking' heartbeats every 10 s to prevent HF's 60-second
    gateway timeout from killing the long-running moondream inference.

    Event stream format:
        data: {"status": "thinking"}   ← heartbeat every 10 s
        data: {"result": {...}}         ← final answer
        data: {"error": "..."}          ← on failure
    """
    from flask import Response, stream_with_context

    data  = request.get_json() or {}
    image = data.get('image', '')
    if not image:
        return jsonify({'error': 'No image provided'}), 400
    if not engine:
        return jsonify({'error': 'No AI engine loaded'}), 503
    if not getattr(engine, 'loaded', False):
        return jsonify({'error': 'AI engine not ready'}), 503

    result_q = queue.Queue()

    def _run():
        try:
            result_q.put(('ok', engine.predict(image)))
        except Exception as exc:
            result_q.put(('err', str(exc)))

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    def _generate():
        while True:
            try:
                status, payload = result_q.get(timeout=10)
                if status == 'ok':
                    yield f'data: {json.dumps({"result": payload})}\n\n'
                else:
                    yield f'data: {json.dumps({"error": payload})}\n\n'
                return
            except queue.Empty:
                # Still thinking — send a heartbeat so HF doesn't close the conn
                yield f'data: {json.dumps({"status": "thinking"})}\n\n'

    return Response(
        stream_with_context(_generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':     'no-cache',
            'X-Accel-Buffering': 'no',   # disable nginx buffering on HF
        }
    )


# ──────────────────────────────────────────────────────────────────────────────
#  AI NUTRITIONIST CHATBOT — /api/ai/chat
# ──────────────────────────────────────────────────────────────────────────────

CHAT_SYSTEM_PROMPT = """You are NutriBot, a friendly and knowledgeable AI nutritionist for NutriTrack.
Your role is to help users understand their nutrition, reach their health goals, and make better food choices.

Guidelines:
- Be warm, encouraging, and concise (2-4 sentences per response)
- Always reference the user's actual food data when relevant
- Give specific, actionable advice
- Use emojis sparingly but effectively 🥗
- If asked something unrelated to nutrition/health/food, politely redirect
- Don't be preachy — be supportive and practical
- For Indian foods, show special knowledge (you know Indian cuisine well)
"""

def _build_chat_context_str(context: dict) -> str:
    """Build a human-readable context string from user data."""
    name  = context.get('user_name', 'there')
    goals = context.get('goals', {})
    logs  = context.get('recent_logs', [])

    lines = [f"User: {name}"]
    if goals:
        lines.append(
            f"Daily Goals: {goals.get('calories', 2000)} kcal, "
            f"{goals.get('protein', 150)}g protein, "
            f"{goals.get('carbs', 250)}g carbs, "
            f"{goals.get('fat', 65)}g fat, "
            f"{goals.get('fiber', 28)}g fiber"
        )

    if logs:
        # Group logs by date for a compact summary
        from collections import defaultdict
        by_date = defaultdict(list)
        for entry in logs:
            by_date[entry['date']].append(entry)

        lines.append("Recent meals (last 7 days):")
        for date in sorted(by_date.keys(), reverse=True)[:3]:
            day_logs  = by_date[date]
            day_cal   = sum(e['cal'] for e in day_logs)
            day_prot  = sum(e['protein_g'] for e in day_logs)
            meal_list = ', '.join(e['food'] for e in day_logs[:4])
            lines.append(f"  {date}: {meal_list} — {round(day_cal)} kcal, {round(day_prot)}g protein")
    else:
        lines.append("No food logged yet today.")

    return '\n'.join(lines)


def _nutribot_ollama(message: str, context: dict) -> str:
    """Call Ollama text model for chat response."""
    ollama_url   = os.getenv('OLLAMA_URL',   'http://localhost:11434')
    # Use a lightweight text model — phi3 or llama3.2 or fall back to the vision model
    chat_model   = os.getenv('OLLAMA_CHAT_MODEL', os.getenv('OLLAMA_MODEL', 'llava-phi3'))

    ctx_str = _build_chat_context_str(context)
    full_prompt = f"{CHAT_SYSTEM_PROMPT}\n\n--- User Data ---\n{ctx_str}\n\n--- User Message ---\n{message}"

    try:
        resp = http_requests.post(
            f'{ollama_url}/api/generate',
            json={
                'model':  chat_model,
                'prompt': full_prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'num_predict': 200,
                    'num_thread':  os.cpu_count() or 4,
                }
            },
            timeout=90
        )
        if resp.status_code == 200:
            return resp.json().get('response', '').strip()
    except Exception as e:
        print(f'  [NutriBot/Ollama] error: {e}')
    return None


def _nutribot_rule_based(message: str, context: dict) -> str:
    """Rule-based fallback when LLM is unavailable."""
    msg   = message.lower()
    goals = context.get('goals', {})
    logs  = context.get('recent_logs', [])
    name  = context.get('user_name', 'there')

    cal_goal  = goals.get('calories', 2000)
    prot_goal = goals.get('protein',  150)

    # Calculate today's totals from logs
    from datetime import date as _date
    today_str = _date.today().isoformat()
    today_logs = [l for l in logs if l.get('date') == today_str]
    today_cal  = sum(l.get('cal', 0) for l in today_logs)
    today_prot = sum(l.get('protein_g', 0) for l in today_logs)

    if any(w in msg for w in ['on track', 'doing', 'how am i', 'progress', 'today']):
        rem_cal = cal_goal - today_cal
        if today_cal == 0:
            return f"Hey {name}! 👋 You haven't logged any food today yet. Log your first meal to start tracking your progress!"
        elif rem_cal > 200:
            return f"You've had {round(today_cal)} kcal so far today — {round(rem_cal)} kcal remaining to hit your {cal_goal} kcal goal. Keep it up! 💪"
        elif rem_cal > 0:
            return f"Almost there, {name}! You've consumed {round(today_cal)} kcal — just {round(rem_cal)} kcal left for today. Great discipline! 🎯"
        else:
            return f"You've hit your calorie goal for today ({round(today_cal)} / {cal_goal} kcal)! Focus on hydration and rest now. 🌟"

    if any(w in msg for w in ['protein', 'muscle', 'gym']):
        rem_prot = prot_goal - today_prot
        if rem_prot > 0:
            return f"You've had {round(today_prot)}g protein so far — you need {round(rem_prot)}g more to hit your {prot_goal}g goal. Try eggs, paneer, dal, or grilled chicken! 🥚"
        else:
            return f"Protein goal hit! You've already consumed {round(today_prot)}g today. Excellent work, {name}! 💪"

    if any(w in msg for w in ['eat', 'dinner', 'lunch', 'breakfast', 'snack', 'what should']):
        remaining = cal_goal - today_cal
        if remaining > 500:
            return f"With {round(remaining)} kcal remaining, try a balanced meal: dal + roti + vegetables, or grilled chicken with rice and salad. Aim for protein + complex carbs! 🍛"
        elif remaining > 200:
            return f"You have about {round(remaining)} kcal left — perfect for a light snack like a fruit bowl, Greek yogurt, or a small handful of nuts. 🍎"
        else:
            return f"You're close to your calorie limit for today! Consider herbal tea, a small fruit, or just water. Great job staying on track! 🌿"

    if any(w in msg for w in ['sodium', 'salt']):
        return f"Your daily sodium goal is {goals.get('sodium', 2300)}mg. Indian home cooking and processed foods are common sources of excess salt. Rinse canned foods and reduce pickles/papad! 🧂"

    if any(w in msg for w in ['fiber', 'digestion', 'gut']):
        return f"Aim for {goals.get('fiber', 28)}g of fiber daily. Dal, vegetables, fruits, and whole grains are excellent sources. Dal + roti is one of the best fiber combinations! 🌾"

    # Default helpful response
    return f"I'm here to help you reach your nutrition goals, {name}! Ask me things like 'Am I on track today?', 'What should I eat for dinner?', or 'How's my protein intake?' 🥗"


@app.route('/api/ai/chat', methods=['POST'])
@limiter.limit('20 per minute')
def nutribot_chat():
    """NutriBot — AI Nutritionist Chatbot endpoint."""
    data    = request.get_json() or {}
    message = (data.get('message') or '').strip()
    context = data.get('context', {})

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    # Try Ollama first, fall back to rule-based
    reply = None
    if engine and getattr(engine, 'loaded', False):
        try:
            reply = _nutribot_ollama(message, context)
        except Exception as e:
            print(f'  [NutriBot] Ollama error: {e}')

    if not reply:
        # Graceful rule-based fallback
        reply = _nutribot_rule_based(message, context)

    return jsonify({
        'reply':  reply,
        'engine': type(engine).__name__ if engine and reply != _nutribot_rule_based(message, context) else 'rule_based',
    })


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--host',         default='0.0.0.0')
    ap.add_argument('--port',         default=5002, type=int)
    ap.add_argument('--engine',       default='auto',
                    choices=['auto', 'vit', 'ollama', 'moondream'],
                    help='Force a specific engine (default: auto = ViT -> Ollama -> Moondream)')
    ap.add_argument('--ollama-model', default=None,
                    help='Override Ollama model name (default: moondream)')
    args = ap.parse_args()

    print()
    print('=' * 62)
    print('  NutriTrack — AI Food Analysis Server  (Ollama Edition)')
    print('=' * 62)

    if args.ollama_model:
        os.environ['OLLAMA_MODEL'] = args.ollama_model

    if args.engine == 'vit':
        engine = ViTFoodEngine()
        if not engine.loaded:
            print('  Failed to load ViT. Check transformers install.')
    elif args.engine == 'ollama':
        engine = OllamaEngine()
        if not engine.loaded:
            print('  Ollama not ready. Run: ollama pull moondream')
    elif args.engine == 'moondream':
        engine = MoondreamEngine()
    else:
        # AUTO priority: ViT (fast, 2-5s) -> Ollama -> Moondream
        print('  Trying ViT food classifier (fast, no API)...')
        vit = ViTFoodEngine()
        if vit.loaded:
            engine = vit
            print('  Engine: ViT/vit-base-patch16-224 (2-5 s CPU, no API)')
        else:
            print('  ViT failed — trying Ollama...')
            ollama = OllamaEngine()
            if ollama.loaded:
                engine = ollama
                print(f'  Engine: Ollama / {os.getenv("OLLAMA_MODEL","moondream")} (slow on CPU)')
            else:
                print('  Ollama not available — trying Moondream2 fallback...')
                md = MoondreamEngine()
                engine = md
                if md.loaded:
                    print('  Engine: Moondream2 (1.8B, ~25 s CPU)')
                else:
                    print('  No engine loaded.')
                    print('  Fix: pip install transformers torch')


    print()
    print('=' * 62)
    print(f'  Ready → http://localhost:{args.port}/api/ai/analyze')
    print('=' * 62)
    print()

    app.run(host=args.host, port=args.port, debug=False)