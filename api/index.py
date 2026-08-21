"""
Vercel Serverless Function Entrypoint for NutriTrack Flask Backend API
"""

import sys
from pathlib import Path

# Add root and backend to python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.App import app

# Vercel serverless export
handler = app
