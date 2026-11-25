// Minimal service worker: makes the dashboard installable as an app. It caches only the static shell;
// API data is never cached (it is always read live from the local server).
const CACHE = "slugshot-shell-v1";
const SHELL = ["/static/app.css", "/static/app.js", "/static/theme.js", "/static/fonts/urbanist-latin-wght-normal.woff2", "/static/icons/icon.svg"];

self.addEventListener("install", (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener("activate", (e) => e.waitUntil(
  caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || !url.pathname.startsWith("/static/")) return;
  // Network first so updates show at once; the cache is only a fallback while the server starts.
  e.respondWith(fetch(e.request).then((r) => {
    const copy = r.clone();
    caches.open(CACHE).then((c) => c.put(e.request, copy));
    return r;
  }).catch(() => caches.match(e.request)));
});
