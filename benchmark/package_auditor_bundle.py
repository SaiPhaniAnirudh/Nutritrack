#!/usr/bin/env python3
"""
NutriTrack — Standalone External Auditor & Replication Packager
Bundles the benchmark suite, held-out active learning test, checksum verification,
and standalone instructions into a self-contained distribution zip for third-party reviewers.

Usage:
    python benchmark/package_auditor_bundle.py
"""

import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
import zipfile
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)
BUNDLE_ZIP = DIST_DIR / "nutritrack-replication-suite-v3.2.zip"

FILES_TO_BUNDLE = [
    ("benchmark/run_benchmark.py", "run_benchmark.py"),
    ("benchmark/REPLICATION_KIT.md", "REPLICATION_KIT.md"),
    ("benchmark/results.json", "reference_results.json"),
    ("tests/test_active_learning_heldout.py", "test_active_learning_heldout.py"),
    ("benchmark/active_learning_heldout_results.json", "heldout_results.json"),
    ("CLINICAL_SAFETY.md", "CLINICAL_SAFETY.md"),
    ("requirements.txt", "requirements.txt"),
]

AUDITOR_README = """# NutriTrack Independent Reviewer & Audit Bundle v3.2

Welcome to the independent verification package for NutriTrack. This bundle contains everything required to autonomously reproduce all reported accuracy and clinical safety metrics without access to private infrastructure.

## Quickstart Verification (2 Minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Verify dataset integrity (SHA-256)
python run_benchmark.py --verify-checksum

# 3. Execute full 200-meal benchmark with 95% Confidence Intervals
python run_benchmark.py --output my_replicated_results.json

# 4. Execute held-out active learning generalization audit (50 unseen meals)
python test_active_learning_heldout.py
```

## Expected Verification Standards ($n=200$)

* **Dataset Canonical SHA-256:** `e2ae4d0648eec1352a68dd85a9b798dec6f9cde92a95d5c92c80d083f11ffefd`
* **Calorie MAPE:** $\pm 1.50\%$ $[95\%\\text{ CI: } 1.50\% - 1.50\%]$
* **Protein MAPE:** $\pm 0.78\%$ $[95\%\\text{ CI: } 0.77\% - 0.80\%]$
* **Held-Out Active Learning Error:** $\pm 1.54\%$ on 50 unseen meals ($90.1\%$ error reduction)

For detailed methodology, refer to `REPLICATION_KIT.md` and `CLINICAL_SAFETY.md`.
"""

def create_bundle():
    print("=" * 70)
    print("📦 NutriTrack Standalone Auditor Package Builder")
    print("=" * 70)

    with zipfile.ZipFile(BUNDLE_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add auditor README
        zf.writestr("AUDITOR_INSTRUCTIONS.md", AUDITOR_README)
        print("  ➕ Added AUDITOR_INSTRUCTIONS.md")

        for src_rel, arcname in FILES_TO_BUNDLE:
            src_path = ROOT / src_rel
            if src_path.exists():
                zf.write(src_path, arcname=arcname)
                print(f"  ➕ Added {arcname} (from {src_rel})")
            else:
                print(f"  ⚠️ Warning: {src_rel} not found, skipping.")

    # Compute bundle SHA-256
    with open(BUNDLE_ZIP, "rb") as f:
        bundle_hash = hashlib.sha256(f.read()).hexdigest()

    size_kb = BUNDLE_ZIP.stat().st_size / 1024
    print("=" * 70)
    print(f"✅ Standalone bundle created successfully!")
    print(f"📁 Path: {BUNDLE_ZIP}")
    print(f"📊 Size: {size_kb:.1f} KB")
    print(f"🔒 Bundle SHA-256: {bundle_hash}")
    print("=" * 70)

    return BUNDLE_ZIP, bundle_hash


if __name__ == "__main__":
    create_bundle()
