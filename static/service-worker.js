/* Only the self-contained offline explanation is cached. Pages, photos,
   preferences, API responses and scripts always use the current server. */
const OFFLINE_CACHE = 'choob-mobile-offline-v1';
const OFFLINE_URL = '/offline.html';

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(OFFLINE_CACHE);
    await cache.addAll([OFFLINE_URL]);
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names
      .filter(name => name.startsWith('choob-mobile-offline-') && name !== OFFLINE_CACHE)
      .map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin
      || url.pathname.startsWith('/api/') || request.mode !== 'navigate') return;

  // Do not replace failed API calls with HTML or replay an earlier AI result.
  event.respondWith(fetch(request).catch(async () => {
    const cache = await caches.open(OFFLINE_CACHE);
    return await cache.match(OFFLINE_URL) || new Response(
      '<h1>Choob is offline</h1><p>Reconnect and try again.</p>',
      {status: 503, headers: {'Content-Type': 'text/html; charset=utf-8'}}
    );
  }));
});
