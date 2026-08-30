# Independent Validation Request — NutriTrack Accuracy Benchmark

I built [NutriTrack](https://nutritrack-rho-rust.vercel.app/), an AI food-photo
nutrition tracker, and ran a 200-meal internal benchmark comparing its calorie/macro
estimates against USDA FoodData Central, IFCT 2024, and manufacturer/QSR nutrition
data. Full methodology and results are in the [README](../README.md#-accuracy-benchmark).

**The results are self-reported** — I wrote the benchmark script and ran it myself,
so I have an obvious incentive for it to look good. I'd genuinely appreciate anyone
willing to independently re-run it and report whether they get comparable numbers.

## What you'd be checking

| Metric (my result) | Value |
|---|---|
| Calorie MAPE | ±1.50% |
| Protein MAPE | ±0.80% |
| Top-1 food ID accuracy | 94.8% |
| Median latency | 480ms |

## How to reproduce it

```bash
git clone https://github.com/SaiPhaniAnirudh/Nutritrack.git
cd Nutritrack
# follow README Quick Start to get the backend + AI server running locally
python benchmark/run_benchmark.py --output results.json
```

The full 200-meal ground-truth dataset (with USDA FDC IDs for traceability) is
downloadable from the in-app Accuracy Benchmark tab, or in `benchmark/` in this repo.

## What would help most

- Running the script as-is and comparing your `results.json` to mine
- Spot-checking a handful of the ground-truth values against USDA FDC directly —
  i.e. checking my reference numbers are right, not just that my code matches them
- Flagging anything that looks like it's overfit to my own test set (cherry-picked
  meals, categories I might have tuned against)

Happy to answer questions or share more detail — open an issue on this repo, or
reach me at [@SaiPhaniAnirudh](https://github.com/SaiPhaniAnirudh).