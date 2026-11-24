"""Deterministic research analysis over collected data and bundles (`ss analyze`). Claude runs these; results feed
the evidence ledger (`ss evidence`) and ChatGPT's interpretation.

  intake [BUNDLE]          what a bundle (zip or folder; default: newest in exports/share/bundles) contains: datasets,
                           providers, scope, dates, expiry, sharing, missingness per column, rounded / estimated /
                           unknown-definition values, discovery contexts vs observations, sample roles, and what each
                           source cannot answer -> intake.json + intake.md next to the bundle
  describe FILE METRIC     n, missing, median, quartiles, range, top-item share, with explicit denominators
                           [--by COL] [--where COL=VAL ...]
  repeat FILE              same-item repeated observations: changes between comparable observations only
  sensitivity FILE METRIC --by COL   medians per group under alternative specifications (all, leave-one-creator-out,
                           drop top 1%, ordinary-only, older-than-48h); flags groups whose order or median moves
  trend TERM               trend dimensions kept separate (heat, velocity, breadth, persistence, novelty, context fit,
                           Slugshot fit) from every local store + a rule-based lifecycle proposal with reasons
  changepoints             change points in Wikipedia daily page-view series (ruptures, PELT) [--entity ID]
  blind-packet FILE        outcome-blind coding packet: an allowlist of descriptive fields, no metrics or ranks
  join-annotations FILE ANNOTATIONS   validate coded annotations (exact-quote evidence, codebook version, states)
                           and join outcomes; association table by code x sample role with denominators
  context wikidata TERM | context gdelt TERM [--days 30]   entity identity/aliases; news-volume context for spikes

Policy guards built in: YouTube API rows are never aggregated across different channels (Developer Policies
III.E.2.a); `describe`, `sensitivity` and `join-annotations` refuse or fall back to per-item listings for them.
Blanks are unknown, never 0. Nothing here produces a composite score.
"""
import argparse
import csv
import json
import re
import statistics
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

import research_common as rc

OUT = rc.DATA / "analysis"
OUTCOME_COLS = {"views", "likes", "comments", "shares", "saves", "posts", "followers", "plays", "rank", "rank_change",
                "view_count", "viewer_count", "playing", "visits", "favorited_count", "up_votes", "down_votes",
                "value_display", "value_numeric", "value_rounded", "views_per_hour_since_prev", "view_increase_since_prev",
                "hours_since_prev", "approx_traffic", "approx_traffic_lower_bound", "position", "breakout_multiple",
                "engagement_rate", "subscribers", "snapshots", "stored_rows", "observations", "like_count", "reply_count"}
BLIND_ALLOW = ["key", "platform", "url", "title", "title_or_name", "description", "tags", "duration_s", "language_hint",
               "published_at", "published_at_utc", "content_language", "notes_for_coder"]
CANNOT_ANSWER = {
    "youtube": "retention, watch time, shares, reach, audience geography/demographics; cross-channel rankings or scores "
               "(not permitted); region_param = viewable-in, relevance_language_param = ranking hint",
    "wikimedia": "fandom size, unique people, country, intent to play; an edition is a language, not a country",
    "google_trends": "absolute search counts; gaming demand (Trending Now covers all searches); comparisons across "
                     "separately normalised Explore downloads",
    "twitch": "spoken language (language = broadcaster setting), audience location; data is local-only and expires in 24 h",
    "roblox": "why player counts moved; legacy endpoint, 'playing' may not cover all places",
    "observations": "metric definitions marked unknown; rounded values are approximate; featured examples are not a "
                    "denominator for ordinary content; tool region filters are not audience geography",
}


def load_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def provider_of(name, cols=()):
    for p in ("youtube", "wikimedia", "google_trend", "twitch", "roblox", "public_observations"):
        if name.startswith(p):
            return {"google_trend": "google_trends", "public_observations": "observations"}.get(p, p)
    # Derived files (samples, joins) keep YouTube's columns but not its filename; the policy follows the data.
    if {"video_id", "channel_id", "views"} <= set(cols):
        return "youtube"
    return "other"


def fnum(x):
    if x in (None, ""):
        return None
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        n, _ = rc.parse_count(x)
        return float(n) if n is not None else None


def quantile(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    i = (len(vals) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (i - lo)


def stats(vals):
    if not vals:
        return {"n": 0}
    s = sorted(vals)
    total = sum(s)
    return {"n": len(s), "median": statistics.median(s), "q25": quantile(s, .25), "q75": quantile(s, .75),
            "min": s[0], "max": s[-1], "top_item_share": round(s[-1] / total, 3) if total else None}


def open_bundle(arg):
    """Returns (folder, label). Zips are extracted to a temp folder."""
    if not arg:
        zips = sorted((rc.ROOT / "exports" / "share" / "bundles").glob("*.zip"))
        if not zips:
            sys.exit("No bundle found; run `ss research bundle` or pass a path.")
        arg = str(zips[-1])
    p = Path(arg)
    if p.suffix == ".zip":
        d = Path(tempfile.mkdtemp(prefix="bundle_"))
        zipfile.ZipFile(p).extractall(d)
        return d, p
    return p, p


# ---------- intake ----------


def cmd_intake(a):
    folder, label = open_bundle(a.bundle)
    manifest = {r["file"]: r for r in rc.read_rows(folder / "MANIFEST.csv")} if (folder / "MANIFEST.csv").exists() else {}
    report = {"bundle": str(label), "checked_at": rc.iso(rc.now()), "datasets": [], "issues": []}
    now = rc.now()
    for f in sorted(folder.glob("*.csv")):
        if f.name == "MANIFEST.csv":
            continue
        rows = load_csv(f)
        cols = list(rows[0].keys()) if rows else []
        prov = provider_of(f.name, cols)
        m = manifest.get(f.name, {})
        d = {"file": f.name, "provider": prov, "rows": len(rows), "columns": len(cols),
             "has_dictionary": (folder / (f.stem + "_README.md")).exists(), "has_json": (f.with_suffix(".json")).exists(),
             "in_manifest": bool(m), "manifest_rows_match": (str(len(rows)) == m.get("rows")) if m else None,
             "provenance": m.get("provenance", ""), "expires_at_utc": m.get("expires_at_utc", ""),
             "share_status": m.get("share_status", ""), "cannot_answer": CANNOT_ANSWER.get(prov, "")}
        if m.get("expires_at_utc") and rc.parse_time(m["expires_at_utc"]) <= now:
            report["issues"].append(f"{f.name}: past its expiry {m['expires_at_utc']} - delete or refresh before use")
        if d["has_json"]:  # the JSON twin must carry the same rows and columns as the CSV
            twin = json.loads(f.with_suffix(".json").read_text(encoding="utf-8"))
            same = len(twin.get("rows", [])) == len(rows) and [c["name"] for c in twin.get("columns", [])] == cols
            d["json_twin_matches"] = same
            if not same:
                report["issues"].append(f"{f.name}: CSV and JSON copy disagree (rows or columns)")
        if not d["has_dictionary"]:
            report["issues"].append(f"{f.name}: no data dictionary (_README.md) next to it")
        if m and not d["manifest_rows_match"]:
            report["issues"].append(f"{f.name}: row count {len(rows)} differs from MANIFEST ({m.get('rows')})")
        d["missing_by_column"] = {c: sum(1 for r in rows if r.get(c, "") == "") for c in cols
                                  if any(r.get(c, "") == "" for r in rows)}
        for tcol in ("observed_at_utc", "observation_moment", "period_start", "trend_started_at_utc"):
            ts = sorted(r[tcol] for r in rows if r.get(tcol))
            if ts:
                d["time_range"] = {"column": tcol, "first": ts[0], "last": ts[-1], "distinct": len(set(ts))}
                break
        if "value_rounded" in cols:
            d["rounded_values"] = sum(1 for r in rows if r.get("value_rounded") == "true")
        if "metric_definition" in cols:
            d["metric_definition"] = dict(Counter(r.get("metric_definition", "") for r in rows))
        if "provenance" in cols:
            d["provenance_rows"] = dict(Counter(r.get("provenance", "") for r in rows))
        if "sample_role" in cols:
            d["sample_role"] = dict(Counter(r.get("sample_role") or "unknown" for r in rows))
            if d["sample_role"].get("unknown", 0) == len(rows):
                report["issues"].append(f"{f.name}: no sample_role recorded; featured vs ordinary is unknown")
        if "duplicate_context" in cols:
            d["duplicate_context_rows"] = sum(1 for r in rows if r.get("duplicate_context") == "true")
        if "stored_rows" in cols and "observations" in cols:
            d["videos_with_multiple_contexts"] = sum(1 for r in rows if r.get("discovery_contexts", "1") not in ("", "1"))
            d["videos_with_repeat_observations"] = sum(1 for r in rows if (fnum(r.get("observations")) or 0) >= 2)
        if "category_mismatch" in cols:
            d["category_mismatch"] = sum(1 for r in rows if r.get("category_mismatch") == "true")
        if "shorts_status" in cols:
            d["shorts_status"] = dict(Counter(r.get("shorts_status") or "blank" for r in rows))
        for col in ("region_param", "relevance_language_param", "language_edition", "geo", "region", "language"):
            if col in cols:
                d.setdefault("scope_values", {})[col] = dict(Counter(r.get(col) or "(blank)" for r in rows).most_common(8))
        if prov == "observations" and rows:
            times = defaultdict(set)
            for r in rows:
                times[r["content_key"]].add(r["observed_at_utc"])
            d["items_with_one_observation_time"] = sum(1 for k in times if len(times[k]) == 1)
            d["items"] = len(times)
        report["datasets"].append(d)
    dest = (label.with_suffix("") if label.suffix == ".zip" else label)
    dest = Path(str(dest) + "_intake") if label.suffix == ".zip" else Path(label) / "intake"
    (dest.parent).mkdir(parents=True, exist_ok=True)
    Path(str(dest) + ".json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    md = [f"# Bundle intake: {Path(label).name}", "", f"Checked {report['checked_at']}. Read this before analysing values.", "",
          "| file | provider | rows | provenance | expires | dictionary | time range |", "|---|---|---|---|---|---|---|"]
    for d in report["datasets"]:
        tr = d.get("time_range", {})
        md.append(f"| {d['file']} | {d['provider']} | {d['rows']} | {d['provenance']} | {d['expires_at_utc'] or 'none'} | "
                  f"{'yes' if d['has_dictionary'] else 'NO'} | {tr.get('first', '')[:16]} to {tr.get('last', '')[:16]} ({tr.get('distinct', 0)} distinct) |")
    md += ["", "## Issues", ""] + ([f"- {i}" for i in report["issues"]] or ["- none found"]) + ["", "## Per dataset", ""]
    for d in report["datasets"]:
        md += [f"### {d['file']}", ""]
        for k in ("missing_by_column", "rounded_values", "metric_definition", "provenance_rows", "sample_role",
                  "duplicate_context_rows", "videos_with_multiple_contexts", "videos_with_repeat_observations",
                  "category_mismatch", "shorts_status", "scope_values", "items", "items_with_one_observation_time"):
            if k in d and d[k] not in ({}, None):
                md.append(f"- {k.replace('_', ' ')}: {json.dumps(d[k], ensure_ascii=False)}")
        md += [f"- cannot answer: {d['cannot_answer']}", ""]
    Path(str(dest) + ".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{len(report['datasets'])} datasets, {len(report['issues'])} issues -> {dest}.md / .json")
    for i in report["issues"]:
        print("  ISSUE", i)
    return report


# ---------- describe / repeat / sensitivity ----------


def filtered(rows, where):
    for w in where or []:
        k, _, v = w.partition("=")
        rows = [r for r in rows if r.get(k) == v]
    return rows


def youtube_guard(path, rows, per_item_ok=False):
    """Policy III.E.2.a: no aggregation of API data across content owners."""
    if provider_of(Path(path).name, rows[0].keys() if rows else ()) == "youtube":
        chans = {r.get("channel_id") or r.get("channel_title") for r in rows}
        if len(chans) > 1:
            return (f"YouTube API rows from {len(chans)} channels: aggregating across channels isn't permitted "
                    "(Developer Policies III.E.2.a). Use --where channel_id=... for one channel, or `repeat` per video.")
    return None


def cmd_describe(a):
    rows = filtered(load_csv(a.file), a.where)
    stop = youtube_guard(a.file, rows)
    if stop:
        sys.exit(stop)
    groups = defaultdict(list)
    for r in rows:
        groups[r.get(a.by, "") if a.by else "all"].append(r)
    out = []
    for g, rs in sorted(groups.items()):
        vals = [fnum(r.get(a.metric)) for r in rs]
        present = [v for v in vals if v is not None]
        out.append({"group": g, "rows": len(rs), "missing": len(vals) - len(present), **stats(present)})
    print(json.dumps({"file": Path(a.file).name, "metric": a.metric, "by": a.by, "where": a.where, "groups": out},
                     indent=1, ensure_ascii=False))
    print("Denominator note: n counts rows with a value; 'missing' rows are unknown, not zero.", file=sys.stderr)


def item_key(name, r):
    if "content_key" in r:
        return (r["content_key"], r.get("metric", ""), r.get("source", ""), r.get("region", ""), r.get("period", ""),
                r.get("category", ""))
    for k in ("video_id", "clip_id", "universe_id", "stream_id"):
        if r.get(k):
            return (r[k],)
    return (r.get("article_title", ""), r.get("project", ""))


def series_value(r):
    for k in ("value_numeric", "views", "view_count", "playing", "visits", "viewer_count"):
        if r.get(k, "") != "":
            return k, fnum(r[k])
    return None, None


def cmd_repeat(a):
    rows = load_csv(a.file)
    name = Path(a.file).name
    tcol = next((c for c in ("observation_moment", "observed_at_utc") if rows and c in rows[0]), None)
    items = defaultdict(list)
    for r in rows:
        items[item_key(name, r)].append(r)
    out = []
    for k, rs in items.items():
        # one value per observation moment (duplicate discovery contexts collapse)
        moments = {}
        for r in sorted(rs, key=lambda r: r.get(tcol, "")):
            moments[r.get(tcol, "")] = r
        seq = list(moments.items())
        if len(seq) < 2 and not a.all:
            continue
        col, _ = series_value(seq[-1][1])
        points = [(t, fnum(r.get(col)) if col else None) for t, r in seq]
        changes = []
        for (t0, v0), (t1, v1) in zip(points, points[1:]):
            h = (rc.parse_time(t1) - rc.parse_time(t0)).total_seconds() / 3600 if t0 and t1 else None
            changes.append({"from": t0, "to": t1, "hours": round(h, 2) if h else h,
                            "change": (v1 - v0) if v0 is not None and v1 is not None else None,
                            "per_hour": round((v1 - v0) / h, 2) if v0 is not None and v1 is not None and h else None,
                            **({"flag": "negative revision (platform correction or removal), not negative demand"}
                               if v0 is not None and v1 is not None and v1 < v0 else {})})
        out.append({"item": list(k), "metric": col, "observations": len(points), "points": points, "changes": changes,
                    "note": "same item, same scope only; compare an item only with itself"})
    print(json.dumps({"file": name, "items_with_repeats": len(out), "items": out[: a.limit]}, indent=1, ensure_ascii=False))


def cmd_sensitivity(a):
    rows = filtered(load_csv(a.file), a.where)
    stop = youtube_guard(a.file, rows)
    if stop:
        sys.exit(stop)
    creator = next((c for c in ("creator_handle", "creator_name", "broadcaster_name", "channel_title") if rows and c in rows[0]), None)
    present = [fnum(r.get(a.metric)) for r in rows if fnum(r.get(a.metric)) is not None]
    cut = quantile(present, 0.99) if present else None
    variants = {"all": rows}
    if cut is not None:
        variants["drop_top_1pct"] = [r for r in rows if fnum(r.get(a.metric)) is None or fnum(r.get(a.metric)) <= cut]
    if rows and "sample_role" in rows[0]:
        variants["ordinary_or_failed_only"] = [r for r in rows if r.get("sample_role") in ("ordinary", "failed")]
    if rows and "published_at_utc" in rows[0] and "observed_at_utc" in rows[0]:
        variants["older_than_48h"] = [r for r in rows if r.get("published_at_utc") and r.get("observed_at_utc") and
                                      (rc.parse_time(r["observed_at_utc"]) - rc.parse_time(r["published_at_utc"])).total_seconds() >= 48 * 3600]
    if creator:
        for c in sorted({r.get(creator) for r in rows if r.get(creator)}):
            variants[f"leave_out:{c}"] = [r for r in rows if r.get(creator) != c]
    table = {}
    for name, subset in variants.items():
        g = defaultdict(list)
        for r in subset:
            v = fnum(r.get(a.metric))
            if v is not None:
                g[r.get(a.by, "")].append(v)
        table[name] = {k: {"n": len(v), "median": statistics.median(v)} for k, v in g.items()}
    base = table["all"]
    order = lambda t: [k for k, _ in sorted(t.items(), key=lambda kv: -kv[1]["median"])]
    fragile = []
    for name, t in table.items():
        if name == "all" or not t:
            continue
        if order(t)[:1] != order(base)[:1]:
            fragile.append(f"{name}: the top group changes ({order(base)[:1]} -> {order(t)[:1]})")
        for k, v in t.items():
            if k in base and base[k]["median"] and abs(v["median"] - base[k]["median"]) / base[k]["median"] > a.tolerance:
                fragile.append(f"{name}: '{k}' median moves {base[k]['median']:g} -> {v['median']:g}")
    verdict = "fragile" if fragile else "robust to these specifications"
    print(json.dumps({"file": Path(a.file).name, "metric": a.metric, "by": a.by, "verdict": verdict, "fragility": fragile,
                      "variants": table}, indent=1, ensure_ascii=False))


# ---------- trend dimensions ----------


def matches(text, term):
    return term.lower().lstrip("#") in (text or "").lower()


def cmd_trend(a):
    term = a.term
    D = rc.DATA
    dims = {"heat": [], "velocity": [], "breadth": [], "persistence": [], "novelty": [], "context_fit": [], "slugshot_fit": []}
    comparable_series = 0
    # Public observations (Creative Center, pages, tools)
    obs = [r for r in rc.read_rows(D / "observations" / "public_observations.csv")
           if matches(r.get("title_or_name", "") + " " + r.get("content_key", ""), term) and r.get("metric") not in ("_seen",)]
    groups = defaultdict(list)
    for r in obs:
        groups[(r["content_key"], r["metric"], r["source"], r["region"], r["period"], r["category"])].append(r)
    for k, rs in groups.items():
        rs.sort(key=lambda r: r["observed_at_utc"])
        last = rs[-1]
        dims["heat"].append(f"{last['title_or_name']} {k[1]} = {last['value_display']} ({last['source']}, {k[3] or 'no region'}, "
                            f"{k[4] or 'no period'}, {last['observed_at_utc'][:10]}, {last['provenance']}, definition {last['metric_definition']})")
        times = sorted({r["observed_at_utc"] for r in rs})
        dims["persistence"].append(f"{last['title_or_name']} {k[1]} [{k[3]}/{k[4]}]: seen at {len(times)} time(s)")
        if len(times) >= 2:
            comparable_series += 1
            dims["velocity"].append(f"{last['title_or_name']} {k[1]} [{k[3]}/{k[4]}]: " + " -> ".join(
                f"{r['value_display']}@{r['observed_at_utc'][:10]}" for r in rs) + (" (rounded displays)" if any(r["value_rounded"] == "true" for r in rs) else ""))
    creators = {r.get("creator_handle") or r.get("creator_name") for r in obs if r.get("entity_type") == "post"} - {""}
    if creators:
        dims["breadth"].append(f"{len(creators)} distinct creators among observed posts mentioning '{term}'")
    # Trending Now
    tn = [r for r in rc.read_rows(D / "google_trends" / "trending_now.csv") if matches(r.get("term", ""), term)]
    if tn:
        dims["heat"].append(f"Google Trending Now: {len(tn)} appearances in {sorted({r['geo'] for r in tn})} (all-topic feed)")
        dims["persistence"].append(f"Trending Now: {len({r['observed_at_utc'][:10] for r in tn})} distinct days")
    # Explore imports
    ex = [r for r in rc.read_rows(D / "google_trends" / "explore_values.csv") if matches(r.get("term", "") + r.get("query", ""), term)]
    if ex:
        dims["heat"].append(f"Google Trends Explore: {len(ex)} values across {len({r['import_id'] for r in ex})} downloads "
                            "(each its own 0-100 scale)")
    # Wikipedia
    wk = [r for r in rc.read_rows(D / "wikimedia" / "wiki_pageviews.csv") if matches(r.get("entity_id", "") + " " + r.get("article_title", ""), term)]
    if wk:
        by = defaultdict(list)
        for r in wk:
            by[r["project"]].append((r["period_start"], fnum(r["views"])))
        for proj, pts in by.items():
            pts.sort()
            half = len(pts) // 2
            if half >= 7:
                m1 = statistics.median(v for _, v in pts[:half] if v is not None)
                m2 = statistics.median(v for _, v in pts[half:] if v is not None)
                dims["velocity"].append(f"Wikipedia {proj}: median daily views {m1:g} (first half) -> {m2:g} (second half) "
                                        f"over {pts[0][0]}..{pts[-1][0]} (attention proxy, not fandom size)")
                comparable_series += 1
    # YouTube (sample counts only; no cross-channel aggregation of statistics)
    yt = [r for r in rc.read_rows(D / "youtube" / "youtube_snapshots.csv") if matches(r.get("title", "") + " " + r.get("tags", ""), term)]
    if yt:
        vids = {r["video_id"] for r in yt}
        dims["breadth"].append(f"YouTube: {len(vids)} retrieved videos from {len({r['channel_id'] for r in yt})} channels mention "
                               f"'{term}' (a retrieval count, not a popularity measure)")
        titles = {re.sub(r"\W+", " ", r["title"].lower()).strip() for r in yt}
        dims["novelty"].append(f"YouTube: {len(titles)} distinct titles among {len(vids)} videos (rough variety indicator; "
                               "real novelty needs coding)")
    tw = [r for r in rc.read_rows(D / "twitch" / "twitch_clips.csv") if matches(r.get("title", ""), term)]
    if tw:
        dims["breadth"].append(f"Twitch: {len({r['clip_id'] for r in tw})} clips from {len({r['broadcaster_id'] for r in tw})} broadcasters (24 h store)")
    ann = rc.read_rows(OUT / "annotations_joined.csv")
    fit = [r for r in ann if matches(r.get("title", "") + r.get("title_or_name", ""), term)]
    dims["context_fit"].append(f"{len(fit)} coded items" if fit else "unknown: no coded examples yet (use blind-packet + coding)")
    dims["slugshot_fit"].append("judgement for ChatGPT/owner: map the mechanism to an approved Slugshot scenario")
    # Lifecycle proposal (rule-based; confirm in the ledger)
    if comparable_series == 0:
        life, why = "unknown", "no repeated comparable observations (one snapshot cannot show direction)"
    else:
        life, why = "unknown (direction data exists)", "read the velocity lines; label only with consistent direction across " \
                                                     "comparable series plus breadth evidence"
    out = {"term": term, "checked_at": rc.iso(rc.now()), "dimensions": dims, "comparable_series": comparable_series,
           "lifecycle_proposal": life, "lifecycle_reason": why,
           "rules": "emerging/accelerating need >=2 comparable rising observations (+ breadth for accelerating); declining needs "
                    ">=2 comparable falling ones; saturated needs high volume AND evidence of falling novelty; else unknown"}
    dest = OUT / f"trend_{re.sub(r'[^a-z0-9]+', '_', term.lower())}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for k, v in dims.items():
        print(f"{k:13} " + (" | ".join(v) if v else "no evidence collected"))
    print(f"lifecycle    {life}: {why}\n-> {dest}")


# ---------- change points ----------


def cmd_changepoints(a):
    import numpy as np
    import ruptures
    rows = rc.read_rows(rc.DATA / "wikimedia" / "wiki_pageviews.csv")
    series = defaultdict(list)
    for r in rows:
        if r["granularity"] == "daily" and (not a.entity or r["entity_id"] == a.entity):
            series[(r["entity_id"], r["project"], r["article_title"])].append((r["period_start"], fnum(r["views"]) or 0.0))
    ok = {(r["project"], r["article_title"]) for r in rc.read_rows(rc.DATA / "wikimedia" / "wiki_coverage.csv") if r["status"] == "ok"}
    out = []
    for k, pts in series.items():
        pts.sort()
        if (k[1], k[2]) in ok:  # Wikimedia omits zero-view days inside a successful window, so those days really are 0
            have = dict(pts)
            day, last, filled = rc.parse_time(pts[0][0]), rc.parse_time(pts[-1][0]), []
            while day <= last:
                ds = day.date().isoformat()
                filled.append((ds, have.get(ds, 0.0)))
                day += timedelta(days=1)
            pts = filled
        if len(pts) < a.min_days:
            out.append({"series": list(k), "points": len(pts), "result": f"too short (< {a.min_days} days); no change-point analysis"})
            continue
        y = np.log1p(np.array([v for _, v in pts]))
        algo = ruptures.Pelt(model="rbf", min_size=7).fit(y.reshape(-1, 1))
        bkps = algo.predict(pen=a.penalty)[:-1]
        segs, start = [], 0
        for b in bkps + [len(pts)]:
            vals = [v for _, v in pts[start:b]]
            segs.append({"from": pts[start][0], "to": pts[b - 1][0], "median_daily_views": statistics.median(vals)})
            start = b
        out.append({"series": list(k), "points": len(pts), "change_points": [pts[b][0] for b in bkps], "segments": segs})
    note = ("Wikipedia page views are an attention proxy for a language edition, not fandom size. Check a change point "
            "against news context (`ss analyze context gdelt`) before interpreting it.")
    print(json.dumps({"method": f"ruptures PELT rbf on log1p(daily views), pen={a.penalty}, min_size=7", "note": note,
                      "series": out}, indent=1, ensure_ascii=False))


# ---------- outcome-blind coding ----------


def blind_key(r):
    for k in ("content_key", "video_id", "clip_id", "url"):
        if r.get(k):
            return r[k]
    return ""


def cmd_sample(a):
    """Deterministic, outcome-blind sample selection from collected YouTube snapshots, driven by a spec:
    {"groups": [{"name", "sample_role", "n", "collections": [prefixes], "max_duration_s", "watchlist_language",
    "declared_audio_language"}]}. declared_audio_language keeps rows whose creator-declared audio matches (e.g. "es"),
    so a Spanish branch's English-declared results don't stand in for Spanish content.
    Order: newest first (published_at desc, then video_id); one item per channel across the whole sample.
    Never reads or prints outcome columns while selecting."""
    import csv as _csv
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    snaps = rc.read_rows(rc.DATA / "youtube" / "youtube_snapshots.csv")
    latest, member = {}, defaultdict(set)
    for r in snaps:
        member[r["video_id"]].add(r.get("collection", ""))
        if r["video_id"] not in latest or r["observed_at_utc"] > latest[r["video_id"]]["observed_at_utc"]:
            latest[r["video_id"]] = r
    wl = {}
    wpath = rc.CONFIG / "youtube_creators.csv"
    if wpath.exists():
        with wpath.open(newline="", encoding="utf-8-sig") as f:
            wl = {x["channel_id"]: x for x in _csv.DictReader(f)}
    used_channels, chosen, report = set(), [], []
    for g in spec["groups"]:
        pool = [v for vid, v in latest.items()
                if any(c.startswith(p) for c in member[vid] for p in g["collections"])
                and (not g.get("max_duration_s") or (fnum(v.get("duration_s")) or 10**9) <= g["max_duration_s"])
                and (not g.get("watchlist_language") or wl.get(v["channel_id"], {}).get("language_stream") == g["watchlist_language"])
                and (not g.get("declared_audio_language")
                     or (v.get("default_audio_language") or "").split("-")[0] == g["declared_audio_language"])]
        pool.sort(key=lambda v: (v.get("published_at", ""), v["video_id"]), reverse=True)
        got = []
        for v in pool:
            if v["channel_id"] in used_channels:
                continue
            used_channels.add(v["channel_id"])
            got.append(v)
            if len(got) >= g["n"]:
                break
        for rank, v in enumerate(got, 1):
            chosen.append({**v, "sample_group": g["name"], "sample_role": g["sample_role"], "selection_rank": rank,
                           "selection_rule": f"newest-first distinct channel in {'|'.join(g['collections'])}"
                                             + (f", <= {g['max_duration_s']} s" if g.get("max_duration_s") else "")
                                             + (f", watchlist language {g['watchlist_language']}" if g.get("watchlist_language") else "")
                                             + (f", declared audio {g['declared_audio_language']}" if g.get("declared_audio_language") else ""),
                           "retrieval_contexts": "|".join(sorted(c for c in member[v["video_id"]] if c))})
        report.append(f"{g['name']}: {len(got)}/{g['n']} selected from {len(pool)} eligible")
    name = Path(a.spec).stem
    dest = OUT / f"sample_{name}.csv"
    fields = list(chosen[0].keys()) if chosen else []
    rc.write_rows(dest, fields, chosen)
    # Outcome-blind packet straight away, so the coder never needs to open the full sample file.
    pkt = OUT / f"blind_packet_sample_{name}.jsonl"
    with pkt.open("w", encoding="utf-8") as f:
        for v in chosen:
            item = {"key": v["video_id"], "platform": "youtube", "url": v["url"], "title": v.get("title", ""),
                    "tags": v.get("tags", ""), "duration_s": v.get("duration_s", ""), "published_at": v.get("published_at", ""),
                    "language_hint": v.get("default_audio_language", "")}
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print("\n".join(report))
    print(f"{len(chosen)} items -> {dest} (contains outcomes: don't open before coding)\nblind packet -> {pkt}")


def cmd_blind_packet(a):
    rows = load_csv(a.file)
    seen, packet = set(), []
    for r in rows:
        k = blind_key(r)
        if not k or k in seen:
            continue
        seen.add(k)
        item = {"key": k}
        for f in BLIND_ALLOW[1:]:  # allowlist: future outcome columns can never leak into the packet
            if r.get(f):
                item[f] = r[f]
        if a.include_creator:  # off by default: a famous name biases coding as much as a view count
            item["creator"] = r.get("creator_handle") or r.get("channel_title") or r.get("broadcaster_name") or ""
        packet.append(item)
    dest = Path(a.out) if a.out else OUT / f"blind_packet_{Path(a.file).stem}.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as f:
        for item in packet:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"{len(packet)} items (no metrics, ranks or outcomes) -> {dest}\nCode them with config/research/codebooks/ before "
          "running join-annotations.")


def cmd_join(a):
    """Multi-label annotations (codebook v1.0): {key, codebook_version, access, blinded, codes: {CODE: state},
    evidence: [{quote}] and/or evidence_note, beats{...}}. States: present / absent / uncertain / unreviewed."""
    rows = load_csv(a.file)
    codebook = json.loads(Path(a.codebook).read_text(encoding="utf-8"))
    codes = [c["code"] for c in codebook["codes"]]
    states, access_levels = set(codebook["states"]), set(codebook["access_levels"])
    index = {}
    for r in rows:
        index.setdefault(blind_key(r), r)
    packet_text = {}
    pkt = OUT / f"blind_packet_{Path(a.file).stem}.jsonl"
    if pkt.exists():
        for line in pkt.read_text(encoding="utf-8").splitlines():
            it = json.loads(line)
            packet_text[it["key"]] = " ".join(str(v) for v in it.values())
    errors, joined, seen = [], [], set()
    anns = [json.loads(line) for line in Path(a.annotations).read_text(encoding="utf-8").splitlines() if line.strip()]
    for n, ann in enumerate(anns, 1):
        k = ann.get("key")
        where = f"annotation {n} ({k})"
        if k not in index:
            errors.append(f"{where}: key not in the dataset")
            continue
        if k in seen:
            errors.append(f"{where}: duplicate key")
        seen.add(k)
        if ann.get("codebook_version") != codebook.get("version"):
            errors.append(f"{where}: codebook_version {ann.get('codebook_version')} != {codebook.get('version')}")
        if ann.get("access") not in access_levels:
            errors.append(f"{where}: access must be one of {sorted(access_levels)}")
        if not isinstance(ann.get("blinded"), bool):
            errors.append(f"{where}: blinded must be true or false (false if outcomes were seen before coding)")
        given = ann.get("codes") or {}
        for code, state in given.items():
            if code not in codes:
                errors.append(f"{where}: unknown code '{code}'")
            if state not in states:
                errors.append(f"{where}: {code} state '{state}' must be one of {sorted(states)}")
            if state == "absent" and ann.get("access") not in ("full_playback", "excerpt"):
                errors.append(f"{where}: {code}=absent needs full_playback or excerpt access")
        if any(s == "present" for s in given.values()) and not (ann.get("evidence") or ann.get("evidence_note")):
            errors.append(f"{where}: 'present' codes need evidence (exact quote or a timestamped viewing note)")
        src = packet_text.get(k, "") + " " + " ".join(index[k].get(f, "") for f in BLIND_ALLOW)
        for ev in ann.get("evidence", []):
            q = ev.get("quote", "")
            if q and q not in src:
                errors.append(f"{where}: quote '{q[:40]}' is not an exact substring of the item text")
        r = index[k]
        joined.append({"key": k, "title": r.get("title") or r.get("title_or_name", ""), "access": ann.get("access"),
                       "blinded": str(ann.get("blinded")).lower(),
                       "sample_role": r.get("sample_role") or ann.get("sample_role") or "unknown",
                       **{f"code_{c}": given.get(c, "unreviewed") for c in codes},
                       "outcome": r.get(a.metric, ""), "provider": provider_of(Path(a.file).name, rows[0].keys() if rows else ())})
    if errors:
        print("\n".join("ERROR " + e for e in errors))
        sys.exit(1)
    dest = OUT / "annotations_joined.csv"
    cols = ["key", "title", "access", "blinded", "sample_role", "provider", "outcome"] + [f"code_{c}" for c in codes]
    rc.write_rows(dest, cols, joined)
    youtube = provider_of(Path(a.file).name, rows[0].keys() if rows else ()) == "youtube"
    table = []
    for c in codes:
        row = {"code": c}
        for role in sorted({j["sample_role"] for j in joined}):
            grp = [j for j in joined if j["sample_role"] == role]
            cnt = Counter(j[f"code_{c}"] for j in grp)
            cell = {s: cnt.get(s, 0) for s in ("present", "absent", "uncertain", "unreviewed")}
            cell["reviewed_denominator"] = cell["present"] + cell["absent"]
            if not youtube:
                for s in ("present", "absent"):
                    vals = [fnum(j["outcome"]) for j in grp if j[f"code_{c}"] == s and fnum(j["outcome"]) is not None]
                    cell[f"median_outcome_{s}"] = statistics.median(vals) if vals else None
                    cell[f"n_outcome_{s}"] = len(vals)
            row[role] = cell
        table.append(row)
    unblinded = sum(1 for j in joined if j["blinded"] == "false")
    print(json.dumps({"joined": len(joined), "unblinded": unblinded, "dest": str(dest), "codebook": codebook["version"],
                      "association_table": table,
                      "note": ("YouTube: counts only (no cross-channel aggregation of statistics). " if youtube else "") +
                              "Associations, not effects. Compare prevalence with ordinary items: a code as common in "
                              "ordinary items as in featured ones does not distinguish success."}, indent=1, ensure_ascii=False))


# ---------- context ----------


def cmd_context(a):
    if a.source == "wikidata":
        body, _ = rc.http("https://www.wikidata.org/w/api.php", {"action": "wbsearchentities", "search": a.term,
                                                                 "language": a.lang, "uselang": a.lang, "format": "json", "limit": 5})
        hits = json.loads(body).get("search", [])
        ids = "|".join(h["id"] for h in hits)
        ents = {}
        if ids:
            body, _ = rc.http("https://www.wikidata.org/w/api.php", {"action": "wbgetentities", "ids": ids, "format": "json",
                                                                     "props": "labels|aliases|descriptions|sitelinks",
                                                                     "languages": "en|es", "sitefilter": "enwiki|eswiki"})
            ents = json.loads(body).get("entities", {})
        for h in hits:
            e = ents.get(h["id"], {})
            print(json.dumps({"id": h["id"], "label": {l: e.get("labels", {}).get(l, {}).get("value") for l in ("en", "es")},
                              "description": h.get("description"),
                              "aliases": {l: [x["value"] for x in e.get("aliases", {}).get(l, [])][:10] for l in ("en", "es")},
                              "wikipedia": {s: v.get("title") for s, v in e.get("sitelinks", {}).items()}}, ensure_ascii=False))
    else:
        import time
        params = {"query": f'"{a.term}"', "mode": "timelinevolraw", "format": "json", "timespan": f"{a.days}d"}
        for attempt in range(3):  # GDELT allows one request per 5 s and answers 429 otherwise
            try:
                body, _ = rc.http("https://api.gdeltproject.org/api/v2/doc/doc", params)
                break
            except rc.HttpError as e:
                if e.status != 429 or attempt == 2:
                    sys.exit(f"GDELT error {e.status}: {e.reason[:160]}")
                time.sleep(6 * (attempt + 1))
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            sys.exit(f"GDELT returned no JSON (it rate-limits rapid calls; retry in a few seconds): {body[:120]!r}")
        tl = (data.get("timeline") or [{}])[0].get("data", [])
        vals = [(p["date"][:8], p.get("value"), p.get("norm")) for p in tl]
        print(json.dumps({"term": a.term, "days": a.days, "points": len(vals),
                          "daily_matching_articles": vals,
                          "note": "News coverage context only (GDELT monitors online news). Use it to check whether a "
                                  "search/page-view spike coincides with a news event; it is not gaming or fandom demand."},
                         ensure_ascii=False))


def main():
    sys.stdout.reconfigure(errors="replace")  # titles contain emoji the Windows console can't encode
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", help="read stores from this folder instead of data/local/research (tests)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("intake")
    i.add_argument("bundle", nargs="?")
    d = sub.add_parser("describe")
    d.add_argument("file")
    d.add_argument("metric")
    d.add_argument("--by")
    d.add_argument("--where", action="append")
    r = sub.add_parser("repeat")
    r.add_argument("file")
    r.add_argument("--all", action="store_true", help="include single-observation items")
    r.add_argument("--limit", type=int, default=200)
    s = sub.add_parser("sensitivity")
    s.add_argument("file")
    s.add_argument("metric")
    s.add_argument("--by", required=True)
    s.add_argument("--where", action="append")
    s.add_argument("--tolerance", type=float, default=0.25, help="relative median change that counts as fragile")
    t = sub.add_parser("trend")
    t.add_argument("term")
    c = sub.add_parser("changepoints")
    c.add_argument("--entity")
    c.add_argument("--penalty", type=float, default=5.0)
    c.add_argument("--min-days", type=int, default=28)
    sp = sub.add_parser("sample", help="deterministic outcome-blind sample from YouTube snapshots (spec JSON)")
    sp.add_argument("spec")
    b = sub.add_parser("blind-packet")
    b.add_argument("file")
    b.add_argument("--out")
    b.add_argument("--include-creator", action="store_true", help="add creator names (excluded by default)")
    j = sub.add_parser("join-annotations")
    j.add_argument("file")
    j.add_argument("annotations", help="JSONL: key, codebook_version, access, blinded, codes{CODE: state}, evidence[{quote}]")
    j.add_argument("--codebook", default=str(rc.CONFIG / "codebooks" / "slugshot-creative.json"))
    j.add_argument("--metric", default="value_numeric")
    x = sub.add_parser("context")
    x.add_argument("source", choices=["wikidata", "gdelt"])
    x.add_argument("term")
    x.add_argument("--lang", default="en")
    x.add_argument("--days", type=int, default=30)
    a = ap.parse_args()
    if a.data_dir:
        global OUT
        rc.DATA = Path(a.data_dir)
        OUT = rc.DATA / "analysis"
    {"intake": cmd_intake, "describe": cmd_describe, "repeat": cmd_repeat, "sensitivity": cmd_sensitivity,
     "trend": cmd_trend, "changepoints": cmd_changepoints, "sample": cmd_sample, "blind-packet": cmd_blind_packet, "join-annotations": cmd_join,
     "context": cmd_context}[a.cmd](a)


if __name__ == "__main__":
    main()
