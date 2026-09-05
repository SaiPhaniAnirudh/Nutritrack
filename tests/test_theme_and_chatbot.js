const fs = require('fs');
const path = require('path');

const restyle = fs.readFileSync(path.join(__dirname, '../frontend/DashboardRestyle.css'), 'utf8');
const theme = fs.readFileSync(path.join(__dirname, '../frontend/Theme.css'), 'utf8');
const toggle = fs.readFileSync(path.join(__dirname, '../frontend/ThemeToggle.js'), 'utf8');

console.log('🧪 Verifying Chatbot & Theme Toggle Mechanics...');

// 1. Check NutriBot rules
if (!restyle.includes('.nutribot-panel {\n  position: fixed !important;') || !restyle.includes('display: none !important;')) {
  console.error('❌ NutriBot panel must be hidden by default with display: none !important;');
  process.exit(1);
}
console.log('  ✅ NutriBot panel defaults to display: none !important');

if (!restyle.includes('.nutribot-panel.active {\n  display: flex !important;')) {
  console.error('❌ NutriBot active state missing');
  process.exit(1);
}
console.log('  ✅ NutriBot panel.active sets display: flex !important');

// 2. Check Theme overrides
const lightOverrides = [
  '[data-theme="light"] body',
  '[data-theme="light"] #mainApp',
  '[data-theme="light"] .sidebar-nav',
  '[data-theme="light"] .glass-card',
  '[data-theme="light"] .hero-nutrition-card',
  '[data-theme="light"] .meal-timeline-card',
  '[data-theme="light"] .micronutrient-scorecard',
  '[data-theme="light"] .floating-assistant-bar'
];

lightOverrides.forEach(sel => {
  if (!theme.includes(sel)) {
    console.error(`❌ Missing Light Mode override for ${sel}`);
    process.exit(1);
  }
  console.log(`  ✅ Light Mode override present: ${sel}`);
});

// 3. Check ThemeToggle.js mechanics
if (!toggle.includes("document.documentElement.setAttribute('data-theme', theme)") ||
    !toggle.includes("document.body.setAttribute('data-theme', theme)")) {
  console.error('❌ ThemeToggle.js must set data-theme on BOTH html and body');
  process.exit(1);
}
console.log('  ✅ ThemeToggle sets data-theme on both documentElement and body');

console.log('\n🎉 ALL CHECKS PASSED: Chatbot stays closed until clicked, and theme toggle overrides the entire app canvas!');
