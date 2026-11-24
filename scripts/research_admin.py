"""Research housekeeping across every collector.

  status    credentials present (yes/no only), gates, stored rows, expired rows, last run per provider,
            today's YouTube quota
  prune     apply every retention rule: YouTube 30 days, Twitch retention_hours, Trends RSS local period,
            and delete expired files in exports/share/research/ (per MANIFEST.csv)
  runs      the last collection runs (parameters actually sent)
  collect   run a profile (daily / spanish / refresh): each step continues if another fails, then bundle
  bundle    export every store, prune, and zip the newest exports + MANIFEST + DATA_DICTIONARY + BUNDLE_SUMMARY.md
            -> exports/share/bundles/slugshot_research_<time>.zip (one file to give ChatGPT)
"""
import argparse
import json
import re
import subprocess
import sys

import research_common as rc

PY = sys.executable


def stores(base):
    return {
        "youtube": [base / "youtube" / f for f in ("youtube_snapshots.csv", "youtube_channels.csv", "youtube_comments.csv")],
        "wikimedia": [base / "wikimedia" / "wiki_pageviews.csv"],
        "google_trends": [base / "google_trends" / f for f in ("trending_now.csv", "explore_values.csv")],
        "twitch": [base / "twitch" / f for f in ("twitch_clips.csv", "twitch_streams.csv")],
        "roblox": [base / "roblox" / "roblox_experiences.csv"],
        "observations": [base / "observations" / "public_observations.csv"],
    }


def cmd_status(a):
    cfg = rc.settings()
    yes = lambda n: "present" if rc.env_value(n) else "MISSING"
    print("Credentials (.env; values never shown):")
    print(f"  YOUTUBE_API_KEY       {yes('YOUTUBE_API_KEY')}")
    print(f"  TWITCH_CLIENT_ID      {yes('TWITCH_CLIENT_ID')}")
    print(f"  TWITCH_CLIENT_SECRET  {yes('TWITCH_CLIENT_SECRET')}")
    print("Gates (config/research/settings.json):")
    print(f"  twitch.terms_reviewed {cfg['twitch']['terms_reviewed']}   twitch.share_exports {cfg['twitch']['share_exports']}"
          f"   twitch.retention_hours {cfg['twitch']['retention_hours']}")
    print(f"  contact for User-Agent: {'set' if cfg.get('contact') else 'not set (optional; Wikimedia asks for one)'}")
    now = rc.now()
    print("Stored data (data/local/research/):")
    for p, files in stores(rc.DATA).items():
        for f in files:
            rows = rc.read_rows(f)
            expired = sum(1 for r in rows if r.get("expires_at_utc") and rc.parse_time(r["expires_at_utc"]) <= now)
            if rows or a.all:
                print(f"  {p:14} {f.name:26} {len(rows):7} rows" + (f"  ({expired} expired: run prune)" if expired else ""))
    runs = rc.read_rows(rc.DATA / "runs.csv")
    last = {}
    for r in runs:
        last[r["provider"]] = r
    print("Last run per provider:")
    for p, r in sorted(last.items()):
        print(f"  {p:14} {r['finished_at_utc']}  {r['command']:12} {r['status']:8} {r['rows_written']} rows")
    if not last:
        print("  none yet")
    sys.stdout.flush()
    subprocess.run([PY, str(rc.ROOT / "scripts" / "yt_collect.py"), "quota"])


def cmd_prune(a):
    removed = 0
    for args in (["yt_collect.py", "prune"], ["twitch_collect.py", "prune"]):
        subprocess.run([PY, str(rc.ROOT / "scripts" / args[0]), *args[1:]])
    from trends_collect import RSS_FIELDS
    removed += rc.prune_file(rc.DATA / "google_trends" / "trending_now.csv", RSS_FIELDS)
    gone = rc.prune_exports()
    print(f"Trends RSS rows pruned: {removed}. Expired exports deleted: {len(gone)}" + (f" ({', '.join(gone)})" if gone else ""))


ES_GEOS = ["MX", "ES", "AR", "CO", "CL"]


def has_set(name):
    try:
        return name in rc.load_json_config("youtube_queries.json")["sets"]
    except Exception:
        return False


def has_rows(csv_name, col):
    import csv as _csv
    p = rc.CONFIG / csv_name
    if not p.exists():
        return False
    with p.open(newline="", encoding="utf-8-sig") as f:
        return any(r.get(col, "").strip() for r in _csv.DictReader(f))


def profile_steps(profile, yt_set):
    geos = rc.settings()["trends"]["geos"]
    s = []
    if profile in ("daily", "spanish"):
        g = ES_GEOS if profile == "spanish" else geos
        s.append(("Google Trending Now", ["trends_collect.py", "rss", "--geo", ",".join(g)]))
        s += [(f"YouTube Gaming chart {r}", ["yt_collect.py", "chart", "--region", r, "--max", "50"]) for r in g]
        name = yt_set or profile
        if has_set(name):
            s.append((f"YouTube saved query set '{name}'", ["yt_collect.py", "sweep", "--set", name, "--check-shorts"]))
        elif profile == "spanish":  # default until ChatGPT defines a 'spanish' set
            s += [(f"YouTube search 'roblox' es/{r} (default query)",
                   ["yt_collect.py", "discover", "roblox", "--lang", "es", "--region", r, "--days", "3", "--max", "25"]) for r in g]
        else:
            s.append((f"YouTube saved query set '{name}'", None))  # reported as skipped: no set defined yet
        lang = "es" if profile == "spanish" else "en,es"
        s.append(("Twitch Roblox clips (24 h)", ["twitch_collect.py", "clips", "--game", "Roblox", "--hours", "24", "--lang", lang]))
        s.append(("Twitch Roblox live streams", ["twitch_collect.py", "streams", "--game", "Roblox", "--lang", lang]))
    if profile in ("daily", "refresh"):
        if has_rows("youtube_creators.csv", "channel_id"):
            s.append(("YouTube creator uploads (7 days)", ["yt_collect.py", "creators", "--days", "7"]))
        s.append(("YouTube watchlist re-snapshot", ["yt_collect.py", "stats"]))
        s.append(("Twitch clip re-observation", ["twitch_collect.py", "recheck"]))
        if has_rows("twitch_broadcasters.csv", "login"):
            s.append(("Twitch broadcaster watchlist", ["twitch_collect.py", "watch", "--hours", "48"]))
    s.append(("Wikipedia page views (7 days)", ["wiki_collect.py", "pull", "--days", "7"]))
    s.append(("Roblox experience watchlist", ["rbx_collect.py", "games"]))
    return s


def cmd_collect(a):
    started = rc.now()
    results = []
    for name, cmd in profile_steps(a.profile, a.yt_set):
        if cmd is None:
            results.append((name, "SKIPPED", "no saved query set with that name yet (config/research/youtube_queries.json)"))
            print(f"SKIPPED  {name}")
            continue
        r = subprocess.run([PY, str(rc.ROOT / "scripts" / cmd[0]), *cmd[1:]], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = [l for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()]
        counts = [l for l in out if re.search(r"\d+ (clips|rows|snapshots|points|live|videos|comments|uploads|values)", l)]
        last = (counts[-1] if counts and r.returncode == 0 else (out[-1] if out else "")).strip()[:240]
        status = "OK" if r.returncode == 0 else ("BLOCKED" if "BLOCKED" in last or "wait until" in last or "Stopped before" in last else "FAILED")
        results.append((name, status, last))
        print(f"{status:8} {name}: {last}")
    a.since = rc.iso(started)
    cmd_bundle(a, results)


def newest_exports(base):
    import re as _re
    newest = {}
    for r in rc.read_rows(base / "MANIFEST.csv"):
        newest[_re.sub(r"_\d{8}T\d{4}Z\.csv$", "", r["file"])] = r
    return newest


def cmd_bundle(a, steps=None):
    """Export every store, apply retention, then zip the newest export of each kind + MANIFEST + DATA_DICTIONARY +
    BUNDLE_SUMMARY.md into exports/share/bundles/. Twitch stays local unless share_exports is on."""
    import zipfile
    for cmd in (["yt_collect.py", "report", "--history", "--comments"], ["wiki_collect.py", "report"],
                ["trends_collect.py", "report"], ["rbx_collect.py", "report"], ["observe.py", "report"],
                ["twitch_collect.py", "report"]):
        subprocess.run([PY, str(rc.ROOT / "scripts" / cmd[0]), *cmd[1:]], capture_output=True, text=True)
    gone = rc.prune_exports()
    base = rc.SHARE
    rc.rebuild_dictionary(base)
    newest = {k: v for k, v in newest_exports(base).items() if v["rows"] not in ("0", "")}  # skip empty exports
    since = getattr(a, "since", None) or rc.iso(rc.now().replace(hour=0, minute=0, second=0))
    runs = [r for r in rc.read_rows(rc.DATA / "runs.csv") if r["started_at_utc"] >= since]
    cfg = rc.settings()
    stamp = f"{rc.now():%Y%m%dT%H%MZ}"
    lines = [f"# Slugshot research bundle {stamp}", "",
             f"Collected since {since}. Prepared by Claude Code from the local collectors; for internal analysis in ChatGPT, "
             "not for publishing. Column definitions: DATA_DICTIONARY.md. Missing = blank, never 0.", ""]
    if steps:
        lines += ["## Collection steps", "", "| step | result | detail |", "|---|---|---|"]
        lines += [f"| {n} | {s} | {d.replace('|', '/')} |" for n, s, d in steps]
        lines.append("")
    lines += ["## Runs", "", "| provider | command | status | requests ok | failed | rows |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['provider']} | {r['command']} | {r['status']} | {r['requests_ok']} | {r['requests_failed']} | {r['rows_written']} |"
              for r in runs if r.get("dry_run") != "true"]
    lines += ["", "## Files in this bundle", "", "| file | rows | provenance | delete or refresh by |", "|---|---|---|---|"]
    lines += [f"| {r['file']} | {r['rows']} | {r['provenance']} | {r['expires_at_utc'] or 'no limit'} |" for r in newest.values()]
    lines += ["", "## Caveats", "",
              "- YouTube rows: per-video arithmetic only; delete copies by the date above (30-day rule).",
              "- Language/region columns record exactly what each source says (see DATA_DICTIONARY.md); none is audience geography.",
              "- Charts and trend feeds are selected samples, not a census; selective feeds are not a denominator.",
              ("- Twitch data stays local (share_exports is off)." if not cfg["twitch"]["share_exports"] else "- Twitch: 24 h retention applies to copies."),
              f"- Expired exports deleted during bundling: {len(gone)}."]
    summary = base / "BUNDLE_SUMMARY.md"
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_dir = rc.ROOT / "exports" / "share" / "bundles"
    out_dir.mkdir(parents=True, exist_ok=True)
    zpath = out_dir / f"slugshot_research_{stamp}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("BUNDLE_SUMMARY.md", "DATA_DICTIONARY.md", "MANIFEST.csv"):
            if (base / name).exists():
                z.write(base / name, name)
        for r in newest.values():
            stem = r["file"][:-4]
            for suffix in (".csv", ".json", "_README.md"):
                if (base / (stem + suffix)).exists():
                    z.write(base / (stem + suffix), stem + suffix)
        # Evidence ledgers (+ cards) and analysis outputs travel with the data they cite.
        for p in sorted((rc.DATA / "evidence").glob("*.json")) + sorted((rc.DATA / "evidence").glob("*.md")):
            z.write(p, f"evidence/{p.name}")
        for p in sorted((rc.DATA / "analysis").glob("trend_*.json")):
            z.write(p, f"analysis/{p.name}")
    # Intake QC of the finished bundle, added to it so ChatGPT reads it first.
    r = subprocess.run([PY, str(rc.ROOT / "scripts" / "research_analysis.py"), "intake", str(zpath)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    intake = zpath.with_name(zpath.stem + "_intake")
    if intake.with_suffix(".md").exists():
        with zipfile.ZipFile(zpath, "a", zipfile.ZIP_DEFLATED) as z:
            z.write(intake.with_suffix(".md"), "INTAKE.md")
            z.write(intake.with_suffix(".json"), "INTAKE.json")
    print((r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else "intake: no output")
    print(f"\nBundle -> {zpath} ({len(newest)} datasets, {zpath.stat().st_size // 1024} KB)\nSummary -> {summary}")


def cmd_families(a):
    """Validate config/research/query_families.json and compile it into YouTube saved query sets."""
    path = rc.CONFIG / "query_families.json"
    fams = json.loads(path.read_text(encoding="utf-8"))
    layers_ok = {"core", "alias", "slang", "format_phrase", "need_language", "community_vocabulary", "negative", "adjacent_culture"}
    problems, sets = [], {}
    for f in fams.get("families", []):
        fid, col = f.get("id"), f.get("collection", {})
        if not fid or not f.get("construct"):
            problems.append(f"family without id/construct: {f}")
            continue
        base = {"days": col.get("days", 7), "order": col.get("order", "date"), "duration": col.get("duration", "any"),
                "max": col.get("max", 25)}
        en_qs = {q["q"].lower() for q in f.get("branches", {}).get("en", {}).get("queries", [])}
        for bname, b in f.get("branches", {}).items():
            for q in b.get("queries", []):
                if q.get("layer") not in layers_ok:
                    problems.append(f"{fid}/{bname}: layer '{q.get('layer')}' not in {sorted(layers_ok)}")
                for m in b.get("markets", []):
                    item = {"id": f"{fid}:{bname}:{m}:{q['layer']}", "query": q["q"], "lang": b.get("lang", bname[:2]),
                            "region": m, **base}
                    sets.setdefault(f"fam-{fid}", []).append(item)
                    sets.setdefault(f"fam-{fid}-{bname}", []).append(item)
            if bname.startswith("es") and en_qs and {q["q"].lower() for q in b.get("queries", [])} == en_qs:
                problems.append(f"{fid}/{bname}: identical to the English branch - write native queries, don't copy")
        for nc in f.get("negative_controls", []):
            for m in nc.get("markets", ["US"]):
                sets.setdefault(f"fam-{fid}-negative", []).append({"id": f"{fid}:negative:{m}", "query": nc["q"],
                                                                   "lang": nc.get("lang", "en"), "region": m, **base})
    for p in problems:
        print("WARN", p)
    for name, items in sets.items():
        print(f"{name}: {len(items)} searches (~{len(items)} of the 100 daily search calls)")
    if a.compile:
        qpath = rc.CONFIG / "youtube_queries.json"
        q = json.loads(qpath.read_text(encoding="utf-8"))
        q["sets"] = {k: v for k, v in q["sets"].items() if not k.startswith("fam-")} | sets
        qpath.write_text(json.dumps(q, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"Compiled into {qpath} (run with `ss yt sweep --set <name> --check-shorts`)")


def cmd_runs(a):
    for r in rc.read_rows(rc.DATA / "runs.csv")[-a.n:]:
        print(f"{r['finished_at_utc']}  {r['provider']:13} {r['command']:14} {r['status']:8} ok={r['requests_ok']} "
              f"failed={r['requests_failed']} rows={r['rows_written']}  {r['params_json'][:120]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("--all", action="store_true", help="list empty stores too")
    sub.add_parser("prune")
    r = sub.add_parser("runs")
    r.add_argument("-n", type=int, default=15)
    c = sub.add_parser("collect", help="run a collection profile, then bundle")
    c.add_argument("--profile", choices=["daily", "spanish", "refresh"], default="daily")
    c.add_argument("--yt-set", help="saved YouTube query set to sweep (default: the profile name)")
    b = sub.add_parser("bundle", help="export everything and zip a clean bundle for ChatGPT")
    b.add_argument("--since", help="list runs since this UTC time (default: today 00:00 UTC)")
    f = sub.add_parser("families", help="validate query families; --compile writes YouTube saved sets")
    f.add_argument("--compile", action="store_true")
    a = ap.parse_args()
    {"status": cmd_status, "prune": cmd_prune, "runs": cmd_runs, "collect": cmd_collect, "bundle": cmd_bundle,
     "families": cmd_families}[a.cmd](a)


if __name__ == "__main__":
    main()
