"""Research housekeeping across every collector.

  status    credentials present (yes/no only), gates, stored rows, expired rows, last run per provider,
            today's YouTube quota
  prune     apply every retention rule: YouTube 30 days, Twitch retention_hours, Trends RSS local period,
            and delete expired files in exports/share/research/ (per MANIFEST.csv)
  runs      the last collection runs (parameters actually sent)
"""
import argparse
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
    a = ap.parse_args()
    {"status": cmd_status, "prune": cmd_prune, "runs": cmd_runs}[a.cmd](a)


if __name__ == "__main__":
    main()
