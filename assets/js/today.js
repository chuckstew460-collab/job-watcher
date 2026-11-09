// Today page: the latest run — time, source status, the four counts, and the
// postings that were new or removed in that run.
import { initChrome, h, icon, loadStatus, loadHistory, fmt, fmtRunTime, relTime, fmtWeekday,
         fmtDay, plural, errorBox } from "./common.js";

initChrome("index.html");
const app = document.getElementById("app");

try {
  const [status, rows] = await Promise.all([loadStatus(), loadHistory()]);
  render(status, rows);
} catch (err) {
  app.replaceChildren(errorBox(err));
}

function tile(label, value, sub) {
  return h("div", { class: "card tile" },
    h("div", { class: "label", text: label }),
    h("div", { class: "value", text: value }),
    h("div", { class: "sub" }, sub));
}

function roleSub(n) {
  return [h("span", { class: "dot role" }), `${fmt(n)} in your role`];
}

function postingItem(r, removed) {
  return h("li", { class: `posting${r.in_role ? " in-role" : ""}` },
    h("div", { class: "title" },
      h("a", { href: r.url, target: "_blank", rel: "noopener", text: r.title })),
    h("div", { class: "meta" },
      r.employer,
      r.location ? [h("span", { class: "sep", text: "·" }), r.location] : null,
      removed ? [h("span", { class: "sep", text: "·" }), `first seen ${fmtDay(r.first_seen)}`] : null),
    h("div", { class: "side" }, r.in_role ? h("span", { class: "chip" },
      h("span", { class: "dot role" }), "Your role") : null));
}

function postingList(title, list, emptyText, removed) {
  const role = list.filter((r) => r.in_role);
  let scope = "all";
  let limit = 40;
  const body = h("div");
  const allBtn = h("button", { type: "button", "aria-pressed": "true" }, `All ${fmt(list.length)}`);
  const roleBtn = h("button", { type: "button", "aria-pressed": "false" },
    h("span", { class: "dot role" }), `Your role ${fmt(role.length)}`);
  const paint = () => {
    allBtn.setAttribute("aria-pressed", String(scope === "all"));
    roleBtn.setAttribute("aria-pressed", String(scope === "role"));
    const shown = scope === "all" ? list : role;
    if (!shown.length) {
      body.replaceChildren(h("p", { class: "empty", text: scope === "all" ? emptyText
        : "None in your role in this run." }));
      return;
    }
    const ul = h("ul", { class: "postings" }, shown.slice(0, limit).map((r) => postingItem(r, removed)));
    const more = shown.length > limit
      ? h("button", { class: "more-btn", type: "button",
                      onclick: () => { limit = Infinity; paint(); } }, `Show all ${fmt(shown.length)}`)
      : null;
    body.replaceChildren(ul, more);
  };
  allBtn.addEventListener("click", () => { scope = "all"; limit = 40; paint(); });
  roleBtn.addEventListener("click", () => { scope = "role"; limit = 40; paint(); });
  paint();
  return h("section", { class: "card", "aria-label": title },
    h("div", { class: "list-head" },
      h("h2", { text: `${title} (${fmt(list.length)})` }),
      h("div", { class: "segmented", role: "group", "aria-label": `${title}: which postings` }, allBtn, roleBtn)),
    body);
}

function render(status, rows) {
  const day = status.run_date;
  const when = fmtRunTime(status.run_time);
  const ok = status.sources.filter((s) => s.ok).length;
  const byRole = (a, b) => (b.in_role - a.in_role) || a.employer.localeCompare(b.employer)
    || a.title.localeCompare(b.title);
  const added = rows.filter((r) => r.first_seen === day && !r.first_run).sort(byRole);
  const removed = rows.filter((r) => r.removed_date === day).sort(byRole);
  const firstRunToday = rows.filter((r) => r.first_seen === day && r.first_run).length;

  const head = h("div", { class: "page-head" },
    h("p", { class: "eyebrow", text: `Today · ${fmtWeekday(day)}` }),
    h("h1", { text: `What changed in the last run` }),
    h("p", { class: "lede" },
      "Last run ", h("strong", { text: when.local }), ` (${when.utc}), ${relTime(status.run_time)}. `,
      `${ok} of ${status.sources.length} job boards answered. `,
      "Postings in your role (financial or data analyst) are marked ",
      h("span", { class: "dot role" }), "."));

  const tiles = h("div", { class: "tiles" },
    tile("Days with a successful run", fmt(status.days_with_success),
      [`since ${fmtDay(status.first_run_date)}`]),
    tile("Open postings", fmt(status.open), roleSub(status.in_role.open)),
    tile("New today", fmt(status.new_today), roleSub(status.in_role.new_today)),
    tile("Removed today", fmt(status.removed_today), roleSub(status.in_role.removed_today)));

  const sources = h("section", { class: "card section-gap", "aria-label": "Job boards" },
    h("div", { class: "list-head" },
      h("h2", { text: "Job boards in the last run" }),
      h("span", { class: "muted small", text: `${ok} ok · ${status.sources.length - ok} failed` })),
    h("p", { class: "muted small", style: "margin:0 0 8px",
             text: "A board that fails writes no raw file that day, so none of its postings are marked removed." }),
    h("div", { class: "sources" }, status.sources.map((s) => h("div", { class: "source" },
      icon(s.ok ? "check" : "cross", `state-icon ${s.ok ? "ok" : "fail"}`),
      h("div", { style: "min-width:0" },
        h("span", { class: "name", text: s.employer }),
        h("span", { class: "ats", text: s.ats })),
      h("span", { class: "count", text: s.ok ? fmt(s.count) : "failed",
                  title: s.ok ? `${fmt(s.count)} postings listed` : s.error }),
      s.ok ? null : h("div", { class: "err", text: s.error })))));

  const newEmpty = firstRunToday
    ? `No new postings: this was the first run for ${firstRunToday === rows.length ? "every board" : "some boards"}, `
      + `so their ${plural(firstRunToday, "posting")} count as already open (first run), not new.`
    : "No postings were first seen in this run.";
  const lists = h("div", { class: "two-col section-gap" },
    postingList("New postings", added, newEmpty, false),
    postingList("Removed postings", removed, "No postings were removed in this run.", true));

  app.replaceChildren(head, tiles, sources, lists);
}
