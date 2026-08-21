# NutriTrack Clinical Safety & Medical Guardrails Protocol

**Version:** 1.0 (August 2026)  
**Classification:** Non-Diagnostic Nutritional Intelligence & Educational Platform  

---

## 🛡️ 1. Core Safety Boundaries

NutriTrack operates under strict programmatic health guardrails to prevent harmful dietary suggestions, extreme caloric deficits, and nutrient deficiencies:

### 1.1 Caloric Deficit Floor
* **Female Absolute Minimum:** $1,200\text{ kcal/day}$
* **Male Absolute Minimum:** $1,500\text{ kcal/day}$
* **Rule Enforcement:** If user-selected weight-loss rates imply a daily intake below these thresholds, the metabolic engine clamps recommendations to the safety floor and warns the user about metabolic slowdown and micronutrient insufficiency risks.

### 1.2 GLP-1 Agonist Protection Mode (Semaglutide / Tirzepatide)
* **Protein Target Threshold:** Clamped to $\ge 100\text{g/day}$ (or $\ge 1.2\text{–}1.5\text{g/kg}$ lean body mass) to protect against lean muscle mass catabolism and sarcopenic obesity.
* **Hydration Protocol:** Minimum baseline hydration goal of $2,500\text{–}3,000\text{ mL/day}$ with electrolyte pacing to mitigate gastrointestinal side effects.
* **Meal Fractionation:** Recommendation split into 4–5 nutrient-dense micro-meals when delayed gastric emptying is active.

---

## ⚠️ 2. Contraindications & High-Risk Exclusions

NutriTrack's automated AI coaching is **explicitly contraindicated** as a primary intervention for:

| Condition | Risk Factor | System Action |
| :--- | :--- | :--- |
| **Active Eating Disorder History (Anorexia / Bulimia)** | Calorie and macro tracking triggers fixation | Calorie number obfuscation mode available; prompt disclaimers displayed |
| **Chronic Kidney Disease (CKD Stages 3–5)** | High protein intake accelerates renal decline | Disables high-protein recommendations; mandates nephrologist target overrides |
| **Pregnancy & Lactation** | Dynamic fetal nutrient and energy demands | Prompts for OB/GYN-supervised caloric floors (+300 to +500 kcal/day) |
| **Type 1 Diabetes Mellitus** | Insulin-to-carbohydrate ratio dosing criticality | Educational macro estimation only; explicitly warns against using estimates for medical insulin bolus dosing |

---

## 📋 3. Clinician Configuration & Data Portability

* **Clinician Override Target:** Healthcare providers can specify custom calorie, protein, and micronutrient targets that override automated algorithms.
* **Transparent Attribution:** All clinical micronutrient logs (82+ fields) reference USDA SR Legacy chemical values with lab-provenance metadata.
* **Structured Export:** Health records can be exported in standardized **Apple HealthKit XML/JSON** and **CSV format** for clinical consultation.

---

## ⚖️ 4. Regulatory & Legal Classification

> **IMPORTANT DISCLAIMER:**  
> NutriTrack is an educational nutritional intelligence platform and personal lifestyle-tracking utility. It is **not a diagnostic medical device** and is **not intended to diagnose, treat, cure, or prevent any disease**. All users should consult a licensed physician or registered dietitian before beginning any new diet or exercise regimen.
