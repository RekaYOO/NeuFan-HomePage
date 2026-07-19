const CACHE_NAME = 'neufan-static-v1';
const VUE_ASSET = '/assets/vue.global.prod.js';
const BOOKMARKS_PATH = '/data/bookmarks.json';

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.add(VUE_ASSET))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(names => Promise.all(names
                .filter(name => name !== CACHE_NAME)
                .map(name => caches.delete(name))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;

    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin) return;

    if (url.pathname === VUE_ASSET) {
        event.respondWith(cacheFirst(event.request));
        return;
    }

    if (url.pathname === BOOKMARKS_PATH) {
        event.respondWith(versionedBookmarks(event.request));
    }
});

async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;

    const response = await fetch(request);
    if (response.ok) {
        const cache = await caches.open(CACHE_NAME);
        await cache.put(request, response.clone());
    }
    return response;
}

async function versionedBookmarks(request) {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(request);
    if (cached) return cached;

    try {
        const response = await fetch(request);
        if (response.ok) {
            const keys = await cache.keys();
            await Promise.all(keys
                .filter(key => new URL(key.url).pathname === BOOKMARKS_PATH)
                .map(key => cache.delete(key)));
            await cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        const keys = await cache.keys();
        const fallbackKey = keys.find(key => new URL(key.url).pathname === BOOKMARKS_PATH);
        if (fallbackKey) return cache.match(fallbackKey);
        throw error;
    }
}
