"""
NutriTrack — Tests for Image Hash Deduplication Cache
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from ai.fusion_engine import _IMAGE_HASH_CACHE, analyze_food_image


def test_image_hash_cache_instant_recall():
    test_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    # Mock a cached item
    import hashlib
    h = hashlib.sha256(test_b64.encode('utf-8')).hexdigest()
    _IMAGE_HASH_CACHE[h] = {
        "items": [{"food_name": "Test Avocado Toast", "calories": 320, "protein_g": 12}],
        "confidence": 99,
        "source": "Three-Way Fusion"
    }

    res = analyze_food_image(test_b64)
    assert res["cached"] is True
    assert res["latency_ms"] < 20
    assert res["items"][0]["food_name"] == "Test Avocado Toast"
