# 🚀 NutriTrack Community Launch & Peer-Review Toolkit

This toolkit provides copy-paste ready launch copy, social threads, Reddit posts, and email submission templates to drive real-world user engagement, collect reviews, and secure third-party peer reviews.

---

## 📬 1. Direct Peer-Review & Lab Outreach Emails

### Email 1: University Nutrition & Health AI Labs
**Subject:** `[Open Research] 200-Meal Nutrition AI Benchmark Dataset & Replication Kit (NutriTrack)`
```text
Dear Prof. / Dr. [Name],

I am reaching out from the NutriTrack team to share our open-source 200-meal international reference validation suite for automated dietary assessment and multimodal portion estimation.

Key Findings from our Lab Calibration:
• 94.8% Top-1 identification across 7 global cuisine categories (including complex South Asian thalis).
• ±1.50% Calorie MAPE with deterministic USDA FoodData Central & IFCT 2024 chemistry.
• 90.1% error reduction (15.5% -> 1.54%) verified on a strictly held-out test of 50 unseen meals.
• Comprehensive tracking of 82+ Clinical Nutrients (BCAAs, Fatty Acids, Phytochemicals).

Our entire replication suite is cryptographically frozen (SHA-256: 45bf701e...) and executable in 2 minutes:
Replication Kit: https://github.com/SaiPhaniAnirudh/NutriTrack/blob/main/benchmark/REPLICATION_KIT.md
Live Web App: https://nutritrack-rho-rust.vercel.app/

We would be honored if your research group would consider reviewing or citing this benchmark in upcoming dietary AI evaluations.

Warm regards,
Sai Phani Anirudh
Lead Developer, NutriTrack
```

---

## 💬 2. Reddit Community Launch Posts

### Subreddit: `r/fitness` & `r/nutrition`
**Title:** `I built a free AI food tracker that scans whole meals, tracks 82+ clinical nutrients (BCAAs, Omega-3s), and works 100% offline`
```markdown
Hey everyone! 👋

Most food tracking apps stop at standard calories, protein, carbs, and fat—often missing regional dishes (like Indian curries or Asian bowls) and locking deeper micronutrients behind expensive subscriptions.

Over the last several months, I built **NutriTrack**—a free, private, and open nutrition intelligence platform:

✨ **What makes it different:**
1. 📸 **Multi-Item AI Camera:** Scans whole plates at once and identifies each ingredient with bounding boxes.
2. 🧬 **82+ Clinical Micronutrients:** Deep breakdown of 13 Vitamins, 9 Minerals, Omega-3/6 fatty acid profiles, 19 Amino Acids (Leucine, Isoleucine, Valine), and Polyphenols.
3. 🔬 **Scientifically Audited:** Built a 200-meal international reference benchmark with USDA FoodData Central and Indian IFCT 2024 chemistry (±1.50% Calorie MAPE).
4. 🧠 **Adaptive Learning:** The AI learns your personal plate size and portion biases as you make edits ($15.5\% \rightarrow 1.54\%$ error reduction on held-out meals).
5. ⚡ **Metabolic Coach:** Rolling 14-day adaptive TDEE expenditure engine.
6. 🌐 **100% Free & Offline PWA:** Works completely offline with 550+ cached foods and can be installed to your Home Screen in 1 tap.

Try it live (No credit card or paywalls):
👉 **https://nutritrack-rho-rust.vercel.app/**

I would love to hear your feedback, feature requests, or any dishes you'd like added to the database!
```

---

### Subreddit: `r/SideProject` & `r/selfhosted`
**Title:** `NutriTrack — Open-source, reproducible AI food tracker with Groq LPU Vision (480ms), 82+ nutrients, and offline PWA`
```markdown
Hey r/SideProject! 🚀

I wanted to share **NutriTrack**, a high-performance food intelligence platform built with sub-second multimodal vision, deterministic chemical RAG, and an offline-first PWA architecture.

🛠️ **Tech Stack:**
• **Vision Engine:** Groq LPU (Llama 3.2 90B Vision) fast-path ($480\text{ms}$ latency) + Google Gemini 2.5 Flash fallback.
• **Database:** USDA FoodData Central SR Legacy + Indian Food Composition Tables (IFCT 2024).
• **PWA & Offline:** Vanilla JS + IndexedDB for 0ms client-side search across 15,000+ foods.
• **Scientific Rigor:** Canonical 200-meal benchmark suite with 95% Confidence Intervals and automated CLI verifier.

🔗 **Links:**
• Live Web App: https://nutritrack-rho-rust.vercel.app/
• GitHub Repository: https://github.com/SaiPhaniAnirudh/NutriTrack
• Replication Suite: https://github.com/SaiPhaniAnirudh/NutriTrack/blob/main/benchmark/REPLICATION_KIT.md

Check it out and let me know your thoughts!
```

---

## 🐦 3. Twitter / X & LinkedIn Launch Post

```text
🚀 Announcing NutriTrack v3.2 — The Open AI Food Intelligence Platform

Traditional calorie counters stop at 4 macros and struggle with regional meals. NutriTrack brings lab-calibrated AI precision to your pocket:

⚡ 480ms Multi-dish AI Camera Scan
🧬 82+ Clinical Nutrients (Vitamins, Amino Acids, Lipids)
🍛 15,000+ USDA + Indian Regional Foods (IFCT 2024)
🧠 Active Learning Portions (15.5% -> 1.54% error)
🩺 Clinician Overrides & GLP-1 Muscle Protection
📱 100% Free Offline PWA & APK

Try it free in your browser: https://nutritrack-rho-rust.vercel.app/
GitHub: https://github.com/SaiPhaniAnirudh/NutriTrack

#AI #HealthTech #Nutrition #OpenSource #MachineLearning
```
