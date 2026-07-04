/**
 * NutriTrack — Service Worker (sw.js)
 * Enables offline support, caching, and PWA install.
 *
 * Strategy:
 *   - HTML navigations (/, /profile, /track, etc.) → Network First
 *     (the backend serves index.html for every clean URL via History API
 *     routing — Cache First here would permanently serve whatever HTML
 *     happened to be cached for that exact path first, which broke /profile
 *     and other routes for anyone who'd cached them before the clean-URL
 *     routing was added.)
 *   - Static assets (CSS/JS/icons)     → Cache First, then Network
 *   - API calls                        → Network First (fall back to cache)
 *   - Images                           → Stale While Revalidate
 */

const CACHE_NAME = 'nutritrack-v12'; // bumped from v11 to evict stale HTML cached under the old Cache-First strategy
const APP_SHELL = [
  '/',
  '/index.html',
  '/Style.css',
  '/App.js',
  '/Foods.js',
  '/manifest.json',
  '/logo-nav.png',
  '/logo-auth.png',
  '/icons/icon.png',
];

// ─── Install: pre-cache app shell ───────────────────────
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Pre-caching app shell');
      return cache.addAll(APP_SHELL);
    })
  );
  self.skipWaiting();
});

// ─── Activate: clean old caches ─────────────────────────
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => {
            console.log('[SW] Removing old cache:', key);
            return caches.delete(key);
          })
      )
    )
  );
  self.clients.claim();
});

// ─── Fetch: smart caching strategy ──────────────────────
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Skip non-GET requests (POST to API etc.)
  if (req.method !== 'GET') return;

  // Skip chrome-extension, devtools, etc.
  if (!url.protocol.startsWith('http')) return;

  // API calls → Network First
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(req)
        .then((response) => {
          // Cache successful GET API responses
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return response;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // HTML navigations (any clean URL — /, /profile, /track, ...) → Network First.
  // These are all served by the same index.html via the backend's SPA catch-all
  // route, so a Cache-First strategy here would happily serve whatever HTML
  // got cached the first time a given path was visited, forever, even after a
  // real deploy fixed something. Always prefer the network; only fall back to
  // cache when fully offline.
  const isNavigation =
    req.mode === 'navigate' ||
    (req.headers.get('accept') || '').includes('text/html');
  if (isNavigation) {
    event.respondWith(
      fetch(req)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return response;
        })
        .catch(() =>
          caches.match(req).then((cached) => cached || caches.match('/index.html'))
        )
    );
    return;
  }

  // Static assets (JS/CSS/images) → Cache First, then Network.
  // Safe to cache aggressively since these are cache-busted via ?v= query
  // params (see index.html) whenever their content changes.
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) {
        // Stale-while-revalidate: return cached immediately, refresh in the
        // background for next time. Clone BEFORE handing the response to
        // cache.put() — cache.put() reads the body stream, and cloning
        // after that has already started is what the previous version of
        // this file did, which risked a "body already used" error.
        fetch(req)
          .then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
            }
          })
          .catch(() => { });
        return cached;
      }
      // Not in cache → fetch from network
      return fetch(req).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
        }
        return response;
      });
    })
  );
});

// ─── Background Sync (future: queue offline food logs) ──
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-food-logs') {
    console.log('[SW] Syncing food logs...');
    // Future: replay queued POST /api/logs requests
  }
});

// ─── Push notifications (future) ────────────────────────
self.addEventListener('push', (event) => {
  if (!event.data) return;
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title || 'NutriTrack', {
      body: data.body || 'Time to log your meal!',
      icon: '/icons/icon.png',
      badge: '/icons/icon.png',
      tag: 'nutritrack-notification',
    })
  );
});