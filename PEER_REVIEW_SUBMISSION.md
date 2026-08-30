# NutriTrack Independent Replication Guide

Instructions for anyone who wants to independently check NutriTrack's
accuracy claims by re-running the benchmark and auditing the ground-truth data.

---

## What we claim (and what you'd be checking)

NutriTrack's internal 200-meal benchmark reports:

| Metric | Our result |
|---|---|
| Top-1 food identification | 94.8% |
| Calorie MAPE | ±1.50% |
| Protein MAPE | ±0.80% |
| Carb MAPE | ±2.10% |
| Fat MAPE | ±1.90% |
| Median inference latency | 480ms |

> **Important caveat:** these numbers come from a benchmark we wrote and ran
> ourselves. The calorie and macro MAPE figures are deterministic (the RAG
> pipeline looks up USDA FoodData Central values, so a given food always
> returns the same nutrients) — meaning variance across runs is near-zero
> by design, not because of extraordinary precision. A previous version of
> this document reported a confidence interval of [1.50%, 1.50%] with
> σ = 0.00%, which is what you get from a deterministic lookup but is
> misleading to present as a statistical result. We removed it rather than
> leave a fake-precision number in place.

**Chemical taxonomy:** 67+ nutrients (vitamins, minerals, amino acids,
omega fatty acids, phytochemicals) mapped to USDA SR Legacy & IFCT 2024.
See [nutrient-count-discrepancy.txt](nutrient-count-discrepancy.txt) for
how this number was verified.

---

## How to reproduce it

### Prerequisites
* Python 3.10+
* Clone the repo and install dependencies

```bash
git clone https://github.com/SaiPhaniAnirudh/Nutritrack.git
cd Nutritrack
pip install -r requirements.txt
```

### Run the benchmark

```bash
# Full 200-meal benchmark
python benchmark/run_benchmark.py --output your_results.json

# Verify dataset integrity (SHA-256 checksum)
python benchmark/run_benchmark.py --verify-checksum
```

The ground-truth dataset (with USDA FDC IDs for traceability) is in
`benchmark/` and also downloadable from the in-app Accuracy Benchmark tab.

---

## What would be most useful from a reviewer

1. **Run the script as-is** and compare your `your_results.json` to ours
   (`benchmark/results.json`). Do the numbers match?

2. **Spot-check the ground-truth values.** Pick 10–20 meals at random and
   look up the USDA FDC IDs in the dataset. Are our reference calories,
   protein, carbs, and fat correct, or did we cherry-pick favorable numbers?

3. **Check for overfitting to the test set.** Are there cuisine categories
   or food types that seem suspiciously absent? Does the 200-meal
   distribution look representative, or does it avoid hard cases?

4. **Try foods not in the benchmark.** Photograph your own meals through
   the [live app](https://nutritrack-rho-rust.vercel.app/) and compare
   the AI estimates to a nutrition label or USDA lookup. The benchmark
   only tests what we chose to include — real-world accuracy on unseen
   foods is the harder (and more honest) test.

---

## Where to find things

| Resource | Location |
|---|---|
| Benchmark script | `benchmark/run_benchmark.py` |
| Ground-truth dataset | `benchmark/results.json` |
| Replication kit docs | `benchmark/REPLICATION_KIT.md` |
| Live app | https://nutritrack-rho-rust.vercel.app/ |
| Validation request (shorter version) | [VALIDATION_REQUEST.md](VALIDATION_REQUEST.md) |

---

## Contact

Questions, findings, or corrections — open an issue on this repo or reach
[@SaiPhaniAnirudh](https://github.com/SaiPhaniAnirudh) directly.
