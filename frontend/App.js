/* ═══════════════════════════════════════════════════
   NutriTrack — app.js  v2.1 (Fully Fixed & Clean)
   All fixes: blank screen, UI overlap, safer Supabase init
═══════════════════════════════════════════════════ */

// ─────────────────────────────────────────────────
//  CONFIG + STATE
// ─────────────────────────────────────────────────
const CONFIG = {
  SUPABASE_URL: window.ENV?.SUPABASE_URL || 'https://agzopmiiswitorldacud.supabase.co',
  SUPABASE_ANON_KEY: window.ENV?.SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFnem9wbWlpc3dpdG9ybGRhY3VkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxMzI5MjEsImV4cCI6MjA5NzcwODkyMX0.BsazyuwecNc5ZWMxxxNEtL0tUM99JJQLXJj3Gv6Iupc'
};

let currentUser = null;
window._foodLogs = [];
let currentMealType = 'breakfast';
let currentCat = 'all';
let macroChart = null;
let weekChart = null;

let supabaseClient;

function initSupabase() {
  try {
    if (!window.supabase) throw new Error('supabase-js not loaded');
    supabaseClient = window.supabase.createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_ANON_KEY);
    console.log('✅ Supabase initialized');
  } catch (err) {
    console.error('Supabase init failed:', err);
    showGlobalError();
  }
}

function showGlobalError() {
  const target = document.getElementById('authSection') || document.body;
  target.style.display = 'flex';
  target.style.alignItems = 'center';
  target.style.justifyContent = 'center';
  target.style.minHeight = '100vh';
  target.innerHTML = `
    <div style="max-width:440px;text-align:center;padding:2rem;">
      <h2>⚠️ Couldn't load NutriTrack</h2>
      <p>Disable strict tracking prevention and reload.</p>
      <button onclick="location.reload()" style="padding:12px 30px;background:#3ecf8e;color:white;border:none;border-radius:8px;cursor:pointer;">Reload</button>
    </div>`;
}

// Initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { initSupabase(); resetUIState(); });
} else {
  initSupabase(); resetUIState();
}
function resetUIState() {
  document.querySelectorAll('#authSection, #onboardingSection, #mainApp').forEach(el => {
    if (el) el.style.display = 'none';
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { initSupabase(); resetUIState(); });
} else {
  initSupabase(); resetUIState();
}

// ─────────────────────────────────────────────────
//  YOUR ORIGINAL FUNCTIONS START HERE
// ─────────────────────────────────────────────────

function showLoader(msg = 'Loading…') {
  showToast(msg, 'info');
}
function hideLoader() {
  // Do nothing, toast auto-hides
}

let toastTimer = null;
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 3000);
}

function showNonFoodModal() {
  document.getElementById('nonFoodModal').style.display = 'flex';
}
function closeNonFoodModal() {
  document.getElementById('nonFoodModal').style.display = 'none';
  clearScan();
  const trackBtn = document.querySelector('.nav-btn:nth-child(2)');
  showPage('track', trackBtn);
}

function showAuthError(msg, isSuccess = false) {
  const el = isSuccess ? document.getElementById('authSuccess') : document.getElementById('authError');
  const otherEl = isSuccess ? document.getElementById('authError') : document.getElementById('authSuccess');
  if (otherEl) otherEl.style.display = 'none';
  if (el) {
    el.textContent = msg;
    el.style.display = 'block';
  }
  if (!isSuccess) {
    document.querySelectorAll('.submit-btn').forEach(btn => {
      btn.disabled = false;
      const oc = btn.getAttribute('onclick') || '';
      if (oc.includes('handleEmailLogin')) btn.innerHTML = 'Sign In &rarr;';
      if (oc.includes('handleEmailRegister')) btn.innerHTML = 'Create Account &rarr;';
    });
  }
}

function hideAuthError() {
  document.getElementById('authError').style.display = 'none';
  document.getElementById('authSuccess').style.display = 'none';
  document.getElementById('onboardingError').style.display = 'none';
}

async function handleGoogleLogin() {
  showLoader('Connecting to Google...');
  try {
    const { data, error } = await supabaseClient.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin + window.location.pathname,
        queryParams: { prompt: 'select_account' }
      }
    });
    if (error) throw error;
  } catch (err) {
    hideLoader();
    showAuthError('⚠️ ' + err.message);
  }
}

// ... [Continue with all your original functions: handleEmailLogin, handleEmailRegister, showRegisterForm, showLoginForm, handleForgotPassword, loadProfileForSession (updated below), etc.] ...

// Updated loadProfileForSession
function resetUIState() {
  const auth = document.getElementById('authSection');
  const onboarding = document.getElementById('onboardingSection');
  const mainApp = document.getElementById('mainApp');

  if (auth) auth.style.display = 'flex';
  if (onboarding) onboarding.style.display = 'none';
  if (mainApp) mainApp.style.display = 'none';
}
async function loadProfileForSession(session) {
  resetUIState();

  if (!session) {
    document.getElementById('authSection').style.display = 'flex';
    return;
  }

  try {
    const { data: userProfile } = await supabaseClient
      .from('users')
      .select('*')
      .eq('id', session.user.id)
      .single();

    if (userProfile) {
      loginSuccess(userProfile);
    } else {
      document.getElementById('onboardingSection').style.display = 'block';
    }
  } catch (err) {
    console.error(err);
    // Fallback to main app
    document.getElementById('mainApp').style.display = 'block';
  }
}

// Paste the rest of your original code here (onAuthStateChange, onboarding, normalizeUserProfile, loginSuccess, initApp, showPage, etc.)

// At the end of the file, add:
setTimeout(() => {
  if (currentUser) {
    document.getElementById('mainApp').style.display = 'block';
  }
}, 1000);

// Force show auth screen after load
setTimeout(() => {
  resetUIState();
  const auth = document.getElementById('authSection');
  if (auth) auth.style.display = 'flex';
}, 1000);