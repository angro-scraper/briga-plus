const CACHE = 'briga-plus-notification-logo-20260811';
const OFFLINE = [
  '/static/briga-v2.css?v=20260808',
  '/static/briga-v2.js?v=20260803',
  '/static/sos-location.js?v=20260809',
  '/static/mobile-enhancements.js?v=20260806',
  '/static/chat-live.js?v=20260807',
  '/static/briga-mark.svg',
  '/static/briga-ui-icons.svg',
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
  event.respondWith(fetch(event.request).then(response => {
    const copy = response.clone();
    caches.open(CACHE).then(cache => cache.put(event.request, copy));
    return response;
  }).catch(() => caches.match(event.request)));
});

self.addEventListener('push', event => {
  const payload = event.data ? event.data.json() : {};
  event.waitUntil(self.registration.showNotification(payload.title || 'Briga+', {
    body: payload.body || 'Imate novo obaveštenje.',
    icon: '/static/briga-notification-icon-512.png?v=20260811',
    badge: '/static/briga-notification-badge-96.png?v=20260811',
    data: { url: payload.url || '/' },
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url || '/'));
});
