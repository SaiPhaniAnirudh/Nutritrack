"""
Test live API connectivity for Groq and Gemini engines.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.ai import groq_engine, gemini_engine

print("🔑 Testing Groq API key configuration...")
print(f"  GROQ_API_KEY present: {bool(os.getenv('GROQ_API_KEY'))}")
print(f"  Groq engine available: {groq_engine.is_available()}")

print("🔑 Testing Gemini API key configuration...")
print(f"  GEMINI_API_KEY present: {bool(os.getenv('GEMINI_API_KEY'))}")
print(f"  Gemini engine available: {gemini_engine.is_available()}")
