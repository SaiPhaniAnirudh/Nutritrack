"""
NutriTrack — Groq Vision Engine
Fast-path AI food photo analysis via Groq API (Llama 3.2 Vision)

Speed: ~0.3-0.8 seconds (fastest inference available)
Free tier: 30 RPM, 14,400 requests/day
Cost: $0 on free tier

This module handles:
1. Sending food photos to Groq's Llama 3.2 Vision model
2. Parsing structured JSON responses
3. Confidence scoring for smart routing decisions
"""

import json
import os
import time

import requests

# Groq API configuration
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_VISION_MODEL = "llama-3.2-90b-vision-preview"  # Best vision model on Groq
GROQ_VISION_MODEL_FALLBACK = "llama-3.2-11b-vision-preview"  # Smaller, faster fallback

# Structured prompt for food identification — forces consistent JSON output
GROQ_FOOD_PROMPT = """You are a food nutrition analysis AI. Analyze this food image carefully.

RULES:
- Identify ONLY foods you can clearly and confidently see in the image.
- Do NOT guess or infer foods that aren't visible.
- For each food, estimate portion size and nutrition values per the visible portion.
- Rate your confidence 0-100 based on how clearly you can identify each item.
- If NO food is visible, return {"not_food": true}

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{"items": [{"food_name": "<specific name>", "serving_size": "<e.g. 1 cup, 200g>", "confidence": <0-100>, "calories": <number>, "protein_g": <number>, "carbs_g": <number>, "fat_g": <number>, "fiber_g": <number>, "sugar_g": <number>, "sodium_mg": <number>, "cholesterol_mg": <number>}]}"""


def analyze_food_photo(image_base64, api_key=None):
    """
    Analyze a food photo using Groq's Llama 3.2 Vision model.
    
    Args:
        image_base64: Base64-encoded image string (JPEG/PNG)
        api_key: Groq API key (falls back to GROQ_API_KEY env var)
    
    Returns:
        dict: {
            "success": bool,
            "items": [...],           # Identified food items
            "confidence": int,        # Overall confidence (0-100)
            "latency_ms": int,        # Response time in milliseconds
            "model": str,             # Model used
            "source": "groq"
        }
    """
    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"success": False, "error": "GROQ_API_KEY not configured", "items": []}

    start_time = time.time()
    
    # Try the larger 90B model first, fall back to 11B
    for model in [GROQ_VISION_MODEL, GROQ_VISION_MODEL_FALLBACK]:
        try:
            result = _call_groq_vision(image_base64, api_key, model)
            if result["success"]:
                result["latency_ms"] = round((time.time() - start_time) * 1000)
                result["model"] = model
                result["source"] = "groq"
                return result
        except Exception as e:
            print(f"⚡ Groq {model} error: {e}")
            continue

    return {
        "success": False,
        "error": "All Groq models failed",
        "items": [],
        "latency_ms": round((time.time() - start_time) * 1000),
        "source": "groq",
    }


def _call_groq_vision(image_base64, api_key, model):
    """Make a single Groq vision API call."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": GROQ_FOOD_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1,    # Low temperature = more deterministic
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},  # Force JSON output
    }

    resp = requests.post(
        GROQ_API_URL,
        headers=headers,
        json=payload,
        timeout=10,  # Groq is fast — 10s is generous
    )

    if resp.status_code == 429:
        # Rate limited — return failure so fusion engine tries Gemini
        return {"success": False, "error": "rate_limited", "items": []}

    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "items": []}

    # Parse response
    data = resp.json()
    raw_text = data["choices"][0]["message"]["content"]
    
    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*(.*?)```', raw_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            return {"success": False, "error": "Invalid JSON response", "items": []}

    # Check for not_food response
    if result.get("not_food"):
        return {"success": True, "not_food": True, "items": [], "confidence": 95}

    items = result.get("items", [])
    if not items:
        return {"success": False, "error": "No food items detected", "items": []}

    # Calculate overall confidence (average of all items)
    confidences = [item.get("confidence", 50) for item in items]
    overall_confidence = round(sum(confidences) / len(confidences)) if confidences else 0

    # Normalize item fields
    normalized_items = []
    for item in items:
        normalized_items.append({
            "food_name":      (item.get("food_name") or "Unknown").strip().title(),
            "serving_size":   item.get("serving_size", "1 serving"),
            "confidence":     item.get("confidence", 50),
            "calories":       _safe_float(item.get("calories")),
            "protein_g":      _safe_float(item.get("protein_g")),
            "carbs_g":        _safe_float(item.get("carbs_g")),
            "fat_g":          _safe_float(item.get("fat_g")),
            "fiber_g":        _safe_float(item.get("fiber_g"), 0),
            "sugar_g":        _safe_float(item.get("sugar_g"), 0),
            "sodium_mg":      _safe_float(item.get("sodium_mg"), 0),
            "cholesterol_mg": _safe_float(item.get("cholesterol_mg"), 0),
        })

    return {
        "success": True,
        "items": normalized_items,
        "confidence": overall_confidence,
    }


def _safe_float(val, default=0.0):
    """Safely convert a value to float."""
    if val is None:
        return default
    try:
        return round(float(val), 1)
    except (ValueError, TypeError):
        return default


def is_available():
    """Check if Groq API key is configured."""
    return bool(os.getenv("GROQ_API_KEY"))
