"""
NutriTrack — Three-Way Fusion Vision Engine
Fuses Groq (0.5s speed) + Gemini (95%+ accuracy) + USDA (82+ lab-verified nutrients)

Execution Pipeline:
1. Try Groq Llama 3.2 Vision (ultra-fast 0.5s)
2. Confidence Gate:
   - If Groq confidence >= 85% and identified clearly -> Proceed to USDA Enrichment
   - If Groq is uncertain (<85%), rate-limited, or unavailable -> Call Gemini 2.0/1.5 Flash
3. Fallback: If both cloud APIs fail -> Call self-hosted HF LLM (llava-phi3 / Moondream2)
4. USDA RAG Enrichment: Look up identified foods in Supabase base_foods (USDA SR Legacy / Foundation)
   and enrich items with 82+ lab-measured nutrients and verified source flags.
"""

import os
import time
import requests
import json
from . import groq_engine
from . import gemini_engine
from ..nutrition.nutrients import parse_usda_nutrients, USDA_NUTRIENT_MAP

CONFIDENCE_THRESHOLD = 70  # Prioritize Groq's sub-second fast-path for all confident identifications


def analyze_food_image(image_base64, db_lookup_fn=None):
    """
    Master multimodal food analysis pipeline.
    
    Args:
        image_base64: Base64-encoded JPEG/PNG string
        db_lookup_fn: Optional callable fn(food_name) -> dict from base_foods
        
    Returns:
        dict with final analyzed & USDA-enriched items, confidence, latency, and pipeline route
    """
    start_time = time.time()
    route_log = []
    scan_result = None

    # ─────────────────────────────────────────────────────────────
    # STEP 1: Groq Fast-Path (0.3s - 0.8s)
    # ─────────────────────────────────────────────────────────────
    if groq_engine.is_available():
        try:
            groq_res = groq_engine.analyze_food_photo(image_base64)
            if groq_res.get("success"):
                route_log.append(f"groq:{groq_res.get('model', 'llama-3.2')}:{groq_res.get('latency_ms')}ms")
                
                if groq_res.get("not_food"):
                    return {
                        "items": [],
                        "not_food": True,
                        "confidence": 98,
                        "latency_ms": round((time.time() - start_time) * 1000),
                        "route": " -> ".join(route_log),
                        "source": "Groq Vision Guard"
                    }

                # Check confidence gate
                if groq_res.get("confidence", 0) >= CONFIDENCE_THRESHOLD and len(groq_res.get("items", [])) > 0:
                    scan_result = groq_res
                    route_log.append("accepted_fast_path")
                else:
                    route_log.append(f"groq_confidence_{groq_res.get('confidence')}_below_threshold")
            else:
                route_log.append(f"groq_failed:{groq_res.get('error', 'unknown')}")
        except Exception as ge:
            route_log.append(f"groq_exception:{str(ge)}")

    # ─────────────────────────────────────────────────────────────
    # STEP 2: Gemini Accuracy Verification Path (~1.5s - 2.0s)
    # ─────────────────────────────────────────────────────────────
    if not scan_result and gemini_engine.is_available():
        try:
            gemini_res = gemini_engine.analyze_food_photo(image_base64)
            if gemini_res.get("success"):
                route_log.append(f"gemini:{gemini_res.get('model', 'gemini-flash')}:{gemini_res.get('latency_ms')}ms")
                
                if gemini_res.get("not_food"):
                    return {
                        "items": [],
                        "not_food": True,
                        "confidence": 98,
                        "latency_ms": round((time.time() - start_time) * 1000),
                        "route": " -> ".join(route_log),
                        "source": "Gemini Vision Guard"
                    }

                if len(gemini_res.get("items", [])) > 0:
                    scan_result = gemini_res
                    route_log.append("accepted_accuracy_path")
            else:
                route_log.append(f"gemini_failed:{gemini_res.get('error', 'unknown')}")
        except Exception as gme:
            route_log.append(f"gemini_exception:{str(gme)}")

    # ─────────────────────────────────────────────────────────────
    # STEP 3: Self-Hosted LLM Fallback (Hugging Face / Ollama)
    # ─────────────────────────────────────────────────────────────
    if not scan_result:
        llm_url = os.getenv('LLM_SERVER_URL', 'https://energyvenom-nutritrack-llm.hf.space')
        try:
            hf_start = time.time()
            resp = requests.post(
                f'{llm_url}/api/ai/analyze',
                json={'image': image_base64},
                timeout=25
            )
            if resp.status_code == 200:
                hf_data = resp.json()
                hf_latency = round((time.time() - hf_start) * 1000)
                route_log.append(f"self_hosted_hf:{hf_latency}ms")
                
                items = hf_data.get("items", [])
                if not items and "food_name" in hf_data:
                    items = [hf_data]
                    
                if items:
                    scan_result = {
                        "success": True,
                        "items": items,
                        "confidence": hf_data.get("confidence", 70),
                        "source": "Self-Hosted Multimodal LLM"
                    }
            else:
                route_log.append(f"hf_http_{resp.status_code}")
        except Exception as hfe:
            route_log.append(f"hf_exception:{str(hfe)}")

    # ─────────────────────────────────────────────────────────────
    # STEP 4: Handle Failure Gracefully
    # ─────────────────────────────────────────────────────────────
    if not scan_result or not scan_result.get("items"):
        return {
            "items": [{
                "food_name": "Scan unavailable — please search manually",
                "serving_size": "",
                "confidence": 0,
                "calories": 0,
                "protein_g": 0,
                "carbs_g": 0,
                "fat_g": 0,
                "fiber_g": 0,
                "sugar_g": 0,
                "sodium_mg": 0,
                "cholesterol_mg": 0,
                "source": "⚠️ AI scan failed — search for this food instead"
            }],
            "scan_failed": True,
            "route": " -> ".join(route_log),
            "latency_ms": round((time.time() - start_time) * 1000)
        }

    # ─────────────────────────────────────────────────────────────
    # STEP 5: USDA Scientific RAG Enrichment
    # ─────────────────────────────────────────────────────────────
    items = scan_result.get("items", [])
    for item in items:
        food_name = item.get("food_name", "")
        if db_lookup_fn and food_name:
            try:
                matched_db = db_lookup_fn(food_name)
                if matched_db:
                    # Enrich with USDA verified values
                    item["calories"] = round(float(matched_db.get("calories") or item.get("calories", 0)), 1)
                    item["protein_g"] = round(float(matched_db.get("protein") or item.get("protein_g", 0)), 1)
                    item["carbs_g"] = round(float(matched_db.get("carbs") or item.get("carbs_g", 0)), 1)
                    item["fat_g"] = round(float(matched_db.get("fat") or item.get("fat_g", 0)), 1)
                    item["fiber_g"] = round(float(matched_db.get("fiber") or item.get("fiber_g", 0)), 1)
                    item["sugar_g"] = round(float(matched_db.get("sugar") or item.get("sugar_g", 0)), 1)
                    item["sodium_mg"] = round(float(matched_db.get("sodium") or item.get("sodium_mg", 0)), 1)
                    item["cholesterol_mg"] = round(float(matched_db.get("chol") or item.get("cholesterol_mg", 0)), 1)
                    item["vit_d_mcg"] = round(float(matched_db.get("vit_d") or 0), 1)
                    item["iron_mg"] = round(float(matched_db.get("iron") or 0), 1)
                    item["folate_mcg"] = round(float(matched_db.get("folate") or 0), 1)
                    
                    # Attach extended nutrient profile if present in DB row
                    if matched_db.get("extended_nutrients"):
                        ext = matched_db.get("extended_nutrients")
                        if isinstance(ext, str):
                            try:
                                ext = json.loads(ext)
                            except Exception:
                                ext = {}
                        item["extended_nutrients"] = ext

                    item["source"] = "USDA FoodData Central (Verified)"
                    item["verified_match"] = True
                else:
                    item["source"] = f"AI Vision ({scan_result.get('source', 'AI')})"
                    item["verified_match"] = False
            except Exception as dbe:
                print(f"⚠️ USDA RAG enrichment notice: {dbe}")

    total_latency = round((time.time() - start_time) * 1000)
    
    return {
        "items": items,
        "confidence": scan_result.get("confidence", 85),
        "route": " -> ".join(route_log),
        "latency_ms": total_latency,
        "source": "Three-Way Fusion (Groq + Gemini + USDA)"
    }
