#!/usr/bin/env python3
"""
NutriTrack — accuracy_audit.py

Tests NutriTrack's /api/foods/search (or /lookup) endpoint against a
30-item generic-food reference set, using the same "% within 5% of
USDA reference" methodology used in public MyFitnessPal/Cronometer
audits. Produces a markdown report you can publish alongside the repo.

Usage:
    python scripts/accuracy_audit.py                # hits live Render API
    python scripts/accuracy_audit.py --base-url http://localhost:5000
"""

import argparse
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

# Reference values are per 100g (matching NutriTrack's DB convention, which
# stores USDA values per 100g) — sourced from USDA FoodData Central
# (SR Legacy / Foundation entries).
# tuple: (query, ref_calories_per_100g, ref_protein, ref_carbs, ref_fat)
REFERENCE_FOODS = [
    ("banana",             89, 1.1, 22.8, 0.3),
    ("boiled egg",        155, 12.6, 1.1, 10.6),
    ("white rice cooked", 130, 2.7, 28.2, 0.3),
    ("chicken breast",    120, 22.5, 0.0, 2.6),
    ("whole milk",          61, 3.2,  4.8, 3.3),
    ("almonds",            579, 21.2, 21.6, 49.9),
    ("broccoli",             34, 2.8,  6.6, 0.4),
    ("apple",                52, 0.3, 13.8, 0.2),
    ("peanut butter",      588, 25.1, 20.0, 50.4),
    ("white bread",         265, 9.0, 49.0, 3.2),
    ("oatmeal cooked",       71, 2.5, 12.0, 1.5),
    ("cheddar cheese",     403, 24.9,  1.3, 33.1),
    ("salmon",              206, 22.1, 0.0, 12.4),
    ("potato baked",         93, 2.5, 21.1, 0.1),
    ("greek yogurt plain",   59, 10.2,  3.6, 0.4),
    ("avocado",             167, 2.0,  8.5, 15.4),
    ("orange",                47, 0.9, 11.8, 0.1),
    ("spinach raw",           23, 2.9,  3.6, 0.4),
    ("ground beef 80/20",   254, 17.2, 0.0, 20.0),
    ("black beans cooked",  132, 8.9, 23.7, 0.5),
    ("brown rice cooked",   123, 2.6, 25.6, 1.0),
    ("olive oil",           884, 0.0,  0.0, 100.0),
    ("carrot raw",            41, 0.9,  9.6, 0.2),
    ("tofu firm",            144, 15.8, 3.0, 8.7),
    ("shrimp cooked",         99, 24.0, 0.2, 0.3),
    ("whole wheat bread",   247, 13.0, 41.0, 3.5),
    ("cottage cheese",        98, 11.1,  3.4, 4.3),
    ("sweet potato baked",    90, 2.0, 20.7, 0.2),
    ("walnuts",             654, 15.2, 13.7, 65.2),
    ("lentils cooked",      116, 9.0, 20.1, 0.4),
]

TOLERANCE_PCT = 5.0  # matches the "within 5% of USDA reference" bar used industry-wide


def pct_diff(actual, ref):
    if ref == 0:
        return 0.0 if actual == 0 else 100.0
    return abs(actual - ref) / ref * 100.0


def run_audit(base_url: str):
    results = []
    for query, ref_cal, ref_pro, ref_carb, ref_fat in REFERENCE_FOODS:
        try:
            r = requests.get(f"{base_url}/api/foods/search",
                              params={"q": query, "limit": 1}, timeout=15)
            r.raise_for_status()
            hits = r.json()
        except Exception as e:
            results.append({"query": query, "found": False, "error": str(e)})
            continue

        if not hits:
            results.append({"query": query, "found": False})
            continue

        item = hits[0]
        cal_diff = pct_diff(item.get("cal", 0), ref_cal)
        pass_ = cal_diff <= TOLERANCE_PCT

        results.append({
            "query": query,
            "found": True,
            "matched_name": item.get("name"),
            "ref_cal": ref_cal,
            "actual_cal": item.get("cal"),
            "cal_diff_pct": round(cal_diff, 1),
            "pass": pass_,
        })
        time.sleep(0.2)  # be polite to the free-tier backend

    return results


def write_report(results, base_url):
    n = len(results)
    found = [r for r in results if r.get("found")]
    passed = [r for r in found if r.get("pass")]

    report = [
        "# NutriTrack Database Accuracy Audit",
        "",
        f"Tested against: `{base_url}`",
        f"Methodology: {n}-item generic-food audit, USDA FoodData Central reference values, "
        f"pass = within {TOLERANCE_PCT}% of reference calories (same bar used in public "
        "MyFitnessPal/Cronometer comparisons).",
        "",
        f"**Result: {len(passed)}/{n} within {TOLERANCE_PCT}% "
        f"({len(found)}/{n} found at all)**",
        "",
        "| Query | Matched to | Ref kcal | Actual kcal | Diff % | Pass |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        if not r.get("found"):
            report.append(f"| {r['query']} | — NOT FOUND — | | | | ❌ |")
            continue
        mark = "✅" if r["pass"] else "❌"
        report.append(
            f"| {r['query']} | {r['matched_name']} | {r['ref_cal']} | "
            f"{r['actual_cal']} | {r['cal_diff_pct']}% | {mark} |"
        )

    report.append("")
    report.append(f"_Generated {time.strftime('%Y-%m-%d')}_")

    out_path = ROOT / "ACCURACY_AUDIT.md"
    out_path.write_text("\n".join(report), encoding="utf-8")
    return out_path, len(passed), len(found), n


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://nutritrack-k96f.onrender.com")
    args = parser.parse_args()

    print(f"Running {len(REFERENCE_FOODS)}-item accuracy audit against {args.base_url} ...")
    results = run_audit(args.base_url)
    out_path, passed, found, n = write_report(results, args.base_url)
    print(f"\n{passed}/{n} passed (within {TOLERANCE_PCT}%), {found}/{n} found in database")
    print(f"Report written to {out_path}")