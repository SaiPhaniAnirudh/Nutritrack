"""
NutriTrack — NutriBot Conversational AI Nutritionist & App Navigator
Powered by Groq (Llama 3.3 70B Versatile) for sub-second advice + Gemini fallback.

Capabilities:
1. Real-time context awareness of user's live 82+ nutrient intake for today.
2. Clinical advice for macronutrient balancing, meal suggestions, and micronutrient deficiencies.
3. GLP-1 therapy nutrition guidance (muscle mass preservation >=100g protein, hydration reminders).
4. Comprehensive knowledge of ALL NutriTrack app features, tools, and troubleshooting.
"""

import os
import json
import requests
from typing import Dict, Optional

import os
import json
import re
import requests
from typing import Dict, Optional

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "groq/compound", "openai/gpt-oss-20b"]

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest"]

APP_KNOWLEDGE_BASE = """
NUTRITRACK APPLICATION KNOWLEDGE & FEATURE GUIDE:
- 📸 Multi-Item AI Photo Scanner: Accessible from 'Track Food' tab. Powered by a Three-Way Fusion Engine (Groq Vision + Gemini Flash + USDA RAG lab enrichment). Can scan whole multi-dish plates at once.
- 📦 Barcode Scanner: Real-time camera UPC scanning and manual barcode entry for packaged foods.
- 🎙️ Voice Logger: Multi-language voice logging (supports English, Hindi, Telugu, Tamil, and 8 other languages). Users can say e.g. "I had 2 boiled eggs and an apple".
- 🥗 Plan My Diet: Complete personalized nutrition planning with customized macro splits for Non-Veg, Veg, Vegan, and Eggetarian diets.
- ⚡ Adaptive Metabolic Coach & TDEE Engine: Rolling 14-day energy balance analysis (Intake vs. Weight trend) that continuously calculates true metabolic expenditure and provides weekly target check-ins. Click 'Metabolic Coach' in the sidebar to open the check-in modal.
- 💊 GLP-1 Medication Mode: Specialized protection for users taking Ozempic, Wegovy, Mounjaro, or Zepbound. Enforces a >=100g daily protein safety baseline, 2,500ml hydration tracking, and clinical alerts to prevent lean muscle wasting.
- 🧬 82+ Clinical Micronutrients: Expandable dashboard panel with 5 tabs: Vitamins (13), Minerals (9), Fat Profile & Omega-3, Amino Acids & BCAAs (19), and Phytochemicals. Calculates real-time % RDA adequacy from logged meals.
- 🍲 Custom Recipe Builder: Allows searching ingredients, scaling custom gram quantities, and saving combos with auto-calculated macros. Accessible via the recipe modal.
- 📋 Restaurant Menu Scanner: Snaps a picture of physical restaurant menus and extracts dishes with verified nutrition estimates.
- 💧 Water Logger: Quick logging (250ml, 500ml, custom) with daily hydration progress ring.
- 🏋️ Workout Tracker: Logs exercise sessions and active calories burned. Supports syncing with Garmin Connect and Oura Ring.
- 📈 Body Weight Progress Tracker: Interactive weight chart with weekly trend rate calculations.
- 🏅 Achievements & Streaks: Milestone badges and consecutive logging streak tracking.
- 📤 Exports: 82-column clinical CSV spreadsheets and Apple HealthKit JSON/XML exports (Profile page).
- 🌐 100% Offline PWA: Works completely offline with 550+ pre-cached foods and full 82+ nutrient estimates.
"""


def _clean_ai_text(text: str) -> str:
    if not text:
        return ""
    # Strip <think> reasoning tags from models like Qwen or DeepSeek
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()


def generate_nutrition_advice(
    message: str,
    user_context: Dict,
    chat_history: Optional[list] = None
) -> Dict:
    """
    Generate context-aware AI nutrition response using Groq / Gemini.
    """
    system_prompt = f"""You are NutriBot, the brilliant, friendly, and scientifically rigorous AI Clinical Nutritionist & Assistant for NutriTrack.

USER CLINICAL CONTEXT:
- Diet Goal: {user_context.get('diet_goal', 'maintain')}
- Diet Type: {user_context.get('diet_type', 'balanced')}
- Target Calories: {user_context.get('goal_calories', 2000)} kcal | Target Protein: {user_context.get('goal_protein', 150)}g
- Today's Consumed: {user_context.get('consumed_calories', 0)} kcal | Protein: {user_context.get('consumed_protein', 0)}g
- Remaining Today: {user_context.get('rem_calories', 0)} kcal | Protein Remaining: {user_context.get('rem_protein', 0)}g
- GLP-1 Protocol Active: {user_context.get('is_glp1', False)}
- Top Micronutrient Gaps (Low RDA): {user_context.get('nutrient_gaps', 'None reported')}

{APP_KNOWLEDGE_BASE}

INSTRUCTIONS:
1. Directly answer the user's specific request (e.g. workout plan, meal ideas, nutrition breakdown, how to use features).
2. For workout/exercise questions, provide structured workout routines with sets, reps, and target muscle groups.
3. For diet questions, suggest foods that fit within their remaining budget ({user_context.get('rem_calories', 0)} kcal, {user_context.get('rem_protein', 0)}g protein).
4. If the user asks about NutriTrack features (e.g. AI scanner, barcode, Garmin sync, Metabolic Coach), give helpful step-by-step guidance.
5. Format responses with clean bullet points and bold highlights for easy reading.
"""

    # 1. Try Groq fast inference
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        for model_name in GROQ_MODELS:
            try:
                messages = [{"role": "system", "content": system_prompt}]
                if chat_history:
                    for turn in chat_history[-4:]:
                        messages.append(turn)
                messages.append({"role": "user", "content": message})

                res = requests.post(
                    GROQ_CHAT_URL,
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": model_name,
                        "messages": messages,
                        "temperature": 0.5,
                        "max_tokens": 650
                    },
                    timeout=10
                )
                if res.status_code == 200:
                    raw_reply = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                    cleaned_reply = _clean_ai_text(raw_reply)
                    if cleaned_reply:
                        return {"reply": cleaned_reply, "response": cleaned_reply, "source": f"Groq ({model_name})", "success": True}
            except Exception as ge:
                print(f"⚡ Groq {model_name} error: {ge}")
                continue

    # 2. Try Gemini Flash Fallback
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        for gem_model in GEMINI_MODELS:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{gem_model}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": f"{system_prompt}\n\nUser Question: {message}"}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 650
                    }
                }
                res = requests.post(url, json=payload, timeout=10)
                if res.status_code == 200:
                    candidates = res.json().get("candidates", [])
                    if candidates:
                        raw = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        cleaned_reply = _clean_ai_text(raw)
                        if cleaned_reply:
                            return {"reply": cleaned_reply, "response": cleaned_reply, "source": f"Google Gemini ({gem_model})", "success": True}
            except Exception as gme:
                print(f"⚡ Gemini {gem_model} error: {gme}")
                continue

    # 3. Dynamic Intent-Aware Clinical Fallback
    lower_msg = message.lower()
    rem_cal = user_context.get('rem_calories', 500)
    rem_pro = user_context.get('rem_protein', 30)

    if any(k in lower_msg for k in ['workout', 'exercise', 'training', 'gym', 'routine', 'cardio', 'muscle']):
        fallback = (
            f"🏋️ **Recommended Today's Workout Routine:**\n"
            f"• **Warm-up:** 5 mins light jogging / jumping jacks + dynamic arm & hip rotations\n"
            f"• **Exercise 1:** Dumbbell/Barbell Squats — 3 sets × 10–12 reps\n"
            f"• **Exercise 2:** Push-Ups / Dumbbell Bench Press — 3 sets × 10–15 reps\n"
            f"• **Exercise 3:** Dumbbell Romanian Deadlifts / Lunges — 3 sets × 12 reps\n"
            f"• **Exercise 4:** Plank / Core Hollow Hold — 3 sets × 45 secs\n"
            f"• **Cool-down:** 10 mins stretching & foam rolling.\n\n"
            f"💡 *Remember to log this in the **Workout & Activity Tracker** on your Dashboard to credit your burned calories!*"
        )
    elif any(k in lower_msg for k in ['eat', 'dinner', 'lunch', 'breakfast', 'snack', 'food', 'meal', 'suggest']):
        fallback = (
            f"🥗 **Smart Meal Suggestion for Your Budget ({round(rem_cal)} kcal & {round(rem_pro)}g Protein remaining):**\n"
            f"• **High-Protein Option:** Grilled chicken breast / Paneer tikka (150g) with steamed broccoli & quinoa (~380 kcal, 32g protein).\n"
            f"• **Quick Vegetarian Option:** Greek yogurt bowl with mixed berries, chia seeds, and 1 tbsp honey (~240 kcal, 18g protein).\n"
            f"• **Hydration Tip:** Drink a large glass of water 15 minutes before your meal to support healthy digestion."
        )
    elif any(k in lower_msg for k in ['glp', 'ozempic', 'wegovy', 'mounjaro', 'zepbound']):
        fallback = (
            f"💊 **GLP-1 Clinical Protocol Guidance:**\n"
            f"• **Muscle Protection:** Prioritize at least **1.6g–2.0g protein/kg** daily (minimum 100g) across small, frequent meals.\n"
            f"• **Hydration & Electrolytes:** Aim for **2,500ml+ water** daily with sodium/potassium to manage side effects.\n"
            f"• **Fiber Floor:** Ensure 25g+ soluble fiber for optimal gastrointestinal motility."
        )
    elif any(k in lower_msg for k in ['scan', 'photo', 'camera', 'barcode', 'voice']):
        fallback = (
            f"📸 **How to Track Food in NutriTrack:**\n"
            f"• **AI Photo Scanner:** Go to **Track Food** → tap **Camera** or **Choose Photo** → AI scans all dishes and bounding boxes automatically.\n"
            f"• **Barcode Scanner:** Tap **Barcode** in Track Food to scan packaged goods.\n"
            f"• **Voice Logger:** Tap **Voice Log** and speak naturally (e.g. *'I had 2 boiled eggs and oatmeal'*)."
        )
    else:
        fallback = (
            f"You have **{round(rem_cal)} kcal** and **{round(rem_pro)}g protein** remaining today toward your goal! "
            f"You can ask me for custom workout routines, meal ideas, macro breakdowns, or how to use any feature in NutriTrack."
        )

    return {"reply": fallback, "response": fallback, "source": "NutriTrack Clinical Intelligence", "success": True}
