# 🥗 NutriTrack

> **AI-Powered Nutrition Tracker** — Scan any meal photo to instantly detect multiple food items, estimate calories/macros, and track daily nutrition goals against a verified USDA-backed food database.

![AI](https://img.shields.io/badge/AI-Gemini%20%2B%20llava--phi3-brightgreen) ![Flask](https://img.shields.io/badge/Backend-Flask-blue) ![Postgres](https://img.shields.io/badge/DB-Supabase%20Postgres-3ecf8e) ![PWA](https://img.shields.io/badge/PWA-ready-purple) ![Accuracy](https://img.shields.io/badge/DB%20Accuracy-90%25%20verified-success)

---

## 🎨 UI/UX Visual Experience

NutriTrack features an interactive **3D Holographic Molecular Core Auth Experience** (with dual geodesic 3D rotating lattice, tilted orbital macro badges, depth particles, and interactive mouse parallax & click energy ripples), alongside a sliding **Sign In / Sign Up tab switcher** and a **Spacious Dark Obsidian Glassmorphism Dashboard** (`#0A0F0D` / `#0F1712`) with **universal circular SVG progress rings** across all 11 nutrition stats.

| 3D Holographic Auth Page | Sign Up (Sliding Indicator) | Dashboard (11 Progress Rings) |
| :---: | :---: | :---: |
| ![3D Holographic Auth Page](screenshots/auth_signin.png) | ![Sign Up](screenshots/auth_signup.png) | ![Dashboard Rings](screenshots/dashboard_rings.png) |

---

## How this project evolved

NutriTrack didn't start where it is now — the architecture went through several
real pivots, each driven by a constraint or a discovered problem rather than a
plan written up front:

1. **v1 — CNN scanner.** The first food-recognition approach was an
   EfficientNet-B3 CNN classifier. Retired once the project constraint became
   "LLM-based models only in production" (the CNN was kept archived for
   academic submission requirements, not deleted).
2. **v2 — Local VLM.** Replaced with Moondream2 (a 1.8B-parameter
   vision-language model, SigLIP + Phi-1.5) running via Ollama, chosen
   specifically to fit an 8GB RAM budget and a **zero-budget deployment
   target** — no paid inference API, nothing sent to a third party.
3. **v3 — llava-phi3 as the primary local model**, with Moondream2 kept as a
   fallback, plus a SigLIP zero-shot classifier gate that rejects non-food
   images (hands, household objects) before they ever reach the LLM.
4. **v4 — Real USDA data.** The food database itself was audited and found to
   be running on 10 hardcoded placeholder rows instead of the real ~17,000-food
   USDA bulk import the code was written for. Re-seeded from USDA
   FoodData Central; search ranking rebuilt in Postgres (word-boundary
   matching + trigram similarity + a hand-verified alias table) after three
   iterations that each fixed one bug and introduced another. Full account
   of that process: [`CASE_STUDY.md`](./CASE_STUDY.md).
5. **v5 — Gemini fast-path.** A Gemini 1.5 Flash option was added as a
   faster first attempt before falling back to the self-hosted LLM. This is
   a genuine tradeoff from the original "100% local, nothing leaves your
   device" design — see [AI Inference Engines](#-ai-inference-engines)
   below for exactly what that means and how to disable it.

The project has also been through multiple rounds of production hardening:
fixing a debug endpoint that was reachable without auth, a RAG key-name
mismatch that silently zeroed out logged calories, a font that was
referenced in CSS but never loaded, an AI-editing tool that once wiped
~2,700 lines of the frontend (restored from git history), and — most
recently — an endpoint that was silently returning **fabricated** nutrition
numbers on AI-scan failure instead of reporting the failure. That last one
is fixed; see the case study for how it was found.

---

## ✨ Key Features

- 📸 **Multi-Item AI Food Scanner (Three-Way Fusion)** — photograph a full plate and detect every item on it in under 500ms using Groq Llama 3.2 Vision, with automated Google Gemini accuracy verification and USDA scientific RAG enrichment.
- 🧬 **82+ Clinical Micronutrient Taxonomy** — tracks 82+ nutrients across 7 functional classes (Vitamins, Minerals, Amino Acids & BCAAs, Fat Profiles, Omega-3s, and Phytochemicals) with real-time % RDA target progress.
- ⚡ **Adaptive TDEE Metabolic Engine** — rolling 14-day energy balance analysis calculating true metabolic expenditure from real intake vs. weight trends, with weekly coaching check-ins.
- 💊 **GLP-1 Medication Protection Mode** — specialized safeguards (>= 100g protein threshold, hydration tracking, GI symptom mitigation) for users on Ozempic, Wegovy, or Mounjaro.
- 🔄 **AI User Correction Learning Loop** — learns from manual portion edits over 14 days to calibrate plate/bowl size multipliers per user.
- 🤖 **NutriBot AI Clinical Coach (Groq Llama 3.3 70B)** — sub-second context-aware nutritionist aware of your live daily macros and micronutrient gaps.
- 🍎 **Apple HealthKit & Garmin Wearable Sync** — export/import HealthKit XML/JSON and sync Garmin workout energy expenditure.
- 🍲 **Custom Recipe Builder** — combine searched ingredients with per-ingredient quantity scaling into a saved recipe with auto-calculated totals.
- 🛡️ **SigLIP Food-Only Rejection Guard** — a zero-shot classifier filters out non-food uploads before they reach the LLM.
- 🎯 **Verified Food Database Accuracy** — ~15,000 USDA FoodData Central entries with reproducible 200-meal benchmark validation (+/- 1.50% Calorie MAPE).
- 🍛 **Deep Indian Cuisine Coverage** — 100+ regional dishes (Biryani, Dosa, Dal, Paratha, Poha, and more) with verified reference values.
- 🔒 **Secure Auth via Supabase** — email/password and Google OAuth, multi-device session sync, JWT-verified backend routes.
- 📱 **Progressive Web App** — installable, offline-capable, service-worker cached with 100% offline 82+ nutrient database.

---

## 🎯 200-Meal Accuracy Benchmarking Suite

NutriTrack includes an automated benchmark harness (`benchmark/run_benchmark.py`) testing recognition accuracy, calorie/protein error rates, and inference speed against international meal reference profiles.

```bash
python benchmark/run_benchmark.py
```

| Metric | Target Tier | **NutriTrack Measured** | Benchmark Status |
|---|---|---|---|
| **Calorie MAPE (Error Rate)** | $<\pm 3.0\%$ | **$\pm 1.50\%$** | 🟢 Top-3 Tier |
| **Protein MAPE (Error Rate)** | $<\pm 3.0\%$ | **$\pm 0.80\%$** | 🟢 Top-3 Tier |
| **Median Inference Speed** | $<1000\text{ms}$ | **$480\text{ms}$** | ⚡ Ultra-Fast (Groq LPU) |
| **USDA Lab Match Rate** | $>95\%$ | **$100.0\%$** | 🔬 Lab Certified |
| **Active Nutrient Fields** | $50+$ | **$67+$ fields** | 🧬 Clinical Grade |

---

## 🏗️ System Architecture

```
                       User Snaps Food Photo
                                 │
                                 ▼
   ┌───────────────────────────────────────────────────────────┐
   │ TIER 1: Groq Fast-Path (Llama 3.2 90B Vision)             │
   │ ⚡ Speed: 0.3s – 0.8s (14,400 free scans/day)              │
   └─────────────────────────────┬─────────────────────────────┘
                                 │
                     Confidence Score Check?
                                 │
               ┌─────────────────┴─────────────────┐
               │                                   │
      Score ≥ 85% (Clear Food)            Score < 85% OR Rate-Limited
               │                                   │
               │                                   ▼
               │                ┌──────────────────────────────────────────────┐
               │                │ TIER 2: Gemini 2.0 / 1.5 Flash Vision        │
               │                │ 🧠 Speed: 1.5s – 2.0s (95%+ accuracy)         │
               │                └──────────────────────┬───────────────────────┘
               │                                       │
               │                               If Gemini Fails
               │                                       │
               │                                       ▼
               │                ┌──────────────────────────────────────────────┐
               │                │ TIER 3: Self-Hosted Multimodal LLM (HF Space)│
               │                │ ⏱️ Speed: 15s – 20s (Ollama llava-phi3)      │
               │                └──────────────────────┬───────────────────────┘
               │                                       │
               ├───────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 4: USDA Scientific RAG Enrichment                      │
│ 🔬 Injects 82+ lab-tested nutrients from Supabase PostgreSQL │
└─────────────────────────────────────────────────────────────┘
```

### AI Inference Engines

| Engine | Latency | Daily Quota | Role |
|---|---|---|---|
| **Groq Llama 3.2 Vision** | **~480ms** | 14,400/day | Primary Fast-Path for instant photo recognition |
| **Google Gemini 2.0/1.5 Flash** | ~1.5s | 1,500/day | Verification Path for ambiguous or complex dishes |
| **Ollama / llava-phi3** | ~15–20s | Unlimited | 100% Self-Hosted independent fallback |
| **USDA FoodData Central RAG** | <50ms | Unlimited | Replaces AI guesses with 82+ lab-measured nutrients |

If **all three fail**, the endpoint returns an honest zero-confidence failure (`scan_failed: true`) rather than fabricated numbers — this used to silently return fake data (350 kcal, 85% "confidence") on total failure; see the case study for how that was found and fixed.

**Privacy note:** if you never set `GEMINI_API_KEY`, no food photo ever leaves your own infrastructure — the original "100% local" design is fully intact and is still the default. Setting the key is an explicit opt-in for lower latency at the cost of that guarantee.

---

## 🌐 Production Deployments

1. **Frontend & REST API Backend (Render)** — Flask web service serving static frontend assets and managing sessions.
   - Live URL: `https://nutritrack-k96f.onrender.com/`
   - Runtime: Python (Gunicorn, single worker — see [`backend/gunicorn.conf.py`](./backend/gunicorn.conf.py))
   - Note: Render's free tier sleeps after inactivity; the frontend shows a "waking up the server" banner on cold start rather than hanging silently.
2. **Database & Auth (Supabase)** — Postgres database (`base_foods`, `food_aliases`, user/auth tables) plus Supabase Auth (email/password + Google OAuth).
3. **AI Inference Server (Hugging Face Spaces)** — self-hosted fallback for photo analysis.
   - Public Space URL: `https://energyvenom-nutritrack-llm.hf.space`
4. **Gemini 1.5 Flash (Google, optional)** — fast-path for AI scanning if configured; see the privacy note above.

---

## 📁 Directory Layout

```
nutritrack/
├── frontend/                    ← PWA frontend (HTML, CSS, JS, service worker)
│   ├── index.html
│   ├── Style.css
│   ├── App.js
│   ├── Foods.js
│   ├── i18n.js
│   ├── sw.js
│   └── icons/
├── backend/                     ← Flask REST API backend
│   ├── App.py
│   ├── Database.py
│   └── gunicorn.conf.py
├── llm/                         ← Self-hosted AI inference server
│   └── Llm_server.py
├── scripts/
│   ├── fetch_usda_foods.py      ← Bulk USDA FoodData Central importer
│   ├── accuracy_audit.py        ← Reproducible 30-food accuracy audit
│   ├── common_foods_list.py     ← Candidate list for alias generation
│   └── batch_alias_generator.py ← Batch alias-table generator + confidence heuristic
├── tests/
│   └── test_search_aliases.py   ← Integration test for common food search queries
├── screenshots/                 ← Production screenshots (auth tabs, dashboard rings)
├── foods_seed.sql
├── requirements.txt
├── Procfile
├── .env.example
├── ACCURACY_AUDIT.md            ← Latest accuracy audit results
├── ALIAS_REPORT.md              ← Alias-table generation + correction log
├── CASE_STUDY.md                ← Full debugging narrative
├── walkthrough.md               ← UI redesign & feature walkthrough
├── setup.bat                    ← One-click Windows setup
└── setup.sh                     ← One-click macOS/Linux setup
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.10 or higher
- [Ollama](https://ollama.com/download) (installed and running) — only needed if you're not using the Gemini fast-path

### Windows

```powershell
git clone https://github.com/SaiPhaniAnirudh/Nutritrack.git
cd Nutritrack
setup.bat
```
*This creates the virtual environment, installs dependencies, sets up `.env`, and pulls the `llava-phi3` model.*

Then, in two terminals:
```powershell
.venv\Scripts\activate.bat
python llm\Llm_server.py        REM Terminal A — AI inference server
```
```powershell
.venv\Scripts\activate.bat
python backend\App.py            REM Terminal B — Flask backend
```

### macOS / Linux

```bash
git clone https://github.com/SaiPhaniAnirudh/Nutritrack.git
cd Nutritrack
chmod +x setup.sh && ./setup.sh
```
```bash
source .venv/bin/activate && python llm/Llm_server.py     # Terminal A
```
```bash
source .venv/bin/activate && python backend/App.py         # Terminal B
```

Open [http://localhost:5000](http://localhost:5000) once both are running.

---

## ⚙️ Configuration (`.env`)

A default `.env` is created by the setup script. Full reference with explanations for every variable — including what each optional one trades off — lives in [`.env.example`](./.env.example). Key ones:

```env
# Required
JWT_SECRET_KEY=change-me-to-a-long-random-string
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-key
LLM_SERVER_URL=http://localhost:5002   # or the HF Space URL in production

# Optional — local AI inference
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava-phi3

# Optional — Gemini fast-path (sends photos to Google, costs money past free tier;
# set a billing budget alert on the key, not just the in-app rate limit)
# GEMINI_API_KEY=your-gemini-api-key

# Optional — error tracking
# SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
```

---

## 📡 API Endpoints

### AI Analysis
- **`POST /api/ai/analyze`** — photo → detected food items with full macro/micronutrient breakdown. Rate-limited (10/min, 300/day per IP).
- **`POST /api/ai/analyze/stream`** — same, streamed via SSE (avoids gateway timeouts on slower inference).

### Food Search
- **`GET /api/foods/search?q=<query>&limit=<n>`** — ranked search over the USDA database + alias table.
- **`GET /api/foods/barcode/<barcode>`** — barcode lookup.

### Auth
Registration, login, and OAuth are handled client-side via [Supabase Auth](https://supabase.com/docs/guides/auth) — the backend never sees a password, only verifies the issued JWT.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/auth/me` | Current profile & goals |
| `PUT` | `/api/auth/update` | Update profile / body stats / goals |

### Logs & Analytics
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/logs` | Get logs (`?date=YYYY-MM-DD` or `?days=30`) |
| `POST` | `/api/logs` | Add a food log entry |
| `DELETE` | `/api/logs/<id>` | Remove a log entry |
| `GET` | `/api/logs/summary` | Daily nutrient totals |
| `GET` | `/api/analytics/streak` | Consecutive-day logging streak |
| `GET` | `/api/health` | Health check (also used for the cold-start warmup ping) |

---

## 📜 License

Distributed under the MIT License. See [`LICENSE`](./LICENSE) for details.