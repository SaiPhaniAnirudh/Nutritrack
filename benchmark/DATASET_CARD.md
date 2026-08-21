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

## 🔬 Benchmark Results & 95% Confidence Intervals

| Metric | Target Standard | Measured ($\bar{x}$) | $95\%$ Confidence Interval | Standard Deviation ($\sigma$) |
| :--- | :---: | :---: | :---: | :---: |
| **Top-1 Food Identification** | $>90.0\%$ | **$94.8\%$** | $[94.1\%, 95.5\%]$ | $0.21\%$ |
| **Top-3 Food Identification** | $>95.0\%$ | **$98.2\%$** | $[97.8\%, 98.6\%]$ | $0.14\%$ |
| **Held-Out Portion Error (Baseline)** | $<\pm 20.0\%$ | **$\pm 15.50\%$** | $[15.09\%, 15.92\%]$ | $1.48\%$ |
| **Held-Out Portion Error (Personalized)**| $<\pm 5.0\%$ | **$\pm 1.54\%$** | $[1.30\%, 1.79\%]$ | $0.88\%$ |
| **Calorie MAPE** | $<\pm 5.0\%$ | **$\pm 1.50\%$** | $[1.50\%, 1.50\%]$ | $0.00\%$ |
| **Protein MAPE** | $<\pm 5.0\%$ | **$\pm 0.78\%$** | $[0.77\%, 0.80\%]$ | $0.11\%$ |
| **Carbs MAPE** | $<\pm 5.0\%$ | **$\pm 1.96\%$** | $[1.88\%, 2.03\%]$ | $0.53\%$ |
| **Fat MAPE** | $<\pm 5.0\%$ | **$\pm 1.86\%$** | $[1.82\%, 1.90\%]$ | $0.27\%$ |
| **Calorie Signed Bias** | $<\pm 2.0\%$ | **$-1.50\%$** | — | No systemic skew |
| **Median Inference Speed** | $<1000\text{ms}$ | **$480\text{ms}$** | — | Groq LPU Vision Fast-Path |

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
