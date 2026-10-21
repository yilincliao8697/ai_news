// PWA service worker — lets the installed app open offline.
// Strategy: network-first for pages and public API reads, falling back to the
// last cached copy. Admin pages and non-GET requests are never cached.
// Bump CACHE when changing this file so old caches are cleared.

const CACHE = "ai-news-v1";
const PRECACHE = ["/", "/manifest.webmanifest", "/icons/icon-192.png", "/icons/icon-512.png"];
const API_PATHS = ["/articles", "/admin/feeds", "/scheduler/status"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function shouldCache(request) {
  if (request.method !== "GET") return false;
  const url = new URL(request.url);
  if (url.origin === self.location.origin) {
    return !url.pathname.startsWith("/admin");
  }
  // Cross-origin: only the public read endpoints of the backend API.
  return API_PATHS.includes(url.pathname);
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (!shouldCache(request)) return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(() =>
        caches.match(request).then((cached) => cached ?? (request.mode === "navigate" ? caches.match("/") : undefined))
      )
      .then((response) => response ?? Response.error())
  );
});
