# NutriTrack — System Architecture

This document describes NutriTrack's actual architecture as implemented in this
repository. Every component and flow below was verified directly against the
code (not copied from commit messages) as of `main` @ `6b6f2b8`.

---

## 1. High-level component diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Browser (PWA, frontend/)                       │
│  index.html · App.js · Style.css · sw.js (offline cache, versioned)    │
│                                                                          │
│  Sidebar nav · Dashboard (11 SVG progress rings + Chart.js macro       │
│  split) · Voice logging (Web Speech API) · 3D holographic auth visual  │
└───────────────┬───────────────────────────────────┬────────────────────┘
                │ REST (JWT bearer)                  │ Auth (Supabase JS SDK)
                ▼                                     ▼
┌────────────────────────────────┐      ┌─────────────────────────────────┐
│   backend/App.py (Flask API)   │      │   Supabase (Postgres + Auth)     │
│   Hosted on Render             │◄─────┤   • base_foods (~15k USDA rows) │
│   46 routes, 9 SQLAlchemy      │ conn │   • food_aliases                │
│   models, gunicorn 2 workers   │      │   • Auth: email/password + OAuth│
└───────┬─────────────────┬──────┘      └─────────────────────────────────┘
        │                 │
        │ (if no          │ (photo scan /
        │  GEMINI_API_KEY) │  menu analysis)
        ▼                 ▼
┌───────────────────┐   ┌──────────────────────────────┐
│ Gemini 1.5 Flash   │   │ llm/Llm_server.py             │
│ (optional, cloud,  │   │ Hugging Face Spaces            │
│  paid, fast-path)  │   │ Ollama: llava-phi3 → Moondream2│
└───────────────────┘   └──────────────────────────────┘
                │
                ▼
        ┌───────────────┐
        │    Sentry      │  ← error tracking, all 3 services
        └───────────────┘
```

---

## 2. Backend surface (verified counts)

- **46 `@app.route` endpoints** across auth, food logs, water, weight, meal
  templates, challenges, workouts, AI (voice parse, chat, photo analysis,
  menu analysis), analytics, and Google Fit integration.
- **9 SQLAlchemy models**: `User`, `FoodLog`, `WaterLog`, `WeightLog`,
  `MealTemplate`, `Challenge`, `ChallengeParticipant`, `WorkoutLog`,
  `GoogleFitToken`.
- **32 of 46 routes** are wrapped in `@db_retry` (every route that touches
  the database except `/api/health`, which already self-handles its own DB
  check and never lets the exception propagate).

## 3. Reliability layer

Two independent hardening mechanisms, each catching a different failure
mode of the same underlying cause — Render's free-tier Postgres dropping
idle SSL connections:

| Mechanism | Where it runs | What it catches |
|---|---|---|
| `@db_retry` decorator | Wraps each route function body | An SSL/connection error that occurs **during** a query inside the request. Rolls back, retries once, returns a `503` with a clean error message if the retry also fails. |
| `teardown_appcontext` hook | Registered right after `db = SQLAlchemy(app)`, runs before Flask-SQLAlchemy's internal teardown (Flask calls these in reverse registration order) | An SSL error that occurs **after** the response has already been sent successfully, when Flask tears down the session. `@db_retry` structurally cannot catch this since it's outside the route function entirely. |

This split exists because a single incident (Sentry `PYTHON-FLASK-5`) showed
the first mechanism alone doesn't cover every failure point — the error can
happen after a 200 OK response has already gone out, during connection
cleanup rather than query execution.

Other standing reliability fixes:
- Null-guarded `.isoformat()` calls across all 8 models with timestamp
  fields, after a `NoneType` crash on rows with a `NULL` `logged_at`.
- A watchdog timeout on the frontend's initial auth check, so a hung or
  slow-waking Supabase connection shows a message instead of a silent blank
  page.

## 4. Key user flows

### 4a. Manual food logging
`Track Food` page → `/api/foods/search` (ranked search against
`base_foods`/`food_aliases` in Supabase) → user selects an item →
`POST /api/logs` → `FoodLog` row created → dashboard re-fetches and
re-renders rings + macro chart.

### 4b. Voice food logging
Browser's native `SpeechRecognition` / `webkitSpeechRecognition` API
transcribes speech client-side (no audio ever leaves the browser) → the
Voice Waveform HUD shows live levels during capture → transcript text is
sent to `POST /api/ai/parse-voice`, which does **regex-based extraction**
(splitting on "and"/"with"/"plus"/commas, stripping quantity words) and
looks up each extracted phrase against `base_foods` — this step is
rule-based, not an LLM call.

### 4c. Photo food scanning
Photo → `POST /api/ai/analyze` (or the streaming variant) → if
`GEMINI_API_KEY` is set, Gemini 1.5 Flash is tried first as a fast-path
(~1–2s, cloud, opt-in); otherwise falls back to the self-hosted
`llm/Llm_server.py` on Hugging Face Spaces, which tries `llava-phi3` via
Ollama first (~15–20s CPU) and `Moondream2` as a secondary fallback
(~30s+ CPU). If all inference paths fail, the endpoint returns an honest
`scan_failed: true` rather than fabricated nutrition numbers.

### 4d. Dashboard rendering
On `showPage('dashboard')`, `refreshDashboard()` computes today's totals
from logged data, then updates 11 circular SVG progress rings (4 primary
macros + 7 secondary micronutrients, via a shared `_dpRing()` helper) and
redraws the Chart.js-based 3D Macro Split doughnut chart in the same pass.

## 5. Deployment topology

| Component | Host | Notes |
|---|---|---|
| Frontend + Flask API | Render | Single Gunicorn service, 2 workers, serves both the static PWA and the REST API. Free tier sleeps after inactivity — frontend shows a "waking up" banner on cold start. |
| Database + Auth | Supabase | Postgres (`base_foods`, `food_aliases`, user data) + Supabase Auth (email/password, Google OAuth). |
| AI inference fallback | Hugging Face Spaces | Self-hosted `llm/Llm_server.py`, no API key required. |
| Gemini 1.5 Flash | Google (optional) | Opt-in fast-path; if never configured, no photo ever leaves the user's own infrastructure. |
| Error tracking | Sentry | Covers backend (Flask) and is the source of the reliability fixes documented above. |

---

*This document reflects verified code state, not commit-message claims —
several prior commit messages in this repo's history overstated their
actual scope, so facts here were confirmed by reading the corresponding
route/model/frontend code directly rather than trusting the log.*
