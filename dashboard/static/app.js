// Slugshot dashboard front end. No build step, no dependencies. All text goes through text nodes.
// Principle (owner, 2026-11-25): the minimum useful information by default; detail only when you go looking for it.
const TOKEN = document.querySelector('meta[name="dash-token"]').content;
const FIXTURE = document.querySelector('meta[name="dash-fixture"]').content === "true";
const EXPAND = new URLSearchParams(location.search).get("expand") === "1";  // screenshots: open every section
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
function icon(d, size = 18) {
  return s("svg", { viewBox: "0 0 24 24", width: size, height: size, fill: "none", stroke: "currentColor", "stroke-width": 1.8,
    "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" }, [].concat(d).map((p) => s("path", { d: p })));
}
const store = {
  get(k, d) { try { const v = localStorage.getItem("ss-" + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem("ss-" + k, JSON.stringify(v)); } catch (e) { /* private window */ } },
};
async function api(path, params) {
  const q = params ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== "")) : "";
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
  youtube: { name: "YouTube", short: "YT", color: "var(--series-youtube)" },
  tiktok: { name: "TikTok", short: "TT", color: "var(--series-tiktok)" },
  instagram: { name: "Instagram", short: "IG", color: "var(--series-instagram)" },
  roblox: { name: "Roblox", short: "RBX", color: "var(--series-roblox)" },
};
function n(v, unit) {
  if (v == null || v === "") return "—";
  if (unit === "fraction") return (v * 100).toFixed(v < 0.1 ? 1 : 0) + "%";
  if (unit === "percent") return v.toFixed(1) + "%";
  if (unit === "seconds") return (v >= 100 ? Math.round(v) : v.toFixed(1)) + " s";
  if (unit === "minutes") return v >= 120 ? (v / 60).toLocaleString(undefined, { maximumFractionDigits: v >= 6000 ? 0 : 1 }) + " h" : Math.round(v) + " min";
  if (unit === "Robux") return compact(v) + " R$";
  return compact(v);
}
function compact(v) {
  const a = Math.abs(v);
  if (a >= 1e6) return (v / 1e6).toFixed(a >= 1e7 ? 0 : 1) + "M";
  if (a >= 1e4) return (v / 1e3).toFixed(a >= 1e5 ? 0 : 1) + "K";
  return Number.isInteger(v) || a >= 100 ? Math.round(v).toLocaleString() : v.toLocaleString(undefined, { maximumFractionDigits: 1 });
}
const signed = (v, unit) => (v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + n(Math.abs(v), unit));
// "25 Nov 16:40": a short local date and time for telling videos apart.
const when = (iso) => new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
function ago(iso) {
  if (!iso) return "never";
  const m = (Date.now() - new Date(iso).getTime()) / 60000;
  if (m < 2) return "just now";
  if (m < 60) return Math.round(m) + " min ago";
  if (m < 48 * 60) return Math.round(m / 60) + " h ago";
  return Math.round(m / 1440) + " days ago";
}
function day(iso, year) {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? iso + "T00:00:00Z" : iso);
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", ...(year ? { year: "numeric" } : {}), timeZone: "UTC" });
}
const dot = (p) => h("span", { class: "swatch", style: `background:${PLAT[p]?.color}` });
const plat = (p) => h("span", { class: "plat" }, dot(p), PLAT[p]?.name || p);
const lang = (l) => (l ? h("span", { class: "lang" }, l.toUpperCase()) : null);
const tip = (text) => h("span", { class: "tip", title: text, tabindex: "0", "aria-label": text }, "i");
const chip = (text, tone) => h("span", { class: "chip " + (tone || "") }, text);
const atHandle = (a) => (a && a.handle ? "@" + a.handle.replace(/^@/, "") : "no handle set");
let META = null;
const mdef = (id) => META?.metrics.metrics.find((m) => m.id === id) || { id, label: id, unit: "" };
function delta(cur, prev, periodLabel) {
  if (cur == null || prev == null) return null;
  if (prev === 0) return cur === 0 ? h("span", { class: "delta flat" }, "no change") : h("span", { class: "delta up" }, `+${n(cur)} vs ${periodLabel}`);
  const pct = ((cur - prev) / prev) * 100;
  const cls = Math.abs(pct) < 0.5 ? "flat" : pct > 0 ? "up" : "down";
  return h("span", { class: "delta " + cls }, `${pct > 0 ? "+" : pct < 0 ? "−" : ""}${Math.abs(pct).toFixed(Math.abs(pct) < 10 ? 1 : 0)}%`, h("span", { class: "muted", style: "font-weight:500" }, ` vs ${periodLabel}`));
}
function panel(title, opts, ...body) {
  opts = opts || {};
  return h("section", { class: "panel", id: opts.id || null },
    title || opts.actions ? h("div", { class: "panel-head" }, h("h2", {}, title), opts.tip ? tip(opts.tip) : null, opts.hint ? h("span", { class: "hint" }, opts.hint) : null,
      h("span", { class: "grow" }), opts.actions || null) : null, body);
}
function sect(title, sub, opts, ...body) {
  return h("details", { class: "sect", open: opts?.open || EXPAND || null, id: opts?.id || null },
    h("summary", {}, h("div", { class: "grow" }, h("h2", {}, title), sub ? h("div", { class: "s" }, sub) : null), opts?.right || null), h("div", { class: "body" }, body));
}
function empty(title, text, action) {
  return h("div", { class: "empty" }, h("strong", {}, title), text ? h("span", {}, text) : null, action || null);
}
function seg(options, value, onChange, label) {
  const el = h("div", { class: "seg", role: "group", "aria-label": label }, options.map(([v, t]) =>
    h("button", { type: "button", "aria-pressed": String(v === value), onclick: (e) => {
      el.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget)));
      onChange(v);
    } }, t)));
  return el;
}
function field(label, input, cls) { return h("label", { class: "field " + (cls || "") }, h("span", {}, label), input); }

// ------------------------------------------------------------------ charts
// Lines for change over time; series coloured by platform identity (fixed, never by rank).
let charts = [];
function lineChart(series, opts = {}) {
  const box = h("div", { class: "chart" });
  const live = series.filter((x) => x.points && x.points.length);
  if (!live.length) return empty(opts.emptyTitle || "Nothing to chart yet", opts.emptyText || "");
  const legend = live.length > 1 ? h("div", { class: "legend" }, live.map((x) => h("span", {}, h("span", { class: "swatch", style: `background:${x.color}` }), x.label))) : null;
  const tableBtn = h("button", { class: "btn ghost small", type: "button" }, "Table");
  const wrap = h("div", {}, h("div", { style: "display:flex;align-items:center;gap:10px;margin-bottom:6px;min-height:28px" }, legend, h("span", { style: "flex:1" }), tableBtn), box);
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
    const W = Math.max(280, box.clientWidth || 640), H = opts.height || 200;
    const pad = { l: 44, r: live.length <= 4 && live.length > 1 ? 86 : 14, t: 8, b: 24 };
    const vals = live.flatMap((x) => x.points.map((p) => p.v)).filter((v) => v != null);
    const min = Math.min(0, ...vals);
    const step = niceStep((Math.max(...vals) - min) / 4 || 1);
    const ticks = Math.max(1, Math.ceil((Math.max(...vals) - min) / step));
    const max = min + ticks * step;
    const X = (i) => pad.l + (dates.length < 2 ? (W - pad.l - pad.r) / 2 : (i / (dates.length - 1)) * (W - pad.l - pad.r));
    const Y = (v) => pad.t + (1 - (v - min) / (max - min)) * (H - pad.t - pad.b);
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img", "aria-label": opts.label || "chart" });
    for (let i = 0; i <= ticks; i++) {
      const v = min + step * i;
      svg.append(s("line", { class: "gridline", x1: pad.l, x2: W - pad.r, y1: Y(v), y2: Y(v) }),
        s("g", { class: "axis" }, s("text", { x: pad.l - 8, y: Y(v) + 4, "text-anchor": "end" }, n(v, opts.unit))));
    }
    const xStep = Math.max(1, Math.ceil(dates.length / Math.floor((W - pad.l - pad.r) / 70)));
    dates.forEach((d, i) => { if (i % xStep === 0) svg.append(s("g", { class: "axis" }, s("text", { x: X(i), y: H - 5, "text-anchor": "middle" }, day(d)))); });
    const ends = [];
    for (const x of live) {
      const pts = dates.map((d, i) => [i, x.points.find((p) => p.d === d)?.v]).filter(([, v]) => v != null);
      svg.append(s("path", { class: "line", stroke: x.color, d: pts.map(([i, v], k) => `${k ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join("") }));
      if (pts.length === 1) svg.append(s("circle", { cx: X(pts[0][0]), cy: Y(pts[0][1]), r: 4, fill: x.color }));
      const last = pts[pts.length - 1];
      if (last && live.length > 1 && live.length <= 4) ends.push({ y: Y(last[1]), x: X(last[0]), label: x.label });
    }
    ends.sort((a, b) => a.y - b.y).forEach((e, i, arr) => { if (i && e.y - arr[i - 1].y < 14) e.y = arr[i - 1].y + 14; });
    ends.forEach((e) => svg.append(s("text", { class: "endlabel", x: e.x + 8, y: e.y + 4 }, e.label)));
    const cross = s("line", { class: "cross", y1: pad.t, y2: H - pad.b, visibility: "hidden" });
    const hit = s("rect", { class: "hit", x: pad.l, y: 0, width: Math.max(1, W - pad.l - pad.r), height: H });
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
      tipEl.style.left = Math.min((X(i) / W) * r.width + 14, r.width - 160) + "px";
      tipEl.style.top = "6px";
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
let resizeT;
window.addEventListener("resize", () => { clearTimeout(resizeT); resizeT = setTimeout(() => charts.forEach((d) => d()), 150); });
// Horizontal bars for a breakdown (one platform colour per row); rows can be clickable.
function bars(rows, opts = {}) {
  rows = rows.filter((r) => r.v != null);
  if (!rows.length) return empty(opts.emptyTitle || "Nothing to show yet", opts.emptyText || "");
  const max = Math.max(...rows.map((r) => Math.abs(r.v))) || 1;
  const diverging = opts.diverging && rows.some((r) => r.v < 0);
  return h("div", { class: "bars" }, rows.map((r) => {
    const w = (100 * Math.abs(r.v)) / max / (diverging ? 2 : 1);
    const fill = h("div", { class: "bar-fill" + (r.v < 0 ? " neg" : ""), style: diverging ? (r.v < 0 ? `right:50%;width:${w}%` : `left:50%;width:${w}%`) + (r.color && r.v >= 0 ? `;background:${r.color}` : "") : `width:${w}%;background:${r.color || "var(--accent)"}` });
    const inner = [h("span", { style: "display:flex;align-items:center;gap:7px;overflow:hidden;white-space:nowrap" }, r.prefix || null, h("span", { style: "overflow:hidden;text-overflow:ellipsis" }, r.label)),
      h("div", { class: "bar-track" + (diverging ? " div" : "") }, fill), h("span", { class: "num", style: "text-align:right" }, opts.signed ? signed(r.v, opts.unit) : n(r.v, opts.unit))];
    return r.onclick ? h("button", { class: "bar-row", type: "button", onclick: r.onclick, title: r.title || null }, inner) : h("div", { class: "bar-row" }, inner);
  }));
}

// ------------------------------------------------------------------ night sky (Jami: NightSkyBackdrop + ShootingStars, ported)
function seeded(seed) {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
function hashOf(text) {
  let x = 2166136261;
  for (let i = 0; i < text.length; i += 1) { x ^= text.charCodeAt(i); x = Math.imul(x, 16777619); }
  return x >>> 0;
}
const TINTS = [["violet", 0.5], ["ice", 0.3], ["green", 0.12], ["gold", 0.08]];
function starTimings(count, seed) {
  const random = seeded(hashOf(`${seed}:timing`));
  const duration = Math.round((16 + random() * 4) * 10) / 10;
  const slots = Math.max(1, Math.ceil(count * 0.6));
  const offsets = Array.from({ length: slots }, (_, k) => (k / slots) * duration + random() * 1.5);
  return Array.from({ length: count }, (_, i) => ({ duration, delay: Math.round((offsets[i % slots] + random() * 0.6) * 10) / 10 }));
}
function starPath(seed, index, pass) {
  const random = seeded(hashOf(`${seed}:${index}:${pass}`));
  const top = Math.round(random() * 70 * 10) / 10, left = Math.round((15 + random() * 85) * 10) / 10;
  const angle = Math.round((14 + random() * 20) * 10) / 10;
  const base = 90 + random() * 90, fireball = random() < 0.14;
  const length = Math.round(base * (fireball ? 1.6 : 1));
  let roll = random(), tint = "violet", acc = 0;
  for (const [t, w] of TINTS) { acc += w; if (roll < acc) { tint = t; break; } }
  return { top, left, angle, length, travel: Math.round(length * (1.7 + random() * 0.8)), tint, fireball };
}
function nightSky() {
  const sky = h("div", { class: "sky", "aria-hidden": "true" });
  const random = seeded(7);
  for (let i = 0; i < 120; i++) {
    sky.append(h("span", { class: "dust", style: `left:${random() * 100}%;top:${random() * 100}%;width:${0.6 + random() * 1.9}px;height:${0.6 + random() * 1.9}px;--o:${0.2 + random() * 0.65};--delay:${random() * 8}s;--t:${3 + random() * 6}s` }));
  }
  starTimings(4, "first-night").forEach((tm, index) => {
    const timing = `animation-duration:${tm.duration}s;animation-delay:${tm.delay}s`;
    const el = h("span", {}, h("span", { class: "shooting-star-tail", style: timing }), h("span", { class: "shooting-star-head", style: timing }));
    let pass = 0;
    const place = () => {
      const p = starPath("first-night", index, pass);
      el.className = `shooting-star shooting-star--${p.tint}${p.fireball ? " shooting-star--fireball" : ""}`;
      el.setAttribute("style", `top:${p.top}%;left:${p.left}%;width:${p.length}px;${timing};--shooting-angle:${p.angle}deg;--shooting-travel:${-p.travel}px`);
    };
    // A streak lands somewhere new each time its cycle comes round, while it is invisible (as in Jami).
    el.addEventListener("animationiteration", (e) => { if (e.target === el) { pass += 1; place(); } });
    place();
    sky.append(el);
  });
  document.body.prepend(sky);
}

// ------------------------------------------------------------------ shell
const ICONS = {
  overview: ["M4 13h6V4H4zM14 20h6v-9h-6zM4 20h6v-3H4zM14 7h6V4h-6z"],
  content: ["M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5z", "M10 9.2v5.6l4.6-2.8z"],
  roblox: ["M7 9h10a4 4 0 0 1 3.9 4.9l-.8 3.3a2 2 0 0 1-3.4.9L14.6 16H9.4l-2.1 2.1a2 2 0 0 1-3.4-.9l-.8-3.3A4 4 0 0 1 7 9z", "M8 12v2.5M6.8 13.2h2.5", "M15.5 12.5h.01M17.5 14h.01"],
  publish: ["M12 15V4", "M7.5 8.5 12 4l4.5 4.5", "M5 14v3.5A2.5 2.5 0 0 0 7.5 20h9a2.5 2.5 0 0 0 2.5-2.5V14"],
  settings: ["M12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z", "M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2-1.2L14.3 3h-4.6l-.3 2.7a7 7 0 0 0-2 1.2l-2.3-1-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2 1.2l.3 2.7h4.6l.3-2.7a7 7 0 0 0 2-1.2l2.3 1 2-3.4-2-1.5c.1-.4.1-.8.1-1.2z"],
  refresh: ["M20 11a8 8 0 0 0-14.6-4.5L4 8", "M4 4v4h4", "M4 13a8 8 0 0 0 14.6 4.5L20 16", "M20 20v-4h-4"],
  close: ["M6 6l12 12M18 6L6 18"],
  back: ["M15 6l-6 6 6 6"],
  go: ["M9 6l6 6-6 6"],
  external: ["M14 4h6v6", "M20 4l-9 9", "M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"],
};
const PAGES = [["overview", "Overview"], ["content", "Content"], ["publish", "Publish"], ["roblox", "Roblox"]];
let STATUS = null;
const syncLine = h("div", { class: "sync-line" });
function renderNav(active) {
  const item = ([id, label]) => h("a", { class: "nav-item", href: "#/" + id, "aria-current": active === id ? "page" : null }, icon(ICONS[id]), h("span", {}, label));
  $nav.replaceChildren(
    h("div", { class: "brand" }, h("img", { src: "/static/icons/icon.svg", width: 26, height: 26, alt: "" }), h("span", { class: "brand-name" }, "Slugshot")),
    ...PAGES.map(item), h("div", { class: "nav-foot" }, item(["settings", "Settings"]), syncLine));
  paintSync();
}
function paintSync() {
  if (!STATUS) return;
  const src = STATUS.sources.filter((x) => x.credential === "ready");
  const bad = STATUS.sources.filter((x) => x.credential === "ready" && (x.last_status === "failed" || x.last_status === "needs_auth" || x.freshness === "stale"));
  const last = src.map((x) => x.last_success_utc).filter(Boolean).sort().pop();
  const tone = STATUS.sync.running ? "ok pulse" : bad.length ? "warn" : src.length ? "ok" : "";
  syncLine.replaceChildren(h("span", { class: "dot " + tone }),
    STATUS.sync.running ? "Refreshing…" : !src.length ? "No accounts connected" : bad.length ? `${bad.length} source${bad.length > 1 ? "s need" : " needs"} attention` : "Updated " + ago(last));
}
async function refreshStatus() {
  try { STATUS = await api("/api/status"); paintSync(); } catch (e) { /* server restarting */ }
  return STATUS;
}
async function pollUntilDone() {
  for (let i = 0; i < 120; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    const st = await refreshStatus();
    if (st && !st.sync.running) { route(); return; }
  }
}
function pageHead(title, opts = {}) {
  const refresh = h("button", { class: "btn icon-btn ghost", type: "button", title: "Refresh data now", "aria-label": "Refresh data now",
    onclick: async () => { await post("/api/sync"); toast("Refreshing connected accounts…"); pollUntilDone(); } }, icon(ICONS.refresh));
  return [FIXTURE ? h("div", { class: "fixture-banner" }, "Fixture data: test values, not real performance.") : null,
    h("header", { class: "page-head" },
      h("div", {}, opts.back ? h("a", { class: "back", href: opts.back[0] }, icon(ICONS.back, 14), opts.back[1]) : null,
        h("h1", {}, title), opts.sub ? h("div", { class: "sub" }, opts.sub) : null),
      h("div", { class: "grow" }), opts.right || null, opts.noRefresh ? null : refresh)];
}

// ------------------------------------------------------------------ filters (Overview, drill-downs, account pages)
const F = Object.assign({ range: "30", start: "", end: "", platform: "", account: "", language: "" }, store.get("filters2", {}));
const RANGE_LABEL = { 7: "previous 7 days", 30: "previous 30 days", 90: "previous 90 days" };
function fParams(extra = {}) {
  const p = { ...F, ...extra };
  return p.range === "custom" ? { start: p.start, end: p.end, platform: p.platform, account: p.account, language: p.language }
    : { range: p.range, platform: p.platform, account: p.account, language: p.language };
}
function setF(patch) { Object.assign(F, patch); store.set("filters2", F); route(); }
function filterBar(opts = {}) {
  const accts = (META?.accounts || []).filter((a) => a.active && ["youtube", "tiktok", "instagram"].includes(a.platform) && (!F.platform || a.platform === F.platform));
  const from = h("input", { type: "date", value: F.start || "", "aria-label": "From" });
  const to = h("input", { type: "date", value: F.end || "", "aria-label": "To" });
  const custom = h("span", { class: "filters", hidden: F.range !== "custom" || null }, from, h("span", { class: "muted small" }, "to"), to,
    h("button", { class: "btn small", type: "button", onclick: () => from.value && setF({ range: "custom", start: from.value, end: to.value || new Date().toISOString().slice(0, 10) }) }, "Apply"));
  return h("div", { class: "filters" },
    seg([["7", "7d"], ["30", "30d"], ["90", "90d"], ["all", "All time"], ["custom", "Custom"]], F.range,
      (v) => (v === "custom" ? (custom.hidden = false, F.range = "custom") : setF({ range: v })), "Date range"), custom,
    opts.platform === false ? null : h("select", { "aria-label": "Platform", onchange: (e) => setF({ platform: e.target.value, account: "" }) },
      [["", "All platforms"], ["youtube", "YouTube"], ["tiktok", "TikTok"], ["instagram", "Instagram"]].map(([v, t]) => h("option", { value: v, selected: F.platform === v }, t))),
    opts.account === false ? null : h("select", { "aria-label": "Account", onchange: (e) => setF({ account: e.target.value }) },
      h("option", { value: "" }, "All accounts"), accts.map((a) => h("option", { value: a.account_id, selected: F.account === a.account_id }, a.label))),
    opts.language === false ? null : seg([["", "All"], ["en", "EN"], ["es", "ES"]], F.language, (v) => setF({ language: v }), "Language"));
}
const periodLabel = () => RANGE_LABEL[F.range] || "previous period";
function rangeDates() {  // explicit dates for endpoints that take start/end (Roblox)
  const iso = (t) => new Date(t).toISOString().slice(0, 10);
  if (F.range === "custom") return { start: F.start, end: F.end };
  if (F.range === "all") return { start: "2020-01-01", end: iso(Date.now()) };
  return { start: iso(Date.now() - (Number(F.range) - 1) * 86400000), end: iso(Date.now()) };
}
const acctLabel = (id) => (META?.accounts || []).find((a) => a.account_id === id)?.label || id;

// ------------------------------------------------------------------ Overview
const VIEWS_TIP = "Combined platform-reported views: added across YouTube, TikTok and Instagram. Not unique viewers; each platform counts a view its own way. TikTok and Instagram figures for a period come from daily snapshots of each video.";
const FOLLOW_TIP = "Combined follower and subscriber counts of the selected accounts. Not unique people: one person can follow several accounts.";
async function pageOverview() {
  const d = await api("/api/analytics", fParams());
  const T = d.totals, v = T.views, f = T.followers, w = T.watch_time_minutes;
  const watchLine = w.value != null
    ? [h("span", {}, "Watch time"), h("b", {}, n(w.value, "minutes")), delta(w.value, w.prev, periodLabel()),
      w.missing.length ? h("span", { class: "muted small", style: "margin-left:auto" }, `${w.covered.length} of ${w.covered.length + w.missing.length} accounts report it`) : null]
    : [h("span", { class: "muted" }, "Watch time appears once an account reports it")];
  const hero = h("div", { class: "hero" },
    h("a", { class: "metric", href: "#/overview/views" },
      h("div", { class: "label" }, "Views", tip(VIEWS_TIP), h("span", { class: "go" }, icon(ICONS.go, 16))),
      h("div", { class: "value" + (v.value == null ? " none" : "") }, v.value == null ? "—" : n(v.value)),
      h("div", { class: "foot" }, v.value == null ? "No views reported in this range yet" : delta(v.value, v.prev, periodLabel()) || h("span", {}, "Platform-reported, combined"),
        v.partial.length ? h("span", {}, "· partly estimated") : null),
      h("div", { class: "secondary" }, watchLine)),
    h("a", { class: "metric", href: "#/overview/followers" },
      h("div", { class: "label" }, "Followers", tip(FOLLOW_TIP), h("span", { class: "go" }, icon(ICONS.go, 16))),
      h("div", { class: "value" + (f.value == null ? " none" : "") }, f.value == null ? "—" : n(f.value)),
      h("div", { class: "foot" }, f.change != null ? h("span", { class: "delta " + (f.change > 0 ? "up" : f.change < 0 ? "down" : "flat") }, signed(f.change) + (f.growth != null ? ` (${f.growth > 0 ? "+" : ""}${f.growth}%)` : "")) : null,
        h("span", {}, f.change != null ? (d.all_time ? "since the accounts began" : "in this range") : "Combined across accounts")),
      h("div", { class: "secondary" }, h("span", { class: "muted" }, `${f.covered.length} account${f.covered.length === 1 ? "" : "s"} counted`, f.missing.length ? ` · ${f.missing.map(acctLabel).join(", ")} not reported` : ""))));
  const series = d.platforms.filter((p) => p.stats.series.views?.length).map((p) => ({ label: PLAT[p.platform].name, color: PLAT[p.platform].color, points: p.stats.series.views }));
  const chart = series.length ? panel("Views per day", { actions: h("a", { class: "btn ghost small", href: "#/overview/views" }, "Details") }, lineChart(series, { label: "Views per day by platform", height: 180 })) : null;
  return [pageHead("Overview", { right: filterBar() }), h("div", { class: "stack" }, hero, chart, accountsPanel(d))];
}
function accountsPanel(d) {
  return panel("Accounts", { hint: d.all_time ? "all time" : `${day(d.start)} – ${day(d.end)}` },
    d.accounts.length ? h("div", { class: "rows" }, d.accounts.map((a) => {
      const st = a.stats;
      return h("a", { class: "row", href: "#/account/" + a.account_id },
        dot(a.platform), h("div", { class: "grow" }, h("div", { class: "t" }, a.label, " ", lang(a.language)), h("div", { class: "s" }, atHandle(a))),
        h("div", { class: "r" }, h("div", {}, n(st.followers)), h("div", { class: "s" }, "followers")),
        h("div", { class: "r" }, h("div", {}, n(st.views)), h("div", { class: "s" }, "views")),
        h("span", { class: "muted" }, icon(ICONS.go, 16)));
    })) : empty("No accounts match these filters"));
}

// Views drill-down
async function pageViews() {
  const d = await api("/api/analytics", fParams());
  const T = d.totals;
  const eng = (m) => T.engagement[m].value;
  const kpis = h("div", { class: "kpis" },
    kpi("Views", n(T.views.value), delta(T.views.value, T.views.prev, periodLabel()), VIEWS_TIP),
    kpi("Watch time", n(T.watch_time_minutes.value, "minutes"), T.watch_time_minutes.covered.length ? `${T.watch_time_minutes.covered.map(acctLabel).join(", ")}` : "not reported yet"),
    kpi("Avg view duration", n(T.avg_view.value, "seconds"), T.avg_view.basis === "period" ? `in range · ${T.avg_view.covered.map(acctLabel).join(", ")}` : T.avg_view.basis === "lifetime" ? "lifetime average per video (no daily data)" : "not reported yet"),
    kpi("Likes", n(eng("likes"))), kpi("Comments", n(eng("comments"))), kpi("Shares", n(eng("shares"))), kpi("Saves", n(eng("saves"))));
  return [pageHead("Views", { back: ["#/overview", "Overview"], right: filterBar() }), h("div", { class: "stack" }, kpis,
    panel("Views over time", { tip: VIEWS_TIP }, lineChart(trendSeries(d, "views"), { label: "Views over time" })),
    h("div", { class: "grid cols-2" },
      panel("By platform", { hint: "click to narrow" }, bars(d.platforms.map((p) => ({ label: PLAT[p.platform].name, prefix: dot(p.platform), v: p.stats.views, color: PLAT[p.platform].color,
        onclick: () => setF({ platform: F.platform === p.platform ? "" : p.platform, account: "" }) })), { emptyTitle: "No views reported yet" })),
      panel("By account", { hint: "click to open" }, bars(d.accounts.map((a) => ({ label: a.label, prefix: dot(a.platform), v: a.stats.views, color: PLAT[a.platform].color,
        onclick: () => { location.hash = "#/account/" + a.account_id; } })), { emptyTitle: "No views reported yet" }))),
    videosPanel(d.videos, "views"), compareSection(d), countingNote(d))];
}
function kpi(label, value, sub, tipText, onclick) {
  const kids = [h("div", { class: "l" }, label, tipText ? tip(tipText) : null), h("div", { class: "v" + (value === "—" ? " none" : "") }, value), sub ? h("div", { class: "s" }, sub) : null];
  return onclick ? h("button", { class: "kpi", type: "button", onclick }, kids) : h("div", { class: "kpi" }, kids);
}
function trendSeries(d, metric) {
  if (F.account) return d.accounts.map((a) => ({ label: a.label, color: PLAT[a.platform].color, points: a.stats.series[metric] || [] }));
  if (F.platform) {
    const shades = ["1", "0.6"];
    return d.accounts.map((a, i) => ({ label: a.label, color: `color-mix(in srgb, ${PLAT[a.platform].color} ${Math.round(Number(shades[i % 2]) * 100)}%, var(--muted))`, points: a.stats.series[metric] || [] }));
  }
  return d.platforms.map((p) => ({ label: PLAT[p.platform].name, color: PLAT[p.platform].color, points: p.stats.series[metric] || [] }));
}
function countingNote(d) {
  const est = d.totals.views.estimated.map(acctLabel), part = d.totals.views.partial.map(acctLabel);
  return h("details", { class: "more" }, h("summary", {}, "How these numbers are counted"),
    h("div", { class: "small muted", style: "display:grid;gap:6px;max-width:80ch" },
      h("div", {}, "Views are added across platforms as reported. They are not unique viewers, and each platform counts a view differently."),
      h("div", {}, "YouTube gives daily analytics. TikTok and Instagram give lifetime totals per video, so a period's views are the growth between daily snapshots."),
      est.length ? h("div", {}, "From snapshots: " + est.join(", ") + ".") : null,
      part.length ? h("div", {}, "Partly measured (tracking began inside this range): " + part.join(", ") + ".") : null,
      h("div", {}, "Each video's figure comes from one source, the platform's own API first, then Buffer, so nothing is counted twice. Missing figures stay blank, never zero.")));
}
function videosPanel(videos, mode) {
  let sort = store.get("videoSort", "period");
  const box = h("div", {});
  const paint = () => {
    const key = (v) => mode === "followers" ? v.metrics.followers_gained : sort === "period" ? v.views_in_period : v.metrics.views;
    const rows = videos.filter((v) => key(v) != null).sort((a, b) => key(b) - key(a)).slice(0, 25);
    box.replaceChildren(rows.length ? h("div", { class: "rows" }, rows.map((v) => h("button", { class: "row", type: "button", onclick: () => openPublication(v.upload_id) },
      dot(v.platform), h("div", { class: "grow" }, h("div", { class: "t" }, v.title), h("div", { class: "s" }, v.account_label, " · ", day(v.published_at_utc))),
      mode === "followers" ? h("div", { class: "r" }, h("div", {}, signed(v.metrics.followers_gained)), h("div", { class: "s" }, "subscribers"))
        : [h("div", { class: "r" }, h("div", {}, n(v.views_in_period)), h("div", { class: "s" }, "in range")),
          h("div", { class: "r" }, h("div", {}, n(v.metrics.views)), h("div", { class: "s" }, "to date")),
          h("div", { class: "r" }, h("div", {}, n(v.metrics.avg_view_duration_s, "seconds")), h("div", { class: "s" }, "avg view"))])))
      : empty(mode === "followers" ? "No video-level follower attribution" : "No videos with views yet",
        mode === "followers" ? "Only YouTube reports subscribers gained per video. TikTok and Instagram don't, so their follower changes aren't split by video." : "Published videos appear after the next refresh."));
  };
  paint();
  return panel(mode === "followers" ? "Videos that brought subscribers" : "Videos", {
    actions: mode === "followers" ? null : seg([["period", "Views in range"], ["total", "Views to date"]], sort, (v) => { sort = v; store.set("videoSort", v); paint(); }, "Sort videos") }, box);
}

// Followers drill-down
async function pageFollowers() {
  const d = await api("/api/analytics", fParams());
  const f = d.totals.followers;
  const gained = d.accounts.map((a) => a.stats.followers_gained).filter((x) => x != null);
  const lost = d.accounts.map((a) => a.stats.followers_lost).filter((x) => x != null);
  const kpis = h("div", { class: "kpis" },
    kpi("Followers", n(f.value), "combined, not unique people", FOLLOW_TIP),
    kpi("Net change", signed(f.change), f.growth != null ? `${f.growth > 0 ? "+" : ""}${f.growth}% growth` : d.all_time ? "since the accounts began" : "in this range"),
    kpi("Gained", gained.length ? n(gained.reduce((a, b) => a + b, 0)) : "—", gained.length ? "where the platform reports it" : "not reported"),
    kpi("Lost", lost.length ? n(lost.reduce((a, b) => a + b, 0)) : "—", lost.length ? "where the platform reports it" : "not reported"));
  const levels = trendSeries(d, "followers");
  return [pageHead("Followers", { back: ["#/overview", "Overview"], right: filterBar() }), h("div", { class: "stack" }, kpis,
    panel("Followers over time", { tip: "Each account's count on each day it was read, carried forward between readings." }, lineChart(levels, { label: "Followers over time" })),
    h("div", { class: "grid cols-2" },
      panel("Change by account", { hint: "gains and losses" }, bars(d.accounts.map((a) => ({ label: a.label, prefix: dot(a.platform), v: a.stats.followers_change, color: PLAT[a.platform].color,
        onclick: () => { location.hash = "#/account/" + a.account_id; } })), { signed: true, diverging: true, emptyTitle: "No change measured yet", emptyText: "Needs two readings, or a platform that reports gains and losses." })),
      panel("Gains and losses", {}, h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Account"), h("th", { class: "n" }, "Now"), h("th", { class: "n" }, "Change"), h("th", { class: "n" }, "Gained"), h("th", { class: "n" }, "Lost"))),
        h("tbody", {}, d.accounts.map((a) => h("tr", { class: "click", onclick: () => { location.hash = "#/account/" + a.account_id; } },
          h("td", {}, plat(a.platform), " ", lang(a.language)), h("td", { class: "n" }, n(a.stats.followers)), h("td", { class: "n" }, signed(a.stats.followers_change)),
          h("td", { class: "n" }, n(a.stats.followers_gained)), h("td", { class: "n" }, n(a.stats.followers_lost))))))))),
    videosPanel(d.videos.filter((v) => v.platform === "youtube"), "followers"))];
}

// Account page
async function pageAccount(id) {
  const d = await api("/api/analytics", fParams({ account: id, platform: "", language: "" }));
  const a = d.accounts[0];
  if (!a) return [pageHead("Account", { back: ["#/overview", "Overview"] }), panel(null, {}, empty("Account not found or inactive"))];
  const st = a.stats, eng = ["likes", "comments", "shares", "saves"].map((m) => st[m]).filter((x) => x != null);
  const profile = { youtube: `https://www.youtube.com/@${(a.handle || "").replace(/^@/, "")}`, tiktok: `https://www.tiktok.com/@${(a.handle || "").replace(/^@/, "")}`, instagram: `https://www.instagram.com/${(a.handle || "").replace(/^@/, "")}/` }[a.platform];
  const src = (STATUS?.sources || []).filter((x) => x.account_id === id && x.credential === "ready");
  let metric = store.get("acctMetric", "views");
  const chartBox = h("div", {});
  const paint = () => chartBox.replaceChildren(lineChart([{ label: { views: "Views", followers: "Followers", watch_time_minutes: "Watch time" }[metric], color: PLAT[a.platform].color, points: st.series[metric] || [] }],
    { unit: metric === "watch_time_minutes" ? "minutes" : "", emptyTitle: "Not reported for this account yet" }));
  paint();
  const pick = seg([["views", "Views"], ["followers", "Followers"], ["watch_time_minutes", "Watch time"]], metric, (v) => { metric = v; store.set("acctMetric", v); paint(); }, "Metric");
  return [pageHead(a.label, { back: ["#/overview", "Overview"], sub: [plat(a.platform), " · ", atHandle(a), " · ", (a.language || "").toUpperCase(), src.length ? ` · updated ${ago(src.map((x) => x.last_success_utc).filter(Boolean).sort().pop())}` : ""],
    right: [h("a", { class: "btn ghost small", href: profile, target: "_blank", rel: "noreferrer" }, "Profile ", icon(ICONS.external, 14)), filterBar({ platform: false, account: false, language: false })] }),
  h("div", { class: "stack" },
    h("div", { class: "kpis" }, kpi("Views", n(st.views), delta(st.views, st.views_prev, periodLabel())), kpi("Followers", n(st.followers), st.followers_change != null ? signed(st.followers_change) + " in range" : null),
      kpi("Watch time", n(st.watch_time_minutes, "minutes"), st.watch_time_minutes == null ? "not reported" : null), kpi("Avg view", n(st.avg_view_s, "seconds"), st.avg_view_s == null ? null : st.avg_view_basis === "period" ? "in range" : "lifetime, per video"),
      kpi("Engagement", eng.length ? n(eng.reduce((x, y) => x + y, 0)) : "—", "likes, comments, shares, saves")),
    panel(null, { actions: pick }, chartBox),
    videosPanel(d.videos, "views"))];
}

// Like-for-like comparison: one platform, one checkpoint, grouped by a creative tag. Collapsed by default.
function compareSection(d) {
  const box = h("div", {});
  const plats = d.platforms.map((p) => p.platform);
  const state = { platform: F.platform || plats[0] || "tiktok", language: F.language, checkpoint: "48h", by: "format" };
  const run = async () => {
    box.replaceChildren(h("p", { class: "muted small" }, "Comparing…"));
    try {
      const r = await api("/api/compare", state);
      box.replaceChildren(
        h("p", { class: "small muted", style: "margin:4px 0 10px" }, `${r.all.n} comparable video${r.all.n === 1 ? "" : "s"} read at ${r.checkpoint} (±${r.tolerance_h} h).`,
          r.excluded.outside_window ? ` ${r.excluded.outside_window} read outside that window, left out.` : "", r.excluded.no_reading ? ` ${r.excluded.no_reading} without a reading yet.` : "",
          r.excluded.untagged ? ` ${r.excluded.untagged} not tagged.` : "", r.multi_label ? " A video with several tags counts in each." : ""),
        r.groups.length ? h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Group"), h("th", { class: "n" }, "Videos"), h("th", { class: "n" }, "Median"), h("th", { class: "n" }, "Range"), h("th", {}, ""))),
          h("tbody", {}, r.groups.map((g) => h("tr", {}, h("td", {}, g.key, g.enough ? null : [" ", chip("too few", "warn")]), h("td", { class: "n" }, g.n), h("td", { class: "n" }, n(g.median)),
            h("td", { class: "n" }, `${n(g.low)}–${n(g.high)}`),
            h("td", { class: "n" }, h("button", { class: "btn ghost small", type: "button", onclick: () => findingDrawer(state, g, r) }, "Record finding")))))))
          : empty("Nothing to compare yet", "Needs published videos read at this age, with their concepts tagged (Content → video → Creative tags)."),
        h("p", { class: "small muted" }, r.note));
    } catch (e) { box.replaceChildren(empty("Couldn't compare", e.message)); }
  };
  const controls = h("div", { class: "filters", style: "margin-bottom:6px" },
    h("select", { "aria-label": "Platform", onchange: (e) => { state.platform = e.target.value; run(); } }, ["youtube", "tiktok", "instagram"].map((p) => h("option", { value: p, selected: state.platform === p }, PLAT[p].name))),
    h("select", { "aria-label": "Language", onchange: (e) => { state.language = e.target.value; run(); } }, [["", "Both languages"], ["en", "English"], ["es", "Spanish"]].map(([v, t]) => h("option", { value: v, selected: state.language === v }, t))),
    h("select", { "aria-label": "Age", onchange: (e) => { state.checkpoint = e.target.value; run(); } }, [["24h", "at 24 hours"], ["48h", "at 48 hours"], ["7d", "at 7 days"]].map(([v, t]) => h("option", { value: v, selected: state.checkpoint === v }, t))),
    h("select", { "aria-label": "Group by", onchange: (e) => { state.by = e.target.value; run(); } },
      [["format", "by format"], ["hook", "by hook"], ["codes", "by narrative code"], ["character", "by character"], ["humour", "by humour style"], ["objective", "by objective"], ["mechanism", "by mechanism"]].map(([v, t]) => h("option", { value: v, selected: state.by === v }, t))));
  const det = h("details", { class: "sect" }, h("summary", {}, h("div", { class: "grow" }, h("h2", {}, "Compare similar videos"), h("div", { class: "s" }, "Same platform, same age after posting, grouped by creative tags"))),
    h("div", { class: "body" }, controls, box));
  det.addEventListener("toggle", () => { if (det.open && !box.childNodes.length) run(); });
  return det;
}
async function findingDrawer(state, g, r) {
  const statement = h("textarea", {}, "");
  const link = h("input", { type: "text", placeholder: "e.g. HOOK-003 or MECH-002 (optional)" });
  const type = h("select", {}, ["supports", "conflicts_with", "refines", "moderates"].map((t) => h("option", { value: t }, t.replace("_", " "))));
  const preview = await post("/api/finding", { ...state, group: g.key }).catch((e) => ({ error: e.message }));
  statement.value = preview.statement || "";
  drawer(h("div", { class: "eyebrow" }, "Learning loop"), h("h2", {}, "Record a finding"),
    h("p", { class: "muted small" }, `${r.platform}, ${r.checkpoint}, ${r.by}: ${g.key} (${g.n} videos). Saved as a draft in the knowledge bank (own result, observational). It appears in "ss kb brief" for the next creative brief; it's only marked approved when you approve it.`),
    preview.error ? h("p", { class: "check-row bad" }, preview.error) : null,
    h("div", { class: "form-grid" }, field("What you saw", statement, "wide"), field("Link to an existing entry", link), field("Relationship", type)),
    h("div", { style: "margin-top:14px;display:flex;gap:8px" }, h("button", { class: "btn primary", type: "button", onclick: async () => {
      try { const res = await post("/api/finding", { ...state, group: g.key, statement: statement.value, link_to: link.value.trim(), link_type: type.value, save: true }); toast("Saved draft " + res.id); closeDrawer(); }
      catch (e) { toast(e.message); }
    } }, "Save draft finding")));
}

// ------------------------------------------------------------------ Content
async function pageContent(tab) {
  tab = tab || "concepts";
  const tabs = seg([["concepts", "Concepts"], ["published", "Published"]], tab, (v) => { location.hash = v === "concepts" ? "#/content" : "#/content/published"; }, "Content");
  return tab === "published" ? publishedView(tabs) : conceptsView(tabs);
}
function thumb(path, opts = {}) {
  const box = h("div", { class: "thumb" });
  if (path) {
    const img = h("img", { src: "/api/thumb?path=" + encodeURIComponent(path), alt: "", loading: "lazy" });
    img.addEventListener("error", () => img.replaceWith(placeholder(opts.platform)));
    box.append(img);
  } else box.append(placeholder(opts.platform));
  if (opts.badge) box.append(h("span", { class: "badge" }, opts.badge));
  if (opts.chips?.length) box.append(h("div", { class: "tl" }, opts.chips));
  return box;
}
function placeholder(p) {
  return h("div", { class: "ph", style: p ? `background:linear-gradient(180deg, color-mix(in srgb, ${PLAT[p].color} 22%, var(--surface-2)), var(--surface-2))` : "" },
    h("span", { class: "plat" }, p ? [dot(p), PLAT[p].name] : "No preview"));
}
const dur = (s) => (s == null ? null : s >= 60 ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}` : `0:${String(Math.round(s)).padStart(2, "0")}`);
const STATUS_CHIP = { ready: ["Ready", "ok"], publishing: ["In Publish", "accent"], posted: ["Posted", ""] };
async function conceptsView(tabs) {
  const showPosted = store.get("showPosted", false);
  const groups = await api("/api/library", { posted: showPosted ? "1" : "" });
  const toggle = h("label", { class: "check small", style: "align-items:center" }, h("input", { type: "checkbox", class: "switch", checked: showPosted || null, onchange: (e) => { store.set("showPosted", e.target.checked); route(); } }), "Show posted");
  return [pageHead("Content", { right: [tabs], noRefresh: true }),
    panel(null, { actions: null },
      h("div", { style: "display:flex;align-items:center;gap:10px;margin-bottom:14px" }, h("div", { class: "muted small" }, "Videos on this PC that are ready to publish."), h("span", { style: "flex:1" }), toggle),
      groups.length ? h("div", { class: "gallery" }, groups.map((g) => {
        const v = g.versions[0];
        const [st, tone] = STATUS_CHIP[g.status];
        return h("button", { class: "card", type: "button", onclick: () => conceptDrawer(g) },
          thumb(v.path, { badge: dur(v.duration_s), chips: g.languages.map((l) => chip(l.toUpperCase())) }),
          h("div", { class: "t" }, g.title),
          h("div", { class: "s muted" }, g.audience),
          g.made_at ? h("div", { class: "s muted", title: new Date(g.made_at).toLocaleString() }, `${ago(g.made_at)} · ${when(g.made_at)}`) : null,
          h("div", { class: "s" }, chip(st, tone), g.versions.length > 1 ? `${g.versions.length} versions` : null));
      })) : empty("No videos waiting", showPosted ? "Finished edits in exports/ appear here." : "Finished edits in exports/ appear here. Posted ones are hidden; switch on Show posted to see them."))];
}
function conceptDrawer(g, index = 0) {
  const v = g.versions[index];
  const versionPick = g.versions.length > 1 ? seg(g.versions.map((x, i) => [String(i), [x.variant, (x.language || "").toUpperCase(), x.version].filter(Boolean).join(" ")]), String(index), (i) => conceptDrawer(g, Number(i)), "Version") : null;
  const [st, tone] = STATUS_CHIP[v.status];
  const publish = h("button", { class: "btn primary", type: "button", onclick: () => startPublish(g, v) }, "Publish…");
  drawer(h("div", { class: "eyebrow" }, "Concept"), h("h2", {}, g.title), h("div", { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center" }, chip(st, tone), versionPick),
    h("div", { class: "media-grid" }, h("div", { class: "phone" }, h("video", { src: "/api/media?path=" + encodeURIComponent(v.path), controls: true, playsinline: true, preload: "metadata" })),
      h("div", {},
        h("dl", { class: "kv" }, h("dt", {}, "Length"), h("dd", {}, dur(v.duration_s) || "—"), h("dt", {}, "Size"), h("dd", {}, v.width ? `${v.width}×${v.height}` : "—"),
          h("dt", {}, "Language"), h("dd", {}, v.language ? v.language.toUpperCase() : "not set"),
          h("dt", {}, "For"), h("dd", {}, v.audience.replace(/^For: /, "")),
          h("dt", {}, "Made"), h("dd", {}, v.made_at ? `${when(v.made_at)} (${ago(v.made_at)})` : "—"),
          v.fiction_label ? [h("dt", {}, "Label"), h("dd", {}, v.fiction_label)] : null,
          h("dt", {}, "Posted on"), h("dd", {}, v.posted_on.length ? v.posted_on.map((p) => h("a", { href: p.url || "#", target: "_blank", rel: "noreferrer", style: "margin-right:10px" }, acctLabel(p.account_id))) : "not yet"),
          v.jobs.length ? [h("dt", {}, "In Publish"), h("dd", {}, v.jobs.map((j) => h("a", { href: "#/publish/" + j.job_id, style: "margin-right:10px", onclick: closeDrawer }, acctLabel(j.account_id))))] : null),
        h("div", { style: "display:flex;gap:8px;margin-top:6px" }, publish,
          v.posted_on.length ? null : h("button", { class: "btn ghost", type: "button", onclick: () => deleteVideo(g, v) }, g.versions.length > 1 ? "Delete this version" : "Delete")),
        v.asset_id ? tagsBlock(g.key) : h("p", { class: "muted small" }, "Creative tags can be added once it's in Publish (that registers the video)."),
        h("details", { class: "more", style: "margin-top:10px" }, h("summary", {}, "File details"),
          h("dl", { class: "kv small" }, h("dt", {}, "File"), h("dd", {}, h("span", { class: "code" }, v.path)), h("dt", {}, "Version"), h("dd", {}, v.version || "—"),
            h("dt", {}, "Quality check"), h("dd", {}, v.qc || "not run"), v.asset_id ? [h("dt", {}, "Record"), h("dd", {}, v.asset_id)] : null)))));
}
async function deleteVideo(g, v) {
  const name = [g.title, v.variant, v.version].filter(Boolean).join(" ");
  const drafts = v.jobs.length ? ` and its ${v.jobs.length} unsent draft${v.jobs.length > 1 ? "s" : ""}` : "";
  if (!confirm(`Delete ${name}${drafts}? The file goes to the Recycle Bin, so you can restore it from there.`)) return;
  try {
    await post("/api/media/delete", { path: v.path });
    toast(`Deleted ${name}`);
    closeDrawer();
    route();
  } catch (e) { toast(e.message); }
}
async function startPublish(g, v) {
  let assetId = v.asset_id;
  if (!assetId) {  // an unregistered render: register it (concept + version) the first time it's published
    const lg = await chooseLanguage();
    if (!lg) return;
    try {
      const cid = (await post("/api/concepts", { title: g.title.replace(/([a-z])([A-Z])/g, "$1 $2") })).concept_id;
      assetId = (await post("/api/assets", { concept_id: cid, language: lg, version: v.version || "V01", edit_file: v.path })).asset_id;
    } catch (e) { toast(e.message); return; }
  }
  closeDrawer();
  location.hash = `#/publish/new?asset=${encodeURIComponent(assetId)}&path=${encodeURIComponent(v.path)}`;
}
function chooseLanguage() {
  return new Promise((resolve) => {
    drawer(h("div", { class: "eyebrow" }, "Publish"), h("h2", {}, "Which language is this video?"),
      h("p", { class: "muted small" }, "Captions and on-screen text are made per language, so each version belongs to one."),
      h("div", { style: "display:flex;gap:8px;margin-top:12px" }, h("button", { class: "btn primary", type: "button", onclick: () => resolve("en") }, "English"),
        h("button", { class: "btn primary", type: "button", onclick: () => resolve("es") }, "Spanish"), h("button", { class: "btn ghost", type: "button", onclick: () => { closeDrawer(); resolve(null); } }, "Cancel")));
  });
}
let VOCAB = null;
function tagsBlock(conceptId) {
  const box = h("div", { style: "margin-top:12px" });
  const NAMES = { format: "Format", hook: "Hook", codes: "Narrative", character: "Characters", humour: "Humour", objective: "Objective", mechanism: "Mechanism" };
  const paint = async () => {
    VOCAB = VOCAB || await api("/api/vocab");
    const c = (await api("/api/content", {})).concepts.find((x) => x.concept_id === conceptId);
    let tags = {};
    try { tags = JSON.parse(c?.tags || "{}"); } catch (e) { tags = {}; }
    if (!tags.format?.length && c?.format) tags.format = [c.format];
    const label = (k, id) => (VOCAB[k].find((x) => x.id === id)?.label || id);
    const chips = Object.entries(NAMES).flatMap(([k]) => (tags[k] || []).map((id) => chip(`${NAMES[k]}: ${label(k, id)}`)));
    box.replaceChildren(h("div", { class: "eyebrow", style: "margin-bottom:6px" }, "Creative tags"),
      h("div", { style: "display:flex;gap:5px;flex-wrap:wrap;align-items:center" }, chips.length ? chips : h("span", { class: "muted small" }, "Not tagged yet."),
        h("button", { class: "btn ghost small", type: "button", onclick: () => editTags(conceptId, tags, NAMES, paint) }, chips.length ? "Edit" : "Tag it")));
  };
  paint();
  return box;
}
function editTags(conceptId, tags, NAMES, done) {
  const sel = {};
  const grid = h("div", { class: "form-grid" }, Object.entries(NAMES).map(([k, name]) => {
    const multi = k !== "hook" && k !== "format";
    sel[k] = h("select", multi ? { multiple: true, size: Math.min(6, VOCAB[k].length || 2) } : {},
      multi ? null : h("option", { value: "" }, "—"), VOCAB[k].map((x) => h("option", { value: x.id, selected: (tags[k] || []).includes(x.id) || null, title: x.hint || x.label }, x.label)));
    return field(name + (multi ? " (several)" : ""), sel[k], k === "mechanism" || k === "humour" ? "wide" : "");
  }));
  drawer(h("div", { class: "eyebrow" }, "Creative tags"), h("h2", {}, "What this video does"),
    h("p", { class: "muted small" }, `Codes from the creative codebook (v${VOCAB.codebook_version}) and entries from the knowledge banks, so results link straight back to them. Tags belong to the concept, so every language version shares them.`),
    grid, h("div", { style: "margin-top:14px" }, h("button", { class: "btn primary", type: "button", onclick: async () => {
      const out = Object.fromEntries(Object.entries(sel).map(([k, el]) => [k, [...el.selectedOptions].map((o) => o.value).filter(Boolean)]));
      try { await post("/api/concept-tags", { concept_id: conceptId, tags: out }); toast("Tags saved"); closeDrawer(); } catch (e) { toast(e.message); }
    } }, "Save tags")));
}
async function publishedView(tabs) {
  const PF = Object.assign({ platform: "", account: "", language: "", range: "all", sort: "new" }, store.get("pubFilters", {}));
  const setP = (patch) => { Object.assign(PF, patch); store.set("pubFilters", PF); route(); };
  const d = await api("/api/analytics", { range: "all", platform: PF.platform, account: PF.account, language: PF.language });
  const cutoff = PF.range === "all" ? "" : new Date(Date.now() - Number(PF.range) * 86400000).toISOString();
  const vids = d.videos.filter((v) => !cutoff || (v.published_at_utc || "") >= cutoff);
  const groups = {};
  for (const v of vids) (groups[v.asset_id || v.upload_id] = groups[v.asset_id || v.upload_id] || []).push(v);
  const score = (g) => PF.sort === "views" ? g.reduce((a, v) => a + (v.metrics.views || 0), 0) : PF.sort === "watch" ? g.reduce((a, v) => a + (v.metrics.watch_time_minutes || 0), 0) : Math.max(...g.map((v) => Date.parse(v.published_at_utc || 0) || 0));
  const list = Object.values(groups).sort((a, b) => score(b) - score(a));
  const accts = (META?.accounts || []).filter((a) => a.active && ["youtube", "tiktok", "instagram"].includes(a.platform) && (!PF.platform || a.platform === PF.platform));
  const controls = h("div", { class: "filters", style: "margin-bottom:14px" },
    h("select", { "aria-label": "Platform", onchange: (e) => setP({ platform: e.target.value, account: "" }) }, [["", "All platforms"], ["youtube", "YouTube"], ["tiktok", "TikTok"], ["instagram", "Instagram"]].map(([v, t]) => h("option", { value: v, selected: PF.platform === v }, t))),
    h("select", { "aria-label": "Account", onchange: (e) => setP({ account: e.target.value }) }, h("option", { value: "" }, "All accounts"), accts.map((a) => h("option", { value: a.account_id, selected: PF.account === a.account_id }, a.label))),
    seg([["", "All"], ["en", "EN"], ["es", "ES"]], PF.language, (v) => setP({ language: v }), "Language"),
    seg([["30", "30d"], ["90", "90d"], ["all", "All time"]], PF.range, (v) => setP({ range: v }), "Published"),
    h("span", { style: "flex:1" }),
    h("select", { "aria-label": "Sort", onchange: (e) => setP({ sort: e.target.value }) }, [["new", "Newest"], ["views", "Most views (combined)"], ["watch", "Most watch time"]].map(([v, t]) => h("option", { value: v, selected: PF.sort === v }, t))));
  return [pageHead("Content", { right: [tabs], noRefresh: true }),
    panel(null, {}, controls, list.length ? h("div", { class: "gallery" }, list.map((g) => {
      const first = g[0], local = g.find((v) => v.local_path)?.local_path;
      return h("button", { class: "card", type: "button", onclick: () => (g.length > 1 ? originalDrawer(g) : openPublication(first.upload_id)) },
        thumb(local, { platform: first.platform, chips: g.length > 1 ? [chip(`${g.length} posts`)] : [] }),
        h("div", { class: "t" }, first.title),
        h("div", { class: "pubs" }, g.map((v) => chip([dot(v.platform), ` ${(v.language || "").toUpperCase()} ${n(v.metrics.views)}`]))),
        h("div", { class: "s" }, day(first.published_at_utc, true)));
    })) : empty("Nothing published yet", "Posts appear here after they go out and the next refresh picks them up."))];
}
function originalDrawer(g) {
  const local = g.find((v) => v.local_path)?.local_path;
  drawer(h("div", { class: "eyebrow" }, "One video, several posts"), h("h2", {}, g[0].title),
    h("div", { class: "media-grid" }, local ? h("div", { class: "phone" }, h("video", { src: "/api/media?path=" + encodeURIComponent(local), controls: true, playsinline: true, preload: "metadata" })) : thumb(null, { platform: g[0].platform }),
      h("div", {}, h("p", { class: "muted small", style: "margin-top:0" }, "Each post keeps its own numbers: platforms count differently, so open a post for its full analytics."),
        h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Post"), h("th", { class: "n" }, "Views"), h("th", { class: "n" }, "Avg view"), h("th", { class: "n" }, "Likes"))),
          h("tbody", {}, g.map((v) => h("tr", { class: "click", onclick: () => openPublication(v.upload_id) }, h("td", {}, plat(v.platform), " ", lang(v.language), h("div", { class: "muted small" }, day(v.published_at_utc, true))),
            h("td", { class: "n" }, n(v.metrics.views)), h("td", { class: "n" }, n(v.metrics.avg_view_duration_s, "seconds")), h("td", { class: "n" }, n(v.metrics.likes))))))))));
}
async function openPublication(id) {
  let d;
  try { d = await api("/api/video/" + encodeURIComponent(id)); } catch (e) { toast(e.message); return; }
  const u = d.upload, p = PLAT[u.platform].name, L = d.latest;
  const metricNames = { views: "Views", watch_time_minutes: "Watch time", avg_view_duration_s: "Avg view", likes: "Likes", comments: "Comments", shares: "Shares", saves: "Saves", reach: "Reach", followers_gained: "Subscribers gained" };
  const unit = { watch_time_minutes: "minutes", avg_view_duration_s: "seconds" };
  const present = Object.keys(metricNames).filter((m) => L[m] != null);
  let hm = present.includes("views") ? "views" : present[0];
  const histBox = h("div", {});
  const paintHist = () => histBox.replaceChildren(hm ? lineChart([{ label: metricNames[hm], color: PLAT[u.platform].color, points: d.history[hm] || [] }], { unit: unit[hm], height: 150, emptyTitle: "One reading so far" }) : empty("No readings yet"));
  paintHist();
  const histPick = present.length > 1 ? h("select", { "aria-label": "Metric", onchange: (e) => { hm = e.target.value; paintHist(); } }, present.map((m) => h("option", { value: m }, metricNames[m]))) : null;
  const cps = ["24h", "48h", "7d"].filter((c) => d.checkpoints[c]?.views);
  const median = d.account_median_views;
  drawer(h("div", { class: "eyebrow" }, `${p} · ${d.account.label}`), h("h2", {}, u.title || u.platform_video_id),
    h("div", { class: "media-grid" },
      d.local_path ? h("div", { class: "phone" }, h("video", { src: "/api/media?path=" + encodeURIComponent(d.local_path), controls: true, playsinline: true, preload: "metadata" })) : thumb(null, { platform: u.platform }),
      h("div", {},
        u.url ? h("a", { class: "btn small", href: u.url, target: "_blank", rel: "noreferrer" }, `Open on ${p} `, icon(ICONS.external, 14)) : null,
        h("dl", { class: "kv" }, h("dt", {}, "Published"), h("dd", {}, u.published_at_utc ? new Date(u.published_at_utc).toLocaleString() : "—"),
          h("dt", {}, "Account"), h("dd", {}, h("a", { href: "#/account/" + u.account_id, onclick: closeDrawer }, d.account.label), " ", atHandle(d.account)),
          d.asset ? [h("dt", {}, "Video"), h("dd", {}, d.asset.concept_title, " · ", (d.asset.language || "").toUpperCase(), " ", d.asset.version)] : null,
          d.siblings.length ? [h("dt", {}, "Also posted on"), h("dd", {}, d.siblings.map((x) => h("a", { href: "#", style: "margin-right:10px", onclick: (e) => { e.preventDefault(); openPublication(x.upload_id); } }, x.account_label)))] : null,
          d.experiments.length ? [h("dt", {}, "Experiment"), h("dd", {}, d.experiments.map((x) => chip(`${x.title} (${x.status})`, "accent")))] : null))),
    h("div", { class: "kpis", style: "margin-top:14px" }, (present.length ? present : ["views"]).slice(0, 6).map((m) => kpi(metricNames[m], n(L[m], unit[m]), m === "views" && median != null && L.views != null ? `account median ${n(median)}` : null))),
    h("h3", {}, "At the same age as other videos"),
    cps.length ? h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Age"), h("th", { class: "n" }, "Views"), h("th", {}, "Read at"))),
      h("tbody", {}, cps.map((c) => { const r = d.checkpoints[c].views; return h("tr", {}, h("td", {}, c), h("td", { class: "n" }, n(r.value)),
        h("td", {}, `${r.age_h} h after posting `, r.within ? chip("comparable", "ok") : chip("outside the window", "warn"))); }))))
      : h("p", { class: "muted small" }, "Readings at 24 h, 48 h and 7 days appear as the video ages. Young videos are refreshed every few hours so these land close to time."),
    h("h3", {}, "Over time"), histPick ? h("div", { style: "margin-bottom:6px" }, histPick) : null, histBox,
    d.siblings.length ? [h("h3", {}, "Same video, other posts"), h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Post"), h("th", { class: "n" }, "Views"), h("th", { class: "n" }, "Likes"))),
      h("tbody", {}, [{ ...d.siblings[0], account_label: d.account.label + " (this)", metrics: L, platform: u.platform }, ...d.siblings].map((x) => h("tr", {}, h("td", {}, plat(x.platform), " · ", x.account_label),
        h("td", { class: "n" }, n(x.metrics.views)), h("td", { class: "n" }, n(x.metrics.likes)))))))] : null,
    d.concept_id ? tagsBlock(d.concept_id) : null,
    h("details", { class: "more", style: "margin-top:12px" }, h("summary", {}, "Sources"), h("div", { class: "small muted" }, Object.entries(d.sources).map(([m, s_]) => `${metricNames[m] || m}: ${s_}`).join(" · ") || "—")))
    .classList.add("wide");
}

// ------------------------------------------------------------------ Roblox
async function pageRoblox() {
  const d = await api("/api/game", rangeDates());
  const val = (id) => { for (const st of d.stages) for (const m of st.metrics) if (m.metric === id) { const v = m.values.find((x) => x.platform === "roblox"); if (v) return v; } return null; };
  const hasData = d.series.dau.length || d.stages.some((st) => st.metrics.some((m) => m.values.some((v) => v.platform === "roblox" && v.value != null)));
  const head = pageHead("Roblox", { right: hasData ? filterBar({ platform: false, account: false, language: false }) : null, noRefresh: !hasData });
  if (!hasData) {
    return [head, h("section", { class: "panel empty-page" }, h("h2", {}, "Slugshot isn't live yet"),
      h("p", {}, "Player analytics start when the game is published and connected. Nothing is shown until then: no empty charts and no made-up numbers."),
      h("div", { class: "eyebrow", style: "margin-bottom:6px" }, "What will appear here"),
      h("div", { class: "soon" }, ["Players now", "Daily players", "New players", "Returning players", "Playtime", "Session length", "Retention", "Acquisition", "Revenue", "Payer conversion", "Activation"].map((t) => chip(t))),
      h("a", { class: "btn", href: "#/settings" }, "Connect at launch (Settings)"))];
  }
  const avg = (pts) => (pts.length ? pts.reduce((a, p) => a + p.v, 0) / pts.length : null);
  const newBy = Object.fromEntries(d.series.new_users.map((p) => [p.d, p.v]));
  const returning = d.series.dau.filter((p) => newBy[p.d] != null).map((p) => ({ d: p.d, v: p.v - newBy[p.d] }));
  const d1 = val("d1_retention");
  const kpis = h("div", { class: "kpis" },
    kpi("Players now", n(val("playing")?.value), "concurrent, latest reading"),
    kpi("Daily players", n(avg(d.series.dau)), "average per day"),
    kpi("New players", n(val("new_users")?.value), "in range"),
    kpi("Returning", n(avg(returning)), "average per day", "Daily players minus that day's new players."),
    kpi("Avg session", n(val("avg_session_min")?.value, "minutes")),
    kpi("D1 retention", n(d1?.value, "fraction"), d1?.basis ? d1.basis.replace(/cohort (\d{4}-\d{2}-\d{2})/, (_m, x) => "cohort " + day(x)) : null),
    kpi("Revenue", n(val("revenue_robux")?.value, "Robux"), "in range"));
  const stageList = h("div", { class: "rows" }, d.stages.map((st) => {
    const cells = st.metrics.flatMap((m) => m.values.filter((v) => v.platform === "roblox").map((v) => ({ m, v })));
    return h("div", { class: "row", style: "align-items:flex-start" }, h("div", { style: "width:150px;flex:none" }, h("div", { class: "t" }, st.label), h("div", { class: "s", style: "white-space:normal" }, st.measures)),
      h("div", { class: "grow", style: "display:flex;flex-wrap:wrap;gap:6px 18px" }, cells.length ? cells.map(({ m, v }) => h("div", { class: "small" }, h("span", { class: "muted" }, m.label + " "), h("b", {}, n(v.value, m.unit))))
        : h("span", { class: "muted small" }, "No Roblox source for this stage")));
  }));
  return [head, h("div", { class: "stack" }, kpis,
    panel("Players per day", {}, lineChart([{ label: "Daily players", color: "var(--series-roblox)", points: d.series.dau }, { label: "New", color: "var(--series-youtube)", points: d.series.new_users }, { label: "Returning", color: "var(--series-instagram)", points: returning }], { label: "Players per day" })),
    sect("Retention", "Day 1, 7 and 30 return rates by first-day cohort", {},
      lineChart([{ label: "D1", color: "var(--series-roblox)", points: d.series.d1_retention }], { unit: "fraction", height: 160 }),
      d.cohorts.length ? h("div", { class: "table-wrap", style: "margin-top:10px" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "First day"), h("th", { class: "n" }, "New"), h("th", { class: "n" }, "D1"), h("th", { class: "n" }, "D7"), h("th", { class: "n" }, "D30"))),
        h("tbody", {}, d.cohorts.slice(0, 14).map((c) => h("tr", {}, h("td", {}, day(c.d)), h("td", { class: "n" }, n(c.new_users)), h("td", { class: "n" }, n(c.d1, "fraction")), h("td", { class: "n" }, n(c.d7, "fraction")), h("td", { class: "n" }, n(c.d30, "fraction")))))))
        : null),
    sect("Acquisition", "Where players come from, and tracked share links", {},
      bars(d.acquisition.map((r) => ({ label: r.source, v: r.v, color: "var(--series-roblox)" })), { emptyTitle: "No acquisition data" }),
      d.share_links.length ? h("div", { class: "table-wrap", style: "margin-top:10px" }, h("table", {}, h("tbody", {}, d.share_links.map((r) => h("tr", {}, h("td", {}, r.link), h("td", {}, mdef(r.metric).label), h("td", { class: "n" }, n(r.v))))))) : null),
    sect("Monetisation", "Revenue, payers and payer conversion", {},
      lineChart([{ label: "Revenue (Robux)", color: "var(--series-roblox)", points: d.series.revenue_robux }], { unit: "Robux", height: 160 }),
      h("div", { class: "small", style: "margin-top:8px;display:flex;gap:18px;flex-wrap:wrap" }, h("span", {}, h("span", { class: "muted" }, "Payers per day "), h("b", {}, n(val("paying_users")?.value))),
        h("span", {}, h("span", { class: "muted" }, "Payer conversion "), h("b", {}, n(val("payer_cvr")?.value, "fraction"))))),
    sect("Funnel", "Each stage measured in its own population; stages are never divided into each other", {}, stageList,
      h("p", { class: "muted small" }, "Activation: " + d.activation_note)))];
}

// ------------------------------------------------------------------ Publish
const PUB_STATE = { draft: ["Draft", ""], approved: ["Approved", "accent"], uploading: ["Uploading…", "accent"], processing: ["Processing", "accent"],
  sent_to_inbox: ["In TikTok inbox", "warn"], in_buffer_drafts: ["In Buffer drafts", "warn"], done: ["Posted", "ok"], failed: ["Failed", "bad"], manual_pending: ["Post by hand", "warn"] };
const ROUTE_LABEL = { buffer: "Via Buffer", api: "Direct upload", inbox: "TikTok inbox (you finish in the app)", direct: "TikTok Direct Post", manual: "I post it myself" };
const CRED_TONE = { ready: "ok", "needs upload permission": "warn" };
const TT_PRIVACY = { PUBLIC_TO_EVERYONE: "Everyone", MUTUAL_FOLLOW_FRIENDS: "Friends", FOLLOWER_OF_CREATOR: "Followers", SELF_ONLY: "Only me" };
async function pagePublish(sub) {
  const d = await api("/api/publish");
  const needs = d.jobs.filter((j) => ["draft", "failed", "manual_pending", "sent_to_inbox", "in_buffer_drafts"].includes(j.state));
  const moving = d.jobs.filter((j) => ["approved", "uploading", "processing"].includes(j.state));
  const done = d.jobs.filter((j) => j.state === "done");
  const assetTitle = (j) => d.assets.find((x) => x.asset_id === j.asset_id)?.title || j.asset_id;
  const jobRow = (j) => {
    const a = d.accounts.find((x) => x.account_id === j.account_id) || { label: j.account_id, platform: j.platform };
    const [label, tone] = PUB_STATE[j.state] || [j.state, ""];
    return h("button", { class: "row", type: "button", onclick: () => openJob(j.job_id) },
      dot(j.platform), h("div", { class: "grow" }, h("div", { class: "t" }, assetTitle(j)), h("div", { class: "s" }, a.label, " · ", ago(j.updated_at_utc))), chip(label, tone));
  };
  const ready = d.accounts.filter((a) => a.active && a.credential === "ready");
  const blocked = d.accounts.filter((a) => a.active && a.credential !== "ready");
  if (sub && sub.startsWith("new")) setTimeout(() => composer(Object.fromEntries(new URLSearchParams(sub.split("?")[1] || ""))), 0);
  else if (sub) setTimeout(() => openJob(decodeURIComponent(sub)), 0);
  return [pageHead("Publish", { noRefresh: true, right: h("button", { class: "btn primary", type: "button", onclick: () => composer({}) }, "New post") }),
    h("div", { class: "stack" },
      panel("Needs you", { hint: needs.length ? `${needs.length}` : "" }, needs.length ? h("div", { class: "rows" }, needs.map(jobRow))
        : empty("Nothing waiting", "Pick a video with New post, or from Content.", h("button", { class: "btn small", type: "button", onclick: () => composer({}) }, "New post"))),
      moving.length ? panel("Uploading", {}, h("div", { class: "rows" }, moving.map(jobRow))) : null,
      done.length ? sect("Posted", `${done.length} post${done.length === 1 ? "" : "s"}`, {}, h("div", { class: "rows" }, done.map(jobRow))) : null,
      sect("Accounts", `${ready.length} ready to post${blocked.length ? ` · ${blocked.length} need attention` : ""}`, {},
        h("div", { class: "rows" }, d.accounts.filter((a) => a.active).map((a) => h("div", { class: "row" }, dot(a.platform),
          h("div", { class: "grow" }, h("div", { class: "t" }, a.label, " ", lang(a.language)), h("div", { class: "s" }, atHandle(a), a.credential_note === "via Buffer" ? " · via Buffer" : "")),
          chip(a.credential === "ready" ? "Ready" : a.credential, CRED_TONE[a.credential] || ""),
          a.credential !== "ready" && a.platform !== "instagram" ? h("button", { class: "btn small", type: "button", onclick: async () => {
            try { const r = await post("/api/oauth/start", { provider: a.platform, account_id: a.account_id, purpose: "publish" }); window.open(r.url, "_blank", "noopener"); toast("Finish signing in the new tab, choosing " + atHandle(a)); } catch (e) { toast(e.message); } } }, "Connect") : null))),
        h("p", { class: "muted small" }, d.reveal_lock ? "Reveal lock on: posts can be public, but nothing may name or show the game. You confirm each public video when you approve it." : "Reveal lock off.",
          d.public_posting ? "" : " Public posting is off: uploads stay private.")))];
}
async function composer(pre) {
  const [d, lib] = await Promise.all([api("/api/publish"), api("/api/library", { posted: "1" })]);
  const versions = lib.flatMap((g) => g.versions.map((v) => ({ ...v, title: g.title, key: g.key })));
  let pick = versions.find((v) => pre.path && v.path === pre.path) || null;
  const previewBox = h("div", {});
  const langBox = h("div", {});
  const assetFor = () => pre.asset && pick && pick.path === pre.path ? pre.asset : pick?.asset_id;
  const paintPick = () => {
    gallery.querySelectorAll(".card").forEach((c) => c.setAttribute("aria-pressed", String(c.dataset.path === pick?.path)));
    previewBox.replaceChildren(pick ? h("div", { class: "media-grid" }, h("div", { class: "phone" }, h("video", { src: "/api/media?path=" + encodeURIComponent(pick.path), controls: true, playsinline: true, preload: "metadata" })),
      h("div", {}, h("div", { class: "t", style: "font-weight:700" }, pick.title), h("div", { class: "muted small" }, [(pick.language || "language not set").toUpperCase(), dur(pick.duration_s), pick.version].filter(Boolean).join(" · ")),
        pick.posted_on.length ? h("p", { class: "small" }, "Already posted on ", pick.posted_on.map((p) => acctLabel(p.account_id)).join(", "), ".") : null)) : h("p", { class: "muted small" }, "Choose a video above."));
    langBox.replaceChildren(pick && !assetFor() ? field("Language of this video", h("select", { id: "newlang" }, h("option", { value: "en" }, "English"), h("option", { value: "es" }, "Spanish"))) : null);
  };
  const gallery = h("div", { class: "pick" }, versions.length ? versions.map((v) => h("button", { class: "card", type: "button", "data-path": v.path, "aria-pressed": "false", onclick: () => { pick = v; paintPick(); } },
    thumb(v.path, { badge: dur(v.duration_s), chips: v.language ? [chip(v.language.toUpperCase())] : [] }), h("div", { class: "t" }, v.title))) : empty("No videos on this PC yet", "Finished edits in exports/ appear here."));
  const exps = d.experiments.filter((e) => ["planned", "running"].includes(e.status));
  const expSel = exps.length ? h("select", {}, h("option", { value: "" }, "No experiment"), exps.flatMap((e) => e.variants.map((v) => h("option", { value: `${e.experiment_id}|${v.variant_id}` }, `${e.title} · ${v.label || v.variant_id}`)))) : null;
  const picks = d.accounts.filter((a) => a.active).map((a) => {
    const box = h("input", { type: "checkbox", value: a.account_id });
    const routeSel = h("select", { "aria-label": "Route for " + a.label }, a.routes.map((r) => h("option", { value: r, selected: a.credential !== "ready" ? r === "manual" : null }, ROUTE_LABEL[r])));
    return { a, box, routeSel, el: h("label", { class: "acct-pick check" }, box, dot(a.platform), h("span", { class: "grow" }, a.label, " ", h("span", { class: "muted small" }, atHandle(a))),
      chip(a.credential === "ready" ? "Ready" : a.credential, CRED_TONE[a.credential] || "")) };
  });
  drawer(h("div", { class: "eyebrow" }, "New post"), h("h2", {}, "Publish a video"),
    h("h3", {}, "1 · Video"), gallery, h("div", { style: "margin-top:12px" }, previewBox, langBox),
    h("h3", {}, "2 · Accounts"), h("div", { class: "rows" }, picks.map((p) => p.el)),
    h("details", { class: "more", style: "margin-top:8px" }, h("summary", {}, "Advanced: route per account" + (expSel ? ", experiment" : "")),
      h("div", { class: "rows" }, picks.map((p) => h("div", { class: "row" }, h("span", { class: "grow small" }, p.a.label), p.routeSel))), expSel ? field("Experiment variant", expSel) : null),
    h("p", { class: "muted small" }, "Each account gets its own draft. You review its text and approve it; nothing goes out before that."),
    h("div", { style: "margin-top:8px" }, h("button", { class: "btn primary", type: "button", onclick: async () => {
      const chosen = picks.filter((p) => p.box.checked);
      if (!pick) return toast("Choose a video first");
      if (!chosen.length) return toast("Choose at least one account");
      const [experiment_id, variant_id] = ((expSel && expSel.value) || "|").split("|");
      try {
        let asset_id = assetFor();
        if (!asset_id) {
          const cid = pick.key.startsWith("CON-") ? pick.key : (await post("/api/concepts", { title: pick.title.replace(/([a-z])([A-Z])/g, "$1 $2") })).concept_id;
          asset_id = (await post("/api/assets", { concept_id: cid, language: document.getElementById("newlang")?.value || "en", version: pick.version || "V01", edit_file: pick.path })).asset_id;
        }
        const r = await post("/api/publish/jobs", { asset_id, video: pick.path, experiment_id, variant_id,
          account_ids: chosen.map((p) => p.a.account_id), routes: Object.fromEntries(chosen.map((p) => [p.a.account_id, p.routeSel.value])) });
        toast(`${r.job_ids.length} draft${r.job_ids.length > 1 ? "s" : ""} created`);
        location.hash = "#/publish"; setTimeout(() => openJob(r.job_ids[0]), 300);
      } catch (e) { toast(e.message); }
    } }, "Create drafts"))).classList.add("wide");
  paintPick();
}
function toggle(label, value, opts = {}) {
  const el = h("input", { type: "checkbox", checked: value ? true : null, disabled: opts.disabled ? true : null });
  return { el, row: h("label", { class: "check" + (opts.disabled ? " muted" : "") }, el, h("span", {}, label, opts.note ? h("span", { class: "muted small" }, " · " + opts.note) : null)) };
}
// The approval drawer. Safety rules live on the server (publish.py): typed handle, file and text binding, account
// identity, reveal lock, duplicate guard. This only presents them.
async function openJob(id) {
  let d;
  try { d = await api("/api/publish/job/" + encodeURIComponent(id)); } catch (e) { toast(e.message); return; }
  const j = d.job, a = d.account, f = j.fields, plat_ = PLAT[j.platform].name;
  const editable = ["draft", "manual_pending", "failed"].includes(j.state);
  const [stLabel, stTone] = PUB_STATE[j.state] || [j.state, ""];
  const ctl = {};
  const inp = (k, type, v) => (ctl[k] = type === "textarea" ? h("textarea", { name: k, disabled: !editable || null }, v || "") : h("input", { name: k, type: type || "text", value: v ?? "", disabled: !editable || null }));
  const advanced = [];
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
      parts.push(h("div", { class: "wide" }, h("p", { class: "muted small" }, "Buffer posts it with the account's own privacy, normally public."), dr.row, aigc.row));
      advanced.push(field("Video link (leave empty: the dashboard hosts it privately on Cloudinary)", inp("video_url", "text", f.video_url), "wide"));
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
      parts.unshift(h("div", { class: "wide" }, d.creator ? ["Posting to ", h("strong", {}, c.creator_nickname || "—"), " (@", c.creator_username || "", ")"] : h("span", { class: "chip bad" }, "Can't read this TikTok account: " + (d.creator_error || "connect it for uploads"))));
      parts.push(field("Who can view this video", ctl.privacy), h("div", { class: "wide" }, cm.row, du.row, stt.row, com.row, sub, aigc.row));
    } else {
      parts.push(h("div", { class: "wide" }, h("p", { class: "muted small" }, "The video goes to your TikTok inbox as a draft. Open the TikTok app's notification to finish the caption, privacy and AI label and post it."), aigc.row));
    }
    fieldsEl = h("div", { class: "form-grid" }, parts);
  } else {
    const feed = toggle("Also show in the main feed", f.share_to_feed !== false);
    ctl.share_to_feed = feed.el;
    const dr = j.route === "buffer" ? toggle("Save as a Buffer draft instead of posting", f.buffer_draft, { note: "you post it from Buffer" }) : null;
    if (dr) ctl.buffer_draft = dr.el;
    const urlField = field(j.route === "api" ? "Public https link to the video file" : "Video link (leave empty: the dashboard hosts it privately on Cloudinary)", inp("video_url", "text", f.video_url), "wide");
    if (j.route === "buffer") advanced.push(urlField);
    fieldsEl = h("div", { class: "form-grid" }, field("Caption", inp("caption", "textarea", f.caption), "wide"), j.route === "api" ? urlField : null, h("div", { class: "wide" }, feed.row, dr ? dr.row : null));
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
    pr.bytes ? (pr.bytes / 1e6).toFixed(1) + " MB" : null].filter(Boolean).join(" · ");
  const checks = h("div", { class: "checks" },
    errors.map((e) => h("div", { class: "check-row bad" }, "✕ ", e)), warns.map((w) => h("div", { class: "check-row warn" }, "! ", w)),
    !errors.length ? h("div", { class: "check-row ok" }, j.route === "manual" ? "✓ Checks pass. You post this one yourself." : "✓ Ready for approval") : null);
  let action = null;
  if (j.route === "manual" || ["sent_to_inbox", "in_buffer_drafts", "processing"].includes(j.state)) {
    const urlIn = h("input", { type: "text", placeholder: `Paste the ${plat_} link once it's posted` });
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
      h("p", {}, "Uploads this video to ", h("strong", {}, `${a.label} (${atHandle(a)})`), " as ", h("strong", {}, visibility), "."),
      j.platform === "tiktok" ? [h("p", { class: "muted small" }, "After you approve, TikTok can take a few minutes to process the video."), h("label", { class: "check" }, consent, h("span", {}, d.tiktok_declaration))] : null,
      revealOk ? h("label", { class: "check" }, revealOk, h("span", {}, "Reveal lock: I've watched this video and checked its text. Nothing names or shows the game (title, logo, place link or anything that identifies it).")) : null,
      h("div", { style: "display:flex;gap:8px;margin-top:10px;flex-wrap:wrap" }, typed, go),
      errors.length ? h("p", { class: "muted small" }, "Fix the checks above first. Save your edits to re-check.") : null);
  } else if (j.state === "failed" && j.approval) {
    action = h("div", { class: "approve" }, h("p", { class: "small" }, "The approved upload failed (see the log). Retry uses the same approval if nothing changed."),
      h("button", { class: "btn", type: "button", onclick: async () => { try { await post("/api/publish/retry", { job_id: j.job_id }); toast("Retrying…"); setTimeout(() => openJob(j.job_id), 1200); } catch (e) { toast(e.message); } } }, "Retry upload"));
  }
  const dr = drawer(h("div", { class: "eyebrow" }, `${plat_} · ${a.label}`), h("h2", {}, d.asset ? d.asset.title : j.asset_id),
    h("div", { style: "display:flex;gap:6px;flex-wrap:wrap" }, chip(stLabel, stTone), d.check.reveal_lock ? chip("Reveal lock", "warn") : null,
      chip({ private: "Private", in_app: "Visibility set in the app", visible: "Others can see it" }[d.check.visibility] || d.check.visibility, d.check.visibility === "visible" ? "accent" : ""),
      j.experiment_id ? chip([j.experiment_id, j.variant_id].filter(Boolean).join(" · "), "accent") : null),
    h("div", { class: "media-grid" }, preview, h("div", {},
      h("h3", { style: "margin-top:0" }, `${plat_} text and settings`), fieldsEl,
      editable ? h("div", { style: "margin-top:12px;display:flex;gap:8px" }, h("button", { class: "btn small", type: "button", onclick: async () => { try { await save(); toast("Saved"); openJob(j.job_id); } catch (e) { toast(e.message); } } }, "Save and re-check"),
        h("button", { class: "btn ghost small", type: "button", onclick: async () => { if (!confirm("Delete this draft?")) return; await post("/api/publish/delete", { job_id: j.job_id }); closeDrawer(); route(); } }, "Delete draft")) : null)),
    h("h3", {}, "Checks"), checks,
    action ? [h("h3", {}, j.route === "manual" ? "Post it yourself" : "Approve"), action] : null,
    j.result?.url ? h("p", { class: "small" }, h("a", { href: j.result.url, target: "_blank", rel: "noreferrer" }, "Open the post ", icon(ICONS.external, 13))) : null,
    h("details", { class: "more", style: "margin-top:12px" }, h("summary", {}, "Advanced"),
      h("div", { class: "form-grid", style: "margin:6px 0" }, field("Route", routeSel), advanced),
      h("dl", { class: "kv small" }, h("dt", {}, "Version"), h("dd", {}, j.asset_id), h("dt", {}, "File"), h("dd", {}, h("span", { class: "code" }, j.video_path)),
        h("dt", {}, "Video"), h("dd", {}, facts || "—"), j.approval ? [h("dt", {}, "Approved"), h("dd", {}, new Date(j.approval.at).toLocaleString())] : null),
      j.log?.length ? h("ul", { class: "small muted" }, j.log.slice().reverse().map((x) => h("li", {}, new Date(x.at).toLocaleString(), " · ", x.msg))) : null));
  dr.classList.add("wide");
  if (["uploading", "processing", "approved"].includes(j.state)) setTimeout(() => { if (document.querySelector(".drawer")) openJob(j.job_id); }, 3000);
}

// ------------------------------------------------------------------ Settings
async function pageSettings() {
  const st = await refreshStatus();
  const accounts = (await api("/api/meta")).accounts;
  const choice = store.get("theme-choice", "system");
  const setTheme = (v) => {
    store.set("theme-choice", v);
    document.documentElement.setAttribute("data-theme", v === "light" || v === "dark" ? v : "blue");
    route();
  };
  let starsOn = !document.documentElement.classList.contains("no-stars");
  const starSwitch = h("input", { type: "checkbox", class: "switch", checked: starsOn || null, "aria-label": "Shooting stars", onchange: (e) => {
    starsOn = e.target.checked;
    try { localStorage.setItem("ss-stars", String(starsOn)); } catch (err) { /* ignore */ }
    document.documentElement.classList.toggle("no-stars", !starsOn);
  } });
  const appearance = sect("Appearance", { system: "System · blue night", light: "Light", dark: "Dark" }[choice] + (starsOn ? " · stars on" : ""), { open: true },
    h("div", { style: "display:flex;gap:18px;align-items:center;flex-wrap:wrap" }, seg([["system", "System"], ["light", "Light"], ["dark", "Dark"]], choice, setTheme, "Theme"),
      h("label", { class: "check", style: "align-items:center" }, starSwitch, "Shooting stars")),
    h("p", { class: "muted small", style: "margin:8px 0 0" }, "System uses Slugshot's blue night theme. Stars stay still when your device asks for reduced motion."));

  // Connected accounts: one row per account, its sources and actions inside.
  const byAcct = {};
  for (const x of st.sources) (byAcct[x.account_id] = byAcct[x.account_id] || []).push(x);
  const acctRows = h("div", { class: "rows" }, Object.entries(byAcct).map(([id, srcs]) => {
    const a = accounts.find((x) => x.account_id === id) || { label: id, platform: srcs[0].platform };
    const ready = srcs.filter((x) => x.credential === "ready");
    const bad = ready.filter((x) => ["failed", "needs_auth"].includes(x.last_status));
    const tone = bad.length ? "bad" : ready.length ? "ok" : "";
    const label = bad.length ? "needs attention" : ready.length ? `connected · ${ago(ready.map((x) => x.last_success_utc).filter(Boolean).sort().pop())}` : "not connected";
    return h("details", { class: "more", style: "border-bottom:1px solid var(--line);padding:4px 0" },
      h("summary", { style: "display:flex;align-items:center;gap:10px" }, dot(a.platform), h("span", { style: "font-weight:650;color:var(--text)" }, a.label), lang(a.language), h("span", { style: "flex:1" }), chip(label, tone)),
      h("div", { style: "padding:4px 0 10px 18px" }, srcs.map((x) => h("div", { class: "row" }, h("div", { class: "grow" }, h("div", { class: "t", style: "font-weight:600" }, x.label),
        h("div", { class: "s" }, x.credential === "ready" ? `${x.freshness}${x.last_success_utc ? " · " + ago(x.last_success_utc) : ""}` : x.credential, x.last_status && x.last_status !== "ok" ? ` · ${x.last_status}: ${x.last_message}` : "")),
        connectAction(x)))));
  }));
  const auto = h("input", { type: "checkbox", class: "switch", checked: st.auto_refresh || null, onchange: async (e) => { await post("/api/prefs", { auto_refresh: e.target.checked }); toast(e.target.checked ? "Automatic refresh on" : "Automatic refresh off"); } });
  const connected = sect("Connected accounts", `${Object.values(byAcct).filter((s_) => s_.some((x) => x.credential === "ready")).length} of ${Object.keys(byAcct).length} connected`, {},
    acctRows, h("div", { style: "display:flex;gap:12px;align-items:center;margin-top:12px;flex-wrap:wrap" },
      h("button", { class: "btn small", type: "button", onclick: async () => { await post("/api/sync"); toast("Refreshing…"); pollUntilDone(); } }, "Refresh now"),
      h("label", { class: "check small", style: "align-items:center" }, auto, "Refresh automatically (daily; every 4 h while a video is under 8 days old)")));

  const pub = await api("/api/publish");
  const hostingLimits = (await api("/api/hosting")).limits;
  const publishing = sect("Publishing", `${pub.public_posting ? "Public posts allowed" : "Private only"} · reveal lock ${pub.reveal_lock ? "on" : "off"}`, {},
    h("dl", { class: "kv" }, h("dt", {}, "Public posts"), h("dd", {}, pub.public_posting ? "Allowed. Every upload still needs your approval." : "Off: uploads stay private."),
      h("dt", {}, "Reveal lock"), h("dd", {}, pub.reveal_lock ? "On: nothing may name or show the game. You confirm each public video." : "Off."),
      h("dt", {}, "TikTok and Instagram"), h("dd", {}, "Via Buffer. The video is hosted privately on Cloudinary only after you approve, and deleted once posted."),
      h("dt", {}, "Hosting limits"), h("dd", {}, `${hostingLimits.max_file_mb} MB per video · ${hostingLimits.max_hosted_files} at once · uploads stop at ${hostingLimits.max_credit_pct}% of the free plan`)),
    h("p", { class: "muted small", style: "margin:0" }, "Ask Claude to change these. Only you can turn the reveal lock off."));

  const credsList = [["YOUTUBE_OAUTH_CLIENT_ID", "Google OAuth client ID"], ["YOUTUBE_OAUTH_CLIENT_SECRET", "Google OAuth client secret"],
    ["TIKTOK_CLIENT_KEY", "TikTok client key"], ["TIKTOK_CLIENT_SECRET", "TikTok client secret"], ["ROBLOX_ANALYTICS_API_KEY", "Roblox Open Cloud key"],
    ["BUFFER_API_KEY", "Buffer API key"], ["CLOUDINARY_CLOUD_NAME", "Cloudinary cloud name"], ["CLOUDINARY_API_KEY", "Cloudinary API key"], ["CLOUDINARY_API_SECRET", "Cloudinary API secret"]];
  const credRows = h("div", { class: "rows" }, credsList.map(([k, t]) => {
    const inp = h("input", { type: "password", autocomplete: "off", placeholder: st.credentials[k] ? "saved · paste to replace" : "paste value", "aria-label": t, style: "flex:1;min-width:0" });
    return h("div", { class: "row" }, h("div", { style: "width:200px;flex:none" }, h("div", { class: "t", style: "font-weight:600" }, t)), inp,
      st.credentials[k] ? chip("saved", "ok") : chip("not set"),
      h("button", { class: "btn small", type: "button", onclick: async () => { if (!inp.value.trim()) return; await post("/api/credentials", { name: k, value: inp.value }); inp.value = ""; toast("Saved to the encrypted vault"); route(); } }, "Save"));
  }));
  const creds = sect("Credentials", `${credsList.filter(([k]) => st.credentials[k]).length} of ${credsList.length} saved · encrypted on this PC`, {}, credRows,
    h("p", { class: "muted small", style: "margin:8px 0 0" }, "Never shown again and never exported. Values in .env also work."));

  const accEdit = h("div", { class: "rows" }, accounts.map((a) => {
    const label = h("input", { type: "text", value: a.label, "aria-label": "Label" });
    const handle = h("input", { type: "text", value: a.handle, placeholder: "handle", "aria-label": "Handle" });
    const ext = h("input", { type: "text", value: a.external_id, placeholder: a.platform === "roblox" ? "universe ID" : "filled on connect", "aria-label": "External ID" });
    const active = h("input", { type: "checkbox", checked: !!a.active, "aria-label": "Active" });
    return h("div", { class: "row", style: "flex-wrap:wrap" }, h("span", { style: "width:110px" }, plat(a.platform), " ", lang(a.language)), label, handle, ext,
      h("label", { class: "small muted", style: "display:flex;gap:6px;align-items:center" }, active, "active"),
      h("button", { class: "btn small", type: "button", onclick: async () => { try { await post("/api/accounts", { ...a, label: label.value, handle: handle.value, external_id: ext.value.trim(), active: active.checked }); toast("Saved"); } catch (e) { toast(e.message); } } }, "Save"));
  }));
  const advanced = sect("Advanced and diagnostics", "Imports, exports, account details, hosted files", {},
    h("div", { class: "grid cols-2" }, importPanel(st), exportPanel()),
    h("h3", { class: "eyebrow", style: "margin:16px 0 6px" }, "Accounts"), accEdit,
    h("h3", { class: "eyebrow", style: "margin:16px 0 6px" }, "Hosted videos"), hostedList(),
    h("p", { class: "muted small", style: "margin:14px 0 0" }, "OAuth redirect URI: ", h("span", { class: "code" }, st.redirect_uri)));
  return [pageHead("Settings", { noRefresh: true }), h("div", { class: "stack" }, appearance, connected, usageSection(), publishing, creds, advanced)];
}
function usageSection() {
  const body = h("div", {}, h("p", { class: "muted small" }, "Loading…"));
  const HOW = { live: ["Live", "live"], "local estimate": ["Estimate", ""], documented: ["Limit only", ""] };
  const paint = (d) => body.replaceChildren(...d.services.map((svc) => h("div", { class: "svc" },
    h("div", { class: "svc-head" }, h("span", { class: "name" }, svc.service), svc.status === "error" ? chip("check failed", "bad") : null, h("span", { style: "flex:1" }),
      svc.link ? h("a", { class: "small", href: svc.link, target: "_blank", rel: "noreferrer" }, "Console ", icon(ICONS.external, 12)) : null),
    svc.rows.map((r) => {
      const [hl, hc] = HOW[r.how] || [r.how, ""];
      const tone = r.pct == null ? "" : r.pct >= 80 ? "bad" : r.pct >= 50 ? "warn" : "";
      const val = r.used != null && r.limit != null ? `${n(r.used)} / ${n(r.limit)} ${r.unit}` : r.limit != null ? `limit ${n(r.limit)} ${r.unit}` : "";
      return h("div", { class: "meter" }, h("div", {}, h("div", { style: "font-weight:600" }, r.label), h("div", { class: "muted", style: "font-size:11.5px" }, [r.period, r.detail].filter(Boolean).join(" · "))),
        r.pct != null ? h("div", { class: "track" }, h("div", { class: "fill " + tone, style: `width:${Math.min(100, Math.max(1, r.pct))}%` })) : h("div", {}),
        h("div", { class: "val" }, val, " ", h("span", { class: "how " + hc }, hl)));
    }),
    svc.note ? h("details", { class: "more" }, h("summary", {}, "About this"), h("p", { class: "muted small", style: "margin:0" }, svc.note)) : null)));
  api("/api/services").then(paint).catch((e) => body.replaceChildren(empty("Couldn't read usage", e.message)));
  return sect("Service usage and quotas", "Free plans: what's used and what's left", {}, body,
    h("div", { style: "display:flex;gap:8px;margin-top:8px" }, h("button", { class: "btn small", type: "button", onclick: async () => {
      body.replaceChildren(h("p", { class: "muted small" }, "Checking…")); await api("/api/hosting", { refresh: "1" }).catch(() => {}); paint(await api("/api/services")); } }, "Check Cloudinary now")),
    h("p", { class: "muted small", style: "margin:8px 0 0" }, "Live = reported by the provider. Estimate = counted from our own logs. Limit only = the published allowance; that provider doesn't report current usage."));
}
function hostedList() {
  const box = h("div", {});
  const paint = (d) => box.replaceChildren(d.hosted.filter((r) => r.state !== "deleted").length ? h("div", { class: "rows" }, d.hosted.filter((r) => r.state !== "deleted").map((r) => h("div", { class: "row" },
    h("span", { class: "code" }, r.public_id.split("/").pop().slice(0, 12)), chip(r.state, r.state === "failed" ? "bad" : "accent"), h("span", { class: "muted small" }, `${(r.bytes / 1e6).toFixed(1)} MB · ${ago(r.updated_at_utc)}`))))
    : h("p", { class: "muted small", style: "margin:0" }, "Nothing hosted. Videos are only hosted while a Buffer post needs them."),
    h("button", { class: "btn ghost small", type: "button", style: "margin-top:6px", onclick: async () => { const r = await post("/api/hosting/cleanup", {}); toast(`${r.deleted.length} abandoned file(s) deleted`); paint(await api("/api/hosting")); } }, "Clean up abandoned files"));
  api("/api/hosting").then(paint).catch(() => {});
  return box;
}
function connectAction(x) {
  if (x.connector === "youtube_analytics" || x.connector === "tiktok") {
    const prov = x.connector === "tiktok" ? "tiktok" : "youtube";
    const blocked = x.credential.startsWith("needs");
    return h("div", { style: "display:flex;gap:6px" },
      h("button", { class: "btn small", type: "button", disabled: blocked, title: blocked ? "Save the app credentials first" : null, onclick: async () => {
        try { const r = await post("/api/oauth/start", { provider: prov, account_id: x.account_id }); window.open(r.url, "_blank", "noopener"); toast("Finish signing in in the browser window"); } catch (e) { toast(e.message); }
      } }, x.credential === "ready" ? "Reconnect" : "Connect"),
      x.credential === "ready" ? disconnectBtn(x) : null);
  }
  if (x.connector === "instagram") {
    return h("button", { class: "btn small", type: "button", onclick: () => {
      const inp = h("input", { type: "password", autocomplete: "off", style: "width:100%" });
      drawer(h("div", { class: "eyebrow" }, "Instagram"), h("h2", {}, "Paste access token"), h("p", { class: "muted small" }, "Meta app dashboard > Instagram > API setup with Instagram login > Generate token. Stored encrypted; refreshed automatically."),
        field("Long-lived token", inp), h("div", { style: "margin-top:14px" }, h("button", { class: "btn primary", type: "button", onclick: async () => {
          await post("/api/credentials", { name: "INSTAGRAM_TOKEN", account_id: x.account_id, value: inp.value }); closeDrawer(); toast("Saved"); route();
        } }, "Save")));
    } }, x.credential === "ready" ? "Replace token" : "Add token");
  }
  return null;
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
  const drop = h("div", { class: "drop", tabindex: "0", role: "button", onclick: () => fileIn.click(), onkeydown: (e) => e.key === "Enter" && fileIn.click() }, "Drop a CSV here or click to choose");
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
  return panel("Import metrics", { tip: "For numbers no API gives: TikTok Studio, Instagram app, YouTube Studio exports, Roblox share links. Checked first; nothing is stored until you press Import." },
    drop, fileIn, out, st.imports.length ? h("details", { class: "more", style: "margin-top:8px" }, h("summary", {}, "Recent imports"), st.imports.map((i) => h("div", { class: "small muted" }, `${day(i.imported_at_utc)} · ${i.file_name} · ${i.rows_ok} rows`))) : null);
}
function exportPanel() {
  let detail = "overview";
  const safe = h("input", { type: "checkbox", checked: true });
  const out = h("div", {});
  const segEl = h("span", {});
  const paint = () => segEl.replaceChildren(seg([["overview", "Overview"], ["detailed", "Detailed"]], detail, (v) => { detail = v; paint(); }, "Detail"));
  paint();
  return panel("Export for AI tools", { tip: "A snapshot for ChatGPT, Claude and Gemini: Markdown summary plus CSV/JSON files. Safe-to-share applies the sharing rules, removes local paths and checks for credentials." },
    h("div", { style: "display:flex;gap:10px;align-items:center;flex-wrap:wrap" }, segEl, h("label", { class: "check small", style: "align-items:center" }, safe, "Safe to share"),
      h("button", { class: "btn primary small", type: "button", onclick: async () => {
        try {
          const r = await post("/api/export", { detail, share: safe.checked, filters: fParams() });
          out.replaceChildren(h("p", { class: "small" }, `${r.files.length} files in `, h("span", { class: "code" }, r.folder)),
            r.excluded.length ? h("p", { class: "small muted" }, "Left out: " + r.excluded.join("; ")) : null,
            h("button", { class: "btn small", type: "button", onclick: () => post("/api/open-folder", { folder: r.folder }) }, "Open folder"));
        } catch (e) { toast(e.message); }
      } }, "Export")), out);
}

// ------------------------------------------------------------------ drawers
function drawer(...content) {
  closeDrawer();
  const scrim = h("div", { class: "scrim", onclick: closeDrawer });
  const d = h("aside", { class: "drawer", role: "dialog", "aria-modal": "true" },
    h("button", { class: "btn ghost icon-btn close", type: "button", "aria-label": "Close", onclick: closeDrawer }, icon(ICONS.close)), content);
  document.body.append(scrim, d);
  d.querySelector("input,select,textarea,button:not(.close)")?.focus({ preventScroll: true });
  return d;
}
function closeDrawer() { document.querySelectorAll(".scrim,.drawer").forEach((x) => { x.querySelectorAll?.("video").forEach((v) => v.pause()); x.remove(); }); }
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

// ------------------------------------------------------------------ router
let routeSeq = 0;
async function route() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [page0, ...rest] = raw.split("/");
  const page = { game: "roblox", research: "overview", experiments: "overview" }[page0] || page0 || "overview";
  const sub = rest.join("/");
  const pages = {
    overview: () => (sub === "views" ? pageViews() : sub === "followers" ? pageFollowers() : pageOverview()),
    account: () => pageAccount(decodeURIComponent(sub)),
    content: () => pageContent(sub || "concepts"),
    roblox: pageRoblox, publish: () => pagePublish(sub), settings: pageSettings,
  };
  const fn = pages[page] || pages.overview;
  const seq = ++routeSeq;
  renderNav(page === "account" ? "overview" : pages[page] ? page : "overview");
  document.title = `${(page[0] || "o").toUpperCase() + page.slice(1)} · Slugshot`;
  try {
    const nodes = await fn();
    if (seq !== routeSeq) return;
    charts = [];
    $main.replaceChildren(...[].concat(nodes).flat(3).filter(Boolean));
    requestAnimationFrame(() => charts.forEach((d) => d()));
  } catch (e) {
    if (seq !== routeSeq) return;
    $main.replaceChildren(...pageHead(page[0].toUpperCase() + page.slice(1), { noRefresh: true }), panel("Couldn't load this page", {}, h("p", { class: "muted" }, e.message)));
  }
}
window.addEventListener("hashchange", () => { closeDrawer(); route(); });

(async function start() {
  nightSky();
  META = await api("/api/meta");
  await refreshStatus();
  route();
  // Refresh stale sources when the app opens (if automatic refresh is on), then keep the status line current.
  if (STATUS && STATUS.auto_refresh && !STATUS.sync.running && !FIXTURE &&
      STATUS.sources.some((x) => x.credential === "ready" && ["due", "stale", "never synced"].includes(x.freshness))) {
    post("/api/sync").then(pollUntilDone).catch(() => {});
  }
  setInterval(refreshStatus, 30000);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
})();
