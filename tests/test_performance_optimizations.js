const fs = require('fs');
const path = require('path');

console.log('🧪 Running PageSpeed Insights Performance Optimization Test Suite...\n');

let failed = false;
function assert(condition, message) {
  if (condition) {
    console.log(`  ✅ ${message}`);
  } else {
    console.error(`  ❌ FAILED: ${message}`);
    failed = true;
  }
}

const html = fs.readFileSync(path.join(__dirname, '../frontend/index.html'), 'utf8');
const restyleCss = fs.readFileSync(path.join(__dirname, '../frontend/DashboardRestyle.css'), 'utf8');
const vercelJson = fs.readFileSync(path.join(__dirname, '../vercel.json'), 'utf8');
const swJs = fs.readFileSync(path.join(__dirname, '../frontend/sw.js'), 'utf8');

// 1. Non-composited animations eliminated
console.log('[1/4] Checking Composited Animations & GPU Acceleration...');
assert(
  restyleCss.includes('@keyframes arLaserSweep') &&
  restyleCss.includes('transform: translateY(20px)') &&
  !restyleCss.includes('0% { top: 8%;'),
  'arLaserSweep uses transform: translateY instead of animating top'
);

assert(
  restyleCss.includes('@keyframes achShimmer') &&
  restyleCss.includes('transform: translateX(-100%)') &&
  !restyleCss.includes('0% { left: -100%;'),
  'achShimmer uses transform: translateX instead of animating left'
);

assert(
  restyleCss.includes('will-change: transform, opacity;') || restyleCss.includes('will-change: transform;'),
  'will-change hardware hints added to high-frequency animated elements'
);

// 2. CSS Loading & Critical Path
console.log('\n[2/4] Checking Critical CSS & Deferred Stylesheet Delivery...');
assert(
  html.includes('<!-- Critical CSS: inlined for instant first paint'),
  'Critical auth & shell CSS inlined in <head>'
);

assert(
  html.includes('rel="stylesheet" href="/DashboardRestyle.css?v=18" media="print" onload="this.media=\'all\'"'),
  'DashboardRestyle.css loaded asynchronously via media=print onload'
);

assert(
  html.includes('rel="stylesheet" href="/Theme.css?v=9" media="print" onload="this.media=\'all\'"'),
  'Theme.css loaded asynchronously via media=print onload'
);

// 3. JavaScript Optimization & Execution Order
console.log('\n[3/4] Checking Script Execution Order & Head Weight...');
const headIndex = html.indexOf('</head>');
const headContent = html.substring(0, headIndex);

assert(
  !headContent.includes('@supabase/supabase-js'),
  'Supabase SDK removed from <head> to prevent head-parse blocking'
);

assert(
  html.includes('<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2" defer></script>') &&
  html.indexOf('@supabase/supabase-js') < html.indexOf('/App.js'),
  'Supabase SDK deferred at bottom of <body> before App.js'
);

assert(
  html.includes('decoding="sync"') && html.includes('fetchpriority="high"'),
  'LCP logo image has fetchpriority=high and decoding=sync'
);

// 4. Server Configuration & Service Worker Cache
console.log('\n[4/4] Checking Vercel Rewrites & Service Worker Cache...');
assert(
  vercelJson.includes('/sample_meals.js') && vercelJson.includes('/IndexedDB.js'),
  'Vercel rewrites configured for /sample_meals.js and /IndexedDB.js'
);

assert(
  swJs.includes("const CACHE_NAME = 'nutritrack-v53';") &&
  swJs.includes("'/sample_meals.js',"),
  'Service worker cache bumped to v53 with sample_meals.js in APP_SHELL'
);

if (failed) {
  console.error('\n❌ SOME PERFORMANCE CHECKS FAILED!');
  process.exit(1);
} else {
  console.log('\n🎉 ALL PAGESPEED INSIGHTS OPTIMIZATION CHECKS PASSED 100%!\n');
}
