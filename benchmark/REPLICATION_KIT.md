# NutriTrack Independent Accuracy Replication Kit v3.2

This document provides independent reviewers, academic researchers, and third-party auditors with everything required to autonomously replicate NutriTrack's 200-meal accuracy metrics and chemical database attribution.

---

## 🔒 1. Dataset Integrity & Cryptographic Checksum

| Property | Value |
| :--- | :--- |
| **Dataset Name** | `NutriTrack-200-International-Reference-Suite-v3` |
| **Sample Size ($n$)** | 200 lab-calibrated reference meals |
| **Cuisine Categories** | 7 global categories (South Asian, High-Protein, Western, Mediterranean, East Asian, Packaged, Edge Cases) |
| **Ground Truth Sources** | USDA FoodData Central SR Legacy, IFCT 2024, NIN Hyderabad |
| **Dataset Canonical SHA-256** | `e2ae4d0648eec1352a68dd85a9b798dec6f9cde92a95d5c92c80d083f11ffefd` |

### Verify Dataset Integrity Locally:
```bash
python benchmark/run_benchmark.py --verify-checksum
```

---

## 🧪 2. Replicating the Benchmark

### Prerequisites:
* Python 3.10+
* Dependencies: `pip install -r requirements.txt`

### Execute Automated Test Suite:
```bash
# 1. Run full 200-meal audit with 95% Confidence Intervals
python benchmark/run_benchmark.py

# 2. Export machine-readable results JSON
python benchmark/run_benchmark.py --output benchmark/results.json
```

---

## 📊 3. Expected Baseline Results

Independent reviewers running this benchmark should observe numbers close to:

| Metric | Our result | Notes |
| :--- | :---: | :--- |
| **Calorie MAPE** | ±1.50% | Deterministic USDA lookup — no stochastic variance |
| **Protein MAPE** | ±0.80% | Deterministic USDA lookup |
| **Carbohydrates MAPE** | ±2.10% | Deterministic USDA lookup |
| **Fat MAPE** | ±1.90% | Deterministic USDA lookup |
| **USDA Chemical Match** | 100.0% | Expected: the benchmark checks its own ground truth |
| **Median Inference Speed** | 480ms | Will vary by hardware and network |

> **On determinism:** The macro MAPE values are near-deterministic because
> they come from a USDA food-ID lookup, not a model prediction. The
> interesting metric is Top-1 food identification accuracy (94.8% in our
> run), which has real variance. A previous version of this file reported
> confidence intervals with σ = 0 — those were technically what the script
> computed but misleading to present as statistical results, so we removed
> them.


---

## 🌐 4. Public Endpoints for Live Replay

External auditors can query live platform endpoints without authentication:

* **Public Benchmark Metrics (v3.2):** `GET /api/benchmark/public`
* **Raw Dataset Download (JSON):** `GET /api/benchmark/download`
* **Raw Dataset Download (CSV):** `GET /api/benchmark/download?format=csv`
* **Active Learning Convergence Metrics:** `GET /api/ai/learning-metrics`
* **Clinical Safety Decision Audit Trail:** `GET /api/clinical/audit-log`
* **Endpoint Observability & P95 Latency:** `GET /api/observability`
* **Database Categorization & Taxonomy Stats:** `GET /api/database/stats`

---

## 🔬 5. Versioned Research Artifact Specifications

| Component | Version / Specification | Checksum / Hash |
| :--- | :--- | :--- |
| **Dataset Version** | `NutriTrack-200-International-Reference-Suite-v3` | `SHA-256: e2ae4d0648eec1352a68dd85a9b798dec6f9cde92a95d5c92c80d083f11ffefd` |
| **Evaluation Script** | `benchmark/run_benchmark.py (v3.2.4)` | Integrated Student-t & Bootstrap 95% CIs |
| **Held-Out Test Suite** | `tests/test_active_learning_heldout.py (v1.0)` | 50 unseen evaluation meals |
| **Primary Vision Engine** | `Groq LPU (Llama-3.2-90B-Vision-Preview)` | Fixed temperature $T=0.1$ |
| **Fallback Multimodal** | `Google Gemini 2.5 Flash` | Fixed temperature $T=0.2$ |
| **Database Chemistry** | `USDA FoodData Central SR Legacy & IFCT 2024` | 67+ verified nutrient taxonomy |
| **Runtime Environment** | Python 3.10+ on Ubuntu / Windows / macOS | Lockfile: `requirements.txt` |

---

## 🏛️ 6. Attribution & Licensing
* **Reference Data:** USDA FoodData Central (Public Domain) & IFCT 2024
* **Harness Code:** MIT License &copy; 2026 Sai Phani Anirudh

