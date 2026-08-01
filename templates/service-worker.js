const CACHE = 'briga-plus-theme-refresh-20260801d1';
const OFFLINE = [
  '/static/briga-v2.css?v=20260801d1',
  '/static/briga-v2.js?v=20260803',
  '/static/sos-location.js?v=20260801d1',
  '/static/mobile-enhancements.js?v=20260816',
  '/static/chat-live.js?v=20260807',
  '/static/deep-links.js?v=20260803',
  '/static/senior-guidance.js?v=20260803',
  '/static/briga-mark.svg',
  '/static/briga-ui-icons.svg',
  '/static/illustrations/family-care-hero.webp',
  '/static/briga-notification-icon-512.png?v=20260811',
  '/static/briga-notification-badge-96.png?v=20260811',
  '/static/manifest.webmanifest',
];

self.addEventListener('install', event => event.waitUntil(
  caches.open(CACHE).then(cache => cache.addAll(OFFLINE)).then(() => self.skipWaiting())
));

self.addEventListener('activate', event => event.waitUntil(
  caches.keys().then(keys => Promise.all(keys
    .filter(key => key.startsWith('briga-plus-') && key !== CACHE)
    .map(key => caches.delete(key))
  )).then(() => self.clients.claim())
));

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  // Lične, zdravstvene i porodične stranice nikada ne čuvamo u kešu.
  // Samo statičke datoteke dobijaju brz odgovor iz lokalnog keša.
  if (url.origin !== self.location.origin || !url.pathname.startsWith('/static/')) return;
  event.respondWith(caches.match(event.request).then(cached => {
    if (cached) return cached;
    return fetch(event.request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE).then(cache => cache.put(event.request, copy));
      }
      return response;
    });
  }));
});

self.addEventListener('push', event => {
  const payload = event.data ? event.data.json() : {};
  const target = payload.kind === 'sos' ? '/?open=sos-detail' : (payload.url || '/');
  event.waitUntil(self.registration.showNotification(payload.title || 'Briga+', {
    body: payload.body || 'Imate novo obaveštenje.',
    icon: '/static/briga-notification-icon-512.png?v=20260811',
    badge: '/static/briga-notification-badge-96.png?v=20260811',
    data: { url: target, kind: payload.kind || '' },
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url || '/'));
});
