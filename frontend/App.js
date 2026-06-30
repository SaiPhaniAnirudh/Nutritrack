window._otpVerifiedToken = '';
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
//  PAGE LOADER  (change #10)
// ─────────────────────────────────────────────────
function showLoader(msg = 'Loading…') {
  const el = document.getElementById('pageLoader');
  const ml = document.getElementById('loaderMsg');
  if (ml) ml.textContent = msg;
  if (el) el.classList.remove('hidden');
}
function hideLoader() {
  const el = document.getElementById('pageLoader');
  if (el) el.classList.add('hidden');
}
// Hide loader as soon as DOM + scripts are ready
// Hide loader immediately when script loads
hideLoader();

// ─────────────────────────────────────────────────
//  LOCAL STORAGE DB
// ─────────────────────────────────────────────────
const DB = {
  getUsers:       ()  => JSON.parse(localStorage.getItem('nt_users')   || '[]'),
  saveUsers:      (u) => localStorage.setItem('nt_users', JSON.stringify(u)),
  getLogs:        ()  => JSON.parse(localStorage.getItem('nt_logs')    || '[]'),
  saveLogs:       (l) => localStorage.setItem('nt_logs', JSON.stringify(l)),
  getCurrentUser: ()  => JSON.parse(sessionStorage.getItem('nt_current') || 'null'),
  setCurrentUser: (u) => sessionStorage.setItem('nt_current', JSON.stringify(u)),
  clearSession:   ()  => sessionStorage.removeItem('nt_current'),
};

// ─────────────────────────────────────────────────
//  APP STATE
// ─────────────────────────────────────────────────
let currentUser     = null;
let currentMealType = 'breakfast';
let currentCat      = 'all';
let macroChart      = null;
let weekChart       = null;

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
//  AUTH — helpers
// ─────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.auth-tab').forEach((t, i) => {
    t.classList.toggle('active', (i === 0) === (tab === 'login'));
  });
  document.getElementById('loginForm').style.display    = tab === 'login'    ? 'block' : 'none';
  document.getElementById('registerForm').style.display = tab === 'register' ? 'block' : 'none';
  hideAuthError();
  if (tab === 'register') { goToStep(1); _prewarmBackend(); }
}

function showAuthError(msg) {
  const el = document.getElementById('authError');
  el.textContent = msg;
  el.style.display = 'block';
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
function hideAuthError() {
  const el = document.getElementById('authError');
  if (el) el.style.display = 'none';
}

// ─────────────────────────────────────────────────
//  MULTI-STEP REGISTRATION  (change #7)
// ─────────────────────────────────────────────────
function goToStep(n) {
  [1,2,3,4].forEach(i => {
    const el = document.getElementById('regStep' + i);
    if (el) el.style.display = i === n ? 'block' : 'none';
  });
  hideAuthError();
}

function goToStep2() {
  // Validate Step 1 fully before advancing (change #7)
  const name   = document.getElementById('regName').value.trim();
  const email  = document.getElementById('regEmail').value.trim();
  const pw     = document.getElementById('regPassword').value;
  const pwConf = document.getElementById('regPasswordConfirm').value;

  if (!name)              return showAuthError('⚠️ Please enter your full name.');
  if (name.length < 2)    return showAuthError('⚠️ Name must be at least 2 characters.');

  const emailRegex = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;
  if (!email)             return showAuthError('⚠️ Please enter your email address.');
  if (!emailRegex.test(email)) return showAuthError('⚠️ Enter a valid email (e.g. name@domain.com).');

  if (!pw)                return showAuthError('⚠️ Please enter a password.');
  if (pw.length < 8)      return showAuthError('⚠️ Password must be at least 8 characters.');
  if (getPasswordStrength(pw) < 2) return showAuthError('⚠️ Password is too weak. Mix letters, numbers, and symbols.');

  if (!pwConf)            return showAuthError('⚠️ Please confirm your password.');
  if (pw !== pwConf)      return showAuthError('⚠️ Passwords do not match. Please re-enter.');

  const users = DB.getUsers();
  if (users.find(u => u.email.toLowerCase() === email.toLowerCase())) {
    return showAuthError('⚠️ An account with this email already exists. Sign in instead.');
  }

  goToStep(2);
}

function goToStep4() {
  // Validate Step 2 fully (change #7)
  const dobStr  = document.getElementById('regDob').value;
  if (!dobStr) return showAuthError('⚠️ Please enter your date of birth.');
  const dobDate = new Date(dobStr);
  let age = new Date().getFullYear() - dobDate.getFullYear();
  if (new Date() < new Date(dobDate.setFullYear(new Date().getFullYear()))) age--;

  const weight  = parseFloat(document.getElementById('regWeight').value);
  const height  = parseFloat(document.getElementById('regHeight').value);
  const gender  = document.querySelector('input[name="gender"]:checked');
  const goal    = document.querySelector('input[name="dietGoal"]:checked');

  if (!age || age < 10 || age > 100) return showAuthError('⚠️ Please enter a valid age (10–100).');
  if (!weight || weight < 20)        return showAuthError('⚠️ Please enter a valid weight.');
  if (!height || height < 50)        return showAuthError('⚠️ Please enter a valid height.');
  if (!gender)                        return showAuthError('⚠️ Please select your gender.');
  if (!goal)                          return showAuthError('⚠️ Please select your diet goal.');

  // Auto-calculate goals from body stats
  const wUnit = document.getElementById('regWeightUnit').value;
  const hUnit = document.getElementById('regHeightUnit').value;
  const weightKg = wUnit === 'lbs' ? weight * 0.4536 : weight;
  const heightCm = hUnit === 'ft'  ? height * 30.48  : height;

  const { calories, protein } = _calcGoals(weightKg, heightCm, age, gender.value, goal.value);

  document.getElementById('goalCalories').value = calories;
  document.getElementById('goalProtein').value  = protein;

  // Show preview cards
  const bmi = (weightKg / ((heightCm/100)**2)).toFixed(1);
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
    bmr = 447.6 + 9.25*weightKg + 3.10*heightCm - 4.33*age;
  } else {
    bmr = 88.36 + 13.40*weightKg + 4.80*heightCm - 5.68*age;
  }
  const activityFactor = 1.55; // moderate activity
  let tdee = bmr * activityFactor;

  let calAdj = 0;
  if (goal === 'lose')     calAdj = -400;
  if (goal === 'gain')     calAdj = +300;
  if (goal === 'bulk')     calAdj = +500;

  const calories = Math.round(tdee + calAdj);
  // Protein: 1.8g/kg for bulk, 1.6g/kg for gain, 1.4g/kg for lose/maintain
  const protMultiplier = goal === 'bulk' ? 1.8 : goal === 'gain' ? 1.6 : 1.4;
  const protein = Math.round(weightKg * protMultiplier);

  return { calories, protein };
}

// ─────────────────────────────────────────────────
//  PASSWORD HASHING  (SHA-256 via WebCrypto — much safer than btoa)
// ─────────────────────────────────────────────────
async function hashPw(pw) {
  // Prefix with a fixed pepper so bare SHA-256 of the password can't be looked up in rainbow tables
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('nt_pepper:' + pw));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

// Detect old btoa-encoded passwords so we can auto-migrate them on login
function _isLegacyBtoa(hash) {
  return !(hash && hash.length === 64 && /^[0-9a-f]+$/.test(hash));
}

// ─────────────────────────────────────────────────
//  EMAIL / PASSWORD VALIDATORS
// ─────────────────────────────────────────────────
function validateEmailField(input) {
  const email = input.value.trim();
  const msgEl = document.getElementById('emailValidationMsg');
  if (!email) { msgEl.style.display = 'none'; return; }
  const valid = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(email);
  msgEl.style.display = 'block';
  if (valid) {
    msgEl.textContent = '✓ Email format looks correct';
    msgEl.style.color = '#7fbb6e';
    msgEl.style.background = 'rgba(127,187,110,0.08)';
    input.style.borderColor = 'rgba(127,187,110,0.4)';
  } else {
    msgEl.textContent = '✗ Please enter a valid email (e.g. name@domain.com)';
    msgEl.style.color = '#F4613A';
    msgEl.style.background = 'rgba(196,132,90,0.08)';
    input.style.borderColor = 'rgba(196,132,90,0.4)';
  }
}

function getPasswordStrength(pw) {
  let score = 0;
  if (pw.length >= 8)  score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return score;
}

function validatePasswordField(input) {
  const pw = input.value;
  const barWrap = document.getElementById('passwordStrengthBar');
  const fill    = document.getElementById('passwordStrengthFill');
  const label   = document.getElementById('passwordStrengthLabel');
  if (!pw) { barWrap.style.display = 'none'; return; }
  barWrap.style.display = 'block';
  const score = getPasswordStrength(pw);
  const colors = ['#e05c5c','#e07e5c','#d4a853','#7fbb6e','#7fbb6e','#4CAF50'];
  const labels = ['Very weak','Weak','Fair','Good','Strong','Very strong'];
  fill.style.width      = Math.min(100, score*20) + '%';
  fill.style.background = colors[score];
  label.textContent     = labels[score];
  label.style.color     = colors[score];
}

function validateConfirmPassword(input) {
  const pw1 = document.getElementById('regPassword').value;
  const msgEl = document.getElementById('confirmPasswordMsg');
  msgEl.style.display = 'block';
  if (input.value === pw1) {
    msgEl.textContent = '✓ Passwords match';
    msgEl.style.color = '#7fbb6e';
    input.style.borderColor = 'rgba(127,187,110,0.4)';
  } else {
    msgEl.textContent = '✗ Passwords do not match';
    msgEl.style.color = '#F4613A';
    input.style.borderColor = 'rgba(196,132,90,0.4)';
  }
}

// ─────────────────────────────────────────────────
//  REGISTER
// ─────────────────────────────────────────────────

// --- OTP LOGIC ---
async function sendOtpAndGoToStepOtp() {
  const email = document.getElementById('regEmail').value.trim();
  if (!email || !email.includes('@')) {
    return showAuthError('?? Please enter a valid email address first.');
  }
  
  // Basic pre-validation
  const name = document.getElementById('regName').value.trim();
  const pw = document.getElementById('regPassword').value;
  const pwConf = document.getElementById('regPasswordConfirm').value;
  if (!name || !pw || pw !== pwConf) {
    return showAuthError('?? Please complete Name and matching Passwords.');
  }

  const btn = document.querySelector('#regStep1 .submit-btn');
  const origText = btn.innerHTML;
  btn.innerHTML = 'Sending... <div class="spinner"></div>';
  btn.disabled = true;

  try {
    const backendUrl = window._BACKEND_URL !== undefined ? window._BACKEND_URL : '';
    const res = await fetch(`${backendUrl}/api/auth/send-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    
    if (!res.ok) throw new Error(data.error || 'Failed to send OTP');
    
    if (data.status && data.status.startsWith('DEMO')) {
      const fallbackOtp = data.status.split(':')[1] || '';
      if (fallbackOtp) {
        showToast(`⚠️ Render blocked the email, but your code is: ${fallbackOtp}`, 'warning');
      } else {
        showToast('⚠️ Backend is in DEMO mode! Check Render Logs for the code.', 'warning');
      }
    }
    
    document.getElementById('regStep1').style.display = 'none';
    document.getElementById('regStep2').style.display = 'block';
    document.getElementById('authError').style.display = 'none';
    
  } catch(e) {
    showAuthError('?? ' + e.message);
  } finally {
    btn.innerHTML = origText;
    btn.disabled = false;
  }
}

async function verifyOtpAndGoToStep3() {
  const email = document.getElementById('regEmail').value.trim();
  const otp = document.getElementById('regOtpCode').value.trim();
  
  if (!otp || otp.length < 5) return showAuthError('?? Please enter the 6-digit code.');

  const btn = document.querySelector('#regStep2 .submit-btn');
  const origText = btn.innerHTML;
  btn.innerHTML = 'Verifying... <div class="spinner"></div>';
  btn.disabled = true;

  try {
    const backendUrl = window._BACKEND_URL !== undefined ? window._BACKEND_URL : '';
    const res = await fetch(`${backendUrl}/api/auth/verify-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, otp })
    });
    const data = await res.json();
    
    if (!res.ok) throw new Error(data.error || 'Invalid OTP');
    
    window._otpVerifiedToken = data.verified_token;
    
    document.getElementById('regStep2').style.display = 'none';
    document.getElementById('regStep3').style.display = 'block';
    document.getElementById('authError').style.display = 'none';
    
  } catch(e) {
    showAuthError('?? ' + e.message);
  } finally {
    btn.innerHTML = origText;
    btn.disabled = false;
  }
}

function goBackToStep1() {
  document.getElementById('regStep2').style.display = 'none';
  document.getElementById('regStep1').style.display = 'block';
  document.getElementById('authError').style.display = 'none';
}
// -----------------

async function handleRegister() {
  const name    = document.getElementById('regName').value.trim();
  const email   = document.getElementById('regEmail').value.trim();
  const pw      = document.getElementById('regPassword').value;
  const pwConf  = document.getElementById('regPasswordConfirm').value;
  const goalCal  = parseInt(document.getElementById('goalCalories').value) || 2000;
  const goalProt = parseInt(document.getElementById('goalProtein').value)  || 150;

  if (!name || !email || !pw || pw !== pwConf) return showAuthError('⚠️ Please complete all steps correctly.');
  if (goalCal < 500 || goalCal > 10000) return showAuthError('⚠️ Calorie goal must be between 500 and 10,000.');

  const dob        = document.getElementById('regDob').value || null;
  const weight     = parseFloat(document.getElementById('regWeight').value) || null;
  const height     = parseFloat(document.getElementById('regHeight').value) || null;
  const weightUnit = document.getElementById('regWeightUnit').value;
  const heightUnit = document.getElementById('regHeightUnit').value;
  const genderEl   = document.querySelector('input[name="gender"]:checked');
  const goalEl     = document.querySelector('input[name="dietGoal"]:checked');
  const dietTypeEl = document.querySelector('input[name="dietType"]:checked');

  const backendUrl = window._BACKEND_URL !== undefined ? window._BACKEND_URL : '';
  const payload = {
      name, email, password: pw,
      verified_token: window._otpVerifiedToken || '',
      body_stats: {
        dob, weight, height, weightUnit, heightUnit,
        gender: genderEl ? genderEl.value : null,
        diet_goal: goalEl ? goalEl.value : 'maintain',
        diet_type: dietTypeEl ? dietTypeEl.value : 'nonveg'
      },
      goals: {
        calories: goalCal, protein: goalProt, carbs: 275, fat: 78,
        fiber: 28, sugar: 50, sodium: 2300, chol: 300,
        vit_d: 15, iron: 18, folate: 400
      }
  };

  showLoader('Creating your account...');
  try {
      const res = await fetch(`${backendUrl}/api/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
          hideLoader();
          return showAuthError('⚠️ ' + (data.error || 'Registration failed'));
      }
      window._otpVerifiedToken = null;
      await _doLogin(email, pw);
  } catch (err) {
      hideLoader();
      return showAuthError('⚠️ Network error during registration.');
  }
}

async function handleLogin() {
  const email = document.getElementById('loginEmail').value.trim();
  const pw    = document.getElementById('loginPassword').value;
  if (!email || !pw) return showAuthError('⚠️ Email and password required.');
  showLoader('Signing you in...');
  await _doLogin(email, pw);
}

async function _doLogin(email, pw) {
  const backendUrl = window._BACKEND_URL !== undefined ? window._BACKEND_URL : '';
  try {
      const res = await fetch(`${backendUrl}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password: pw })
      });
      const data = await res.json();
      if (!res.ok) {
          hideLoader();
          return showAuthError('⚠️ ' + (data.error || 'Invalid credentials'));
      }
      localStorage.setItem('nt_access_token', data.access_token);
      if (data.refresh_token) localStorage.setItem('nt_refresh_token', data.refresh_token);
      loginSuccess(data.user);
  } catch (err) {
      hideLoader();
      return showAuthError('⚠️ Network error during login.');
  }
}

function loginSuccess(user) {
  currentUser = { ...user, ...(user.body_stats || {}) };
  currentUser.token = localStorage.getItem('nt_access_token');
  document.getElementById('authSection').style.display = 'none';
  document.getElementById('mainApp').style.display = 'block';
  initApp();
  fetchLogsFromCloud();
  hideLoader();
}

function handleLogout() {
  showLoader('Signing out…');
  setTimeout(() => {
    currentUser = null;
    DB.clearSession();
    document.getElementById('mainApp').style.display   = 'none';
    document.getElementById('authSection').style.display = 'block';
    document.getElementById('loginEmail').value    = '';
    document.getElementById('loginPassword').value = '';
    hideLoader();
  }, 500);
}

// ─────────────────────────────────────────────────
//  INIT APP
// ─────────────────────────────────────────────────
function initApp() {
  const hour = new Date().getHours();
  document.getElementById('timeGreet').textContent = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening';
  document.getElementById('greetName').textContent  = currentUser.name.split(' ')[0];
  document.getElementById('greetDate').textContent  = new Date().toLocaleDateString('en-IN', {weekday:'long', year:'numeric', month:'long', day:'numeric'});
  document.getElementById('navAvatar').textContent  = currentUser.name[0].toUpperCase();
  document.getElementById('navName').textContent    = currentUser.name.split(' ')[0];

  const g = currentUser.goals || {calories:2000, protein:150, carbs:275, fat:78, fiber:28, sugar:50, sodium:2300, chol:300};
  document.getElementById('editCalGoal').value    = g.calories;
  document.getElementById('editProtGoal').value   = g.protein;
  document.getElementById('editCarbGoal').value   = g.carbs;
  document.getElementById('editFatGoal').value    = g.fat;
  document.getElementById('editFiberGoal').value  = g.fiber  || 28;
  document.getElementById('editSugarGoal').value  = g.sugar  || 50;
  document.getElementById('editSodiumGoal').value = g.sodium || 2300;
  document.getElementById('editCholGoal').value   = g.chol   || 300;
  document.getElementById('editVitDGoal').value   = g.vit_d  || 15;
  document.getElementById('editIronGoal').value   = g.iron   || 18;
  document.getElementById('editFolateGoal').value = g.folate || 400;

  buildCatFilters();
  autoSelectMeal();
  loadApiKey();
  refreshDashboard();
  searchFoods('');
  _updateDietWidget(); // change #11
  
  // Show chatbot button if it exists
  const nbBtn = document.getElementById('nutribotBtn');
  if (nbBtn) nbBtn.style.display = 'flex';
}

// ─────────────────────────────────────────────────
//  NAVIGATION  (change #10: show loader on nav)
// ─────────────────────────────────────────────────
const PAGE_NAMES = {
  dashboard: 'Dashboard',
  track:     'Track Food',
  history:   'History',
  profile:   'Profile',
};

function showPage(id, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.mob-nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');
  if (btn) btn.classList.add('active');

  // Keep mobile bottom nav in sync
  const mobBtn = document.getElementById('mobBtn-' + id);
  if (mobBtn) mobBtn.classList.add('active');

  if (id === 'dashboard') refreshDashboard();
  if (id === 'track')     { autoSelectMeal(); searchFoods(document.getElementById('foodSearch').value || ''); }
  if (id === 'history')   renderHistory();
  if (id === 'profile')   renderProfile();
}

// ─────────────────────────────────────────────────
//  HELPERS
// ─────────────────────────────────────────────────
function todayStr() { return new Date().toISOString().split('T')[0]; }

function getLast30Days() {
  return Array.from({length:30}, (_,i) => {
    const d = new Date(); d.setDate(d.getDate() - (29-i));
    return d.toISOString().split('T')[0];
  });
}

function sumLogs(logs) {
  return logs.reduce((acc, l) => ({
    cal:    acc.cal    + (l.cal    || 0),
    pro:    acc.pro    + (l.pro    || 0),
    carb:   acc.carb   + (l.carb   || 0),
    fat:    acc.fat    + (l.fat    || 0),
    fiber:  acc.fiber  + (l.fiber  || 0),
    sugar:  acc.sugar  + (l.sugar  || 0),
    sodium: acc.sodium + (l.sodium || 0),
    chol:   acc.chol   + (l.chol   || 0),
    vit_d:  acc.vit_d  + (l.vit_d  || 0),
    iron:   acc.iron   + (l.iron   || 0),
    folate: acc.folate + (l.folate || 0),
  }), {cal:0, pro:0, carb:0, fat:0, fiber:0, sugar:0, sodium:0, chol:0, vit_d:0, iron:0, folate:0});
}

// ─────────────────────────────────────────────────
//  DASHBOARD
// ─────────────────────────────────────────────────
function refreshDashboard() {
  const today  = todayStr();
  const logs   = window._foodLogs.filter(l => l.date === today);
  const totals = sumLogs(logs);
  const goals  = currentUser.goals || {calories:2000, protein:150, carbs:275, fat:78, fiber:28, sugar:50, sodium:2300, chol:300};

  [['dashCals','calBar',totals.cal,goals.calories,false],
   ['dashProtein','protBar',totals.pro,goals.protein,false],
   ['dashCarbs','carbBar',totals.carb,goals.carbs,false],
   ['dashFat','fatBar',totals.fat,goals.fat,false],
  ].forEach(([vId,bId,val,goal]) => {
    const el = document.getElementById(vId); if (el) el.textContent = Math.round(val);
    const bar = document.getElementById(bId); if (bar) bar.style.width = Math.min(100,(val/(goal||1))*100)+'%';
  });

  [['dashFiber','fiberBar',totals.fiber,goals.fiber||28,false,'fiber-card'],
   ['dashSugar','sugarBar',totals.sugar,goals.sugar||50,true,'sugar-card'],
   ['dashSodium','sodiumBar',totals.sodium,goals.sodium||2300,true,'sodium-card'],
   ['dashChol','cholBar',totals.chol,goals.chol||300,true,'chol-card'],
   ['dashVitD','vitDBar',totals.vit_d,goals.vit_d||15,false,'vitD-card'],
   ['dashIron','ironBar',totals.iron,goals.iron||18,false,'iron-card'],
   ['dashFolate','folateBar',totals.folate,goals.folate||400,false,'folate-card'],
  ].forEach(([vId,bId,val,goal,warnOnOver,cardId]) => {
    const el = document.getElementById(vId); if (el) el.textContent = Math.round(val);
    const bar = document.getElementById(bId); if (bar) bar.style.width = Math.min(100,(val/(goal||1))*100)+'%';
    const card = document.getElementById(cardId);
    if (card) card.classList.toggle('warning-high', warnOnOver && val > goal);
  });

  const logEl = document.getElementById('dashFoodLog');
  if (logs.length === 0) {
    logEl.innerHTML = `<div class="empty-log"><div class="empty-icon">🍽️</div><p>No meals logged today.<br>Head to Track Food to get started.</p></div>`;
  } else {
    logEl.innerHTML = logs.map(l => `
      <div class="log-item">
        <div class="log-item-left">
          <div class="food-emoji">${l.emoji||'🍽️'}</div>
          <div>
            <div class="log-item-name">${l.name}</div>
            <div class="log-item-meta">${l.mealType} · ${l.pro}g P · ${l.carb}g C · ${l.fat}g F</div>
            <div class="nutrient-pills">
              ${l.fiber  ? `<span class="npill fiber">🌿 ${l.fiber}g fiber</span>` : ''}
              ${l.sugar  ? `<span class="npill sugar">🍬 ${l.sugar}g sugar</span>` : ''}
              ${l.sodium ? `<span class="npill sodium">🧂 ${l.sodium}mg salt</span>` : ''}<!-- change #13 -->
              ${l.chol   ? `<span class="npill chol">❤️ ${l.chol}mg chol</span>` : ''}
              ${l.vit_d  ? `<span class="npill vit_d" style="background:rgba(245,166,35,0.1);color:#F5A623;border-color:rgba(245,166,35,0.2)">☀️ ${l.vit_d}mcg VitD</span>` : ''}
              ${l.iron   ? `<span class="npill iron" style="background:rgba(208,2,27,0.1);color:#D0021B;border-color:rgba(208,2,27,0.2)">🥩 ${l.iron}mg Iron</span>` : ''}
              ${l.folate ? `<span class="npill folate" style="background:rgba(126,211,33,0.1);color:#7ED321;border-color:rgba(126,211,33,0.2)">🥬 ${l.folate}mcg Fol</span>` : ''}
            </div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:0.5rem">
          <div class="log-item-cal">${l.cal} kcal</div>
          <button class="remove-item-btn" onclick="removeLog('${l.id}')">✕</button>
        </div>
      </div>
    `).join('');
  }
  renderMacroChart(totals.pro, totals.carb, totals.fat, totals.fiber, totals.sugar, totals.sodium, totals.chol, totals.cal);
}

function renderMacroChart(p, c, f, fiber, sugar, sodium, chol, cal) {
  const ctx2 = document.getElementById('macroChart').getContext('2d');
  if (macroChart) macroChart.destroy();

  const sodiumG = +(sodium/10).toFixed(1);
  const cholG   = +(chol/10).toFixed(1);

  const labels   = ['Protein','Carbs','Fat','Fiber','Sugar','Salt','Cholesterol']; // change #13
  const rawVals  = [p,c,f,fiber,sugar,sodiumG,cholG];
  const units    = ['g','g','g','g','g','mg (÷10)','mg (÷10)'];
  const realVals = [p,c,f,fiber,sugar,sodium,chol];

  const bgColors = [
    'rgba(127,184,212,0.85)',
    'rgba(196,168,127,0.85)',
    'rgba(244,97,58,0.85)',
    'rgba(100,180,110,0.85)',
    'rgba(212,168,83,0.85)',
    'rgba(160,120,200,0.85)',
    'rgba(220,100,100,0.85)',
  ];
  const borderColors = bgColors.map(c => c.replace('0.85','1'));

  const nonZeroIdx  = rawVals.map((v,i) => v>0?i:-1).filter(i=>i>=0);
  const filtLabels  = nonZeroIdx.map(i=>labels[i]);
  const filtRaw     = nonZeroIdx.map(i=>rawVals[i]);
  const filtReal    = nonZeroIdx.map(i=>realVals[i]);
  const filtUnits   = nonZeroIdx.map(i=>units[i]);
  const filtBg      = nonZeroIdx.map(i=>bgColors[i]);
  const filtBorder  = nonZeroIdx.map(i=>borderColors[i]);
  const total       = filtRaw.reduce((s,v)=>s+v,0)||1;

  macroChart = new Chart(ctx2, {
    type: 'doughnut',
    data: {
      labels: filtLabels,
      datasets: [{ data:filtRaw, backgroundColor:filtBg, borderColor:filtBorder, borderWidth:2, hoverOffset:8 }]
    },
    options: {
      responsive:true, maintainAspectRatio:false, cutout:'62%',
      plugins: {
        legend: {
          position:'bottom',
          labels: {
            color:'rgba(184,201,186,0.8)', font:{family:'Plus Jakarta Sans',size:11}, padding:10,
            usePointStyle:true, pointStyleWidth:10,
            generateLabels(chart) {
              return chart.data.labels.map((label,i) => ({
                text:`${label}: ${filtReal[i]}${filtUnits[i]==='g'?'g':'mg'}`,
                fillStyle:filtBg[i], strokeStyle:filtBorder[i],
                fontColor:'rgba(184,201,186,0.8)', lineWidth:1, pointStyle:'circle', hidden:false, index:i,
              }));
            }
          }
        },
        tooltip: {
          callbacks: {
            label(ctx) {
              const idx=ctx.dataIndex, real=filtReal[idx], unit=filtUnits[idx]==='g'?'g':'mg';
              const pct=Math.round((filtRaw[idx]/total)*100);
              return `  ${real}${unit}  (${pct}% of chart)`;
            },
            title(ctx){return ctx[0].label;}
          },
          backgroundColor:'rgba(255,255,255,0.96)', titleColor:'#12110F', bodyColor:'rgba(18,17,15,0.6)',
          borderColor:'rgba(18,17,15,0.1)', borderWidth:1, padding:10, cornerRadius:8,
        }
      },
      animation:{animateRotate:true, duration:600}
    },
    plugins:[{
      id:'centerLabel',
      afterDraw(chart){
        const {ctx:c2,chartArea:{width,height,left,top}}=chart;
        c2.save();
        const cx=left+width/2, cy=top+height/2;
        c2.textAlign='center'; c2.textBaseline='middle';
        c2.fillStyle='#B87200';
        c2.font=`bold 18px "Plus Jakarta Sans",sans-serif`;
        c2.fillText(Math.round(cal)+' kcal',cx,cy-8);
        c2.fillStyle='rgba(18,17,15,0.4)';
        c2.font=`11px "Plus Jakarta Sans",sans-serif`;
        c2.fillText('today',cx,cy+10);
        c2.restore();
      }
    }]
  });
}

// ─────────────────────────────────────────────────
//  AI SCAN (Multimodal LLM)
// ─────────────────────────────────────────────────
let scanStream      = null;
let scanImageB64    = null;
let _scanAbortCtrl  = null;   // tracks in-flight AI request so Clear can cancel it

// ── LLM MODE (Ollama/Qwen2-VL — no API key required) ──
function saveApiKey()       { /* LLM — no key needed */ }
function editApiKey()       { /* LLM — no key needed */ }
function _showApiKeySaved() { /* LLM — no key needed */ }
function loadApiKey()       { /* LLM — no key needed */ }
function getApiKey()        { return 'LLM_MODE'; }

function showScanStatus(msg, type='info') {
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
    try   { scanStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode:'environment', width:{ideal:1280} } }); }
    catch { scanStream = await navigator.mediaDevices.getUserMedia({ video: true }); }

    const video = document.getElementById('camVideo');
    const area  = document.getElementById('camArea');
    video.srcObject = scanStream;
    video.style.display = 'block';
    area.classList.add('has-media');
    document.getElementById('camPlaceholder').style.display = 'none';
    document.getElementById('scanPreview').style.display    = 'none';
    document.getElementById('scanActionRow').style.display  = 'none';
    document.getElementById('scanCamRow').style.display     = 'flex';
    document.getElementById('scanReadyRow').style.display   = 'none';
    // change #5: clear any in-memory image when camera starts
    scanImageB64 = null;
    hideScanStatus();
  } catch(e) {
    showScanStatus('Camera access denied — use Choose Photo instead', 'error');
  }
}

function takeScanPhoto() {
  const video = document.getElementById('camVideo');
  if (!video || !video.videoWidth) { showScanStatus('Camera not ready — wait a moment', 'error'); return; }
  const cvs = document.getElementById('scanCanvas');
  cvs.width  = video.videoWidth;
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
    document.getElementById('scanActionRow').style.display  = 'flex';
    scanImageB64 = null; // change #5: clear immediately
  }
}

function pickScanPhoto() {
  const input = document.createElement('input');
  input.type   = 'file';
  input.accept = 'image/*';
  input.style.cssText = 'position:absolute;left:-9999px';
  document.body.appendChild(input);
  input.addEventListener('change', function() {
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
    setTimeout(() => { try { document.body.removeChild(input); } catch(e){} }, 1000);
  });
  setTimeout(() => input.click(), 50);
}

function _showScanPreview(dataUrl) {
  const preview = document.getElementById('scanPreview');
  const area    = document.getElementById('camArea');
  preview.src           = dataUrl;
  preview.style.display = 'block';
  area.style.display    = 'block';
  area.style.minHeight  = '0';
  area.classList.add('has-media');
  document.getElementById('camPlaceholder').style.display = 'none';
  document.getElementById('scanActionRow').style.display  = 'none';
  document.getElementById('scanCamRow').style.display     = 'none';
  document.getElementById('scanReadyRow').style.display   = 'flex';
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
  document.getElementById('scanActionRow').style.display  = 'flex';
  document.getElementById('scanReadyRow').style.display   = 'none';
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
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ image: imageB64 }),
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
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ image: imageB64 }),
        signal,
      });
      if (!response.ok) {
        let msg = 'LLM_OFFLINE';
        try { const errData = await response.json(); if(errData.error) msg = 'SERVER_ERROR: ' + errData.error; } catch(e){}
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
        if (quality < 0.3) { w=Math.round(w*0.75); h=Math.round(h*0.75); quality=0.75; }
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
  showScanStatus('🧠 Analysing with AI… (free server, please wait up to 2 min)', 'info');
  try {
    const result = await _callLLMAPI(imageToSend, signal);
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
  } catch(e) {
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
  return `<div class="scan-nutrient-cell ${warn?'warn':''}">
    <span>${icon}</span>
    <div>
      <div class="scan-n-label">${label}${warn?' ⚠️':''}</div>
      <div><span class="scan-n-val">${val}</span><span class="scan-n-unit"> ${unit}</span></div>
    </div>
  </div>`;
}

function _renderScanResult(r) {
  const goals = (currentUser && currentUser.goals) || {calories:2000,protein:150,carbs:275,fat:78,fiber:28,sugar:50,sodium:2300,chol:300};

  const items = r.items && r.items.length > 0 ? r.items
    : [{ food_name:r.food_name, serving_size:r.serving_size, confidence:r.confidence,
         calories:r.calories, protein_g:r.protein_g, carbs_g:r.carbs_g, fat_g:r.fat_g,
         fiber_g:r.fiber_g, sugar_g:r.sugar_g, sodium_mg:r.sodium_mg, cholesterol_mg:r.cholesterol_mg }];

  const isMulti = items.length > 1;

  const parsed = items.map(item => ({
    name:  item.food_name   || 'Unknown food',
    size:  item.serving_size|| '1 serving',
    conf:  Math.min(100,Math.max(0,item.confidence||80)),
    cal:   Math.round(item.calories||0),
    pro:   +(item.protein_g||0).toFixed(1),
    carb:  +(item.carbs_g||0).toFixed(1),
    fat:   +(item.fat_g||0).toFixed(1),
    fiber: +(item.fiber_g||0).toFixed(1),
    sugar: +(item.sugar_g||0).toFixed(1),
    sod:   Math.round(item.sodium_mg||0),
    chol:  Math.round(item.cholesterol_mg||0),
    vit_d: +(item.vit_d||0).toFixed(1),
    iron:  +(item.iron||0).toFixed(1),
    folate:+(item.folate||0).toFixed(1),
  }));

  const total = parsed.reduce((acc,f) => ({
    cal:acc.cal+f.cal, pro:+(acc.pro+f.pro).toFixed(1), carb:+(acc.carb+f.carb).toFixed(1),
    fat:+(acc.fat+f.fat).toFixed(1), fiber:+(acc.fiber+f.fiber).toFixed(1),
    sugar:+(acc.sugar+f.sugar).toFixed(1), sod:acc.sod+f.sod, chol:acc.chol+f.chol,
    vit_d:+(acc.vit_d+f.vit_d).toFixed(1), iron:+(acc.iron+f.iron).toFixed(1), folate:+(acc.folate+f.folate).toFixed(1),
  }), {cal:0,pro:0,carb:0,fat:0,fiber:0,sugar:0,sod:0,chol:0,vit_d:0,iron:0,folate:0});

  const avgConf  = Math.round(parsed.reduce((a,f)=>a+f.conf,0)/parsed.length);
  const macroT   = (total.pro*4)+(total.carb*4)+(total.fat*9)||1;
  const pW       = Math.round((total.pro *4/macroT)*100);
  const cW       = Math.round((total.carb*4/macroT)*100);
  const fW       = 100-pW-cW;
  const confColor= avgConf>=85?'rgba(100,180,110,0.9)':avgConf>=65?'rgba(212,168,83,0.9)':'rgba(196,132,90,0.9)';

  const sugarWarn= total.sugar > (goals.sugar ||50);
  const sodWarn  = total.sod   > (goals.sodium||2300);
  const cholWarn = total.chol  > (goals.chol  ||300);

  const itemRows = parsed.map(f => {
    const mT  = (f.pro*4)+(f.carb*4)+(f.fat*9)||1;
    const ipW = Math.round((f.pro*4/mT)*100), icW=Math.round((f.carb*4/mT)*100), ifW=100-ipW-icW;
    const iCC = f.conf>=85?'rgba(100,180,110,0.8)':f.conf>=65?'rgba(212,168,83,0.8)':'rgba(196,132,90,0.8)';
    const foodJson = JSON.stringify({name:f.name,emoji:'🍽️',cal:f.cal,pro:f.pro,carb:f.carb,fat:f.fat,fiber:f.fiber,sugar:f.sugar,sodium:f.sod,chol:f.chol,vit_d:f.vit_d,iron:f.iron,folate:f.folate}).replace(/'/g,"&#39;");
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
        <span>💪 ${f.pro}g</span><span>🌾 ${f.carb}g</span><span>🫒 ${f.fat}g</span><span>🌿 ${f.fiber}g</span>
        <span>🍬 ${f.sugar}g</span><span>🧂 ${f.sod}mg</span><span>❤️ ${f.chol}mg</span>
      </div>
      <button class="scan-add-btn" style="padding:0.45rem;font-size:0.78rem;" onclick='addFoodToLog(${foodJson})'>
        ✓ Add ${f.name} to ${currentMealType}
      </button>
    </div>`;
  }).join('');

  const allFoodsJson   = JSON.stringify({name:parsed.map(f=>f.name).join(' + '),emoji:'🍽️',cal:total.cal,pro:total.pro,carb:total.carb,fat:total.fat,fiber:total.fiber,sugar:total.sugar,sodium:total.sod,chol:total.chol,vit_d:total.vit_d,iron:total.iron,folate:total.folate}).replace(/'/g,"&#39;");
  const singleFoodJson = JSON.stringify({name:parsed[0].name,emoji:'🍽️',cal:parsed[0].cal,pro:parsed[0].pro,carb:parsed[0].carb,fat:parsed[0].fat,fiber:parsed[0].fiber,sugar:parsed[0].sugar,sodium:parsed[0].sod,chol:parsed[0].chol,vit_d:parsed[0].vit_d,iron:parsed[0].iron,folate:parsed[0].folate}).replace(/'/g,"&#39;");

  document.getElementById('scanResult').innerHTML = `
    <div class="scan-result-card">
      ${r.description ? `<div style="font-size:0.75rem;color:rgba(184,201,186,0.55);margin-bottom:0.9rem;line-height:1.4;font-style:italic">👁 ${r.description}</div>` : ''}
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.5rem;">
        <div>
          <div class="scan-food-name">${isMulti?'🍱 Full Meal Total':parsed[0].name}</div>
          <div class="scan-portion">${isMulti?parsed.length+' items detected':parsed[0].size}</div>
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
        <span>💪 P ${pW}%</span><span>🌾 C ${cW}%</span><span>🫒 F ${fW}%</span>
      </div>
      <div class="scan-nutrient-grid">
        ${_buildNutrientCell('💪','Protein',total.pro,'g',false)}
        ${_buildNutrientCell('🌾','Carbs',total.carb,'g',false)}
        ${_buildNutrientCell('🫒','Fat',total.fat,'g',false)}
        ${_buildNutrientCell('🌿','Fiber',total.fiber,'g',false)}
        ${_buildNutrientCell('🍬','Sugar',total.sugar,'g',sugarWarn)}
        ${_buildNutrientCell('🧂','Salt',total.sod,'mg',sodWarn)}<!-- change #13 -->
        ${_buildNutrientCell('❤️','Cholesterol',total.chol,'mg',cholWarn)}
        ${_buildNutrientCell('🔥','Calories',total.cal,'kcal',false)}
        ${_buildNutrientCell('☀️','Vit D',total.vit_d,'mcg',false)}
        ${_buildNutrientCell('🥩','Iron',total.iron,'mg',false)}
        ${_buildNutrientCell('🥬','Folate',total.folate,'mcg',false)}
      </div>
      ${r.tips ? `<div style="font-size:0.72rem;color:rgba(100,180,110,0.7);background:rgba(100,180,110,0.06);border:1px solid rgba(100,180,110,0.15);border-radius:8px;padding:0.55rem 0.8rem;margin-bottom:0.9rem;line-height:1.4">💡 ${r.tips}</div>` : ''}
      ${isMulti ? `
        <button class="scan-add-btn" style="margin-bottom:1rem;" onclick='addFoodToLog(${allFoodsJson})'>✓ Add Entire Meal to ${currentMealType}</button>
        <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.07em;color:var(--ink-50);margin-bottom:0.6rem;font-weight:600;">Or add individually:</div>
        ${itemRows}
      ` : `
        <button class="scan-add-btn" onclick='addFoodToLog(${singleFoodJson})'>✓ Add to ${currentMealType}</button>
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
    <button class="cat-chip ${c.key==='all'?'active':''}" onclick="setCat('${c.key}',this)">${c.label}</button>
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
  if (h>=5  && h<11) return 'breakfast';
  if (h>=11 && h<16) return 'lunch';
  if (h>=16 && h<19) return 'snack';
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
  const hint    = document.getElementById('mealTimeHint');
  const timeStr = new Date().toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit'});
  if (hint) hint.textContent = 'Auto-selected · ' + timeStr;
}

const SEARCH_ALIASES = {
  // Indian
  'dahi':'curd','curd':'dahi','kadhai':'paneer','makhani':'butter masala',
  'fried egg':'egg (fried','boiled egg':'egg (whole','scrambled':'egg (scrambled',
  'chana':'chickpea','rajma':'kidney','moong':'lentil','masoor':'lentil',
  'chaas':'buttermilk','bhatura':'bhature','sabzi':'veg','mithai':'sweet',
  'roti':'roti','paratha':'paratha','naan':'naan','dosa':'dosa','idli':'idli',
  'biryani':'biryani','curry':'curry','dal':'dal','chai':'chai','lassi':'lassi',
  'tikka':'tikka','kebab':'kebab','samosa':'samosa','pav':'pav','chaat':'chaat',
  // International
  'noodles':'ramen','pasta':'spaghetti','pizza':'margherita',
  'sushi':'sushi','ramen':'ramen','pho':'pho bo',
  'taco':'taco','burrito':'burrito','paella':'paella',
  'souvlaki':'souvlaki','croissant':'croissant',
  'banh mi':'banh mi','banh':'banh mi','pho ga':'pho ga','bun bo':'bun bo',
  'moussaka':'moussaka','spanakopita':'spanakopita','gyoza':'gyoza',
  'feijoada':'feijoada','churros':'churros','lahmacun':'lahmacun',
  // General
  'veg':'vegetable','nonveg':'chicken','non veg':'chicken',
  'juice':'juice','shake':'smoothie','coffee':'coffee',
  'salad':'salad','soup':'soup','rice':'rice','bread':'bread',
  'chicken':'chicken','beef':'beef','fish':'fish','pork':'pork',
};

// Simple food descriptions by category (change #2)
const FOOD_DESCRIPTIONS = {
  fruit:     'Fresh & naturally sweet',
  veg:       'Wholesome vegetables',
  grain:     'Grains & starches',
  protein:   'High-protein food',
  dairy:     'Dairy product',
  legume:    'Legumes & beans',
  drink:     'Beverage',
  snack:     'Snack item',
  fastfood:  'Fast food',
  indian:    'Indian cuisine',
  japanese:  'Japanese cuisine',
  chinese:   'Chinese cuisine',
  american:  'American cuisine',
  middleeast:'Middle Eastern cuisine',
  italian:   'Italian cuisine',
  thai:      'Thai cuisine',
  korean:    'Korean cuisine',
  mexican:   'Mexican cuisine',
  african:   'African cuisine',
};

function searchFoods(query) {
  const q = query.toLowerCase().trim();
  let searchQ = q;
  for (const [alias, replacement] of Object.entries(SEARCH_ALIASES)) {
    if (q.includes(alias)) { searchQ = q.replace(alias, replacement); break; }
  }
  let results = FOODS;
  if (currentCat !== 'all') results = results.filter(f => f.cat === currentCat);
  if (q) results = results.filter(f =>
    f.name.toLowerCase().includes(q) ||
    f.name.toLowerCase().includes(searchQ) ||
    q.split(' ').every(word => word.length > 2 && f.name.toLowerCase().includes(word))
  );
  else if (currentCat === 'all') results = results.slice(0, 32);

  const countEl = document.getElementById('searchCount');
  countEl.textContent = q || currentCat !== 'all'
    ? `${results.length} result${results.length!==1?'s':''} found`
    : `Showing ${results.length} of ${FOODS.length} foods`;

  const container = document.getElementById('foodResults');
  if (results.length === 0) {
    container.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:2rem;color:var(--ink-50)">No foods found for "<strong>${q}</strong>"</div>`;
    return;
  }
  container.innerHTML = results.map(f => {
    const desc = f.desc || FOOD_DESCRIPTIONS[f.cat] || ''; // change #2
    return `
    <div class="food-result-card" onclick='addFoodToLog(${JSON.stringify(f)})'>
      <div class="emoji">${f.emoji}</div>
      <div class="name">${f.name}</div>
      ${desc ? `<div class="desc">${desc}</div>` : ''}
      <div class="cals">${f.cal} kcal</div>
      <div class="macros">P:${f.pro}g · C:${f.carb}g · F:${f.fat}g · Fiber:${f.fiber}g</div>
      <div class="macros" style="color:rgba(184,201,186,0.8); margin-top:2px;">
        ☀️ Vit D: ${f.vit_d || 0}mcg · 🥩 Iron: ${f.iron || 0}mg · 🥬 Folate: ${f.folate || 0}mcg
      </div>
      <div class="macros" style="color:rgba(184,201,186,0.5)">Sugar:${f.sugar}g · Salt:${f.sodium}mg</div><!-- change #13 -->
    </div>`;
  }).join('');
}

async function addFoodToLog(food) {
  const backendUrl = window._BACKEND_URL !== undefined ? window._BACKEND_URL : '';
  const payload = {
    date: todayStr(),
    mealType: currentMealType,
    name: food.name,
    emoji: food.emoji,
    cal: food.cal,
    pro: food.pro,
    carb: food.carb,
    fat: food.fat,
    fiber: food.fiber || 0,
    sugar: food.sugar || 0,
    sodium: food.sodium || 0,
    chol: food.chol || 0,
    vit_d: food.vit_d || 0,
    iron: food.iron || 0,
    folate: food.folate || 0
  };

  try {
    const res = await fetch(`${backendUrl}/api/logs`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentUser.token}`
      },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const savedLog = await res.json();
      window._foodLogs.push(savedLog);
      refreshDashboard();
      showToast(`✓ ${food.name} added to ${currentMealType}`, 'success');
    } else {
      showToast('Failed to add food to cloud.', 'error');
    }
  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
  }
}

async function removeLog(id) {
  const backendUrl = window._BACKEND_URL !== undefined ? window._BACKEND_URL : '';
  try {
    const res = await fetch(`${backendUrl}/api/logs/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${currentUser.token}` }
    });
    if (res.ok) {
      window._foodLogs = window._foodLogs.filter(l => l.id !== id);
      refreshDashboard();
      renderHistory();
      showToast('Item removed', 'success');
    } else {
      showToast('Failed to remove item from cloud.', 'error');
    }
  } catch (e) {
    showToast('Network error removing item.', 'error');
  }
}

// ─────────────────────────────────────────────────
//  HISTORY
// ─────────────────────────────────────────────────
function renderHistory() {
  const logs    = window._foodLogs;
  const last30  = getLast30Days();
  const monthData = last30.map(d => sumLogs(logs.filter(l => l.date===d)).cal);

  const wCtx = document.getElementById('weekChart').getContext('2d');
  if (weekChart) weekChart.destroy();
  weekChart = new Chart(wCtx, {
    type:'bar',
    data:{
      labels: last30.map(d => {
        const [,m,day] = d.split('-');
        // Show label only every 5 days to avoid crowding
        const idx = last30.indexOf(d);
        return (idx % 5 === 0 || idx === last30.length - 1) ? `${day}/${m}` : '';
      }),
      datasets:[{ label:'Calories', data:monthData, backgroundColor:'rgba(45,158,107,0.2)', borderColor:'rgba(45,158,107,1)', borderWidth:1.5, borderRadius:6 }]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{display:false}, tooltip:{callbacks:{
        label: c => ` ${Math.round(c.parsed.y)} kcal`,
        title: c => { const d = last30[c[0].dataIndex]; const [,m,day]=d.split('-'); return `${day}/${m}`; }
      }}},
      scales:{
        x:{ grid:{color:'rgba(18,17,15,0.06)'}, ticks:{color:'rgba(18,17,15,0.5)',font:{family:'Plus Jakarta Sans',size:10}} },
        y:{ grid:{color:'rgba(18,17,15,0.06)'}, ticks:{color:'rgba(18,17,15,0.5)',font:{family:'Plus Jakarta Sans',size:10}} }
      }
    }
  });

  const recent = [...logs].reverse().slice(0,60);
  document.getElementById('historyBody').innerHTML = recent.map(l => `
    <tr>
      <td>${l.emoji||'🍽️'} ${l.name}</td>
      <td><span class="badge ${l.mealType}">${l.mealType}</span></td>
      <td>${l.cal} kcal</td>
      <td style="font-size:0.78rem;color:var(--ink-50)">${l.fiber||0}g fiber · ${l.sodium||0}mg salt</td>
      <td>${l.date}</td>
    </tr>
  `).join('') || '<tr><td colspan="5" style="text-align:center;color:#B8C9BA;padding:2rem">No history yet.</td></tr>';

  const monthLogs   = logs.filter(l => last30.includes(l.date));
  const monthTotals = sumLogs(monthLogs);
  const days = [...new Set(monthLogs.map(l=>l.date))].length || 1;

  document.getElementById('weeklyStats').innerHTML = `
    <div style="display:grid;gap:0.8rem;margin-top:0.5rem">
      ${[
        ['🔥','Total Calories',        Math.round(monthTotals.cal)+' kcal'],
        ['💪','Avg Protein/day',       Math.round(monthTotals.pro/days)+'g'],
        ['🌾','Avg Carbs/day',         Math.round(monthTotals.carb/days)+'g'],
        ['🫒','Avg Fat/day',           Math.round(monthTotals.fat/days)+'g'],
        ['🌿','Avg Fiber/day',         Math.round(monthTotals.fiber/days)+'g'],
        ['🍬','Avg Sugar/day',         Math.round(monthTotals.sugar/days)+'g'],
        ['🧂','Avg Salt/day',          Math.round(monthTotals.sodium/days)+'mg'],
        ['❤️','Avg Cholesterol/day',   Math.round(monthTotals.chol/days)+'mg'],
        ['🍽️','Total Meals',           monthLogs.length],
        ['📅','Days Logged',           days]
      ].map(([i,l,v]) => `
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
  document.getElementById('profileName').textContent   = currentUser.name;
  document.getElementById('profileEmail').textContent  = currentUser.email;

  // Body stats chips
  const bsc = document.getElementById('profileBodyStats');
  if (bsc) {
    const chips = [];
    if (currentUser.age)    chips.push(`🎂 Age: ${currentUser.age}`);
    if (currentUser.weight) chips.push(`⚖️ ${currentUser.weight}${currentUser.weightUnit||'kg'}`);
    if (currentUser.height) chips.push(`📏 ${currentUser.height}${currentUser.heightUnit||'cm'}`);
    if (currentUser.gender) chips.push(`${currentUser.gender==='female'?'👩':'👨'} ${currentUser.gender.charAt(0).toUpperCase()+currentUser.gender.slice(1)}`);
    if (currentUser.dietGoal) {
      const goalLabels = {lose:'🔥 Lose Weight',maintain:'⚖️ Maintain',gain:'💪 Gain Weight',bulk:'🏋️ Bulk Up'};
      chips.push(goalLabels[currentUser.dietGoal] || currentUser.dietGoal);
    }
    if (currentUser.dietType) {
      const dtLabels = {nonveg:'🍖 Non-Veg', veg:'🌱 Pure Veg', eggetarian:'🥚 Eggetarian', vegan:'🌿 Vegan'};
      chips.push(dtLabels[currentUser.dietType] || currentUser.dietType);
    }
    bsc.innerHTML = chips.length ? chips.map(c=>`<span class="bsc">${c}</span>`).join('') : '';
  }
  // Restore diet type dropdown
  const dtSel = document.getElementById('editDietType');
  if (dtSel) dtSel.value = currentUser.dietType || 'nonveg';

  const logs   = window._foodLogs;
  const days   = [...new Set(logs.map(l=>l.date))];
  const totals = sumLogs(logs);
  const avgCal = days.length ? Math.round(totals.cal/days.length) : 0;

  document.getElementById('totalMeals').textContent = logs.length;
  document.getElementById('totalDays').textContent  = days.length;
  document.getElementById('avgCals').textContent    = avgCal;

  let streak = 0;
  for (let i=0; i<30; i++) {
    const d = new Date(); d.setDate(d.getDate()-i);
    const ds = d.toISOString().split('T')[0];
    if (logs.some(l=>l.date===ds)) streak++; else break;
  }
  document.getElementById('streakDays').textContent = streak;
}

function saveGoals() {
  const newGoals = {
    calories: parseInt(document.getElementById('editCalGoal').value)    || 2000,
    protein:  parseInt(document.getElementById('editProtGoal').value)   || 150,
    carbs:    parseInt(document.getElementById('editCarbGoal').value)   || 275,
    fat:      parseInt(document.getElementById('editFatGoal').value)    || 78,
    fiber:    parseInt(document.getElementById('editFiberGoal').value)  || 28,
    sugar:    parseInt(document.getElementById('editSugarGoal').value)  || 50,
    sodium:   parseInt(document.getElementById('editSodiumGoal').value) || 2300,
    chol:     parseInt(document.getElementById('editCholGoal').value)   || 300,
    vit_d:    parseInt(document.getElementById('editVitDGoal').value)   || 15,
    iron:     parseInt(document.getElementById('editIronGoal').value)   || 18,
    folate:   parseInt(document.getElementById('editFolateGoal').value) || 400,
  };
  currentUser.goals = newGoals;
  // Save diet type change
  const dtSel = document.getElementById('editDietType');
  if (dtSel) currentUser.dietType = dtSel.value;
  try {
    const backendUrl = window._BACKEND_URL !== undefined ? window._BACKEND_URL : '';
    fetch(`${backendUrl}/api/auth/update`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentUser.token}`
      },
      body: JSON.stringify({
        goals: newGoals,
        body_stats: {
          diet_type: dtSel ? dtSel.value : currentUser.dietType
        }
      })
    });
  } catch(e) { console.error('Failed to update cloud profile'); }
  refreshDashboard();
  renderProfile();
  showToast('✓ Goals & diet type saved!', 'success');
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
  const map = { lose:'Fat Loss', maintain:'Maintenance', gain:'Lean Gain', bulk:'Bulk & Build' };
  const vegBadge = currentUser.dietType === 'veg'        ? ' 🌱'
                 : currentUser.dietType === 'vegan'      ? ' 🌿'
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

function _dpRing(pct, color, size=80, stroke=8) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const dash = Math.min(1, pct / 100) * circ;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="${stroke}"/>
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="${stroke}"
      stroke-linecap="round" stroke-dasharray="${dash} ${circ}"
      transform="rotate(-90 ${size/2} ${size/2})" style="transition:stroke-dasharray 1s ease"/>
  </svg>`;
}

function openDietModal() {
  if (!currentUser) return;

  const u  = currentUser;
  const g  = u.goals || { calories:2000, protein:150, carbs:275, fat:78, fiber:28, sugar:50, sodium:2300, chol:300 };

  // ── Diet type flags ──
  const dietType = u.dietType || 'nonveg';
  const isVeg    = ['veg','eggetarian','vegan'].includes(dietType);
  const isVegan  = dietType === 'vegan';
  const isEgg    = dietType === 'eggetarian';
  const dtLabels = { nonveg:'🍖 Non-Veg', veg:'🌱 Pure Veg', eggetarian:'🥚 Eggetarian', vegan:'🌿 Vegan' };

  let wKg = null, hCm = null, bmi = null, bmiLabel = '', bmiColor = '#7fbb6e';
  if (u.weight && u.height) {
    wKg = u.weightUnit === 'lbs' ? u.weight * 0.4536 : u.weight;
    hCm = u.heightUnit === 'ft'  ? u.height * 30.48  : u.height;
    bmi = +(wKg / ((hCm / 100) ** 2)).toFixed(1);
    if      (bmi < 18.5) { bmiLabel = 'Underweight'; bmiColor = '#7fb8d4'; }
    else if (bmi < 25)   { bmiLabel = 'Normal';       bmiColor = '#7fbb6e'; }
    else if (bmi < 30)   { bmiLabel = 'Overweight';   bmiColor = '#d4a853'; }
    else                  { bmiLabel = 'Obese';         bmiColor = '#e05c5c'; }
  }

  const PLANS = {
    lose: {
      name:'Fat Loss', icon:'🔥', accentColor:'#e07b7b',
      tagline:'Burn fat, preserve muscle, feel energised',
      summary: `Your goal is to lose weight by eating at a calorie deficit of ~${g.calories} kcal/day. High protein intake (${g.protein}g) protects muscle while you shed fat. Consistency beats perfection.`,
      tip:'Even a 300–500 kcal daily deficit leads to ~0.5kg fat loss per week. Don\'t go too aggressive — you\'ll lose muscle.',
      meals: [
        { time:'7:00 AM',  name:'Breakfast',   emoji:'🌅', bg:'rgba(212,162,64,0.12)',  line:'rgba(212,162,64,0.3)',  foods:['Boiled eggs × 3','Greek yoghurt','Mixed berries','Black coffee'],             kcal: Math.round(g.calories*0.25) },
        { time:'12:30 PM', name:'Lunch',        emoji:'☀️', bg:'rgba(107,174,122,0.12)', line:'rgba(107,174,122,0.3)', foods:['Grilled chicken','Brown rice','Cucumber salad','Lemon water'],               kcal: Math.round(g.calories*0.35) },
        { time:'4:00 PM',  name:'Snack',        emoji:'🍎', bg:'rgba(127,184,212,0.1)',  line:'rgba(127,184,212,0.25)',foods:['Handful almonds','Apple','Green tea'],                                        kcal: Math.round(g.calories*0.10) },
        { time:'7:30 PM',  name:'Dinner',       emoji:'🌙', bg:'rgba(167,139,250,0.1)',  line:'rgba(167,139,250,0.25)',foods:['Baked fish / tofu','Steamed veggies','Small salad','Herbal tea'],             kcal: Math.round(g.calories*0.30) },
      ],
      avoid:['Sugary drinks & juices','Deep-fried foods','White bread & pasta','Alcohol','Late-night snacks'],
      habits:[
        { icon:'💧', title:'Drink 2.5L water/day',    desc:'Water suppresses appetite, boosts metabolism, and helps flush fat metabolites.',                              badge:'Daily',      badgeType:'green' },
        { icon:'🚶', title:'8,000+ steps daily',       desc:'Low-intensity walking burns fat without spiking hunger hormones like intense cardio.',                        badge:'Daily',      badgeType:'green' },
        { icon:'💪', title:'3× strength training/week',desc:'Preserves muscle during deficit. More muscle = higher resting metabolic rate.',                              badge:'3×/week',    badgeType:'amber' },
        { icon:'😴', title:'Sleep 7–9 hours',          desc:'Poor sleep increases cortisol and ghrelin (hunger hormone), making fat loss harder.',                        badge:'Essential',  badgeType:'amber' },
        { icon:'📱', title:'Track every meal',         desc:'Research shows food journalling doubles weight loss results. Log honestly.',                                  badge:'Every day',  badgeType:'green' },
        { icon:'🚫', title:'No alcohol this month',    desc:'Alcohol halts fat oxidation for hours and adds empty calories.',                                              badge:'Limit',      badgeType:'red'   },
      ]
    },
    maintain: {
      name:'Maintenance', icon:'⚖️', accentColor:'#7fbb6e',
      tagline:'Stay balanced, feel great, build healthy habits',
      summary:`Your goal is to maintain current weight by eating ~${g.calories} kcal/day. Focus on food quality, macro balance, and building sustainable habits you can keep long-term.`,
      tip:'Maintenance is actually the hardest goal — most people drift up over time. Tracking a few days per week keeps you anchored.',
      meals: [
        { time:'7:30 AM',  name:'Breakfast',   emoji:'🌅', bg:'rgba(212,162,64,0.12)',  line:'rgba(212,162,64,0.3)',  foods:['Oats with banana','Boiled eggs × 2','Glass of milk','Tea/coffee'],             kcal: Math.round(g.calories*0.25) },
        { time:'1:00 PM',  name:'Lunch',        emoji:'☀️', bg:'rgba(107,174,122,0.12)', line:'rgba(107,174,122,0.3)', foods:['Dal + rice / roti','Sabzi (veg curry)','Curd / raita','Salad'],               kcal: Math.round(g.calories*0.35) },
        { time:'4:30 PM',  name:'Snack',        emoji:'🍎', bg:'rgba(127,184,212,0.1)',  line:'rgba(127,184,212,0.25)',foods:['Fruit bowl','Handful nuts','Herbal tea'],                                      kcal: Math.round(g.calories*0.10) },
        { time:'8:00 PM',  name:'Dinner',       emoji:'🌙', bg:'rgba(167,139,250,0.1)',  line:'rgba(167,139,250,0.25)',foods:['Grilled chicken/paneer','Chapati × 2','Cooked veggies','Warm milk'],           kcal: Math.round(g.calories*0.30) },
      ],
      avoid:['Excessive junk food','Skipping meals','Crash diets','Binge eating weekends'],
      habits:[
        { icon:'💧', title:'Drink 2L water/day',       desc:'Adequate hydration supports all metabolic processes and prevents false hunger.',                              badge:'Daily',        badgeType:'green' },
        { icon:'💪', title:'Strength train 3×/week',   desc:'Building lean muscle slightly increases TDEE, giving you more calorie headroom.',                            badge:'3×/week',      badgeType:'amber' },
        { icon:'🧘', title:'Manage stress',            desc:'Chronic stress elevates cortisol which promotes fat storage, especially visceral fat.',                      badge:'Daily',        badgeType:'green' },
        { icon:'😴', title:'Sleep 7–8 hours',          desc:'Sleep regulates appetite hormones leptin and ghrelin — critical for weight maintenance.',                    badge:'Nightly',      badgeType:'amber' },
        { icon:'🍽️', title:'Eat at regular times',    desc:'Consistent meal timing stabilises blood sugar and prevents overeating later in the day.',                    badge:'Recommended',  badgeType:'green' },
      ]
    },
    gain: {
      name:'Lean Gain', icon:'💪', accentColor:'#7fb8d4',
      tagline:'Build muscle cleanly without excessive fat',
      summary:`Your goal is lean muscle gain by eating ~${g.calories} kcal/day (small surplus). High protein (${g.protein}g/day) is non-negotiable. Lift heavy, recover well, and be patient.`,
      tip:"Aim for 0.25–0.5kg gain per month. Faster than that and you're mostly gaining fat.",
      meals: [
        { time:'7:00 AM',  name:'Breakfast',    emoji:'🌅', bg:'rgba(212,162,64,0.12)',  line:'rgba(212,162,64,0.3)',  foods:['Eggs × 4 scrambled','Oats with honey','Banana','Full-fat milk'],               kcal: Math.round(g.calories*0.28) },
        { time:'1:00 PM',  name:'Lunch',         emoji:'☀️', bg:'rgba(107,174,122,0.12)', line:'rgba(107,174,122,0.3)', foods:['Chicken breast 200g','Brown rice 150g','Stir-fried veggies','Curd'],          kcal: Math.round(g.calories*0.32) },
        { time:'4:00 PM',  name:'Pre-Workout',   emoji:'⚡', bg:'rgba(127,184,212,0.1)',  line:'rgba(127,184,212,0.25)',foods:['Banana + protein shake','Peanut butter toast','Dates × 3'],                   kcal: Math.round(g.calories*0.15) },
        { time:'8:00 PM',  name:'Dinner',        emoji:'🌙', bg:'rgba(167,139,250,0.1)',  line:'rgba(167,139,250,0.25)',foods:['Paneer / fish 150g','Rice or chapati','Mixed dal','Casein / milk before bed'], kcal: Math.round(g.calories*0.25) },
      ],
      avoid:['Skipping meals','Low protein days','Cardio overload','Undereating carbs on training days'],
      habits:[
        { icon:'🏋️', title:'Progressive overload',      desc:'Add weight or reps every week. Muscles only grow when challenged beyond their current capacity.',           badge:'Every session', badgeType:'green' },
        { icon:'🥩', title:`Hit ${g.protein}g protein`, desc:'Protein is the limiting factor for muscle growth. No training compensates for low protein intake.',         badge:'Non-negotiable',badgeType:'green' },
        { icon:'😴', title:'Sleep 8–9 hours',           desc:'80% of muscle protein synthesis happens during sleep. This is when you actually grow.',                    badge:'Critical',      badgeType:'amber' },
        { icon:'💧', title:'Drink 3L water/day',        desc:'Muscle is 75% water. Dehydration of even 2% significantly reduces training performance.',                  badge:'Daily',         badgeType:'green' },
        { icon:'📅', title:'Eat every 3–4 hours',       desc:'Frequent protein doses maximise muscle protein synthesis throughout the day.',                              badge:'Recommended',   badgeType:'amber' },
      ]
    },
    bulk: {
      name:'Bulk & Build', icon:'🏋️', accentColor:'#f0a04b',
      tagline:'Aggressive surplus to maximise muscle mass',
      summary:`Your goal is aggressive muscle building at ~${g.calories} kcal/day (large surplus). Aim for ${g.protein}g protein daily. Without heavy training stimulus, the surplus becomes fat.`,
      tip:'Dirty bulking leads to excess fat. Prioritise whole foods — just eat more of them.',
      meals: [
        { time:'7:00 AM',  name:'Breakfast',    emoji:'🌅', bg:'rgba(212,162,64,0.12)',  line:'rgba(212,162,64,0.3)',  foods:['Eggs × 5','Oats 100g + milk','Banana × 2','Peanut butter toast'],              kcal: Math.round(g.calories*0.30) },
        { time:'10:30 AM', name:'Mid-Morning',  emoji:'🥛', bg:'rgba(107,174,122,0.1)',  line:'rgba(107,174,122,0.2)', foods:['Mass gainer / whole milk','Mixed nuts','Seasonal fruit'],                     kcal: Math.round(g.calories*0.15) },
        { time:'1:30 PM',  name:'Lunch',        emoji:'☀️', bg:'rgba(107,174,122,0.12)', line:'rgba(107,174,122,0.3)', foods:['Chicken / paneer 250g','Rice 200g cooked','Dal + sabzi','Curd 150g'],         kcal: Math.round(g.calories*0.30) },
        { time:'8:00 PM',  name:'Dinner',       emoji:'🌙', bg:'rgba(167,139,250,0.1)',  line:'rgba(167,139,250,0.25)',foods:['Meat / legumes 200g','Rice or chapati × 3','Cooked greens','Milk + honey'],   kcal: Math.round(g.calories*0.25) },
      ],
      avoid:['Skipping any meal','Low-calorie foods as mains','Long cardio sessions','Chronic undersleeping'],
      habits:[
        { icon:'🏋️', title:'Train 4–5 days/week',       desc:'Volume and frequency are key for hypertrophy. Hit all major muscle groups 2× per week.',                  badge:'4–5×/week',     badgeType:'green' },
        { icon:'🥩', title:`${g.protein}g protein daily`,desc:'At this training volume, your muscles can absorb and utilise very high protein amounts.',                  badge:'Every day',     badgeType:'green' },
        { icon:'🍚', title:'Load up on carbs',           desc:'Carbs fuel intense training and spare protein for muscle building — not energy.',                          badge:'Pre+post workout',badgeType:'amber'},
        { icon:'😴', title:'Sleep 8–9 hours minimum',   desc:'Growth hormone peaks during deep sleep. Missing sleep during a bulk is actively counterproductive.',        badge:'Non-negotiable', badgeType:'amber' },
        { icon:'📊', title:'Track weekly weight',        desc:'Aim for 0.5–1kg gain per month. Gaining faster? Reduce calories slightly to keep it lean.',               badge:'Weekly check',   badgeType:'green' },
        { icon:'🫀', title:'Light cardio 2×/week',       desc:'Keeps cardiovascular health strong and improves workout recovery without burning surplus.',                 badge:'2×/week',        badgeType:'amber' },
      ]
    }
  };

  const plan = PLANS[u.dietGoal] || PLANS.maintain;

  // ── Veg meal override ──
  if (isVeg) {
    const VEG_MEALS = {
      lose: [
        { time:'7:00 AM',  name:'Breakfast',  emoji:'🌅', bg:'rgba(212,162,64,0.12)',  line:'rgba(212,162,64,0.3)',
          foods: isVegan ? ['Moong sprout bowl','Chia pudding (almond milk)','Mixed berries','Black coffee']
               : isEgg  ? ['Boiled eggs × 2','Moong sprouts','Greek yoghurt','Green tea']
                        : ['Moong sprout salad','Greek yoghurt','Mixed berries','Green tea'],
          kcal: Math.round(g.calories*0.25) },
        { time:'12:30 PM', name:'Lunch',      emoji:'☀️', bg:'rgba(107,174,122,0.12)', line:'rgba(107,174,122,0.3)',
          foods: isVegan ? ['Tofu stir-fry 150g','Brown rice','Steamed veggies','Lemon water']
                        : ['Paneer tikka 120g','Brown rice','Cucumber salad','Buttermilk'],
          kcal: Math.round(g.calories*0.35) },
        { time:'4:00 PM',  name:'Snack',      emoji:'🍎', bg:'rgba(127,184,212,0.1)',  line:'rgba(127,184,212,0.25)',
          foods:['Handful almonds','Apple','Green tea'], kcal: Math.round(g.calories*0.10) },
        { time:'7:30 PM',  name:'Dinner',     emoji:'🌙', bg:'rgba(167,139,250,0.1)',  line:'rgba(167,139,250,0.25)',
          foods: isVegan ? ['Tofu + mixed dal','Steamed veggies','Salad','Herbal tea']
                        : ['Dal tadka + 1 chapati','Steamed veggies','Small salad','Warm milk'],
          kcal: Math.round(g.calories*0.30) },
      ],
      maintain: [
        { time:'7:30 AM',  name:'Breakfast',  emoji:'🌅', bg:'rgba(212,162,64,0.12)',  line:'rgba(212,162,64,0.3)',
          foods: isVegan ? ['Oats + almond milk + banana','Chia seeds','Mixed nuts','Black coffee']
               : isEgg  ? ['Oats with banana','Boiled eggs × 2','Glass of milk','Tea/coffee']
                        : ['Oats with banana + milk','Greek yoghurt','Handful almonds','Tea/coffee'],
          kcal: Math.round(g.calories*0.25) },
        { time:'1:00 PM',  name:'Lunch',      emoji:'☀️', bg:'rgba(107,174,122,0.12)', line:'rgba(107,174,122,0.3)',
          foods: isVegan ? ['Rajma / chana curry','Brown rice / roti','Mixed sabzi','Salad']
                        : ['Dal + rice / roti','Sabzi (veg curry)','Curd / raita','Salad'],
          kcal: Math.round(g.calories*0.35) },
        { time:'4:30 PM',  name:'Snack',      emoji:'🍎', bg:'rgba(127,184,212,0.1)',  line:'rgba(127,184,212,0.25)',
          foods:['Fruit bowl','Handful nuts','Herbal tea'], kcal: Math.round(g.calories*0.10) },
        { time:'8:00 PM',  name:'Dinner',     emoji:'🌙', bg:'rgba(167,139,250,0.1)',  line:'rgba(167,139,250,0.25)',
          foods: isVegan ? ['Tofu bhurji','Chapati × 2','Cooked veggies','Herbal tea']
                        : ['Paneer bhurji','Chapati × 2','Cooked veggies','Warm milk'],
          kcal: Math.round(g.calories*0.30) },
      ],
      gain: [
        { time:'7:00 AM',  name:'Breakfast',  emoji:'🌅', bg:'rgba(212,162,64,0.12)',  line:'rgba(212,162,64,0.3)',
          foods: isVegan ? ['Tofu scramble 200g','Oats + almond milk + honey','Banana','Peanut butter']
               : isEgg  ? ['Eggs × 4 scrambled','Oats with honey','Banana','Full-fat milk']
                        : ['Paneer bhurji 150g','Oats with honey','Banana','Full-fat milk'],
          kcal: Math.round(g.calories*0.28) },
        { time:'1:00 PM',  name:'Lunch',      emoji:'☀️', bg:'rgba(107,174,122,0.12)', line:'rgba(107,174,122,0.3)',
          foods: isVegan ? ['Soya chunks 200g','Brown rice 150g','Stir-fried veggies','Hummus']
                        : ['Paneer / soya chunks 150g','Brown rice 150g','Stir-fried veggies','Curd'],
          kcal: Math.round(g.calories*0.32) },
        { time:'4:00 PM',  name:'Pre-Workout',emoji:'⚡', bg:'rgba(127,184,212,0.1)',  line:'rgba(127,184,212,0.25)',
          foods:['Banana + protein shake','Peanut butter toast','Dates × 3'], kcal: Math.round(g.calories*0.15) },
        { time:'8:00 PM',  name:'Dinner',     emoji:'🌙', bg:'rgba(167,139,250,0.1)',  line:'rgba(167,139,250,0.25)',
          foods: isVegan ? ['Tofu 150g + Rajma','Rice or chapati','Mixed dal','Plant-based protein shake']
                        : ['Paneer 150g','Rice or chapati','Mixed dal','Milk + casein before bed'],
          kcal: Math.round(g.calories*0.25) },
      ],
      bulk: [
        { time:'7:00 AM',  name:'Breakfast',  emoji:'🌅', bg:'rgba(212,162,64,0.12)',  line:'rgba(212,162,64,0.3)',
          foods: isVegan ? ['Tofu scramble 250g','Oats 100g + almond milk','Banana × 2','Peanut butter toast × 2']
               : isEgg  ? ['Eggs × 5','Oats 100g + milk','Banana × 2','Peanut butter toast']
                        : ['Paneer bhurji 200g','Oats 100g + milk','Banana × 2','Peanut butter toast'],
          kcal: Math.round(g.calories*0.30) },
        { time:'10:30 AM', name:'Mid-Morning',emoji:'🥛', bg:'rgba(107,174,122,0.1)',  line:'rgba(107,174,122,0.2)',
          foods: isVegan ? ['Peanut butter shake (almond milk)','Mixed nuts 50g','Dates × 5']
                        : ['Full-fat milk 400ml','Mixed nuts 50g','Seasonal fruit'],
          kcal: Math.round(g.calories*0.15) },
        { time:'1:30 PM',  name:'Lunch',      emoji:'☀️', bg:'rgba(107,174,122,0.12)', line:'rgba(107,174,122,0.3)',
          foods: isVegan ? ['Soya chunks 250g','Rice 200g','Rajma + sabzi','Hummus']
                        : ['Paneer / Rajma 250g','Rice 200g cooked','Dal + sabzi','Curd 150g'],
          kcal: Math.round(g.calories*0.30) },
        { time:'8:00 PM',  name:'Dinner',     emoji:'🌙', bg:'rgba(167,139,250,0.1)',  line:'rgba(167,139,250,0.25)',
          foods: isVegan ? ['Tofu / Chickpeas 200g','Chapati × 3','Cooked greens','Almond milk + honey']
                        : ['Paneer / legumes 200g','Rice or chapati × 3','Cooked greens','Milk + honey'],
          kcal: Math.round(g.calories*0.25) },
      ],
    };
    plan.meals = VEG_MEALS[u.dietGoal] || VEG_MEALS.maintain;
    // Veg-specific avoid additions
    if (isVegan) plan.avoid = ['All dairy & eggs','Processed vegan junk food','White bread & maida','Refined sugar','Artificial flavours'];
    // Add B12 habit for veg/vegan
    const b12Habit = { icon:'💊', title:'Supplement B12 daily', desc:'Vitamin B12 is found almost exclusively in animal products. All vegans and many vegetarians need a daily B12 supplement.', badge:'Daily', badgeType:'red' };
    if (!plan.habits.find(h=>h.title.includes('B12'))) plan.habits.unshift(b12Habit);
  }

  const proKcal  = g.protein * 4;
  const carbKcal = (g.carbs||275) * 4;
  const fatKcal  = (g.fat||78) * 9;
  const totalMK  = proKcal + carbKcal + fatKcal || 1;
  const proPct   = Math.round(proKcal/totalMK*100);
  const carbPct  = Math.round(carbKcal/totalMK*100);
  const fatPct   = 100 - proPct - carbPct;

  // header subtitle with diet type badge
  const sub = document.getElementById('dpSubtitle');
  if (sub) sub.textContent = `${u.name.split(' ')[0]} · ${plan.name} · ${dtLabels[dietType]||''}`;

  // HERO
  document.getElementById('dpHero').innerHTML = [
    { icon:'🔥', val:g.calories, unit:' kcal', label:'Daily Target',   accent:'#F5A623'  },
    { icon:'💪', val:g.protein+'g', unit:'', label:'Protein/Day',      accent:'#7fb8d4'      },
    { icon:'🌾', val:(g.carbs||275)+'g', unit:'', label:'Carbs/Day',   accent:'#c4a87f'      },
    { icon:'🫒', val:(g.fat||78)+'g',    unit:'', label:'Fat/Day',     accent:'#F4613A'  },
  ].map(s=>`<div class="dp-stat" style="--dp-accent:${s.accent}">
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
          ${_dpRing(Math.min(100,Math.max(0,(bmi-15)/25*100)), bmiColor, 80, 8)}
          <div class="dp-bmi-center"><span class="dp-bmi-val">${bmi}</span><span class="dp-bmi-tiny">BMI</span></div>
        </div>
        <div class="dp-bmi-info">
          <div class="dp-bmi-label" style="color:${bmiColor}">${bmiLabel}</div>
          <div class="dp-bmi-desc">
            ${wKg?`<strong style="color:var(--ink)">${Math.round(wKg)}kg</strong>`:''}
            ${hCm?` · <strong style="color:var(--ink)">${Math.round(hCm)}cm</strong>`:''}
            ${u.age?` · Age <strong style="color:var(--ink)">${u.age}</strong>`:''}
            <br><span style="color:var(--ink-50);font-size:0.75rem">${
              bmi<18.5?'Consider increasing calories to reach a healthy weight range.':
              bmi<25  ?'You\'re in a healthy range. Focus on body composition.':
              bmi<30  ?'A moderate calorie deficit with exercise will help.':
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
          ? [['Tofu','8g/100g'],['Soya Chunks','52g/100g'],['Tempeh','19g/100g'],['Lentils (Dal)','9g/100g'],['Chickpeas','19g/100g'],['Edamame','11g/100g'],['Quinoa','4g/100g'],['Peanut Butter','25g/100g'],['Chia Seeds','17g/100g']]
          : isEgg
          ? [['Eggs','13g/100g'],['Greek Yoghurt','10g/100g'],['Paneer','18g/100g'],['Soya Chunks','52g/100g'],['Lentils (Dal)','9g/100g'],['Chickpeas','19g/100g'],['Cottage Cheese','11g/100g'],['Tofu','8g/100g'],['Almonds','21g/100g']]
          : [['Paneer','18g/100g'],['Soya Chunks','52g/100g'],['Greek Yoghurt','10g/100g'],['Lentils (Dal)','9g/100g'],['Chickpeas','19g/100g'],['Tofu','8g/100g'],['Rajma','24g/100g'],['Moong Dal','24g/100g'],['Almonds','21g/100g']]
        ).map(([name,pro])=>`<div class="veg-protein-item"><span class="veg-protein-name">${name}</span><span class="veg-protein-val">${pro} protein</span></div>`).join('')}
      </div>
    </div>` : ''}
  `;


  // MEALS TAB
  document.getElementById('dpTab-meals').innerHTML = `
    <div class="dp-card">
      <div class="dp-card-title">🍽️ Sample Day — ${plan.name}</div>
      <div class="dp-timeline">
        ${plan.meals.map(m=>`
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
              <div class="dp-meal-foods">${m.foods.map(f=>`<span class="dp-food-tag">🍽 ${f}</span>`).join('')}</div>
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
        <div class="dp-macro-ring-item">${_dpRing(proPct,'#7fb8d4',90,9)}<div class="dp-mring-val">${g.protein}g</div><div class="dp-mring-label">💪 Protein</div></div>
        <div class="dp-macro-ring-item">${_dpRing(carbPct,'#c4a87f',90,9)}<div class="dp-mring-val">${g.carbs||275}g</div><div class="dp-mring-label">🌾 Carbs</div></div>
        <div class="dp-macro-ring-item">${_dpRing(fatPct,'#F4613A',90,9)}<div class="dp-mring-val">${g.fat||78}g</div><div class="dp-mring-label">🫒 Fat</div></div>
      </div>
    </div>
    <div class="dp-card">
      <div class="dp-card-title">⚡ Calorie Breakdown</div>
      ${[['💪 Protein',proKcal,proKcal/totalMK,'#7fb8d4',`${g.protein}g × 4`],
         ['🌾 Carbs',carbKcal,carbKcal/totalMK,'#c4a87f',`${g.carbs||275}g × 4`],
         ['🫒 Fat',fatKcal,fatKcal/totalMK,'#F4613A',`${g.fat||78}g × 9`]
        ].map(([label,kcal,ratio,color,note])=>`
        <div style="margin-bottom:0.85rem">
          <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:0.35rem">
            <span style="color:var(--ink)">${label}</span>
            <span style="color:${color};font-family:'Fraunces',serif">${kcal} kcal <span style="color:var(--ink-50);font-family:'Plus Jakarta Sans',sans-serif;font-size:0.68rem">(${note} kcal/g)</span></span>
          </div>
          <div style="height:7px;background:rgba(255,255,255,0.07);border-radius:4px;overflow:hidden">
            <div style="width:${Math.round(ratio*100)}%;height:100%;background:${color};border-radius:4px"></div>
          </div>
        </div>`).join('')}
    </div>
    <div class="dp-card">
      <div class="dp-card-title">🌿 Micronutrient Goals</div>
      ${[['🌿 Fiber',g.fiber||28,'g','Aim for','#5DBD8A'],
         ['🍬 Sugar',g.sugar||50,'g','Limit to','#D97060'],
         ['🧂 Salt',g.sodium||2300,'mg','Limit to','#9A7FE8'],
         ['❤️ Cholesterol',g.chol||300,'mg','Limit to','#E89A3C']
        ].map(([label,val,unit,prefix,color])=>`
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
          {icon:'💊', name:'Vitamin B12', tip:'Found almost only in animal foods. Take a daily B12 supplement — critical for nerve health and energy.', severity: isVegan?'high':'medium'},
          {icon:'🧲', name:'Iron', tip:'Plant iron (non-haem) absorbs 2–3× less than meat iron. Always pair iron foods with Vitamin C (lemon, amla, tomato).', severity:'medium'},
          {icon:'🥛', name:'Calcium', tip: isVegan ? 'Skip dairy — get calcium from fortified plant milk, ragi flour, sesame seeds, and green leafy veggies.' : 'Dairy is your main source. Aim for 2–3 servings daily.', severity: isVegan?'high':'low'},
          {icon:'🐟', name:'Omega-3 (DHA/EPA)', tip:'Fatty fish is the richest source. For veg: eat flaxseeds, chia seeds, walnuts daily. Consider algae-oil supplements.', severity:'medium'},
          {icon:'🪙', name:'Zinc', tip:'Plant zinc is less bioavailable due to phytates. Good sources: pumpkin seeds, hemp seeds, legumes, cashews.', severity:'low'},
          {icon:'☀️', name:'Vitamin D', tip:'Sunlight is the best source. If mostly indoors, supplement 1000–2000 IU/day — especially in winter.', severity:'medium'},
        ].map(n=>`
        <div class="nutrient-watch-item">
          <span class="nw-icon">${n.icon}</span>
          <div class="nw-info">
            <div class="nw-name">${n.name}</div>
            <div class="nw-tip">${n.tip}</div>
          </div>
          <span class="nw-badge nw-${n.severity}">${n.severity==='high'?'Critical':n.severity==='medium'?'Watch':'Note'}</span>
        </div>`).join('')}
      </div>
    </div>` : ''}`;


  // HABITS TAB
  document.getElementById('dpTab-habits').innerHTML = `
    <div class="dp-card">
      <div class="dp-card-title">✅ Key Habits for ${plan.name}</div>
      <div class="dp-habit-list">
        ${plan.habits.map(h=>`
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
//  AUTO-LOGIN
// ─────────────────────────────────────────────────
(function() {
  const saved = DB.getCurrentUser();
  if (saved) {
    currentUser = saved;
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('mainApp').style.display     = 'block';
    initApp();
  }
})();

// ─────────────────────────────────────────────────
//  KEYBOARD SHORTCUTS
// ─────────────────────────────────────────────────
document.getElementById('loginPassword').addEventListener('keypress', e => { if(e.key==='Enter') handleLogin(); });
document.getElementById('loginEmail').addEventListener('keypress',    e => { if(e.key==='Enter') handleLogin(); });
// Registration Enter key -- routes through OTP verification flow
document.getElementById('regEmail').addEventListener('keypress',    e => { if(e.key==='Enter') sendOtpAndGoToStepOtp(); });
document.getElementById('regPassword').addEventListener('keypress', e => { if(e.key==='Enter') sendOtpAndGoToStepOtp(); });




// ═══════════════════════════════════════════════════════════════
//  NUTRIBOT — AI NUTRITIONIST CHATBOT
// ═══════════════════════════════════════════════════════════════

let _chatOpen = false;
let _chatHistory = [];    // { role: 'user'|'bot', text }
let _chatTyping = false;

function toggleChat() {
  _chatOpen = !_chatOpen;
  const panel  = document.getElementById('nutribotPanel');
  const fabBtn = document.getElementById('nutribotBtn');

  if (_chatOpen) {
    panel.style.display = 'flex';
    fabBtn.style.display = 'none';
    if (_chatHistory.length === 0) _initChat();
    // scroll to bottom
    setTimeout(() => _scrollChatBottom(), 50);
  } else {
    panel.style.display = 'none';
    fabBtn.style.display = 'flex';
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
    const formatted = msg.text
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
  const msg   = (input.value || '').trim();
  if (!msg || _chatTyping) return;

  input.value = '';
  _addUserMessage(msg);

  // Hide chips after first message
  const chips = document.getElementById('nutribotChips');
  if (chips) chips.style.display = 'none';

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
  const jwt = _getJwt();

  if (jwt) {
    // Use the backend proxy (which fetches logs from DB)
    try {
      const backendUrl = window._BACKEND_URL || '';
      const res = await fetch(`${backendUrl}/api/ai/chat`, {
        method:  'POST',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': `Bearer ${jwt}`,
        },
        body: JSON.stringify({ message }),
        signal: AbortSignal.timeout(95000),
      });
      if (res.ok) {
        const data = await res.json();
        return data.reply || "I didn't quite understand that. Could you rephrase?";
      }
    } catch (e) {
      // Fall through to client-side fallback
    }
  }

  // Client-side fallback: call LLM server directly with local log context
  const context = _buildLocalChatContext();
  const llmUrl  = window.LLM_SERVER_URL || 'https://energyvenom-nutritrack-llm.hf.space';
  try {
    const res = await fetch(`${llmUrl}/api/ai/chat`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message, context }),
      signal:  AbortSignal.timeout(95000),
    });
    if (res.ok) {
      const data = await res.json();
      return data.reply || "I didn't quite get that. Try asking something else!";
    }
  } catch (e) {
    // Both failed — return a rule-based fallback inline
  }
  return _localNutribotFallback(message, context);
}

function _getJwt() {
  // Get JWT from localStorage so it persists across tab closes
  try {
    const s = localStorage.getItem('nt_jwt');
    if (s) return s;
  } catch (e) {}
  return null;
}

function _buildLocalChatContext() {
  if (!currentUser) return {};
  const goals = currentUser.goals || {};
  const logs  = window._foodLogs;
  const today = todayStr();

  // Last 7 days of logs
  const recent = logs
    .filter(l => l.date >= (new Date(Date.now() - 7*86400000)).toISOString().split('T')[0])
    .slice(0, 30)
    .map(l => ({
      date:      l.date,
      meal:      l.mealType || 'meal',
      food:      l.name,
      cal:       Math.round(l.cal || 0),
      protein_g: Math.round((l.pro || 0) * 10) / 10,
      carbs_g:   Math.round((l.carb || 0) * 10) / 10,
      fat_g:     Math.round((l.fat || 0) * 10) / 10,
      vit_d:     Math.round((l.vit_d || 0) * 10) / 10,
      iron:      Math.round((l.iron || 0) * 10) / 10,
      folate:    Math.round((l.folate || 0) * 10) / 10,
    }));

  return {
    user_name:   currentUser.name.split(' ')[0],
    goals: {
      calories: goals.calories || 2000,
      protein:  goals.protein  || 150,
      carbs:    goals.carbs    || 250,
      fat:      goals.fat      || 65,
      fiber:    goals.fiber    || 28,
      vit_d:    goals.vit_d    || 15,
      iron:     goals.iron     || 18,
      folate:   goals.folate   || 400,
    },
    recent_logs: recent,
  };
}

function _localNutribotFallback(message, context) {
  const msg      = message.toLowerCase();
  const goals    = (context && context.goals) || {};
  const logs     = (context && context.recent_logs) || [];
  const name     = (context && context.user_name) || 'there';
  const calGoal  = goals.calories || 2000;
  const protGoal = goals.protein  || 150;
  const carbGoal = goals.carbs    || 250;
  const fatGoal  = goals.fat      || 65;
  const fiberGoal= goals.fiber    || 28;
  const today    = todayStr();
  const todayLog = logs.filter(l => l.date === today);
  const todayCal = todayLog.reduce((s, l) => s + (l.cal || 0), 0);
  const todayProt= todayLog.reduce((s, l) => s + (l.protein_g || 0), 0);
  const todayCarb= todayLog.reduce((s, l) => s + (l.carbs_g || 0), 0);
  const todayFat = todayLog.reduce((s, l) => s + (l.fat_g || 0), 0);
  const remCal   = calGoal - todayCal;

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
    if (rem > 0)  return `Almost at protein goal! Just **${Math.round(rem)}g more** to go. A boiled egg or a small protein shake will do it!`;
    return `Protein goal crushed! **${Math.round(todayProt)}g** consumed today. Your muscles will thank you!`;
  }
  if (/carb|carbohydrate|rice|roti|bread|sugar|glucose|energy/.test(msg)) {
    const rem = carbGoal - todayCarb;
    if (rem > 0) return `Carbs: **${Math.round(todayCarb)}g / ${carbGoal}g** (${Math.round(rem)}g remaining). Prefer complex carbs: oats, brown rice, whole wheat roti over refined options.`;
    return `You've hit your carb goal (**${Math.round(todayCarb)}g**). Focus on protein and vegetables for the rest of the day.`;
  }
  if (/fat|oil|ghee|butter|avocado|nuts|omega/.test(msg)) {
    const rem = fatGoal - todayFat;
    return `Fat today: **${Math.round(todayFat)}g / ${fatGoal}g** (${Math.round(Math.max(0,rem))}g remaining). Healthy fats: ghee (in moderation), nuts, avocado, olive oil. Avoid trans fats in fried fast food.`;
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
    return `BMI = weight(kg) / height(m)^2. Healthy range: **18.5-24.9**. But BMI doesn't account for muscle mass. Focus on waist circumference and body fat % for a fuller picture.`;
  }
  if (/meal time|when to eat|timing|skip meal|intermittent|16:8|fasting/.test(msg)) {
    return `Ideal timing: **Breakfast** within 1hr of waking, **Lunch** 12-2 PM, **Dinner** before 8 PM. For intermittent fasting (16:8), eat between 12-8 PM. Avoid eating within 2 hours of sleep.`;
  }
  if (/breakfast|morning meal|wake up|poha|upma|idli|paratha/.test(msg)) {
    return `Great Indian breakfasts: **Poha** (250 kcal), **Oats+milk** (300 kcal), **2 Eggs+2 roti** (350 kcal), **Idli+sambar** (220 kcal), **Greek yogurt+fruit** (200 kcal). High-protein breakfast controls hunger till lunch!`;
  }
  if (/lunch|afternoon|midday|dal rice|thali/.test(msg)) {
    return `Balanced Indian lunch: **Dal + 2 roti + sabzi + curd** (~600 kcal, 25g protein), **Rajma rice** (~550 kcal), **Chicken curry + rice** (~650 kcal). Fill half your plate with vegetables!`;
  }
  if (/dinner|evening meal|night|supper/.test(msg)) {
    if (remCal > 500) return `You have **${Math.round(remCal)} kcal** for dinner - enjoy a proper meal: grilled chicken/paneer + vegetables + small portion rice or 2 rotis.`;
    if (remCal > 150) return `Keep dinner light - **${Math.round(remCal)} kcal** remaining. Try khichdi, vegetable soup + 1 roti, or salad with paneer.`;
    return `You're near your limit. Have a very light dinner - vegetable soup, cucumber salad, or warm milk. Your body will thank you!`;
  }
  if (/snack|munchies|hunger|evening bite|mid.?meal|craving/.test(msg)) {
    return `Healthy snacks under 200 kcal: **Almonds** (164 kcal/28g), **Apple** (95 kcal), **Roasted chana** (120 kcal), **Greek yogurt** (100 kcal), **Cucumber+hummus** (80 kcal). Avoid chips and biscuits!`;
  }
  if (/pre.?workout|before gym|before exercise|pre.?train/.test(msg)) {
    return `**Pre-workout (1-2hr before):** Banana + peanut butter, oats with milk, or rice + chicken. You need fast carbs for energy + some protein. Avoid heavy/fatty meals right before training.`;
  }
  if (/post.?workout|after gym|after exercise|recovery meal|muscle recovery/.test(msg)) {
    return `**Post-workout (within 45 min):** 30-40g protein + carbs. Try: protein shake + banana, eggs + toast, paneer + roti, or curd rice. Don't skip this meal - it's when muscles repair!`;
  }
  if (/biryani|butter chicken|dal makhani|samosa|pav bhaji|chole|rajma|dosa|idli|roti|chapati|paratha|paneer|tikka/.test(msg)) {
    return `Indian food can be very nutritious! **Best choices:** Dal (high protein/fiber), Idli+sambar (light, fermented), Rajma (plant protein), Roti. **Limit:** Biryani (high cal), Butter chicken (high fat), Samosa (deep fried). Balance is key!`;
  }
  if (/vitamin|mineral|deficiency|iron|calcium|d3|b12|zinc|magnesium/.test(msg)) {
    return `Common Indian deficiencies: **Vitamin D** (get 20min sun daily), **B12** (vegetarians: take supplements), **Iron** (eat spinach, lentils, jaggery), **Calcium** (milk, curd, ragi). Get a blood test annually!`;
  }
  if (/diabetes|blood sugar|insulin|glycemic|glucose/.test(msg)) {
    return `For blood sugar control: prefer **low glycemic foods** - oats, barley, dal, vegetables over white rice/bread. Eat smaller frequent meals. A 10-min walk after meals helps lower blood sugar significantly!`;
  }
  if (/cholesterol|heart|hdl|ldl|triglyceride|cardiovascular/.test(msg)) {
    return `For heart health: reduce saturated fat, increase soluble fiber (oats, beans), eat flaxseeds/walnuts for omega-3, exercise 150 min/week. Get your lipid panel checked annually.`;
  }
  if (/sleep|rest|recovery|fatigue|tired|insomnia/.test(msg)) {
    return `Sleep is when your body repairs muscle! Aim for **7-9 hours**. Poor sleep raises ghrelin (hunger hormone), causes cravings, and slows metabolism. Avoid screens 1hr before bed.`;
  }
  if (/cheat|junk|pizza|burger|cheat meal|cheat day|treat yourself/.test(msg)) {
    return `Cheat meals are okay! Rule: **1 cheat meal per week**, not a full cheat day. Enjoy what you love in moderation. One meal never ruined progress - just like one salad never created it. Get back on track the next meal!`;
  }
  if (/vegetarian|vegan|plant.?based|no meat/.test(msg)) {
    return `Top veg protein sources: **Paneer** (18g/100g), **Tofu** (8g/100g), **Rajma** (9g/cup), **Chana dal** (9g/cup), **Moong dal** (7g/cup), **Greek yogurt** (10g/100g), **Quinoa** (8g/cup). Combine sources for complete amino acids!`;
  }
  if (/burn|exercise|workout|cardio|run|walk|cycling|swim|calorie burn/.test(msg)) {
    return `Approx calorie burn (70kg, 30 min): **Running** ~300 kcal, **Cycling** ~240 kcal, **Swimming** ~250 kcal, **Brisk Walk** ~150 kcal, **HIIT** ~350 kcal, **Yoga** ~100 kcal.`;
  }
  if (/macro|breakdown|split|nutrient|today.?s nutrition/.test(msg)) {
    if (todayCal === 0) return `No food logged yet today, ${name}! Log your first meal and I'll give you a full macro breakdown.`;
    return `Today's macros:\n- Protein: **${Math.round(todayProt)}g / ${protGoal}g** (${Math.round(todayProt/protGoal*100)}%)\n- Carbs: **${Math.round(todayCarb)}g / ${carbGoal}g** (${Math.round(todayCarb/carbGoal*100)}%)\n- Fat: **${Math.round(todayFat)}g / ${fatGoal}g** (${Math.round(todayFat/fatGoal*100)}%)\n- Calories: **${Math.round(todayCal)} / ${calGoal} kcal**`;
  }
  if (/metabolism|tdee|maintenance|metabolic rate|bmr/.test(msg)) {
    return `Your TDEE is how many calories you burn daily at your activity level. Eat less to lose weight, more to gain. Strength training boosts metabolic rate long-term - you burn more even at rest!`;
  }
  if (/supplement|creatine|whey|protein powder|bcaa|multivitamin/.test(msg)) {
    return `Supplements worth considering: **Creatine monohydrate** (proven for strength/muscle), **Whey protein** (convenient protein), **Vitamin D3+K2** (most Indians are deficient), **Omega-3** (heart+brain). Food first, supplements second!`;
  }
  if (/alcohol|beer|wine|whisky|drinking/.test(msg)) {
    return `Alcohol has **7 kcal/gram** - more than carbs! A beer adds ~200 kcal, wine ~120 kcal. It disrupts sleep and fat metabolism. If you drink, account for it in your daily calories.`;
  }
  if (/motivat|inspire|stuck|plateau|not losing|demotivat|give up/.test(msg)) {
    return `Plateaus are normal - your body adapts! Try: changing your workout, adjusting calories by 100-150 kcal, prioritizing sleep, taking body measurements instead of just scale weight. Consistency beats perfection, ${name}!`;
  }
  if (/what did i eat|my food today|today.?s log|show log|food log/.test(msg)) {
    if (todayLog.length === 0) return `No food logged today yet, ${name}! Start logging your meals to track your nutrition.`;
    const foods = todayLog.map(l => l.food).slice(0, 6).join(', ');
    return `Today you logged: **${foods}** - totaling **${Math.round(todayCal)} kcal** and **${Math.round(todayProt)}g protein**. Check your Dashboard for the full breakdown!`;
  }
  if (/my goal|daily goal|target|calorie goal|how much should/.test(msg)) {
    return `Your daily targets: **${calGoal} kcal** - **${protGoal}g protein** - **${carbGoal}g carbs** - **${fatGoal}g fat** - **${fiberGoal}g fiber**. These are calculated from your body stats. Update your profile to recalculate!`;
  }
  if (/^(hi|hello|hey|hii|helo|namaste|sup|yo)\b/.test(msg)) {
    return `Hey ${name}! I'm NutriBot, your AI nutritionist. Ask me about nutrition, your food logs, meal ideas, weight loss, protein, or anything health-related!`;
  }
  if (/thank|thanks|great|awesome|nice|helpful/.test(msg)) {
    return `You're welcome, ${name}! Keep up the great work on your nutrition journey. Small consistent steps lead to big results! Anything else I can help with?`;
  }
  return `I'm your AI nutritionist, **${name}**! Ask me about:\n- "Am I on track today?"\n- "What should I eat for dinner?"\n- "Show my macro breakdown"\n- "How to lose weight?"\n- "Best vegetarian protein sources"\n- "Pre-workout nutrition"\n- "Does sleep affect weight?"\n\nJust type your question!`;
}
// Show NutriBot button when user is logged in
const _origLoginSuccess = loginSuccess;
loginSuccess = function(user) {
  _origLoginSuccess(user);
  const btn = document.getElementById('nutribotBtn');
  if (btn) btn.style.display = 'flex';
  // Reset chat on login
  _chatHistory = [];
  _chatOpen = false;
  const panel = document.getElementById('nutribotPanel');
  if (panel) panel.style.display = 'none';
};

// Hide NutriBot button when user logs out
const _origHandleLogout = handleLogout;
handleLogout = function() {
  const btn = document.getElementById('nutribotBtn');
  if (btn) btn.style.display = 'none';
  const panel = document.getElementById('nutribotPanel');
  if (panel) { panel.style.display = 'none'; _chatOpen = false; }
  _chatHistory = [];
  _origHandleLogout();
};

