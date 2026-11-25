// Slugshot dashboard front end. No build step, no dependencies. All text goes through text nodes.
const TOKEN = document.querySelector('meta[name="dash-token"]').content;
const FIXTURE = document.querySelector('meta[name="dash-fixture"]').content === "true";
const $main = document.getElementById("main");
const $nav = document.getElementById("nav");

// ------------------------------------------------------------------ helpers
function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "style") el.setAttribute("style", v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  add(el, kids);
  return el;
}
function add(el, kids) {
  for (const k of kids.flat(9)) {
    if (k == null || k === false) continue;
    el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return el;
}
const NS = "http://www.w3.org/2000/svg";
function s(tag, attrs, ...kids) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v != null) el.setAttribute(k, v);
  for (const k of kids.flat(9)) if (k != null) el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  return el;
}
function icon(d, size = 19) {
  return s("svg", { viewBox: "0 0 24 24", width: size, height: size, fill: "none", stroke: "currentColor", "stroke-width": 1.8,
    "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" }, [].concat(d).map((p) => s("path", { d: p })));
}
const store = {
  get(k, d) { try { const v = localStorage.getItem("ss-" + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem("ss-" + k, JSON.stringify(v)); } catch (e) { /* private window */ } },
};
async function api(path, params) {
  const q = params ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v)) : "";
  const r = await fetch(path + q, { headers: { Accept: "application/json" } });
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}
async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json", "X-Dash-Token": TOKEN }, body: JSON.stringify(body || {}) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}
function toast(msg) {
  document.querySelectorAll(".toast").forEach((t) => t.remove());
  const t = h("div", { class: "toast", role: "status" }, msg);
  document.body.append(t);
  setTimeout(() => t.remove(), 4200);
}

// ------------------------------------------------------------------ formatting
const PLAT = {
  youtube: { name: "YouTube", color: "var(--series-youtube)" },
  tiktok: { name: "TikTok", color: "var(--series-tiktok)" },
  instagram: { name: "Instagram", color: "var(--series-instagram)" },
  roblox: { name: "Roblox", color: "var(--series-roblox)" },
};
function n(v, unit) {
  if (v == null || v === "") return "—";
  if (unit === "fraction") return (v * 100).toFixed(v < 0.1 ? 1 : 0) + "%";
  if (unit === "percent") return v.toFixed(1) + "%";
  if (unit === "seconds") return (v >= 100 ? Math.round(v) : v.toFixed(1)) + " s";
  if (unit === "minutes") return v >= 600 ? (v / 60).toLocaleString(undefined, { maximumFractionDigits: 0 }) + " h" : Math.round(v) + " min";
  if (unit === "Robux") return compact(v) + " R$";
  return compact(v);
}
function compact(v) {
  const a = Math.abs(v);
  if (a >= 1e6) return (v / 1e6).toFixed(a >= 1e7 ? 0 : 1) + "M";
  if (a >= 1e4) return (v / 1e3).toFixed(a >= 1e5 ? 0 : 1) + "K";
  return Number.isInteger(v) || a >= 100 ? Math.round(v).toLocaleString() : v.toLocaleString(undefined, { maximumFractionDigits: 1 });
}
function ago(iso) {
  if (!iso) return "never";
  const m = (Date.now() - new Date(iso).getTime()) / 60000;
  if (m < 2) return "just now";
  if (m < 60) return Math.round(m) + " min ago";
  if (m < 48 * 60) return Math.round(m / 60) + " h ago";
  return Math.round(m / 1440) + " days ago";
}
function day(iso) {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? iso + "T00:00:00Z" : iso);
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", timeZone: "UTC" });
}
const plat = (p) => h("span", { class: "plat" }, h("span", { class: "swatch", style: `background:${PLAT[p]?.color}` }), PLAT[p]?.name || p);
const lang = (l) => (l ? h("span", { class: "lang" }, l.toUpperCase()) : null);
const tip = (text) => h("span", { class: "tip", title: text, tabindex: "0", "aria-label": text }, "i");
const chip = (text, tone) => h("span", { class: "chip " + (tone || "") }, text);
const eyebrow = (t) => h("div", { class: "eyebrow" }, t);
let META = null;
const mdef = (id) => META?.metrics.metrics.find((m) => m.id === id) || { id, label: id, unit: "" };
const FRESH_TONE = { fresh: "ok", due: "warn", stale: "bad", "never synced": "", "not connected": "" };

function panel(title, opts, ...body) {
  opts = opts || {};
  return h("section", { class: "panel" + (opts.flat ? " flat" : ""), id: opts.id || null, style: opts.delay ? `animation-delay:${opts.delay}ms` : null },
    title || opts.eyebrow || opts.actions ? h("div", { class: "panel-head" },
      h("div", { class: "grow" }, opts.eyebrow ? eyebrow(opts.eyebrow) : null, title ? h("h2", {}, title, opts.tip ? tip(opts.tip) : null) : null),
      opts.actions || null) : null,
    body);
}
function empty(title, text, action) {
  return h("div", { class: "empty" }, h("strong", {}, title), text ? h("span", {}, text) : null, action || null);
}

// ------------------------------------------------------------------ charts
// Lines for change over time. One y axis; series coloured by platform identity (fixed, never by rank).
function lineChart(series, opts = {}) {
  const box = h("div", { class: "chart" });
  const live = series.filter((x) => x.points.length);
  if (!live.length) return empty("No daily data in this range", opts.emptyText || "");
  const legend = live.length > 1 ? h("div", { class: "legend" }, live.map((x) => h("span", {}, h("span", { class: "swatch", style: `background:${x.color}` }), x.label))) : null;
  const tableBtn = h("button", { class: "btn ghost small", type: "button" }, "Table");
  const wrap = h("div", {}, h("div", { style: "display:flex;align-items:center;gap:10px;margin-bottom:8px" }, legend, h("span", { style: "flex:1" }), tableBtn), box);
  let showTable = false;
  tableBtn.onclick = () => { showTable = !showTable; tableBtn.textContent = showTable ? "Chart" : "Table"; draw(); };
  const dates = [...new Set(live.flatMap((x) => x.points.map((p) => p.d)))].sort();
  function draw() {
    box.replaceChildren();
    if (showTable) {
      box.append(h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Day"), live.map((x) => h("th", { class: "n" }, x.label)))),
        h("tbody", {}, dates.slice().reverse().map((d) => h("tr", {}, h("td", {}, day(d)),
          live.map((x) => h("td", { class: "n" }, n(x.points.find((p) => p.d === d)?.v, opts.unit)))))))));
      return;
    }
    const W = Math.max(280, box.clientWidth || 640), H = opts.height || 220;
    const pad = { l: 46, r: live.length <= 4 ? 92 : 16, t: 10, b: 26 };
    const vals = live.flatMap((x) => x.points.map((p) => p.v)).filter((v) => v != null);
    const min = Math.min(0, ...vals);
    const step = niceStep((Math.max(...vals) - min) / 4 || 1);
    const ticks = Math.max(1, Math.ceil((Math.max(...vals) - min) / step));
    const max = min + ticks * step;
    const X = (i) => pad.l + (dates.length < 2 ? 0 : (i / (dates.length - 1)) * (W - pad.l - pad.r));
    const Y = (v) => pad.t + (1 - (v - min) / (max - min)) * (H - pad.t - pad.b);
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img", "aria-label": opts.label || "chart" });
    for (let i = 0; i <= ticks; i++) {
      const v = min + step * i;
      svg.append(s("line", { class: "gridline", x1: pad.l, x2: W - pad.r, y1: Y(v), y2: Y(v) }),
        s("g", { class: "axis" }, s("text", { x: pad.l - 8, y: Y(v) + 4, "text-anchor": "end" }, n(v, opts.unit))));
    }
    const xStep = Math.max(1, Math.ceil(dates.length / Math.floor((W - pad.l - pad.r) / 70)));
    dates.forEach((d, i) => { if (i % xStep === 0) svg.append(s("g", { class: "axis" }, s("text", { x: X(i), y: H - 6, "text-anchor": "middle" }, day(d)))); });
    const ends = [];
    for (const x of live) {
      const pts = dates.map((d, i) => [i, x.points.find((p) => p.d === d)?.v]).filter(([, v]) => v != null);
      svg.append(s("path", { class: "line", stroke: x.color, d: pts.map(([i, v], k) => `${k ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join("") }));
      if (pts.length === 1) svg.append(s("circle", { cx: X(pts[0][0]), cy: Y(pts[0][1]), r: 4, fill: x.color }));
      const last = pts[pts.length - 1];
      if (last && live.length <= 4) ends.push({ y: Y(last[1]), x: X(last[0]), label: x.label, color: x.color });
    }
    ends.sort((a, b) => a.y - b.y).forEach((e, i, arr) => { if (i && e.y - arr[i - 1].y < 14) e.y = arr[i - 1].y + 14; });
    ends.forEach((e) => svg.append(s("text", { class: "endlabel", x: e.x + 8, y: e.y + 4 }, e.label)));
    const cross = s("line", { class: "cross", y1: pad.t, y2: H - pad.b, visibility: "hidden" });
    const hit = s("rect", { class: "hit", x: pad.l, y: 0, width: W - pad.l - pad.r, height: H });
    svg.append(cross, hit);
    const tipEl = h("div", { class: "chart-tip hidden" });
    hit.addEventListener("mousemove", (ev) => {
      const r = svg.getBoundingClientRect();
      const px = ((ev.clientX - r.left) / r.width) * W;
      const i = Math.max(0, Math.min(dates.length - 1, Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (dates.length - 1))));
      cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.setAttribute("visibility", "visible");
      tipEl.replaceChildren(h("div", { class: "d" }, day(dates[i])), live.map((x) => h("div", { class: "r" },
        h("span", { class: "swatch", style: `background:${x.color}` }), x.label, h("b", {}, n(x.points.find((p) => p.d === dates[i])?.v, opts.unit)))));
      tipEl.classList.remove("hidden");
      const left = (X(i) / W) * r.width;
      tipEl.style.left = Math.min(left + 14, r.width - 170) + "px";
      tipEl.style.top = "8px";
    });
    hit.addEventListener("mouseleave", () => { cross.setAttribute("visibility", "hidden"); tipEl.classList.add("hidden"); });
    box.append(svg, tipEl);
  }
  requestAnimationFrame(draw);
  charts.push(draw);
  return wrap;
}
function niceStep(raw) {
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  const f = raw / p;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
}
let charts = [];
let resizeT;
window.addEventListener("resize", () => { clearTimeout(resizeT); resizeT = setTimeout(() => charts.forEach((d) => d()), 150); });

function bars(rows, opts = {}) {
  if (!rows.length) return empty(opts.emptyTitle || "No data", opts.emptyText || "");
  const max = Math.max(...rows.map((r) => r.v)) || 1;
  return h("div", { class: "bars" }, rows.map((r) => h("div", { class: "bar-row", title: `${r.label}: ${n(r.v, opts.unit)}` },
    h("span", { style: "overflow:hidden;text-overflow:ellipsis;white-space:nowrap" }, r.label),
    h("div", { class: "bar-track" }, h("div", { class: "bar-fill", style: `width:${(100 * r.v) / max}%` })),
    h("span", { class: "num" }, n(r.v, opts.unit)))));
}

// ------------------------------------------------------------------ shell
const ICONS = {
  overview: ["M4 13h6V4H4zM14 20h6v-9h-6zM4 20h6v-3H4zM14 7h6V4h-6z"],
  content: ["M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5z", "M10 9.2v5.6l4.6-2.8z"],
  research: ["M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z", "M20 20l-4-4", "M8.5 11h5M11 8.5v5"],
  game: ["M7 9h10a4 4 0 0 1 3.9 4.9l-.8 3.3a2 2 0 0 1-3.4.9L14.6 16H9.4l-2.1 2.1a2 2 0 0 1-3.4-.9l-.8-3.3A4 4 0 0 1 7 9z", "M8 12v2.5M6.8 13.2h2.5", "M15.5 12.5h.01M17.5 14h.01"],
  publish: ["M12 15V4", "M7.5 8.5 12 4l4.5 4.5", "M5 14v3.5A2.5 2.5 0 0 0 7.5 20h9a2.5 2.5 0 0 0 2.5-2.5V14"],
  experiments: ["M9.5 3.5h5", "M10.5 3.5v5.2L5.4 17.4A2 2 0 0 0 7.1 20.5h9.8a2 2 0 0 0 1.7-3.1l-5.1-8.7V3.5", "M7.6 14h8.8"],
  settings: ["M12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z", "M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2-1.2L14.3 3h-4.6l-.3 2.7a7 7 0 0 0-2 1.2l-2.3-1-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2 1.2l.3 2.7h4.6l.3-2.7a7 7 0 0 0 2-1.2l2.3 1 2-3.4-2-1.5c.1-.4.1-.8.1-1.2z"],
  refresh: ["M20 11a8 8 0 0 0-14.6-4.5L4 8", "M4 4v4h4", "M4 13a8 8 0 0 0 14.6 4.5L20 16", "M20 20v-4h-4"],
  close: ["M6 6l12 12M18 6L6 18"],
  sun: ["M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4", "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"],
};
const PAGES = [
  { id: "overview", label: "Overview", desc: "Campaign at a glance" },
  { id: "content", label: "Content", desc: "Videos and adaptations" },
  { id: "research", label: "Research", desc: "Signals and evidence" },
  { id: "game", label: "Game", desc: "Players and revenue" },
  { id: "experiments", label: "Experiments", desc: "Tests and decisions" },
  { id: "publish", label: "Publish", desc: "Uploads and approvals" },
];
let STATUS = null;
const syncLine = h("div", { class: "sync-line" });

function renderNav(active) {
  const item = (p) => h("a", { class: "nav-item", href: "#/" + p.id, "aria-current": active === p.id ? "page" : null },
    h("span", { class: "bubble" }, icon(ICONS[p.id])), h("span", {}, h("span", { class: "nav-label" }, p.label), h("span", { class: "nav-desc" }, p.desc)));
  $nav.replaceChildren(
    h("div", { class: "brand" }, h("span", { class: "brand-mark" }, h("img", { src: "/static/icons/icon.svg", width: 22, height: 22, alt: "" })), h("span", { class: "brand-name" }, "Slugshot")),
    eyebrow("Marketing"), ...PAGES.map(item),
    h("div", { class: "nav-foot" }, item({ id: "settings", label: "Settings", desc: "Connections and exports" }), syncLine));
  paintSync();
}
function paintSync() {
  if (!STATUS) return;
  const src = STATUS.sources.filter((x) => x.credential === "ready");
  const running = STATUS.sync.running;
  const bad = STATUS.sources.filter((x) => x.last_status === "failed" || x.last_status === "needs_auth" || x.freshness === "stale");
  const last = src.map((x) => x.last_success_utc).filter(Boolean).sort().pop();
  const tone = running ? "ok pulse" : bad.length ? "warn" : src.length ? "ok" : "";
  syncLine.replaceChildren(h("span", { class: "dot " + tone }),
    running ? "Refreshing…" : !src.length ? "No accounts connected" : bad.length ? `${bad.length} source${bad.length > 1 ? "s need" : " needs"} attention` : "Updated " + ago(last));
  syncLine.title = STATUS.sources.map((x) => `${x.account_label} · ${x.label}: ${x.freshness}`).join("\n");
}
async function refreshStatus() {
  try { STATUS = await api("/api/status"); paintSync(); } catch (e) { /* server restarting */ }
  return STATUS;
}

// Filters shared by Overview, Content and Game
const F = store.get("filters", { range: "28", platform: "", language: "" });
function filterParams() {
  const end = new Date();
  const start = new Date(end.getTime() - (Number(F.range) - 1) * 86400000);
  const iso = (d) => d.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end), platform: F.platform, language: F.language };
}
function seg(options, value, onChange, label) {
  return h("div", { class: "seg", role: "group", "aria-label": label }, options.map(([v, t]) =>
    h("button", { type: "button", "aria-pressed": String(v === value), onclick: () => onChange(v) }, t)));
}
function filterBar(opts = {}) {
  const set = (k) => (v) => { F[k] = v; store.set("filters", F); route(); };
  return h("div", { class: "filters" },
    opts.range === false ? null : seg([["7", "7 days"], ["28", "28 days"], ["90", "90 days"]], F.range, set("range"), "Date range"),
    h("select", { "aria-label": "Platform", onchange: (e) => set("platform")(e.target.value) },
      [["", "All platforms"], ["youtube", "YouTube"], ["tiktok", "TikTok"], ["instagram", "Instagram"]].map(([v, t]) => h("option", { value: v, selected: F.platform === v }, t))),
    seg([["", "All"], ["en", "EN"], ["es", "ES"]], F.language, set("language"), "Language"));
}
function topbar(title, right) {
  const btn = h("button", { class: "btn icon-btn", type: "button", title: "Refresh data now", "aria-label": "Refresh data now",
    onclick: async () => { await post("/api/sync"); toast("Refreshing connected sources…"); pollUntilDone(); } }, icon(ICONS.refresh));
  return [FIXTURE ? h("div", { class: "fixture-banner" }, "Fixture data: test values from tests/fixtures, not real performance.") : null,
    h("header", { class: "topbar" }, h("div", {}, eyebrow("Slugshot"), h("h1", {}, title)), h("div", { class: "grow" }), right || null, btn)];
}
async function pollUntilDone() {
  for (let i = 0; i < 120; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    const st = await refreshStatus();
    if (st && !st.sync.running) { route(); return; }
  }
}

// ------------------------------------------------------------------ Overview
async function pageOverview() {
  const d = await api("/api/overview", filterParams());
  const head = topbar("Overview", filterBar());
  if (!d.has_data) {
    const connected = (STATUS?.sources || []).filter((x) => x.credential === "ready").length;
    return [head, h("div", { class: "stack" },
      panel("No data yet", { eyebrow: "Getting started" },
        h("p", { class: "muted", style: "margin:0 0 14px;max-width:60ch" }, "Numbers appear here after the first refresh of a connected account or a manual import."),
        h("div", { style: "display:flex;gap:10px;flex-wrap:wrap" }, h("a", { class: "btn primary", href: "#/settings" }, "Connect accounts"), h("a", { class: "btn", href: "#/settings" }, "Import metrics"))),
      panel("Accounts", { eyebrow: `${d.accounts.length} set up · ${connected} connected` }, accountsList(d.accounts)))];
  }
  const P = d.platforms;
  const rowsOf = (key, unit) => P.filter((p) => p[key] != null).map((p) => h("div", { class: "row" }, h("span", { class: "swatch", style: `background:${PLAT[p.platform].color}` }), PLAT[p.platform].name,
    key === "views" && p.views_basis === "lifetime" ? h("span", { class: "basis" }, "lifetime") : null, h("span", { class: "v" }, n(p[key], unit))));
  const single = (key) => (P.length === 1 ? P[0][key] : null);
  const tile = (label, value, unit, sub, tipText, delay) => h("div", { class: "panel tile flat", style: `animation-delay:${delay}ms` },
    h("div", { class: "eyebrow" }, label, tipText ? tip(tipText) : null),
    h("div", { class: "value" + (value == null ? " none" : "") }, value == null ? (sub && sub.length ? "" : "—") : n(value, unit)),
    sub && sub.length ? h("div", { class: "sub" }, sub) : null);
  const g = d.game;
  const tiles = h("div", { class: "tiles" },
    tile("Views", single("views"), "", P.length > 1 ? rowsOf("views") : [], "Each platform counts a view differently, so platforms are listed, not added. 'lifetime' = total so far (TikTok gives no daily views).", 0),
    tile("Followers", single("followers"), "", P.length > 1 ? rowsOf("followers") : [], "Latest count per platform. Not added: one person can follow several accounts.", 40),
    tile("Watch time", single("watch_time_minutes"), "minutes", P.length > 1 ? rowsOf("watch_time_minutes", "minutes") : [], "YouTube and Instagram only. TikTok's API doesn't offer it.", 80),
    tile("New players", g?.new_users, "", [], "Roblox: players whose first visit was in this range. Not attributable to a video without a tracked share link.", 120),
    tile("D1 retention", g?.d1_latest?.v, "fraction", g?.d1_latest ? [h("div", { class: "row muted" }, "Cohort of " + day(g.d1_latest.d))] : [], "Share of a day's new players who came back the next day (latest complete cohort).", 160),
    tile("Revenue", g?.revenue_robux, "Robux", [], "Roblox revenue in Robux in this range, as reported. Not converted to money.", 200));
  const viewSeries = P.filter((p) => p.views_series.length).map((p) => ({ label: PLAT[p.platform].name, color: PLAT[p.platform].color, points: p.views_series }));
  const noDaily = P.filter((p) => !p.views_series.length).map((p) => PLAT[p.platform].name);
  return [head, h("div", { class: "stack" }, tiles,
    h("div", { class: "grid cols-2" },
      panel("Views per day", { eyebrow: "Social", delay: 80 }, lineChart(viewSeries, { label: "Views per day by platform" }),
        noDaily.length ? h("p", { class: "muted small", style: "margin:10px 0 0" }, `${noDaily.join(", ")}: lifetime totals only, so no daily line.`) : null),
      panel("Players per day", { eyebrow: "Roblox", delay: 120 }, g ? lineChart([
        { label: "Daily players", color: "var(--series-roblox)", points: g.dau_series },
        { label: "New players", color: "var(--series-youtube)", points: g.new_users_series }], { label: "Players per day" })
        : empty("Not connected", "Add the universe ID and an Analytics API key in Settings."))),
    h("div", { class: "grid cols-2" },
      panel("Accounts", { delay: 160 }, accountsList(d.accounts)),
      panel("Recent content", { delay: 200, actions: h("a", { class: "btn ghost small", href: "#/content" }, "All") }, recentList(d.recent))))];
}
function freshChip(accountId) {
  const src = (STATUS?.sources || []).filter((x) => x.account_id === accountId);
  if (!src.length) return null;
  const order = ["stale", "due", "never synced", "not connected", "fresh"];
  const worst = src.map((x) => x.freshness).sort((a, b) => order.indexOf(a) - order.indexOf(b))[0];
  return chip(worst, FRESH_TONE[worst]);
}
function accountsList(accounts) {
  if (!accounts.length) return empty("No accounts", "Add them in Settings.");
  return h("div", { class: "list" }, accounts.map((a) => h("div", { class: "list-row" },
    h("span", { class: "swatch", style: `background:${PLAT[a.platform].color}` }),
    h("div", { class: "grow" }, h("div", { class: "t" }, a.label, " ", lang(a.language)), h("div", { class: "s" }, a.handle ? "@" + a.handle.replace(/^@/, "") : "no handle yet")),
    a.platform !== "roblox" ? h("div", { class: "num", style: "text-align:right" }, h("div", {}, n(a.followers)), h("div", { class: "s" }, "followers")) : null,
    freshChip(a.account_id))));
}
function recentList(items) {
  if (!items.length) return empty("Nothing published yet", "Uploads appear after a refresh or an import.");
  return h("div", { class: "list" }, items.map((u) => h("div", { class: "list-row", style: "cursor:pointer", onclick: () => openUpload(u.upload_id) },
    h("span", { class: "swatch", style: `background:${PLAT[u.platform].color}` }),
    h("div", { class: "grow" }, h("div", { class: "t" }, u.title || u.concept_title || u.platform_video_id), h("div", { class: "s" }, PLAT[u.platform].name, " · ", day(u.published_at_utc), " · ", (u.language || "").toUpperCase())),
    h("div", { class: "num", style: "text-align:right" }, h("div", {}, n(u.metrics.views)), h("div", { class: "s" }, "views")))));
}

// ------------------------------------------------------------------ Content
let contentTab = store.get("contentTab", "published");
async function pageContent() {
  const p = filterParams();
  const sort = store.get("contentSort", "published");
  const [d, renders] = await Promise.all([api("/api/content", { ...p, sort }), contentTab === "renders" ? api("/api/renders") : null]);
  const tabs = seg([["published", "Published"], ["concepts", "Concepts"], ["renders", "Local renders"]], contentTab, (v) => { contentTab = v; store.set("contentTab", v); route(); }, "Content view");
  const head = topbar("Content", filterBar({ range: false }));
  let body;
  if (contentTab === "published") {
    const oneplat = new Set(d.uploads.map((u) => u.platform)).size <= 1;
    const sortSel = h("select", { "aria-label": "Sort", onchange: (e) => { store.set("contentSort", e.target.value); route(); } },
      h("option", { value: "published", selected: d.sort_applied === "published" }, "Newest"),
      h("option", { value: "views", selected: d.sort_applied === "views", disabled: !oneplat }, "Most views (one platform)"));
    body = panel(null, { actions: null },
      h("div", { style: "display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap" }, tabs, h("span", { style: "flex:1" }), sortSel,
        !oneplat ? tip("Views can only be ranked within one platform. Pick a platform to sort by views.") : null),
      d.uploads.length ? h("div", { class: "table-wrap" }, h("table", {},
        h("thead", {}, h("tr", {}, h("th", {}, "Video"), h("th", {}, "Platform"), h("th", {}, "Published"), h("th", { class: "n" }, "Views"),
          h("th", { class: "n" }, "Likes"), h("th", { class: "n" }, "Avg view", tip("Average seconds watched per view")), h("th", { class: "n" }, "% viewed", tip("YouTube: average percentage of the video viewed. TikTok rows marked 'full' show 'watched full video' instead (a different measure, from Studio imports). Compare within one platform only.")), h("th", {}, "Updated"))),
        h("tbody", {}, d.uploads.map((u) => h("tr", { class: "click", onclick: () => openUpload(u.upload_id), tabindex: "0", onkeydown: (e) => e.key === "Enter" && openUpload(u.upload_id) },
          h("td", { class: "title-cell" }, u.title || u.concept_title || u.platform_video_id, h("span", { class: "muted" }, [u.concept_id ? u.concept_id : "not linked to a concept", u.format].filter(Boolean).join(" · "))),
          h("td", {}, plat(u.platform), " ", lang(u.language)), h("td", {}, day(u.published_at_utc)),
          h("td", { class: "n" }, n(u.metrics.views)), h("td", { class: "n" }, n(u.metrics.likes)),
          h("td", { class: "n" }, n(u.metrics.avg_view_duration_s, "seconds")),
          h("td", { class: "n" }, u.metrics.avg_view_pct != null ? n(u.metrics.avg_view_pct, "percent")
            : u.metrics.completion_rate != null ? [n(u.metrics.completion_rate, "percent"), h("span", { class: "basis" }, " full")] : "—"),
          h("td", { class: "muted small" }, ago(u.observed_at)))))))
        : empty("No uploads", "Connected accounts list their uploads after a refresh; manual imports add the rest."));
  } else if (contentTab === "concepts") {
    body = panel(null, {},
      h("div", { style: "display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap" }, tabs, h("span", { style: "flex:1" }),
        h("button", { class: "btn primary small", type: "button", onclick: () => conceptForm() }, "New concept")),
      d.concepts.length ? h("div", { class: "list" }, d.concepts.map((c) => {
        const ups = d.uploads.filter((u) => u.concept_id === c.concept_id);
        return h("div", { class: "list-row" },
          h("div", { class: "grow" }, h("div", { class: "t" }, c.title), h("div", { class: "s" }, [c.concept_id, c.format, c.hook_type, c.slug].filter(Boolean).join(" · "))),
          h("div", { style: "display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end" }, c.assets.map((a) => chip(`${(a.language || "xx").toUpperCase()} ${a.version}`, "accent"))),
          h("span", { class: "muted small num" }, `${ups.length} upload${ups.length === 1 ? "" : "s"}`),
          h("button", { class: "btn ghost small", type: "button", onclick: () => assetForm({ concept_id: c.concept_id }, d.concepts) }, "Add version"));
      })) : empty("No concepts yet", "A concept is one creative idea; its EN and ES edits are versions of it, and each upload belongs to one version. Uploading the same version to three platforms is still one experiment unit."));
  } else {
    body = panel(null, {},
      h("div", { style: "display:flex;gap:10px;align-items:center;margin-bottom:12px" }, tabs),
      renders.length ? h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "File"), h("th", {}, "Format"), h("th", { class: "n" }, "Length"), h("th", {}, "QC"), h("th", {}, ""))),
        h("tbody", {}, renders.map((r) => h("tr", {}, h("td", { class: "title-cell" }, r.concept, h("span", { class: "muted" }, r.file)),
          h("td", {}, r.format, r.test ? h("span", { class: "muted small" }, " (test)") : null), h("td", { class: "n" }, r.duration_s ? r.duration_s + " s" : "—"),
          h("td", {}, r.qc ? chip(r.qc, r.qc === "PASS" ? "ok" : "warn") : "—"),
          h("td", { class: "n" }, h("button", { class: "btn ghost small", type: "button", onclick: () => assetForm({ edit_file: r.file, concept_title: r.concept, format: r.format }, d.concepts) }, "Register")))))))
        : empty("No renders in exports/", "Edited videos named SS_<date>_<FORMAT>_<Concept>_..._V01_MASTER.mp4 show here."));
  }
  return [head, body];
}

// ------------------------------------------------------------------ drawers
function drawer(...content) {
  closeDrawer();
  const scrim = h("div", { class: "scrim", onclick: closeDrawer });
  const d = h("aside", { class: "drawer", role: "dialog", "aria-modal": "true" },
    h("button", { class: "btn ghost icon-btn close", type: "button", "aria-label": "Close", onclick: closeDrawer }, icon(ICONS.close)), content);
  document.body.append(scrim, d);
  d.querySelector("input,select,textarea,button:not(.close)")?.focus();
  return d;
}
function closeDrawer() { document.querySelectorAll(".scrim,.drawer").forEach((x) => x.remove()); }
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

async function openUpload(id) {
  const [d, content] = await Promise.all([api("/api/upload/" + encodeURIComponent(id)), api("/api/content", {})]);
  const u = d.upload;
  const caps = d.capabilities;
  const metricRows = Object.keys(caps).filter((m) => mdef(m).platforms?.includes(u.platform) || d.latest[m]).map((m) => {
    const L = d.latest[m];
    const how = caps[m];
    const val = L ? (L.status === "value" ? n(L.value, mdef(m).unit) : "unavailable") : how === "api" ? "no data yet" : how === "manual" ? "manual import" : how;
    return h("tr", {}, h("td", {}, mdef(m).label, tip(mdef(m).definition)), h("td", { class: "n" + (L?.status === "value" ? "" : " muted") }, val),
      h("td", { class: "muted small" }, L ? L.source.replace("manual:", "import · ") : ""));
  });
  const views = d.history.filter((x) => x.metric === "views" && x.status === "value").map((x) => ({ d: x.observed_at_utc.slice(0, 10), v: x.value }));
  const assets = content.concepts.flatMap((c) => c.assets.map((a) => ({ ...a, title: c.title })));
  const link = h("select", { "aria-label": "Version" }, h("option", { value: "" }, "Not linked"), assets.map((a) => h("option", { value: a.asset_id, selected: a.asset_id === u.asset_id }, `${a.title} · ${(a.language || "").toUpperCase()} ${a.version}`)));
  drawer(eyebrow(`${PLAT[u.platform].name} upload`), h("h2", {}, u.title || u.platform_video_id),
    h("dl", { class: "kv" },
      h("dt", {}, "Account"), h("dd", {}, u.account_id), h("dt", {}, "Published"), h("dd", {}, u.published_at_utc ? new Date(u.published_at_utc).toLocaleString() : "—"),
      h("dt", {}, "Link"), h("dd", {}, u.url ? h("a", { href: u.url, target: "_blank", rel: "noreferrer" }, u.url) : "—"),
      h("dt", {}, "Concept"), h("dd", {}, d.concept ? `${d.concept.title} (${d.concept.concept_id})` : "—"),
      d.concept ? [h("dt", {}, "Format · hook · slug"), h("dd", {}, [d.concept.format, d.concept.hook_type, d.concept.slug].filter(Boolean).join(" · ") || "—")] : null,
      d.asset ? [h("dt", {}, "Version"), h("dd", {}, `${(d.asset.language || "").toUpperCase()} ${d.asset.version}`), h("dt", {}, "Production time"), h("dd", {}, d.asset.production_minutes != null ? d.asset.production_minutes + " min" : "—"),
        h("dt", {}, "Edit file"), h("dd", {}, d.asset.edit_file ? h("span", { class: "code" }, d.asset.edit_file) : "—")] : null,
      d.siblings.length ? [h("dt", {}, "Same version on"), h("dd", {}, d.siblings.map((x) => h("a", { href: "#", onclick: (e) => { e.preventDefault(); openUpload(x.upload_id); }, style: "margin-right:10px" }, PLAT[x.platform].name)))] : null,
      d.experiments.length ? [h("dt", {}, "Experiments"), h("dd", {}, d.experiments.map((x) => `${x.experiment_id} (${x.status})`).join(", "))] : null),
    h("div", { style: "display:flex;gap:8px;align-items:center" }, link, h("button", { class: "btn small", type: "button", onclick: async () => {
      await post("/api/uploads", { platform: u.platform, platform_video_id: u.platform_video_id, asset_id: link.value || null });
      toast("Saved"); openUpload(id);
    } }, "Link version")),
    h("h3", { class: "eyebrow section-title" }, "Latest metrics"),
    h("div", { class: "table-wrap" }, h("table", {}, h("tbody", {}, metricRows))),
    views.length > 1 ? [h("h3", { class: "eyebrow section-title" }, "Views over time"), lineChart([{ label: "Views (lifetime)", color: PLAT[u.platform].color, points: views }], { height: 160 })] : null,
    h("details", { class: "more", style: "margin-top:14px" }, h("summary", {}, `All observations (${d.history.length})`),
      h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Metric"), h("th", { class: "n" }, "Value"), h("th", {}, "Observed"), h("th", {}, "Source"))),
        h("tbody", {}, d.history.slice().reverse().map((x) => h("tr", {}, h("td", {}, mdef(x.metric).label), h("td", { class: "n" }, x.status === "value" ? n(x.value, mdef(x.metric).unit) : x.status),
          h("td", { class: "small" }, new Date(x.observed_at_utc).toLocaleString()), h("td", { class: "small muted" }, x.source, x.note ? " · " + x.note : ""))))))));
}

function field(label, input, cls) { return h("label", { class: "field " + (cls || "") }, h("span", {}, label), input); }
function form(fields) {
  const els = {};
  const grid = h("div", { class: "form-grid" }, fields.map(([key, label, type, value, opts]) => {
    let el;
    if (type === "textarea") el = h("textarea", { name: key }, value || "");
    else if (type === "select") el = h("select", { name: key }, opts.map(([v, t]) => h("option", { value: v, selected: String(v) === String(value ?? "") }, t)));
    else el = h("input", { name: key, type: type || "text", value: value ?? "" });
    els[key] = el;
    return field(label, el, type === "textarea" ? "wide" : "");
  }));
  return { grid, values: () => Object.fromEntries(Object.entries(els).map(([k, el]) => [k, el.value.trim()])) };
}
function conceptForm(c = {}) {
  const f = form([["title", "Title", "text", c.title], ["format", "Format", "text", c.format], ["hook_type", "Hook type", "text", c.hook_type],
    ["slug", "Featured slug", "text", c.slug], ["hook_text", "Hook line", "textarea", c.hook_text], ["notes", "Notes", "textarea", c.notes]]);
  drawer(eyebrow("Concept"), h("h2", {}, c.concept_id ? "Edit concept" : "New concept"),
    h("p", { class: "muted small" }, "One creative idea. Language versions and platform uploads hang off it."), f.grid,
    h("div", { style: "margin-top:16px" }, h("button", { class: "btn primary", type: "button", onclick: async () => {
      try { const r = await post("/api/concepts", { ...c, ...f.values() }); toast("Saved " + r.concept_id); closeDrawer(); route(); } catch (e) { toast(e.message); }
    } }, "Save")));
}
function assetForm(a, concepts) {
  const opts = concepts.map((c) => [c.concept_id, c.title]);
  const newConcept = !a.concept_id && a.concept_title;
  const f = form([
    ["concept_id", "Concept", "select", a.concept_id || "", [["", newConcept ? `New: ${a.concept_title}` : "Choose…"], ...opts]],
    ["language", "Language", "select", a.language || "en", [["en", "English"], ["es", "Spanish"]]],
    ["version", "Version", "text", a.version || "V01"], ["production_minutes", "Production time (min)", "number", a.production_minutes],
    ["edit_file", "Edit file", "text", a.edit_file], ["fiction_label", "Fiction / AI label", "text", a.fiction_label]]);
  drawer(eyebrow("Version"), h("h2", {}, "Add a language version"), f.grid,
    h("div", { style: "margin-top:16px" }, h("button", { class: "btn primary", type: "button", onclick: async () => {
      const v = f.values();
      try {
        if (!v.concept_id && newConcept) v.concept_id = (await post("/api/concepts", { title: a.concept_title, format: a.format || "" })).concept_id;
        const r = await post("/api/assets", v); toast("Saved " + r.asset_id); closeDrawer(); route();
      } catch (e) { toast(e.message); }
    } }, "Save")));
}

// ------------------------------------------------------------------ Research
let claimLevel = "";
async function pageResearch() {
  const d = await api("/api/research");
  const head = topbar("Research");
  const tone = (st) => (st === "ok" ? "ok" : st === "partial" ? "warn" : "bad");
  const ledgers = d.ledgers.slice().sort((a, b) => a.example - b.example);
  const levelSeg = seg([["", "All"], ...Object.entries({ O: "Observed", D: "Derived", P: "Pattern", I: "Interpretation", C: "Causal", R: "Recommendation" })], claimLevel, (v) => { claimLevel = v; route(); }, "Evidence level");
  const claimEl = (c) => h("div", { class: "claim" }, h("span", { class: "lvl", title: c.level_label }, c.level),
    h("div", {}, c.text, h("div", { style: "display:flex;gap:6px;margin-top:6px;flex-wrap:wrap" },
      chip(c.support, c.support === "supported" ? "ok" : c.support === "contradicted" ? "bad" : "warn"), chip(c.strength), c.reviewed ? null : chip("unreviewed", "warn"))));
  const findings = ledgers.length ? ledgers.map((l) => {
    const claims = l.claims.filter((c) => !claimLevel || c.level === claimLevel);
    // Interpretations and recommendations first when unfiltered: they say what the observations mean for a decision.
    const order = { R: 0, I: 1, P: 2, C: 3, D: 4, O: 5 };
    const sorted = claimLevel ? claims : claims.slice().sort((a, b) => (order[a.level] ?? 9) - (order[b.level] ?? 9));
    const head = sorted.slice(0, l.example ? 0 : 4), tail = sorted.slice(l.example ? 0 : 4);
    return h("div", { style: "margin-bottom:12px" },
      h("div", { style: "display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0" }, h("strong", {}, l.ledger_id), l.example ? chip("worked example") : null, h("span", { class: "muted small" }, day(l.updated_at))),
      l.decision ? h("p", { class: "muted small", style: "margin:0 0 6px" }, l.decision) : null,
      head.map(claimEl),
      tail.length ? h("details", { class: "more" }, h("summary", {}, l.example ? `${tail.length} claims` : `${tail.length} more claims`), tail.map(claimEl)) : null,
      !claims.length ? h("p", { class: "muted small" }, "No claims at this level.") : null);
  }) : empty("No evidence ledgers", "Findings appear when `ss evidence` writes a ledger.");
  const memo = ledgers.filter((l) => !l.example && l.memo && Object.keys(l.memo).length).map((l) => h("div", { class: "list-row", style: "align-items:flex-start" },
    h("div", { class: "grow" }, h("div", { class: "t" }, l.ledger_id), h("div", { class: "small", style: "margin-top:4px;white-space:normal" },
      typeof l.memo === "string" ? l.memo : Object.entries(l.memo).slice(0, 4).map(([k, v]) => h("div", { style: "margin-bottom:4px" }, h("span", { class: "muted" }, k.replace(/_/g, " ") + ": "), typeof v === "string" ? v : Array.isArray(v) ? v.join("; ") : JSON.stringify(v)))))));
  return [head, h("div", { class: "stack" },
    h("div", { class: "grid cols-3" },
      panel("Findings", { eyebrow: "Evidence ledgers", tip: "Each claim keeps its level (O observation, D derived, P pattern, I interpretation, C causal, R recommendation), support status and verbal strength. No scores." }, h("div", { style: "margin-bottom:6px;overflow-x:auto" }, levelSeg), findings),
      h("div", { class: "stack" },
        panel("Collection", { eyebrow: "Research runs" }, d.collection.length ? h("div", { class: "list" }, d.collection.map((c) => h("div", { class: "list-row" },
          h("div", { class: "grow" }, h("div", { class: "t" }, c.provider.replace(/_/g, " ")), h("div", { class: "s" }, `${c.command} · ${ago(c.at)} · ${c.rows} rows`)), chip(c.status, tone(c.status)))))
          : empty("No runs yet", "Run `ss research collect`.")),
        kbSidePanel(d.kb))),
    knowledgePanel(),
    memo.length ? panel("Decisions and opportunities", { eyebrow: "From decision memos" }, h("div", { class: "list" }, memo)) : null,
    h("div", { class: "grid cols-2" },
      panel("Trending searches", { eyebrow: `Google Trending Now · ${day(d.trends.observed_day)}`, tip: "Raw P2 observation: feed order is not a rank, and these are all searches in each country, not gaming." },
        Object.keys(d.trends.by_geo).length ? h("div", { class: "table-wrap" }, h("table", {}, h("tbody", {}, Object.entries(d.trends.by_geo).map(([geo, terms]) =>
          h("tr", {}, h("td", { style: "width:52px" }, h("span", { class: "lang" }, geo)), h("td", { class: "small" }, terms.map((t) => t.term).join(" · "))))))) : empty("No trends collected", "")),
      panel("Watchlists", { eyebrow: "Creators and topics" }, h("div", { class: "list" },
        [["YouTube creators", d.watchlists.youtube_creators.map((x) => x.label)], ["Twitch broadcasters", d.watchlists.twitch_broadcasters.map((x) => x.label)],
          ["Wikipedia topics", d.watchlists.wiki_entities], ["Roblox experiences", d.watchlists.roblox_experiences]].map(([t, items]) =>
          h("details", { class: "more list-row", style: "display:block" }, h("summary", {}, `${t} · ${items.length}`), h("div", { class: "small muted", style: "padding:4px 0 6px" }, items.join(", ") || "none")))))),
    panel("Recent observations", { eyebrow: "Manual and tool observations", tip: "Values as seen on TikTok, Instagram, Creative Center or third-party tools, with provenance (P1 platform count, P2 index or rank, P3 third-party estimate, P4 interpretation)." },
      d.observations.length ? h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Item"), h("th", {}, "Metric"), h("th", { class: "n" }, "Value"), h("th", {}, "Source"), h("th", {}, "Scope"), h("th", {}, "Seen"))),
        h("tbody", {}, d.observations.map((o) => h("tr", {}, h("td", { class: "title-cell" }, o.name, h("span", { class: "muted" }, o.platform)), h("td", {}, o.metric), h("td", { class: "n" }, o.value || "—"),
          h("td", {}, o.source, " ", chip(o.provenance)), h("td", { class: "small muted" }, [o.region, o.period].filter(Boolean).join(" · ")), h("td", { class: "small" }, day(o.observed_at)))))))
        : empty("No observations", "`ss observe import` adds them.")))];
}

// ------------------------------------------------------------------ Knowledge banks
const KB_TONE = { fresh: "ok", evergreen: "", due: "warn", stale: "bad", undated: "warn" };
const EV_LABEL = { established: "established", adjacent: "adjacent domain", verified_platform: "verified platform", owned_result: "our result",
  application: "application", untested: "untested", owner_hypothesis: "owner hypothesis", inventory: "report inventory", observed: "observed sample" };
let kbState = { q: "", bank: "", evidence: "", status: "", format: "", lang: "", due: false };
function kbRow(r) {
  return h("div", { class: "list-row", style: "align-items:flex-start;cursor:pointer", onclick: () => openKnowledge(r.id) },
    h("div", { class: "grow" },
      h("div", { class: "t" }, r.title, " ", h("span", { class: "muted small" }, r.id)),
      r.statement ? h("div", { class: "s", style: "white-space:normal;margin-top:3px" }, r.statement.length > 220 ? r.statement.slice(0, 220) + "…" : r.statement) : null,
      h("div", { style: "display:flex;gap:6px;margin-top:6px;flex-wrap:wrap" },
        chip(EV_LABEL[r.evidence_label] || r.evidence_label), chip(r.review_status, r.review_status === "approved" ? "ok" : r.review_status === "draft" ? "warn" : ""),
        r.support_status ? chip(r.support_status, r.support_status === "supported" ? "ok" : r.support_status === "unsupported" ? "bad" : "warn") : null,
        r.strength ? chip(r.strength) : null,
        r.freshness !== "evergreen" ? chip(r.freshness + (r.review_by ? " · " + r.review_by : ""), KB_TONE[r.freshness]) : null,
        ...r.formats.slice(0, 3).map((f) => chip(f)), ...r.languages.map((l) => h("span", { class: "lang" }, l)))));
}
function knowledgePanel() {
  const list = h("div", { class: "list" }, h("div", { class: "muted small" }, "Loading…"));
  const count = h("span", { class: "muted small" }, "");
  let built = false, timer = null;
  const sel = (key, label, opts) => field(label, h("select", { onchange: (ev) => { kbState[key] = ev.target.value; load(); } },
    [["", "Any"], ...opts].map(([v, t]) => h("option", { value: v, selected: kbState[key] === v }, t))));
  const filters = h("div", { class: "form-grid", style: "margin-bottom:10px" });
  async function load() {
    const params = Object.fromEntries(Object.entries({ ...kbState, due: kbState.due ? "1" : "", inventory: kbState.bank === "inventory" ? "1" : "" }).filter(([, v]) => v));
    const d = await api("/api/knowledge", params);
    if (!built) {
      built = true;
      filters.replaceChildren(
        field("Search", h("input", { type: "search", value: kbState.q, placeholder: "e.g. floppy, payoff, spanish, RFY", oninput: (ev) => { clearTimeout(timer); timer = setTimeout(() => { kbState.q = ev.target.value; load(); }, 220); } }), "wide"),
        sel("bank", "Bank", d.banks.filter((b) => b.bank !== "inventory").map((b) => [b.bank, `${b.bank} (${b.n})`]).concat([["inventory", "inventory (raw reports)"]])),
        sel("evidence", "Evidence", d.facets.evidence.map((x) => [x, EV_LABEL[x] || x])),
        sel("status", "Review", d.facets.status.map((x) => [x, x])),
        sel("format", "Format", d.facets.format.map((x) => [x, x])),
        sel("lang", "Language", [["en", "EN"], ["es", "ES"]]),
        field("Freshness", h("label", { class: "small", style: "display:flex;gap:6px;align-items:center" }, h("input", { type: "checkbox", checked: kbState.due, onchange: (ev) => { kbState.due = ev.target.checked; load(); } }), "Due or stale only")));
    }
    count.textContent = `${d.total} entries${d.total > d.rows.length ? ` · showing ${d.rows.length}` : ""}`;
    const anyFilter = Object.values(kbState).some(Boolean);
    list.replaceChildren(...(d.rows.length ? d.rows.map(kbRow) : [empty("Nothing matches", !anyFilter ? "No knowledge banks yet. Run `ss kb migrate` and add curated entries." : "Try fewer filters.")]));
  }
  load().catch((e) => list.replaceChildren(empty("Knowledge banks unavailable", e.message)));
  return panel("Knowledge", { eyebrow: "Knowledge banks", tip: "Evidence label, review status and freshness are separate. Review is not evidence; support comes from ledgers. The raw report inventory is hidden unless you pick it. No scores.", actions: count }, filters, list);
}
function kbSidePanel(k) {
  if (!k || !k.available) return panel("Knowledge banks", { eyebrow: "Not built yet" }, empty("None yet", "Run `ss kb migrate --audit …` and `ss kb validate`."));
  const opp = k.opportunities.map((o) => h("div", { class: "list-row", style: "align-items:flex-start;cursor:pointer", onclick: () => openKnowledge(o.id) },
    h("div", { class: "grow" }, h("div", { class: "t" }, o.title), h("div", { class: "s", style: "white-space:normal" }, o.target),
      h("div", { style: "display:flex;gap:4px;flex-wrap:wrap;margin-top:5px" }, Object.entries(o.dimensions).map(([dim, v]) => chip(`${dim.replace(/_/g, " ")}: ${v.rating}`, v.rating === "unknown" ? "" : "ok")))),
    chip(EV_LABEL[o.evidence_label] || o.evidence_label, "warn")));
  const sent = k.sentiment.map((x) => h("div", { class: "list-row", style: "cursor:pointer", onclick: () => openKnowledge(x.id) }, h("div", { class: "grow" }, h("div", { class: "t" }, x.title), h("div", { class: "s" }, `${x.denominators.coded || 0} of ${x.denominators.items || 0} coded · ${x.source}`)), chip(x.freshness, KB_TONE[x.freshness])));
  return h("div", { class: "stack" },
    panel("Opportunities", { eyebrow: "Cultural openings", tip: "Popularity, velocity, persistence, saturation, sentiment, fatigue and Slugshot fit are kept separate; an opportunity is a written judgement, never a score." },
      opp.length ? h("div", { class: "list" }, opp) : empty("None yet", "Opportunity cards come from audience samples or owner ideas.")),
    panel("Audience sentiment", { eyebrow: "Coded comment samples", tip: "Each sample is one read of one target with its own denominators. Commenters are self-selected; no demographics are inferred and no comment text is shown here." },
      sent.length ? h("div", { class: "list" }, sent) : empty("No samples yet", "`ss sentiment packet` then `ss sentiment join`.")),
    panel("Due for review", { eyebrow: `${k.n} entries · ${k.errors} validation errors` },
      k.due.length ? h("div", { class: "list" }, k.due.map((r) => h("div", { class: "list-row", style: "cursor:pointer", onclick: () => openKnowledge(r.id) }, h("div", { class: "grow" }, h("div", { class: "t" }, r.title), h("div", { class: "s" }, r.id)), chip(r.freshness + " · " + r.review_by, KB_TONE[r.freshness]))))
        : empty("Nothing due", "Cultural and platform entries list here before their review date.")));
}
async function openKnowledge(id) {
  const e = await api("/api/knowledge/" + encodeURIComponent(id)).catch(() => null);
  if (!e) return toast("Not found: " + id);
  const dl = (pairs) => h("dl", { class: "kv" }, pairs.filter(([, v]) => v && (!Array.isArray(v) || v.length)).flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, Array.isArray(v) ? v.join(", ") : String(v))]));
  const t = e.tags || {};
  const sec = (title) => h("h3", { class: "eyebrow section-title" }, title);
  drawer(eyebrow(`${e.bank} · ${e.id}`), h("h2", {}, e.title),
    h("div", { style: "display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px" }, chip(EV_LABEL[e.evidence_label] || e.evidence_label), chip(e.review_status),
      e.support_status ? chip(e.support_status) : null, e.strength ? chip(e.strength) : null, chip(e.status_freshness + (e.review_by ? " · " + e.review_by : ""), KB_TONE[e.status_freshness])),
    e.statement ? h("p", { style: "max-width:70ch" }, e.statement) : null,
    e.original_text && e.bank !== "inventory" ? h("details", { class: "more" }, h("summary", {}, "Original report wording"), h("p", { class: "small muted", style: "white-space:pre-wrap" }, e.original_text)) : null,
    e.bank === "inventory" ? h("pre", { class: "small", style: "white-space:pre-wrap;max-height:40vh;overflow:auto" }, e.original_text) : null,
    dl([["Boundaries", e.boundaries], ["Transfer assumption", e.transfer_assumption], ["Rival explanations", e.rivals], ["Risks", e.risks],
      ["Bibliographic", e.bibliographic_verification || e.bibliographic_status], ["Figures found", e.figure_presence], ["Context review", e.contextual_verification],
      ["Design", e.design], ["Access", e.access], ["Report self-assessment", e.report_self_support ? `${e.report_self_support} · ${e.report_self_strength}` : ""],
      ["Audit flags", e.audit_flags], ["When / gate", e.gate], ["Comparator", e.comparator], ["Scope", e.scope], ["Linked experiments", e.experiment_refs],
      ["Report IDs", e.report_aliases], ["Formats", t.format], ["Languages", t.language], ["Characters", t.character], ["Stages", t.funnel_stage], ["Journey", t.journey],
      ["Locator", e.locator], ["DOI", e.doi], ["DOI as cited", e.doi_as_cited], ["Next check", e.next_check]]),
    (e.game_truth || []).length ? [sec("Game truth"), h("div", { class: "list" }, e.game_truth.map((g) => h("div", { class: "list-row" }, h("div", { class: "grow small", style: "white-space:normal" }, g.row), chip(g.label, g.label === "OK" ? "ok" : g.label === "NO" || g.label === "AVOID" ? "bad" : "warn"))))] : null,
    e.dimensions ? [sec("Dimensions (separate; no score)"), dl(Object.entries(e.dimensions).map(([k, v]) => [k.replace(/_/g, " "), `${v.rating}${v.note ? " · " + v.note : ""}`]))] : null,
    e.units ? [sec("Per unit (video or thread)"), h("div", { class: "list" }, Object.entries(e.units).map(([u, v]) => h("div", { class: "list-row", style: "align-items:flex-start" }, h("div", { class: "grow" }, h("div", { class: "t" }, u),
      h("div", { class: "s", style: "white-space:normal" }, `${v.n_coded} of ${v.n_items} coded · ` + (Object.entries(v.codes).filter(([, st]) => st.present).map(([c, st]) => `${c} ${st.present}`).join(" · ") || "no codes present"))))))] : null,
    (e.caveats || []).length ? h("ul", { class: "small muted" }, e.caveats.map((c) => h("li", {}, c))) : null,
    e.claims_resolved.length ? [sec("Evidence (ledger claims)"), e.claims_resolved.map((c) => h("div", { class: "claim" }, h("span", { class: "lvl" }, c.level), h("div", {}, c.claim_text, h("div", { style: "display:flex;gap:6px;margin-top:6px" }, chip(c.support_status), chip(c.strength)), h("div", { class: "muted small" }, c.ref))))] : null,
    e.links_resolved.length ? [sec("Links"), h("div", { class: "list" }, e.links_resolved.map((l) => h("div", { class: "list-row", style: "cursor:pointer", onclick: () => openKnowledge(l.to) }, h("div", { class: "grow" }, h("div", { class: "t" }, l.title || l.to), h("div", { class: "s" }, l.to)), chip(l.type.replace(/_/g, " ")))))] : null,
    e.inbound.length ? [sec("Referenced by"), h("div", { class: "small muted" }, e.inbound.map((x) => x.id).join(", "))] : null,
    (e.history || []).length ? h("details", { class: "more" }, h("summary", {}, "History"), e.history.map((x) => h("div", { class: "small" }, `${x.date} · ${x.by}: ${x.note}`))) : null);
}

// ------------------------------------------------------------------ Game
async function pageGame() {
  const d = await api("/api/game", filterParams());
  const head = topbar("Game", filterBar());
  const connected = d.roblox_accounts.some((a) => (STATUS?.sources || []).some((x) => x.account_id === a.account_id && x.credential === "ready"));
  const howChip = (how) => (how === "api" ? null : chip(how === "manual" ? "import" : how, how === "manual" ? "" : "warn"));
  const basis = (b) => (b ? b.replace(/(cohort|day) (\d{4}-\d{2}-\d{2})/, (_m, w, d_) => `${w} ${day(d_)}`) : null);
  const metricCell = (m, v) => h("div", { class: "sm", title: m.definition },
    h("div", { class: "l" }, m.label, " · ", PLAT[v.platform].name, " ", howChip(v.how)),
    h("div", { class: "v" + (v.value == null ? " muted" : "") }, n(v.value, m.unit), v.basis && v.value != null ? h("span", { class: "p" }, basis(v.basis)) : null));
  // Progressive disclosure: primary metrics with data first; everything else (and every gap) behind "More".
  const stages = h("div", { class: "stages" }, d.stages.map((st, i) => {
    const cells = st.metrics.flatMap((m) => m.values.map((v) => ({ m, v })));
    const main = cells.filter(({ m, v }) => m.primary && v.value != null);
    const rest = cells.filter((c) => !main.includes(c));
    return h("div", { class: "stage", style: `animation:slide-up var(--duration-slow) var(--ease-standard) ${i * 30}ms backwards` },
      h("div", {}, h("div", { class: "name" }, st.label), h("div", { class: "what" }, st.measures)),
      h("div", {}, main.length ? h("div", { class: "stage-metrics" }, main.map(({ m, v }) => metricCell(m, v)))
        : h("div", { class: "muted small" }, cells.length ? "No data yet." : "No source for this stage yet."),
        rest.length ? h("details", { class: "more", style: "margin-top:6px" }, h("summary", {}, `More (${rest.length})`),
          h("div", { class: "stage-metrics", style: "margin-top:6px" }, rest.map(({ m, v }) => metricCell(m, v)))) : null));
  }));
  const S = d.series;
  return [head, h("div", { class: "stack" },
    !connected && !FIXTURE ? panel("Roblox analytics not connected", { flat: true },
      h("p", { class: "muted", style: "margin:0 0 12px" }, "Slugshot isn't published yet. When it is, add the universe ID and an Open Cloud key with universe.analytics:read."), h("a", { class: "btn", href: "#/settings" }, "Settings")) : null,
    panel("Measurement stages", { eyebrow: "Commercial funnel", tip: "Each stage is measured in its own population and window. Stages are never divided into each other: a viewer can't be followed into the game except through a tracked share link." }, stages),
    h("div", { class: "grid cols-2" },
      panel("Players per day", { eyebrow: "Retention" }, lineChart([{ label: "Daily players", color: "var(--series-roblox)", points: S.dau }, { label: "New players", color: "var(--series-youtube)", points: S.new_users }], { label: "Players per day" })),
      panel("D1 retention by cohort", { eyebrow: "Retention", tip: "Each point is the share of that day's new players who returned the next day. The newest day has no value until its cohort completes." }, lineChart([{ label: "D1", color: "var(--series-roblox)", points: S.d1_retention }], { unit: "fraction" }))),
    h("div", { class: "grid cols-2" },
      panel("Revenue per day", { eyebrow: "Monetisation" }, lineChart([{ label: "Revenue (Robux)", color: "var(--series-roblox)", points: S.revenue_robux }], { unit: "Robux" })),
      panel("Acquisition sources", { eyebrow: "Acquisition · average per day", tip: "Average daily unique players with sessions, by Roblox's acquisition source, over the selected range. Days aren't added: the same player returns on several days." },
        bars(d.acquisition.map((r) => ({ label: r.source, v: r.v })), { emptyTitle: "No acquisition data" }))),
    h("div", { class: "grid cols-2" },
      panel("Share links", { eyebrow: "Tracked links", tip: "From Creator Dashboard > Share Links, imported by hand. Use one link per account or campaign so arrivals can be attributed." },
        d.share_links.length ? h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Link"), h("th", {}, "Metric"), h("th", { class: "n" }, "Value"))),
          h("tbody", {}, d.share_links.map((r) => h("tr", {}, h("td", {}, r.link), h("td", {}, mdef(r.metric).label), h("td", { class: "n" }, n(r.v)))))))
          : empty("No share-link data", "Import the Share Links numbers (long template, breakdown_dim ShareLink).")),
      panel("Cohorts", { eyebrow: "New players by first day" }, d.cohorts.length ? h("div", { class: "table-wrap" }, h("table", {},
        h("thead", {}, h("tr", {}, h("th", {}, "First day"), h("th", { class: "n" }, "New"), h("th", { class: "n" }, "D1"), h("th", { class: "n" }, "D7"), h("th", { class: "n" }, "D30"))),
        h("tbody", {}, d.cohorts.slice(0, 14).map((c) => h("tr", {}, h("td", {}, day(c.d)), h("td", { class: "n" }, n(c.new_users)), h("td", { class: "n" }, n(c.d1, "fraction")), h("td", { class: "n" }, n(c.d7, "fraction")), h("td", { class: "n" }, n(c.d30, "fraction")))))))
        : empty("No cohorts yet", ""))),
    h("p", { class: "muted small" }, "Activation: " + d.activation_note))];
}

// ------------------------------------------------------------------ Experiments
const STATUS_TONE = { proposed: "", planned: "accent", running: "ok", analysing: "warn", decided: "ok", abandoned: "" };
async function familiesPanel() {
  const fams = await api("/api/hypotheses").catch(() => []);
  if (!fams.length) return null;
  return panel("Hypothesis families", { eyebrow: "Knowledge bank · learning portfolio", tip: "The 51 report hypotheses merged into 17 families (original IDs kept). A family becomes an experiment here when scheduled. Options, not gates: unrelated concepts are always allowed." },
    h("div", { class: "list" }, fams.map((f) => h("div", { class: "list-row", style: "align-items:flex-start;cursor:pointer", onclick: () => openKnowledge(f.id) },
      h("div", { class: "grow" }, h("div", { class: "t" }, f.title), h("div", { class: "s", style: "white-space:normal" }, f.question),
        h("div", { class: "s", style: "white-space:normal;margin-top:3px" }, "When: " + f.gate + (f.experiments.length ? " · linked: " + f.experiments.join(", ") : ""))),
      chip(f.aliases.length + (f.aliases.length === 1 ? " report hypothesis" : " report hypotheses"))))));
}
async function pageExperiments() {
  const [exps, content] = await Promise.all([api("/api/experiments"), api("/api/content", {})]);
  const head = topbar("Experiments", h("button", { class: "btn primary", type: "button", onclick: () => experimentForm({}, content) }, "New experiment"));
  return [head, exps.length ? h("div", { class: "stack" }, exps.map((e, i) => panel(e.title, {
    eyebrow: e.experiment_id, delay: i * 40,
    actions: h("div", { style: "display:flex;gap:8px;align-items:center" }, chip(e.status, STATUS_TONE[e.status]), h("button", { class: "btn small", type: "button", onclick: () => experimentForm(e, content) }, "Open")) },
    h("p", { style: "margin:0 0 12px;max-width:80ch" }, e.hypothesis),
    (e.hypothesis_families || []).length ? h("div", { style: "display:flex;gap:6px;flex-wrap:wrap;margin:-4px 0 12px" }, e.hypothesis_families.map((f) => h("button", { class: "chip linkish", type: "button", title: f.gate, onclick: () => openKnowledge(f.id) }, f.id + " · " + f.title))) : null,
    h("div", { class: "stage-metrics", style: "margin-bottom:12px" },
      h("div", { class: "sm" }, h("div", { class: "l" }, "Primary metric"), h("div", { class: "v" }, mdef(e.primary_metric).label, h("span", { class: "p" }, e.window_hours ? `at ${e.window_hours} h` : ""))),
      h("div", { class: "sm" }, h("div", { class: "l" }, "One change"), h("div", { class: "small", style: "max-width:46ch" }, e.one_change || "—")),
      h("div", { class: "sm" }, h("div", { class: "l" }, "Next action"), h("div", { class: "small", style: "max-width:46ch" }, e.next_action || "—"))),
    h("div", { class: "grid cols-2" }, e.variants.map((v) => h("div", { class: "stage", style: "grid-template-columns:1fr" },
      h("div", {}, h("div", { class: "name" }, `${v.variant_id} · ${v.label}`, " ", chip(v.role)), h("div", { class: "what" }, v.description)),
      v.uploads.length ? h("div", { class: "stage-metrics" }, v.uploads.map((u) => {
        const at = u.at_window[e.primary_metric];
        return h("div", { class: "sm" }, h("div", { class: "l" }, PLAT[u.platform].name, " ", u.account_id),
          h("div", { class: "v" + (at ? "" : " muted") }, at ? n(at.value, mdef(e.primary_metric).unit) : "no reading", at ? h("span", { class: "p" }, `${at.hours_from_window >= 0 ? "+" : ""}${at.hours_from_window} h from read time`) : null));
      })) : h("div", { class: "muted small" }, "No uploads linked yet."))))))) : panel(null, {}, empty("No experiments", "Record one with New experiment.")),
    await familiesPanel()];
}
function experimentForm(e, content) {
  const metrics = META.metrics.metrics.filter((m) => m.platforms.length && m.platforms[0] !== "roblox").map((m) => [m.id, m.label]);
  const f = form([
    ["title", "Title", "text", e.title], ["status", "Status", "select", e.status || "proposed", ["proposed", "planned", "running", "analysing", "decided", "abandoned"].map((x) => [x, x])],
    ["hypothesis", "Hypothesis", "textarea", e.hypothesis], ["one_change", "The one change", "textarea", e.one_change],
    ["primary_metric", "Primary metric", "select", e.primary_metric || "avg_view_pct", metrics], ["window_hours", "Read at (hours after posting)", "number", e.window_hours ?? 48],
    ["language", "Language", "select", e.language || "", [["", "Both"], ["en", "EN"], ["es", "ES"]]], ["campaign", "Campaign", "text", e.campaign],
    ["stop_rule", "Stop rule", "textarea", e.stop_rule], ["threshold", "Decision threshold", "textarea", e.threshold],
    ["design", "Design", "textarea", e.design], ["results", "Results", "textarea", e.results], ["limitations", "Limitations", "textarea", e.limitations],
    ["decision", "Decision", "textarea", e.decision], ["next_action", "Next action", "textarea", e.next_action]]);
  const assets = content.concepts.flatMap((c) => c.assets.map((a) => [a.asset_id, `${c.title} · ${(a.language || "").toUpperCase()} ${a.version}`]));
  const variants = (e.variants?.length ? e.variants : [{ variant_id: "A", role: "control", label: "", description: "", asset_ids: [] }, { variant_id: "B", role: "treatment", label: "", description: "", asset_ids: [] }]).map((v) => ({ ...v }));
  const vbox = h("div", { class: "stack" });
  const paintVariants = () => vbox.replaceChildren(...variants.map((v) => h("div", { class: "stage", style: "grid-template-columns:1fr" },
    h("div", { class: "form-grid" },
      field("Variant", h("input", { type: "text", value: v.variant_id, oninput: (ev) => (v.variant_id = ev.target.value) })),
      field("Role", h("select", { onchange: (ev) => (v.role = ev.target.value) }, ["control", "treatment"].map((r) => h("option", { value: r, selected: v.role === r }, r)))),
      field("Label", h("input", { type: "text", value: v.label, oninput: (ev) => (v.label = ev.target.value) }), "wide"),
      field("Description", h("textarea", { oninput: (ev) => (v.description = ev.target.value) }, v.description), "wide"),
      field("Versions", h("select", { multiple: true, size: Math.min(4, Math.max(2, assets.length)), onchange: (ev) => (v.asset_ids = [...ev.target.selectedOptions].map((o) => o.value)) },
        assets.length ? assets.map(([id, t]) => h("option", { value: id, selected: v.asset_ids.includes(id) }, t)) : h("option", { disabled: true }, "No versions yet (Content > Concepts)")), "wide")))));
  paintVariants();
  drawer(eyebrow(e.experiment_id || "New experiment"), h("h2", {}, e.title || "New experiment"),
    h("p", { class: "muted small" }, "One main change, a metric and read time fixed in advance. Variants link to versions, so one version on three platforms stays one unit."),
    f.grid, h("h3", { class: "eyebrow section-title" }, "Variants"), vbox,
    h("button", { class: "btn ghost small", type: "button", style: "margin-top:8px", onclick: () => { variants.push({ variant_id: String.fromCharCode(65 + variants.length), role: "treatment", label: "", description: "", asset_ids: [] }); paintVariants(); } }, "Add variant"),
    h("div", { style: "margin-top:18px;display:flex;gap:10px" }, h("button", { class: "btn primary", type: "button", onclick: async () => {
      try {
        const v = f.values();
        const r = await post("/api/experiments", { ...e, ...v, window_hours: v.window_hours || null, secondary_metrics: e.secondary_metrics || [], platforms: e.platforms || [], variants });
        toast("Saved " + r.experiment_id); closeDrawer(); route();
      } catch (err) { toast(err.message); }
    } }, "Save")));
}

// ------------------------------------------------------------------ Settings
async function pageSettings() {
  const st = await refreshStatus();
  const accounts = (await api("/api/meta")).accounts;
  const head = topbar("Settings");
  const credTone = (c) => (c === "ready" ? "ok" : "");
  const conn = h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Account"), h("th", {}, "Source"), h("th", {}, "Status"), h("th", {}, "Last refresh"), h("th", {}, ""))),
    h("tbody", {}, st.sources.map((x) => h("tr", {},
      h("td", {}, plat(x.platform), " ", lang(x.language), h("div", { class: "muted small" }, x.account_label)),
      h("td", { class: "small" }, x.label),
      h("td", {}, ["failed", "needs_auth"].includes(x.last_status) && x.credential === "ready" ? chip(x.last_status === "failed" ? "failed" : "reconnect", "bad")
        : chip(x.credential === "ready" ? x.freshness : x.credential, x.credential === "ready" ? FRESH_TONE[x.freshness] : credTone(x.credential)),
        x.last_status && x.last_status !== "ok" ? h("div", { class: "small muted", style: "margin-top:4px;max-width:34ch" }, `${x.last_status}: ${x.last_message}`) : null),
      h("td", { class: "small" }, x.last_success_utc ? ago(x.last_success_utc) : "—"),
      h("td", { class: "n" }, connectAction(x)))))));
  const creds = [["YOUTUBE_OAUTH_CLIENT_ID", "Google OAuth client ID"], ["YOUTUBE_OAUTH_CLIENT_SECRET", "Google OAuth client secret"],
    ["TIKTOK_CLIENT_KEY", "TikTok client key"], ["TIKTOK_CLIENT_SECRET", "TikTok client secret"], ["ROBLOX_ANALYTICS_API_KEY", "Roblox Open Cloud key"],
    ["BUFFER_API_KEY", "Buffer API key"], ["CLOUDINARY_CLOUD_NAME", "Cloudinary cloud name"], ["CLOUDINARY_API_KEY", "Cloudinary API key"],
    ["CLOUDINARY_API_SECRET", "Cloudinary API secret"]];
  const credRows = h("div", { class: "list" }, creds.map(([k, t]) => {
    const inp = h("input", { type: "password", autocomplete: "off", placeholder: st.credentials[k] ? "saved · paste to replace" : "paste value", "aria-label": t, style: "flex:1;min-width:0" });
    return h("div", { class: "list-row" }, h("div", { style: "width:220px;flex:none" }, h("div", { class: "t" }, t), h("div", { class: "s" }, k)), inp,
      st.credentials[k] ? chip("saved", "ok") : chip("not set"),
      h("button", { class: "btn small", type: "button", onclick: async () => {
        if (!inp.value.trim()) return;
        await post("/api/credentials", { name: k, value: inp.value }); inp.value = ""; toast("Saved to the encrypted local vault"); route();
      } }, "Save"));
  }));
  const acctRows = h("div", { class: "list" }, accounts.map((a) => {
    const label = h("input", { type: "text", value: a.label, "aria-label": "Label" });
    const handle = h("input", { type: "text", value: a.handle, placeholder: "handle", "aria-label": "Handle" });
    const ext = h("input", { type: "text", value: a.external_id, placeholder: a.platform === "roblox" ? "universe ID" : "channel / user ID (filled on connect)", "aria-label": "External ID" });
    const active = h("input", { type: "checkbox", checked: !!a.active, "aria-label": "Active" });
    return h("div", { class: "list-row", style: "flex-wrap:wrap" }, h("span", { style: "width:120px" }, plat(a.platform), " ", lang(a.language)), label, handle, ext,
      h("label", { class: "small muted", style: "display:flex;gap:6px;align-items:center" }, active, "active"),
      h("button", { class: "btn small", type: "button", onclick: async () => {
        try { await post("/api/accounts", { ...a, label: label.value, handle: handle.value, external_id: ext.value.trim(), active: active.checked }); toast("Saved"); } catch (e) { toast(e.message); }
      } }, "Save"));
  }));
  const auto = h("input", { type: "checkbox", checked: st.auto_refresh, onchange: async (e) => { await post("/api/prefs", { auto_refresh: e.target.checked }); toast(e.target.checked ? "Daily refresh on" : "Daily refresh off"); } });
  const theme = store.get("theme-choice", "system");
  const setTheme = (v) => {
    store.set("theme-choice", v);
    try { v === "system" ? localStorage.removeItem("ss-theme") : localStorage.setItem("ss-theme", v); } catch (e) { /* ignore */ }
    const t = v === "system" ? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark") : v;
    document.documentElement.setAttribute("data-theme", t);
    route();
  };
  return [head, h("div", { class: "stack" },
    panel("Connections", { eyebrow: "Sources", tip: "Each account is refreshed on its own. A failure in one never stops the others." }, conn,
      h("p", { class: "muted small", style: "margin:12px 0 0" }, "OAuth redirect URI to register: ", h("span", { class: "code" }, st.redirect_uri))),
    h("div", { class: "grid cols-2" },
      panel("Refresh", { eyebrow: "Sync" }, h("div", { style: "display:flex;gap:12px;align-items:center;flex-wrap:wrap" },
        h("button", { class: "btn primary", type: "button", onclick: async () => { await post("/api/sync"); toast("Refreshing…"); pollUntilDone(); } }, "Refresh now"),
        h("label", { style: "display:flex;gap:8px;align-items:center" }, auto, "Daily, and when the app opens"))),
      panel("Appearance", { eyebrow: "Theme" }, seg([["system", "System"], ["light", "Light"], ["dark", "Dark"]], theme, setTheme, "Theme"))),
    hostingPanel(),
    h("div", { class: "grid cols-2" }, importPanel(st), exportPanel()),
    panel("App credentials", { eyebrow: "Stored encrypted on this PC (Windows DPAPI)", tip: "Never shown again, never exported. .env values also work." }, credRows),
    panel("Accounts", { eyebrow: "English and Spanish accounts", id: "accounts-panel" }, acctRows))];
}
// Free-tier watch: Cloudinary (video hosting for Buffer) and Buffer's API window. Figures come from the providers.
function hostingPanel() {
  const body = h("div", {}, h("p", { class: "muted small" }, "Loading…"));
  const pct = (x) => (x && x.used_percent != null ? `${Number(x.used_percent).toFixed(1)}%` : "—");
  const mb = (b) => (b == null ? "—" : `${(b / 1e6).toFixed(1)} MB`);
  const render = (d) => {
    const u = d.usage || {}, q = d.buffer_quota, L = d.limits;
    body.replaceChildren(
      h("dl", { class: "kv tight" },
        h("dt", {}, "Cloudinary"), h("dd", {}, d.configured ? `${u.plan || "plan unknown"} plan` : chip("not set up"), d.error ? h("span", { class: "chip bad" }, d.error) : null),
        h("dt", {}, "Credits (30 days)"), h("dd", {}, u.credits && u.credits.usage != null ? `${u.credits.usage} of ${u.credits.limit} · ${pct(u.credits)}` : "—", ` · uploads stop at ${L.max_credit_pct}%`),
        h("dt", {}, "Storage"), h("dd", {}, u.storage ? `${mb(u.storage.usage)} ${u.storage.used_percent != null ? "· " + pct(u.storage) : ""}` : "—"),
        h("dt", {}, "Bandwidth"), h("dd", {}, u.bandwidth ? `${mb(u.bandwidth.usage)} ${u.bandwidth.used_percent != null ? "· " + pct(u.bandwidth) : ""}` : "—"),
        h("dt", {}, "Limits"), h("dd", {}, `${L.max_file_mb} MB per video · ${L.max_hosted_files} hosted at once · abandoned after ${L.abandon_hours} h`),
        h("dt", {}, "Buffer API"), h("dd", {}, q ? `${q.remaining} of ${q.limit} requests left this 30-day window` : "—", " · analytics pause below 150"),
        h("dt", {}, "Checked"), h("dd", {}, u.fetched_at ? ago(u.fetched_at) : "—")),
      d.hosted.length ? h("div", { class: "table-wrap", style: "margin-top:10px" }, h("table", {}, h("thead", {}, h("tr", {}, ["Hosted file", "State", "Size", "Updated"].map((t) => h("th", {}, t)))),
        h("tbody", {}, d.hosted.map((r) => h("tr", {}, h("td", { class: "small code" }, r.public_id.split("/").pop().slice(0, 12)), h("td", {}, chip(r.state, r.state === "deleted" ? "" : r.state === "failed" ? "bad" : "accent")),
          h("td", { class: "small" }, mb(r.bytes)), h("td", { class: "small muted" }, ago(r.updated_at_utc))))))) : h("p", { class: "muted small" }, "Nothing hosted."),
      h("div", { style: "display:flex;gap:8px;margin-top:10px" },
        h("button", { class: "btn small", type: "button", onclick: async () => { body.replaceChildren(h("p", { class: "muted small" }, "Checking…")); render(await api("/api/hosting?refresh=1")); } }, "Check usage now"),
        h("button", { class: "btn ghost small", type: "button", onclick: async () => { const r = await post("/api/hosting/cleanup", {}); toast(`${r.deleted.length} abandoned file(s) deleted`); render(await api("/api/hosting")); } }, "Clean up abandoned files")));
  };
  api("/api/hosting").then(render).catch((e) => body.replaceChildren(h("p", { class: "muted small" }, e.message)));
  return panel("Hosting and quotas", { eyebrow: "Free plans", tip: "Videos for Buffer are hosted on Cloudinary behind a private signed link, only after you approve, and deleted once every post of them has finished. No transformations are ever requested." }, body);
}
function connectAction(x) {
  if (x.connector === "youtube_analytics" || x.connector === "tiktok") {
    const prov = x.connector === "tiktok" ? "tiktok" : "youtube";
    const blocked = x.credential.startsWith("needs");
    return h("div", { style: "display:flex;gap:6px;justify-content:flex-end" },
      h("button", { class: "btn small", type: "button", disabled: blocked, title: blocked ? "Save the app credentials below first" : null, onclick: async () => {
        try { const r = await post("/api/oauth/start", { provider: prov, account_id: x.account_id }); window.open(r.url, "_blank", "noopener"); toast("Finish signing in in the browser window"); } catch (e) { toast(e.message); }
      } }, x.credential === "ready" ? "Reconnect" : "Connect"),
      x.credential === "ready" ? disconnectBtn(x) : null);
  }
  if (x.connector === "instagram") {
    return h("div", { style: "display:flex;gap:6px;justify-content:flex-end" }, h("button", { class: "btn small", type: "button", onclick: () => {
      const inp = h("input", { type: "password", autocomplete: "off", style: "width:100%" });
      drawer(eyebrow("Instagram"), h("h2", {}, "Paste access token"), h("p", { class: "muted small" }, "Meta app dashboard > Instagram > API setup with Instagram login > Generate token, for this account. Stored encrypted; refreshed automatically before it expires."),
        field("Long-lived token", inp), h("div", { style: "margin-top:14px" }, h("button", { class: "btn primary", type: "button", onclick: async () => {
          await post("/api/credentials", { name: "INSTAGRAM_TOKEN", account_id: x.account_id, value: inp.value }); closeDrawer(); toast("Saved"); route();
        } }, "Save")));
    } }, x.credential === "ready" ? "Replace token" : "Add token"), x.credential === "ready" ? disconnectBtn(x) : null);
  }
  return h("button", { class: "btn ghost small", type: "button", onclick: () => document.getElementById("accounts-panel")?.scrollIntoView({ behavior: "smooth" }) },
    x.credential === "ready" ? "Ready" : "Set ID below");
}
function disconnectBtn(x) {
  return h("button", { class: "btn ghost small", type: "button", onclick: async () => {
    if (!confirm(`Disconnect ${x.account_label} (${x.label})?`)) return;
    const forget = confirm("Also delete the data already collected from it?\n\nOK deletes it. Cancel keeps it.");
    await post("/api/disconnect", { connector: x.connector, account_id: x.account_id, forget_data: forget });
    toast(forget ? "Disconnected and data removed" : "Disconnected"); route();
  } }, "Disconnect");
}
function importPanel(st) {
  const out = h("div", {});
  let text = "", name = "";
  const fileIn = h("input", { type: "file", accept: ".csv,text/csv", class: "hidden", onchange: (e) => read(e.target.files[0]) });
  const drop = h("div", { class: "drop", tabindex: "0", role: "button", onclick: () => fileIn.click(), onkeydown: (e) => e.key === "Enter" && fileIn.click() },
    "Drop a CSV here or click to choose");
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); read(e.dataTransfer.files[0]); });
  async function read(file) {
    if (!file) return;
    text = await file.text(); name = file.name;
    show(await post("/api/import", { text, file_name: name, dry_run: true }), true);
  }
  function show(r, check) {
    out.replaceChildren(
      r.ok ? h("p", { class: "small" }, `${name}: ${r.kind}, ${r.rows_ok} rows ok${r.rows_rejected ? `, ${r.rows_rejected} rejected` : ""}${check ? " (checked, not imported yet)" : " imported"}.`) : h("p", { class: "small" }, `${name}: not imported.`),
      r.errors?.length ? h("pre", { class: "errors" }, r.errors.join("\n")) : null,
      check && r.ok ? h("button", { class: "btn primary small", type: "button", onclick: async () => { show(await post("/api/import", { text, file_name: name, skip_bad: true }), false); route(); } }, "Import") : null);
  }
  return panel("Import metrics", { eyebrow: "Manual", tip: "For numbers no API gives us: TikTok Studio, Instagram app, YouTube Studio exports, Roblox share links. Files are checked first; nothing is stored until you press Import." },
    drop, fileIn, out,
    h("p", { class: "muted small", style: "margin:10px 0 0" }, "Templates: ", h("span", { class: "code" }, "data/templates/platform_metrics_template.csv"), " ", h("span", { class: "code" }, "data/templates/dashboard_metrics_long_template.csv")),
    st.imports.length ? h("details", { class: "more", style: "margin-top:8px" }, h("summary", {}, "Recent imports"), st.imports.map((i) => h("div", { class: "small muted" }, `${day(i.imported_at_utc)} · ${i.file_name} · ${i.rows_ok} rows`))) : null);
}
function exportPanel() {
  let detail = "overview";
  const safe = h("input", { type: "checkbox", checked: true });
  const out = h("div", {});
  const segEl = h("span", {});
  const paint = () => segEl.replaceChildren(seg([["overview", "Overview"], ["detailed", "Detailed"]], detail, (v) => { detail = v; paint(); }, "Detail"));
  paint();
  return panel("Export snapshot", { eyebrow: "For ChatGPT, Claude and Gemini", tip: "Markdown summary plus CSV/JSON files, readable one by one. Safe-to-share applies the sharing rules, removes local paths and checks for credentials." },
    h("div", { style: "display:flex;gap:12px;align-items:center;flex-wrap:wrap" }, segEl, h("label", { style: "display:flex;gap:8px;align-items:center" }, safe, "Safe to share"),
      h("button", { class: "btn primary", type: "button", onclick: async () => {
        try {
          const r = await post("/api/export", { detail, share: safe.checked, filters: filterParams() });
          out.replaceChildren(h("p", { class: "small" }, `${r.files.length} files in `, h("span", { class: "code" }, r.folder)),
            r.excluded.length ? h("p", { class: "small muted" }, "Excluded: " + r.excluded.join("; ")) : null,
            h("button", { class: "btn small", type: "button", onclick: () => post("/api/open-folder", { folder: r.folder }) }, "Open folder"));
        } catch (e) { toast(e.message); }
      } }, "Export")), out);
}

// ------------------------------------------------------------------ Publish
// Drafts -> preview and checks -> the owner types the handle to approve -> official-API upload or manual package.
const PUB_STATE = { draft: ["Draft", ""], approved: ["Approved", "accent"], uploading: ["Uploading…", "accent"], processing: ["Processing", "accent"],
  sent_to_inbox: ["In TikTok inbox", "warn"], in_buffer_drafts: ["In Buffer drafts", "warn"], done: ["Posted", "ok"], failed: ["Failed", "bad"], manual_pending: ["Manual", "warn"] };
const ROUTE_LABEL = { buffer: "Via Buffer (needs a public video link)", api: "Direct upload (API)", inbox: "Upload to TikTok inbox (you finish in the app)", direct: "Direct Post (API)", manual: "Manual: I post it myself" };
const CRED_TONE = { ready: "ok", "needs upload permission": "warn", "not connected": "", unsupported: "" };
const TT_PRIVACY = { PUBLIC_TO_EVERYONE: "Everyone", MUTUAL_FOLLOW_FRIENDS: "Friends", FOLLOWER_OF_CREATOR: "Followers", SELF_ONLY: "Only me" };
const atHandle = (a) => (a.handle ? "@" + a.handle.replace(/^@/, "") : "no handle set");

async function pagePublish() {
  const d = await api("/api/publish");
  const lockChip = [d.reveal_lock ? chip("Reveal lock: game unnamed", "warn") : chip("Reveal lock off", "bad"),
    chip(d.public_posting ? "Public posts allowed" : "Private posts only", d.public_posting ? "" : "warn")];
  const head = topbar("Publish", h("div", { style: "display:flex;gap:10px;align-items:center" }, lockChip,
    h("button", { class: "btn primary", type: "button", onclick: () => composer(d) }, "New post")));
  const accounts = panel("Accounts", { eyebrow: "Where videos can go", tip: "Uploads reuse the analytics connection. Connecting for uploads adds the upload permission; nothing is posted until you approve a job." },
    h("div", { class: "list" }, d.accounts.filter((a) => a.active).map((a) => h("div", { class: "list-row" },
      h("span", { class: "dot", style: `background:${PLAT[a.platform].color}` }),
      h("div", { class: "grow" }, h("div", { class: "t" }, a.label, " ", lang(a.language)),
        h("div", { class: "s" }, atHandle(a), a.buffer ? " · Buffer ready" : "", " · ", a.routes.filter((r) => r !== "manual").map((r) => ROUTE_LABEL[r].split(" (")[0]).join(", "), " or manual")),
      chip(a.credential === "ready" ? "Ready to upload" : a.credential, CRED_TONE[a.credential]),
      a.credential !== "ready" ? (a.platform === "instagram"
        ? h("a", { class: "btn ghost small", href: "#/settings" }, "Add token")
        : h("button", { class: "btn small", type: "button", onclick: async () => {
            try { const r = await post("/api/oauth/start", { provider: a.platform, account_id: a.account_id, purpose: "publish" }); window.open(r.url, "_blank", "noopener"); toast("Finish signing in the new tab, choosing " + atHandle(a)); }
            catch (e) { toast(e.message); } } }, "Connect for uploads")) : null))),
    d.accounts.some((a) => !a.active) ? h("p", { class: "muted small" }, "Not active yet: ", d.accounts.filter((a) => !a.active).map((a) => a.label).join(", "), ".") : null);
  const rows = d.jobs.map((j) => {
    const a = d.accounts.find((x) => x.account_id === j.account_id) || { label: j.account_id };
    const asset = d.assets.find((x) => x.asset_id === j.asset_id);
    const [label, tone] = PUB_STATE[j.state] || [j.state, ""];
    return h("tr", { class: "clickable", tabindex: "0", onclick: () => openJob(j.job_id), onkeydown: (e) => { if (e.key === "Enter") openJob(j.job_id); } },
      h("td", {}, h("div", { class: "t" }, asset ? asset.title : j.asset_id), h("div", { class: "s muted small" }, j.video_path.split("/").pop())),
      h("td", {}, a.label), h("td", { class: "small" }, ROUTE_LABEL[j.route].split(" (")[0].split(":")[0]),
      h("td", {}, chip(label, tone)), h("td", { class: "small muted" }, j.experiment_id ? [j.experiment_id, j.variant_id].filter(Boolean).join(" · ") : "—"),
      h("td", { class: "small muted" }, ago(j.updated_at_utc)));
  });
  const queue = panel("Queue", { eyebrow: "Drafts and uploads" }, rows.length
    ? h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, ["Video", "Account", "Route", "State", "Experiment", "Updated"].map((t) => h("th", {}, t)))), h("tbody", {}, rows)))
    : empty("Nothing queued", "Pick a registered version and a video, then the accounts. Every job waits for your approval.",
      h("button", { class: "btn small", type: "button", onclick: () => composer(d) }, "New post")));
  const how = panel("How publishing works", { flat: true },
    h("ol", { class: "steps small" },
      h("li", {}, "Choose the video, its version and any experiment, then the accounts. Each account gets its own draft and its own captions."),
      h("li", {}, "Open a draft: watch the preview, edit the platform's text, and fix anything the checks flag."),
      h("li", {}, "Approve by typing the account's handle. That approval covers this exact file and text; editing either cancels it."),
      h("li", {}, "The upload runs through the platform's official API. Where the API can't do it, the draft becomes a manual package you post yourself, then paste the link back."),
      h("li", {}, "Successful posts appear under Content, linked to the version and experiment.")),
    d.reveal_lock ? h("p", { class: "muted small" }, "Reveal lock: posts can be public, but nothing may name or show the game yet. Text that names it blocks any post others can see, and you confirm the video itself when you approve.") : null,
    d.public_posting ? null : h("p", { class: "muted small" }, "Public posting is off: YouTube uploads stay private and TikTok Direct Post stays 'Only me'."));
  const deep = location.hash.split("/")[2];  // #/publish/<job id> opens that job
  if (deep) setTimeout(() => openJob(decodeURIComponent(deep)), 0);
  return [head, h("div", { class: "grid cols-3" }, h("div", { class: "stack" }, queue, how), accounts)];
}

function composer(d) {
  const videoSel = h("select", { name: "video" }, h("option", { value: "" }, "Choose a video…"), d.videos.map((v) => h("option", { value: v.path }, `${v.file}${v.qc ? " · QC " + v.qc : ""}`)));
  const assetSel = h("select", { name: "asset" }, h("option", { value: "" }, "Choose a version…"), d.assets.map((a) => h("option", { value: a.asset_id }, `${a.title} · ${(a.language || "").toUpperCase()} ${a.version}`)));
  const expSel = h("select", { name: "exp" }, h("option", { value: "" }, "No experiment"), d.experiments.flatMap((e) => e.variants.map((v) => h("option", { value: `${e.experiment_id}|${v.variant_id}` }, `${e.title} · ${v.label || v.variant_id} (${v.role})`))));
  assetSel.addEventListener("change", () => {
    const a = d.assets.find((x) => x.asset_id === assetSel.value);
    const ef = a?.edit_file?.split(/[\\/]/).pop();
    const match = ef && d.videos.find((v) => v.file === ef);
    if (match) videoSel.value = match.path;
  });
  const picks = d.accounts.filter((a) => a.active).map((a) => {
    const box = h("input", { type: "checkbox", value: a.account_id });
    const route = h("select", { "aria-label": "Route for " + a.label }, a.routes.map((r) => h("option", { value: r, selected: a.credential !== "ready" ? r === "manual" : null }, ROUTE_LABEL[r])));
    return { a, box, route, el: h("div", { class: "list-row" }, h("label", { class: "check grow" }, box, h("span", {}, a.label, " ", h("span", { class: "muted small" }, atHandle(a)))), route) };
  });
  drawer(eyebrow("New post"), h("h2", {}, "What goes where"),
    h("p", { class: "muted small" }, "Creates one draft per account. Nothing uploads until you approve each one."),
    d.assets.length ? null : h("p", { class: "chip warn" }, "Register a version on the Content page first (Local renders → Register)."),
    h("div", { class: "form-grid" }, field("Version", assetSel, "wide"), field("Video file", videoSel, "wide"), field("Experiment variant (optional)", expSel, "wide")),
    h("h3", { class: "eyebrow section-title" }, "Accounts"), h("div", { class: "list" }, picks.map((p) => p.el)),
    h("div", { style: "margin-top:16px" }, h("button", { class: "btn primary", type: "button", onclick: async () => {
      const chosen = picks.filter((p) => p.box.checked);
      const [experiment_id, variant_id] = (expSel.value || "|").split("|");
      try {
        const r = await post("/api/publish/jobs", { asset_id: assetSel.value, video: videoSel.value, experiment_id, variant_id,
          account_ids: chosen.map((p) => p.a.account_id), routes: Object.fromEntries(chosen.map((p) => [p.a.account_id, p.route.value])) });
        toast(`${r.job_ids.length} draft${r.job_ids.length > 1 ? "s" : ""} created`); route(); openJob(r.job_ids[0]);
      } catch (e) { toast(e.message); }
    } }, "Create drafts")));
}

function toggle(label, value, opts = {}) {
  const el = h("input", { type: "checkbox", checked: value ? true : null, disabled: opts.disabled ? true : null });
  return { el, row: h("label", { class: "check" + (opts.disabled ? " muted" : "") }, el, h("span", {}, label, opts.note ? h("span", { class: "muted small" }, " · " + opts.note) : null)) };
}

async function openJob(id) {
  let d;
  try { d = await api("/api/publish/job/" + encodeURIComponent(id)); } catch (e) { toast(e.message); return; }
  const j = d.job, a = d.account, f = j.fields, plat = PLAT[j.platform].name;
  const editable = ["draft", "manual_pending", "failed"].includes(j.state);
  const [stLabel, stTone] = PUB_STATE[j.state] || [j.state, ""];
  const ctl = {};
  const inp = (k, type, v) => (ctl[k] = type === "textarea" ? h("textarea", { name: k, disabled: !editable || null }, v || "") : h("input", { name: k, type: type || "text", value: v ?? "", disabled: !editable || null }));
  let fieldsEl;
  if (j.platform === "youtube") {
    ctl.privacy = h("select", { disabled: !editable || null }, [["private", "Private"], ["unlisted", "Unlisted"], ["public", "Public"]].map(([v, t]) => h("option", { value: v, selected: f.privacy === v || null, disabled: !d.check.public_posting && v !== "private" ? true : null }, t)));
    ctl.made_for_kids = h("select", { disabled: !editable || null }, [["", "Choose…"], ["no", "No, it's not made for kids"], ["yes", "Yes, it's made for kids"]].map(([v, t]) => h("option", { value: v, selected: (f.made_for_kids === true ? "yes" : f.made_for_kids === false ? "no" : "") === v || null }, t)));
    const syn = toggle("Altered or synthetic content", f.synthetic_media, { note: "YouTube's disclosure for realistic AI or altered scenes" });
    ctl.synthetic_media = syn.el;
    fieldsEl = h("div", { class: "form-grid" }, field(`Title (${(f.title || "").length}/100)`, inp("title", "text", f.title), "wide"),
      field("Description", inp("description", "textarea", f.description), "wide"), field("Tags (comma separated)", inp("tags", "text", (f.tags || []).join(", ")), "wide"),
      field("Visibility", ctl.privacy), field("Made for kids", ctl.made_for_kids), h("div", { class: "wide" }, syn.row));
  } else if (j.platform === "tiktok") {
    const c = d.creator || {};
    const parts = [field("Caption", inp("caption", "textarea", f.caption), "wide")];
    const aigc = toggle("AI-generated content label", f.is_aigc, { note: "adds TikTok's 'Creator labeled as AI-generated'" });
    ctl.is_aigc = aigc.el;
    if (j.route === "buffer") {
      const dr = toggle("Save as a Buffer draft instead of posting", f.buffer_draft, { note: "you post it from Buffer" });
      ctl.buffer_draft = dr.el;
      parts.push(field("Public https link to the video file", inp("video_url", "text", f.video_url), "wide"),
        h("div", { class: "wide" }, h("p", { class: "muted small" }, "Buffer posts it with the account's own privacy (Buffer's TikTok app is audited, so posts can be public). Buffer's API can't take a file, only a link."), dr.row, aigc.row));
    } else if (j.route === "direct") {
      ctl.privacy = h("select", { disabled: !editable || null }, h("option", { value: "" }, "Choose who can view…"),
        (c.privacy_level_options || []).map((v) => h("option", { value: v, selected: f.privacy === v || null, disabled: (!d.check.public_posting || !d.check.tiktok_app_audited) && v !== "SELF_ONLY" ? true : null }, TT_PRIVACY[v] || v)));
      const cm = toggle("Allow comments", f.allow_comment, { disabled: c.comment_disabled, note: c.comment_disabled ? "off in this account's settings" : "" });
      const du = toggle("Allow Duet", f.allow_duet, { disabled: c.duet_disabled, note: c.duet_disabled ? "off in this account's settings" : "" });
      const stt = toggle("Allow Stitch", f.allow_stitch, { disabled: c.stitch_disabled, note: c.stitch_disabled ? "off in this account's settings" : "" });
      const com = toggle("Disclose commercial content", f.commercial);
      const yb = toggle("Your brand", f.your_brand, { note: "labelled 'Promotional content'" });
      const bc = toggle("Branded content", f.branded_content, { note: "labelled 'Paid partnership'; can't be private" });
      Object.assign(ctl, { allow_comment: cm.el, allow_duet: du.el, allow_stitch: stt.el, commercial: com.el, your_brand: yb.el, branded_content: bc.el });
      const sub = h("div", { class: "indent", hidden: !f.commercial || null }, yb.row, bc.row);
      com.el.addEventListener("change", () => { sub.hidden = !com.el.checked; });
      parts.unshift(h("div", { class: "wide creator" }, d.creator ? ["Posting to ", h("strong", {}, c.creator_nickname || "—"), " (@", c.creator_username || "", ")"] : h("span", { class: "chip bad" }, "Can't read this TikTok account: " + (d.creator_error || "connect it for uploads"))));
      parts.push(field("Who can view this video", ctl.privacy), h("div", { class: "wide" }, cm.row, du.row, stt.row, com.row, sub, aigc.row));
    } else {
      parts.push(h("div", { class: "wide" }, h("p", { class: "muted small" }, "The video goes to your TikTok inbox as a draft. Open the TikTok app's notification to finish the caption, privacy and AI label and post it. Copy the caption from here."), aigc.row));
    }
    fieldsEl = h("div", { class: "form-grid" }, parts);
  } else {
    const feed = toggle("Also show in the main feed", f.share_to_feed !== false);
    ctl.share_to_feed = feed.el;
    const dr = j.route === "buffer" ? toggle("Save as a Buffer draft instead of posting", f.buffer_draft, { note: "you post it from Buffer" }) : null;
    if (dr) ctl.buffer_draft = dr.el;
    fieldsEl = h("div", { class: "form-grid" }, field("Caption", inp("caption", "textarea", f.caption), "wide"),
      ["api", "buffer"].includes(j.route) ? field("Public https link to the video file", inp("video_url", "text", f.video_url), "wide") : null, h("div", { class: "wide" }, feed.row, dr ? dr.row : null));
  }
  const routeSel = h("select", { disabled: !editable || null }, d.routes.map((r) => h("option", { value: r, selected: r === j.route || null }, ROUTE_LABEL[r])));
  const collect = () => {
    const out = {};
    for (const [k, el] of Object.entries(ctl)) {
      if (el.type === "checkbox") out[k] = el.checked;
      else if (k === "tags") out[k] = el.value.split(",").map((t) => t.trim()).filter(Boolean);
      else if (k === "made_for_kids") out[k] = el.value === "yes" ? true : el.value === "no" ? false : null;
      else out[k] = el.value;
    }
    return out;
  };
  const save = async () => { await post("/api/publish/update", { job_id: j.job_id, fields: collect(), route: routeSel.value }); };
  const preview = h("div", { class: "phone" }, h("video", { src: "/api/publish/media/" + encodeURIComponent(j.job_id) + "#t=0.5", controls: true, playsinline: true, preload: "metadata" }),
    h("div", { class: "phone-cap" }, h("strong", {}, atHandle(a)), " ", (f.caption || f.title || "").slice(0, 140)));
  const errors = d.check.errors, warns = d.check.warnings, pr = d.check.probe || {};
  const facts = [pr.width ? `${pr.width}×${pr.height}` : null, pr.duration_s ? pr.duration_s.toFixed(1) + " s" : null, pr.fps ? pr.fps + " fps" : null,
    pr.bytes ? (pr.bytes / 1e6).toFixed(1) + " MB" : null, pr.video_codec, pr.audio_codec].filter(Boolean).join(" · ");
  const checks = h("div", { class: "checks" },
    errors.map((e) => h("div", { class: "check-row bad" }, "✕ ", e)), warns.map((w) => h("div", { class: "check-row warn" }, "! ", w)),
    !errors.length ? h("div", { class: "check-row ok" }, j.route === "manual" ? "✓ Checks pass. You post this one yourself." : "✓ Ready for approval") : null);

  let action = null;
  if (j.route === "manual" || ["sent_to_inbox", "in_buffer_drafts", "processing"].includes(j.state)) {
    const urlIn = h("input", { type: "text", placeholder: `Paste the ${plat} link once it's posted` });
    action = h("div", { class: "approve" },
      j.route === "manual" ? h("button", { class: "btn", type: "button", onclick: async () => {
        try { await save(); const r = await post("/api/publish/package", { job_id: j.job_id }); toast("Package in " + r.folder);
          await post("/api/open-folder", { folder: r.folder }).catch(() => {}); openJob(j.job_id); } catch (e) { toast(e.message); } } }, "Make manual package") : null,
      j.state === "sent_to_inbox" ? h("p", { class: "small" }, "In your TikTok inbox: open TikTok, tap the notification and finish the post. Then paste its link here.") : null,
      j.state === "in_buffer_drafts" ? h("p", { class: "small" }, "Saved in Buffer as a draft: open Buffer, post it, then paste its link here.") : null,
      h("div", { style: "display:flex;gap:8px;margin-top:10px" }, urlIn, h("button", { class: "btn small", type: "button", onclick: async () => {
        try { await post("/api/publish/mark-posted", { job_id: j.job_id, url: urlIn.value }); toast("Recorded and linked"); route(); openJob(j.job_id); } catch (e) { toast(e.message); } } }, "Mark as posted")));
  } else if (["draft", "failed"].includes(j.state) && !(j.state === "failed" && j.approval)) {
    const typed = h("input", { type: "text", placeholder: atHandle(a), "aria-label": "Type the account handle to approve", autocomplete: "off" });
    const consent = j.platform === "tiktok" ? h("input", { type: "checkbox" }) : null;
    const revealOk = d.check.needs_reveal_ok ? h("input", { type: "checkbox" }) : null;
    const go = h("button", { class: "btn primary", type: "button", disabled: errors.length ? true : null, onclick: async () => {
      try { await post("/api/publish/approve", { job_id: j.job_id, confirm: typed.value, consent: consent ? consent.checked : false, reveal_ok: revealOk ? revealOk.checked : false }); toast("Approved. Uploading…"); route(); setTimeout(() => openJob(j.job_id), 1200); }
      catch (e) { toast(e.message); } } }, "Approve and upload");
    const visibility = j.route === "buffer" ? (f.buffer_draft ? "a draft in Buffer (you post it from there)" : "a post via Buffer, with the account's own privacy (normally public)") : j.platform === "youtube" ? (f.privacy || "private") : j.platform === "tiktok" ? (j.route === "inbox" ? "a draft in your TikTok inbox (you choose who can view in the app)" : TT_PRIVACY[f.privacy] || "(choose who can view first)") : "public (Instagram has no private posts)";
    action = h("div", { class: "approve" },
      h("p", {}, "Uploads ", h("strong", {}, j.video_path.split("/").pop()), " to ", h("strong", {}, `${a.label} (${atHandle(a)})`), " as ", h("strong", {}, visibility), "."),
      j.platform === "tiktok" ? [h("p", { class: "muted small" }, "After you approve, TikTok can take a few minutes to process the video."),
        h("label", { class: "check" }, consent, h("span", {}, d.tiktok_declaration))] : null,
      revealOk ? h("label", { class: "check" }, revealOk, h("span", {}, "Reveal lock: I've watched this video and checked its text. Nothing names or shows the game (title, logo, place link or anything that identifies it).")) : null,
      h("div", { style: "display:flex;gap:8px;margin-top:10px;flex-wrap:wrap" }, typed, go),
      errors.length ? h("p", { class: "muted small" }, "Fix the checks above first. Save your edits to re-check.") : null);
  } else if (j.state === "failed" && j.approval) {
    action = h("div", { class: "approve" }, h("p", { class: "small" }, "The approved upload failed (see the log). Retry uses the same approval if nothing changed."),
      h("button", { class: "btn", type: "button", onclick: async () => { try { await post("/api/publish/retry", { job_id: j.job_id }); toast("Retrying…"); setTimeout(() => openJob(j.job_id), 1200); } catch (e) { toast(e.message); } } }, "Retry upload"));
  }
  const dr = drawer(eyebrow(`${plat} · ${a.label}`), h("h2", {}, d.asset ? d.asset.title : j.asset_id), h("div", { style: "display:flex;gap:8px;flex-wrap:wrap" }, chip(stLabel, stTone), d.check.reveal_lock ? chip("Reveal lock", "warn") : null, chip({ private: "Private", in_app: "Visibility set in TikTok", visible: "Others can see it" }[d.check.visibility] || d.check.visibility, d.check.visibility === "visible" ? "accent" : ""),
      j.experiment_id ? chip([j.experiment_id, j.variant_id].filter(Boolean).join(" · "), "accent") : null),
    h("div", { class: "pub-grid" }, preview, h("div", {},
      h("dl", { class: "kv tight" }, h("dt", {}, "Version"), h("dd", {}, j.asset_id), h("dt", {}, "File"), h("dd", {}, h("span", { class: "code" }, j.video_path)),
        h("dt", {}, "Video"), h("dd", {}, facts || "—"), j.result?.url ? [h("dt", {}, "Link"), h("dd", {}, h("a", { href: j.result.url, target: "_blank", rel: "noreferrer" }, j.result.url))] : null,
        j.approval ? [h("dt", {}, "Approved"), h("dd", {}, new Date(j.approval.at).toLocaleString())] : null),
      field("Route", routeSel))),
    h("h3", { class: "eyebrow section-title" }, `${plat} text and settings`), fieldsEl,
    editable ? h("div", { style: "margin-top:12px;display:flex;gap:8px" }, h("button", { class: "btn small", type: "button", onclick: async () => { try { await save(); toast("Saved"); openJob(j.job_id); } catch (e) { toast(e.message); } } }, "Save and re-check"),
      h("button", { class: "btn ghost small", type: "button", onclick: async () => { if (!confirm("Delete this draft?")) return; await post("/api/publish/delete", { job_id: j.job_id }); closeDrawer(); route(); } }, "Delete draft")) : null,
    h("h3", { class: "eyebrow section-title" }, "Checks"), checks,
    action ? [h("h3", { class: "eyebrow section-title" }, j.route === "manual" ? "Post it yourself" : "Approve"), action] : null,
    j.log?.length ? h("details", { class: "more", style: "margin-top:14px" }, h("summary", {}, `Log (${j.log.length})`),
      h("ul", { class: "small muted" }, j.log.slice().reverse().map((x) => h("li", {}, new Date(x.at).toLocaleString(), " · ", x.msg)))) : null);
  dr.classList.add("wide");
  if (["uploading", "processing", "approved"].includes(j.state)) setTimeout(() => { if (document.querySelector(".drawer")) openJob(j.job_id); }, 3000);
}

// ------------------------------------------------------------------ router
const ROUTES = { overview: pageOverview, content: pageContent, research: pageResearch, game: pageGame, experiments: pageExperiments, publish: pagePublish, settings: pageSettings };
let routeSeq = 0;
async function route() {
  const id = (location.hash.replace(/^#\/?/, "").split(/[/?#]/)[0]) || "overview";
  const page = ROUTES[id] ? id : "overview";
  const seq = ++routeSeq;
  renderNav(page);
  document.title = `${page[0].toUpperCase() + page.slice(1)} · Slugshot`;
  try {
    const nodes = await ROUTES[page]();
    if (seq !== routeSeq) return;
    charts = [];
    $main.replaceChildren(...[].concat(nodes).flat(3).filter(Boolean));
    requestAnimationFrame(() => charts.forEach((d) => d()));
  } catch (e) {
    if (seq !== routeSeq) return;
    $main.replaceChildren(...topbar(page), panel("Couldn't load this page", {}, h("p", { class: "muted" }, e.message)));
  }
}
window.addEventListener("hashchange", route);

(async function start() {
  META = await api("/api/meta");
  await refreshStatus();
  route();
  // Refresh stale sources when the app opens (if daily refresh is on), then keep the status line current.
  if (STATUS && STATUS.auto_refresh && !STATUS.sync.running && !FIXTURE &&
      STATUS.sources.some((x) => x.credential === "ready" && ["due", "stale", "never synced"].includes(x.freshness))) {
    post("/api/sync").then(pollUntilDone).catch(() => {});
  }
  setInterval(refreshStatus, 30000);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
})();
