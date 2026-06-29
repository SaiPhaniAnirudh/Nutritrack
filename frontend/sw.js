/**
 * NutriTrack — Service Worker (sw.js)
 * Enables offline support, caching, and PWA install.
 *
 * Strategy:
 *   - App shell (HTML/CSS/JS/icons) → Cache First
 *   - API calls                     → Network First (fall back to cache)
 *   - Images                        → Stale While Revalidate
 */

const CACHE_NAME = 'nutritrack-v4';
const APP_SHELL = [
  '/',
  '/index.html',
  '/Style.css',
  '/App.js',
  '/Foods.js',
  '/manifest.json',
  '/logo-nav.png',
  '/logo-auth.png',
  '/logo-loader.png',
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
  const url = new URL(event.request.url);

  // Skip non-GET requests (POST to API etc.)
  if (event.request.method !== 'GET') return;

  // Skip chrome-extension, devtools, etc.
  if (!url.protocol.startsWith('http')) return;

  // API calls → Network First
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache successful GET API responses
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // App shell & static assets → Cache First, then Network
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        // Stale-while-revalidate: return cached, update in background
        const fetchPromise = fetch(event.request).then((response) => {
          if (response.ok) {
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, response));
          }
          return response.clone();
        }).catch(() => {});
        return cached;
      }
      // Not in cache → fetch from network
      return fetch(event.request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
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
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-72.png',
      tag: 'nutritrack-notification',
    })
  );
});
