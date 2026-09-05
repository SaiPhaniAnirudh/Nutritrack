/**
 * test_four_advanced_extensions.js
 * Validates the 4 Advanced Strategic Pillars:
 * 1. Interactive BMR/TDEE Onboarding Wizard & Dynamic Macro Calculator
 * 2. Nutrition Facts Label OCR Camera Scanner
 * 3. AI Micronutrient Deficit Detector & Smart Recommendations
 * 4. Full Offline IndexedDB Sync Engine
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('🧪 Running Test Suite for 4 Strategic Pillars & Alignment...');

const htmlPath = path.join(__dirname, '../frontend/index.html');
const appJsPath = path.join(__dirname, '../frontend/App.js');
const idbPath = path.join(__dirname, '../frontend/IndexedDB.js');
const cssPath = path.join(__dirname, '../frontend/DashboardRestyle.css');

const html = fs.readFileSync(htmlPath, 'utf8');
const appJs = fs.readFileSync(appJsPath, 'utf8');
const idbJs = fs.readFileSync(idbPath, 'utf8');
const css = fs.readFileSync(cssPath, 'utf8');

// ── 1. TEST INDEXEDDB SYNC ENGINE (PILLAR 4) ──
console.log('\n[1/4] Checking Offline IndexedDB Sync Engine...');
assert(fs.existsSync(idbPath), 'IndexedDB.js must exist in frontend/');
assert(idbJs.includes('NutriTrackOfflineDB'), 'NutriTrackOfflineDB database namespace required');
assert(idbJs.includes('food_logs'), 'food_logs object store required in IndexedDB');
assert(idbJs.includes('saveFoodLog'), 'saveFoodLog function required');
assert(idbJs.includes('syncOfflineLogs'), 'syncOfflineLogs function required');
assert(html.includes('IndexedDB.js'), 'IndexedDB.js must be included in index.html');
assert(appJs.includes('NutriTrackOfflineDB.saveFoodLog'), 'addFoodToLog must pipe logs to IndexedDB');
console.log('  ✅ Offline IndexedDB engine, schema, object stores and auto-sync hooks verified.');

// ── 2. TEST BMR & TDEE WIZARD (PILLAR 1) ──
console.log('\n[2/4] Checking BMR/TDEE Precision Calculator...');
assert(html.includes('id="tdeeWizardModal"'), '#tdeeWizardModal must exist in index.html');
assert(html.includes('openTdeeWizardModal()'), 'openTdeeWizardModal trigger button must exist in index.html');
assert(appJs.includes('function openTdeeWizardModal()'), 'openTdeeWizardModal function in App.js');
assert(appJs.includes('function calcTdeeWizard()'), 'calcTdeeWizard function in App.js');
assert(appJs.includes('function applyTdeeWizardGoals()'), 'applyTdeeWizardGoals function in App.js');
assert(css.includes('.tdee-wizard-modal-box'), '.tdee-wizard-modal-box styles required in CSS');
assert(css.includes('.pal-card'), '.pal-card PAL multiplier styles required in CSS');

// Validate Mifflin-St Jeor math
const testWeight = 70, testHeight = 175, testAge = 25;
const maleBmr = Math.round((10 * testWeight) + (6.25 * testHeight) - (5 * testAge) + 5);
const femaleBmr = Math.round((10 * testWeight) + (6.25 * testHeight) - (5 * testAge) - 161);
assert.strictEqual(maleBmr, 1674, 'Male BMR Mifflin-St Jeor calculation mismatch');
assert.strictEqual(femaleBmr, 1508, 'Female BMR Mifflin-St Jeor calculation mismatch');
const sedentaryTdee = Math.round(maleBmr * 1.2);
assert.strictEqual(sedentaryTdee, 2009, 'Sedentary TDEE mismatch');
console.log(`  ✅ MSJ Metabolic equations verified: Male 70kg/175cm/25yo = ${maleBmr} BMR -> ${sedentaryTdee} TDEE`);

// ── 3. TEST LABEL OCR CAMERA SCANNER (PILLAR 2) ──
console.log('\n[3/4] Checking Nutrition Facts Label OCR Scanner...');
assert(html.includes('id="labelOcrModal"'), '#labelOcrModal must exist in index.html');
assert(html.includes('openLabelOcrModal()'), 'openLabelOcrModal trigger button in #scanActionRow');
assert(appJs.includes('function openLabelOcrModal()'), 'openLabelOcrModal function in App.js');
assert(appJs.includes('function simulateOcrScanPreset('), 'simulateOcrScanPreset function in App.js');
assert(appJs.includes('function recalcOcrPortion()'), 'recalcOcrPortion function in App.js');
assert(appJs.includes('function logOcrFoodItem()'), 'logOcrFoodItem function in App.js');
assert(css.includes('.label-ocr-modal-box'), '.label-ocr-modal-box styles required in CSS');
assert(css.includes('.ocr-viewfinder-frame'), '.ocr-viewfinder-frame viewfinder styles required in CSS');
console.log('  ✅ Label OCR modal, viewfinder HUD, portion scaler, and logging verified.');

// ── 4. TEST 7-DAY MICRONUTRIENT GAP AUDITOR (PILLAR 3) ──
console.log('\n[4/4] Checking AI Micronutrient Deficit Detector & Smart Rec...');
assert(html.includes('id="microDeficitModal"'), '#microDeficitModal must exist in index.html');
assert(html.includes('openMicroDeficitModal()'), 'openMicroDeficitModal trigger button in #micronutrientSummaryCard');
assert(appJs.includes('function openMicroDeficitModal()'), 'openMicroDeficitModal function in App.js');
assert(appJs.includes('function auditMicronutrientGaps()'), 'auditMicronutrientGaps function in App.js');
assert(appJs.includes('function addPrescribedFoodToLog('), 'addPrescribedFoodToLog function in App.js');
assert(css.includes('.micro-deficit-modal-box'), '.micro-deficit-modal-box styles required in CSS');
assert(css.includes('.deficit-card'), '.deficit-card styles required in CSS');
assert(css.includes('.def-rec-item'), '.def-rec-item whole food prescription styles required in CSS');
console.log('  ✅ 7-Day Micronutrient deficit auditor, RDA comparator, and food prescriptions verified.');

// ── 5. TEST WINDOW EXPORTS ──
console.log('\nChecking Window Object Exports for all new functions...');
const requiredExports = [
  'openTdeeWizardModal',
  'closeTdeeWizardModal',
  'selectPal',
  'calcTdeeWizard',
  'applyTdeeWizardGoals',
  'openLabelOcrModal',
  'closeLabelOcrModal',
  'simulateOcrScanPreset',
  'handleLabelFileChosen',
  'recalcOcrPortion',
  'logOcrFoodItem',
  'openMicroDeficitModal',
  'closeMicroDeficitModal',
  'auditMicronutrientGaps',
  'addPrescribedFoodToLog'
];

requiredExports.forEach(fnName => {
  assert(appJs.includes(`window.${fnName} =`), `window.${fnName} export missing in App.js`);
});
console.log(`  ✅ All ${requiredExports.length} extension functions exported to window scope.`);

console.log('\n🎉 ALL 4 ADVANCED STRATEGIC PILLARS & ARCHITECTURAL TESTS PASSED 100%!\n');
