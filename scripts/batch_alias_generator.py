#!/usr/bin/env python3
"""
NutriTrack — batch_alias_generator.py

Batch-generates food_aliases entries by running each candidate food name
through the existing search_foods_ranked() RPC, validating the top result,
and inserting high-confidence matches as aliases.

This avoids hand-verifying 500+ foods: the algorithm is already correct for
~90% of common foods, so we auto-accept those and flag edge cases.

Usage:
    python scripts/batch_alias_generator.py                  # dry run (report only)
    python scripts/batch_alias_generator.py --insert         # insert accepted aliases
    python scripts/batch_alias_generator.py --stats          # show current alias stats
    python scripts/batch_alias_generator.py --report         # generate detailed report
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# ─── Setup ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("alias_gen")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    log.error("DATABASE_URL not set in .env")
    sys.exit(1)

# Import the food candidate list
sys.path.insert(0, str(ROOT / "scripts"))
from common_foods_list import ALL_FOODS, INDIAN_CUISINE

# ─── Confidence rules ─────────────────────────────────────────────────────────
#
# A match is auto-accepted if:
# 1. The top result has a name that "makes sense" for the query
# 2. It's from a quality data source (SR Legacy or Foundation preferred)
# 3. It has valid calories (not 0, not absurdly high for the category)
#
# Matches that fail these checks get flagged for manual review.

QUALITY_SOURCES = {"usda_sr_legacy", "usda_foundation", "usda_fndds"}

# Branded / restaurant foods to deprioritize
BRAND_INDICATORS = [
    "applebee", "mcdonald", "wendy", "burger king", "subway",
    "taco bell", "chick-fil-a", "pizza hut", "domino",
    "kraft", "nestle", "campbell", "progresso", "stouffer",
    "lean cuisine", "healthy choice", "smart ones",
]

# Calorie sanity ranges per food category (kcal per 100g)
CALORIE_RANGES = {
    "fruit":    (5, 350),      # most fruits 20-100, dried up to 300
    "veg":      (5, 400),      # most vegs 10-80, dried up to 350
    "protein":  (50, 900),     # lean chicken ~165, fatty cuts higher
    "dairy":    (15, 900),     # skim milk ~35, butter ~717
    "grain":    (50, 400),     # cooked rice ~130, bread ~265
    "legume":   (50, 600),     # cooked beans ~130, peanut butter ~588
    "snack":    (50, 700),     # varies widely
    "drink":    (0, 400),      # water 0, juice ~45, milkshake higher
    "fat":      (100, 920),    # oils ~884
    "indian":   (30, 500),     # cooked dishes
    "fastfood": (100, 600),    # prepared foods
    "meal":     (30, 600),     # prepared meals
    "default":  (0, 920),      # catch-all
}


def get_calorie_range(query):
    """Infer expected calorie range from query keywords."""
    q = query.lower()
    for cat, range_ in CALORIE_RANGES.items():
        # Simple keyword matching
        if cat == "fruit" and any(w in q for w in ["fruit", "apple", "banana", "mango", "berry", "melon", "grape"]):
            return range_
        if cat == "veg" and any(w in q for w in ["broccoli", "spinach", "carrot", "potato", "tomato", "cabbage"]):
            return range_
        if cat == "protein" and any(w in q for w in ["chicken", "beef", "pork", "fish", "egg", "shrimp", "lamb"]):
            return range_
        if cat == "dairy" and any(w in q for w in ["milk", "cheese", "yogurt", "cream", "butter", "ghee", "paneer"]):
            return range_
        if cat == "grain" and any(w in q for w in ["rice", "bread", "pasta", "noodle", "oat", "wheat", "flour"]):
            return range_
        if cat == "fat" and any(w in q for w in ["oil", "lard", "shortening"]):
            return range_
        if cat == "drink" and any(w in q for w in ["juice", "tea", "coffee", "soda", "wine", "beer", "water"]):
            return range_
    return CALORIE_RANGES["default"]


def is_branded(name):
    """Check if a food name looks like a branded/restaurant product."""
    name_lower = name.lower()
    return any(brand in name_lower for brand in BRAND_INDICATORS)


def name_relevance(query, result_name):
    """
    Score how relevant the result name is to the query.
    Returns a score 0-1. Higher = more relevant.
    """
    q_words = set(query.lower().split())
    r_words = set(result_name.lower().replace(",", " ").replace("(", " ").replace(")", " ").split())

    if not q_words:
        return 0.0

    # What fraction of query words appear in the result?
    matched = sum(1 for w in q_words if any(w in rw or rw in w for rw in r_words))
    coverage = matched / len(q_words)

    # Bonus for short result names (less noise)
    brevity_bonus = max(0, 1.0 - len(r_words) / 15) * 0.2

    return min(1.0, coverage + brevity_bonus)


# ─── Main logic ───────────────────────────────────────────────────────────────

def process_candidates(conn, dry_run=True, verbose=False):
    """
    Process all food candidates and classify them as:
    - EXISTING: already has an alias
    - ACCEPTED: auto-accepted with high confidence
    - FLAGGED: needs manual review
    - SKIPPED: no match found
    """
    cur = conn.cursor()

    # Get existing aliases
    cur.execute("SELECT alias FROM food_aliases;")
    existing_aliases = {row[0] for row in cur.fetchall()}
    log.info(f"Existing aliases: {len(existing_aliases)}")

    results = {
        "existing": [],
        "accepted": [],
        "flagged": [],
        "skipped": [],
    }
    new_aliases = []

    total = len(ALL_FOODS)
    for i, food in enumerate(ALL_FOODS, 1):
        food_lower = food.lower().strip()

        # Skip if alias already exists
        if food_lower in existing_aliases:
            results["existing"].append(food_lower)
            continue

        # Query the search function
        try:
            cur.execute(
                "SELECT * FROM search_foods_ranked(%s, %s);",
                (food, 5)
            )
            rows = cur.fetchall()
        except Exception as e:
            log.warning(f"  Query error for '{food}': {e}")
            conn.rollback()
            results["skipped"].append((food_lower, "query_error", str(e)))
            continue

        if not rows:
            results["skipped"].append((food_lower, "no_results", ""))
            continue

        # Get column names from cursor description
        col_names = [desc[0] for desc in cur.description]
        top = dict(zip(col_names, rows[0]))

        food_id = top.get("id")
        matched_name = top.get("name", "")
        calories = float(top.get("calories") or 0)
        data_source = top.get("data_source", "unknown")

        # ── Confidence checks ──
        reasons = []

        # Check 1: Is it branded?
        if is_branded(matched_name):
            reasons.append(f"branded: {matched_name}")

        # Check 2: Name relevance
        relevance = name_relevance(food, matched_name)
        if relevance < 0.4:
            reasons.append(f"low_relevance={relevance:.2f}")

        # Check 3: Calorie sanity
        cal_min, cal_max = get_calorie_range(food)
        if calories < cal_min or calories > cal_max:
            reasons.append(f"calories={calories} outside [{cal_min},{cal_max}]")

        # Check 4: Data source quality
        if data_source and data_source not in QUALITY_SOURCES and data_source != "unknown":
            reasons.append(f"source={data_source}")

        if reasons:
            results["flagged"].append({
                "query": food_lower,
                "matched": matched_name,
                "food_id": food_id,
                "calories": calories,
                "source": data_source,
                "reasons": reasons,
            })
        else:
            results["accepted"].append({
                "query": food_lower,
                "matched": matched_name,
                "food_id": food_id,
                "calories": calories,
                "source": data_source,
            })
            new_aliases.append((food_lower, food_id, f"auto-batch: {matched_name[:80]}"))

        if i % 50 == 0:
            log.info(f"  Progress: {i}/{total} ({i/total*100:.0f}%)")

    log.info(f"\n{'='*60}")
    log.info(f"  Results Summary")
    log.info(f"{'='*60}")
    log.info(f"  Total candidates:  {total}")
    log.info(f"  Already aliased:   {len(results['existing'])}")
    log.info(f"  Auto-accepted:     {len(results['accepted'])}")
    log.info(f"  Flagged (review):  {len(results['flagged'])}")
    log.info(f"  Skipped (no hit):  {len(results['skipped'])}")
    log.info(f"{'='*60}")

    # Insert accepted aliases
    if not dry_run and new_aliases:
        log.info(f"\nInserting {len(new_aliases)} new aliases...")
        try:
            execute_values(
                cur,
                "INSERT INTO food_aliases (alias, food_id, note) VALUES %s "
                "ON CONFLICT (alias) DO NOTHING",
                new_aliases,
            )
            conn.commit()
            log.info(f"  [OK] Inserted {len(new_aliases)} aliases successfully!")
        except Exception as e:
            conn.rollback()
            log.error(f"  [FAIL] Insert error: {e}")
    elif dry_run and new_aliases:
        log.info(f"\n  [DRY RUN] Would insert {len(new_aliases)} aliases. "
                 f"Use --insert to execute.")

    return results, new_aliases


def print_flagged(results):
    """Print flagged items for manual review."""
    flagged = results.get("flagged", [])
    if not flagged:
        print("\nNo flagged items!")
        return

    print(f"\n{'='*80}")
    print(f"  FLAGGED ITEMS -- Need Manual Review ({len(flagged)} total)")
    print(f"{'='*80}")
    print(f"{'Query':<30} {'Matched To':<35} {'Cal':>5} {'Reasons'}")
    print(f"{'-'*30} {'-'*35} {'-'*5} {'-'*30}")

    for item in flagged:
        reasons_str = "; ".join(item["reasons"])
        print(f"{item['query']:<30} {item['matched'][:35]:<35} "
              f"{item['calories']:>5.0f} {reasons_str}")


def print_accepted(results, limit=20):
    """Print accepted items sample."""
    accepted = results.get("accepted", [])
    if not accepted:
        print("\nNo accepted items!")
        return

    shown = accepted[:limit]
    print(f"\n{'='*80}")
    print(f"  ACCEPTED ({len(accepted)} total, showing first {len(shown)})")
    print(f"{'='*80}")
    print(f"{'Query':<30} {'Matched To':<40} {'Cal':>5} {'Source'}")
    print(f"{'-'*30} {'-'*40} {'-'*5} {'-'*20}")

    for item in shown:
        print(f"{item['query']:<30} {item['matched'][:40]:<40} "
              f"{item['calories']:>5.0f} {item['source']}")


def show_stats(conn):
    """Show current alias statistics."""
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM food_aliases;")
    total = cur.fetchone()[0]

    cur.execute(
        "SELECT note, COUNT(*) FROM food_aliases "
        "GROUP BY note ORDER BY 2 DESC LIMIT 10;"
    )
    by_note = cur.fetchall()

    cur.execute(
        "SELECT fa.alias, bf.name, bf.calories "
        "FROM food_aliases fa JOIN base_foods bf ON fa.food_id = bf.id "
        "ORDER BY fa.alias LIMIT 20;"
    )
    samples = cur.fetchall()

    print(f"\n{'='*60}")
    print(f"  Food Aliases -- {total} total")
    print(f"{'='*60}")

    print(f"\n  By note type:")
    for note, count in by_note:
        print(f"    {(note or 'null')[:50]:<50} {count:>4}")

    print(f"\n  Sample aliases:")
    print(f"  {'Alias':<30} {'Maps To':<35} {'Cal':>5}")
    print(f"  {'-'*30} {'-'*35} {'-'*5}")
    for alias, name, cal in samples:
        print(f"  {alias:<30} {name[:35]:<35} {cal:>5.0f}")

    cur.close()


def generate_report(results, new_aliases, output_path):
    """Generate a detailed markdown report."""
    accepted = results.get("accepted", [])
    flagged = results.get("flagged", [])
    skipped = results.get("skipped", [])
    existing = results.get("existing", [])

    lines = [
        "# Batch Alias Generation Report",
        "",
        f"**Total candidates:** {len(ALL_FOODS)}",
        f"**Already aliased:** {len(existing)}",
        f"**Auto-accepted:** {len(accepted)}",
        f"**Flagged (review):** {len(flagged)}",
        f"**Skipped (no match):** {len(skipped)}",
        "",
        "## Accepted Aliases",
        "",
        "| Query | Matched To | Calories | Source |",
        "|---|---|---|---|",
    ]

    for item in accepted:
        lines.append(
            f"| {item['query']} | {item['matched']} | "
            f"{item['calories']:.0f} | {item['source']} |"
        )

    lines.extend([
        "",
        "## Flagged (Need Review)",
        "",
        "| Query | Matched To | Calories | Reasons |",
        "|---|---|---|---|",
    ])

    for item in flagged:
        reasons_str = "; ".join(item["reasons"])
        lines.append(
            f"| {item['query']} | {item['matched']} | "
            f"{item['calories']:.0f} | {reasons_str} |"
        )

    if skipped:
        lines.extend([
            "",
            "## Skipped (No Match)",
            "",
        ])
        for alias, reason, detail in skipped:
            lines.append(f"- **{alias}**: {reason} {detail}")

    report_text = "\n".join(lines)
    Path(output_path).write_text(report_text, encoding="utf-8")
    log.info(f"Report written to {output_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch food alias generator")
    parser.add_argument("--insert", action="store_true",
                        help="Actually insert aliases (default is dry run)")
    parser.add_argument("--stats", action="store_true",
                        help="Show current alias stats and exit")
    parser.add_argument("--report", action="store_true",
                        help="Generate a detailed markdown report")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)

    if args.stats:
        show_stats(conn)
        conn.close()
        return

    dry_run = not args.insert
    mode = "DRY RUN" if dry_run else "LIVE INSERT"
    log.info(f"\n{'='*60}")
    log.info(f"  NutriTrack Batch Alias Generator — {mode}")
    log.info(f"  Candidates: {len(ALL_FOODS)} foods")
    log.info(f"{'='*60}\n")

    results, new_aliases = process_candidates(conn, dry_run=dry_run, verbose=args.verbose)

    print_accepted(results, limit=30)
    print_flagged(results)

    if args.report:
        report_path = ROOT / "ALIAS_REPORT.md"
        generate_report(results, new_aliases, report_path)

    conn.close()


if __name__ == "__main__":
    main()
