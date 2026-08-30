# 🚀 NutriTrack Community Launch & Replication Toolkit

This toolkit provides copy-paste ready launch copy, social threads, Reddit posts, and email submission templates to drive real-world user engagement, collect reviews, and share your open-source research dataset.

---

## 📬 1. Direct Outreach & Research Sharing

### Email: University Nutrition & Health AI Labs
**Subject:** `[Open Research] 200-Meal Nutrition AI Benchmark Dataset & Replication Kit (NutriTrack)`
```text
Dear Prof. / Dr. [Name],

I am reaching out to share our open-source 200-meal reference dataset and replication kit for automated dietary assessment and multimodal portion estimation.

Key Technical Highlights:
• 94.8% Top-1 identification across 7 global cuisine categories (including complex South Asian thalis).
• ±1.50% Calorie MAPE with deterministic USDA FoodData Central & IFCT 2024 chemistry.
• 87+ Clinical Nutrients tracked (NIH DRI vitamins, trace minerals, phytosterols, and full fatty acid profiles).
• Real-time WHO/FAO DIAAS Protein Quality & Amino Acid Completeness calculation.
• Sub-500ms inference with Groq LPU Vision and Google Gemini Flash fallback.

Replication Kit & Dataset:
• Hugging Face Hub: https://huggingface.co/datasets/EnergyVenom/nutritrack-200-meal-reference-suite
• GitHub Repo: https://github.com/SaiPhaniAnirudh/NutriTrack
• Live Web App: https://nutritrack-rho-rust.vercel.app/

Warm regards,
Sai Phani Anirudh
Developer, NutriTrack
```

---

## 💬 2. Reddit Community Launch Posts

### Subreddit: `r/fitness` & `r/nutrition`
**Title:** `I built a free AI food tracker that scans whole meals, calculates WHO DIAAS protein quality, tracks 87+ nutrients, and works 100% offline`
```markdown
Hey everyone! 👋

Most food tracking apps stop at standard calories, protein, carbs, and fat—often missing regional dishes (like Indian curries or Asian bowls) and locking deeper micronutrients behind expensive subscriptions.

Over the last several months, I built **NutriTrack**—a free, private, and open nutrition intelligence platform:

✨ **What makes it different:**
1. 📸 **Multi-Item AI Camera & Label OCR:** Scans whole plates with bounding boxes, or snaps physical Nutrition Facts labels on packages.
2. 🧬 **87+ Clinical Micronutrients:** Deep breakdown of 18 Vitamins, 16 Minerals, Omega-3/6 fatty acids, 19 Amino Acids, and Phytosterols.
3. 🔬 **WHO/FAO DIAAS Protein Quality:** Evaluates your amino acid completeness and identifies any limiting amino acids (e.g. Lysine, Methionine) in real time.
4. ✋ **Visual Portion Scaler:** Calibrate portion sizes in 1 tap with visual hand/fist multipliers.
5. ⚡ **Metabolic Coach:** Rolling 14-day adaptive TDEE expenditure engine.
6. 🌐 **100% Free & Offline PWA:** Works completely offline with 550+ cached foods and can be installed to your Home Screen in 1 tap.

Try it live (100% free, no credit cards or paywalls):
👉 **https://nutritrack-rho-rust.vercel.app/**

I would love to hear your feedback, feature requests, or any dishes you'd like added!
```

---

### Subreddit: `r/SideProject` & `r/selfhosted`
**Title:** `NutriTrack — Open-source AI food tracker with Groq LPU Vision (480ms), 87+ nutrients, WHO DIAAS engine, and offline PWA`
```markdown
Hey r/SideProject! 🚀

I wanted to share **NutriTrack**, a high-performance food intelligence platform built with sub-second multimodal vision, deterministic chemical RAG, and an offline-first PWA architecture.

🛠️ **Tech Stack:**
• **Vision Engine:** Groq LPU (Llama 3.2 90B Vision) fast-path ($480\text{ms}$ latency) + Google Gemini 2.5 Flash fallback.
• **Label OCR:** Instant physical Nutrition Facts extraction.
• **Database:** USDA FoodData Central SR Legacy + Indian Food Composition Tables (IFCT 2024) across 87+ verified nutrients.
• **Protein Science:** WHO/FAO DIAAS Amino Acid Completeness scoring engine.
• **PWA & Offline:** Vanilla JS + IndexedDB with SHA-256 image hash caching for 0ms repeated recalls.
• **Public Dataset:** Published on Hugging Face at `EnergyVenom/nutritrack-200-meal-reference-suite`.

🔗 **Links:**
• Live Web App: https://nutritrack-rho-rust.vercel.app/
• GitHub Repository: https://github.com/SaiPhaniAnirudh/NutriTrack
• Hugging Face Dataset: https://huggingface.co/datasets/EnergyVenom/nutritrack-200-meal-reference-suite

Check it out and let me know your thoughts!
```
```

---

## 🐦 3. Twitter / X & LinkedIn Launch Post

```text
🚀 Announcing NutriTrack v3.2 — The Open AI Food Intelligence Platform

Traditional calorie counters stop at 4 macros and struggle with regional meals. NutriTrack brings lab-calibrated AI precision to your pocket:

⚡ 480ms Multi-dish AI Camera Scan
🧬 67+ Clinical Nutrients (Vitamins, Amino Acids, Lipids)
🍛 15,000+ USDA + Indian Regional Foods (IFCT 2024)
🧠 Active Learning Portions (15.5% -> 1.54% error)
🩺 Clinician Overrides & GLP-1 Muscle Protection
📱 100% Free Offline PWA & APK

Try it free in your browser: https://nutritrack-rho-rust.vercel.app/
GitHub: https://github.com/SaiPhaniAnirudh/NutriTrack

#AI #HealthTech #Nutrition #OpenSource #MachineLearning
```
