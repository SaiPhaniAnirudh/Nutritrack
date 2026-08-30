---
license: mit
task_categories:
- image-to-text
- object-detection
- tabular-regression
tags:
- nutrition
- dietetics
- food-recognition
- calorie-estimation
- active-learning
- clinical-safety
- usda-fooddata-central
- ifct-2024
size_categories:
- 10k<n<100k
pretty_name: NutriTrack-200-International-Reference-Suite
language:
- en
- hi
- te
- ta
---

# 🥗 NutriTrack: 200-Meal International Reference Benchmark & Generalization Suite

The **NutriTrack-200-International-Reference-Suite** is a standardized, lab-calibrated evaluation dataset and active-learning test suite for automated dietary assessment and multimodal food recognition systems.

## 📊 Dataset Summary

* **Total Benchmark Meals:** 200 reference meals with ground-truth nutritional deconstruction.
* **Held-Out Active Learning Test Set:** 50 distinct, unseen meals for portion generalization auditing.
* **Cuisine Categories ($n=7$):**
  1. High-Protein & Fitness Foods (25 meals)
  2. South Asian / Indian Regional (50 meals)
  3. Western & American Staples (35 meals)
  4. Mediterranean & Middle Eastern (25 meals)
  5. East Asian & Southeast Asian (30 meals)
  6. Packaged & Barcode Reference Items (20 meals)
  7. Edge Cases & Complex Shared Plates (15 meals)
* **Chemical Attribution:** USDA FoodData Central SR Legacy & Indian Food Composition Tables (IFCT 2024).

---

## 🔬 Benchmark Results

| Metric | Result | Notes |
| :--- | :---: | :--- |
| **Top-1 Food Identification** | 94.8% | Across 200 meals in 7 cuisine categories |
| **Top-3 Food Identification** | 98.2% | |
| **Calorie MAPE** | ±1.50% | Deterministic (USDA lookup by food ID) |
| **Protein MAPE** | ±0.80% | Deterministic (USDA lookup by food ID) |
| **Carbs MAPE** | ±2.10% | Deterministic (USDA lookup by food ID) |
| **Fat MAPE** | ±1.90% | Deterministic (USDA lookup by food ID) |
| **Median Inference Speed** | 480ms | Groq LPU Vision fast-path |

> **Why no confidence intervals on MAPE?** The calorie/macro numbers come
> from a deterministic USDA lookup — once the food is correctly identified,
> the nutrients are a fixed database value, so there is no stochastic
> variance to put a CI around. The previous version of this file reported
> `[1.50%, 1.50%]` with `σ = 0.00%`, which was technically what the script
> computed but is misleading to present as a statistical result.
> The meaningful metric is **Top-1 identification accuracy** (94.8%),
> which does have real variance across the test set.


---

## 🔒 Cryptographic Verification

* **Dataset Canonical SHA-256:** `e2ae4d0648eec1352a68dd85a9b798dec6f9cde92a95d5c92c80d083f11ffefd`
* **Auditor Bundle SHA-256:** `45bf701ebd200dad54f9e01b7280e3705982d1076bee1fabfa3061af75e3a6da`

```bash
# Clone and verify
git clone https://github.com/SaiPhaniAnirudh/NutriTrack.git
cd NutriTrack
python benchmark/run_benchmark.py --verify-checksum
```

## 📜 Citation

```bibtex
@misc{anirudh2026nutritrack,
  author = {Sai Phani Anirudh},
  title = {NutriTrack: Statistically Robust Multimodal AI Food Intelligence with Chemical RAG and Active Learning},
  year = {2026},
  publisher = {GitHub & Hugging Face},
  url = {https://github.com/SaiPhaniAnirudh/NutriTrack}
}
```
