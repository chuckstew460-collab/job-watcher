// Market page: a report on the history the pipeline has built. Every number
// is computed here, in the browser, from data/history.csv, so the page
// changes as the history grows.
//
// Definitions (first-run postings were already open when the tool started
// watching their board, so their start date is unknown):
//   1. new per day      first_seen = day, first_run = false (all, and in role)
//   2. removed per day  removed_date = day
//   3. open by employer status = open
//   4. days open        removed, not first-run: removed_date - first_seen; median
//   5. gone in 7 days   not first-run, first_seen <= last run - 7 days:
//                       share with removed_date - first_seen <= 7
//   6. top locations    status = open, grouped by location
import { initChrome, h, loadHistory, fmt, pct, fmtDay, fmtDayYear, dateRange, daysBetween, addDays,
         lastRunDate, firstRunDate, median, plural, errorBox } from "./common.js";
import { columns, hbars, segmented, tableView, empty } from "./charts.js";

initChrome("market.html");
const app = document.getElementById("app");


const ALL = "var(--all)", ROLE = "var(--role)";

function section(n, id, finding, explain, ...body) {
  return h("section", { class: "card report-section", id, "aria-labelledby": `${id}-h` },
    h("span", { class: "sec-num", text: `${String(n).padStart(2, "0")} · ${SECTION_NAMES[n - 1]}` }),
    h("h2", { class: "finding", id: `${id}-h`, text: finding }),
    h("p", { class: "explain", text: explain }),
    ...body);
}
const SECTION_NAMES = ["New postings per day", "Removed postings per day", "Open postings by employer",
                       "Days open", "Removed within seven days", "Top locations"];

function chartBox(title, color) {
  const box = h("div", { class: "chart" });
  return [h("div", { class: "chart-title" }, h("span", { class: "key", style: `background:${color}` }), title), box];
}

function countBy(rows, key) {
  const m = new Map();
  for (const r of rows) m.set(r[key], (m.get(r[key]) || 0) + 1);
  return m;
}

function render(rows) {
  const first = firstRunDate(rows), last = lastRunDate(rows);
  const days = dateRange(first, last);
  const watched = days.length;
  const fresh = rows.filter((r) => !r.first_run);          // start date known
  const open = rows.filter((r) => r.status === "open");
  const removed = rows.filter((r) => r.status === "removed");
  const roleRows = rows.filter((r) => r.in_role);

  const head = h("div", { class: "page-head" },
    h("p", { class: "eyebrow", text: `Market · ${fmtDayYear(first)} to ${fmtDayYear(last)}` }),
    h("h1", { text: "What the job boards did while we watched" }),
    h("p", { class: "lede", text: `A report on ${fmt(rows.length)} postings tracked over ${plural(watched, "day")} `
      + `at ${new Set(rows.map((r) => r.employer)).size} employers. Every number below is computed in your `
      + "browser from data/history.csv, so the page updates as the history grows. Postings that were already open "
      + "on a board's first day of watching (first-run postings) have no known start date and are left out "
      + "where noted." }),
    h("nav", { class: "toc", "aria-label": "Sections" },
      SECTION_NAMES.map((name, i) => h("a", { href: `#s${i + 1}`, text: name }))));

  // ------------------------------------------------------------ 1. new per day
  const newAll = countBy(fresh, "first_seen");
  const newRole = countBy(fresh.filter((r) => r.in_role), "first_seen");
  const series1 = days.map((d) => ({ day: d, all: newAll.get(d) || 0, role: newRole.get(d) || 0 }));
  const afterFirst = series1.slice(1);
  const totNew = afterFirst.reduce((a, d) => a + d.all, 0);
  const totNewRole = afterFirst.reduce((a, d) => a + d.role, 0);
  let s1;
  if (!afterFirst.length) {
    s1 = section(1, "s1", "No new postings yet: the first day is the baseline",
      `The tool first ran on ${fmtDay(first)}. Every posting listed that day counts as already open (first run), `
      + "so new postings start appearing from the second day.",
      empty("The first new postings will show here after the next daily run."));
  } else {
    const avg = totNew / afterFirst.length, avgRole = totNewRole / afterFirst.length;
    const peak = afterFirst.reduce((a, b) => (b.all > a.all ? b : a));
    const [t1, c1] = chartBox("All postings", ALL), [t2, c2] = chartBox("Your role (financial / data analyst)", ROLE);
    s1 = section(1, "s1",
      `About ${fmt(Math.round(avg))} new postings appear each day, ${avgRole < 1 ? avgRole.toFixed(1) : fmt(Math.round(avgRole))} of them in your role`,
      `Postings first seen on each day, leaving out first-run postings. Over the ${plural(afterFirst.length, "day")} `
      + `after the first run (${fmtDay(first)}), the boards added ${fmt(totNew)} new postings, ${fmt(totNewRole)} `
      + `in your role. The busiest day was ${fmtDay(peak.day)} with ${fmt(peak.all)}. The first day shows zero `
      + "because everything listed then was already open. The two charts have their own scales.",
      h("div", { class: "multiples" }, h("div", {}, t1, c1), h("div", {}, t2, c2)),
      tableView([{ key: "date", label: "Date" }, { key: "all", label: "New, all postings", num: true },
                 { key: "role", label: "New, your role", num: true }],
                series1.map((d) => ({ date: d.day, all: d.all, role: d.role }))));
    queueMicrotask(() => {
      columns(c1, { labels: days, values: series1.map((d) => d.all), color: ALL, name: "new postings", fmtLabel: fmtDay });
      columns(c2, { labels: days, values: series1.map((d) => d.role), color: ROLE, name: "new in your role", fmtLabel: fmtDay });
    });
  }

  // ------------------------------------------------------------ 2. removed per day
  const remAll = countBy(removed, "removed_date");
  const remRole = countBy(removed.filter((r) => r.in_role), "removed_date");
  const series2 = days.map((d) => ({ day: d, all: remAll.get(d) || 0, role: remRole.get(d) || 0 }));
  const totRem = removed.length, totRemRole = removed.filter((r) => r.in_role).length;
  let s2;
  if (!totRem) {
    s2 = section(2, "s2", "No postings have been removed yet",
      "A posting is removed on the first day its board answers without listing it. That needs at least two runs.",
      empty("Removed postings will show here once a board drops a listing."));
  } else {
    const span = Math.max(1, watched - 1);
    const peak = series2.reduce((a, b) => (b.all > a.all ? b : a));
    const [t1, c1] = chartBox("All postings", ALL), [t2, c2] = chartBox("Your role (financial / data analyst)", ROLE);
    s2 = section(2, "s2",
      `About ${fmt(Math.round(totRem / span))} postings come down each day, ${fmt(totRemRole)} in your role so far`,
      `Postings with a removed date on each day: the board answered that day but no longer listed them. `
      + `${fmt(totRem)} postings are currently removed (a posting that is listed again reopens and loses its `
      + `removed date). The most removals came on ${fmtDay(peak.day)}, with ${fmt(peak.all)}.`,
      h("div", { class: "multiples" }, h("div", {}, t1, c1), h("div", {}, t2, c2)),
      tableView([{ key: "date", label: "Date" }, { key: "all", label: "Removed, all postings", num: true },
                 { key: "role", label: "Removed, your role", num: true }],
                series2.map((d) => ({ date: d.day, all: d.all, role: d.role }))));
    queueMicrotask(() => {
      columns(c1, { labels: days, values: series2.map((d) => d.all), color: ALL, name: "removed", fmtLabel: fmtDay });
      columns(c2, { labels: days, values: series2.map((d) => d.role), color: ROLE, name: "removed in your role", fmtLabel: fmtDay });
    });
  }

  // ------------------------------------------------------------ 3. open per employer
  const empAll = countBy(open, "employer");
  const empRole = countBy(open.filter((r) => r.in_role), "employer");
  const employers = [...empAll].map(([employer, n]) => ({ employer, n, role: empRole.get(employer) || 0 }))
    .sort((a, b) => b.n - a.n || a.employer.localeCompare(b.employer));
  const topEmp = employers[0];
  const topRoleEmp = [...employers].sort((a, b) => b.role - a.role)[0];
  const c3 = h("div", { class: "chart" });
  const s3 = section(3, "s3",
    `${topEmp.employer} has the most open postings: ${fmt(topEmp.n)} of ${fmt(open.length)}`,
    `Open postings at each employer as of the last run (${fmtDay(last)}). ${topEmp.employer} alone lists `
    + `${pct(topEmp.n / open.length)} of everything open. In your role, ${topRoleEmp.employer} leads with `
    + `${fmt(topRoleEmp.role)} open postings. JPMorgan Chase is read with the search term "analyst" because its `
    + "full board lists more than 5,000 postings; hover a bar for the in-role count.",
    c3,
    tableView([{ key: "employer", label: "Employer" }, { key: "n", label: "Open postings", num: true },
               { key: "role", label: "Open in your role", num: true }], employers));
  queueMicrotask(() => hbars(c3, {
    items: employers.map((e) => ({ label: e.employer, value: e.n,
      extra: [{ value: fmt(e.role), label: "in your role", color: ROLE }] })),
    color: ALL, name: "open postings" }));

  // ------------------------------------------------------------ 4. days open
  const durations = removed.filter((r) => !r.first_run).map((r) => daysBetween(r.first_seen, r.removed_date));
  let s4;
  if (!durations.length) {
    s4 = section(4, "s4", "No posting first seen by the tool has closed yet",
      "Days open is measured for removed postings that are not first-run postings: removed date minus "
      + "first-seen date. It needs a posting to appear after the first run and later come down.",
      empty("The median days open will show here once a new posting is removed."));
  } else {
    const med = median(durations);
    const maxD = Math.max(...durations);
    const bins = Array.from({ length: maxD }, (_, i) => i + 1);
    const hist = countBy(durations.map((d) => ({ d })), "d");
    const roleDur = removed.filter((r) => !r.first_run && r.in_role).map((r) => daysBetween(r.first_seen, r.removed_date));
    const c4 = h("div", { class: "chart" });
    s4 = section(4, "s4",
      `Postings that closed stayed up a median of ${plural(med, "day")}`,
      `For the ${fmt(durations.length)} removed postings that are not first-run postings, days open is the `
      + `removed date minus the first-seen date. The median is ${plural(med, "day")}`
      + (roleDur.length ? ` (${plural(median(roleDur), "day")} for the ${fmt(roleDur.length)} in your role)` : "")
      + `. The history is ${plural(watched, "day")} long, so no posting can show more than `
      + `${plural(watched - 1, "day")} yet; the median will rise as longer-lived postings close.`,
      h("div", { class: "chart-title" }, h("span", { class: "key", style: `background:${ALL}` }),
        "Removed postings by days open"),
      c4,
      tableView([{ key: "days", label: "Days open", num: true }, { key: "n", label: "Removed postings", num: true }],
                bins.map((b) => ({ days: b, n: hist.get(b) || 0 }))));
    queueMicrotask(() => columns(c4, {
      labels: bins, values: bins.map((b) => hist.get(b) || 0), color: ALL, name: "postings",
      fmtLabel: (b) => `${b}d`, ref: { at: med - 1, label: `median ${med}` },
      ariaLabel: `Histogram of days open; median ${med} days` }));
  }

  // ------------------------------------------------------------ 5. removed within seven days
  const cutoff = addDays(last, -7);
  const shares = (subset) => {
    const eligible = subset.filter((r) => !r.first_run && r.first_seen <= cutoff);
    const quick = eligible.filter((r) => r.removed_date && daysBetween(r.first_seen, r.removed_date) <= 7).length;
    const later = eligible.filter((r) => r.removed_date && daysBetween(r.first_seen, r.removed_date) > 7).length;
    return { n: eligible.length, quick, later, open: eligible.length - quick - later };
  };
  const sAll = shares(rows), sRole = shares(roleRows);
  let s5;
  if (!sAll.n) {
    const firstEligible = fresh.length ? addDays([...fresh].sort((a, b) => a.first_seen.localeCompare(b.first_seen))[0].first_seen, 7)
                                       : addDays(first, 8);
    s5 = section(5, "s5", "Not enough history yet to say how many postings vanish within a week",
      "This share counts postings that are not first-run postings and were first seen at least seven days "
      + `before the last run. None qualify yet; the first ones will on ${fmtDayYear(firstEligible)}.`,
      empty(`Eligible postings start on ${fmtDay(firstEligible)}.`));
  } else {
    const c5 = h("div", { class: "chart" });
    const parts = (x) => [
      { name: "Removed within 7 days", value: x.quick, fill: "var(--all)", ink: "#ffffff" },
      { name: "Removed after 7 days", value: x.later, fill: "var(--all-soft)", ink: "var(--ink)" },
      { name: "Still open", value: x.open, fill: "var(--neutral-fill)", ink: "var(--ink)" },
    ];
    s5 = section(5, "s5",
      `${pct(sAll.quick / sAll.n)} of new postings came down within a week`,
      `Among the ${fmt(sAll.n)} postings that are not first-run postings and were first seen on or before `
      + `${fmtDay(cutoff)} (at least seven days before the last run), ${fmt(sAll.quick)} were removed seven `
      + "days or less after they were first seen."
      + (sRole.n ? ` In your role the share is ${pct(sRole.quick / sRole.n)} of ${fmt(sRole.n)}.` : ""),
      c5,
      tableView([{ key: "scope", label: "Postings" }, { key: "n", label: "Eligible", num: true },
                 { key: "quick", label: "Removed ≤ 7 days", num: true }, { key: "later", label: "Removed > 7 days", num: true },
                 { key: "open", label: "Still open", num: true }, { key: "share", label: "Share ≤ 7 days", num: true }],
                [{ scope: "All postings", ...sAll, share: pct(sAll.quick / sAll.n, 1) },
                 { scope: "Your role", ...sRole, share: sRole.n ? pct(sRole.quick / sRole.n, 1) : "–" }]));
    queueMicrotask(() => segmented(c5, {
      rows: [{ label: "All postings", note: `${fmt(sAll.n)} eligible`, parts: parts(sAll) },
             ...(sRole.n ? [{ label: "Your role", note: `${fmt(sRole.n)} eligible`, parts: parts(sRole) }] : [])],
      legend: parts(sAll) }));
  }

  // ------------------------------------------------------------ 6. top locations
  const withLoc = open.filter((r) => r.location);
  const locAll = countBy(withLoc, "location");
  const locRole = countBy(withLoc.filter((r) => r.in_role), "location");
  const locs = [...locAll].map(([location, n]) => ({ location, n, role: locRole.get(location) || 0 }))
    .sort((a, b) => b.n - a.n || a.location.localeCompare(b.location));
  const top = locs.slice(0, 12);
  const topShare = top.reduce((a, l) => a + l.n, 0) / open.length;
  const roleTop = [...locs].sort((a, b) => b.role - a.role)[0];
  const c6 = h("div", { class: "chart" });
  const s6 = section(6, "s6",
    `${top[0].location} has the most open postings: ${fmt(top[0].n)}`,
    `Open postings grouped by location as the boards write it (tidied: US states shortened, "United States" `
    + `dropped). The top ${top.length} of ${fmt(locs.length)} locations hold ${pct(topShare)} of open postings. `
    + `For your role, ${roleTop.location} leads with ${fmt(roleTop.role)}. A posting open in several places counts `
    + "once, under its primary location.",
    c6,
    tableView([{ key: "location", label: "Location" }, { key: "n", label: "Open postings", num: true },
               { key: "role", label: "Open in your role", num: true }], locs.slice(0, 50), "Show the top 50"));
  queueMicrotask(() => hbars(c6, {
    items: top.map((l) => ({ label: l.location, value: l.n,
      extra: [{ value: fmt(l.role), label: "in your role", color: ROLE }] })),
    color: ALL, name: "open postings" }));

  app.replaceChildren(head, s1, s2, s3, s4, s5, s6);
}

// Load last, after every constant above is initialised.
try {
  render(await loadHistory());
} catch (err) {
  app.replaceChildren(errorBox(err));
}
