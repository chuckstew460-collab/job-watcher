// Service worker: makes the site installable and usable offline.
//
// Online:  every request goes to the network first (so pages and the two data
//          files are always fresh), and a copy of each answer is kept.
// Offline: the kept copy is served, so the site opens and shows the last data
//          this device loaded.
const CACHE = "job-watcher-v1";
const SHELL = [
  "./",
  "index.html",
  "browse.html",
  "market.html",
  "manifest.webmanifest",
  "assets/css/site.css",
  "assets/js/common.js",
  "assets/js/charts.js",
  "assets/js/today.js",
  "assets/js/browse.js",
  "assets/js/market.js",
  "assets/icons/favicon.svg",
  "assets/icons/icon-192.png",
  "assets/icons/icon-512.png",
];
const DATA = ["data/status.json", "data/history.csv"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then(async (cache) => {
    await cache.addAll(SHELL);
    // The data files are cached too, but a missing one must not block installing.
    await Promise.allSettled(DATA.map((url) => cache.add(url)));
  }).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()));
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok || response.type === "opaque") cache.put(request, response.clone());
    return response;
  } catch (err) {
    const kept = await cache.match(request, { ignoreSearch: true })
      || (request.mode === "navigate" && await cache.match("index.html"));
    if (kept) return kept;
    throw err;
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const kept = await cache.match(request);
  if (kept) return kept;
  const response = await fetch(request);
  if (response.ok || response.type === "opaque") cache.put(request, response.clone());
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin === self.location.origin) {
    event.respondWith(networkFirst(request));
  } else if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") {
    event.respondWith(cacheFirst(request));  // font files never change at a given URL
  }
});
