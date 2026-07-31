const CACHE = 'briga-plus-chat-sos-20260805';
const OFFLINE = [
  '/static/briga-v2.css?v=20260805',
  '/static/briga-v2.js?v=20260803',
  '/static/sos-location.js?v=20260804',
  '/static/mobile-enhancements.js?v=20260805',
  '/static/briga-mark.svg',
  '/static/briga-ui-icons.svg',
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
    icon: '/static/briga-app-icon-512.png',
    badge: '/static/briga-app-icon-512.png',
    data: { url: payload.url || '/' },
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url || '/'));
});
