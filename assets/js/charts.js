// Small chart kit for the Market page: column chart, ranked bars, segmented bar,
// one shared tooltip, and a table view for every chart. Colors come from CSS
// tokens (var(--all), var(--role)) so light/dark switch without re-rendering.
import { h, fmt } from "./common.js";

const NS = "http://www.w3.org/2000/svg";
function s(tag, attrs = {}) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

// ------------------------------------------------------------------ tooltip
let tipEl = null;
function tip() {
  if (!tipEl) {
    tipEl = h("div", { class: "tooltip", hidden: true });
    document.body.append(tipEl);
  }
  return tipEl;
}
// rows: [{ value, label, color }]
export function showTip(x, y, head, rows) {
  const t = tip();
  t.replaceChildren(
    h("div", { class: "tt-head", text: head }),
    ...rows.map((r) => h("div", { class: "tt-row" },
      r.color ? h("span", { class: "tt-key", style: `background:${r.color}` }) : null,
      h("strong", { text: r.value }),
      h("span", { text: r.label || "" }))));
  t.hidden = false;
  const pad = 14, w = t.offsetWidth, ht = t.offsetHeight;
  let left = x + pad, top = y - ht - pad;
  if (left + w > innerWidth - 8) left = x - w - pad;
  if (top < 8) top = y + pad;
  t.style.left = `${Math.max(8, left)}px`;
  t.style.top = `${top}px`;
}
export function hideTip() { if (tipEl) tipEl.hidden = true; }
addEventListener("scroll", hideTip, { passive: true });

// ------------------------------------------------------------------ re-render on resize
const live = new Set();
let resizeTimer;
addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => live.forEach((fn) => fn()), 150);
});
function mount(container, draw) {
  const run = () => {
    if (!container.isConnected) { live.delete(run); return; }
    container.replaceChildren();
    draw(Math.max(240, container.clientWidth));
  };
  run();
  live.add(run);
}

// Round axis steps for counts: 1, 2, 5, 10, 20, 25, 50, ...
function niceTicks(max, target = 4) {
  if (max <= 0) return [0, 1];
  const raw = max / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = Math.max(1, [1, 2, 2.5, 5, 10].map((m) => m * mag).find((v) => v >= raw));
  const top = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = 0; v <= top + 1e-9; v += step) ticks.push(Math.round(v * 100) / 100);
  return ticks;
}
const compact = (n) => (n >= 10000 ? `${Math.round(n / 1000)}K` : fmt(n));

function roundedTop(x, y, w, hgt, r) {
  r = Math.min(r, w / 2, hgt);
  return `M${x},${y + hgt}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + hgt}Z`;
}

// ------------------------------------------------------------------ column chart
// labels: x categories; values: numbers; color: CSS color; name: series name
// opts.ref = { at: <fractional index>, label } draws a reference line (e.g. a median)
export function columns(container, { labels, values, color, name, fmtLabel = String, height = 190,
                                     ref = null, labelPeak = true, ariaLabel = "" }) {
  mount(container, (W) => {
    const m = { l: 44, r: 10, t: 22, b: 28 };
    const pw = W - m.l - m.r, ph = height - m.t - m.b;
    const n = labels.length;
    const ticks = niceTicks(Math.max(...values, 0));
    const yMax = ticks[ticks.length - 1];
    const y = (v) => m.t + ph - (v / yMax) * ph;
    const band = pw / Math.max(n, 1);
    const bw = Math.max(1, Math.min(24, band * 0.7));
    const svg = s("svg", { width: W, height, viewBox: `0 0 ${W} ${height}`, role: "img",
                           "aria-label": ariaLabel || name });

    for (const t of ticks) {
      const gy = y(t);
      svg.append(s("line", { x1: m.l, x2: W - m.r, y1: gy, y2: gy, class: t === 0 ? "baseline" : "gridline" }));
      const lab = s("text", { x: m.l - 8, y: gy + 4, "text-anchor": "end", class: "tick" });
      lab.textContent = compact(t);
      svg.append(lab);
    }
    // x labels: as many as fit without colliding, always the last one
    const every = Math.max(1, Math.ceil(52 / band));
    labels.forEach((lab, i) => {
      if (i % every !== 0 && i !== n - 1) return;
      if (i !== n - 1 && n - 1 - i < every) return;  // keep clear of the last label
      const t = s("text", { x: m.l + band * (i + 0.5), y: height - 8, "text-anchor": "middle", class: "tick" });
      t.textContent = fmtLabel(lab);
      svg.append(t);
    });

    const peak = values.indexOf(Math.max(...values));
    values.forEach((v, i) => {
      const cx = m.l + band * (i + 0.5);
      const hit = s("rect", { x: m.l + band * i, y: m.t, width: band, height: ph, class: "bar-hit" });
      const bar = s("path", { d: roundedTop(cx - bw / 2, y(v), bw, Math.max(0, y(0) - y(v)), 4),
                              class: "bar", style: `fill:${color}` });
      const enter = (e) => {
        bar.classList.add("hover");
        showTip(e.clientX, e.clientY, fmtLabel(labels[i]), [{ value: fmt(v), label: name, color }]);
      };
      hit.addEventListener("pointermove", enter);
      hit.addEventListener("pointerleave", () => { bar.classList.remove("hover"); hideTip(); });
      svg.append(bar, hit);
      if (labelPeak && v > 0 && (i === peak || i === n - 1) && bw >= 6) {
        const t = s("text", { x: cx, y: y(v) - 6, "text-anchor": "middle", class: "tick" });
        t.textContent = fmt(v);
        svg.append(t);
      }
    });

    if (ref) {
      const rx = m.l + band * (ref.at + 0.5);
      svg.append(s("line", { x1: rx, x2: rx, y1: m.t - 6, y2: m.t + ph, class: "refline" }));
      const t = s("text", { x: rx + 6, y: m.t + 4, class: "reflabel",
                            "text-anchor": rx > W - 140 ? "end" : "start" });
      if (rx > W - 140) t.setAttribute("x", rx - 6);
      t.textContent = ref.label;
      svg.append(t);
    }
    container.append(svg);
  });
}

// ------------------------------------------------------------------ ranked horizontal bars
// items: [{ label, value, extra: [{label, value}] }]
export function hbars(container, { items, color, name }) {
  mount(container, () => {
    const max = Math.max(...items.map((d) => d.value), 1);
    const grid = h("div", { class: "hbars", role: "list" });
    for (const d of items) {
      const fill = h("div", { class: "fill",
                              style: `background:${color};width:calc((100% - 64px) * ${d.value / max})` });
      const row = [
        h("div", { class: "lbl", title: d.label, text: d.label }),
        h("div", { class: "track" }, fill, h("span", { class: "val", text: fmt(d.value) })),
      ];
      const enter = (e) => showTip(e.clientX, e.clientY, d.label,
        [{ value: fmt(d.value), label: name, color }, ...(d.extra || [])]);
      for (const cell of row) {
        cell.addEventListener("pointermove", enter);
        cell.addEventListener("pointerleave", hideTip);
      }
      grid.append(...row);
    }
    container.append(grid);
  });
}

// ------------------------------------------------------------------ segmented bars (part of a whole)
// rows: [{ label, note, parts: [{ name, value, fill, ink }] }]
export function segmented(container, { rows, legend }) {
  mount(container, () => {
    const wrap = h("div", { class: "seg-rows" });
    for (const row of rows) {
      const total = row.parts.reduce((a, p) => a + p.value, 0);
      const bar = h("div", { class: "segbar", role: "img",
        "aria-label": `${row.label}: ` + row.parts.map((p) => `${p.name} ${fmt(p.value)}`).join(", ") });
      for (const p of row.parts) {
        if (!p.value) continue;
        const share = p.value / total;
        const part = h("div", { class: "part", style: `flex:${p.value} 1 0;background:${p.fill};color:${p.ink}` },
          `${Math.round(share * 100)}%`);
        part.addEventListener("pointermove", (e) => showTip(e.clientX, e.clientY, row.label,
          [{ value: `${fmt(p.value)} (${(share * 100).toFixed(1)}%)`, label: p.name, color: p.fill }]));
        part.addEventListener("pointerleave", hideTip);
        bar.append(part);
      }
      wrap.append(h("div", { class: "seg-row" },
        h("div", { class: "seg-label" }, row.label, h("span", { text: row.note || "" })), bar));
    }
    wrap.append(h("div", { class: "legend" },
      legend.map((l) => h("span", {}, h("span", { class: "key", style: `background:${l.fill}` }), l.name))));
    container.append(wrap);
    // A label that does not fit its block is dropped (the value stays in the tooltip and table).
    requestAnimationFrame(() => wrap.querySelectorAll(".part").forEach((p) => {
      if (p.scrollWidth > p.clientWidth + 1) p.textContent = "";
    }));
  });
}

// ------------------------------------------------------------------ table view twin
export function tableView(columnsSpec, rows, summary = "Show the numbers") {
  return h("details", { class: "table-view" },
    h("summary", { text: summary }),
    h("div", { class: "scroll" },
      h("table", {},
        h("thead", {}, h("tr", {}, columnsSpec.map((c) => h("th", { class: c.num ? "n" : null, text: c.label })))),
        h("tbody", {}, rows.map((r) => h("tr", {},
          columnsSpec.map((c) => h("td", { class: c.num ? "n" : null,
                                           text: c.num && typeof r[c.key] === "number" ? fmt(r[c.key]) : r[c.key] }))))))));
}

export function empty(text) {
  return h("div", { class: "chart-empty", text });
}
