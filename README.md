# 🥗 NutriTrack — AI Food Intelligence

> **AI-powered nutrition tracking PWA.** Snap a photo of your meal and let a locally-run vision-language model identify it, log macros and 67+ micronutrients, and keep you on track — no manual food search required.

[![Live App](https://img.shields.io/badge/Live-nutritrack--rho--rust.vercel.app-3ecf8e)](https://nutritrack-rho-rust.vercel.app/)
[![AI](https://img.shields.io/badge/AI-llava--phi3-brightgreen)](https://ollama.com)
[![Backend](https://img.shields.io/badge/Backend-Flask-blue)](https://flask.palletsprojects.com/)
[![PWA](https://img.shields.io/badge/PWA-ready-purple)](https://web.dev/progressive-web-apps/)
[![CI](https://github.com/SaiPhaniAnirudh/Nutritrack/actions/workflows/ci.yml/badge.svg)](https://github.com/SaiPhaniAnirudh/Nutritrack/actions/workflows/ci.yml)
[![Hugging Face Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-nutritrack--200--meal--suite-ffd21e)](https://huggingface.co/datasets/EnergyVenom/nutritrack-200-meal-reference-suite)
[![Monitored with Sentry](https://img.shields.io/badge/monitored%20with-Sentry-362d59?logo=sentry&logoColor=white)](https://sentry.io)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

**Live app:** https://nutritrack-rho-rust.vercel.app/
**Hugging Face Dataset:** https://huggingface.co/datasets/EnergyVenom/nutritrack-200-meal-reference-suite
**Try it:** first load can take up to ~60s — the free-tier backend spins down when idle.

---

## ✨ What it does

- 📸 **AI Meal Scanner** — photograph a plate; a vision-language model (Ollama `llava-phi3`, SigLIP zero-shot food-only guard, Moondream2 fallback) identifies multiple food items in one shot and estimates calories, protein, carbs, fat, fiber, sugar, sodium, and cholesterol.
- 🧬 **67+ nutrient tracking** — vitamins, minerals, amino acids, omega-3/6 fat profile, and phytochemicals, referenced against USDA FoodData Central, IFCT 2024, and NIN Hyderabad composition tables. *(See [nutrient-count-discrepancy.txt](nutrient-count-discrepancy.txt) for audit notes on how this number was verified.)*

- 📦 **Barcode scanning** — live camera UPC lookup for packaged foods, backed by Open Food Facts.
- 🎙️ **Voice logging** — natural-language meal entry ("2 scrambled eggs, avocado toast and black coffee") parsed into structured food logs.
- ⚡ **Adaptive Metabolic Coach** — calibrates true TDEE from logged history and recommends weekly calorie/macro targets, with a GLP-1 medication protection mode enforcing minimum protein/hydration.
- 🩺 **Clinician Mode** — lets a registered dietitian/physician lock individualized calorie floors and CKD-style protein caps.
- ⌚ **Wearable sync** — Google Fit, Apple HealthKit export/import, Garmin Connect, and Oura activity sync feed into daily energy balance.
- 🏅 **Gamification** — streaks, achievement badges, shareable progress cards, community challenges.
- 🌐 **Multi-language UI** — English, Hindi, Telugu, Tamil, Spanish.
- 📱 **Installable PWA + Android APK** — offline-capable home-screen app.
- 🔬 **Open accuracy benchmark** — a reproducible 200-meal validation suite across 7 cuisine categories (see [Accuracy Benchmark](#-accuracy-benchmark) below).

---

## 🔬 Accuracy Benchmark

A 200-meal internal reference suite (High-Protein/Fitness, South Asian/Indian, Western/American, Mediterranean, East Asian, Packaged/Barcode, Edge Cases) evaluated against USDA FDC, IFCT 2024, and manufacturer/QSR nutrition data:

| Metric | Result |
|---|---|
| Calorie MAPE | ±1.50% |
| Protein MAPE | ±0.80% |
| Carb MAPE | ±2.10% |
| Fat MAPE | ±1.90% |
| Top-1 food ID accuracy | 94.8% |
| Median latency | 480ms |

> **Note on methodology:** these numbers come from an internal benchmark script (`benchmark/run_benchmark.py`) that anyone can run and audit — not a third-party lab. The full dataset (ground-truth values + USDA FDC IDs) is downloadable in-app for independent replication. Treat this as a reproducible self-report, not an independently certified result, until an outside party reproduces it.

```bash
python benchmark/run_benchmark.py --output results.json
```

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                       Browser / PWA                       │
└─────────────────────────────┬───────────────────────────-─┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────┐
│           backend/App.py (Flask REST API Server)          │
│   Auth (JWT) · Food logs · Analytics · Supabase (RAG DB)   │
└─────────────────────────────┬──────────────────────────-──┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────┐
│           llm/Llm_server.py (AI Inference Hub)             │
│   Ollama llava-phi3 · SigLIP food guard · Moondream2 fallback│
└──────────────────────────────────────────────────────────┘
```

## 🌐 Production Deployments

> **Error tracking:** the backend integrates Sentry (`sentry-sdk[flask]`) for exception and
> performance monitoring in production. Enabled automatically when a `SENTRY_DSN` environment
> variable is set on the deploy target (Render); no-ops cleanly in local development without it.

| Layer | Host | URL |
|---|---|---|
| Frontend | Vercel | https://nutritrack-rho-rust.vercel.app/ |
| Backend API | Render | https://nutritrack-k96f.onrender.com/ |
| AI Inference | Hugging Face Spaces | https://energyvenom-nutritrack-llm.hf.space |
| Auth/RAG DB | Supabase | — |

> Render's free tier sleeps after inactivity — the backend can take up to ~60s to wake on first request. A keep-alive workflow (`.github/workflows/keepalive.yml`) pings it periodically to reduce cold starts during active use.

## 🤖 AI Inference Engines

| Engine | Latency | Accuracy | Cloud/Local | Config |
|---|---|---|---|---|
| Ollama / llava-phi3 | ~15–20s (CPU) / <2s (GPU) | ~85% (high) | 100% local option | None (default) |
| Moondream2 | ~30s+ (CPU) | ~50% (low) | 100% local | `HF_TOKEN` (fallback) |

---

## 📁 Directory Layout

```
nutritrack/
├── frontend/     ← PWA UI (HTML, CSS, JS, service worker)
├── backend/      ← Flask REST API (App.py, Database.py)
├── llm/          ← AI inference server (Llm_server.py)
├── docker/       ← Container configs
├── benchmark/    ← 200-meal accuracy validation suite
├── requirements.txt
├── docker-compose.yml
└── setup.bat / setup.sh
```

## 🚀 Quick Start (Local Development)

**Prerequisites:** Python 3.10+, [Ollama](https://ollama.com/download) installed and running.

```bash
git clone https://github.com/SaiPhaniAnirudh/Nutritrack.git
cd Nutritrack

# Windows
setup.bat
# macOS/Linux
chmod +x setup.sh && ./setup.sh
```

Then, in two terminals:
```bash
# Terminal A — AI server
python llm/Llm_server.py
# Terminal B — Flask backend
python backend/App.py
```
Open http://localhost:5000.

### Docker

```bash
docker compose up -d          # start Ollama + Flask API + AI server
docker compose logs -f        # watch logs
docker compose down           # stop
```

---

## 📡 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/ai/analyze` | Photo → identified food items + macros |
| `POST` | `/api/auth/register` / `/login` | Auth |
| `GET`/`POST` | `/api/logs` | Fetch/create food log entries |
| `GET` | `/api/logs/summary` | Macro summary over a date range |
| `GET` | `/api/analytics/streak` | Consecutive logging streak |

---

## 📜 License

MIT — see [LICENSE](LICENSE).

📚 Nutrition data: [USDA FoodData Central](https://fdc.nal.usda.gov/) (public domain), [Open Food Facts](https://world.openfoodfacts.org) (ODbL).