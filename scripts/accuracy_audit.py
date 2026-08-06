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

# Reference values are per standard USDA serving, sourced from
# USDA FoodData Central (SR Legacy / Foundation entries).
# tuple: (query, ref_calories, ref_protein_g, ref_carbs_g, ref_fat_g, serving)
REFERENCE_FOODS = [
    ("banana",            105, 1.3, 27.0, 0.4, "1 medium (118g)"),
    ("boiled egg",         78, 6.3,  0.6, 5.3, "1 large (50g)"),
    ("white rice cooked", 205, 4.3, 44.5, 0.4, "1 cup (158g)"),
    ("chicken breast",    165, 31.0, 0.0, 3.6, "100g cooked"),
    ("whole milk",        149, 7.7, 11.7, 8.0, "1 cup (244g)"),
    ("almonds",            164, 6.0,  6.1, 14.2, "1 oz (28g)"),
    ("broccoli",            55, 3.7, 11.2, 0.6, "1 cup (91g)"),
    ("apple",               95, 0.5, 25.1, 0.3, "1 medium (182g)"),
    ("peanut butter",      188, 8.0,  6.9, 16.0, "2 tbsp (32g)"),
    ("white bread",         79, 2.7, 14.7, 1.0, "1 slice (28g)"),
    ("oatmeal cooked",     166, 5.9, 28.1, 3.6, "1 cup (234g)"),
    ("cheddar cheese",     113, 7.0,  0.4, 9.3, "1 oz (28g)"),
    ("salmon",             206, 22.1, 0.0, 12.4, "100g cooked"),
    ("potato baked",       161, 4.3, 36.6, 0.2, "1 medium (173g)"),
    ("greek yogurt plain", 100, 17.3,  6.1, 0.7, "170g container"),
    ("avocado",            234, 2.9, 12.5, 21.4, "1 medium (150g)"),
    ("orange",              62, 1.2, 15.4, 0.2, "1 medium (131g)"),
    ("spinach raw",          7, 0.9,  1.1, 0.1, "1 cup (30g)"),
    ("ground beef 80/20",  287, 19.9, 0.0, 21.8, "100g cooked"),
    ("black beans cooked", 227, 15.2, 40.8, 0.9, "1 cup (172g)"),
    ("brown rice cooked",  216, 5.0, 44.8, 1.8, "1 cup (195g)"),
    ("olive oil",           119, 0.0,  0.0, 13.5, "1 tbsp (13.5g)"),
    ("carrot raw",           25, 0.6,  5.8, 0.1, "1 medium (61g)"),
    ("tofu firm",           181, 21.8, 2.3, 11.0, "1 cup (252g)"),
    ("shrimp cooked",       84, 20.4,  0.0, 0.5, "3 oz (85g)"),
    ("whole wheat bread",   69, 3.6, 12.0, 0.9, "1 slice (28g)"),
    ("cottage cheese",      98, 11.1,  3.4, 4.3, "1/2 cup (113g)"),
    ("sweet potato baked", 103, 2.3, 23.6, 0.2, "1 medium (114g)"),
    ("walnuts",              185, 4.3,  3.9, 18.5, "1 oz (28g)"),
    ("lentils cooked",     230, 17.9, 39.9, 0.8, "1 cup (198g)"),
]

TOLERANCE_PCT = 5.0  # matches the "within 5% of USDA reference" bar used industry-wide


def pct_diff(actual, ref):
    if ref == 0:
        return 0.0 if actual == 0 else 100.0
    return abs(actual - ref) / ref * 100.0


def run_audit(base_url: str):
    results = []
    for query, ref_cal, ref_pro, ref_carb, ref_fat, serving in REFERENCE_FOODS:
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
            "ref_serving": serving,
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