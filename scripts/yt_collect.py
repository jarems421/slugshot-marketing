"""Public YouTube statistics collector (YouTube Data API v3, API key only).

  discover QUERY   search recent uploads (search.list: 1 call from its own 100-calls/day allowance)
                   + their stats (videos.list: 1 unit per 50 IDs); new IDs join the watchlist
  stats            re-snapshot IDs (--ids, --ids-file, or the watchlist): 1 unit per 50 IDs
  report           latest snapshot per video + change since the previous snapshot of the SAME video
                   -> data/local/reports/ with a data dictionary. INTERNAL ONLY: not exported to
                   external AI services until the policy question is settled
  prune            delete snapshot rows older than --days (at most 30)

Policy limits (YouTube API Services Developer Policies, checked 2026-11-24; see docs/youtube-api-policy.md):
- Statistics are kept at most 30 days (III.E.4.b): every discover/stats run prunes older rows.
- Only simple per-video arithmetic is calculated (view increase, views/hour between two snapshots).
  Cross-channel comparisons, rankings, ratios to averages/medians and scores are NOT calculated
  (III.E.4.h and the policy guide's "Acceptable metrics"); they would need YouTube's approval.
- No merging with non-YouTube data inside these files.

Snapshots append to data/local/youtube_snapshots.csv (git-ignored). Missing values stay blank.
`duration_le_180s` only says the upload is 3 minutes or shorter; it does not mean it is a Short.
The API gives views/likes/comments only: no retention, shares or watch time for other people's videos.
--dry-run reads tests/fixtures/ (fake IDs) and writes to data/local/dryrun/ instead; no network.
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://www.googleapis.com/youtube/v3/"
FIXTURES = ROOT / "tests" / "fixtures"
FIELDS = ["video_id", "url", "title", "channel_id", "channel_title", "published_at", "observed_at_utc",
          "duration_s", "duration_le_180s", "views", "likes", "comments", "source", "query"]
MAX_STORE_DAYS = 30
REPORT_COLUMNS = [
    # (column, source, meaning) - written to the data dictionary next to each report
    ("video_id", "YouTube", "YouTube video ID"),
    ("url", "YouTube", "watch URL built from the ID"),
    ("title", "YouTube", "title at the latest snapshot"),
    ("channel_title", "YouTube", "creator/channel name"),
    ("published_at", "YouTube", "upload time, UTC"),
    ("observed_at_utc", "local", "when the latest snapshot was taken"),
    ("duration_le_180s", "derived", "true if the upload is 3 minutes or shorter; NOT proof it is a Short"),
    ("views", "YouTube", "public view count at the latest snapshot (YouTube counts a view when playback starts, since Aug 2026)"),
    ("likes", "YouTube", "public like count; blank when hidden"),
    ("comments", "YouTube", "public comment count; blank when disabled"),
    ("age_hours", "derived", "hours between upload and the latest snapshot"),
    ("snapshots", "local", "how many snapshots of this video are stored (only the last 30 days are kept)"),
    ("hours_since_prev", "derived", "hours between the last two snapshots of this video"),
    ("view_increase_since_prev", "derived", "views at the latest snapshot minus views at the previous one"),
    ("views_per_hour_since_prev", "derived", "view_increase_since_prev / hours_since_prev"),
]


class Store:
    def __init__(self, dry_run, data_dir=None):
        self.dir = Path(data_dir) if data_dir else ROOT / "data" / "local" / ("dryrun" if dry_run else "")
        self.dir.mkdir(parents=True, exist_ok=True)
        self.snapshots = self.dir / "youtube_snapshots.csv"
        self.watchlist = self.dir / "youtube_watchlist.txt"
        self.quota = self.dir / "quota_log.csv"

    def read(self):
        if not self.snapshots.exists():
            return []
        with self.snapshots.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def append(self, rows):
        new = not self.snapshots.exists()
        with self.snapshots.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, FIELDS)
            if new:
                w.writeheader()
            w.writerows(rows)

    def watch(self, ids):
        known = self.watched()
        add = [i for i in ids if i not in known]
        with self.watchlist.open("a", encoding="utf-8") as f:
            f.writelines(i + "\n" for i in add)
        return len(add)

    def watched(self):
        return [l.strip() for l in self.watchlist.read_text(encoding="utf-8").splitlines() if l.strip()] \
            if self.watchlist.exists() else []

    def log_units(self, command, units):
        new = not self.quota.exists()
        with self.quota.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["date_utc", "command", "estimated_units"])
            w.writerow([now().date().isoformat(), command, units])


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def api_key():
    key = os.environ.get("YOUTUBE_API_KEY", "")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("YOUTUBE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("BLOCKED: no YOUTUBE_API_KEY. Copy .env.example to .env and add a key (see README). "
                 "Use --dry-run to test without one.")
    return key


def call(endpoint, params, dry_run):
    if dry_run:
        return json.loads((FIXTURES / f"youtube_{endpoint}.json").read_text(encoding="utf-8"))
    url = API + endpoint + "?" + urllib.parse.urlencode({**params, "key": api_key()})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:  # report the API's reason, never the URL (it holds the key)
        try:
            err = json.load(e)["error"]
            reason = f"{err.get('code')} {err.get('message')}"
        except Exception:
            reason = str(e.code)
        sys.exit(f"YouTube API error on {endpoint}: {reason}")


def seconds(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return None
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def video_rows(ids, query, dry_run, store, command):
    rows, observed = [], now().isoformat()
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        data = call("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(batch),
                               "maxResults": 50}, dry_run)
        store.log_units(command + ":videos.list", 1)
        for v in data.get("items", []):
            sn, st = v.get("snippet", {}), v.get("statistics", {})
            dur = seconds(v.get("contentDetails", {}).get("duration"))
            rows.append({
                "video_id": v["id"],
                "url": f"https://www.youtube.com/watch?v={v['id']}",
                "title": sn.get("title", ""),
                "channel_id": sn.get("channelId", ""),
                "channel_title": sn.get("channelTitle", ""),
                "published_at": sn.get("publishedAt", ""),
                "observed_at_utc": observed,
                "duration_s": "" if dur is None else dur,
                "duration_le_180s": "" if dur is None else str(dur <= 180).lower(),
                "views": st.get("viewCount", ""),  # absent when hidden/unavailable: left blank
                "likes": st.get("likeCount", ""),
                "comments": st.get("commentCount", ""),
                "source": "dry_run_fixture" if dry_run else "youtube_data_api_v3:videos.list",
                "query": query,
            })
    return rows


def prune(store, days):
    rows = store.read()
    cutoff = now() - timedelta(days=days)
    keep = [r for r in rows if datetime.fromisoformat(r["observed_at_utc"]) >= cutoff]
    if len(keep) != len(rows):
        store.snapshots.unlink()
        store.append(keep)
    return len(rows) - len(keep)


def cmd_discover(a, store):
    params = {"part": "id", "type": "video", "q": a.query, "maxResults": min(a.max, 50), "order": a.order,
              "publishedAfter": (now() - timedelta(days=a.days)).isoformat().replace("+00:00", "Z")}
    if a.region:
        params["regionCode"] = a.region
    if a.short_only:
        params["videoDuration"] = "short"  # YouTube's filter: under 4 minutes, not "is a Short"
    data = call("search", params, a.dry_run)
    store.log_units("discover:search.list (search bucket, 100 calls/day)", 1)
    ids = [it["id"]["videoId"] for it in data.get("items", []) if it.get("id", {}).get("videoId")]
    rows = video_rows(ids, a.query, a.dry_run, store, "discover")
    store.append(rows)
    added = store.watch(ids)
    print(f"{len(rows)} snapshots -> {store.snapshots} ({added} new on watchlist; "
          f"1 search call + {-(-len(ids) // 50)} videos.list unit)")


def cmd_stats(a, store):
    ids = a.ids.split(",") if a.ids else (
        Path(a.ids_file).read_text(encoding="utf-8").split() if a.ids_file else store.watched())
    ids = [i.strip() for i in ids if i.strip()]
    if not ids:
        sys.exit("No IDs: pass --ids, --ids-file, or run discover first.")
    rows = video_rows(ids, "", a.dry_run, store, "stats")
    store.append(rows)
    print(f"{len(rows)}/{len(ids)} snapshots -> {store.snapshots} (~{-(-len(ids) // 50)} units)")
    if len(rows) < len(ids):
        print("Missing IDs are private, deleted or mistyped; nothing was recorded for them.")


def num(x):
    return int(x) if x not in ("", None) else None


def cmd_report(a, store):
    by_video = {}
    for r in store.read():
        by_video.setdefault(r["video_id"], []).append(r)
    out = []
    for vid, snaps in by_video.items():
        snaps.sort(key=lambda r: r["observed_at_utc"])
        last = snaps[-1]
        t_last = datetime.fromisoformat(last["observed_at_utc"])
        age_h = (t_last - datetime.fromisoformat(last["published_at"].replace("Z", "+00:00"))).total_seconds() / 3600
        row = {k: last[k] for k in ("video_id", "url", "title", "channel_title", "published_at",
                                    "observed_at_utc", "duration_le_180s", "views", "likes", "comments")}
        row["age_hours"] = round(age_h, 1)
        row["snapshots"] = len(snaps)
        row.update(hours_since_prev="", view_increase_since_prev="", views_per_hour_since_prev="")
        # Only per-video differences over time; nothing is compared across videos or channels (see docstring).
        if len(snaps) > 1 and num(last["views"]) is not None and num(snaps[-2]["views"]) is not None:
            hours = (t_last - datetime.fromisoformat(snaps[-2]["observed_at_utc"])).total_seconds() / 3600
            if hours > 0:
                increase = num(last["views"]) - num(snaps[-2]["views"])
                row.update(hours_since_prev=round(hours, 2), view_increase_since_prev=increase,
                           views_per_hour_since_prev=round(increase / hours, 1))
        out.append(row)

    stem = ("dryrun_" if a.dry_run else "") + f"youtube_report_{now():%Y%m%d}"
    # Internal only: not written to exports/share/ (the folder for ChatGPT) until it's clear whether
    # YouTube's policies allow sharing API data with external AI services. See docs/youtube-api-policy.md.
    dest = store.dir / "reports" / f"{stem}.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, [c for c, _, _ in REPORT_COLUMNS], extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(out, key=lambda r: (r["channel_title"], r["published_at"])))
    write_dictionary(dest.with_name(f"{stem}_README.md"), dest.name, len(out), a.dry_run)
    print(f"{len(out)} videos -> {dest} (+ _README.md data dictionary)")


def write_dictionary(path, csv_name, count, dry_run):
    lines = [f"# {csv_name}", "",
             ("**FAKE TEST DATA from fixtures. Do not analyse.**\n" if dry_run else ""),
             "**INTERNAL ONLY. Do not upload this file or its contents to ChatGPT, Gemini or other external AI "
             "services until YouTube API permissions for that use are confirmed (docs/youtube-api-policy.md).**\n",
             f"{count} public YouTube videos, one row each, from Slugshot's local collector "
             f"(YouTube Data API v3, public data only). Generated {now().isoformat()}.", "",
             "| column | source | meaning |", "|---|---|---|"]
    lines += [f"| {c} | {s} | {m} |" for c, s, m in REPORT_COLUMNS]
    lines += ["", "How to read it:",
              "- 'YouTube' columns are YouTube's public numbers; 'derived' columns are simple per-video arithmetic.",
              "- Blank means unknown (hidden, disabled or only one snapshot). Never treat blank as 0.",
              "- Views here are public counts, not reach, retention, watch time or shares (the API doesn't give those "
              "for other people's videos).",
              "- Videos differ in age and audience; use this to spot formats and hooks worth testing, not to rank creators.",
              "- duration_le_180s does not mean the video is a Short.",
              "- Rows older than 30 days are deleted to follow YouTube's storage rules, so long histories don't exist."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="use tests/fixtures, write to data/local/dryrun")
    ap.add_argument("--data-dir", help=argparse.SUPPRESS)  # smoke test writes elsewhere
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover")
    d.add_argument("query")
    d.add_argument("--days", type=int, default=7, help="uploaded within the last N days")
    d.add_argument("--max", type=int, default=25)
    d.add_argument("--order", choices=["date", "viewCount", "relevance"], default="viewCount")
    d.add_argument("--region", default="GB")
    d.add_argument("--short-only", action="store_true", help="YouTube's under-4-minute filter")
    s = sub.add_parser("stats")
    s.add_argument("--ids", help="comma-separated video IDs")
    s.add_argument("--ids-file")
    sub.add_parser("report")
    p = sub.add_parser("prune")
    p.add_argument("--days", type=int, default=MAX_STORE_DAYS, choices=range(1, MAX_STORE_DAYS + 1),
                   metavar=f"1-{MAX_STORE_DAYS}")
    a = ap.parse_args()

    store = Store(a.dry_run, a.data_dir)
    if a.cmd in ("discover", "stats"):
        removed = prune(store, MAX_STORE_DAYS)
        if removed:
            print(f"Pruned {removed} snapshot rows older than {MAX_STORE_DAYS} days.")
    {"discover": cmd_discover, "stats": cmd_stats, "report": cmd_report,
     "prune": lambda a, s: print(f"Pruned {prune(s, a.days)} rows.")}[a.cmd](a, store)


if __name__ == "__main__":
    main()
