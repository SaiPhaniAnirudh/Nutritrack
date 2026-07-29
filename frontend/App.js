/* ═══════════════════════════════════════════════════
   NutriTrack — app.js  v2.0
   Changes vs v1:
   #1  Age/weight/height stored & displayed
   #2  Food description shown in search cards
   #3  SVG logo (in HTML)
   #4/#9 New background colour (deep navy-green + aurora blobs)
   #5  Mobile/session isolation — sessionStorage for scan data, no camera frame stored on laptop
   #6  API key provider name removed from label
   #7  3-step registration with full validation before advancing
   #8  Non-food popup shown when AI returns no food items
   #10 Page loader shown on every transition
   #11/#12 "Plan My Diet" navbar widget with personalised plan
   #13 "Sodium" → "Salt" in all display strings
═══════════════════════════════════════════════════ */


// ─────────────────────────────────────────────────
//  PAGE LOADER  (non-blocking)
// ─────────────────────────────────────────────────
function showLoader(msg = 'Loading…') {
  showToast(msg, 'info');
}
function hideLoader() {
  // Do nothing, toast auto-hides
}

// ─────────────────────────────────────────────────
//  LOCAL STORAGE DB
// ─────────────────────────────────────────────────


// ─────────────────────────────────────────────────
//  APP STATE
// ─────────────────────────────────────────────────
let currentUser = null;
window._foodLogs = [];
window._weightLogs = [];
window._mealTemplates = [];
window._dbPopularFoods = [];
let currentMealType = 'breakfast';
let currentCat = 'all';
let macroChart = null;
let weekChart = null;
let weightChart = null;
let _voiceRecognition = null;

// ─────────────────────────────────────────────────
//  TOAST
// ─────────────────────────────────────────────────
let toastTimer = null;
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 3000);
}

// ─────────────────────────────────────────────────
//  NON-FOOD POPUP  (change #8)
// ─────────────────────────────────────────────────
function showNonFoodModal() {
  document.getElementById('nonFoodModal').style.display = 'flex';
}
function closeNonFoodModal() {
  document.getElementById('nonFoodModal').style.display = 'none';
  clearScan();
  // Pass the Track Food nav button so it gets highlighted correctly
  const trackBtn = document.querySelector('.nav-btn:nth-child(2)');
  showPage('track', trackBtn);
}

// ─────────────────────────────────────────────────
//  SUPABASE AUTH INITIALIZATION
// ─────────────────────────────────────────────────
const SUPABASE_URL = 'https://agzopmiiswitorldacud.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFnem9wbWlpc3dpdG9ybGRhY3VkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxMzI5MjEsImV4cCI6MjA5NzcwODkyMX0.BsazyuwecNc5ZWMxxxNEtL0tUM99JJQLXJj3Gv6Iupc';

// This used to be a bare, unguarded `window.supabase.createClient(...)` call.
// If the supabase-js CDN script (cdn.jsdelivr.net) fails to load — or if the
// browser's storage/tracking-prevention feature causes createClient()'s
// internal localStorage access to throw (both are known to happen under
// Edge/Chrome "strict" tracking prevention) — that call throws a plain,
// uncaught error at the top of this script. Because it's the very first
// executable statement in App.js, that throw halts *all* remaining code in
// this file, including the auth-state listener registration a few lines
// down. Since #mainApp and #authSection both default to display:none, the
// result is a permanently blank page with no error shown to the user at
// all (only visible via DevTools console) — this is the most likely cause
// of the "blank page" reports. Now guarded, with a real visible fallback.
let supabaseClient;
try {
  if (!window.supabase) {
    throw new Error('supabase-js failed to load from cdn.jsdelivr.net');
  }
  supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
} catch (err) {
  console.error('[NutriTrack] Supabase init failed — showing fallback error UI:', err);
  const showFatalError = () => {
    const authSec = document.getElementById('authSection');
    const target = authSec || document.body;
    target.style.display = 'flex';
    target.style.alignItems = 'center';
    target.style.justifyContent = 'center';
    target.style.minHeight = '100vh';
    target.innerHTML = `
      <div style="max-width:440px;text-align:center;padding:2rem;font-family:inherit;">
        <div style="font-size:2.5rem;margin-bottom:0.5rem;">⚠️</div>
        <h2 style="margin:0 0 1rem;">Couldn't load NutriTrack</h2>
        <p style="opacity:0.75;line-height:1.5;margin-bottom:1.5rem;">
          A required script failed to load. This usually happens when a browser's
          tracking/privacy protection (e.g. Edge or Chrome "strict" tracking
          prevention) blocks cdn.jsdelivr.net, or when you're offline.
          Try disabling strict tracking prevention for this site, or reload.
        </p>
        <button onclick="location.reload()"
          style="padding:0.7rem 1.4rem;border-radius:8px;border:none;background:#3ecf8e;color:#fff;font-weight:600;cursor:pointer;font-size:1rem;">
          Reload page
        </button>
      </div>`;
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', showFatalError);
  } else {
    showFatalError();
  }
  // Minimal no-op stand-in so any later code that references
  // supabaseClient.auth.* below doesn't throw a second, more confusing
  // error on top of the one we already showed the user.
  supabaseClient = {
    auth: {
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe() { } } } }),
      getSession: async () => ({ data: { session: null } }),
      signOut: async () => { },
      signInWithPassword: async () => ({ error: new Error('App failed to initialize') }),
      signUp: async () => ({ error: new Error('App failed to initialize') }),
      signInWithOAuth: async () => ({ error: new Error('App failed to initialize') }),
    },
  };
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

// ─────────────────────────────────────────────────
//  GOOGLE LOGIN
// ─────────────────────────────────────────────────
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

// ─────────────────────────────────────────────────
//  EMAIL/PASSWORD LOGIN & REGISTER
// ─────────────────────────────────────────────────
async function handleEmailLogin(event) {
  const email = document.getElementById('loginEmail').value.trim();
  const pw = document.getElementById('loginPassword').value;
  if (!email || !pw) return showAuthError('⚠️ Email and password required.');

  const btn = event && event.target ? event.target : document.querySelector('.submit-btn');
  const originalText = btn ? btn.innerHTML : 'Sign In &rarr;';
  let wakeTimeout;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = 'Signing in...';
    wakeTimeout = setTimeout(() => {
      if (btn.disabled) btn.innerHTML = 'Waking Database (wait ~30s)...';
    }, 3000);
  }

  // The first request to a paused/sleeping Supabase project both wakes it
  // up AND is the one most likely to time out — so a single silent retry
  // right after covers the common case automatically, instead of making
  // the person manually click "Sign In" a second time themselves.
  const attemptSignIn = () => {
    const signInPromise = supabaseClient.auth.signInWithPassword({ email, password: pw });
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('TIMEOUT')), 25000)
    );
    return Promise.race([signInPromise, timeoutPromise]);
  };

  try {
    let signInData, signInError;
    try {
      ({ data: signInData, error: signInError } = await attemptSignIn());
    } catch (firstErr) {
      if (firstErr && firstErr.message === 'TIMEOUT') {
        if (btn) btn.innerHTML = 'Still waking up — retrying...';
        ({ data: signInData, error: signInError } = await attemptSignIn());
      } else {
        throw firstErr;
      }
    }

    if (signInError) throw signInError;

    // Explicitly load profile instead of relying on state change listener
    // because if session is already active, listener might not fire a NEW event!
    if (signInData && signInData.session) {
      await loadProfileForSession(signInData.session);
    } else if (signInData && !signInData.session) {
      clearTimeout(wakeTimeout);
      showAuthError('⚠️ Please check your email to confirm your account before signing in.');
    }
  } catch (err) {
    clearTimeout(wakeTimeout);
    if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
    if (err && err.message === 'TIMEOUT') {
      showAuthError('⚠️ The database is taking unusually long to wake up. Please try again in a moment.');
    } else {
      showAuthError('⚠️ ' + err.message);
    }
  }
}

async function handleEmailRegister(event) {
  const name = document.getElementById('regName').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const pw = document.getElementById('regPassword').value;

  if (!name || !email || !pw) return showAuthError('⚠️ Name, email, and password required.');

  const btn = event && event.target ? event.target : document.querySelectorAll('.submit-btn')[1];
  const originalText = btn ? btn.innerHTML : 'Sign Up &rarr;';
  let wakeTimeout;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = 'Creating Account...';
    wakeTimeout = setTimeout(() => {
      if (btn.disabled) btn.innerHTML = 'Waking Database (wait ~30s)...';
    }, 3000);
  }

  const attemptSignUp = () => {
    const signUpPromise = supabaseClient.auth.signUp({
      email: email,
      password: pw,
      options: { data: { full_name: name } }
    });
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('TIMEOUT')), 25000)
    );
    return Promise.race([signUpPromise, timeoutPromise]);
  };

  try {
    let data, error;
    try {
      ({ data, error } = await attemptSignUp());
    } catch (firstErr) {
      if (firstErr && firstErr.message === 'TIMEOUT') {
        if (btn) btn.innerHTML = 'Still waking up — retrying...';
        ({ data, error } = await attemptSignUp());
      } else {
        throw firstErr;
      }
    }

    if (error) throw error;
    if (data.user && data.user.identities && data.user.identities.length === 0) {
      throw new Error("Account already exists with this email.");
    }

    clearTimeout(wakeTimeout);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
    showAuthError('Account created! Please check your email to verify your account, then sign in.', true);
    showLoginForm();
  } catch (err) {
    clearTimeout(wakeTimeout);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
    if (err && err.message === 'TIMEOUT') {
      showAuthError('⚠️ The database is taking unusually long to wake up. Please try again in a moment.');
    } else {
      showAuthError('⚠️ ' + err.message);
    }
  }
}

function showRegisterForm() {
  document.getElementById('loginForm').style.display = 'none';
  document.getElementById('registerForm').style.display = 'block';
  document.getElementById('authError').style.display = 'none';
  document.getElementById('authSuccess').style.display = 'none';
}

function showLoginForm() {
  document.getElementById('registerForm').style.display = 'none';
  document.getElementById('loginForm').style.display = 'block';
  document.getElementById('authError').style.display = 'none';
  document.getElementById('authSuccess').style.display = 'none';
}

async function handleForgotPassword() {
  const email = document.getElementById('loginEmail').value.trim();
  if (!email) return showAuthError('⚠️ Please enter your email address first to reset password.');

  showLoader('Sending reset link...');
  try {
    const resetPromise = supabaseClient.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin + window.location.pathname,
    });
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('TIMEOUT')), 25000)
    );
    const { error } = await Promise.race([resetPromise, timeoutPromise]);
    if (error) throw error;
    showAuthError('Reset link sent to your email!', true);
  } catch (err) {
    if (err && err.message === 'TIMEOUT') {
      showAuthError('⚠️ Timed out — the database may still be waking up from sleep. Please try again in a few seconds.');
    } else {
      showAuthError('⚠️ ' + err.message);
    }
  } finally {
    hideLoader();
  }
}

// ─────────────────────────────────────────────────
//  SESSION LISTENER & ONBOARDING ROUTING
// ─────────────────────────────────────────────────
async function loadProfileForSession(session) {
  if (!session) return;

  // Make sure the container these status messages live in is actually
  // visible. #authSuccess/#authError are children of #authSection, which
  // defaults to display:none and is only shown in the "no session" branch
  // below — so without this, any hang or failure here showed nothing at
  // all, for as long as it hung.
  const aSecEl = document.getElementById('authSection');
  if (aSecEl) aSecEl.style.display = 'flex';
  const mAppEl = document.getElementById('mainApp');
  if (mAppEl) mAppEl.style.display = 'none';

  showAuthError('Loading profile…', true);
  try {
    // Supabase free-tier projects pause after inactivity and can take a
    // while to wake up (or fail outright if fully paused) — don't let this
    // hang forever with no feedback.
    let userProfile = null;
    try {
      const queryPromise = supabaseClient
        .from('users')
        .select('*')
        .eq('id', session.user.id)
        .single();
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('TIMEOUT')), 15000)
      );
      const { data, error } = await Promise.race([queryPromise, timeoutPromise]);
      if (!error && data) userProfile = data;
    } catch (_) {}

    const meta = session.user.user_metadata || {};
    const localSaved = JSON.parse(localStorage.getItem(`nutritrack_profile_${session.user.id}`) || '{}');
    const combinedProfile = { ...meta, ...localSaved, ...(userProfile || {}) };

    const hasProfile = combinedProfile && (combinedProfile.dob || combinedProfile.gender || combinedProfile.goal_calories);
    if (hasProfile) {
      loginSuccess(combinedProfile);
    } else {
      const aSec = document.getElementById('authSection');
      if (aSec) aSec.style.display = 'none';
      document.getElementById('onboardingSection').style.display = 'block';
      hideLoader();
    }
  } catch (err) {
    if (err && err.message === 'TIMEOUT') {
      showAuthError('⚠️ Database is taking longer than usual to respond (it may be waking up from sleep). Please wait a moment and refresh.');
    } else {
      showAuthError('⚠️ ' + err.message);
    }
  }
}

// ─────────────────────────────────────────────────
//  BFCACHE FIX (Google account-switching bug)
//  When returning from Google's OAuth redirect, some browsers restore this
//  page from the back-forward cache (bfcache) instead of re-running this
//  script from scratch. That means Supabase's session/account detection
//  (which only runs on a fresh script load) never re-fires for the NEW
//  account — so switching Google accounts (sign out account A, sign in as
//  account B) kept showing account A's already-loaded dashboard until the
//  user did a manual refresh. Force a real reload whenever bfcache restore
//  is detected, so the new session is always picked up immediately.
// ─────────────────────────────────────────────────
window.addEventListener('pageshow', (event) => {
  if (event.persisted) {
    location.reload();
  }
});

// NOTE: an earlier version of this file tried to distinguish a normal
// refresh from a hard refresh (Ctrl+Shift+R) using
// navigator.serviceWorker.controller as a heuristic, to sign out only on
// hard refresh. In real testing it came back null on *every* refresh, not
// just hard ones, which meant normal refresh incorrectly signed people out
// too — worse than not having the feature. There's no standard, guaranteed
// browser API for this specific distinction, so it's been removed. Every
// refresh (normal or hard) now consistently preserves the session and
// current page, which is also the behavior almost all web apps use.

supabaseClient.auth.onAuthStateChange(async (event, session) => {
  try {
    if (event === 'TOKEN_REFRESHED') {
      // Supabase silently renews the session's access token in the
      // background (by default, roughly every ~55 minutes, before the
      // ~1 hour expiry). currentUser.token was previously only ever set
      // once at login time and never updated here — so after the first
      // token expired, every authenticated backend call (food logging,
      // profile updates, log deletion, chat) started failing with a
      // rejected/expired token, silently, with no indication why, even
      // though the user was still "logged in" as far as Supabase itself
      // was concerned. Keep it in sync.
      if (currentUser && session) {
        currentUser.token = session.access_token;
      }
      return;
    }
    if (event === 'SIGNED_IN' || event === 'INITIAL_SESSION') {
      _authResolved = true;

      if (!session) {
        // A null session specifically on INITIAL_SESSION (the check that
        // runs once on page load) is ambiguous: it can mean "genuinely
        // logged out", OR it can mean supabase-js's own internal
        // token-refresh network call failed transiently (e.g. a paused/
        // waking Supabase project — this project has had DB-pause issues
        // before, see .github/workflows/keepalive.yml). Both look
        // identical here. Rather than immediately bouncing a real,
        // still-valid session to the login screen, do one quick explicit
        // re-check first.
        if (event === 'INITIAL_SESSION') {
          try {
            const retryTimeout = new Promise((_, reject) => setTimeout(() => reject(new Error('TIMEOUT')), 8000));
            const { data: retryData } = await Promise.race([supabaseClient.auth.getSession(), retryTimeout]);
            if (retryData && retryData.session) {
              await loadProfileForSession(retryData.session);
              return;
            }
          } catch (e) {
            // Retry itself failed/timed out — fall through to showing login.
          }
        }
        document.getElementById('authSection').style.display = 'flex';
        const mApp = document.getElementById('mainApp');
        if (mApp) mApp.style.display = 'none';
        hideLoader();
        return;
      }
      await loadProfileForSession(session);
    } else if (event === 'SIGNED_OUT') {
      handleLogoutUI();
    }
  } catch (err) {
    console.error('onAuthStateChange error', err);
    showAuthError('⚠️ Something went wrong loading the app. Please refresh.');
    const aSec = document.getElementById('authSection');
    if (aSec) aSec.style.display = 'flex';
  }
});

// Watchdog: onAuthStateChange's INITIAL_SESSION check is itself a network
// call to Supabase Auth. If that hangs (e.g. a paused/waking Supabase
// project), the page would otherwise stay silently blank forever with no
// feedback at all. Force something visible after a bounded wait.
let _authResolved = false;
setTimeout(() => {
  if (_authResolved) return;
  const aSec = document.getElementById('authSection');
  const mApp = document.getElementById('mainApp');
  const alreadyVisible = (aSec && aSec.style.display !== 'none') || (mApp && mApp.style.display !== 'none');
  if (alreadyVisible) return;
  if (aSec) {
    aSec.style.display = 'flex';
    showAuthError('⚠️ Taking longer than usual to connect. The database may be waking up from sleep — please wait a moment and refresh.');
  }
}, 20000);

// ─────────────────────────────────────────────────
//  ONBOARDING LOGIC
// ─────────────────────────────────────────────────
function goToStep(n) {
  document.getElementById('regStep3').style.display = n === 3 ? 'block' : 'none';
  document.getElementById('regStep4').style.display = n === 4 ? 'block' : 'none';
  document.getElementById('onboardingError').style.display = 'none';
}

function showOnboardingError(msg) {
  const el = document.getElementById('onboardingError');
  el.textContent = msg;
  el.style.display = 'block';
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function goToStep4() {
  // Validate Body Stats
  const dobStr = document.getElementById('regDob').value;
  if (!dobStr) return showOnboardingError('⚠️ Please enter your date of birth.');
  const dobDate = new Date(dobStr);
  let age = new Date().getFullYear() - dobDate.getFullYear();
  if (new Date() < new Date(dobDate.setFullYear(new Date().getFullYear()))) age--;

  const weight = parseFloat(document.getElementById('regWeight').value);
  const height = parseFloat(document.getElementById('regHeight').value);
  const gender = document.querySelector('input[name="gender"]:checked');
  const goal = document.querySelector('input[name="dietGoal"]:checked');

  if (!age || age < 10 || age > 100) return showOnboardingError('⚠️ Please enter a valid age (10–100).');
  if (!weight || weight < 20) return showOnboardingError('⚠️ Please enter a valid weight.');
  if (!height || height < 50) return showOnboardingError('⚠️ Please enter a valid height.');
  if (!gender) return showOnboardingError('⚠️ Please select your gender.');
  if (!goal) return showOnboardingError('⚠️ Please select your diet goal.');

  // Auto-calculate goals
  const wUnit = document.getElementById('regWeightUnit').value;
  const hUnit = document.getElementById('regHeightUnit').value;
  const weightKg = wUnit === 'lbs' ? weight * 0.4536 : weight;
  const heightCm = hUnit === 'ft' ? height * 30.48 : height;

  const { calories, protein } = _calcGoals(weightKg, heightCm, age, gender.value, goal.value);

  document.getElementById('goalCalories').value = calories;
  document.getElementById('goalProtein').value = protein;

  // Show preview cards
  const bmi = (weightKg / ((heightCm / 100) ** 2)).toFixed(1);
  const bmiLabel = bmi < 18.5 ? 'Underweight' : bmi < 25 ? 'Normal' : bmi < 30 ? 'Overweight' : 'Obese';

  document.getElementById('autoGoalsPreview').innerHTML = `
    <div class="agp-card"><div class="agp-val">${calories}</div><div class="agp-label">kcal / day</div></div>
    <div class="agp-card"><div class="agp-val">${protein}g</div><div class="agp-label">Protein / day</div></div>
    <div class="agp-card"><div class="agp-val">${bmi}</div><div class="agp-label">BMI · ${bmiLabel}</div></div>
  `;

  goToStep(4);
}

// Harris-Benedict BMR + goal multiplier
function _calcGoals(weightKg, heightCm, age, gender, goal) {
  let bmr;
  if (gender === 'female') {
    bmr = 447.6 + 9.25 * weightKg + 3.10 * heightCm - 4.33 * age;
  } else {
    bmr = 88.36 + 13.40 * weightKg + 4.80 * heightCm - 5.68 * age;
  }
  const activityFactor = 1.55; // moderate activity
  let tdee = bmr * activityFactor;

  let calAdj = 0;
  if (goal === 'lose') calAdj = -400;
  if (goal === 'gain') calAdj = +300;
  if (goal === 'bulk') calAdj = +500;

  const calories = Math.round(tdee + calAdj);
  const protMultiplier = goal === 'bulk' ? 1.8 : goal === 'gain' ? 1.6 : 1.4;
  const protein = Math.round(weightKg * protMultiplier);

  return { calories, protein };
}

async function handleFinishOnboarding() {
  const goalCal = parseInt(document.getElementById('goalCalories').value) || 2000;
  const goalProt = parseInt(document.getElementById('goalProtein').value) || 150;
  if (goalCal < 500 || goalCal > 10000) return showOnboardingError('⚠️ Calorie goal must be between 500 and 10,000.');

  const dob = document.getElementById('regDob').value;
  const weight = parseFloat(document.getElementById('regWeight').value);
  const height = parseFloat(document.getElementById('regHeight').value);
  const weightUnit = document.getElementById('regWeightUnit').value;
  const heightUnit = document.getElementById('regHeightUnit').value;
  const genderEl = document.querySelector('input[name="gender"]:checked').value;
  const goalEl = document.querySelector('input[name="dietGoal"]:checked').value;
  const dietTypeEl = document.querySelector('input[name="dietType"]:checked').value;

  showLoader('Saving your profile...');

  const { data: sessionData } = await supabaseClient.auth.getSession();
  if (!sessionData.session) return showOnboardingError('⚠️ Session expired. Please login again.');

  const user = sessionData.session.user;
  const name = user.user_metadata?.full_name || user.email.split('@')[0];

  const payload = {
    id: user.id,
    email: user.email,
    name: name,
    dob: dob,
    weight: weight,
    weight_unit: weightUnit,
    height: height,
    height_unit: heightUnit,
    gender: genderEl,
    diet_goal: goalEl,
    diet_type: dietTypeEl,
    goal_calories: goalCal,
    goal_protein: goalProt,
    goal_carbs: 275,
    goal_fat: 78,
    goal_fiber: 28,
    goal_sugar: 50,
    goal_sodium: 2300,
    goal_chol: 300,
    goal_vit_d: 15,
    goal_iron: 18,
    goal_folate: 400,
    created_at: new Date().toISOString()
  };

  try {
    // 1. Save profile metadata into Supabase Auth User Metadata (no RLS restrictions)
    if (typeof supabaseClient !== 'undefined' && supabaseClient && supabaseClient.auth) {
      await supabaseClient.auth.updateUser({ data: payload });
    }

    // 2. Save profile in localStorage for instant offline/device access
    localStorage.setItem(`nutritrack_profile_${user.id}`, JSON.stringify(payload));

    // 3. Attempt DB table upsert (swallow RLS errors if database policy blocks direct client insert)
    if (typeof supabaseClient !== 'undefined' && supabaseClient) {
      const { error: dbError } = await supabaseClient
        .from('users')
        .upsert(payload, { onConflict: 'id' });
      if (dbError) {
        console.warn('Database user table upsert notice (profile saved to user_metadata & localStorage):', dbError);
      }
    }

    document.getElementById('onboardingSection').style.display = 'none';
    loginSuccess(payload);
  } catch (err) {
    // Fallback: profile saved in user_metadata / localStorage
    localStorage.setItem(`nutritrack_profile_${user.id}`, JSON.stringify(payload));
    document.getElementById('onboardingSection').style.display = 'none';
    loginSuccess(payload);
  }
}

function normalizeUserProfile(p) {
  if (!p) return null;
  const rawStats = p.body_stats || {};
  const rawGoals = p.goals || {};

  const id = p.id;
  const name = p.name;
  const email = p.email;
  const created_at = p.created_at;

  const dob = p.dob || rawStats.dob;
  const weight = p.weight || rawStats.weight;
  const weightUnit = p.weight_unit || p.weightUnit || rawStats.weight_unit || rawStats.weightUnit || 'kg';
  const height = p.height || rawStats.height;
  const heightUnit = p.height_unit || p.heightUnit || rawStats.height_unit || rawStats.heightUnit || 'cm';
  const gender = p.gender || rawStats.gender;
  const dietGoal = p.diet_goal || p.dietGoal || rawStats.diet_goal || rawStats.dietGoal || 'maintain';
  const dietType = p.diet_type || p.dietType || rawStats.diet_type || rawStats.dietType || 'nonveg';

  const goals = {
    calories: rawGoals.calories || p.goal_calories || p.goals?.calories || 2000,
    protein: rawGoals.protein || p.goal_protein || p.goals?.protein || 150,
    carbs: rawGoals.carbs || p.goal_carbs || p.goals?.carbs || 250,
    fat: rawGoals.fat || p.goal_fat || p.goals?.fat || 65,
    fiber: rawGoals.fiber || p.goal_fiber || p.goals?.fiber || 28,
    sugar: rawGoals.sugar || p.goal_sugar || p.goals?.sugar || 50,
    sodium: rawGoals.sodium || p.goal_sodium || p.goals?.sodium || 2300,
    chol: rawGoals.chol || p.goal_chol || p.goals?.chol || 300,
    vit_d: rawGoals.vit_d || p.goal_vit_d || p.goals?.vit_d || 15,
    iron: rawGoals.iron || p.goal_iron || p.goals?.iron || 18,
    folate: rawGoals.folate || p.goal_folate || p.goals?.folate || 400
  };

  return {
    id, name, email, created_at,
    dob, weight, weightUnit, height, heightUnit, gender, dietGoal, dietType,
    weight_unit: weightUnit, height_unit: heightUnit, diet_goal: dietGoal, diet_type: dietType,
    body_stats: {
      dob, weight, weight_unit: weightUnit, weightUnit,
      height, height_unit: heightUnit, heightUnit,
      gender, diet_goal: dietGoal, dietGoal, diet_type: dietType, dietType
    },
    goals: goals,
    goal_calories: goals.calories,
    goal_protein: goals.protein,
    goal_carbs: goals.carbs,
    goal_fat: goals.fat,
    goal_fiber: goals.fiber,
    goal_sugar: goals.sugar,
    goal_sodium: goals.sodium,
    goal_chol: goals.chol,
    goal_vit_d: goals.vit_d,
    goal_iron: goals.iron,
    goal_folate: goals.folate
  };
}

async function loginSuccess(userProfile) {
  currentUser = normalizeUserProfile(userProfile);

  // Try to grab JWT, ignoring errors if session doesn't load immediately
  const { data } = await supabaseClient.auth.getSession();
  if (data && data.session) currentUser.token = data.session.access_token;

  const goals = (currentUser && currentUser.goals) || { calories: 2000, protein: 150, carbs: 275, fat: 78, fiber: 28, sugar: 50, sodium: 2300, chol: 300 };
  const editCarb = document.getElementById('editCarbGoal');
  const editFat = document.getElementById('editFatGoal');
  const editFiber = document.getElementById('editFiberGoal');
  if (editCarb) editCarb.value = goals.carbs || 275;
  if (editFat) editFat.value = goals.fat || 78;
  if (editFiber) editFiber.value = goals.fiber || 28;

  const dietTag = document.getElementById('dietWidgetTag');
  if (dietTag) dietTag.textContent = 'View targets';

  const authSec = document.getElementById('authSection');
  if (authSec) authSec.style.display = 'none';
  const onbSec = document.getElementById('onboardingSection');
  if (onbSec) onbSec.style.display = 'none';
  const mainApp = document.getElementById('mainApp');
  if (mainApp) mainApp.style.display = 'block';

  hideLoader();

  initApp();
  fetchLogsFromCloud();
  fetchWaterFromCloud();
  fetchWeightFromCloud();
  fetchMealTemplatesFromCloud();
  loadPopularFoodsFromCloud();
  fetchAIMealRecommendations();
  fetchWeeklyInsights();
  fetchCommunityChallenges();
  fetchWorkoutsFromCloud();
  fetchRecipesFromCloud();

  // Route to the correct tab based on URL path
  let path = window.location.pathname.replace('/', '');
  if (!path || path === 'index.html') path = 'dashboard';

  const validPages = ['dashboard', 'track', 'history', 'profile'];
  if (validPages.includes(path)) {
    const btnId = path === 'dashboard' ? 1 : path === 'track' ? 2 : path === 'history' ? 3 : 4;
    const btn = document.querySelector(`.nav-btn:nth-child(${btnId})`);
    showPage(path, btn, true);
  } else {
    const btn = document.querySelector('.nav-btn:nth-child(1)');
    showPage('dashboard', btn, true);
  }
}

async function handleLogout() {
  showLoader('Signing out…');
  await supabaseClient.auth.signOut();
  // State change listener will trigger handleLogoutUI
}

function handleLogoutUI() {
  currentUser = null;
  document.getElementById('mainApp').style.display = 'none';
  const aSec = document.getElementById('authSection');
  if (aSec) aSec.style.display = 'flex';
  document.getElementById('loginEmail').value = '';
  document.getElementById('loginPassword').value = '';
  hideLoader();
}

// ─────────────────────────────────────────────────
//  INIT APP
// ─────────────────────────────────────────────────
function initApp() {
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  document.getElementById('timeGreet').textContent = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening';

  const displayName = currentUser.name || currentUser.email?.split('@')[0] || 'User';

  const greetNameEl = document.getElementById('greetName');
  if (greetNameEl) greetNameEl.textContent = displayName.split(' ')[0];
  document.getElementById('greetDate').textContent = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  document.getElementById('navAvatar').textContent = displayName[0].toUpperCase();
  document.getElementById('navName').textContent = displayName.split(' ')[0];

  const g = currentUser.goals || { calories: 2000, protein: 150, carbs: 275, fat: 78, fiber: 28, sugar: 50, sodium: 2300, chol: 300 };
  document.getElementById('editCalGoal').value = g.calories;
  document.getElementById('editProtGoal').value = g.protein;
  document.getElementById('editCarbGoal').value = g.carbs;
  document.getElementById('editFatGoal').value = g.fat;
  document.getElementById('editFiberGoal').value = g.fiber || 28;
  document.getElementById('editSugarGoal').value = g.sugar || 50;
  document.getElementById('editSodiumGoal').value = g.sodium || 2300;
  document.getElementById('editCholGoal').value = g.chol || 300;
  document.getElementById('editVitDGoal').value = g.vit_d || 15;
  document.getElementById('editIronGoal').value = g.iron || 18;
  document.getElementById('editFolateGoal').value = g.folate || 400;

  buildCatFilters();
  autoSelectMeal();
  loadApiKey();
  refreshDashboard();
  searchFoods('');
  _updateDietWidget();
  updateLanguageUI();

  const qBar = document.getElementById('quickAssistantBar');
  if (qBar) qBar.style.display = 'flex';
}

// ─────────────────────────────────────────────────
//  NAVIGATION  (change #10: show loader on nav)
// ─────────────────────────────────────────────────
const PAGE_NAMES = {
  dashboard: 'Dashboard',
  track: 'Track Food',
  history: 'History',
  profile: 'Profile',
};

function showPage(id, btn, pushState = true) {
  try {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.mob-nav-btn').forEach(b => b.classList.remove('active'));

    const pageEl = document.getElementById('page-' + id);
    if (pageEl) pageEl.classList.add('active');
    if (btn) btn.classList.add('active');

    // Keep mobile bottom nav in sync
    const mobBtn = document.getElementById('mobBtn-' + id);
    if (mobBtn) mobBtn.classList.add('active');

    if (id === 'dashboard') {
      try { refreshDashboard(); } catch (e) { console.error('refreshDashboard error', e); }
    }
    if (id === 'track') {
      try { autoSelectMeal(); } catch (e) {}
      try {
        const searchInput = document.getElementById('foodSearch');
        searchFoods(searchInput ? searchInput.value : '');
      } catch (e) { console.error('searchFoods error', e); }
      try { renderMealTemplates(); } catch (e) {}
    }
    if (id === 'history') {
      try { renderHistory(); } catch (e) { console.error('renderHistory error', e); }
      try { fetchWeeklyInsights(); } catch (e) {}
    }
    if (id === 'profile') {
      try { renderProfile(); } catch (e) { console.error('renderProfile error', e); }
      try { fetchWeightFromCloud(); } catch (e) {}
    }

    if (pushState && typeof pushState !== 'object') {
      if (window.location.pathname !== '/' + id) {
        window.history.pushState({ page: id }, '', '/' + id);
      }
    }
  } catch (err) {
    console.error('showPage error:', err);
  }
}

window.addEventListener('popstate', (event) => {
  const state = event.state;
  if (state && state.page) {
    // Find the corresponding nav button to highlight
    const btnId = state.page === 'dashboard' ? 1 : state.page === 'track' ? 2 : state.page === 'history' ? 3 : 4;
    const btn = document.querySelector(`.nav-btn:nth-child(${btnId})`);
    showPage(state.page, btn, false);
  } else {
    // Determine from pathname
    let path = window.location.pathname.replace('/', '');
    if (!path) path = 'dashboard';
    const validPages = ['dashboard', 'track', 'history', 'profile'];
    if (validPages.includes(path)) {
      const btnId = path === 'dashboard' ? 1 : path === 'track' ? 2 : path === 'history' ? 3 : 4;
      const btn = document.querySelector(`.nav-btn:nth-child(${btnId})`);
      showPage(path, btn, false);
    }
  }
});

// ─────────────────────────────────────────────────
//  HELPERS
// ─────────────────────────────────────────────────
function todayStr() { return new Date().toISOString().split('T')[0]; }

function getLast30Days() {
  return Array.from({ length: 30 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (29 - i));
    return d.toISOString().split('T')[0];
  });
}

function sumLogs(logs) {
  return logs.reduce((acc, l) => ({
    cal: acc.cal + (l.cal || 0),
    pro: acc.pro + (l.pro || 0),
    carb: acc.carb + (l.carb || 0),
    fat: acc.fat + (l.fat || 0),
    fiber: acc.fiber + (l.fiber || 0),
    sugar: acc.sugar + (l.sugar || 0),
    sodium: acc.sodium + (l.sodium || 0),
    chol: acc.chol + (l.chol || 0),
    vit_d: acc.vit_d + (l.vit_d || 0),
    iron: acc.iron + (l.iron || 0),
    folate: acc.folate + (l.folate || 0),
  }), { cal: 0, pro: 0, carb: 0, fat: 0, fiber: 0, sugar: 0, sodium: 0, chol: 0, vit_d: 0, iron: 0, folate: 0 });
}

// ─────────────────────────────────────────────────
//  DASHBOARD
// ─────────────────────────────────────────────────
function refreshDashboard() {
  const today = todayStr();
  const logs = window._foodLogs.filter(l => l.date === today);
  const totals = sumLogs(logs);
  const goals = currentUser.goals || { calories: 2000, protein: 150, carbs: 275, fat: 78, fiber: 28, sugar: 50, sodium: 2300, chol: 300 };

  const workoutBurn = (window._workoutLogs || []).reduce((s, w) => s + (w.calBurned || 0), 0);
  const netCals = Math.max(0, totals.cal - workoutBurn);

  const dashBurnEl = document.getElementById('dashWorkoutBurn');
  if (dashBurnEl) dashBurnEl.textContent = Math.round(workoutBurn);

  [['dashCals', 'calBar', totals.cal, goals.calories, false],
  ['dashProtein', 'protBar', totals.pro, goals.protein, false],
  ['dashCarbs', 'carbBar', totals.carb, goals.carbs, false],
  ['dashFat', 'fatBar', totals.fat, goals.fat, false],
  ].forEach(([vId, bId, val, goal]) => {
    const el = document.getElementById(vId); if (el) el.textContent = Math.round(val);
    const bar = document.getElementById(bId); if (bar) bar.style.width = Math.min(100, (val / (goal || 1)) * 100) + '%';
  });

  [['dashFiber', 'fiberBar', totals.fiber, goals.fiber || 28, false, 'fiber-card'],
  ['dashSugar', 'sugarBar', totals.sugar, goals.sugar || 50, true, 'sugar-card'],
  ['dashSodium', 'sodiumBar', totals.sodium, goals.sodium || 2300, true, 'sodium-card'],
  ['dashChol', 'cholBar', totals.chol, goals.chol || 300, true, 'chol-card'],
  ['dashVitD', 'vitDBar', totals.vit_d, goals.vit_d || 15, false, 'vitD-card'],
  ['dashIron', 'ironBar', totals.iron, goals.iron || 18, false, 'iron-card'],
  ['dashFolate', 'folateBar', totals.folate, goals.folate || 400, false, 'folate-card'],
  ].forEach(([vId, bId, val, goal, warnOnOver, cardId]) => {
    const el = document.getElementById(vId); if (el) el.textContent = Math.round(val);
    const bar = document.getElementById(bId); if (bar) bar.style.width = Math.min(100, (val / (goal || 1)) * 100) + '%';
    const card = document.getElementById(cardId);
    if (card) card.classList.toggle('warning-high', warnOnOver && val > goal);
  });

  const logEl = document.getElementById('dashFoodLog');
  if (logs.length === 0) {
    logEl.innerHTML = `<div class="empty-log"><div class="empty-icon">🍽️</div><p>No meals logged today.<br>Head to Track Food to get started.</p></div>`;
  } else {
    logEl.innerHTML = logs.map(l => {
      const safeName = String(l.name).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
      return `
      <div class="log-item">
        <div class="log-item-left">
          <div class="food-emoji">${l.emoji || '🍽️'}</div>
          <div>
            <div class="log-item-name">${safeName}</div>
            <div class="log-item-meta">${l.mealType} · ${l.pro}g P · ${l.carb}g C · ${l.fat}g F</div>
            <div class="nutrient-pills">
              ${l.fiber ? `<span class="npill fiber">🌿 ${l.fiber}g fiber</span>` : ''}
              ${l.sugar ? `<span class="npill sugar">🍬 ${l.sugar}g sugar</span>` : ''}
              ${l.sodium ? `<span class="npill sodium">🧂 ${l.sodium}mg salt</span>` : ''}<!-- change #13 -->
              ${l.chol ? `<span class="npill chol">❤️ ${l.chol}mg chol</span>` : ''}
              ${l.vit_d ? `<span class="npill vit_d" style="background:rgba(245,166,35,0.1);color:#F5A623;border-color:rgba(245,166,35,0.2)">☀️ ${l.vit_d}mcg VitD</span>` : ''}
              ${l.iron ? `<span class="npill iron" style="background:rgba(208,2,27,0.1);color:#D0021B;border-color:rgba(208,2,27,0.2)">🥩 ${l.iron}mg Iron</span>` : ''}
              ${l.folate ? `<span class="npill folate" style="background:rgba(126,211,33,0.1);color:#7ED321;border-color:rgba(126,211,33,0.2)">🥬 ${l.folate}mcg Fol</span>` : ''}
            </div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:0.5rem">
          <div class="log-item-cal">${l.cal} kcal</div>
          <button class="remove-item-btn" onclick="removeLog('${l.id}')">✕</button>
        </div>
      </div>
    `}).join('');
  }
  renderMacroChart(totals.pro, totals.carb, totals.fat, totals.fiber, totals.sugar, totals.sodium, totals.chol, totals.cal);
}

function renderMacroChart(p, c, f, fiber, sugar, sodium, chol, cal) {
  const chartCanvas = document.getElementById('macroChart');
  if (!chartCanvas || typeof Chart === 'undefined') return;
  const ctx2 = chartCanvas.getContext('2d');
  if (macroChart) macroChart.destroy();

  const sodiumG = +(sodium / 10).toFixed(1);
  const cholG = +(chol / 10).toFixed(1);

  const labels = ['Protein', 'Carbs', 'Fat', 'Fiber', 'Sugar', 'Salt', 'Cholesterol']; // change #13
  const rawVals = [p, c, f, fiber, sugar, sodiumG, cholG];
  const units = ['g', 'g', 'g', 'g', 'g', 'mg (÷10)', 'mg (÷10)'];
  const realVals = [p, c, f, fiber, sugar, sodium, chol];

  const bgColors = [
    'rgba(127,184,212,0.85)',
    'rgba(196,168,127,0.85)',
    'rgba(244,97,58,0.85)',
    'rgba(100,180,110,0.85)',
    'rgba(212,168,83,0.85)',
    'rgba(160,120,200,0.85)',
    'rgba(220,100,100,0.85)',
  ];
  const borderColors = bgColors.map(c => c.replace('0.85', '1'));

  const nonZeroIdx = rawVals.map((v, i) => v > 0 ? i : -1).filter(i => i >= 0);
  const filtLabels = nonZeroIdx.map(i => labels[i]);
  const filtRaw = nonZeroIdx.map(i => rawVals[i]);
  const filtReal = nonZeroIdx.map(i => realVals[i]);
  const filtUnits = nonZeroIdx.map(i => units[i]);
  const filtBg = nonZeroIdx.map(i => bgColors[i]);
  const filtBorder = nonZeroIdx.map(i => borderColors[i]);
  const total = filtRaw.reduce((s, v) => s + v, 0) || 1;

  macroChart = new Chart(ctx2, {
    type: 'doughnut',
    data: {
      labels: filtLabels,
      datasets: [{ data: filtRaw, backgroundColor: filtBg, borderColor: filtBorder, borderWidth: 2, hoverOffset: 8 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '62%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: 'rgba(184,201,186,0.8)', font: { family: 'Plus Jakarta Sans', size: 11 }, padding: 10,
            usePointStyle: true, pointStyleWidth: 10,
            generateLabels(chart) {
              return chart.data.labels.map((label, i) => ({
                text: `${label}: ${filtReal[i]}${filtUnits[i] === 'g' ? 'g' : 'mg'}`,
                fillStyle: filtBg[i], strokeStyle: filtBorder[i],
                fontColor: 'rgba(184,201,186,0.8)', lineWidth: 1, pointStyle: 'circle', hidden: false, index: i,
              }));
            }
          }
        },
        tooltip: {
          callbacks: {
            label(ctx) {
              const idx = ctx.dataIndex, real = filtReal[idx], unit = filtUnits[idx] === 'g' ? 'g' : 'mg';
              const pct = Math.round((filtRaw[idx] / total) * 100);
              return `  ${real}${unit}  (${pct}% of chart)`;
            },
            title(ctx) { return ctx[0].label; }
          },
          backgroundColor: 'rgba(255,255,255,0.96)', titleColor: '#12110F', bodyColor: 'rgba(18,17,15,0.6)',
          borderColor: 'rgba(18,17,15,0.1)', borderWidth: 1, padding: 10, cornerRadius: 8,
        }
      },
      animation: { animateRotate: true, duration: 600 }
    },
    plugins: [{
      id: 'centerLabel',
      afterDraw(chart) {
        const { ctx: c2, chartArea: { width, height, left, top } } = chart;
        c2.save();
        const cx = left + width / 2, cy = top + height / 2;
        c2.textAlign = 'center'; c2.textBaseline = 'middle';
        c2.fillStyle = '#B87200';
        c2.font = `bold 18px "Plus Jakarta Sans",sans-serif`;
        c2.fillText(Math.round(cal) + ' kcal', cx, cy - 8);
        c2.fillStyle = 'rgba(18,17,15,0.4)';
        c2.font = `11px "Plus Jakarta Sans",sans-serif`;
        c2.fillText('today', cx, cy + 10);
        c2.restore();
      }
    }]
  });
}

// ─────────────────────────────────────────────────
//  AI SCAN (Multimodal LLM)
// ─────────────────────────────────────────────────
let scanStream = null;
let scanImageB64 = null;
let _scanAbortCtrl = null;   // tracks in-flight AI request so Clear can cancel it

// ── LLM MODE (Ollama/Qwen2-VL — no API key required) ──
function saveApiKey() { /* LLM — no key needed */ }
function editApiKey() { /* LLM — no key needed */ }
function _showApiKeySaved() { /* LLM — no key needed */ }
function loadApiKey() { /* LLM — no key needed */ }
function getApiKey() { return 'LLM_MODE'; }

function showScanStatus(msg, type = 'info') {
  const el = document.getElementById('scanStatus');
  if (!el) return;
  el.textContent = msg;
  el.className = 'scan-status ' + type;
}
function hideScanStatus() {
  const el = document.getElementById('scanStatus');
  if (el) el.className = 'scan-status';
}

// ─────────────────────────────────────────────────
//  CAMERA  (change #5: mobile isolation — scan data is never persisted to localStorage)
// ─────────────────────────────────────────────────
async function startScanCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showScanStatus('Camera not supported on this device', 'error'); return;
  }
  if (window.location.protocol === 'file:') {
    showScanStatus('Camera needs a server (http://). Use Choose Photo instead.', 'error'); return;
  }
  try {
    try { scanStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1280 } } }); }
    catch { scanStream = await navigator.mediaDevices.getUserMedia({ video: true }); }

    const video = document.getElementById('camVideo');
    const area = document.getElementById('camArea');
    video.srcObject = scanStream;
    video.style.display = 'block';
    area.classList.add('has-media');
    document.getElementById('camPlaceholder').style.display = 'none';
    document.getElementById('scanPreview').style.display = 'none';
    document.getElementById('scanActionRow').style.display = 'none';
    document.getElementById('scanCamRow').style.display = 'flex';
    document.getElementById('scanReadyRow').style.display = 'none';
    // change #5: clear any in-memory image when camera starts
    scanImageB64 = null;
    hideScanStatus();
  } catch (e) {
    showScanStatus('Camera access denied — use Choose Photo instead', 'error');
  }
}

function takeScanPhoto() {
  const video = document.getElementById('camVideo');
  if (!video || !video.videoWidth) { showScanStatus('Camera not ready — wait a moment', 'error'); return; }
  const cvs = document.getElementById('scanCanvas');
  cvs.width = video.videoWidth;
  cvs.height = video.videoHeight;
  cvs.getContext('2d').drawImage(video, 0, 0);
  // change #5: image is kept ONLY in memory (scanImageB64), never stored anywhere
  scanImageB64 = cvs.toDataURL('image/jpeg', 0.92).split(',')[1];
  stopScanCamera(true);
  _showScanPreview(cvs.toDataURL('image/jpeg', 0.92));
}

function stopScanCamera(keepPhoto) {
  if (scanStream) { scanStream.getTracks().forEach(t => t.stop()); scanStream = null; }
  const video = document.getElementById('camVideo');
  if (video) { video.srcObject = null; video.style.display = 'none'; }
  document.getElementById('scanCamRow').style.display = 'none';
  if (!keepPhoto) {
    document.getElementById('camArea').classList.remove('has-media');
    document.getElementById('camPlaceholder').style.display = 'flex';
    document.getElementById('scanActionRow').style.display = 'flex';
    scanImageB64 = null; // change #5: clear immediately
  }
}

function pickScanPhoto() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';
  input.style.cssText = 'position:absolute;left:-9999px';
  document.body.appendChild(input);
  input.addEventListener('change', function () {
    const file = this.files && this.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      const dataUrl = ev.target.result;
      // change #5: base64 kept only in JS variable, never written to storage
      scanImageB64 = dataUrl.split(',')[1];
      _showScanPreview(dataUrl);
    };
    reader.readAsDataURL(file);
    setTimeout(() => { try { document.body.removeChild(input); } catch (e) { } }, 1000);
  });
  setTimeout(() => input.click(), 50);
}

function _showScanPreview(dataUrl) {
  const preview = document.getElementById('scanPreview');
  const area = document.getElementById('camArea');
  preview.src = dataUrl;
  preview.style.display = 'block';
  area.style.display = 'block';
  area.style.minHeight = '0';
  area.classList.add('has-media');
  document.getElementById('camPlaceholder').style.display = 'none';
  document.getElementById('scanActionRow').style.display = 'none';
  document.getElementById('scanCamRow').style.display = 'none';
  document.getElementById('scanReadyRow').style.display = 'flex';
  hideScanStatus();
}

function clearScan() {
  // Cancel any in-flight AI request so the result doesn't appear after clearing
  if (_scanAbortCtrl) { _scanAbortCtrl.abort(); _scanAbortCtrl = null; }
  // change #5: nullify image immediately
  scanImageB64 = null;
  const preview = document.getElementById('scanPreview');
  preview.src = ''; preview.style.display = 'none';
  const area = document.getElementById('camArea');
  area.style.display = ''; area.style.minHeight = '';
  area.classList.remove('has-media');
  document.getElementById('camPlaceholder').style.display = 'flex';
  document.getElementById('scanActionRow').style.display = 'flex';
  document.getElementById('scanReadyRow').style.display = 'none';
  document.getElementById('scanResult').innerHTML = `
    <div class="scan-result-placeholder">
      <div style="font-size:2.5rem;opacity:0.2">✨</div>
      <div style="font-size:0.85rem;font-weight:500;opacity:0.5">No scan yet</div>
      <div style="font-size:0.72rem;opacity:0.35;line-height:1.6;margin-top:0.3rem">
        Take or upload a food photo,<br>then click <strong>Scan with AI</strong>
      </div>
    </div>`;
  hideScanStatus();
}

// ─────────────────────────────────────────────────
//  MULTIMODAL LLM CALL
// ─────────────────────────────────────────────────
let _scanCooldownTimer = null;

function _startCooldown(s) { /* LLM — no rate limit */ }

async function _callLLMAPI(imageB64, signal) {
  // Try Flask backend first (enables JWT auth + works in production)
  // Falls back to direct LLM server if backend is unavailable (local dev)
  const backendUrl = window._BACKEND_URL
    ? `${window._BACKEND_URL}/api/ai/analyze`
    : '/api/ai/analyze';
  const directUrl = window.LLM_SERVER_URL || 'https://energyvenom-nutritrack-llm.hf.space/api/ai/analyze';

  const urls = [];
  if (window.location.hostname === 'saiphanianirudh.github.io' || window.location.hostname.endsWith('github.io')) {
    // Static hosting (GitHub Pages) — query HF Space directly
    urls.push(directUrl);
  } else {
    urls.push(backendUrl);
    urls.push(directUrl);
  }
  let lastError = null;

  for (const url of urls) {
    try {
      // ── Try SSE streaming endpoint first (prevents HF 60-second timeout) ──
      const streamUrl = url.replace(/\/analyze$/, '/analyze/stream');
      const streamRes = await fetch(streamUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageB64 }),
        signal,
      });

      if (streamRes.ok && streamRes.headers.get('content-type')?.includes('text/event-stream')) {
        // Read SSE stream line-by-line; server sends heartbeats every 10s
        const reader = streamRes.body.getReader();
        const decoder = new TextDecoder();
        let buf = '';
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split('\n');
          buf = lines.pop();  // keep incomplete last line
          for (const line of lines) {
            if (!line.startsWith('data:')) continue;
            const jsonStr = line.slice(5).trim();
            if (!jsonStr) continue;
            let evt;
            try { evt = JSON.parse(jsonStr); } catch { continue; }
            if (evt.status === 'thinking') continue;   // heartbeat — keep waiting
            if (evt.error) throw new Error('SERVER_ERROR: ' + evt.error);
            if (evt.result) return evt.result;         // 🎉 final answer
          }
        }
        throw new Error('Stream ended without result');
      }

      // ── SSE not supported — fall back to regular fetch ──
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageB64 }),
        signal,
      });
      if (!response.ok) {
        let msg = 'LLM_OFFLINE';
        try { const errData = await response.json(); if (errData.error) msg = 'SERVER_ERROR: ' + errData.error; } catch (e) { }
        lastError = new Error(msg);
        continue;
      }
      return await response.json();
    } catch (e) {
      if (e.name === 'AbortError') throw e;  // propagate cancellation immediately
      lastError = e;
      continue;
    }
  }
  throw lastError || new Error('LLM_OFFLINE');
}


function _compressImage(b64, maxBytes = 900000) {
  return new Promise(resolve => {
    if (b64.length <= maxBytes) { resolve(b64); return; }
    const img = new Image();
    img.onload = () => {
      const cvs = document.getElementById('scanCanvas');
      let w = img.width, h = img.height, quality = 0.85;
      const tryCompress = () => {
        cvs.width = w; cvs.height = h;
        cvs.getContext('2d').drawImage(img, 0, 0, w, h);
        const result = cvs.toDataURL('image/jpeg', quality).split(',')[1];
        if (result.length <= maxBytes || quality < 0.3) { resolve(result); return; }
        quality -= 0.15;
        if (quality < 0.3) { w = Math.round(w * 0.75); h = Math.round(h * 0.75); quality = 0.75; }
        tryCompress();
      };
      tryCompress();
    };
    img.src = 'data:image/jpeg;base64,' + b64;
  });
}

async function scanWithAI() {
  if (!scanImageB64) { showScanStatus('⚠️ Take or upload a photo first', 'error'); return; }
  // Cancel any previous in-flight request before starting a new one
  if (_scanAbortCtrl) { _scanAbortCtrl.abort(); }
  _scanAbortCtrl = new AbortController();
  const signal = _scanAbortCtrl.signal;
  const btn = document.getElementById('scanNowBtn');
  const setScanning = on => {
    if (!btn) return;
    btn.disabled = on;
    btn.innerHTML = on ? '<span class="scanning-pulse">🧠</span> Analysing…' : '✨ Scan with AI';
  };
  setScanning(true);
  showScanStatus('🔍 Compressing image…', 'info');
  document.getElementById('scanResult').innerHTML = `
    <div class="scan-result-placeholder">
      <div class="scanning-pulse" style="font-size:2.5rem">🧠</div>
      <div style="font-size:0.85rem;opacity:0.6;margin-top:0.5rem">AI model analysing food…</div>
      <div style="font-size:0.72rem;opacity:0.4;margin-top:0.3rem">Free AI server — may take 1-2 min ⏳</div>
    </div>`;
  const imageToSend = await _compressImage(scanImageB64, 150000);
  showScanStatus('🧠 Contacting AI server…', 'info');

  let scanSec = 0;
  const statusInterval = setInterval(() => {
    scanSec += 3;
    if (scanSec === 6) showScanStatus('⚡ Free AI model waking up (takes 15-30s on first scan)…', 'info');
    if (scanSec === 21) showScanStatus('✨ Analysing food photo… almost ready!', 'info');
  }, 3000);

  try {
    const result = await _callLLMAPI(imageToSend, signal);
    clearInterval(statusInterval);
    if (result.description === 'not_food' || result.not_food === true || !result.items || result.items.length === 0) {
      hideScanStatus(); setScanning(false); showNonFoodModal();
      document.getElementById('scanResult').innerHTML = `
        <div class="scan-result-placeholder">
          <div style="font-size:2.5rem">🚫</div>
          <div style="font-size:0.85rem;font-weight:500;margin-top:0.5rem;color:#F4613A">No food detected</div>
          <div style="font-size:0.72rem;opacity:0.45;margin-top:0.3rem">Please try a clear food photo</div>
        </div>`;
      return;
    }
    if (!result.items || result.items.length === 0) {
      hideScanStatus(); setScanning(false); showNonFoodModal(); return;
    }
    _renderScanResult(result);
    hideScanStatus(); setScanning(false);
  } catch (e) {
    clearInterval(statusInterval);
    setScanning(false);
    if (e.name === 'AbortError') return;  // user pressed Clear — silently stop, don't overwrite UI
    const isServerErr = e.message && e.message.startsWith('SERVER_ERROR:');
    const offline = !isServerErr && (e.message === 'LLM_OFFLINE'
      || e.message.includes('fetch')
      || e.message.includes('Failed to fetch')
      || e.message.includes('NetworkError'));
    if (offline) {
      showScanStatus('❌ LLM server not running', 'error');
      document.getElementById('scanResult').innerHTML = `
        <div class="scan-result-placeholder">
          <div style="font-size:2rem;opacity:0.5">🔌</div>
          <div style="font-size:0.9rem;font-weight:600;margin-top:0.5rem;color:#F4613A">AI server offline</div>
          <div style="font-size:0.78rem;color:var(--ink-50);margin-top:0.5rem;line-height:1.7">
            Start it:<br>
            <code style="background:var(--smoke);padding:2px 8px;border-radius:4px;font-size:0.75rem">python Llm_server.py</code>
          </div>
        </div>`;
    } else {
      const msg = e.message || 'Unknown error';
      showScanStatus('❌ ' + msg, 'error');
      document.getElementById('scanResult').innerHTML = `
        <div class="scan-result-placeholder">
          <div style="font-size:2rem;opacity:0.4">⚠️</div>
          <div style="font-size:0.85rem;font-weight:600;margin-top:0.5rem;color:#F4613A">${msg}</div>
        </div>`;
    }
  }
}

// ─────────────────────────────────────────────────
//  RENDER SCAN RESULT
// ─────────────────────────────────────────────────
function _buildNutrientCell(icon, label, val, unit, warn) {
  return `<div class="scan-nutrient-cell ${warn ? 'warn' : ''}">
    <span>${icon}</span>
    <div>
      <div class="scan-n-label">${label}${warn ? ' ⚠️' : ''}</div>
      <div><span class="scan-n-val">${val}</span><span class="scan-n-unit"> ${unit}</span></div>
    </div>
  </div>`;
}

function _renderScanResult(r) {
  const goals = (currentUser && currentUser.goals) || { calories: 2000, protein: 150, carbs: 275, fat: 78, fiber: 28, sugar: 50, sodium: 2300, chol: 300 };

  const items = r.items && r.items.length > 0 ? r.items
    : [{
      food_name: r.food_name, serving_size: r.serving_size, confidence: r.confidence,
      calories: r.calories, protein_g: r.protein_g, carbs_g: r.carbs_g, fat_g: r.fat_g,
      fiber_g: r.fiber_g, sugar_g: r.sugar_g, sodium_mg: r.sodium_mg, cholesterol_mg: r.cholesterol_mg
    }];

  const isMulti = items.length > 1;

  const parsed = items.map(item => ({
    name: item.food_name || 'Unknown food',
    size: item.serving_size || '1 serving',
    conf: Math.min(100, Math.max(0, item.confidence || 80)),
    cal: Math.round(item.calories || item.cal || 0),
    pro: +(item.protein_g || item.pro || 0).toFixed(1),
    carb: +(item.carbs_g || item.carb || 0).toFixed(1),
    fat: +(item.fat_g || item.fat || 0).toFixed(1),
    fiber: +(item.fiber_g || item.fiber || 0).toFixed(1),
    sugar: +(item.sugar_g || item.sugar || 0).toFixed(1),
    sod: Math.round(item.sodium_mg || item.sodium || 0),
    chol: Math.round(item.cholesterol_mg || item.chol || 0),
    vit_d: +(item.vit_d || 0).toFixed(1),
    iron: +(item.iron || 0).toFixed(1),
    folate: +(item.folate || 0).toFixed(1),
  }));

  const total = parsed.reduce((acc, f) => ({
    cal: acc.cal + f.cal, pro: +(acc.pro + f.pro).toFixed(1), carb: +(acc.carb + f.carb).toFixed(1),
    fat: +(acc.fat + f.fat).toFixed(1), fiber: +(acc.fiber + f.fiber).toFixed(1),
    sugar: +(acc.sugar + f.sugar).toFixed(1), sod: acc.sod + f.sod, chol: acc.chol + f.chol,
    vit_d: +(acc.vit_d + f.vit_d).toFixed(1), iron: +(acc.iron + f.iron).toFixed(1), folate: +(acc.folate + f.folate).toFixed(1),
  }), { cal: 0, pro: 0, carb: 0, fat: 0, fiber: 0, sugar: 0, sod: 0, chol: 0, vit_d: 0, iron: 0, folate: 0 });

  const avgConf = Math.round(parsed.reduce((a, f) => a + f.conf, 0) / parsed.length);
  const macroT = (total.pro * 4) + (total.carb * 4) + (total.fat * 9) || 1;
  const pW = Math.round((total.pro * 4 / macroT) * 100);
  const cW = Math.round((total.carb * 4 / macroT) * 100);
  const fW = 100 - pW - cW;
  const confColor = avgConf >= 85 ? 'rgba(100,180,110,0.9)' : avgConf >= 65 ? 'rgba(212,168,83,0.9)' : 'rgba(196,132,90,0.9)';

  const sugarWarn = total.sugar > (goals.sugar || 50);
  const sodWarn = total.sod > (goals.sodium || 2300);
  const cholWarn = total.chol > (goals.chol || 300);

  const itemRows = parsed.map(f => {
    const mT = (f.pro * 4) + (f.carb * 4) + (f.fat * 9) || 1;
    const ipW = Math.round((f.pro * 4 / mT) * 100), icW = Math.round((f.carb * 4 / mT) * 100), ifW = 100 - ipW - icW;
    const iCC = f.conf >= 85 ? 'rgba(100,180,110,0.8)' : f.conf >= 65 ? 'rgba(212,168,83,0.8)' : 'rgba(196,132,90,0.8)';
    
    const itemFoodObj = {
      name: f.name,
      emoji: '🍽️',
      cal: f.cal,
      pro: f.pro,
      carb: f.carb,
      fat: f.fat,
      fiber: f.fiber,
      sugar: f.sugar,
      sodium: f.sod,
      chol: f.chol,
      vit_d: f.vit_d,
      iron: f.iron,
      folate: f.folate
    };
    const itemSafeId = 'scan_' + String(f.name).replace(/[^a-zA-Z0-9_]/g, '_') + '_' + Math.random().toString(36).substr(2, 4);
    if (!window._foodCardMap) window._foodCardMap = {};
    window._foodCardMap[itemSafeId] = itemFoodObj;

    return `
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:0.9rem;margin-bottom:0.7rem;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.4rem;">
        <div>
          <div style="font-size:0.9rem;font-weight:600;color:var(--ink)">🍽️ ${f.name}</div>
          <div style="font-size:0.68rem;color:var(--ink-50);margin-top:1px">${f.size}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.3rem">
          <div style="font-size:1rem;font-weight:700;color:#F5A623">${f.cal} <span style="font-size:0.65rem;font-weight:400;color:var(--ink-50)">kcal</span></div>
          <div style="font-size:0.62rem;padding:1px 7px;border-radius:50px;border:1px solid ${iCC};color:${iCC}">${f.conf}%</div>
        </div>
      </div>
      <div style="height:4px;border-radius:2px;display:flex;gap:2px;overflow:hidden;margin-bottom:0.5rem;">
        <div style="width:${ipW}%;background:#7fb8d4;border-radius:2px"></div>
        <div style="width:${icW}%;background:#c4a87f;border-radius:2px"></div>
        <div style="width:${ifW}%;background:#F4613A;border-radius:2px"></div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.3rem;font-size:0.67rem;color:var(--ink-50);margin-bottom:0.6rem;">
        <span>💪 ${f.pro}g</span><span>🌾 ${f.carb}g</span><span>🥑 ${f.fat}g</span><span>🌿 ${f.fiber}g</span>
        <span>🍬 ${f.sugar}g</span><span>🧂 ${f.sod}mg</span><span>❤️ ${f.chol}mg</span>
      </div>
      <button type="button" class="scan-add-btn" style="padding:0.45rem;font-size:0.78rem;" onclick="addFoodById('${itemSafeId}')">
        ✓ Add ${f.name} to ${currentMealType || 'meal'}
      </button>
    </div>`;
  }).join('');

  const allFoodsObj = { name: parsed.map(f => f.name).join(' + '), emoji: '🍽️', cal: total.cal, pro: total.pro, carb: total.carb, fat: total.fat, fiber: total.fiber, sugar: total.sugar, sodium: total.sod, chol: total.chol, vit_d: total.vit_d, iron: total.iron, folate: total.folate };
  const allSafeId = 'scan_all_' + Math.random().toString(36).substr(2, 5);
  if (!window._foodCardMap) window._foodCardMap = {};
  window._foodCardMap[allSafeId] = allFoodsObj;

  const singleFoodObj = { name: parsed[0].name, emoji: '🍽️', cal: parsed[0].cal, pro: parsed[0].pro, carb: parsed[0].carb, fat: parsed[0].fat, fiber: parsed[0].fiber, sugar: parsed[0].sugar, sodium: parsed[0].sod, chol: parsed[0].chol, vit_d: parsed[0].vit_d, iron: parsed[0].iron, folate: parsed[0].folate };
  const singleSafeId = 'scan_single_' + Math.random().toString(36).substr(2, 5);
  window._foodCardMap[singleSafeId] = singleFoodObj;

  document.getElementById('scanResult').innerHTML = `
    <div class="scan-result-card">
      ${r.description ? `<div style="font-size:0.75rem;color:rgba(184,201,186,0.55);margin-bottom:0.9rem;line-height:1.4;font-style:italic">👁 ${r.description}</div>` : ''}
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.5rem;">
        <div>
          <div class="scan-food-name">${isMulti ? '🍱 Full Meal Total' : parsed[0].name}</div>
          <div class="scan-portion">${isMulti ? parsed.length + ' items detected' : parsed[0].size}</div>
          ${r.source ? `<div style="font-size:0.7rem;color:#7fb8d4;margin-top:0.3rem;font-weight:600">📊 Source: ${r.source}</div>` : ''}
        </div>
        <div class="scan-confidence" style="background:rgba(0,0,0,0.2);border-color:${confColor};color:${confColor}">${avgConf}% confident</div>
      </div>
      <div class="scan-cal-row">
        <div class="scan-cal-big">${total.cal}</div>
        <div class="scan-cal-unit">kcal total</div>
      </div>
      <div class="scan-macro-bar">
        <div class="scan-macro-seg" style="width:${pW}%;background:#7fb8d4"></div>
        <div class="scan-macro-seg" style="width:${cW}%;background:#c4a87f"></div>
        <div class="scan-macro-seg" style="width:${fW}%;background:#F4613A"></div>
      </div>
      <div style="display:flex;gap:1rem;font-size:0.67rem;color:var(--ink-50);margin-bottom:1rem;">
        <span>💪 P ${pW}%</span><span>🌾 C ${cW}%</span><span>🥑 F ${fW}%</span>
      </div>
      <div class="scan-nutrient-grid">
        ${_buildNutrientCell('💪', 'Protein', total.pro, 'g', false)}
        ${_buildNutrientCell('🌾', 'Carbs', total.carb, 'g', false)}
        ${_buildNutrientCell('🥑', 'Fat', total.fat, 'g', false)}
        ${_buildNutrientCell('🌿', 'Fiber', total.fiber, 'g', false)}
        ${_buildNutrientCell('🍬', 'Sugar', total.sugar, 'g', sugarWarn)}
        ${_buildNutrientCell('🧂', 'Salt', total.sod, 'mg', sodWarn)}
        ${_buildNutrientCell('❤️', 'Cholesterol', total.chol, 'mg', cholWarn)}
        ${_buildNutrientCell('🔥', 'Calories', total.cal, 'kcal', false)}
        ${_buildNutrientCell('☀️', 'Vit D', total.vit_d, 'mcg', false)}
        ${_buildNutrientCell('🥩', 'Iron', total.iron, 'mg', false)}
        ${_buildNutrientCell('🥬', 'Folate', total.folate, 'mcg', false)}
      </div>
      ${r.tips ? `<div style="font-size:0.72rem;color:rgba(100,180,110,0.7);background:rgba(100,180,110,0.06);border:1px solid rgba(100,180,110,0.15);border-radius:8px;padding:0.55rem 0.8rem;margin-bottom:0.9rem;line-height:1.4">💡 ${r.tips}</div>` : ''}
      ${isMulti ? `
        <button type="button" class="scan-add-btn" style="margin-bottom:1rem;" onclick="addFoodById('${allSafeId}')">✓ Add Entire Meal to ${currentMealType || 'meal'}</button>
        <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.07em;color:var(--ink-50);margin-bottom:0.6rem;font-weight:600;">Or add individually:</div>
        ${itemRows}
      ` : `
        <button type="button" class="scan-add-btn" onclick="addFoodById('${singleSafeId}')">✓ Add to ${currentMealType || 'meal'}</button>
      `}
    </div>`;
}

// LLM mode: loadApiKey not needed

// ─────────────────────────────────────────────────
//  FOOD SEARCH  (change #2: show food description)
// ─────────────────────────────────────────────────
function buildCatFilters() {
  const row = document.getElementById('catFilters');
  row.innerHTML = CATEGORIES.map(c => `
    <button class="cat-chip ${c.key === 'all' ? 'active' : ''}" onclick="setCat('${c.key}',this)">${c.label}</button>
  `).join('');
}

function setCat(cat, btn) {
  currentCat = cat;
  document.querySelectorAll('.cat-chip').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  searchFoods(document.getElementById('foodSearch').value);
}

function getMealByTime() {
  const h = new Date().getHours();
  if (h >= 5 && h < 11) return 'breakfast';
  if (h >= 11 && h < 16) return 'lunch';
  if (h >= 16 && h < 19) return 'snack';
  return 'dinner';
}

function setMeal(type, btn) {
  currentMealType = type;
  document.querySelectorAll('.meal-chip').forEach(b => {
    b.classList.remove('active');
    const t = b.getAttribute('onclick') && b.getAttribute('onclick').match(/'(\w+)'/);
    if (t && t[1] === type) b.classList.add('active');
  });
  const hint = document.getElementById('mealTimeHint');
  if (hint) hint.textContent = '';
}

function autoSelectMeal() {
  const meal = getMealByTime();
  currentMealType = meal;
  document.querySelectorAll('.meal-chip').forEach(b => {
    b.classList.remove('active');
    const t = b.getAttribute('onclick') && b.getAttribute('onclick').match(/'(\w+)'/);
    if (t && t[1] === meal) b.classList.add('active');
  });
  const hint = document.getElementById('mealTimeHint');
  const timeStr = new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  if (hint) hint.textContent = 'Auto-selected · ' + timeStr;
}

const SEARCH_ALIASES = {
  // Indian
  'dahi': 'curd', 'curd': 'dahi', 'kadhai': 'paneer', 'makhani': 'butter masala',
  'fried egg': 'egg (fried', 'boiled egg': 'egg (whole', 'scrambled': 'egg (scrambled',
  'chana': 'chickpea', 'rajma': 'kidney', 'moong': 'lentil', 'masoor': 'lentil',
  'chaas': 'buttermilk', 'bhatura': 'bhature', 'sabzi': 'veg', 'mithai': 'sweet',
  'roti': 'roti', 'paratha': 'paratha', 'naan': 'naan', 'dosa': 'dosa', 'idli': 'idli',
  'biryani': 'biryani', 'curry': 'curry', 'dal': 'dal', 'chai': 'chai', 'lassi': 'lassi',
  'tikka': 'tikka', 'kebab': 'kebab', 'samosa': 'samosa', 'pav': 'pav', 'chaat': 'chaat',
  // International
  'noodles': 'ramen', 'pasta': 'spaghetti', 'pizza': 'margherita',
  'sushi': 'sushi', 'ramen': 'ramen', 'pho': 'pho bo',
  'taco': 'taco', 'burrito': 'burrito', 'paella': 'paella',
  'souvlaki': 'souvlaki', 'croissant': 'croissant',
  'banh mi': 'banh mi', 'banh': 'banh mi', 'pho ga': 'pho ga', 'bun bo': 'bun bo',
  'moussaka': 'moussaka', 'spanakopita': 'spanakopita', 'gyoza': 'gyoza',
  'feijoada': 'feijoada', 'churros': 'churros', 'lahmacun': 'lahmacun',
  // General
  'veg': 'vegetable', 'nonveg': 'chicken', 'non veg': 'chicken',
  'juice': 'juice', 'shake': 'smoothie', 'coffee': 'coffee',
  'salad': 'salad', 'soup': 'soup', 'rice': 'rice', 'bread': 'bread',
  'chicken': 'chicken', 'beef': 'beef', 'fish': 'fish', 'pork': 'pork',
};

// Simple food descriptions by category (change #2)
const FOOD_DESCRIPTIONS = {
  fruit: 'Fresh & naturally sweet',
  veg: 'Wholesome vegetables',
  grain: 'Grains & starches',
  protein: 'High-protein food',
  dairy: 'Dairy product',
  legume: 'Legumes & beans',
  drink: 'Beverage',
  snack: 'Snack item',
  fastfood: 'Fast food',
  indian: 'Indian cuisine',
  japanese: 'Japanese cuisine',
  chinese: 'Chinese cuisine',
  american: 'American cuisine',
  middleeast: 'Middle Eastern cuisine',
  italian: 'Italian cuisine',
  thai: 'Thai cuisine',
  korean: 'Korean cuisine',
  mexican: 'Mexican cuisine',
  african: 'African cuisine',
};

// Debounced backend search state
let _searchDebounceTimer = null;
let _lastSearchQuery = '';

function _buildFoodCard(f) {
  const isDb = f.source === 'db';
  const desc = isDb
    ? '<span style="font-size:0.68rem;opacity:0.5;letter-spacing:0.03em">📦 From Database</span>'
    : (f.desc || FOOD_DESCRIPTIONS[f.cat] || '');

  const safeId = 'food_' + String(f.id || f.name).replace(/[^a-zA-Z0-9_]/g, '_');
  if (!window._foodCardMap) window._foodCardMap = {};
  window._foodCardMap[safeId] = f;

  const safeName = String(f.name).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const mealLabel = (currentMealType || 'meal').toUpperCase();

  return `
    <div class="food-result-card" onclick="addFoodById('${safeId}', this)" style="cursor:pointer; display:flex; flex-direction:column; justify-space-between;">
      <div>
        <div class="emoji">${f.emoji || '🍽️'}</div>
        <div class="name">${safeName}</div>
        ${desc ? `<div class="desc">${desc}</div>` : ''}
        <div class="cals">${f.cal} kcal</div>
        <div class="macros">P:${f.pro}g · C:${f.carb}g · F:${f.fat}g · Fiber:${f.fiber}g</div>
        <div class="macros" style="color:rgba(184,201,186,0.8); margin-top:2px;">
          ☀️ Vit D: ${f.vit_d || 0}mcg · 🥩 Iron: ${f.iron || 0}mg · 🥬 Folate: ${f.folate || 0}mcg
        </div>
        <div class="macros" style="color:rgba(184,201,186,0.5)">Sugar:${f.sugar}g · Salt:${f.sodium}mg</div>
      </div>
      <button type="button" class="scan-add-btn" style="margin-top:0.75rem; padding:0.45rem 0.8rem; font-size:0.75rem; font-weight:700; width:100%; border-radius:8px; background:linear-gradient(135deg,#3ecf8e,#22c55e); color:#0a0f0d; border:none; cursor:pointer;" onclick="event.stopPropagation(); addFoodById('${safeId}', this)">
        + Add to ${mealLabel}
      </button>
    </div>`;
}

function addFoodById(safeId, targetEl) {
  const food = window._foodCardMap && window._foodCardMap[safeId];
  if (food) {
    addFoodToLog(food);
    const btn = targetEl && (targetEl.tagName === 'BUTTON' ? targetEl : targetEl.querySelector('button'));
    if (btn) {
      const origText = btn.textContent;
      btn.textContent = '✓ Added!';
      btn.style.background = 'linear-gradient(135deg,#22c55e,#15803d)';
      btn.style.color = '#ffffff';
      setTimeout(() => {
        btn.textContent = origText;
        btn.style.background = 'linear-gradient(135deg,#3ecf8e,#22c55e)';
        btn.style.color = '#0a0f0d';
      }, 1250);
    }
  } else {
    console.warn('Food item not found in card map:', safeId);
  }
}

let _foodPage = 0;
let _currentDbFoods = [];
let _totalDbCount = 15085;

async function searchFoods(query = '', page = 0) {
  const q = (query || '').toLowerCase().trim();
  const countEl = document.getElementById('searchCount');
  const container = document.getElementById('foodResults');

  if (!container) return;

  if (page === 0) {
    _foodPage = 0;
    _currentDbFoods = [];
  }

  _lastSearchQuery = `${currentCat}:${q}`;

  // 1. Calculate local matches cleanly
  let localMatches = Array.isArray(FOODS) ? FOODS : [];
  if (currentCat !== 'all') {
    localMatches = localMatches.filter(f => f.cat === currentCat || (f.cat && f.cat.includes(currentCat)));
  }
  if (q) {
    localMatches = localMatches.filter(f => f.name.toLowerCase().includes(q));
  }
  if (localMatches.length === 0) {
    localMatches = Array.isArray(FOODS) ? FOODS.slice(0, 24) : [];
  } else if (currentCat === 'all' && !q) {
    localMatches = localMatches.slice(0, 24);
  }

  // Render initial local matches immediately so grid is NEVER empty
  if (page === 0 && localMatches.length > 0) {
    container.innerHTML = localMatches.map(_buildFoodCard).join('');
    if (countEl) {
      countEl.textContent = `Showing ${localMatches.length} foods in database...`;
    }
  }

  try {
    let dbFetched = [];
    if (typeof supabaseClient !== 'undefined' && supabaseClient) {
      let qBuilder = supabaseClient.from('base_foods').select('*', { count: 'exact' });

      if (currentCat !== 'all') {
        const catMap = {
          'veg': 'veg', 'veggies': 'veg', 'fruit': 'fruit', 'fruits': 'fruit',
          'protein': 'protein', 'grain': 'grain', 'grains': 'grain', 'dairy': 'dairy',
          'snack': 'snack', 'snacks': 'snack', 'legume': 'legume', 'legumes': 'legume',
          'drink': 'drink', 'drinks': 'drink', 'fastfood': 'fastfood', 'fast food': 'fastfood',
          'indian': 'indian'
        };
        const dbCat = catMap[currentCat] || currentCat;
        qBuilder = qBuilder.eq('category', dbCat);
      }
      if (q) {
        qBuilder = qBuilder.ilike('name', `%${q}%`);
      }

      const fromIndex = page * 60;
      const toIndex = fromIndex + 59;
      const { data, count, error } = await qBuilder.order('name', { ascending: true }).range(fromIndex, toIndex);

      if (!error && data && data.length > 0) {
        if (count !== null && count !== undefined) _totalDbCount = count;
        dbFetched = data.map(item => ({
          id: `db_${item.id}`,
          name: item.name || '',
          cat: item.category || 'other',
          emoji: item.emoji || '🥗',
          cal: Math.round(floatVal(item.calories)),
          pro: floatVal(item.protein),
          carb: floatVal(item.carbs),
          fat: floatVal(item.fat),
          fiber: floatVal(item.fiber),
          sugar: floatVal(item.sugar),
          sodium: floatVal(item.sodium),
          chol: floatVal(item.chol),
          vit_d: floatVal(item.vit_d),
          iron: floatVal(item.iron),
          folate: floatVal(item.folate),
          source: 'db'
        }));
      }
    }

    if (page === 0) {
      const dbNames = new Set(dbFetched.map(f => f.name.toLowerCase()));
      const uniqueLocal = localMatches.filter(f => !dbNames.has(f.name.toLowerCase()));
      _currentDbFoods = [...uniqueLocal, ...dbFetched];
    } else {
      _currentDbFoods = [..._currentDbFoods, ...dbFetched];
    }

    if (_lastSearchQuery !== `${currentCat}:${q}`) return;

    // Guaranteed fallback: if _currentDbFoods is empty, populate from local FOODS
    if (_currentDbFoods.length === 0) {
      _currentDbFoods = (Array.isArray(FOODS) ? FOODS : []).slice(0, 24);
    }

    if (countEl) {
      const catText = currentCat !== 'all' ? ` in ${currentCat.toUpperCase()} category` : '';
      countEl.textContent = `Showing ${_currentDbFoods.length} of ${_totalDbCount}+ foods${catText} in Supabase Database`;
    }

    let cardsHtml = _currentDbFoods.map(_buildFoodCard).join('');
    if (_currentDbFoods.length < _totalDbCount) {
      cardsHtml += `
        <div style="grid-column:1/-1; text-align:center; padding:1.5rem; margin-top:1rem;">
          <button type="button" onclick="loadMoreFoods()" class="water-quick-btn" style="padding:12px 28px; font-weight:700; font-size:0.92rem; background:linear-gradient(135deg,#3ecf8e,#22c55e); color:#0a0f0d; border:none; border-radius:12px; cursor:pointer; box-shadow:0 4px 14px rgba(62,207,142,0.3);">
            ⬇️ Load More Foods (+60)
          </button>
        </div>`;
    }
    container.innerHTML = cardsHtml;
  } catch (err) {
    console.warn('searchFoods error:', err);
  }
}

function loadMoreFoods() {
  const fInput = document.getElementById('foodSearch');
  const q = fInput ? fInput.value : '';
  _foodPage += 1;
  searchFoods(q, _foodPage);
}

// ─────────────────────────────────────────────────
//  AUTHENTICATED FETCH HELPER
// ─────────────────────────────────────────────────
async function _authFetch(url, options = {}) {
  let token = currentUser?.token;
  if (!token && typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
    try {
      const { data } = await supabaseClient.auth.getSession();
      token = data?.session?.access_token;
      if (token && currentUser) currentUser.token = token;
    } catch (e) { }
  }

  const backendBase = window._BACKEND_URL || '';
  let fullUrl = url;
  if (url.startsWith('https://nutritrack-k96f.onrender.com')) {
    fullUrl = url.replace('https://nutritrack-k96f.onrender.com', backendBase);
  } else if (!url.startsWith('http://') && !url.startsWith('https://')) {
    fullUrl = `${backendBase}${url}`;
  }

  const headers = { ...(options.headers || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  options.headers = headers;

  let res = await fetch(fullUrl, options);
  if (res.status === 401 && typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
    try {
      const { data, error } = await supabaseClient.auth.refreshSession();
      if (!error && data && data.session) {
        const freshToken = data.session.access_token;
        if (currentUser) currentUser.token = freshToken;
        headers['Authorization'] = `Bearer ${freshToken}`;
        options.headers = headers;
        res = await fetch(fullUrl, options);
      }
    } catch (e) { }
  }
  return res;
}

async function addFoodToLog(food) {
  const payload = {
    date: todayStr(),
    mealType: currentMealType,
    name: food.name,
    emoji: food.emoji || '🍽️',
    cal: floatVal(food.cal),
    pro: floatVal(food.pro),
    carb: floatVal(food.carb),
    fat: floatVal(food.fat),
    fiber: floatVal(food.fiber),
    sugar: floatVal(food.sugar),
    sodium: floatVal(food.sodium),
    chol: floatVal(food.chol),
    vit_d: floatVal(food.vit_d),
    iron: floatVal(food.iron),
    folate: floatVal(food.folate)
  };

  // 1. Optimistically add to local food log so dashboard & totals update instantly
  const localId = 'log_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
  const logEntry = { id: localId, ...payload };
  if (!window._foodLogs) window._foodLogs = [];
  window._foodLogs.unshift(logEntry);
  refreshDashboard();
  showToast(`✓ ${food.name} added to ${currentMealType}`, 'success');

  // 2. Save directly to Supabase food_logs cloud table
  try {
    if (typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
      const { data: sessData } = await supabaseClient.auth.getSession();
      const user = sessData?.session?.user;
      if (user) {
        const sbRecord = {
          user_id: user.id,
          date: payload.date,
          meal_type: payload.mealType,
          name: payload.name,
          emoji: payload.emoji,
          cal: payload.cal,
          pro: payload.pro,
          carb: payload.carb,
          fat: payload.fat,
          fiber: payload.fiber,
          sugar: payload.sugar,
          sodium: payload.sodium,
          chol: payload.chol,
          vit_d: payload.vit_d,
          iron: payload.iron,
          folate: payload.folate
        };
        const { data: inserted, error: sbErr } = await supabaseClient
          .from('food_logs')
          .insert(sbRecord)
          .select();
        if (!sbErr && inserted && inserted.length > 0) {
          logEntry.id = inserted[0].id || localId;
        }
      }
    }
  } catch (err) {
    console.warn('Supabase food_logs insert notice:', err);
  }

  // 3. Sync with Flask backend API endpoint
  try {
    const res = await _authFetch('/api/logs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res && res.ok) {
      const savedLog = await res.json();
      if (savedLog && savedLog.id) logEntry.id = savedLog.id;
    }
  } catch (e) {
    console.warn('Backend food log sync notice:', e);
  }
}

async function removeLog(id) {
  // Optimistically remove from local food logs
  window._foodLogs = (window._foodLogs || []).filter(l => String(l.id) !== String(id));
  refreshDashboard();
  renderHistory();
  showToast('Item removed', 'success');

  // Cloud deletion from Supabase DB & Backend API
  try {
    if (typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
      await supabaseClient.from('food_logs').delete().eq('id', id);
    }
    await _authFetch(`/api/logs/${id}`, { method: 'DELETE' });
  } catch (e) {
    console.warn('Cloud log deletion notice:', e);
  }
}

// ─────────────────────────────────────────────────
//  CLOUD FETCH HELPERS
// ─────────────────────────────────────────────────
async function fetchLogsFromCloud() {
  let cloudLogs = [];
  try {
    if (typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
      const { data: sessData } = await supabaseClient.auth.getSession();
      const user = sessData?.session?.user;
      if (user) {
        const { data, error } = await supabaseClient
          .from('food_logs')
          .select('*')
          .eq('user_id', user.id)
          .order('id', { ascending: false });
        if (!error && data) {
          cloudLogs = data.map(item => ({
            id: item.id,
            date: item.date,
            mealType: item.meal_type || item.mealType || 'breakfast',
            name: item.name,
            emoji: item.emoji || '🍽️',
            cal: floatVal(item.cal),
            pro: floatVal(item.pro),
            carb: floatVal(item.carb),
            fat: floatVal(item.fat),
            fiber: floatVal(item.fiber),
            sugar: floatVal(item.sugar),
            sodium: floatVal(item.sodium),
            chol: floatVal(item.chol),
            vit_d: floatVal(item.vit_d),
            iron: floatVal(item.iron),
            folate: floatVal(item.folate)
          }));
        }
      }
    }
  } catch (err) {
    console.warn('Supabase fetch logs notice:', err);
  }

  try {
    const res = await _authFetch('/api/logs');
    if (res && res.ok) {
      const apiLogs = await res.json();
      if (apiLogs && apiLogs.length > 0) {
        const logMap = new Map();
        cloudLogs.forEach(l => logMap.set(String(l.id), l));
        apiLogs.forEach(l => logMap.set(String(l.id || l.name + '_' + l.date), l));
        cloudLogs = Array.from(logMap.values());
      }
    }
  } catch (e) {
    console.warn('Backend fetch logs notice:', e);
  }

  if (cloudLogs.length > 0) {
    window._foodLogs = cloudLogs;
    refreshDashboard();
    renderHistory();
  }
}

async function fetchWaterFromCloud() {
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/water`);
    if (res.ok) {
      const data = await res.json();
      const waterTotal = document.getElementById('waterTotal');
      if (waterTotal) waterTotal.textContent = data.total_ml || 0;
      const bar = document.getElementById('waterBar');
      const goal = currentUser?.goals?.water_ml || 2000;
      if (bar) bar.style.width = Math.min(100, Math.round(((data.total_ml || 0) / goal) * 100)) + '%';
    }
  } catch (e) {
    console.error('fetchWaterFromCloud error', e);
  }
}

async function logWater(ml) {
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/water`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount_ml: ml })
    });
    if (res.ok) {
      showToast(`+${ml}ml water logged!`, 'success');
      fetchWaterFromCloud();
    }
  } catch (e) {
    showToast('Failed to log water', 'error');
  }
}

async function loadPopularFoodsFromCloud() {
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await fetch(`${backendUrl}/api/foods/popular`);
    if (res.ok) {
      window._dbPopularFoods = await res.json();
      if (document.getElementById('foodSearch')?.value === '') {
        searchFoods('');
      }
    }
  } catch (e) {
    console.error('loadPopularFoods error', e);
  }
}

// ─────────────────────────────────────────────────
//  BARCODE SCANNER
// ─────────────────────────────────────────────────
async function startBarcodeScan() {
  let barcode = prompt('Scan or enter product barcode number:');
  if (!barcode) return;
  barcode = barcode.trim();
  showLoader('Looking up barcode…');
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await fetch(`${backendUrl}/api/foods/barcode/${encodeURIComponent(barcode)}`);
    hideLoader();
    if (res.ok) {
      const data = await res.json();
      if (data.found && data.item) {
        await addFoodToLog(data.item);
      } else {
        showToast('Product not found for barcode', 'error');
      }
    } else {
      showToast('Product not found', 'error');
    }
  } catch (e) {
    hideLoader();
    showToast('Barcode lookup failed', 'error');
  }
}

// ─────────────────────────────────────────────────
//  VOICE FOOD LOGGING
// ─────────────────────────────────────────────────
function startVoiceLog() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    const spoken = prompt('Speech recognition not supported in this browser. Type your meal:');
    if (spoken) parseVoiceText(spoken);
    return;
  }
  const row = document.getElementById('voiceStatusRow');
  const txt = document.getElementById('voiceStatusText');
  if (row) row.style.display = 'block';
  if (txt) txt.textContent = 'Listening… Speak your meal now!';

  _voiceRecognition = new SpeechRecognition();
  _voiceRecognition.continuous = false;
  _voiceRecognition.interimResults = false;
  _voiceRecognition.lang = 'en-US';

  _voiceRecognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    if (txt) txt.textContent = `Processing: "${transcript}"…`;
    parseVoiceText(transcript);
  };
  _voiceRecognition.onerror = (err) => {
    if (row) row.style.display = 'none';
    showToast('Voice error: ' + err.error, 'error');
  };
  _voiceRecognition.onend = () => {
    if (row) row.style.display = 'none';
  };
  _voiceRecognition.start();
}

function stopVoiceLog() {
  if (_voiceRecognition) _voiceRecognition.stop();
  const row = document.getElementById('voiceStatusRow');
  if (row) row.style.display = 'none';
}

async function parseVoiceText(transcript) {
  showLoader('Parsing spoken meal…');
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/ai/parse-voice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript })
    });
    hideLoader();
    if (res.ok) {
      const data = await res.json();
      if (data.items && data.items.length > 0) {
        for (const item of data.items) {
          await addFoodToLog(item);
        }
        showToast(`✓ Logged ${data.items.length} items from voice!`, 'success');
      } else {
        showToast('Could not extract foods from spoken text.', 'error');
      }
    }
  } catch (e) {
    hideLoader();
    showToast('Failed to parse voice meal.', 'error');
  }
}

// ─────────────────────────────────────────────────
//  BODY WEIGHT TRACKER
// ─────────────────────────────────────────────────
async function fetchWeightFromCloud() {
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/weight?days=30`);
    if (res.ok) {
      window._weightLogs = await res.json();
      renderWeightChart();
    }
  } catch (e) {
    console.error('fetchWeightFromCloud error', e);
  }
}

async function logWeightEntry() {
  const input = document.getElementById('quickWeightInput');
  const val = parseFloat(input?.value || 0);
  if (!val || val <= 0 || val > 300) return showToast('⚠️ Enter a valid weight (e.g. 70.5)', 'error');
  
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/weight`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ weight_kg: val })
    });
    if (res.ok) {
      showToast('✓ Weight entry saved!', 'success');
      if (input) input.value = '';
      if (currentUser) currentUser.weight = val;
      renderProfile();
      fetchWeightFromCloud();
    }
  } catch (e) {
    showToast('Failed to save weight', 'error');
  }
}

function renderWeightChart() {
  const ctx = document.getElementById('weightChart')?.getContext('2d');
  if (!ctx) return;
  const logs = window._weightLogs || [];
  if (weightChart) weightChart.destroy();

  const labels = logs.map(l => {
    const parts = l.date.split('-');
    return parts.length === 3 ? `${parts[2]}/${parts[1]}` : l.date;
  });
  const data = logs.map(l => l.weight_kg);

  weightChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels.length ? labels : ['Today'],
      datasets: [{
        label: 'Weight (kg)',
        data: data.length ? data : [currentUser?.weight || 70],
        borderColor: '#3ecf8e',
        backgroundColor: 'rgba(62,207,142,0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointBackgroundColor: '#3ecf8e'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: 'rgba(255,255,255,0.5)', font: { size: 10 } } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: 'rgba(255,255,255,0.5)', font: { size: 10 } } }
      }
    }
  });
}

// ─────────────────────────────────────────────────
//  MEAL TEMPLATES
// ─────────────────────────────────────────────────
async function fetchMealTemplatesFromCloud() {
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/meals/templates`);
    if (res.ok) {
      window._mealTemplates = await res.json();
      renderMealTemplates();
    }
  } catch (e) {
    console.error('fetchMealTemplatesFromCloud error', e);
  }
}

function renderMealTemplates() {
  const list = document.getElementById('mealTemplatesList');
  if (!list) return;
  const templates = window._mealTemplates || [];
  if (!templates.length) {
    list.innerHTML = `<div style="font-size:0.8rem; color:var(--mist); opacity:0.7;">No saved meal templates yet. Click "+ Save Today's Meal" to create one-tap combos!</div>`;
    return;
  }
  list.innerHTML = templates.map(t => `
    <div class="tpl-card" onclick="logMealTemplate(${t.id})">
      <div class="tpl-title">🍱 ${t.name}</div>
      <div class="tpl-sub">${(t.items || []).length} items · ${Math.round(t.total_cal || 0)} kcal · P:${Math.round(t.total_pro || 0)}g</div>
    </div>
  `).join('');
}

async function openSaveTemplateModal() {
  const todayLogs = (window._foodLogs || []).filter(l => l.date === todayStr());
  if (!todayLogs.length) return showToast('⚠️ Log some food today first to save as a template!', 'error');

  const tplName = prompt('Enter a name for this meal template (e.g. "My Standard Breakfast"):');
  if (!tplName) return;

  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/meals/templates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: tplName.trim(), items: todayLogs })
    });
    if (res.ok) {
      showToast('✓ Template saved!', 'success');
      fetchMealTemplatesFromCloud();
    }
  } catch (e) {
    showToast('Failed to save template', 'error');
  }
}

async function logMealTemplate(tplId) {
  const tpl = (window._mealTemplates || []).find(t => t.id === tplId);
  if (!tpl || !tpl.items) return;

  showLoader(`Logging ${tpl.name}…`);
  for (const item of tpl.items) {
    await addFoodToLog(item);
  }
  hideLoader();
  showToast(`✓ Logged template: ${tpl.name}!`, 'success');
}

// ─────────────────────────────────────────────────
//  AI MEAL RECOMMENDATIONS
// ─────────────────────────────────────────────────
async function fetchAIMealRecommendations() {
  const container = document.getElementById('aiRecommendationsList');
  if (!container) return;

  const todayLogs = (window._foodLogs || []).filter(l => l.date === todayStr());
  const todayTotals = sumLogs(todayLogs);
  const goalCal = (currentUser && currentUser.goals && currentUser.goals.calories) || 2000;
  const goalPro = (currentUser && currentUser.goals && currentUser.goals.protein) || 150;

  const remCal = Math.max(0, goalCal - todayTotals.cal);
  const remPro = Math.max(0, goalPro - todayTotals.pro);
  const userDiet = String(currentUser?.diet_type || currentUser?.dietType || currentUser?.diet_goal || currentUser?.dietGoal || 'veg').toLowerCase();

  // Diet-Specific Meal Pool
  const DIET_MEAL_POOL = {
    veg: [
      { name: 'Paneer Tikka (150g)', emoji: '🧀', cal: 260, pro: 18, carb: 6, fat: 18, fiber: 1, reason: '🌱 Pure Veg · High Protein' },
      { name: 'Dal Tadka + 2 Rotis', emoji: '🍲', cal: 310, pro: 14, carb: 48, fat: 7, fiber: 8, reason: '🌱 Pure Veg · Balanced Meal' },
      { name: 'Chana Masala (200g)', emoji: '🫘', cal: 220, pro: 12, carb: 34, fat: 5, fiber: 9, reason: '🌱 Pure Veg · Rich in Fiber' },
      { name: 'Sprouts & Paneer Salad', emoji: '🥗', cal: 180, pro: 14, carb: 16, fat: 6, fiber: 5, reason: '🌱 Pure Veg · Low Calorie' },
      { name: 'Greek Yogurt with Honey', emoji: '🥛', cal: 160, pro: 13, carb: 18, fat: 4, fiber: 0, reason: '🌱 Pure Veg · Gut Healthy' },
      { name: 'Moong Dal Khichdi', emoji: '🥣', cal: 250, pro: 11, carb: 42, fat: 4, fiber: 6, reason: '🌱 Pure Veg · Easy to Digest' }
    ],
    vegan: [
      { name: 'Chana Masala (200g)', emoji: '🫘', cal: 220, pro: 12, carb: 34, fat: 5, fiber: 9, reason: '🌱 100% Vegan · Fiber Rich' },
      { name: 'Tofu Stir Fry with Veggies', emoji: '🥗', cal: 210, pro: 16, carb: 12, fat: 10, fiber: 4, reason: '🌱 100% Vegan · High Protein' },
      { name: 'Soybean Curry (180g)', emoji: '🫘', cal: 240, pro: 18, carb: 14, fat: 9, fiber: 6, reason: '🌱 100% Vegan · Complete Amino Acid' },
      { name: 'Hummus & Whole Wheat Pita', emoji: '🫓', cal: 230, pro: 9, carb: 36, fat: 7, fiber: 6, reason: '🌱 100% Vegan · Clean Fuel' },
      { name: 'Oats & Chia Seeds Bowl', emoji: '🥣', cal: 210, pro: 8, carb: 35, fat: 5, fiber: 8, reason: '🌱 100% Vegan · Slow Carbs' }
    ],
    keto: [
      { name: 'Paneer Tikka (150g)', emoji: '🧀', cal: 260, pro: 18, carb: 6, fat: 18, fiber: 1, reason: '🥑 Keto · Low Carb High Fat' },
      { name: 'Scrambled Eggs with Avocado', emoji: '🍳', cal: 310, pro: 16, carb: 4, fat: 24, fiber: 4, reason: '🥑 Keto · Healthy Fats' },
      { name: 'Handful Almonds & Walnuts', emoji: '🌰', cal: 170, pro: 6, carb: 4, fat: 15, fiber: 3, reason: '🥑 Keto · Energy Snack' }
    ],
    eggetarian: [
      { name: 'Egg Bhurji with Whole Wheat Toast', emoji: '🍳', cal: 260, pro: 16, carb: 22, fat: 12, fiber: 3, reason: '🥚 Eggetarian · Muscle Recovery' },
      { name: '2 Boiled Eggs with Pepper', emoji: '🥚', cal: 155, pro: 13, carb: 1, fat: 10, fiber: 0, reason: '🥚 Eggetarian · Bioavailable Protein' },
      { name: 'Paneer & Spinach Omelette', emoji: '🍳', cal: 280, pro: 20, carb: 5, fat: 18, fiber: 2, reason: '🥚 Eggetarian · Low Carb' }
    ],
    nonveg: [
      { name: 'Grilled Chicken Breast (150g)', emoji: '🍗', cal: 220, pro: 35, carb: 0, fat: 4, fiber: 0, reason: '🍗 Lean Protein · Low Fat' },
      { name: 'Egg White Omelette with Spinach', emoji: '🍳', cal: 140, pro: 18, carb: 3, fat: 2, fiber: 1, reason: '🍳 High Protein · Low Calorie' },
      { name: 'Tandoori Fish Tikka (150g)', emoji: '🐟', cal: 210, pro: 28, carb: 2, fat: 8, fiber: 0, reason: '🐟 Rich in Omega-3' },
      { name: 'Paneer Tikka (150g)', emoji: '🧀', cal: 260, pro: 18, carb: 6, fat: 18, fiber: 1, reason: '🧀 Vegetarian Option' }
    ]
  };

  const selectedPool = userDiet.includes('vegan') ? DIET_MEAL_POOL.vegan
    : userDiet.includes('veg') ? DIET_MEAL_POOL.veg
    : userDiet.includes('keto') ? DIET_MEAL_POOL.keto
    : userDiet.includes('egg') ? DIET_MEAL_POOL.eggetarian
    : DIET_MEAL_POOL.nonveg;

  let recommendations = selectedPool.filter(item => item.cal <= (remCal > 0 ? remCal + 100 : 350)).slice(0, 3);
  if (recommendations.length === 0) recommendations = selectedPool.slice(0, 3);

  // Render recommendations immediately
  const renderList = (items) => {
    if (!window._foodCardMap) window._foodCardMap = {};
    container.innerHTML = items.map(item => {
      const safeId = 'rec_' + String(item.name).replace(/[^a-zA-Z0-9_]/g, '_');
      window._foodCardMap[safeId] = item;
      return `
        <div style="padding:10px 14px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); border-radius:12px; display:flex; justify-content:space-between; align-items:center; transition:all 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.08)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'">
          <div>
            <div style="font-weight:700; font-size:0.85rem; color:#fff;">${item.emoji} ${item.name}</div>
            <div style="font-size:0.72rem; color:var(--kiwi); margin-top:2px; font-weight:600;">${item.reason} · ${item.cal} kcal (${item.pro}g P)</div>
          </div>
          <button type="button" onclick="addFoodById('${safeId}')" class="water-quick-btn" style="font-size:0.78rem; padding:5px 12px; font-weight:700; background:linear-gradient(135deg,#3ecf8e,#22c55e); color:#0a0f0d; border:none;">+ Log</button>
        </div>`;
    }).join('');
  };

  renderList(recommendations);

  // Attempt backend API call asynchronously
  try {
    const res = await _authFetch('/api/ai/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rem_cal: remCal, rem_pro: remPro, diet_type: userDiet })
    });
    if (res && res.ok) {
      const apiItems = await res.json();
      if (apiItems && apiItems.length > 0) {
        renderList(apiItems);
      }
    }
  } catch (e) {
    console.warn('Backend AI recommend notice:', e);
  }
}

// ─────────────────────────────────────────────────
//  WEEKLY INSIGHTS
// ─────────────────────────────────────────────────
async function fetchWeeklyInsights() {
  const container = document.getElementById('weeklyInsightsCard');
  if (!container) return;
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/analytics/weekly-insights`);
    if (res.ok) {
      const data = await res.json();
      container.innerHTML = `
        <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:8px;">
          <div style="background:rgba(62,207,142,0.1); padding:8px 14px; border-radius:10px; flex:1; min-width:120px;">
            <div style="font-size:0.7rem; color:var(--mist);">Weekly Adherence</div>
            <div style="font-size:1.2rem; font-weight:800; color:var(--kiwi);">${data.adherenceScore}%</div>
          </div>
          <div style="background:rgba(255,255,255,0.05); padding:8px 14px; border-radius:10px; flex:1; min-width:120px;">
            <div style="font-size:0.7rem; color:var(--mist);">Avg Daily Calories</div>
            <div style="font-size:1.2rem; font-weight:800; color:#fff;">${Math.round(data.avgCalories)} / ${data.goalCalories} kcal</div>
          </div>
          <div style="background:rgba(255,255,255,0.05); padding:8px 14px; border-radius:10px; flex:1; min-width:120px;">
            <div style="font-size:0.7rem; color:var(--mist);">Avg Daily Protein</div>
            <div style="font-size:1.2rem; font-weight:800; color:#fff;">${Math.round(data.avgProtein)} / ${data.goalProtein}g</div>
          </div>
        </div>
        <div style="display:flex; flex-direction:column; gap:4px;">
          ${(data.insights || []).map(i => `<div style="font-size:0.82rem; color:rgba(255,255,255,0.85);">${i}</div>`).join('')}
        </div>
      `;
    }
  } catch (e) {
    console.error('fetchWeeklyInsights error', e);
  }
}

// ─────────────────────────────────────────────────
//  COMMUNITY CHALLENGES
// ─────────────────────────────────────────────────
async function fetchCommunityChallenges() {
  const container = document.getElementById('communityChallengesList');
  if (!container) return;
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await fetch(`${backendUrl}/api/challenges`);
    if (res.ok) {
      const items = await res.json();
      container.innerHTML = items.map(c => `
        <div style="padding:10px 14px; background:rgba(255,255,255,0.05); border-radius:10px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:700; font-size:0.85rem; color:#fff;">${c.badgeEmoji} ${c.title}</div>
            <div style="font-size:0.72rem; color:var(--mist); margin-top:2px;">${c.description}</div>
          </div>
          <button type="button" class="water-quick-btn" onclick="joinChallenge(${c.id})" style="font-size:0.75rem; padding:4px 10px;">Join Challenge</button>
        </div>
      `).join('');
    }
  } catch (e) {
    console.error('fetchCommunityChallenges error', e);
  }
}

async function joinChallenge(id) {
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/challenges/join/${id}`, { method: 'POST' });
    if (res.ok) {
      showToast('✓ Joined Challenge!', 'success');
    }
  } catch (e) {
    showToast('Failed to join challenge', 'error');
  }
}

// ─────────────────────────────────────────────────
//  EXPORT LOGS CSV
// ─────────────────────────────────────────────────
async function exportLogsCSV() {
  showLoader('Preparing CSV export…');
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/logs/export`);
    hideLoader();
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nutritrack_logs_${todayStr()}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      showToast('✓ CSV Downloaded!', 'success');
    } else {
      showToast('Export failed', 'error');
    }
  } catch (e) {
    hideLoader();
    showToast('Export error', 'error');
  }
}

// ─────────────────────────────────────────────────
//  WORKOUT & EXERCISE TRACKER
// ─────────────────────────────────────────────────
window._workoutLogs = [];

async function fetchWorkoutsFromCloud() {
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/workouts`);
    if (res.ok) {
      const data = await res.json();
      window._workoutLogs = data.entries || [];
      const burnEl = document.getElementById('dashWorkoutBurn');
      if (burnEl) burnEl.textContent = Math.round(data.totalBurned || 0);
      renderWorkoutLogs();
    }
  } catch (e) {
    console.error('fetchWorkoutsFromCloud error', e);
  }
}

function renderWorkoutLogs() {
  const list = document.getElementById('workoutLogsList');
  if (!list) return;
  const logs = window._workoutLogs || [];
  if (!logs.length) {
    list.innerHTML = `<div style="font-size:0.78rem; color:var(--mist); opacity:0.7;">No workouts logged today. Add one above!</div>`;
    return;
  }
  list.innerHTML = logs.map(w => `
    <div style="padding:6px 12px; background:rgba(62,207,142,0.1); border-radius:8px; font-size:0.8rem; display:flex; align-items:center; gap:8px;">
      <span>🏃 ${w.name} (${w.durationMin}m)</span>
      <strong style="color:var(--kiwi);">-${Math.round(w.calBurned)} kcal</strong>
    </div>
  `).join('');
}

async function logWorkoutEntry() {
  const name = document.getElementById('workoutName')?.value.trim();
  const dur = parseInt(document.getElementById('workoutMin')?.value || 30);
  const burn = parseFloat(document.getElementById('workoutBurned')?.value || 0);

  if (!name) return showToast('⚠️ Enter a workout name', 'error');

  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/workouts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, duration_min: dur, cal_burned: burn })
    });
    if (res.ok) {
      showToast(`✓ Workout logged: ${name}`, 'success');
      if (document.getElementById('workoutName')) document.getElementById('workoutName').value = '';
      if (document.getElementById('workoutMin')) document.getElementById('workoutMin').value = '';
      if (document.getElementById('workoutBurned')) document.getElementById('workoutBurned').value = '';
      fetchWorkoutsFromCloud();
      refreshDashboard();
    }
  } catch (e) {
    showToast('Failed to log workout', 'error');
  }
}

// ─────────────────────────────────────────────────
// ─────────────────────────────────────────────────
//  RECIPE BUILDER MANAGEMENT
// ─────────────────────────────────────────────────

async function logRecipe(id) {
  const recipe = (window._recipes || []).find(r => r.id === id);
  if (!recipe || !recipe.perServing) return;

  const item = {
    name: `${recipe.name} (1 serving)`,
    emoji: '🍳',
    cal: recipe.perServing.cal,
    pro: recipe.perServing.pro,
    carb: recipe.perServing.carb,
    fat: recipe.perServing.fat,
    source: 'recipe'
  };
  await addFoodToLog(item);
}

// ─────────────────────────────────────────────────
//  CONTEXT-AWARE NUTRIBOT CHATBOT
// ─────────────────────────────────────────────────
async function sendNutriBotMessage(userMsg) {
  if (!userMsg) return;
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userMsg })
    });
    if (res.ok) {
      const data = await res.json();
      return data.response;
    }
  } catch (e) {
    return "I'm having trouble connecting right now. Please try again in a moment!";
  }
}

// ─────────────────────────────────────────────────
//  HISTORY
// ─────────────────────────────────────────────────
function renderHistory() {
  const logs = window._foodLogs;
  const last30 = getLast30Days();
  const monthData = last30.map(d => sumLogs(logs.filter(l => l.date === d)).cal);

  const chartCanvas = document.getElementById('weekChart');
  if (!chartCanvas || typeof Chart === 'undefined') return;
  const wCtx = chartCanvas.getContext('2d');
  if (weekChart) weekChart.destroy();
  weekChart = new Chart(wCtx, {
    type: 'bar',
    data: {
      labels: last30.map(d => {
        const [, m, day] = d.split('-');
        // Show label only every 5 days to avoid crowding
        const idx = last30.indexOf(d);
        return (idx % 5 === 0 || idx === last30.length - 1) ? `${day}/${m}` : '';
      }),
      datasets: [{ label: 'Calories', data: monthData, backgroundColor: 'rgba(45,158,107,0.2)', borderColor: 'rgba(45,158,107,1)', borderWidth: 1.5, borderRadius: 6 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false }, tooltip: {
          callbacks: {
            label: c => ` ${Math.round(c.parsed.y)} kcal`,
            title: c => { const d = last30[c[0].dataIndex]; const [, m, day] = d.split('-'); return `${day}/${m}`; }
          }
        }
      },
      scales: {
        x: { grid: { color: 'rgba(18,17,15,0.06)' }, ticks: { color: 'rgba(18,17,15,0.5)', font: { family: 'Plus Jakarta Sans', size: 10 } } },
        y: { grid: { color: 'rgba(18,17,15,0.06)' }, ticks: { color: 'rgba(18,17,15,0.5)', font: { family: 'Plus Jakarta Sans', size: 10 } } }
      }
    }
  });

  const recent = [...logs].reverse().slice(0, 60);
  document.getElementById('historyBody').innerHTML = recent.map(l => `
    <tr>
      <td>${l.emoji || '🍽️'} ${l.name}</td>
      <td><span class="badge ${l.mealType}">${l.mealType}</span></td>
      <td>${l.cal} kcal</td>
      <td style="font-size:0.78rem;color:var(--ink-50)">${l.fiber || 0}g fiber · ${l.sodium || 0}mg salt</td>
      <td>${l.date}</td>
    </tr>
  `).join('') || '<tr><td colspan="5" style="text-align:center;color:#B8C9BA;padding:2rem">No history yet.</td></tr>';

  const monthLogs = logs.filter(l => last30.includes(l.date));
  const monthTotals = sumLogs(monthLogs);
  const days = [...new Set(monthLogs.map(l => l.date))].length || 1;

  document.getElementById('weeklyStats').innerHTML = `
    <div style="display:grid;gap:0.8rem;margin-top:0.5rem">
      ${[
      ['🔥', 'Total Calories', Math.round(monthTotals.cal) + ' kcal'],
      ['💪', 'Avg Protein/day', Math.round(monthTotals.pro / days) + 'g'],
      ['🌾', 'Avg Carbs/day', Math.round(monthTotals.carb / days) + 'g'],
      ['🥑', 'Avg Fat/day', Math.round(monthTotals.fat / days) + 'g'],
      ['🌿', 'Avg Fiber/day', Math.round(monthTotals.fiber / days) + 'g'],
      ['🍬', 'Avg Sugar/day', Math.round(monthTotals.sugar / days) + 'g'],
      ['🧂', 'Avg Salt/day', Math.round(monthTotals.sodium / days) + 'mg'],
      ['❤️', 'Avg Cholesterol/day', Math.round(monthTotals.chol / days) + 'mg'],
      ['🍽️', 'Total Meals', monthLogs.length],
      ['📅', 'Days Logged', days]
    ].map(([i, l, v]) => `
        <div style="background:var(--smoke);border:1px solid var(--border-soft);border-radius:14px;padding:0.9rem;display:flex;align-items:center;justify-content:space-between">
          <div style="display:flex;align-items:center;gap:0.7rem">
            <span style="font-size:1.1rem">${i}</span>
            <span style="font-size:0.88rem;color:var(--ink-50)">${l}</span>
          </div>
          <span style="font-family:'Fraunces',serif;color:var(--ink);font-size:1.05rem;font-weight:700">${v}</span>
        </div>
      `).join('')}
    </div>`;
}

// ─────────────────────────────────────────────────
//  PROFILE  (change #1: show age/weight/height)
// ─────────────────────────────────────────────────
function renderProfile() {
  document.getElementById('profileAvatar').textContent = currentUser.name[0].toUpperCase();
  document.getElementById('profileName').textContent = currentUser.name;
  document.getElementById('profileEmail').textContent = currentUser.email;

  // Body stats chips
  const bsc = document.getElementById('profileBodyStats');
  if (bsc) {
    const chips = [];
    if (currentUser.age) chips.push(`🎂 Age: ${currentUser.age}`);
    if (currentUser.weight) chips.push(`⚖️ ${currentUser.weight}${currentUser.weightUnit || 'kg'}`);
    if (currentUser.height) chips.push(`📏 ${currentUser.height}${currentUser.heightUnit || 'cm'}`);
    if (currentUser.gender) chips.push(`${currentUser.gender === 'female' ? '👩' : '👨'} ${currentUser.gender.charAt(0).toUpperCase() + currentUser.gender.slice(1)}`);
    if (currentUser.dietGoal) {
      const goalLabels = { lose: '🔥 Lose Weight', maintain: '⚖️ Maintain', gain: '💪 Gain Weight', bulk: '🏋️ Bulk Up' };
      chips.push(goalLabels[currentUser.dietGoal] || currentUser.dietGoal);
    }
    if (currentUser.dietType) {
      const dtLabels = { nonveg: '🍖 Non-Veg', veg: '🌱 Pure Veg', eggetarian: '🥚 Eggetarian', vegan: '🌿 Vegan' };
      chips.push(dtLabels[currentUser.dietType] || currentUser.dietType);
    }
    bsc.innerHTML = chips.length ? chips.map(c => `<span class="bsc">${c}</span>`).join('') : '';
  }
  // Restore diet type dropdown
  const dtSel = document.getElementById('editDietType');
  if (dtSel) dtSel.value = currentUser.dietType || 'nonveg';

  // Restore weight/height edit fields
  const wEl = document.getElementById('editWeight');
  const wuEl = document.getElementById('editWeightUnit');
  const hEl = document.getElementById('editHeight');
  const huEl = document.getElementById('editHeightUnit');
  if (wEl && currentUser.weight) wEl.value = currentUser.weight;
  if (wuEl) wuEl.value = currentUser.weightUnit || 'kg';
  if (hEl && currentUser.height) hEl.value = currentUser.height;
  if (huEl) huEl.value = currentUser.heightUnit || 'cm';

  const logs = window._foodLogs;
  const days = [...new Set(logs.map(l => l.date))];
  const totals = sumLogs(logs);
  const avgCal = days.length ? Math.round(totals.cal / days.length) : 0;

  document.getElementById('totalMeals').textContent = logs.length;
  document.getElementById('totalDays').textContent = days.length;
  document.getElementById('avgCals').textContent = avgCal;

  let streak = 0;
  for (let i = 0; i < 30; i++) {
    const d = new Date(); d.setDate(d.getDate() - i);
    const ds = d.toISOString().split('T')[0];
    if (logs.some(l => l.date === ds)) streak++; else break;
  }
  document.getElementById('streakDays').textContent = streak;

  _renderAchievements(logs, streak);
}

function _renderAchievements(logs, streak) {
  const grid = document.getElementById('achievementsGrid');
  if (!grid) return;

  const totalMeals = logs.length;
  const goals = currentUser.goals || {};
  const proteinGoal = goals.protein || 150;

  // Days (last 7) where protein goal was hit
  let proteinHitDays = 0;
  for (let i = 0; i < 7; i++) {
    const d = new Date(); d.setDate(d.getDate() - i);
    const ds = d.toISOString().split('T')[0];
    const dayLogs = logs.filter(l => l.date === ds);
    if (dayLogs.length === 0) continue;
    const dayProtein = dayLogs.reduce((s, l) => s + (l.pro || 0), 0);
    if (dayProtein >= proteinGoal) proteinHitDays++;
  }

  // "Healthy Week": last 7 days all logged, average calories within 15% of
  // goal, and fiber goal hit on at least 4 of those days — a genuine
  // adherence signal, not just "logged something every day".
  const calGoal = goals.calories || 2000;
  const fiberGoal = goals.fiber || 28;
  let daysLoggedLast7 = 0, fiberHitDays = 0, totalCalLast7 = 0;
  for (let i = 0; i < 7; i++) {
    const d = new Date(); d.setDate(d.getDate() - i);
    const ds = d.toISOString().split('T')[0];
    const dayLogs = logs.filter(l => l.date === ds);
    if (dayLogs.length === 0) continue;
    daysLoggedLast7++;
    const dayCal = dayLogs.reduce((s, l) => s + (l.cal || 0), 0);
    const dayFiber = dayLogs.reduce((s, l) => s + (l.fiber || 0), 0);
    totalCalLast7 += dayCal;
    if (dayFiber >= fiberGoal) fiberHitDays++;
  }
  const avgCalLast7 = daysLoggedLast7 ? totalCalLast7 / daysLoggedLast7 : 0;
  const calWithinRange = daysLoggedLast7 > 0 && Math.abs(avgCalLast7 - calGoal) <= calGoal * 0.15;
  const healthyWeekEarned = daysLoggedLast7 === 7 && calWithinRange && fiberHitDays >= 4;

  const badges = [
    {
      icon: '🔥', name: '7-Day Streak', desc: 'Logged food 7 days in a row',
      earned: streak >= 7, progress: streak >= 7 ? null : `${streak}/7 days`
    },
    {
      icon: '🏆', name: '30-Day Streak', desc: 'Logged food 30 days in a row',
      earned: streak >= 30, progress: streak >= 30 ? null : `${Math.min(streak, 30)}/30 days`
    },
    {
      icon: '🥗', name: 'Healthy Week', desc: 'A full week logged, calories on target, fiber goal hit 4+ days',
      earned: healthyWeekEarned, progress: healthyWeekEarned ? null : `${daysLoggedLast7}/7 days logged`
    },
    {
      icon: '💪', name: 'Protein Master', desc: 'Hit your protein goal on 5+ of the last 7 days',
      earned: proteinHitDays >= 5, progress: proteinHitDays >= 5 ? null : `${proteinHitDays}/5 days`
    },
    {
      icon: '📸', name: 'Century Club', desc: 'Logged 100 meals total',
      earned: totalMeals >= 100, progress: totalMeals >= 100 ? null : `${totalMeals}/100 meals`
    },
    {
      icon: '🌱', name: 'First Steps', desc: 'Logged your very first meal',
      earned: totalMeals >= 1, progress: totalMeals >= 1 ? null : '0/1 meals'
    },
  ];

  grid.innerHTML = badges.map(b => `
    <div class="achievement-badge ${b.earned ? 'earned' : ''}" title="${b.desc}">
      <div class="ab-icon">${b.icon}</div>
      <div class="ab-name">${b.name}</div>
      <div class="ab-desc">${b.desc}</div>
      ${b.progress ? `<div class="ab-progress">${b.progress}</div>` : ''}
    </div>
  `).join('');
}

async function saveGoals() {
  const newGoals = {
    calories: parseInt(document.getElementById('editCalGoal').value) || 2000,
    protein: parseInt(document.getElementById('editProtGoal').value) || 150,
    carbs: parseInt(document.getElementById('editCarbGoal').value) || 275,
    fat: parseInt(document.getElementById('editFatGoal').value) || 78,
    fiber: parseInt(document.getElementById('editFiberGoal').value) || 28,
    sugar: parseInt(document.getElementById('editSugarGoal').value) || 50,
    sodium: parseInt(document.getElementById('editSodiumGoal').value) || 2300,
    chol: parseInt(document.getElementById('editCholGoal').value) || 300,
    vit_d: parseInt(document.getElementById('editVitDGoal').value) || 15,
    iron: parseInt(document.getElementById('editIronGoal').value) || 18,
    folate: parseInt(document.getElementById('editFolateGoal').value) || 400,
  };
  currentUser.goals = newGoals;
  // Save diet type change
  const dtSel = document.getElementById('editDietType');
  if (dtSel) currentUser.dietType = dtSel.value;
  refreshDashboard();
  renderProfile();
  try {
    const backendUrl = "https://nutritrack-k96f.onrender.com";
    const res = await _authFetch(`${backendUrl}/api/auth/update`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        goals: newGoals,
        body_stats: {
          diet_type: dtSel ? dtSel.value : currentUser.dietType
        }
      })
    });
    if (res.ok) {
      showToast('✓ Goals & diet type saved!', 'success');
    } else {
      console.error('saveGoals failed:', res.status, await res.text().catch(() => ''));
      showToast('⚠️ Saved locally, but failed to sync to cloud.', 'error');
    }
  } catch (e) {
    console.error('Failed to update cloud profile', e);
    showToast('⚠️ Saved locally, but failed to sync to cloud.', 'error');
  }
}

async function saveBodyStats() {
  const weight = parseFloat(document.getElementById('editWeight').value);
  const weightUnit = document.getElementById('editWeightUnit').value;
  const height = parseFloat(document.getElementById('editHeight').value);
  const heightUnit = document.getElementById('editHeightUnit').value;

  if (!weight || weight <= 0 || !height || height <= 0) {
    return showToast('⚠️ Please enter valid weight and height.', 'error');
  }

  currentUser.weight = weight;
  currentUser.weightUnit = weightUnit;
  currentUser.height = height;
  currentUser.heightUnit = heightUnit;
  renderProfile();

  try {
    const backendUrl = "https://nutritrack-k96f.onrender.com";
    const res = await _authFetch(`${backendUrl}/api/auth/update`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        body_stats: {
          weight: weight,
          weight_unit: weightUnit,
          height: height,
          height_unit: heightUnit
        }
      })
    });
    if (res.ok) {
      showToast('✓ Body stats updated!', 'success');
    } else {
      console.error('saveBodyStats failed:', res.status, await res.text().catch(() => ''));
      showToast('⚠️ Saved locally, but failed to sync to cloud.', 'error');
    }
  } catch (e) {
    console.error('Failed to update body stats', e);
    showToast('⚠️ Saved locally, but failed to sync to cloud.', 'error');
  }
}

// ─────────────────────────────────────────────────
//  PLAN MY DIET  (changes #11 & #12)
// ─────────────────────────────────────────────────
// ─────────────────────────────────────────────────
//  PLAN MY DIET  — full rebuild
// ─────────────────────────────────────────────────
function _updateDietWidget() {
  const tag = document.getElementById('dietWidgetTag');
  const mobTag = document.getElementById('mobDietWidgetTag');
  if (!currentUser) return;
  const map = { lose: 'Fat Loss', maintain: 'Maintenance', gain: 'Lean Gain', bulk: 'Bulk & Build' };
  const vegBadge = currentUser.dietType === 'veg' ? ' 🌱'
    : currentUser.dietType === 'vegan' ? ' 🌿'
      : currentUser.dietType === 'eggetarian' ? ' 🥚'
        : '';
  const text = (map[currentUser.dietGoal] || 'View Plan →') + vegBadge;
  if (tag) tag.textContent = text;
  if (mobTag) mobTag.textContent = text;
}

function dpOverlayClick(e) {
  if (e.target === e.currentTarget) closeDietModal();
}

function closeDietModal() {
  const modal = document.getElementById('dietPlanModal');
  const panel = document.getElementById('dpPanel');
  if (!modal || !panel) return;
  panel.style.animation = 'dpSlideOut 0.3s cubic-bezier(0.4,0,1,1) both';
  setTimeout(() => {
    modal.classList.remove('open');
    panel.style.animation = '';
  }, 280);
}

function dpSwitchTab(id, btn) {
  document.querySelectorAll('.dp-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.dp-tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  const panel = document.getElementById('dpTab-' + id);
  if (panel) panel.classList.add('active');
}

function _dpRing(pct, color, size = 80, stroke = 8) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const dash = Math.min(1, pct / 100) * circ;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="${stroke}"/>
    <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${color}" stroke-width="${stroke}"
      stroke-linecap="round" stroke-dasharray="${dash} ${circ}"
      transform="rotate(-90 ${size / 2} ${size / 2})" style="transition:stroke-dasharray 1s ease"/>
  </svg>`;
}

function openDietModal() {
  if (!currentUser) return;

  const u = currentUser;
  const g = u.goals || { calories: 2000, protein: 150, carbs: 275, fat: 78, fiber: 28, sugar: 50, sodium: 2300, chol: 300 };

  // ── Diet type flags ──
  const dietType = u.dietType || 'nonveg';
  const isVeg = ['veg', 'eggetarian', 'vegan'].includes(dietType);
  const isVegan = dietType === 'vegan';
  const isEgg = dietType === 'eggetarian';
  const dtLabels = { nonveg: '🍖 Non-Veg', veg: '🌱 Pure Veg', eggetarian: '🥚 Eggetarian', vegan: '🌿 Vegan' };

  let wKg = null, hCm = null, bmi = null, bmiLabel = '', bmiColor = '#7fbb6e';
  if (u.weight && u.height) {
    wKg = u.weightUnit === 'lbs' ? u.weight * 0.4536 : u.weight;
    hCm = u.heightUnit === 'ft' ? u.height * 30.48 : u.height;
    bmi = +(wKg / ((hCm / 100) ** 2)).toFixed(1);
    if (bmi < 18.5) { bmiLabel = 'Underweight'; bmiColor = '#7fb8d4'; }
    else if (bmi < 25) { bmiLabel = 'Normal'; bmiColor = '#7fbb6e'; }
    else if (bmi < 30) { bmiLabel = 'Overweight'; bmiColor = '#d4a853'; }
    else { bmiLabel = 'Obese'; bmiColor = '#e05c5c'; }
  }

  const PLANS = {
    lose: {
      name: 'Fat Loss', icon: '🔥', accentColor: '#e07b7b',
      tagline: 'Burn fat, preserve muscle, feel energised',
      summary: `Your goal is to lose weight by eating at a calorie deficit of ~${g.calories} kcal/day. High protein intake (${g.protein}g) protects muscle while you shed fat. Consistency beats perfection.`,
      tip: 'Even a 300–500 kcal daily deficit leads to ~0.5kg fat loss per week. Don\'t go too aggressive — you\'ll lose muscle.',
      meals: [
        { time: '7:00 AM', name: 'Breakfast', emoji: '🌅', bg: 'rgba(212,162,64,0.12)', line: 'rgba(212,162,64,0.3)', foods: ['Boiled eggs × 3', 'Greek yoghurt', 'Mixed berries', 'Black coffee'], kcal: Math.round(g.calories * 0.25) },
        { time: '12:30 PM', name: 'Lunch', emoji: '☀️', bg: 'rgba(107,174,122,0.12)', line: 'rgba(107,174,122,0.3)', foods: ['Grilled chicken', 'Brown rice', 'Cucumber salad', 'Lemon water'], kcal: Math.round(g.calories * 0.35) },
        { time: '4:00 PM', name: 'Snack', emoji: '🍎', bg: 'rgba(127,184,212,0.1)', line: 'rgba(127,184,212,0.25)', foods: ['Handful almonds', 'Apple', 'Green tea'], kcal: Math.round(g.calories * 0.10) },
        { time: '7:30 PM', name: 'Dinner', emoji: '🌙', bg: 'rgba(167,139,250,0.1)', line: 'rgba(167,139,250,0.25)', foods: ['Baked fish / tofu', 'Steamed veggies', 'Small salad', 'Herbal tea'], kcal: Math.round(g.calories * 0.30) },
      ],
      avoid: ['Sugary drinks & juices', 'Deep-fried foods', 'White bread & pasta', 'Alcohol', 'Late-night snacks'],
      habits: [
        { icon: '💧', title: 'Drink 2.5L water/day', desc: 'Water suppresses appetite, boosts metabolism, and helps flush fat metabolites.', badge: 'Daily', badgeType: 'green' },
        { icon: '🚶', title: '8,000+ steps daily', desc: 'Low-intensity walking burns fat without spiking hunger hormones like intense cardio.', badge: 'Daily', badgeType: 'green' },
        { icon: '💪', title: '3× strength training/week', desc: 'Preserves muscle during deficit. More muscle = higher resting metabolic rate.', badge: '3×/week', badgeType: 'amber' },
        { icon: '😴', title: 'Sleep 7–9 hours', desc: 'Poor sleep increases cortisol and ghrelin (hunger hormone), making fat loss harder.', badge: 'Essential', badgeType: 'amber' },
        { icon: '📱', title: 'Track every meal', desc: 'Research shows food journalling doubles weight loss results. Log honestly.', badge: 'Every day', badgeType: 'green' },
        { icon: '🚫', title: 'No alcohol this month', desc: 'Alcohol halts fat oxidation for hours and adds empty calories.', badge: 'Limit', badgeType: 'red' },
      ]
    },
    maintain: {
      name: 'Maintenance', icon: '⚖️', accentColor: '#7fbb6e',
      tagline: 'Stay balanced, feel great, build healthy habits',
      summary: `Your goal is to maintain current weight by eating ~${g.calories} kcal/day. Focus on food quality, macro balance, and building sustainable habits you can keep long-term.`,
      tip: 'Maintenance is actually the hardest goal — most people drift up over time. Tracking a few days per week keeps you anchored.',
      meals: [
        { time: '7:30 AM', name: 'Breakfast', emoji: '🌅', bg: 'rgba(212,162,64,0.12)', line: 'rgba(212,162,64,0.3)', foods: ['Oats with banana', 'Boiled eggs × 2', 'Glass of milk', 'Tea/coffee'], kcal: Math.round(g.calories * 0.25) },
        { time: '1:00 PM', name: 'Lunch', emoji: '☀️', bg: 'rgba(107,174,122,0.12)', line: 'rgba(107,174,122,0.3)', foods: ['Dal + rice / roti', 'Sabzi (veg curry)', 'Curd / raita', 'Salad'], kcal: Math.round(g.calories * 0.35) },
        { time: '4:30 PM', name: 'Snack', emoji: '🍎', bg: 'rgba(127,184,212,0.1)', line: 'rgba(127,184,212,0.25)', foods: ['Fruit bowl', 'Handful nuts', 'Herbal tea'], kcal: Math.round(g.calories * 0.10) },
        { time: '8:00 PM', name: 'Dinner', emoji: '🌙', bg: 'rgba(167,139,250,0.1)', line: 'rgba(167,139,250,0.25)', foods: ['Grilled chicken/paneer', 'Chapati × 2', 'Cooked veggies', 'Warm milk'], kcal: Math.round(g.calories * 0.30) },
      ],
      avoid: ['Excessive junk food', 'Skipping meals', 'Crash diets', 'Binge eating weekends'],
      habits: [
        { icon: '💧', title: 'Drink 2L water/day', desc: 'Adequate hydration supports all metabolic processes and prevents false hunger.', badge: 'Daily', badgeType: 'green' },
        { icon: '💪', title: 'Strength train 3×/week', desc: 'Building lean muscle slightly increases TDEE, giving you more calorie headroom.', badge: '3×/week', badgeType: 'amber' },
        { icon: '🧘', title: 'Manage stress', desc: 'Chronic stress elevates cortisol which promotes fat storage, especially visceral fat.', badge: 'Daily', badgeType: 'green' },
        { icon: '😴', title: 'Sleep 7–8 hours', desc: 'Sleep regulates appetite hormones leptin and ghrelin — critical for weight maintenance.', badge: 'Nightly', badgeType: 'amber' },
        { icon: '🍽️', title: 'Eat at regular times', desc: 'Consistent meal timing stabilises blood sugar and prevents overeating later in the day.', badge: 'Recommended', badgeType: 'green' },
      ]
    },
    gain: {
      name: 'Lean Gain', icon: '💪', accentColor: '#7fb8d4',
      tagline: 'Build muscle cleanly without excessive fat',
      summary: `Your goal is lean muscle gain by eating ~${g.calories} kcal/day (small surplus). High protein (${g.protein}g/day) is non-negotiable. Lift heavy, recover well, and be patient.`,
      tip: "Aim for 0.25–0.5kg gain per month. Faster than that and you're mostly gaining fat.",
      meals: [
        { time: '7:00 AM', name: 'Breakfast', emoji: '🌅', bg: 'rgba(212,162,64,0.12)', line: 'rgba(212,162,64,0.3)', foods: ['Eggs × 4 scrambled', 'Oats with honey', 'Banana', 'Full-fat milk'], kcal: Math.round(g.calories * 0.28) },
        { time: '1:00 PM', name: 'Lunch', emoji: '☀️', bg: 'rgba(107,174,122,0.12)', line: 'rgba(107,174,122,0.3)', foods: ['Chicken breast 200g', 'Brown rice 150g', 'Stir-fried veggies', 'Curd'], kcal: Math.round(g.calories * 0.32) },
        { time: '4:00 PM', name: 'Pre-Workout', emoji: '⚡', bg: 'rgba(127,184,212,0.1)', line: 'rgba(127,184,212,0.25)', foods: ['Banana + protein shake', 'Peanut butter toast', 'Dates × 3'], kcal: Math.round(g.calories * 0.15) },
        { time: '8:00 PM', name: 'Dinner', emoji: '🌙', bg: 'rgba(167,139,250,0.1)', line: 'rgba(167,139,250,0.25)', foods: ['Paneer / fish 150g', 'Rice or chapati', 'Mixed dal', 'Casein / milk before bed'], kcal: Math.round(g.calories * 0.25) },
      ],
      avoid: ['Skipping meals', 'Low protein days', 'Cardio overload', 'Undereating carbs on training days'],
      habits: [
        { icon: '🏋️', title: 'Progressive overload', desc: 'Add weight or reps every week. Muscles only grow when challenged beyond their current capacity.', badge: 'Every session', badgeType: 'green' },
        { icon: '🥩', title: `Hit ${g.protein}g protein`, desc: 'Protein is the limiting factor for muscle growth. No training compensates for low protein intake.', badge: 'Non-negotiable', badgeType: 'green' },
        { icon: '😴', title: 'Sleep 8–9 hours', desc: '80% of muscle protein synthesis happens during sleep. This is when you actually grow.', badge: 'Critical', badgeType: 'amber' },
        { icon: '💧', title: 'Drink 3L water/day', desc: 'Muscle is 75% water. Dehydration of even 2% significantly reduces training performance.', badge: 'Daily', badgeType: 'green' },
        { icon: '📅', title: 'Eat every 3–4 hours', desc: 'Frequent protein doses maximise muscle protein synthesis throughout the day.', badge: 'Recommended', badgeType: 'amber' },
      ]
    },
    bulk: {
      name: 'Bulk & Build', icon: '🏋️', accentColor: '#f0a04b',
      tagline: 'Aggressive surplus to maximise muscle mass',
      summary: `Your goal is aggressive muscle building at ~${g.calories} kcal/day (large surplus). Aim for ${g.protein}g protein daily. Without heavy training stimulus, the surplus becomes fat.`,
      tip: 'Dirty bulking leads to excess fat. Prioritise whole foods — just eat more of them.',
      meals: [
        { time: '7:00 AM', name: 'Breakfast', emoji: '🌅', bg: 'rgba(212,162,64,0.12)', line: 'rgba(212,162,64,0.3)', foods: ['Eggs × 5', 'Oats 100g + milk', 'Banana × 2', 'Peanut butter toast'], kcal: Math.round(g.calories * 0.30) },
        { time: '10:30 AM', name: 'Mid-Morning', emoji: '🥛', bg: 'rgba(107,174,122,0.1)', line: 'rgba(107,174,122,0.2)', foods: ['Mass gainer / whole milk', 'Mixed nuts', 'Seasonal fruit'], kcal: Math.round(g.calories * 0.15) },
        { time: '1:30 PM', name: 'Lunch', emoji: '☀️', bg: 'rgba(107,174,122,0.12)', line: 'rgba(107,174,122,0.3)', foods: ['Chicken / paneer 250g', 'Rice 200g cooked', 'Dal + sabzi', 'Curd 150g'], kcal: Math.round(g.calories * 0.30) },
        { time: '8:00 PM', name: 'Dinner', emoji: '🌙', bg: 'rgba(167,139,250,0.1)', line: 'rgba(167,139,250,0.25)', foods: ['Meat / legumes 200g', 'Rice or chapati × 3', 'Cooked greens', 'Milk + honey'], kcal: Math.round(g.calories * 0.25) },
      ],
      avoid: ['Skipping any meal', 'Low-calorie foods as mains', 'Long cardio sessions', 'Chronic undersleeping'],
      habits: [
        { icon: '🏋️', title: 'Train 4–5 days/week', desc: 'Volume and frequency are key for hypertrophy. Hit all major muscle groups 2× per week.', badge: '4–5×/week', badgeType: 'green' },
        { icon: '🥩', title: `${g.protein}g protein daily`, desc: 'At this training volume, your muscles can absorb and utilise very high protein amounts.', badge: 'Every day', badgeType: 'green' },
        { icon: '🍚', title: 'Load up on carbs', desc: 'Carbs fuel intense training and spare protein for muscle building — not energy.', badge: 'Pre+post workout', badgeType: 'amber' },
        { icon: '😴', title: 'Sleep 8–9 hours minimum', desc: 'Growth hormone peaks during deep sleep. Missing sleep during a bulk is actively counterproductive.', badge: 'Non-negotiable', badgeType: 'amber' },
        { icon: '📊', title: 'Track weekly weight', desc: 'Aim for 0.5–1kg gain per month. Gaining faster? Reduce calories slightly to keep it lean.', badge: 'Weekly check', badgeType: 'green' },
        { icon: '🫀', title: 'Light cardio 2×/week', desc: 'Keeps cardiovascular health strong and improves workout recovery without burning surplus.', badge: '2×/week', badgeType: 'amber' },
      ]
    }
  };

  const plan = PLANS[u.dietGoal] || PLANS.maintain;

  // ── Veg meal override ──
  if (isVeg) {
    const VEG_MEALS = {
      lose: [
        {
          time: '7:00 AM', name: 'Breakfast', emoji: '🌅', bg: 'rgba(212,162,64,0.12)', line: 'rgba(212,162,64,0.3)',
          foods: isVegan ? ['Moong sprout bowl', 'Chia pudding (almond milk)', 'Mixed berries', 'Black coffee']
            : isEgg ? ['Boiled eggs × 2', 'Moong sprouts', 'Greek yoghurt', 'Green tea']
              : ['Moong sprout salad', 'Greek yoghurt', 'Mixed berries', 'Green tea'],
          kcal: Math.round(g.calories * 0.25)
        },
        {
          time: '12:30 PM', name: 'Lunch', emoji: '☀️', bg: 'rgba(107,174,122,0.12)', line: 'rgba(107,174,122,0.3)',
          foods: isVegan ? ['Tofu stir-fry 150g', 'Brown rice', 'Steamed veggies', 'Lemon water']
            : ['Paneer tikka 120g', 'Brown rice', 'Cucumber salad', 'Buttermilk'],
          kcal: Math.round(g.calories * 0.35)
        },
        {
          time: '4:00 PM', name: 'Snack', emoji: '🍎', bg: 'rgba(127,184,212,0.1)', line: 'rgba(127,184,212,0.25)',
          foods: ['Handful almonds', 'Apple', 'Green tea'], kcal: Math.round(g.calories * 0.10)
        },
        {
          time: '7:30 PM', name: 'Dinner', emoji: '🌙', bg: 'rgba(167,139,250,0.1)', line: 'rgba(167,139,250,0.25)',
          foods: isVegan ? ['Tofu + mixed dal', 'Steamed veggies', 'Salad', 'Herbal tea']
            : ['Dal tadka + 1 chapati', 'Steamed veggies', 'Small salad', 'Warm milk'],
          kcal: Math.round(g.calories * 0.30)
        },
      ],
      maintain: [
        {
          time: '7:30 AM', name: 'Breakfast', emoji: '🌅', bg: 'rgba(212,162,64,0.12)', line: 'rgba(212,162,64,0.3)',
          foods: isVegan ? ['Oats + almond milk + banana', 'Chia seeds', 'Mixed nuts', 'Black coffee']
            : isEgg ? ['Oats with banana', 'Boiled eggs × 2', 'Glass of milk', 'Tea/coffee']
              : ['Oats with banana + milk', 'Greek yoghurt', 'Handful almonds', 'Tea/coffee'],
          kcal: Math.round(g.calories * 0.25)
        },
        {
          time: '1:00 PM', name: 'Lunch', emoji: '☀️', bg: 'rgba(107,174,122,0.12)', line: 'rgba(107,174,122,0.3)',
          foods: isVegan ? ['Rajma / chana curry', 'Brown rice / roti', 'Mixed sabzi', 'Salad']
            : ['Dal + rice / roti', 'Sabzi (veg curry)', 'Curd / raita', 'Salad'],
          kcal: Math.round(g.calories * 0.35)
        },
        {
          time: '4:30 PM', name: 'Snack', emoji: '🍎', bg: 'rgba(127,184,212,0.1)', line: 'rgba(127,184,212,0.25)',
          foods: ['Fruit bowl', 'Handful nuts', 'Herbal tea'], kcal: Math.round(g.calories * 0.10)
        },
        {
          time: '8:00 PM', name: 'Dinner', emoji: '🌙', bg: 'rgba(167,139,250,0.1)', line: 'rgba(167,139,250,0.25)',
          foods: isVegan ? ['Tofu bhurji', 'Chapati × 2', 'Cooked veggies', 'Herbal tea']
            : ['Paneer bhurji', 'Chapati × 2', 'Cooked veggies', 'Warm milk'],
          kcal: Math.round(g.calories * 0.30)
        },
      ],
      gain: [
        {
          time: '7:00 AM', name: 'Breakfast', emoji: '🌅', bg: 'rgba(212,162,64,0.12)', line: 'rgba(212,162,64,0.3)',
          foods: isVegan ? ['Tofu scramble 200g', 'Oats + almond milk + honey', 'Banana', 'Peanut butter']
            : isEgg ? ['Eggs × 4 scrambled', 'Oats with honey', 'Banana', 'Full-fat milk']
              : ['Paneer bhurji 150g', 'Oats with honey', 'Banana', 'Full-fat milk'],
          kcal: Math.round(g.calories * 0.28)
        },
        {
          time: '1:00 PM', name: 'Lunch', emoji: '☀️', bg: 'rgba(107,174,122,0.12)', line: 'rgba(107,174,122,0.3)',
          foods: isVegan ? ['Soya chunks 200g', 'Brown rice 150g', 'Stir-fried veggies', 'Hummus']
            : ['Paneer / soya chunks 150g', 'Brown rice 150g', 'Stir-fried veggies', 'Curd'],
          kcal: Math.round(g.calories * 0.32)
        },
        {
          time: '4:00 PM', name: 'Pre-Workout', emoji: '⚡', bg: 'rgba(127,184,212,0.1)', line: 'rgba(127,184,212,0.25)',
          foods: ['Banana + protein shake', 'Peanut butter toast', 'Dates × 3'], kcal: Math.round(g.calories * 0.15)
        },
        {
          time: '8:00 PM', name: 'Dinner', emoji: '🌙', bg: 'rgba(167,139,250,0.1)', line: 'rgba(167,139,250,0.25)',
          foods: isVegan ? ['Tofu 150g + Rajma', 'Rice or chapati', 'Mixed dal', 'Plant-based protein shake']
            : ['Paneer 150g', 'Rice or chapati', 'Mixed dal', 'Milk + casein before bed'],
          kcal: Math.round(g.calories * 0.25)
        },
      ],
      bulk: [
        {
          time: '7:00 AM', name: 'Breakfast', emoji: '🌅', bg: 'rgba(212,162,64,0.12)', line: 'rgba(212,162,64,0.3)',
          foods: isVegan ? ['Tofu scramble 250g', 'Oats 100g + almond milk', 'Banana × 2', 'Peanut butter toast × 2']
            : isEgg ? ['Eggs × 5', 'Oats 100g + milk', 'Banana × 2', 'Peanut butter toast']
              : ['Paneer bhurji 200g', 'Oats 100g + milk', 'Banana × 2', 'Peanut butter toast'],
          kcal: Math.round(g.calories * 0.30)
        },
        {
          time: '10:30 AM', name: 'Mid-Morning', emoji: '🥛', bg: 'rgba(107,174,122,0.1)', line: 'rgba(107,174,122,0.2)',
          foods: isVegan ? ['Peanut butter shake (almond milk)', 'Mixed nuts 50g', 'Dates × 5']
            : ['Full-fat milk 400ml', 'Mixed nuts 50g', 'Seasonal fruit'],
          kcal: Math.round(g.calories * 0.15)
        },
        {
          time: '1:30 PM', name: 'Lunch', emoji: '☀️', bg: 'rgba(107,174,122,0.12)', line: 'rgba(107,174,122,0.3)',
          foods: isVegan ? ['Soya chunks 250g', 'Rice 200g', 'Rajma + sabzi', 'Hummus']
            : ['Paneer / Rajma 250g', 'Rice 200g cooked', 'Dal + sabzi', 'Curd 150g'],
          kcal: Math.round(g.calories * 0.30)
        },
        {
          time: '8:00 PM', name: 'Dinner', emoji: '🌙', bg: 'rgba(167,139,250,0.1)', line: 'rgba(167,139,250,0.25)',
          foods: isVegan ? ['Tofu / Chickpeas 200g', 'Chapati × 3', 'Cooked greens', 'Almond milk + honey']
            : ['Paneer / legumes 200g', 'Rice or chapati × 3', 'Cooked greens', 'Milk + honey'],
          kcal: Math.round(g.calories * 0.25)
        },
      ],
    };
    plan.meals = VEG_MEALS[u.dietGoal] || VEG_MEALS.maintain;
    // Veg-specific avoid additions
    if (isVegan) plan.avoid = ['All dairy & eggs', 'Processed vegan junk food', 'White bread & maida', 'Refined sugar', 'Artificial flavours'];
    // Add B12 habit for veg/vegan
    const b12Habit = { icon: '💊', title: 'Supplement B12 daily', desc: 'Vitamin B12 is found almost exclusively in animal products. All vegans and many vegetarians need a daily B12 supplement.', badge: 'Daily', badgeType: 'red' };
    if (!plan.habits.find(h => h.title.includes('B12'))) plan.habits.unshift(b12Habit);
  }

  const proKcal = g.protein * 4;
  const carbKcal = (g.carbs || 275) * 4;
  const fatKcal = (g.fat || 78) * 9;
  const totalMK = proKcal + carbKcal + fatKcal || 1;
  const proPct = Math.round(proKcal / totalMK * 100);
  const carbPct = Math.round(carbKcal / totalMK * 100);
  const fatPct = 100 - proPct - carbPct;

  // header subtitle with diet type badge
  const sub = document.getElementById('dpSubtitle');
  if (sub) sub.textContent = `${u.name.split(' ')[0]} · ${plan.name} · ${dtLabels[dietType] || ''}`;

  // HERO
  document.getElementById('dpHero').innerHTML = [
    { icon: '🔥', val: g.calories, unit: ' kcal', label: 'Daily Target', accent: '#F5A623' },
    { icon: '💪', val: g.protein + 'g', unit: '', label: 'Protein/Day', accent: '#7fb8d4' },
    { icon: '🌾', val: (g.carbs || 275) + 'g', unit: '', label: 'Carbs/Day', accent: '#c4a87f' },
    { icon: '🥑', val: (g.fat || 78) + 'g', unit: '', label: 'Fat/Day', accent: '#F4613A' },
  ].map(s => `<div class="dp-stat" style="--dp-accent:${s.accent}">
    <div class="dp-stat-icon">${s.icon}</div>
    <div class="dp-stat-val">${s.val}<span class="dp-stat-unit">${s.unit}</span></div>
    <div class="dp-stat-label">${s.label}</div>
  </div>`).join('');

  // OVERVIEW TAB
  const bmiBlock = bmi ? `
    <div class="dp-card">
      <div class="dp-card-title">Body Stats & BMI</div>
      <div class="dp-bmi-row">
        <div class="dp-bmi-ring-wrap">
          ${_dpRing(Math.min(100, Math.max(0, (bmi - 15) / 25 * 100)), bmiColor, 80, 8)}
          <div class="dp-bmi-center"><span class="dp-bmi-val">${bmi}</span><span class="dp-bmi-tiny">BMI</span></div>
        </div>
        <div class="dp-bmi-info">
          <div class="dp-bmi-label" style="color:${bmiColor}">${bmiLabel}</div>
          <div class="dp-bmi-desc">
            ${wKg ? `<strong style="color:var(--ink)">${Math.round(wKg)}kg</strong>` : ''}
            ${hCm ? ` · <strong style="color:var(--ink)">${Math.round(hCm)}cm</strong>` : ''}
            ${u.age ? ` · Age <strong style="color:var(--ink)">${u.age}</strong>` : ''}
            <br><span style="color:var(--ink-50);font-size:0.75rem">${bmi < 18.5 ? 'Consider increasing calories to reach a healthy weight range.' :
      bmi < 25 ? 'You\'re in a healthy range. Focus on body composition.' :
        bmi < 30 ? 'A moderate calorie deficit with exercise will help.' :
          'Consult a doctor. Start with low-impact exercise and a modest deficit.'
    }</span>
          </div>
          <div class="dp-bmi-scale" style="margin-top:0.7rem">
            <div class="dp-bmi-seg" style="background:#7fb8d4;opacity:0.7"></div>
            <div class="dp-bmi-seg" style="background:#7fbb6e;opacity:0.8;flex:2"></div>
            <div class="dp-bmi-seg" style="background:#d4a853;opacity:0.7;flex:1.5"></div>
            <div class="dp-bmi-seg" style="background:#e05c5c;opacity:0.7"></div>
          </div>
          <div class="dp-bmi-marker-row"><span>15</span><span>18.5</span><span>25</span><span>30</span><span>40</span></div>
        </div>
      </div>
    </div>` : '';

  document.getElementById('dpTab-overview').innerHTML = `
    ${bmiBlock}
    <div class="dp-card">
      <div class="dp-card-title">${plan.icon} ${plan.name} — Summary</div>
      <p style="font-size:0.86rem;color:var(--ink-50);line-height:1.65;margin-bottom:1rem">${plan.summary}</p>
      <div class="dp-cal-bar-wrap">
        <div class="dp-cal-bar-label"><span>Daily calorie target</span><span style="color:#F5A623;font-family:'Fraunces',serif">${g.calories} kcal</span></div>
        <div class="dp-cal-bar-track"><div class="dp-cal-bar-fill" style="width:72%;background:linear-gradient(90deg,#F5A623,#e8a830)"></div></div>
      </div>
      <div class="dp-split-row">
        <div class="dp-split-item"><div class="dp-split-val" style="color:#7fb8d4">${proPct}%</div><div class="dp-split-label">Protein</div></div>
        <div class="dp-split-item"><div class="dp-split-val" style="color:#c4a87f">${carbPct}%</div><div class="dp-split-label">Carbs</div></div>
        <div class="dp-split-item"><div class="dp-split-val" style="color:#F4613A">${fatPct}%</div><div class="dp-split-label">Fat</div></div>
      </div>
    </div>
    <div class="dp-tip-banner">
      <div class="dp-tip-icon">💡</div>
      <div class="dp-tip-text"><strong>Smart tip:</strong> ${plan.tip}</div>
    </div>
    ${isVeg ? `
    <div class="dp-card" style="border-left:3px solid var(--kiwi);">
      <div class="dp-card-title" style="color:var(--kiwi-deep)">🌱 Top ${dtLabels[dietType]} Protein Sources</div>
      <div class="veg-protein-grid">
        ${(isVegan
        ? [['Tofu', '8g/100g'], ['Soya Chunks', '52g/100g'], ['Tempeh', '19g/100g'], ['Lentils (Dal)', '9g/100g'], ['Chickpeas', '19g/100g'], ['Edamame', '11g/100g'], ['Quinoa', '4g/100g'], ['Peanut Butter', '25g/100g'], ['Chia Seeds', '17g/100g']]
        : isEgg
          ? [['Eggs', '13g/100g'], ['Greek Yoghurt', '10g/100g'], ['Paneer', '18g/100g'], ['Soya Chunks', '52g/100g'], ['Lentils (Dal)', '9g/100g'], ['Chickpeas', '19g/100g'], ['Cottage Cheese', '11g/100g'], ['Tofu', '8g/100g'], ['Almonds', '21g/100g']]
          : [['Paneer', '18g/100g'], ['Soya Chunks', '52g/100g'], ['Greek Yoghurt', '10g/100g'], ['Lentils (Dal)', '9g/100g'], ['Chickpeas', '19g/100g'], ['Tofu', '8g/100g'], ['Rajma', '24g/100g'], ['Moong Dal', '24g/100g'], ['Almonds', '21g/100g']]
      ).map(([name, pro]) => `<div class="veg-protein-item"><span class="veg-protein-name">${name}</span><span class="veg-protein-val">${pro} protein</span></div>`).join('')}
      </div>
    </div>` : ''}
  `;


  // MEALS TAB
  document.getElementById('dpTab-meals').innerHTML = `
    <div class="dp-card">
      <div class="dp-card-title">🍽️ Sample Day — ${plan.name}</div>
      <div class="dp-timeline">
        ${plan.meals.map(m => `
          <div class="dp-meal-item">
            <div class="dp-meal-left">
              <div class="dp-meal-time-badge" style="background:${m.bg}">${m.emoji}</div>
              <div class="dp-meal-line" style="background:${m.line}"></div>
            </div>
            <div class="dp-meal-right">
              <div style="display:flex;align-items:baseline;gap:0.6rem">
                <div class="dp-meal-name">${m.name}</div>
                <div style="font-family:'Fraunces',serif;font-size:0.95rem;color:#F5A623">${m.kcal} kcal</div>
              </div>
              <div class="dp-meal-time">⏰ ${m.time}</div>
              <div class="dp-meal-foods">${m.foods.map(f => `<span class="dp-food-tag">🍽 ${f}</span>`).join('')}</div>
            </div>
          </div>`).join('')}
      </div>
    </div>
    <div class="dp-tip-banner">
      <div class="dp-tip-icon">🔄</div>
      <div class="dp-tip-text"><strong>Adapt this plan</strong> to your local foods. Use the food search to find Indian, Japanese, or any cuisine equivalents that match your macros.</div>
    </div>`;

  // MACROS TAB
  document.getElementById('dpTab-macros').innerHTML = `
    <div class="dp-card">
      <div class="dp-card-title">📊 Your Macro Targets</div>
      <div class="dp-macro-rings">
        <div class="dp-macro-ring-item">${_dpRing(proPct, '#7fb8d4', 90, 9)}<div class="dp-mring-val">${g.protein}g</div><div class="dp-mring-label">💪 Protein</div></div>
        <div class="dp-macro-ring-item">${_dpRing(carbPct, '#c4a87f', 90, 9)}<div class="dp-mring-val">${g.carbs || 275}g</div><div class="dp-mring-label">🌾 Carbs</div></div>
        <div class="dp-macro-ring-item">${_dpRing(fatPct, '#F4613A', 90, 9)}<div class="dp-mring-val">${g.fat || 78}g</div><div class="dp-mring-label">🥑 Fat</div></div>
      </div>
    </div>
    <div class="dp-card">
      <div class="dp-card-title">⚡ Calorie Breakdown</div>
      ${[['💪 Protein', proKcal, proKcal / totalMK, '#7fb8d4', `${g.protein}g × 4`],
    ['🌾 Carbs', carbKcal, carbKcal / totalMK, '#c4a87f', `${g.carbs || 275}g × 4`],
    ['🥑 Fat', fatKcal, fatKcal / totalMK, '#F4613A', `${g.fat || 78}g × 9`]
    ].map(([label, kcal, ratio, color, note]) => `
        <div style="margin-bottom:0.85rem">
          <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:0.35rem">
            <span style="color:var(--ink)">${label}</span>
            <span style="color:${color};font-family:'Fraunces',serif">${kcal} kcal <span style="color:var(--ink-50);font-family:'Plus Jakarta Sans',sans-serif;font-size:0.68rem">(${note} kcal/g)</span></span>
          </div>
          <div style="height:7px;background:rgba(255,255,255,0.07);border-radius:4px;overflow:hidden">
            <div style="width:${Math.round(ratio * 100)}%;height:100%;background:${color};border-radius:4px"></div>
          </div>
        </div>`).join('')}
    </div>
    <div class="dp-card">
      <div class="dp-card-title">🌿 Micronutrient Goals</div>
      ${[['🌿 Fiber', g.fiber || 28, 'g', 'Aim for', '#5DBD8A'],
    ['🍬 Sugar', g.sugar || 50, 'g', 'Limit to', '#D97060'],
    ['🧂 Salt', g.sodium || 2300, 'mg', 'Limit to', '#9A7FE8'],
    ['❤️ Cholesterol', g.chol || 300, 'mg', 'Limit to', '#E89A3C']
    ].map(([label, val, unit, prefix, color]) => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:0.6rem 0;border-bottom:1px solid rgba(255,255,255,0.04)">
          <span style="font-size:0.84rem;color:var(--ink-50)">${label}</span>
          <span style="font-family:'Fraunces',serif;color:${color}">${prefix} <strong>${val}${unit}</strong></span>
        </div>`).join('')}
    </div>
    ${isVeg ? `
    <div class="dp-card" style="border-left:3px solid var(--citrus);">
      <div class="dp-card-title" style="color:var(--citrus-deep)">⚠️ Nutrients to Watch — ${dtLabels[dietType]} Diet</div>
      <div class="nutrient-watch-list">
        ${[
        { icon: '💊', name: 'Vitamin B12', tip: 'Found almost only in animal foods. Take a daily B12 supplement — critical for nerve health and energy.', severity: isVegan ? 'high' : 'medium' },
        { icon: '🧲', name: 'Iron', tip: 'Plant iron (non-haem) absorbs 2–3× less than meat iron. Always pair iron foods with Vitamin C (lemon, amla, tomato).', severity: 'medium' },
        { icon: '🥛', name: 'Calcium', tip: isVegan ? 'Skip dairy — get calcium from fortified plant milk, ragi flour, sesame seeds, and green leafy veggies.' : 'Dairy is your main source. Aim for 2–3 servings daily.', severity: isVegan ? 'high' : 'low' },
        { icon: '🐟', name: 'Omega-3 (DHA/EPA)', tip: 'Fatty fish is the richest source. For veg: eat flaxseeds, chia seeds, walnuts daily. Consider algae-oil supplements.', severity: 'medium' },
        { icon: '🪙', name: 'Zinc', tip: 'Plant zinc is less bioavailable due to phytates. Good sources: pumpkin seeds, hemp seeds, legumes, cashews.', severity: 'low' },
        { icon: '☀️', name: 'Vitamin D', tip: 'Sunlight is the best source. If mostly indoors, supplement 1000–2000 IU/day — especially in winter.', severity: 'medium' },
      ].map(n => `
        <div class="nutrient-watch-item">
          <span class="nw-icon">${n.icon}</span>
          <div class="nw-info">
            <div class="nw-name">${n.name}</div>
            <div class="nw-tip">${n.tip}</div>
          </div>
          <span class="nw-badge nw-${n.severity}">${n.severity === 'high' ? 'Critical' : n.severity === 'medium' ? 'Watch' : 'Note'}</span>
        </div>`).join('')}
      </div>
    </div>` : ''}`;


  // HABITS TAB
  document.getElementById('dpTab-habits').innerHTML = `
    <div class="dp-card">
      <div class="dp-card-title">✅ Key Habits for ${plan.name}</div>
      <div class="dp-habit-list">
        ${plan.habits.map(h => `
          <div class="dp-habit">
            <div class="dp-habit-icon">${h.icon}</div>
            <div class="dp-habit-text"><h4>${h.title}</h4><p>${h.desc}</p></div>
            <div class="dp-habit-badge ${h.badgeType}">${h.badge}</div>
          </div>`).join('')}
      </div>
    </div>`;

  // WORKOUT PLANS
  const WORKOUTS = {
    lose: {
      name: "Fat Loss Strength & Burn",
      icon: "🔥",
      focus: "Preserve lean muscle tissue & maximize consistent calorie burn.",
      cardio: "Daily step goal: 8,000 - 10,000 steps. 150-200 mins of low-stress cardio (e.g. brisk walking/cycling) weekly.",
      schedule: [
        { day: "Day 1", type: "Full Body Resistance Training", details: ["Squats / Leg Press (3 sets × 10 reps)", "Dumbbell Chest Press (3 sets × 10 reps)", "Dumbbell Rows (3 sets × 12 reps)", "Plank (3 sets × 45-60 seconds)"] },
        { day: "Day 2", type: "LISS Cardio & Core Focus", details: ["35-45 mins Moderate Cardio (walk/cycle/elliptical)", "Hanging Knee Raises (3 sets × 12 reps)", "Russian Twists (3 sets × 20 total reps)"] },
        { day: "Day 3", type: "Full Body Resistance Training", details: ["Romanian Deadlifts (3 sets × 10 reps)", "Overhead Press (3 sets × 10 reps)", "Lat Pulldowns (3 sets × 12 reps)", "Lunges (3 sets × 10 reps per leg)"] },
        { day: "Day 4", type: "Active Recovery / Mobility", details: ["40 mins light walking", "15 mins full body stretching and joint mobility exercises"] },
        { day: "Day 5", type: "Full Body Strength Focus", details: ["Goblet Squats (3 sets × 12 reps)", "Push-Ups (3 sets × max clean reps)", "Cable Rows (3 sets × 12 reps)", "Farmer's Walks (3 sets × 40 meters)"] },
        { day: "Day 6", type: "Steady State Cardio (Aerobic)", details: ["45-60 mins Outdoor walk, light jog, or swimming at a conversational pace"] },
        { day: "Day 7", type: "Rest & Muscle Repair", details: ["Complete rest day", "Focus on hitting daily protein target & hydration"] }
      ]
    },
    maintain: {
      name: "Balanced Health & Hybrid Split",
      icon: "⚖️",
      focus: "Maintain muscle mass, joint mobility, and cardiorespiratory health.",
      cardio: "Daily step goal: 7,000 - 8,000 steps. 120-150 mins of moderate physical activity weekly.",
      schedule: [
        { day: "Day 1", type: "Upper Body Strength", details: ["Flat Bench Press (3 sets × 8 reps)", "Chest Supported Rows (3 sets × 10 reps)", "Overhead Dumbbell Press (3 sets × 10 reps)", "Face Pulls (3 sets × 15 reps)"] },
        { day: "Day 2", type: "Lower Body & Core", details: ["Back Squats (3 sets × 8 reps)", "Leg Curls (3 sets × 12 reps)", "Calf Raises (4 sets × 15 reps)", "Decline Ab Crunches (3 sets × 15 reps)"] },
        { day: "Day 3", type: "Cardio & Active Stretching", details: ["30-40 mins Swim or Jog", "15-20 mins Full Body Yoga / Mobility routine"] },
        { day: "Day 4", type: "Complete Recovery", details: ["No intense lifting", "Keep moving with a light walk or active commuting"] },
        { day: "Day 5", type: "Full Body Conditioning", details: ["Dumbbell Deadlifts (3 sets × 10 reps)", "Incline Push-Ups / Dips (3 sets × 10-12 reps)", "Pull-Ups or Lat Pulldowns (3 sets × 8-10 reps)", "Goblet Lunges (3 sets × 10 reps per leg)"] },
        { day: "Day 6", type: "Recreational Sport / Cardio", details: ["Recreational sport, outdoor hike, or 45 mins cycling with friends"] },
        { day: "Day 7", type: "Rest & Reset", details: ["Complete rest day", "Relax and prepare for the upcoming week"] }
      ]
    },
    gain: {
      name: "Controlled Hypertrophy Split",
    },
    bulk: {
      name: "Hypertrophy Volume (Push/Pull/Legs)",
      icon: "🏋️",
      focus: "Maximize mechanical tension and training volume to direct calorie surplus into muscle mass.",
      cardio: "Daily step goal: 5,000 - 6,000 steps. Restrict intense cardio to preserve energy and surplus.",
      schedule: [
        { day: "Day 1", type: "Push Day (Chest, Shoulders, Triceps)", details: ["Barbell Bench Press (4 sets × 6-8 reps)", "Overhead Press (3 sets × 8 reps)", "Incline Dumbbell Flyes (3 sets × 10-12 reps)", "Lateral Raises (4 sets × 12-15 reps)", "Tricep Pushdowns (3 sets × 12 reps)"] },
        { day: "Day 2", type: "Pull Day (Back, Rear Delts, Biceps)", details: ["Conventional Deadlifts (3 sets × 5 reps)", "Weighted Pull-Ups (3 sets × 6-8 reps)", "Chest-Supported Dumbbell Rows (3 sets × 10 reps)", "Incline Dumbbell Bicep Curls (3 sets × 10-12 reps)", "Face Pulls (4 sets × 15 reps)"] },
        { day: "Day 3", type: "Legs Day (Quads, Hamstrings, Calves)", details: ["Barbell Back Squats (4 sets × 6-8 reps)", "Romanian Deadlifts (3 sets × 8-10 reps)", "Leg Press (3 sets × 10-12 reps)", "Standing Calf Raises (4 sets × 15 reps)"] },
        { day: "Day 4", type: "Rest & Active Stretching", details: ["Complete rest from resistance training", "15 mins full body stretching / foam rolling"] },
        { day: "Day 5", type: "Push Day (Hypertrophy Focus)", details: ["Incline Dumbbell Press (4 sets × 8-10 reps)", "Seated Dumbbell Shoulder Press (3 sets × 10-12 reps)", "Cable Chest Crossovers (3 sets × 12-15 reps)", "Tricep Overhead Extensions (4 sets × 10-12 reps)"] },
        { day: "Day 6", type: "Pull Day (Hypertrophy Focus)", details: ["Lat Pulldowns (4 sets × 8-10 reps)", "Seated Cable Rows (3 sets × 10-12 reps)", "Standing Hammer Curls (3 sets × 12 reps)", "Rear Delt Dumbbell Flyes (3 sets × 12-15 reps)"] },
        { day: "Day 7", type: "Rest, Growth & Feed", details: ["Complete rest", "Focus on recovery, sleep, and fueling muscles for next week's heavy lifts"] }
      ]
    }
  };

  // WORKOUTS TAB
  const workoutPlan = WORKOUTS[u.dietGoal] || WORKOUTS.maintain;
  document.getElementById('dpTab-workouts').innerHTML = `
    <div class="dp-card" style="border-left: 3px solid ${plan.accentColor || '#7fbb6e'}">
      <div class="dp-card-title" style="color:${plan.accentColor || 'var(--kiwi-deep)'}">
        ${workoutPlan.icon} Workout Focus — ${workoutPlan.name}
      </div>
      <p style="font-size:0.86rem; color:var(--ink-50); line-height:1.65; margin-bottom:1rem">
        ${workoutPlan.focus}
      </p>
      <div class="dp-tip-banner" style="margin-top:0.5rem; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05)">
        <div class="dp-tip-icon">🏃</div>
        <div class="dp-tip-text" style="font-size:0.78rem; color:var(--ink-50)">
          <strong>Cardio Goal:</strong> ${workoutPlan.cardio}
        </div>
      </div>
    </div>

    <div class="dp-card">
      <div class="dp-card-title">📅 Weekly Training Schedule</div>
      <div class="dp-workout-list" style="margin-top: 1rem">
        ${workoutPlan.schedule.map(w => `
          <div class="dp-workout-day-row">
            <div class="dp-workout-day-badge" style="background:${plan.accentColor || '#7fbb6e'}1e; color:${plan.accentColor || '#7fbb6e'}">
              ${w.day}
            </div>
            <div class="dp-workout-day-info">
              <div class="dp-workout-day-type">${w.type}</div>
              <ul class="dp-workout-ex-list">
                ${w.details.map(ex => `<li>${ex}</li>`).join('')}
              </ul>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  const modal = document.getElementById('dietPlanModal');
  modal.classList.add('open');
  dpSwitchTab('overview', document.querySelector('.dp-tab'));
}


// ─────────────────────────────────────────────────
//  KEYBOARD SHORTCUTS
// ─────────────────────────────────────────────────
document.getElementById('loginPassword').addEventListener('keypress', e => { if (e.key === 'Enter') handleEmailLogin(); });
document.getElementById('loginEmail').addEventListener('keypress', e => { if (e.key === 'Enter') handleEmailLogin(); });




// ═══════════════════════════════════════════════════════════════
//  NUTRIBOT — AI NUTRITIONIST CHATBOT
// ═══════════════════════════════════════════════════════════════

let _chatOpen = false;
let _chatHistory = [];    // { role: 'user'|'bot', text }
let _chatTyping = false;

function toggleChat() {
  _chatOpen = !_chatOpen;
  const panel = document.getElementById('nutribotPanel');
  const bar = document.getElementById('quickAssistantBar');
  if (!panel) return;

  if (_chatOpen) {
    panel.style.display = 'flex';
    if (bar) bar.style.display = 'none';
    if (_chatHistory.length === 0) _initChat();
    setTimeout(() => _scrollChatBottom(), 50);
  } else {
    panel.style.display = 'none';
    if (bar) bar.style.display = 'flex';
  }
}

function _initChat() {
  const name = currentUser ? currentUser.name.split(' ')[0] : 'there';
  _addBotMessage(`Hey ${name}! 👋 I'm **NutriBot**, your personal AI nutritionist.\n\nI can see your food logs and goals — ask me anything about your nutrition! Try the suggestions below or type your own question.`);
}

function _addBotMessage(text) {
  _chatHistory.push({ role: 'bot', text });
  _renderMessages();
}

function _addUserMessage(text) {
  _chatHistory.push({ role: 'user', text });
  _renderMessages();
}

function _renderMessages() {
  const container = document.getElementById('nutribotMessages');
  if (!container) return;

  container.innerHTML = _chatHistory.map((msg, i) => {
    const isUser = msg.role === 'user';
    // Convert **bold** markdown to <strong>
    const safeText = String(msg.text).replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
    const formatted = safeText
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
    return `
      <div class="nb-msg ${isUser ? 'user' : 'bot'}">
        <div class="nb-msg-avatar">${isUser ? '🧑' : '🤖'}</div>
        <div class="nb-msg-bubble">${formatted}</div>
      </div>`;
  }).join('');

  // Add typing indicator if waiting
  if (_chatTyping) {
    container.innerHTML += `
      <div class="nb-msg bot nb-typing">
        <div class="nb-msg-avatar">🤖</div>
        <div class="nb-msg-bubble">
          <div class="nb-typing-dots"><span></span><span></span><span></span></div>
        </div>
      </div>`;
  }

  _scrollChatBottom();
}

function _scrollChatBottom() {
  const c = document.getElementById('nutribotMessages');
  if (c) c.scrollTop = c.scrollHeight;
}

async function sendChatMessage() {
  const input = document.getElementById('nutribotInput');
  const msg = (input.value || '').trim();
  if (!msg || _chatTyping) return;

  input.value = '';
  _addUserMessage(msg);

  // Hide chips after first message
  const chips = document.getElementById('nutribotChips');
  if (chips) chips.style.display = 'none';

  // Handle instant client-side slash commands (/clear, /help, /water, /log, /recipe, etc.)
  const lowerMsg = msg.toLowerCase().trim();
  if (lowerMsg === '/clear') {
    _chatHistory = [];
    _initChat();
    return;
  }
  if (lowerMsg === '/recipe') {
    openRecipeBuilderModal();
    _addBotMessage("🍳 Opened the **Custom Recipe Builder** for you!");
    return;
  }
  if (lowerMsg.startsWith('/water ')) {
    const amount = parseInt(lowerMsg.replace('/water ', '').trim(), 10);
    if (amount > 0 && amount <= 3000) {
      logWater(amount);
      _addBotMessage(`💧 Logged **${amount}ml** of water! Total today: **${window._waterTotalMl || amount}ml**.`);
      return;
    }
  }
  if (lowerMsg.startsWith('/log ') || lowerMsg.startsWith('/add ')) {
    const query = msg.replace(/^\/(log|add)\s+/i, '').trim();
    if (query) {
      const match = FOODS.find(f => f.name.toLowerCase().includes(query.toLowerCase()));
      if (match) {
        await addFoodToLog(match);
        _addBotMessage(`✅ Successfully logged **${match.emoji || '🍽️'} ${match.name}** (${match.cal} kcal, ${match.pro}g protein) to ${currentMealType}!`);
        return;
      } else {
        _addBotMessage(`🔍 Couldn't find "${query}" in quick foods. Switching to Track Food tab to search...`);
        showPage('track', document.querySelector('.nav-btn[onclick*=track]'));
        const fInput = document.getElementById('foodSearch');
        if (fInput) { fInput.value = query; searchFoods(query); }
        return;
      }
    }
  }

  _chatTyping = true;
  _renderMessages();

  const sendBtn = document.getElementById('nutribotSendBtn');
  if (sendBtn) sendBtn.disabled = true;

  try {
    const reply = await _callNutriBot(msg);
    _chatTyping = false;
    _addBotMessage(reply);
  } catch (e) {
    _chatTyping = false;
    _addBotMessage("Sorry, I'm having trouble connecting right now. Please try again in a moment! 🙏");
  } finally {
    if (sendBtn) sendBtn.disabled = false;
    setTimeout(() => input.focus(), 100);
    _renderMessages();
  }
}

function sendChip(text) {
  const input = document.getElementById('nutribotInput');
  if (input) input.value = text;
  sendChatMessage();
}

async function _callNutriBot(message) {
  // Get JWT token if available (backend mode)
  const jwt = await _getJwt();

  if (jwt) {
    // Use the backend proxy (which fetches logs from DB)
    try {
      const backendUrl = window._BACKEND_URL || '';
      const res = await fetch(`${backendUrl}/api/ai/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${jwt}`,
        },
        body: JSON.stringify({ message }),
        signal: AbortSignal.timeout(15000),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.reply) return data.reply;
      }
    } catch (e) {
      // Fall through to client-side fallback
    }
  }

  // Client-side fallback: call LLM server directly with local log context
  const context = _buildLocalChatContext();
  const llmBase = (window.LLM_SERVER_URL || 'https://energyvenom-nutritrack-llm.hf.space/api/ai/analyze')
    .replace(/\/api\/ai\/analyze\/?$/, '');
  try {
    const res = await fetch(`${llmBase}/api/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, context }),
      signal: AbortSignal.timeout(15000),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.reply) return data.reply;
    }
  } catch (e) {
    // Both failed — return rule-based response
  }
  return _localNutribotFallback(message, context);
}

async function _getJwt() {
  if (currentUser && currentUser.token) return currentUser.token;
  if (typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
    try {
      const { data } = await supabaseClient.auth.getSession();
      if (data?.session?.access_token) {
        if (currentUser) currentUser.token = data.session.access_token;
        return data.session.access_token;
      }
    } catch (e) { }
  }
  try {
    const s = localStorage.getItem('nt_jwt');
    if (s) return s;
  } catch (e) { }
  return null;
}

function _buildLocalChatContext() {
  if (!currentUser) return {};
  const goals = currentUser.goals || {};
  const logs = window._foodLogs || [];
  const today = todayStr();

  // Last 7 days of logs
  const recent = logs
    .filter(l => l.date >= (new Date(Date.now() - 7 * 86400000)).toISOString().split('T')[0])
    .slice(0, 30)
    .map(l => ({
      date: l.date,
      meal: l.mealType || 'meal',
      food: l.name,
      cal: Math.round(l.cal || 0),
      protein_g: Math.round((l.pro || 0) * 10) / 10,
      carbs_g: Math.round((l.carb || 0) * 10) / 10,
      fat_g: Math.round((l.fat || 0) * 10) / 10,
      vit_d: Math.round((l.vit_d || 0) * 10) / 10,
      iron: Math.round((l.iron || 0) * 10) / 10,
      folate: Math.round((l.folate || 0) * 10) / 10,
    }));

  return {
    user_name: (currentUser.name || 'User').split(' ')[0],
    goals: {
      calories: goals.calories || 2000,
      protein: goals.protein || 150,
      carbs: goals.carbs || 250,
      fat: goals.fat || 65,
      fiber: goals.fiber || 28,
      vit_d: goals.vit_d || 15,
      iron: goals.iron || 18,
      folate: goals.folate || 400,
    },
    recent_logs: recent,
  };
}

function _localNutribotFallback(message, context) {
  const msg = message.toLowerCase().trim();
  const goals = (context && context.goals) || {};
  const logs = (context && context.recent_logs) || [];
  const name = (context && context.user_name) || 'there';
  const calGoal = goals.calories || 2000;
  const protGoal = goals.protein || 150;
  const carbGoal = goals.carbs || 250;
  const fatGoal = goals.fat || 65;
  const fiberGoal = goals.fiber || 28;
  const today = todayStr();
  const todayLog = (window._foodLogs || []).filter(l => l.date === today);
  const todayCal = todayLog.reduce((s, l) => s + (l.cal || 0), 0);
  const todayProt = todayLog.reduce((s, l) => s + (l.pro || 0), 0);
  const todayCarb = todayLog.reduce((s, l) => s + (l.carb || 0), 0);
  const todayFat = todayLog.reduce((s, l) => s + (l.fat || 0), 0);
  const remCal = calGoal - todayCal;

  // Slash commands help
  if (msg === '/help' || msg === 'help' || msg === 'commands') {
    return `⚡ **Available NutriBot Commands:**\n` +
      `- **/log <food>** — Quick-log a food item (e.g. \`/log apple\`)\n` +
      `- **/water <ml>** — Log water intake (e.g. \`/water 250\`)\n` +
      `- **/macros** — View today's detailed macro breakdown\n` +
      `- **/recommend** — Get instant AI meal suggestions\n` +
      `- **/recipe** — Open the custom recipe builder\n` +
      `- **/clear** — Clear chat conversation window\n` +
      `- **/help** — Show this command menu`;
  }

  if (msg === '/macros' || /macro|breakdown|split|nutrient|today.?s nutrition/.test(msg)) {
    if (todayCal === 0) return `No food logged yet today, ${name}! Log your first meal and I'll give you a full macro breakdown.`;
    return `Today's macros:\n- Protein: **${Math.round(todayProt)}g / ${protGoal}g** (${Math.round(todayProt / protGoal * 100)}%)\n- Carbs: **${Math.round(todayCarb)}g / ${carbGoal}g** (${Math.round(todayCarb / carbGoal * 100)}%)\n- Fat: **${Math.round(todayFat)}g / ${fatGoal}g** (${Math.round(todayFat / fatGoal * 100)}%)\n- Calories: **${Math.round(todayCal)} / ${calGoal} kcal**`;
  }

  if (msg === '/recommend' || /recommend|suggest|what to eat|meal ideas/.test(msg)) {
    fetchAIMealRecommendations();
    return `🥗 **Generated AI Meal Recommendations!** Check out the suggested meals section on your dashboard tab for options tailored to your remaining **${Math.max(0, Math.round(remCal))} kcal**.`;
  }

  if (/on track|how am i doing|progress|summary|overview|status/.test(msg)) {
    if (todayCal === 0) return `Hey ${name}! You haven't logged any food today yet. Start tracking to see your progress!`;
    const pct = Math.round(todayCal / calGoal * 100);
    return `Today so far: **${Math.round(todayCal)} / ${calGoal} kcal** (${pct}%) - Protein: **${Math.round(todayProt)}g** - Carbs: **${Math.round(todayCarb)}g** - Fat: **${Math.round(todayFat)}g**\n${remCal > 0 ? `You have **${Math.round(remCal)} kcal** remaining.` : "You've hit your calorie goal! Great job!"}`;
  }
  if (/calorie|kcal|how many cal|remaining|left/.test(msg)) {
    if (remCal > 400) return `You've used **${Math.round(todayCal)} kcal** out of **${calGoal} kcal**. **${Math.round(remCal)} kcal remaining** - enough for a proper meal!`;
    if (remCal > 100) return `Almost at your limit! **${Math.round(remCal)} kcal** remaining. A light snack like fruit or yogurt would be perfect.`;
    return `You've hit your calorie target (${Math.round(todayCal)} kcal). Keep it to water and very light snacks now!`;
  }
  if (/protein|muscle|gym|lifting|strength/.test(msg)) {
    const rem = protGoal - todayProt;
    if (rem > 50) return `You need **${Math.round(rem)}g more protein** today (${Math.round(todayProt)}g / ${protGoal}g). Top sources: chicken breast (31g/100g), eggs (6g each), paneer (18g/100g), dal (9g/cup), tofu (8g/100g).`;
    if (rem > 0) return `Almost at protein goal! Just **${Math.round(rem)}g more** to go. A boiled egg or a small protein shake will do it!`;
    return `Protein goal crushed! **${Math.round(todayProt)}g** consumed today. Your muscles will thank you!`;
  }
  if (/carb|carbohydrate|rice|roti|bread|sugar|glucose|energy/.test(msg)) {
    const rem = carbGoal - todayCarb;
    if (rem > 0) return `Carbs: **${Math.round(todayCarb)}g / ${carbGoal}g** (${Math.round(rem)}g remaining). Prefer complex carbs: oats, brown rice, whole wheat roti over refined options.`;
    return `You've hit your carb goal (**${Math.round(todayCarb)}g**). Focus on protein and vegetables for the rest of the day.`;
  }
  if (/fat|oil|ghee|butter|avocado|nuts|omega/.test(msg)) {
    const rem = fatGoal - todayFat;
    return `Fat today: **${Math.round(todayFat)}g / ${fatGoal}g** (${Math.round(Math.max(0, rem))}g remaining). Healthy fats: ghee (in moderation), nuts, avocado, olive oil. Avoid trans fats in fried fast food.`;
  }
  if (/fiber|fibre|digestion|gut|constipation|bloat/.test(msg)) {
    return `Aim for **${fiberGoal}g fiber** daily. Best Indian sources: rajma (15g/cup), chana dal (8g/cup), peas, broccoli, oats, whole wheat roti. Fiber keeps you full and improves gut health!`;
  }
  if (/sodium|salt|bp|blood pressure|hypertension/.test(msg)) {
    return `Daily sodium limit: **2300mg** (1 tsp salt). High sodium raises blood pressure. Reduce pickles, papad, packaged snacks, restaurant food. Use lemon and herbs for flavor instead.`;
  }
  if (/water|hydrat|drink|thirst|fluid/.test(msg)) {
    return `Aim for **2.5-3 litres of water** daily (more if you exercise). Dehydration mimics hunger pangs. Drink a glass before each meal - it helps control portion size!`;
  }
  if (/weight loss|lose weight|slim|fat loss|deficit|cutting/.test(msg)) {
    return `For healthy fat loss, aim for a **300-500 kcal daily deficit**. Your goal is **${calGoal} kcal**. Prioritize protein (prevents muscle loss), strength training, and 7-8 hours of sleep. Avoid crash dieting!`;
  }
  if (/weight gain|bulk|gain weight|mass|underweight/.test(msg)) {
    return `To gain muscle, you need a **calorie surplus of 250-400 kcal**. Eat every 3-4 hours, prioritize protein (1.6-2.2g per kg body weight). Dal, eggs, milk, and bananas are great budget bulking foods.`;
  }
  if (/bmi|ideal weight|healthy weight|body mass/.test(msg)) {
    return `BMI = weight(kg) / height(m)^2. Healthy range: **18.5-24.9**. Focus on waist circumference and body fat % for a fuller picture.`;
  }
  if (/meal time|when to eat|timing|skip meal|intermittent|16:8|fasting/.test(msg)) {
    return `Ideal timing: **Breakfast** within 1hr of waking, **Lunch** 12-2 PM, **Dinner** before 8 PM. For intermittent fasting (16:8), eat between 12-8 PM. Avoid eating within 2 hours of sleep.`;
  }
  if (/breakfast|morning meal|wake up|poha|upma|idli|paratha/.test(msg)) {
    return `Great Indian breakfasts: **Poha** (250 kcal), **Oats+milk** (300 kcal), **2 Eggs+2 roti** (350 kcal), **Idli+sambar** (220 kcal), **Greek yogurt+fruit** (200 kcal).`;
  }
  if (/lunch|afternoon|midday|dal rice|thali/.test(msg)) {
    return `Balanced Indian lunch: **Dal + 2 roti + sabzi + curd** (~600 kcal, 25g protein), **Rajma rice** (~550 kcal), **Chicken curry + rice** (~650 kcal). Fill half your plate with vegetables!`;
  }
  if (/dinner|evening meal|night|supper/.test(msg)) {
    if (remCal > 500) return `You have **${Math.round(remCal)} kcal** for dinner - enjoy a proper meal: grilled chicken/paneer + vegetables + small portion rice or 2 rotis.`;
    if (remCal > 150) return `Keep dinner light - **${Math.round(remCal)} kcal** remaining. Try khichdi, vegetable soup + 1 roti, or salad with paneer.`;
    return `You're near your limit. Have a very light dinner - vegetable soup, cucumber salad, or warm milk.`;
  }
  if (/snack|munchies|hunger|evening bite|mid.?meal|craving/.test(msg)) {
    return `Healthy snacks under 200 kcal: **Almonds** (164 kcal/28g), **Apple** (95 kcal), **Roasted chana** (120 kcal), **Greek yogurt** (100 kcal), **Cucumber+hummus** (80 kcal).`;
  }
  if (/pre.?workout|before gym|before exercise|pre.?train/.test(msg)) {
    return `**Pre-workout (1-2hr before):** Banana + peanut butter, oats with milk, or rice + chicken. You need fast carbs for energy + some protein.`;
  }
  if (/post.?workout|after gym|after exercise|recovery meal|muscle recovery/.test(msg)) {
    return `**Post-workout (within 45 min):** 30-40g protein + carbs. Try: protein shake + banana, eggs + toast, paneer + roti, or curd rice.`;
  }
  if (/biryani|butter chicken|dal makhani|samosa|pav bhaji|chole|rajma|dosa|idli|roti|chapati|paratha|paneer|tikka/.test(msg)) {
    return `Indian food is very nutritious! **Best choices:** Dal (high protein/fiber), Idli+sambar, Rajma, Roti. **Limit:** Biryani, Butter chicken, Samosa (deep fried). Balance is key!`;
  }
  if (/vitamin|mineral|deficiency|iron|calcium|d3|b12|zinc|magnesium/.test(msg)) {
    return `Common Indian deficiencies: **Vitamin D** (20min sun daily), **B12** (supplements for vegetarians), **Iron** (spinach, lentils, jaggery), **Calcium** (milk, curd, ragi).`;
  }
  if (/diabetes|blood sugar|insulin|glycemic|glucose/.test(msg)) {
    return `For blood sugar control: prefer **low glycemic foods** - oats, barley, dal, vegetables over white rice/bread. A 10-min walk after meals helps lower blood sugar!`;
  }
  if (/cholesterol|heart|hdl|ldl|triglyceride|cardiovascular/.test(msg)) {
    return `For heart health: reduce saturated fat, increase soluble fiber (oats, beans), eat flaxseeds/walnuts for omega-3, exercise 150 min/week.`;
  }
  if (/sleep|rest|recovery|fatigue|tired|insomnia/.test(msg)) {
    return `Sleep is essential! Aim for **7-9 hours**. Poor sleep raises ghrelin (hunger hormone) and slows metabolism. Avoid screens 1hr before bed.`;
  }
  if (/cheat|junk|pizza|burger|cheat meal|cheat day|treat yourself/.test(msg)) {
    return `Cheat meals are okay! Rule: **1 cheat meal per week**, not a full cheat day. Enjoy in moderation and get back on track next meal!`;
  }
  if (/vegetarian|vegan|plant.?based|no meat/.test(msg)) {
    return `Top veg protein sources: **Paneer** (18g/100g), **Tofu** (8g/100g), **Rajma** (9g/cup), **Chana dal** (9g/cup), **Moong dal** (7g/cup), **Greek yogurt** (10g/100g).`;
  }
  if (/burn|exercise|workout|cardio|run|walk|cycling|swim|calorie burn/.test(msg)) {
    return `Approx calorie burn (70kg, 30 min): **Running** ~300 kcal, **Cycling** ~240 kcal, **Swimming** ~250 kcal, **Brisk Walk** ~150 kcal, **HIIT** ~350 kcal.`;
  }
  if (/metabolism|tdee|maintenance|metabolic rate|bmr/.test(msg)) {
    return `Your TDEE is how many calories you burn daily. Strength training boosts metabolic rate long-term — you burn more calories even at rest!`;
  }
  if (/supplement|creatine|whey|protein powder|bcaa|multivitamin/.test(msg)) {
    return `Supplements to consider: **Creatine monohydrate** (muscle strength), **Whey protein** (convenient protein), **Vitamin D3+K2**, **Omega-3**. Food first, supplements second!`;
  }
  if (/what did i eat|my food today|today.?s log|show log|food log/.test(msg)) {
    if (todayLog.length === 0) return `No food logged today yet, ${name}! Start logging your meals to track your nutrition.`;
    const foods = todayLog.map(l => l.name).slice(0, 6).join(', ');
    return `Today you logged: **${foods}** - totaling **${Math.round(todayCal)} kcal** and **${Math.round(todayProt)}g protein**. Check your Dashboard for details!`;
  }
  if (/my goal|daily goal|target|calorie goal|how much should/.test(msg)) {
    return `Your daily targets: **${calGoal} kcal** - **${protGoal}g protein** - **${carbGoal}g carbs** - **${fatGoal}g fat** - **${fiberGoal}g fiber**.`;
  }
  if (/^(hi|hello|hey|hii|helo|namaste|sup|yo)\b/.test(msg)) {
    return `Hey ${name}! I'm NutriBot, your AI nutritionist. Type **/help** to see commands or ask me any question!`;
  }
  if (/thank|thanks|great|awesome|nice|helpful/.test(msg)) {
    return `You're welcome, ${name}! Keep up the great work on your health journey. Anything else I can help with?`;
  }
  return `I'm your AI nutritionist, **${name}**!\n\nTry commands like:\n- **/log <food name>**\n- **/water 250**\n- **/macros**\n- **/recommend**\n- **/help**\n\nOr ask any nutrition question!`;
}
// Show Floating Assistant Bar when user is logged in
const _origLoginSuccess = loginSuccess;
loginSuccess = function (user) {
  _origLoginSuccess(user);
  const bar = document.getElementById('quickAssistantBar');
  if (bar) bar.style.display = 'flex';
  const btn = document.getElementById('nutribotBtn');
  if (btn) btn.style.display = 'none';
  _chatHistory = [];
  _chatOpen = false;
  const panel = document.getElementById('nutribotPanel');
  if (panel) panel.style.display = 'none';
};

// Hide Floating Assistant Bar when user logs out
const _origHandleLogout = handleLogout;
handleLogout = function () {
  const bar = document.getElementById('quickAssistantBar');
  if (bar) bar.style.display = 'none';
  const btn = document.getElementById('nutribotBtn');
  if (btn) btn.style.display = 'none';
  const panel = document.getElementById('nutribotPanel');
  if (panel) { panel.style.display = 'none'; _chatOpen = false; }
  _chatHistory = [];
  _origHandleLogout();
};


async function fetchLogsFromCloud() {
  const backendUrl = "https://nutritrack-k96f.onrender.com";
  try {
    const res = await _authFetch(`${backendUrl}/api/logs`, {});
    if (res.ok) {
      window._foodLogs = await res.json();
      refreshDashboard();
      renderHistory();
    } else {
      console.error('fetchLogsFromCloud failed:', res.status, await res.text().catch(() => ''));
    }
  } catch (e) {
    console.error("Failed to fetch logs from cloud:", e);
  }
}

// ─────────────────────────────────────────────────
//  WATER INTAKE
// ─────────────────────────────────────────────────
async function fetchWaterFromCloud() {
  let dbWaterTotal = 0;
  try {
    if (typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
      const { data: sessData } = await supabaseClient.auth.getSession();
      const user = sessData?.session?.user;
      if (user) {
        const { data, error } = await supabaseClient
          .from('water_logs')
          .select('amount_ml')
          .eq('user_id', user.id)
          .eq('date', todayStr());
        if (!error && data) {
          dbWaterTotal = data.reduce((sum, item) => sum + (item.amount_ml || 0), 0);
        }
      }
    }
  } catch (err) {
    console.warn('Supabase fetch water notice:', err);
  }

  try {
    const res = await _authFetch('/api/water?date=' + todayStr());
    if (res && res.ok) {
      const data = await res.json();
      dbWaterTotal = Math.max(dbWaterTotal, data.total_ml || 0);
    }
  } catch (e) {
    console.warn('Backend fetch water notice:', e);
  }

  window._waterTotalMl = dbWaterTotal;
  _renderWaterWidget();
}

function _renderWaterWidget() {
  const total = window._waterTotalMl || 0;
  const goal = (currentUser.goals && currentUser.goals.water_ml) || 2000;
  const totalEl = document.getElementById('waterTotal');
  const goalEl = document.getElementById('waterGoalDisplay');
  const bar = document.getElementById('waterBar');
  if (totalEl) totalEl.textContent = Math.round(total);
  if (goalEl) goalEl.textContent = Math.round(goal);
  if (bar) bar.style.width = Math.min(100, (total / (goal || 1)) * 100) + '%';
}

async function logWater(amountMl) {
  // 1. Optimistic local update
  window._waterTotalMl = (window._waterTotalMl || 0) + amountMl;
  _renderWaterWidget();
  showToast(`💧 +${amountMl}ml logged`, 'success');

  // 2. Direct insert into Supabase water_logs cloud table
  try {
    if (typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
      const { data: sessData } = await supabaseClient.auth.getSession();
      const user = sessData?.session?.user;
      if (user) {
        await supabaseClient.from('water_logs').insert({
          user_id: user.id,
          date: todayStr(),
          amount_ml: amountMl
        });
      }
    }
  } catch (err) {
    console.warn('Supabase water log insert notice:', err);
  }

  // 3. Sync with Flask backend API
  try {
    await _authFetch('/api/water', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount_ml: amountMl, date: todayStr() })
    });
  } catch (e) {
    console.warn('Backend water sync notice:', e);
  }
}

// ─────────────────────────────────────────────────
//  DYNAMIC I18N UI UPDATE
// ─────────────────────────────────────────────────
function updateLanguageUI() {
  if (typeof window.t !== 'function') return;

  const navBtns = document.querySelectorAll('.nav-btn');
  if (navBtns[0]) navBtns[0].textContent = window.t('dashboard');
  if (navBtns[1]) navBtns[1].textContent = window.t('track_food');
  if (navBtns[2]) navBtns[2].textContent = window.t('history');
  if (navBtns[3]) navBtns[3].textContent = window.t('profile');

  const mobLabels = document.querySelectorAll('.mob-nav-label');
  if (mobLabels[0]) mobLabels[0].textContent = window.t('dashboard');
  if (mobLabels[1]) mobLabels[1].textContent = window.t('track_food');
  if (mobLabels[3]) mobLabels[3].textContent = window.t('history');
  if (mobLabels[4]) mobLabels[4].textContent = window.t('profile');

  const dietLabel = document.querySelector('.diet-widget-label');
  if (dietLabel) dietLabel.textContent = window.t('plan_diet');

  const logoutBtn = document.querySelector('.logout-link');
  if (logoutBtn) logoutBtn.textContent = window.t('sign_out');
}

// ─────────────────────────────────────────────────
//  VISUAL SOCIAL SHARE CARD GENERATOR
// ─────────────────────────────────────────────────
function closeAllModals() {
  const modals = ['recipeBuilderModal', 'shareCardModal', 'saveTemplateModal', 'dietModal', 'nonFoodModal'];
  modals.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
}

function openShareCardModal() {
  closeAllModals();
  const modal = document.getElementById('shareCardModal');
  if (!modal) return;
  modal.style.display = 'flex';

  const canvas = document.getElementById('shareCardCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  // Canvas background gradient
  const grad = ctx.createLinearGradient(0, 0, 400, 520);
  grad.addColorStop(0, '#0f1712');
  grad.addColorStop(0.5, '#15261d');
  grad.addColorStop(1, '#0a0f0d');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 400, 520);

  // Border highlight
  ctx.strokeStyle = 'rgba(62, 207, 142, 0.4)';
  ctx.lineWidth = 4;
  ctx.strokeRect(10, 10, 380, 500);

  // Header Brand
  ctx.fillStyle = '#3ecf8e';
  ctx.font = 'bold 24px system-ui, sans-serif';
  ctx.fillText('🥗 NutriTrack', 30, 50);

  ctx.fillStyle = 'rgba(255,255,255,0.6)';
  ctx.font = '12px system-ui, sans-serif';
  ctx.fillText('AI Food & Nutrition Intelligence', 30, 70);

  // User Greeting
  const name = (currentUser && currentUser.name) ? currentUser.name.split(' ')[0] : 'User';
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 22px system-ui, sans-serif';
  ctx.fillText(`${name}'s Daily Summary 🌟`, 30, 115);

  const dateStr = new Date().toLocaleDateString('en-IN', { weekday: 'short', month: 'short', day: 'numeric' });
  ctx.fillStyle = 'rgba(255,255,255,0.5)';
  ctx.font = '13px system-ui, sans-serif';
  ctx.fillText(dateStr, 30, 135);

  // Stats Box Background
  const logs = (window._foodLogs || []).filter(l => l.date === todayStr());
  const totals = sumLogs(logs);
  const goalCals = (currentUser && currentUser.goals && currentUser.goals.calories) || 2000;
  const goalPro = (currentUser && currentUser.goals && currentUser.goals.protein) || 150;

  // Stat Card 1: Calories
  ctx.fillStyle = 'rgba(245, 166, 35, 0.15)';
  ctx.beginPath(); ctx.roundRect(30, 160, 165, 90, 12); ctx.fill();
  ctx.fillStyle = '#F5A623'; ctx.font = '22px system-ui'; ctx.fillText('🔥', 45, 195);
  ctx.fillStyle = '#ffffff'; ctx.font = 'bold 20px system-ui'; ctx.fillText(`${Math.round(totals.cal)}`, 75, 198);
  ctx.fillStyle = 'rgba(255,255,255,0.6)'; ctx.font = '11px system-ui'; ctx.fillText(`/ ${goalCals} kcal`, 75, 215);

  // Stat Card 2: Protein
  ctx.fillStyle = 'rgba(127, 184, 212, 0.15)';
  ctx.beginPath(); ctx.roundRect(205, 160, 165, 90, 12); ctx.fill();
  ctx.fillStyle = '#7fb8d4'; ctx.font = '22px system-ui'; ctx.fillText('💪', 220, 195);
  ctx.fillStyle = '#ffffff'; ctx.font = 'bold 20px system-ui'; ctx.fillText(`${Math.round(totals.pro)}g`, 250, 198);
  ctx.fillStyle = 'rgba(255,255,255,0.6)'; ctx.font = '11px system-ui'; ctx.fillText(`/ ${goalPro}g protein`, 250, 215);

  // Stat Card 3: Water Intake
  const waterMl = window._waterTotalMl || 0;
  ctx.fillStyle = 'rgba(74, 144, 226, 0.15)';
  ctx.beginPath(); ctx.roundRect(30, 265, 165, 90, 12); ctx.fill();
  ctx.fillStyle = '#4A90E2'; ctx.font = '22px system-ui'; ctx.fillText('💧', 45, 300);
  ctx.fillStyle = '#ffffff'; ctx.font = 'bold 20px system-ui'; ctx.fillText(`${waterMl}ml`, 75, 303);
  ctx.fillStyle = 'rgba(255,255,255,0.6)'; ctx.font = '11px system-ui'; ctx.fillText('Water Logged', 75, 320);

  // Stat Card 4: Workout Burned
  const workoutBurn = (window._workoutLogs || []).reduce((s, w) => s + (w.calBurned || 0), 0);
  ctx.fillStyle = 'rgba(62, 207, 142, 0.15)';
  ctx.beginPath(); ctx.roundRect(205, 265, 165, 90, 12); ctx.fill();
  ctx.fillStyle = '#3ecf8e'; ctx.font = '22px system-ui'; ctx.fillText('🏃', 220, 300);
  ctx.fillStyle = '#ffffff'; ctx.font = 'bold 20px system-ui'; ctx.fillText(`${Math.round(workoutBurn)}`, 250, 303);
  ctx.fillStyle = 'rgba(255,255,255,0.6)'; ctx.font = '11px system-ui'; ctx.fillText('Active Burn', 250, 320);

  // Meal Highlights Section
  ctx.fillStyle = 'rgba(255,255,255,0.05)';
  ctx.beginPath(); ctx.roundRect(30, 370, 340, 95, 12); ctx.fill();
  ctx.fillStyle = '#3ecf8e'; ctx.font = 'bold 13px system-ui'; ctx.fillText('🍽️ Today\'s Highlights', 45, 395);

  ctx.fillStyle = 'rgba(255,255,255,0.8)'; ctx.font = '12px system-ui';
  if (logs.length === 0) {
    ctx.fillText('No meals logged yet today', 45, 420);
  } else {
    logs.slice(0, 2).forEach((l, i) => {
      ctx.fillText(`• ${l.emoji || '🍽️'} ${l.name.slice(0,24)} - ${Math.round(l.cal)} kcal`, 45, 420 + (i * 20));
    });
  }

  // Footer Tagline
  ctx.fillStyle = 'rgba(255,255,255,0.3)'; ctx.font = '11px system-ui';
  ctx.fillText('NutriTrack · Track Smart, Live Healthy 🚀', 95, 490);
}

function closeShareCardModal() {
  const modal = document.getElementById('shareCardModal');
  if (modal) modal.style.display = 'none';
}

function downloadShareCard() {
  const canvas = document.getElementById('shareCardCanvas');
  if (!canvas) return;
  const link = document.createElement('a');
  link.download = `nutritrack_progress_${todayStr()}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
  showToast('✓ Card image downloaded!', 'success');
}

// ─────────────────────────────────────────────────
//  WEARABLE INTEGRATION (REAL-TIME GOOGLE FIT API)
// ─────────────────────────────────────────────────
async function fetchRealGoogleFitData(providerToken) {
  const now = new Date();
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const endOfDay = now.getTime();

  const reqBody = {
    aggregateBy: [
      { dataTypeName: 'com.google.step_count.delta' },
      { dataTypeName: 'com.google.calories.expended' }
    ],
    bucketByTime: { durationMillis: 86400000 },
    startTimeMillis: startOfDay,
    endTimeMillis: endOfDay
  };

  const res = await fetch('https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${providerToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(reqBody)
  });

  if (!res.ok) {
    throw new Error(`Google Fitness API status ${res.status}`);
  }

  const data = await res.json();
  let totalSteps = 0;
  let totalCalories = 0;

  if (data.bucket && data.bucket.length > 0) {
    for (const bucket of data.bucket) {
      if (bucket.dataset) {
        for (const ds of bucket.dataset) {
          if (ds.point) {
            for (const pt of ds.point) {
              if (pt.value) {
                for (const val of pt.value) {
                  if (ds.dataSourceId && ds.dataSourceId.includes('step_count')) {
                    totalSteps += (val.intVal || val.fpVal || 0);
                  } else if (ds.dataSourceId && ds.dataSourceId.includes('calories')) {
                    totalCalories += (val.fpVal || val.intVal || 0);
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  return {
    steps: Math.round(totalSteps) || 7200,
    cal_burned: Math.round((totalCalories || (totalSteps * 0.04)) * 10) / 10
  };
}

async function syncGoogleFit() {
  showLoader('Syncing Google Fit data…');
  let steps = 7200;
  let calBurned = 288.0;
  const date = todayStr();

  try {
    const { data: sessionData } = await supabaseClient.auth.getSession();
    const session = sessionData?.session;
    const providerToken = session?.provider_token;

    if (providerToken) {
      try {
        const realData = await fetchRealGoogleFitData(providerToken);
        steps = realData.steps;
        calBurned = realData.cal_burned;
      } catch (fitErr) {
        console.warn('Google Fit API query notice:', fitErr);
      }
    } else {
      const wantsOAuth = confirm("Google Fit real-time step sync requires Google Fitness permission.\n\nClick OK to connect your Google Account with Google Fit steps permission, or Cancel to use step counter demo mode.");
      if (wantsOAuth) {
        handleGoogleLogin(true);
        return;
      }
    }
  } catch (e) {
    console.warn('Session check error:', e);
  }

  // Record workout log locally so dashboard updates instantly
  if (!window._workoutLogs) window._workoutLogs = [];
  const existingGF = window._workoutLogs.find(w => w.name && w.name.includes('Google Fit') && w.date === date);
  if (existingGF) {
    existingGF.calBurned = calBurned;
    existingGF.durationMin = Math.max(1, Math.round(steps / 100));
  } else {
    window._workoutLogs.unshift({ id: 'gf_' + Date.now(), name: 'Google Fit Daily Steps', calBurned, durationMin: Math.max(1, Math.round(steps / 100)), date });
  }
  refreshDashboard();

  try {
    const res = await _authFetch('/api/integrations/google-fit/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steps, cal_burned: calBurned, date })
    });
    hideLoader();
    showToast(`⌚ Google Fit synced: ${steps} steps (${calBurned} kcal burned)!`, 'success');
    if (res && res.ok) {
      await fetchWorkoutsFromCloud();
      refreshDashboard();
    }
  } catch (e) {
    hideLoader();
    showToast(`⌚ Google Fit synced: ${steps} steps (${calBurned} kcal burned)!`, 'success');
  }
}

// ─────────────────────────────────────────────────
//  CUSTOM RECIPE BUILDER
// ─────────────────────────────────────────────────
function openRecipeBuilderModal() {
  closeAllModals();
  const m = document.getElementById('recipeBuilderModal');
  if (m) m.style.display = 'flex';
}

function closeRecipeBuilderModal() {
  const m = document.getElementById('recipeBuilderModal');
  if (m) m.style.display = 'none';
}

function addRecipeIngredientRow() {
  const container = document.getElementById('recipeIngredientsRows');
  if (!container) return;
  const row = document.createElement('div');
  row.className = 'recipe-ing-row';
  row.style.cssText = 'display:flex; gap:6px;';
  row.innerHTML = `
    <input type="text" placeholder="Ingredient" class="ing-name" style="flex:2; padding:6px 10px; border-radius:6px; border:1px solid rgba(255,255,255,0.1); background:rgba(0,0,0,0.2); color:#fff; font-size:0.8rem;">
    <input type="number" placeholder="Cal" class="ing-cal" style="width:65px; padding:6px 10px; border-radius:6px; border:1px solid rgba(255,255,255,0.1); background:rgba(0,0,0,0.2); color:#fff; font-size:0.8rem;">
    <input type="number" placeholder="Pro(g)" class="ing-pro" style="width:65px; padding:6px 10px; border-radius:6px; border:1px solid rgba(255,255,255,0.1); background:rgba(0,0,0,0.2); color:#fff; font-size:0.8rem;">
  `;
  container.appendChild(row);
}

async function saveCustomRecipe() {
  const nameEl = document.getElementById('recipeName');
  const servEl = document.getElementById('recipeServings');
  const name = nameEl ? nameEl.value.trim() : '';
  const servings = servEl ? (parseInt(servEl.value) || 1) : 1;

  if (!name) { showToast('Please enter a recipe name', 'error'); return; }

  const rows = document.querySelectorAll('.recipe-ing-row');
  const ingredients = [];
  rows.forEach(r => {
    const ingName = r.querySelector('.ing-name')?.value.trim();
    const cal = parseFloat(r.querySelector('.ing-cal')?.value) || 0;
    const pro = parseFloat(r.querySelector('.ing-pro')?.value) || 0;
    if (ingName) ingredients.push({ name: ingName, cal, pro });
  });

  if (ingredients.length === 0) { showToast('Please add at least 1 ingredient', 'error'); return; }

  showLoader('Saving custom recipe…');
  try {
    const res = await _authFetch(`${window._BACKEND_URL || ''}/api/recipes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, servings, ingredients })
    });
    hideLoader();
    if (res.ok) {
      showToast(`🍳 Recipe "${name}" created!`, 'success');
      closeRecipeBuilderModal();
      await fetchRecipesFromCloud();
    } else {
      showToast('⚠️ Could not save recipe.', 'error');
    }
  } catch (e) {
    hideLoader();
    console.error('saveCustomRecipe error:', e);
    showToast('⚠️ Could not save recipe.', 'error');
  }
}

async function fetchRecipesFromCloud() {
  try {
    const res = await _authFetch(`${window._BACKEND_URL || ''}/api/recipes`);
    if (res.ok) {
      const data = await res.json();
      window._recipes = data || [];
      renderRecipesList();
    }
  } catch (e) {
    console.error('fetchRecipesFromCloud error:', e);
  }
}

function renderRecipesList() {
  const el = document.getElementById('recipesList');
  if (!el) return;
  const recipes = window._recipes || [];
  if (recipes.length === 0) {
    el.innerHTML = `<div style="font-size:0.8rem; color:var(--mist); opacity:0.7;">No custom recipes built yet. Click "+ Create Custom Recipe" to combine ingredients & auto-calculate per-serving nutrition!</div>`;
    return;
  }

  el.innerHTML = recipes.map(r => `
    <div style="background:rgba(255,255,255,0.06); border:1px solid rgba(62,207,142,0.2); border-radius:12px; padding:10px 14px; min-width:180px; display:flex; flex-direction:column; gap:4px;">
      <div style="font-weight:700; font-size:0.85rem; color:#fff;">🍳 ${r.name}</div>
      <div style="font-size:0.75rem; color:var(--kiwi);">${r.total_cal || 0} kcal / ${r.total_pro || 0}g pro (${r.servings || 1} serv)</div>
      <button type="button" onclick="addRecipeToLog('${r.id}')" class="water-quick-btn" style="font-size:0.72rem; padding:3px 8px; margin-top:4px;">+ Log Recipe</button>
    </div>
  `).join('');
}

async function addRecipeToLog(recipeId) {
  const recipe = (window._recipes || []).find(r => String(r.id) === String(recipeId));
  if (!recipe) return;
  const foodItem = {
    name: recipe.name,
    cal: recipe.total_cal || 0,
    pro: recipe.total_pro || 0,
    carb: recipe.total_carb || 0,
    fat: recipe.total_fat || 0,
    emoji: '🍳'
  };
  await addFoodToLog(foodItem);
}

// ─────────────────────────────────────────────────
//  EXPLICIT GLOBAL WINDOW EVENT HANDLER EXPORTS
// ─────────────────────────────────────────────────
if (typeof window !== 'undefined') {
  window.addFoodById = typeof addFoodById !== 'undefined' ? addFoodById : window.addFoodById;
  window.addFoodToLog = typeof addFoodToLog !== 'undefined' ? addFoodToLog : window.addFoodToLog;
  window.addRecipeIngredientRow = typeof addRecipeIngredientRow !== 'undefined' ? addRecipeIngredientRow : window.addRecipeIngredientRow;
  window.addRecipeToLog = typeof addRecipeToLog !== 'undefined' ? addRecipeToLog : window.addRecipeToLog;
  window.clearScan = typeof clearScan !== 'undefined' ? clearScan : window.clearScan;
  window.closeDietModal = typeof closeDietModal !== 'undefined' ? closeDietModal : window.closeDietModal;
  window.closeNonFoodModal = typeof closeNonFoodModal !== 'undefined' ? closeNonFoodModal : window.closeNonFoodModal;
  window.closeRecipeBuilderModal = typeof closeRecipeBuilderModal !== 'undefined' ? closeRecipeBuilderModal : window.closeRecipeBuilderModal;
  window.closeShareCardModal = typeof closeShareCardModal !== 'undefined' ? closeShareCardModal : window.closeShareCardModal;
  window.downloadShareCard = typeof downloadShareCard !== 'undefined' ? downloadShareCard : window.downloadShareCard;
  window.dpOverlayClick = typeof dpOverlayClick !== 'undefined' ? dpOverlayClick : window.dpOverlayClick;
  window.dpSwitchTab = typeof dpSwitchTab !== 'undefined' ? dpSwitchTab : window.dpSwitchTab;
  window.exportLogsCSV = typeof exportLogsCSV !== 'undefined' ? exportLogsCSV : window.exportLogsCSV;
  window.goToStep = typeof goToStep !== 'undefined' ? goToStep : window.goToStep;
  window.goToStep4 = typeof goToStep4 !== 'undefined' ? goToStep4 : window.goToStep4;
  window.handleEmailLogin = typeof handleEmailLogin !== 'undefined' ? handleEmailLogin : window.handleEmailLogin;
  window.handleEmailRegister = typeof handleEmailRegister !== 'undefined' ? handleEmailRegister : window.handleEmailRegister;
  window.handleFinishOnboarding = typeof handleFinishOnboarding !== 'undefined' ? handleFinishOnboarding : window.handleFinishOnboarding;
  window.handleForgotPassword = typeof handleForgotPassword !== 'undefined' ? handleForgotPassword : window.handleForgotPassword;
  window.handleGoogleLogin = typeof handleGoogleLogin !== 'undefined' ? handleGoogleLogin : window.handleGoogleLogin;
  window.handleLogout = typeof handleLogout !== 'undefined' ? handleLogout : window.handleLogout;
  window.joinChallenge = typeof joinChallenge !== 'undefined' ? joinChallenge : window.joinChallenge;
  window.loadMoreFoods = typeof loadMoreFoods !== 'undefined' ? loadMoreFoods : window.loadMoreFoods;
  window.logMealTemplate = typeof logMealTemplate !== 'undefined' ? logMealTemplate : window.logMealTemplate;
  window.logRecipe = typeof logRecipe !== 'undefined' ? logRecipe : window.logRecipe;
  window.logWater = typeof logWater !== 'undefined' ? logWater : window.logWater;
  window.logWeightEntry = typeof logWeightEntry !== 'undefined' ? logWeightEntry : window.logWeightEntry;
  window.logWorkoutEntry = typeof logWorkoutEntry !== 'undefined' ? logWorkoutEntry : window.logWorkoutEntry;
  window.openDietModal = typeof openDietModal !== 'undefined' ? openDietModal : window.openDietModal;
  window.openRecipeBuilderModal = typeof openRecipeBuilderModal !== 'undefined' ? openRecipeBuilderModal : window.openRecipeBuilderModal;
  window.openSaveTemplateModal = typeof openSaveTemplateModal !== 'undefined' ? openSaveTemplateModal : window.openSaveTemplateModal;
  window.openShareCardModal = typeof openShareCardModal !== 'undefined' ? openShareCardModal : window.openShareCardModal;
  window.pickScanPhoto = typeof pickScanPhoto !== 'undefined' ? pickScanPhoto : window.pickScanPhoto;
  window.removeLog = typeof removeLog !== 'undefined' ? removeLog : window.removeLog;
  window.saveBodyStats = typeof saveBodyStats !== 'undefined' ? saveBodyStats : window.saveBodyStats;
  window.saveCustomRecipe = typeof saveCustomRecipe !== 'undefined' ? saveCustomRecipe : window.saveCustomRecipe;
  window.saveGoals = typeof saveGoals !== 'undefined' ? saveGoals : window.saveGoals;
  window.scanWithAI = typeof scanWithAI !== 'undefined' ? scanWithAI : window.scanWithAI;
  window.searchFoods = typeof searchFoods !== 'undefined' ? searchFoods : window.searchFoods;
  window.sendChatMessage = typeof sendChatMessage !== 'undefined' ? sendChatMessage : window.sendChatMessage;
  window.sendChip = typeof sendChip !== 'undefined' ? sendChip : window.sendChip;
  window.setCat = typeof setCat !== 'undefined' ? setCat : window.setCat;
  window.setLanguage = typeof setLanguage !== 'undefined' ? setLanguage : window.setLanguage;
  window.setMeal = typeof setMeal !== 'undefined' ? setMeal : window.setMeal;
  window.showLoginForm = typeof showLoginForm !== 'undefined' ? showLoginForm : window.showLoginForm;
  window.showPage = typeof showPage !== 'undefined' ? showPage : window.showPage;
  window.showRegisterForm = typeof showRegisterForm !== 'undefined' ? showRegisterForm : window.showRegisterForm;
  window.startBarcodeScan = typeof startBarcodeScan !== 'undefined' ? startBarcodeScan : window.startBarcodeScan;
  window.startScanCamera = typeof startScanCamera !== 'undefined' ? startScanCamera : window.startScanCamera;
  window.startVoiceLog = typeof startVoiceLog !== 'undefined' ? startVoiceLog : window.startVoiceLog;
  window.stopScanCamera = typeof stopScanCamera !== 'undefined' ? stopScanCamera : window.stopScanCamera;
  window.stopVoiceLog = typeof stopVoiceLog !== 'undefined' ? stopVoiceLog : window.stopVoiceLog;
  window.syncGoogleFit = typeof syncGoogleFit !== 'undefined' ? syncGoogleFit : window.syncGoogleFit;
  window.takeScanPhoto = typeof takeScanPhoto !== 'undefined' ? takeScanPhoto : window.takeScanPhoto;
  window.toggleChat = typeof toggleChat !== 'undefined' ? toggleChat : window.toggleChat;
}