// Browse page: open postings with a role switch, filters (employer, location,
// days open), title search, sort by first-seen date, apply links, and a
// starred shortlist saved in this browser.
import { initChrome, h, icon, loadHistory, fmt, fmtDay, daysBetween, lastRunDate, shortlist,
         plural, errorBox } from "./common.js";

initChrome("browse.html");
const app = document.getElementById("app");
const PAGE = 60;

const state = { scope: "role", q: "", employer: "", location: "", days: "any", sort: "newest", limit: PAGE };


function daysOpen(r, last) {
  return daysBetween(r.first_seen, r.status === "removed" ? r.removed_date : last);
}

function daysChip(r, last) {
  const d = daysOpen(r, last);
  if (r.status === "removed") return h("span", { class: "chip removed", text: `Removed ${fmtDay(r.removed_date)}` });
  if (r.first_run) return h("span", { class: "chip", title: "Already open when the tool started watching this board",
                                      text: `≥ ${plural(d, "day")}` });
  return h("span", { class: "chip", text: d === 0 ? "New today" : plural(d, "day") });
}

const DAY_FILTERS = {
  any: () => true,
  "0": (d) => d === 0,
  "7": (d) => d <= 7,
  "30": (d) => d <= 30,
  over30: (d) => d > 30,
};

function render(rows) {
  const last = lastRunDate(rows);
  const open = rows.filter((r) => r.status === "open");
  const byId = new Map(rows.map((r) => [r.posting_id, r]));
  const employers = [...new Set(open.map((r) => r.employer))].sort();
  const locCounts = new Map();
  for (const r of open) if (r.location) locCounts.set(r.location, (locCounts.get(r.location) || 0) + 1);
  const locations = [...locCounts].sort((a, b) => b[1] - a[1]).map(([l]) => l);

  // ------------------------------------------------------------ controls
  const scopeBtns = {
    role: h("button", { type: "button" }, h("span", { class: "dot role" }),
      `Your role ${fmt(open.filter((r) => r.in_role).length)}`),
    all: h("button", { type: "button" }, h("span", { class: "dot all" }), `All postings ${fmt(open.length)}`),
    starred: h("button", { type: "button" }, icon("star", "state-icon"), h("span", { id: "star-count" })),
  };
  for (const [key, btn] of Object.entries(scopeBtns)) {
    btn.addEventListener("click", () => { state.scope = key; state.limit = PAGE; paint(); });
  }
  const search = h("input", { type: "search", id: "q", placeholder: "e.g. FP&A, SQL, intern", autocomplete: "off" });
  search.addEventListener("input", () => { state.q = search.value.trim().toLowerCase(); state.limit = PAGE; paint(); });
  const empSel = h("select", { id: "emp" }, h("option", { value: "", text: "All employers" }),
    employers.map((e) => h("option", { value: e, text: e })));
  empSel.addEventListener("change", () => { state.employer = empSel.value; state.limit = PAGE; paint(); });
  const locInput = h("input", { type: "search", id: "loc", list: "loc-list", placeholder: "Any location",
                                autocomplete: "off" });
  const locList = h("datalist", { id: "loc-list" }, locations.slice(0, 400).map((l) => h("option", { value: l })));
  locInput.addEventListener("input", () => { state.location = locInput.value.trim().toLowerCase(); state.limit = PAGE; paint(); });
  const daysSel = h("select", { id: "days" },
    h("option", { value: "any", text: "Any" }),
    h("option", { value: "0", text: "New today (0 days)" }),
    h("option", { value: "7", text: "Up to 7 days" }),
    h("option", { value: "30", text: "Up to 30 days" }),
    h("option", { value: "over30", text: "More than 30 days" }));
  daysSel.addEventListener("change", () => { state.days = daysSel.value; state.limit = PAGE; paint(); });
  const sortSel = h("select", { id: "sort" },
    h("option", { value: "newest", text: "Newest first" }),
    h("option", { value: "oldest", text: "Oldest first" }));
  sortSel.addEventListener("change", () => { state.sort = sortSel.value; paint(); });
  const clear = h("button", { type: "button", class: "more-btn", style: "margin:0" }, "Clear filters");
  clear.addEventListener("click", () => {
    Object.assign(state, { q: "", employer: "", location: "", days: "any", limit: PAGE });
    search.value = ""; empSel.value = ""; locInput.value = ""; daysSel.value = "any";
    paint();
  });

  const field = (label, id, control, cls) => h("div", { class: `field ${cls}` },
    h("label", { for: id, text: label }), control);

  const count = h("p", { class: "result-count", role: "status" });
  const list = h("ul", { class: "postings" });
  const more = h("div");

  app.replaceChildren(
    h("div", { class: "page-head" },
      h("p", { class: "eyebrow", text: `Browse · as of ${fmtDay(last)}` }),
      h("h1", { text: "Open postings" }),
      h("p", { class: "lede", text: `${fmt(open.length)} postings are open at ${employers.length} employers. `
        + "Star a posting to keep it on your shortlist; the shortlist is saved in this browser." })),
    h("div", { class: "card" },
      h("div", { class: "segmented", role: "group", "aria-label": "Which postings", style: "margin-bottom:14px" },
        Object.values(scopeBtns)),
      h("div", { class: "controls" },
        field("Search titles", "q", search, "grow"),
        field("Employer", "emp", empSel, "w-emp"),
        field("Location", "loc", h("div", { style: "display:contents" }, locInput, locList), "w-loc"),
        field("Days open", "days", daysSel, "w-days"),
        field("Sort by first seen", "sort", sortSel, "w-sort"))),
    h("div", { class: "toolbar" }, count, clear),
    h("section", { class: "card browse", "aria-label": "Postings" }, list, more));

  // ------------------------------------------------------------ filtering
  function source() {
    if (state.scope === "starred") {
      const saved = shortlist.all();
      return Object.entries(saved).map(([id, snap]) => byId.get(id) || {
        posting_id: id, title: snap.title, employer: snap.employer, url: snap.url, location: snap.location || "",
        department: "", first_seen: last, status: "removed", removed_date: last, first_run: false, in_role: false,
        gone: true,
      });
    }
    return state.scope === "role" ? open.filter((r) => r.in_role) : open;
  }

  function paint() {
    for (const [key, btn] of Object.entries(scopeBtns)) btn.setAttribute("aria-pressed", String(state.scope === key));
    document.getElementById("star-count").textContent = `Shortlist ${fmt(Object.keys(shortlist.all()).length)}`;
    const keepDays = DAY_FILTERS[state.days];
    const matches = source().filter((r) =>
      (!state.q || r.title.toLowerCase().includes(state.q))
      && (!state.employer || r.employer === state.employer)
      && (!state.location || r.location.toLowerCase().includes(state.location))
      && keepDays(daysOpen(r, last)));
    const dir = state.sort === "newest" ? -1 : 1;
    matches.sort((a, b) => dir * a.first_seen.localeCompare(b.first_seen)
      || a.employer.localeCompare(b.employer) || a.title.localeCompare(b.title));

    const what = state.scope === "starred" ? "starred" : state.scope === "role" ? "open in your role" : "open";
    count.textContent = `${plural(matches.length, "posting")} ${what}`;
    list.replaceChildren(...matches.slice(0, state.limit).map((r) => item(r, last)));
    if (!matches.length) {
      list.replaceChildren(h("li", { class: "empty", text: state.scope === "starred"
        ? "No starred postings match. Tap the star on any posting to add it to your shortlist."
        : "No open postings match these filters." }));
    }
    more.replaceChildren(matches.length > state.limit
      ? h("button", { type: "button", class: "more-btn",
                      onclick: () => { state.limit += PAGE * 4; paint(); } },
          `Show more (${fmt(matches.length - state.limit)} left)`)
      : "");
  }

  function item(r, lastDay) {
    const starred = shortlist.has(r.posting_id);
    const star = h("button", { type: "button", class: "star-btn", "aria-pressed": String(starred),
                               "aria-label": `${starred ? "Remove" : "Add"} ${r.title} ${starred ? "from" : "to"} shortlist`,
                               title: starred ? "Remove from shortlist" : "Add to shortlist" },
      icon(starred ? "star" : "starOutline"));
    star.addEventListener("click", () => {
      const on = shortlist.toggle(r);
      star.setAttribute("aria-pressed", String(on));
      star.replaceChildren(icon(on ? "star" : "starOutline"));
      star.title = on ? "Remove from shortlist" : "Add to shortlist";
      document.getElementById("star-count").textContent = `Shortlist ${fmt(Object.keys(shortlist.all()).length)}`;
    });
    const seen = r.gone ? "no longer in the history"
      : r.first_run ? `listed since watching began ${fmtDay(r.first_seen)}` : `first seen ${fmtDay(r.first_seen)}`;
    return h("li", { class: `posting${r.in_role ? " in-role" : ""}` },
      h("div", { class: "star-cell" }, star),
      h("div", { class: "title" }, h("a", { href: r.url, target: "_blank", rel: "noopener", text: r.title })),
      h("div", { class: "meta" },
        h("strong", { style: "font-weight:500;color:var(--ink)", text: r.employer }),
        r.location ? [h("span", { class: "sep", text: "·" }), r.location] : null,
        r.department ? [h("span", { class: "sep", text: "·" }), r.department] : null,
        h("span", { class: "sep", text: "·" }), seen,
        r.posted_date ? [h("span", { class: "sep", text: "·" }), `posted ${fmtDay(r.posted_date)}`] : null),
      h("div", { class: "side" },
        r.gone ? null : daysChip(r, lastDay),
        h("a", { class: "apply", href: r.url, target: "_blank", rel: "noopener" }, "Apply ", icon("external", "state-icon"))));
  }

  paint();
}

// Load last, after every constant above is initialised.
try {
  render(await loadHistory());
} catch (err) {
  app.replaceChildren(errorBox(err));
}
