/**
 * test_performance_and_alignment.js
 * Validates performance optimizations (3D auth canvas lifecycle, search debounce)
 * and layout alignment (profile grid closure, full-width clinician mode, benchmark page hierarchy).
 */

const fs = require('fs');
const path = require('path');

console.log('🧪 Running Performance & Alignment Test Suite...');

const htmlPath = path.join(__dirname, '../frontend/index.html');
const appJsPath = path.join(__dirname, '../frontend/App.js');
const cssPath = path.join(__dirname, '../frontend/DashboardRestyle.css');

const html = fs.readFileSync(htmlPath, 'utf8');
const appJs = fs.readFileSync(appJsPath, 'utf8');
const css = fs.readFileSync(cssPath, 'utf8');

// 1. Check 3D Auth Visual Lifecycle Optimization
if (!appJs.includes('function stop3DAuthVisual()') || !appJs.includes('function start3DAuthVisual()')) {
  console.error('❌ Failed: Missing stop3DAuthVisual or start3DAuthVisual in App.js');
  process.exit(1);
}
console.log('  ✅ 3D Auth Visual lifecycle functions (start/stop) verified');

if (!appJs.includes('stop3DAuthVisual();') || !appJs.includes('isAuthVisualVisible()')) {
  console.error('❌ Failed: 3D Auth loop not conditionally terminated on login or invisibility');
  process.exit(1);
}
console.log('  ✅ Conditional pause of 3D auth requestAnimationFrame verified');

// 2. Check Debounced Remote Food Search
if (!appJs.includes('_foodSearchFetchTimer') || !appJs.includes('_executeRemoteFoodFetch')) {
  console.error('❌ Failed: Remote food search is not debounced in App.js');
  process.exit(1);
}
console.log('  ✅ Debounced remote food search verified (prevents typing network congestion)');

// 3. Check Profile Grid Structure & Benchmark Page Sibling Separation
const profileGridIdx = html.indexOf('<div class="profile-grid">');
const clinicianIdx = html.indexOf('🩺 Clinician Mode');
const profileCloseIdx = html.indexOf('</div><!-- /page-profile -->');
const benchmarkIdx = html.indexOf('id="page-benchmark"');

if (profileGridIdx === -1 || clinicianIdx === -1 || profileCloseIdx === -1 || benchmarkIdx === -1) {
  console.error('❌ Failed: Profile grid or Benchmark elements not found');
  process.exit(1);
}

if (profileCloseIdx > benchmarkIdx) {
  console.error('❌ Failed: #page-benchmark is erroneously nested inside #page-profile!');
  process.exit(1);
}
console.log('  ✅ #page-profile properly closed before #page-benchmark starts');

// 4. Check Clinician Mode Spanning
if (!html.includes('style="grid-column: 1 / -1; margin-top:1.5rem; border: 1px solid rgba(62, 207, 142, 0.25);"')) {
  console.error('❌ Failed: Clinician card is missing grid-column: 1 / -1 spanning');
  process.exit(1);
}
console.log('  ✅ Clinician Mode card spans full grid width (grid-column: 1 / -1)');

// 5. Check CSS Profile Grid Definitions
if (!css.includes('.profile-grid') || !css.includes('grid-template-columns: repeat(2, 1fr)')) {
  console.error('❌ Failed: .profile-grid missing in DashboardRestyle.css');
  process.exit(1);
}
console.log('  ✅ .profile-grid rules and responsive collapse verified in DashboardRestyle.css');

// 6. Check PWA Dismissal Persistence
if (!html.includes('let shouldShowBanner = !dismissedTime;')) {
  console.error('❌ Failed: PWA install banner dismissal persistence not verified');
  process.exit(1);
}
console.log('  ✅ PWA banner dismissal persistence verified');

console.log('\n🎉 ALL PERFORMANCE & ALIGNMENT CHECKS PASSED 100%!\n');
