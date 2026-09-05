// NutriTrack — ThemeToggle.js
// Universal Dark / Light mode controller with instant DOM-wide synchronization,
// localStorage persistence, and multi-control state updates across all viewports.

(function () {
  const STORAGE_KEY = 'nutritrack-theme';

  function applyTheme(theme) {
    if (!theme || (theme !== 'dark' && theme !== 'light')) {
      theme = 'dark';
    }

    const isDark = theme === 'dark';

    // 1. Set data-theme on BOTH root html and body
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);

    // 2. Add explicit utility classes for maximum CSS selector compatibility
    if (isDark) {
      document.documentElement.classList.remove('theme-light');
      document.documentElement.classList.add('theme-dark');
      document.body.classList.remove('theme-light');
      document.body.classList.add('theme-dark');
    } else {
      document.documentElement.classList.remove('theme-dark');
      document.documentElement.classList.add('theme-light');
      document.body.classList.remove('theme-dark');
      document.body.classList.add('theme-light');
    }

    // 3. Persist to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      console.warn('Theme storage unavailable:', e);
    }

    // 4. Update all switch buttons across the app
    document.querySelectorAll('#themeToggleDark, .theme-btn-dark').forEach(b => {
      b.classList.toggle('active', isDark);
    });
    document.querySelectorAll('#themeToggleLight, .theme-btn-light').forEach(b => {
      b.classList.toggle('active', !isDark);
    });

    // 5. Update mobile topbar icon
    const mobIcon = document.getElementById('mobThemeIcon');
    if (mobIcon) mobIcon.textContent = isDark ? '🌙' : '☀️';

    // 6. Update dashboard header toggle pill
    const dashIcon = document.getElementById('dashThemeIcon');
    const dashText = document.getElementById('dashThemeText');
    const dashBtn = document.getElementById('dashThemeBtn');
    if (dashIcon) dashIcon.textContent = isDark ? '🌙' : '☀️';
    if (dashText) dashText.textContent = isDark ? 'Dark Mode' : 'Light Mode';
    if (dashBtn) {
      dashBtn.setAttribute('data-current-theme', theme);
      dashBtn.setAttribute('title', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
    }

    // 7. Update sidebar theme buttons
    const sideIcon = document.getElementById('sidebarThemeIcon');
    const sideText = document.getElementById('sidebarThemeText');
    if (sideIcon) sideIcon.textContent = isDark ? '🌙' : '☀️';
    if (sideText) sideText.textContent = isDark ? 'Dark' : 'Light';

    // 8. Dispatch event so charts and dynamic components can re-style
    try {
      window.dispatchEvent(new CustomEvent('themechange', { detail: { theme, isDark } }));
      document.dispatchEvent(new CustomEvent('themechange', { detail: { theme, isDark } }));
    } catch (e) {}

    // 9. Re-render macro chart if active
    if (typeof window.renderMacroDonutChart === 'function') {
      try { window.renderMacroDonutChart(); } catch (e) {}
    }
  }

  function getInitialTheme() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'dark' || saved === 'light') return saved;
    } catch (e) {}
    return 'dark';
  }

  window.setAppTheme = function (theme) {
    applyTheme(theme);
  };

  window.toggleAppTheme = function () {
    const cur = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = cur === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    return next;
  };

  // Apply immediately (before DOMContentLoaded to avoid FOUC)
  applyTheme(getInitialTheme());

  function injectToggle() {
    const statsBlock = document.querySelector('.profile-stats');
    if (statsBlock && !document.getElementById('themeToggleCard')) {
      const card = document.createElement('div');
      card.id = 'themeToggleCard';
      card.className = 'theme-toggle-card';
      card.innerHTML = `
        <span class="ttc-label">Appearance Theme</span>
        <div class="theme-toggle-switch">
          <button type="button" id="themeToggleDark" onclick="setAppTheme('dark')">🌙 Dark</button>
          <button type="button" id="themeToggleLight" onclick="setAppTheme('light')">☀️ Light</button>
        </div>
      `;
      statsBlock.insertAdjacentElement('afterend', card);
    }

    applyTheme(document.documentElement.getAttribute('data-theme') || 'dark');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectToggle);
  } else {
    injectToggle();
  }
})();