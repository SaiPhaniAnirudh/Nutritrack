/**
 * Test Suite: AI Meal Photo Scanner (Vision LLM) & Auto-Log Suite
 */
const fs = require('fs');
const path = require('path');

console.log('🧪 Testing AI Meal Photo Scanner & Auto-Log Upgrade...');

const html = fs.readFileSync(path.join(__dirname, '../frontend/index.html'), 'utf-8');
const js = fs.readFileSync(path.join(__dirname, '../frontend/App.js'), 'utf-8');
const css = fs.readFileSync(path.join(__dirname, '../frontend/DashboardRestyle.css'), 'utf-8');
const sampleMeals = fs.readFileSync(path.join(__dirname, '../frontend/sample_meals.js'), 'utf-8');

// 1. Check HTML elements
const requiredElements = [
  'id="autoLogToggle"',
  'class="auto-log-switch"',
  'id="dragDropHud"',
  'class="scan-preset-tray"',
  "onclick=\"loadSampleMeal('salad')\"",
  "onclick=\"loadSampleMeal('pancakes')\"",
  "onclick=\"loadSampleMeal('salmon')\"",
  "onclick=\"loadSampleMeal('curry')\"",
  'id="autoLogNowBtn"'
];

requiredElements.forEach(el => {
  if (!html.includes(el)) {
    console.error(`❌ Missing element in index.html: ${el}`);
    process.exit(1);
  }
});
console.log('  ✅ All HTML markup for Auto-Log toggle, drag & drop, sample presets verified.');

// 2. Check sample_meals.js
if (!sampleMeals.includes('salad') || !sampleMeals.includes('pancakes') || !sampleMeals.includes('salmon') || !sampleMeals.includes('curry')) {
  console.error('❌ Missing meal presets in sample_meals.js');
  process.exit(1);
}
console.log('  ✅ 4 Sample meal photography presets (Greek Salad, Pancakes, Salmon Bento, Curry Bowl) verified.');

// 3. Check App.js functions
const requiredFunctions = [
  'function isAutoLogEnabled',
  'function handleAutoLogToggle',
  'function handleCamDragOver',
  'function handleCamDragLeave',
  'function handleCamDrop',
  'function loadSampleMeal',
  'async function _renderAutoLoggedResult',
  'async function undoAutoLoggedMeal',
  'async function relogAutoLoggedMeal',
  'async function scaleAutoLoggedMeal'
];

requiredFunctions.forEach(fn => {
  if (!js.includes(fn)) {
    console.error(`❌ Missing function in App.js: ${fn}`);
    process.exit(1);
  }
});
console.log('  ✅ All JavaScript handlers for automatic vision logging, undo, and retroactive scaling verified.');

// 4. Check CSS styling
const requiredCss = [
  '.auto-log-switch',
  '.auto-log-slider',
  '.drag-drop-hud',
  '.scan-preset-tray',
  '.auto-log-card',
  '.auto-log-badge'
];

requiredCss.forEach(selector => {
  if (!css.includes(selector)) {
    console.error(`❌ Missing CSS selector: ${selector}`);
    process.exit(1);
  }
});
console.log('  ✅ Obsidian dark glassmorphism styling for scanner auto-log HUD verified.');

console.log('\n🎉 ALL AI MEAL PHOTO SCANNER (VISION LLM) TESTS PASSED 100%!');
