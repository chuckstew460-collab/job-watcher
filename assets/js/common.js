// Shared by all three pages: the nav bar, theme, data loading, CSV parsing,
// date helpers, number formatting, the shortlist, and the service worker.

export const DATA = { history: "data/history.csv", status: "data/status.json" };

const PAGES = [
  ["index.html", "Today"],
  ["browse.html", "Browse"],
  ["market.html", "Market"],
];

// ------------------------------------------------------------------ DOM helper
// Builds elements with textContent only, so posting titles from the job boards
// can never inject markup.
export function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k === "style") el.style.cssText = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

const ICONS = {
  star: '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" fill="currentColor"/>',
  starOutline: '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
  check: '<circle cx="12" cy="12" r="10" fill="currentColor"/><path d="M7.5 12.3l3 3 6-6.3" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
  cross: '<circle cx="12" cy="12" r="10" fill="currentColor"/><path d="M8.5 8.5l7 7m0-7l-7 7" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>',
  moon: '<path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',
  sun: '<circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 2.5v2.2M12 19.3v2.2M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  external: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
};

export function icon(name, cls = "") {
  const wrap = document.createElement("span");
  wrap.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true" class="${cls}">${ICONS[name]}</svg>`;
  return wrap.firstChild;
}

// ------------------------------------------------------------------ storage (never required)
export function store(key, value) {
  try {
    if (value === undefined) return JSON.parse(localStorage.getItem(key) ?? "null");
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch { /* private window or blocked storage: carry on without it */ }
  return null;
}

// ------------------------------------------------------------------ theme
function effectiveTheme() {
  const set = document.documentElement.dataset.theme;
  if (set) return set;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function applyTheme(theme) {
  if (theme) document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = effectiveTheme() === "dark" ? "#1a1a19" : "#fcfcfb";
}
applyTheme(store("jw-theme"));

// ------------------------------------------------------------------ nav bar, footer, PWA
export function initChrome(current) {
  const nav = document.getElementById("site-nav");
  nav.className = "nav";
  nav.replaceChildren(
    h("div", { class: "nav-inner" },
      h("a", { class: "brand", href: "index.html" },
        h("img", { src: "assets/icons/favicon.svg", alt: "", width: 28, height: 28 }),
        h("span", { text: "Job Watcher" }),
        h("small", { text: "Finance & data analyst" })),
      h("nav", { class: "nav-links", "aria-label": "Pages" },
        PAGES.map(([href, label]) =>
          h("a", { href, "aria-current": href === current ? "page" : null, text: label }))),
      h("div", { class: "nav-tools" },
        h("button", { class: "install-btn", id: "install-btn", hidden: true, text: "Install app" }),
        h("button", { class: "icon-btn", id: "theme-btn", type: "button" }))),
    h("div", { class: "offline-banner", id: "offline-banner", hidden: true,
               text: "You're offline. Showing the last data this device loaded." }));

  const themeBtn = document.getElementById("theme-btn");
  const paintThemeBtn = () => {
    const dark = effectiveTheme() === "dark";
    themeBtn.replaceChildren(icon(dark ? "sun" : "moon"));
    themeBtn.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
    themeBtn.title = themeBtn.getAttribute("aria-label");
  };
  themeBtn.addEventListener("click", () => {
    const next = effectiveTheme() === "dark" ? "light" : "dark";
    applyTheme(next);
    store("jw-theme", next);
    paintThemeBtn();
    window.dispatchEvent(new Event("themechange"));
  });
  paintThemeBtn();

  const foot = document.getElementById("site-foot");
  if (foot) {
    foot.replaceChildren(h("div", { class: "inner" },
      h("span", { text: "Pulled every day from 20 employer job boards by GitHub Actions." }),
      h("span", {},
        h("a", { href: "https://github.com/chuckstew460-collab/job-watcher", text: "Source & data" }),
        " · ",
        h("a", { href: "https://github.com/chuckstew460-collab/job-watcher/issues", text: "Daily issues" }))));
  }

  // Offline banner
  const banner = document.getElementById("offline-banner");
  const paintOnline = () => { banner.hidden = navigator.onLine; };
  addEventListener("online", paintOnline);
  addEventListener("offline", paintOnline);
  paintOnline();

  // Install button (Chromium fires beforeinstallprompt when the site is installable)
  const installBtn = document.getElementById("install-btn");
  let deferred = null;
  addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferred = e;
    installBtn.hidden = false;
  });
  installBtn.addEventListener("click", async () => {
    if (!deferred) return;
    deferred.prompt();
    await deferred.userChoice;
    deferred = null;
    installBtn.hidden = true;
  });
  addEventListener("appinstalled", () => { installBtn.hidden = true; });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch((err) => console.warn("service worker", err));
  }
}

// ------------------------------------------------------------------ data
async function get(url) {
  // no-cache: always ask the network (the service worker answers from its
  // cache only when the network is unreachable).
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res;
}

export async function loadStatus() {
  return (await get(DATA.status)).json();
}

export async function loadHistory() {
  const text = await (await get(DATA.history)).text();
  const [header, ...lines] = parseCSV(text);
  return lines
    .filter((cells) => cells.length === header.length)
    .map((cells) => {
      const row = {};
      header.forEach((col, i) => { row[col] = cells[i]; });
      row.in_role = row.in_role === "true";
      row.first_run = row.first_run === "true";
      return row;
    });
}

// RFC 4180 CSV: quoted fields may hold commas, doubled quotes and newlines.
export function parseCSV(text) {
  const rows = [];
  let row = [], field = "", inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += c;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  return rows;
}

// ------------------------------------------------------------------ dates (all UTC 'YYYY-MM-DD')
const DAY_MS = 86400000;
export const dayNumber = (d) => Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)) / DAY_MS;
export const daysBetween = (a, b) => dayNumber(b) - dayNumber(a);
export const addDays = (d, n) => new Date((dayNumber(d) + n) * DAY_MS).toISOString().slice(0, 10);
export function dateRange(from, to) {
  const out = [];
  for (let d = from; d <= to; d = addDays(d, 1)) out.push(d);
  return out;
}

// The last run in the history: the latest date any posting was listed or removed.
export function lastRunDate(rows) {
  let last = "";
  for (const r of rows) {
    if (r.last_seen > last) last = r.last_seen;
    if (r.removed_date > last) last = r.removed_date;
  }
  return last;
}
export function firstRunDate(rows) {
  let first = "9999";
  for (const r of rows) if (r.first_seen < first) first = r.first_seen;
  return first;
}

const dayFmt = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const dayFmtY = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
const dayFmtW = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
const asDate = (d) => new Date(dayNumber(d) * DAY_MS);
export const fmtDay = (d) => (d ? dayFmt.format(asDate(d)) : "");
export const fmtDayYear = (d) => (d ? dayFmtY.format(asDate(d)) : "");
export const fmtWeekday = (d) => (d ? dayFmtW.format(asDate(d)) : "");

export function fmtRunTime(iso) {
  const t = new Date(iso);
  const local = t.toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric",
                                            year: "numeric", hour: "numeric", minute: "2-digit",
                                            timeZoneName: "short" });
  const utc = t.toLocaleString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" });
  return { local, utc: `${utc} UTC` };
}

export function relTime(iso) {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  return `${days} days ago`;
}

// ------------------------------------------------------------------ numbers
const nf = new Intl.NumberFormat("en-US");
export const fmt = (n) => nf.format(n);
export const pct = (x, digits = 0) => `${(x * 100).toFixed(digits)}%`;
export const plural = (n, one, many = `${one}s`) => `${fmt(n)} ${n === 1 ? one : many}`;
export function median(values) {
  if (!values.length) return null;
  const s = [...values].sort((a, b) => a - b);
  const mid = s.length >> 1;
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

// ------------------------------------------------------------------ shortlist (this browser only)
const SHORTLIST_KEY = "jw-shortlist";
export const shortlist = {
  all() { return store(SHORTLIST_KEY) || {}; },
  has(id) { return Boolean(this.all()[id]); },
  toggle(row) {
    const list = this.all();
    if (list[row.posting_id]) delete list[row.posting_id];
    else list[row.posting_id] = { title: row.title, employer: row.employer, url: row.url,
                                  location: row.location, starred: new Date().toISOString() };
    store(SHORTLIST_KEY, list);
    return Boolean(list[row.posting_id]);
  },
};

export function errorBox(err) {
  return h("div", { class: "error-box", role: "alert" },
    h("strong", { text: "The data could not be loaded. " }),
    h("span", { text: navigator.onLine
      ? `(${err.message}) Try reloading the page.`
      : "You're offline and this device has not loaded the data before." }));
}
