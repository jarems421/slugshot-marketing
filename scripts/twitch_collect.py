"""Twitch Helix collector: clips and live streams for streamer-culture research (app access token only).

  categories QUERY   find a game/category ID (e.g. "Roblox")
  clips              clips created in a window, by --game/--game-id or --broadcaster (paginated, max ~1000/query)
  streams            live streams now for a game, optionally by broadcaster language (en, es)
  watch              clips from every broadcaster in config/research/twitch_broadcasters.csv
  recheck            re-read view counts of stored clips (repeat observations, 100 IDs per request)
  report             export snapshots (LOCAL ONLY until settings.json twitch.share_exports is true)
  prune              delete rows past the retention period

Gates: live calls need TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET in .env AND settings.json
twitch.terms_reviewed = true, set by the owner after reading the Developer Services Agreement's storage
clause. Rows are kept `retention_hours` (default 24, a conservative reading of Twitch staff guidance, not
a confirmed rule). No clip media is downloaded. Clipper names/IDs are not stored.
`language` is the broadcaster's chosen stream language, not the language actually spoken or the audience.
--dry-run reads tests/fixtures/research/twitch_*.json and needs no credentials.
"""
import argparse
import csv
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

import research_common as rc

HELIX = "https://api.twitch.tv/helix/"
TOKEN = "https://id.twitch.tv/oauth2/token"
CLIP_FIELDS = ["clip_id", "url", "broadcaster_id", "broadcaster_name", "video_id", "game_id", "language", "title",
               "view_count", "created_at", "duration_s", "vod_offset", "is_featured", "observed_at_utc", "collection",
               "query", "window_start", "window_end", "run_id", "expires_at_utc"]
STREAM_FIELDS = ["stream_id", "user_id", "user_login", "user_name", "game_id", "game_name", "language", "title",
                 "viewer_count", "started_at", "is_mature", "tags", "observed_at_utc", "query", "run_id", "expires_at_utc"]
CLIP_COLUMNS = [
    ("clip_id", "Twitch", "clip ID"), ("url", "Twitch", "clip URL"),
    ("broadcaster_id", "Twitch", "channel the clip is from"), ("broadcaster_name", "Twitch", "channel display name"),
    ("video_id", "Twitch", "source VOD ID; blank if unavailable"), ("game_id", "Twitch", "category when clipped"),
    ("language", "Twitch", "broadcaster's stream-language setting (ISO 639-1 or 'other'); not verified speech"),
    ("title", "Twitch", "clip title"), ("view_count", "Twitch", "clip views at observation"),
    ("created_at", "Twitch", "when the clip was made, UTC"), ("duration_s", "Twitch", "clip length, seconds"),
    ("vod_offset", "Twitch", "offset in the VOD; blank when unknown"), ("is_featured", "Twitch", "featured by the broadcaster"),
    ("observed_at_utc", "local", "when the count was read"), ("collection", "local", "clips / watch / recheck"),
    ("query", "local", "game ID or broadcaster used"), ("window_start", "local", "started_at sent"),
    ("window_end", "local", "ended_at sent"),
]
STREAM_COLUMNS = [
    ("stream_id", "Twitch", "live stream ID"), ("user_login", "Twitch", "channel login"),
    ("user_name", "Twitch", "channel display name"), ("game_name", "Twitch", "category"),
    ("language", "Twitch", "broadcaster's stream-language setting"), ("title", "Twitch", "stream title"),
    ("viewer_count", "Twitch", "concurrent viewers at observation"), ("started_at", "Twitch", "stream start, UTC"),
    ("tags", "Twitch", "stream tags, | separated"), ("observed_at_utc", "local", "when it was read"),
]


class Twitch:
    def __init__(self, a):
        self.a, self.dry = a, a.dry_run
        cfg = rc.settings()["twitch"]
        self.cfg = cfg
        self.dir = Path(a.data_dir) if a.data_dir else rc.DATA / ("dryrun" if a.dry_run else "") / "twitch"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.clips = self.dir / "twitch_clips.csv"
        self.streams = self.dir / "twitch_streams.csv"
        self.token = None
        self.run = None

    def ready(self):
        if self.dry:
            return
        missing = [n for n in ("TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET") if not rc.env_value(n)]
        if missing:
            sys.exit(f"BLOCKED: {', '.join(missing)} not in .env. Register an app at https://dev.twitch.tv/console "
                     "(see docs/research-data.md, Twitch). --dry-run works without credentials.")
        if not self.cfg.get("terms_reviewed"):
            sys.exit("BLOCKED: live Twitch collection is off until the owner has read the Developer Services Agreement "
                     "storage clause and set twitch.terms_reviewed to true in config/research/settings.json "
                     "(docs/research-data.md, Twitch). --dry-run works meanwhile.")

    def auth(self):
        if self.dry or self.token:
            return
        body, _ = rc.http(TOKEN, data={"client_id": rc.env_value("TWITCH_CLIENT_ID"),
                                       "client_secret": rc.env_value("TWITCH_CLIENT_SECRET"),
                                       "grant_type": "client_credentials"})
        self.token = json.loads(body)["access_token"]  # kept in memory only, never written

    def get(self, endpoint, params, fixture=None):
        if self.dry:
            self.run.ok += 1
            name = fixture or f"twitch_{endpoint.replace('/', '_')}.json"
            if params.get("after"):
                name = name.replace(".json", "_page2.json")
            return json.loads(rc.fixture(name))
        self.auth()
        headers = {"Client-Id": rc.env_value("TWITCH_CLIENT_ID"), "Authorization": f"Bearer {self.token}"}
        for attempt in (1, 2):
            try:
                body, h = rc.http(HELIX + endpoint, params, headers=headers)
                self.run.ok += 1
                self.run.units += 1
                if int(h.get("Ratelimit-Remaining", h.get("ratelimit-remaining", 100)) or 100) < 5:
                    time.sleep(2)
                return json.loads(body)
            except rc.HttpError as e:
                self.run.failed += 1
                self.run.units += 1
                if e.status == 429 and attempt == 1:
                    print("  rate limited; waiting 30 s and retrying once")
                    time.sleep(30)
                    continue
                raise

    def expiry(self):
        return rc.iso(rc.now() + timedelta(hours=self.cfg["retention_hours"]))

    def prune(self):
        return rc.prune_file(self.clips, CLIP_FIELDS) + rc.prune_file(self.streams, STREAM_FIELDS)


def clip_row(c, t, collection, query, ws="", we=""):
    return {"clip_id": c["id"], "url": c.get("url", ""), "broadcaster_id": c.get("broadcaster_id", ""),
            "broadcaster_name": c.get("broadcaster_name", ""), "video_id": c.get("video_id", ""),
            "game_id": c.get("game_id", ""), "language": c.get("language", ""), "title": c.get("title", ""),
            "view_count": c.get("view_count", ""), "created_at": c.get("created_at", ""),
            "duration_s": c.get("duration", ""), "vod_offset": "" if c.get("vod_offset") is None else c["vod_offset"],
            "is_featured": str(c.get("is_featured", "")).lower(), "observed_at_utc": rc.iso(rc.now()),
            "collection": collection, "query": query, "window_start": ws, "window_end": we, "run_id": t.run.id,
            "expires_at_utc": t.expiry()}


def window(a):
    end = rc.parse_time(a.before) if a.before else rc.now()
    start = rc.parse_time(a.after) if a.after else end - timedelta(hours=a.hours)
    if (end - start) > timedelta(days=7):
        print("Note: Twitch's ended_at defaults to one week after started_at; long windows are split per week.")
    return start, end


def fetch_clips(t, key, value, start, end, max_n, featured, collection):
    rows, cursor, s = [], None, start
    while s < end and len(rows) < max_n:
        e = min(end, s + timedelta(days=7))
        params = {key: value, "started_at": rc.iso(s).replace("+00:00", "Z"), "ended_at": rc.iso(e).replace("+00:00", "Z"),
                  "first": 100}
        if featured is not None:
            params["is_featured"] = str(featured).lower()
        while len(rows) < max_n:
            if cursor:
                params["after"] = cursor
            data = t.get("clips", params)
            rows += [clip_row(c, t, collection, f"{key}={value}", params["started_at"], params["ended_at"]) for c in data.get("data", [])]
            cursor = data.get("pagination", {}).get("cursor")
            if not cursor:
                break
        cursor, s = None, e
    return rows[:max_n]


def game_id(t, a):
    if a.game_id:
        return a.game_id
    data = t.get("games", {"name": a.game})
    if not data.get("data"):
        sys.exit(f"No Twitch category named '{a.game}'. Try: ss twitch categories \"{a.game}\"")
    return data["data"][0]["id"]


def langs(a):
    return [l.strip().lower() for l in (a.lang or "").split(",") if l.strip()]


def start_run(t, command, a):
    t.ready()
    t.run = rc.Run("twitch", command, {k: v for k, v in vars(a).items() if k not in ("data_dir", "cmd") and v not in (None, False)},
                   a.dry_run, a.data_dir)
    removed = t.prune()
    if removed:
        print(f"Pruned {removed} rows past {t.cfg['retention_hours']} h retention.")


def store_clips(t, rows, a, label):
    keep = [r for r in rows if not langs(a) or r["language"] in langs(a)]
    rc.append_rows(t.clips, CLIP_FIELDS, keep)
    t.run.rows += len(keep)
    by = {}
    for r in keep:
        by[r["language"] or "?"] = by.get(r["language"] or "?", 0) + 1
    print(f"  {label}: {len(rows)} clips read, {len(keep)} kept" + (f" (languages {', '.join(langs(a))})" if langs(a) else "")
          + (f"; by stream language {by}" if by else ""))


def cmd_categories(a, t):
    start_run(t, "categories", a)
    data = t.get("search/categories", {"query": a.query, "first": 20})
    for c in data.get("data", []):
        print(f"  {c['id']:>12}  {c['name']}")
    t.run.finish()


def cmd_clips(a, t):
    start_run(t, "clips", a)
    s, e = window(a)
    if a.broadcaster:
        users = t.get("users", {"login": a.broadcaster}).get("data", [])
        if not users:
            sys.exit(f"No broadcaster '{a.broadcaster}'.")
        rows = fetch_clips(t, "broadcaster_id", users[0]["id"], s, e, a.max, a.featured, "clips")
        label = a.broadcaster
    else:
        gid = game_id(t, a)
        rows = fetch_clips(t, "game_id", gid, s, e, a.max, a.featured, "clips")
        label = f"game {gid}"
    store_clips(t, rows, a, label)
    t.run.finish("ok" if not t.run.failed else "partial")
    print(f"-> {t.clips} [run {t.run.id}; rows expire after {t.cfg['retention_hours']} h]")


def cmd_streams(a, t):
    start_run(t, "streams", a)
    gid = game_id(t, a)
    params = {"game_id": gid, "first": 100, "type": "live"}
    if langs(a):
        params["language"] = langs(a)  # Helix accepts the parameter repeated
    rows, cursor = [], None
    while len(rows) < a.max:
        if cursor:
            params["after"] = cursor
        data = t.get("streams", params)
        for s in data.get("data", []):
            rows.append({"stream_id": s["id"], "user_id": s.get("user_id", ""), "user_login": s.get("user_login", ""),
                         "user_name": s.get("user_name", ""), "game_id": s.get("game_id", ""), "game_name": s.get("game_name", ""),
                         "language": s.get("language", ""), "title": s.get("title", ""), "viewer_count": s.get("viewer_count", ""),
                         "started_at": s.get("started_at", ""), "is_mature": str(s.get("is_mature", "")).lower(),
                         "tags": "|".join(s.get("tags") or []), "observed_at_utc": rc.iso(rc.now()),
                         "query": f"game_id={gid};language={','.join(langs(a))}", "run_id": t.run.id, "expires_at_utc": t.expiry()})
        cursor = data.get("pagination", {}).get("cursor")
        if not cursor:
            break
    rows = rows[:a.max]
    rc.append_rows(t.streams, STREAM_FIELDS, rows)
    t.run.rows = len(rows)
    t.run.finish("ok" if not t.run.failed else "partial")
    print(f"{len(rows)} live streams (game {gid}) -> {t.streams} [run {t.run.id}]")


def cmd_watch(a, t):
    path = Path(a.list) if a.list else rc.CONFIG / "twitch_broadcasters.csv"
    with path.open(newline="", encoding="utf-8-sig") as f:
        logins = [r["login"].strip().lower() for r in csv.DictReader(f) if r.get("login", "").strip()]
    if not logins:
        sys.exit("No broadcasters: add Twitch logins to config/research/twitch_broadcasters.csv")
    start_run(t, "watch", a)
    s, e = window(a)
    users = []
    for i in range(0, len(logins), 100):
        users += t.get("users", {"login": logins[i:i + 100]}).get("data", [])
    for u in users:
        rows = fetch_clips(t, "broadcaster_id", u["id"], s, e, a.max, a.featured, "watch")
        store_clips(t, rows, a, u.get("login", u["id"]))
    t.run.finish("ok" if not t.run.failed else "partial")


def cmd_recheck(a, t):
    start_run(t, "recheck", a)
    ids = list(dict.fromkeys(r["clip_id"] for r in rc.read_rows(t.clips)))
    if not ids:
        sys.exit("No stored clips to recheck (within the retention period).")
    rows = []
    for i in range(0, len(ids), 100):
        rows += [clip_row(c, t, "recheck", "id") for c in t.get("clips", {"id": ids[i:i + 100]}, fixture="twitch_clips_ids.json").get("data", [])]
    rc.append_rows(t.clips, CLIP_FIELDS, rows)
    t.run.rows = len(rows)
    t.run.finish("ok" if not t.run.failed else "partial")
    print(f"{len(rows)}/{len(ids)} clips re-observed -> {t.clips} (missing = deleted or private)")


def cmd_report(a, t):
    t.prune()
    share = bool(t.cfg.get("share_exports")) and bool(t.cfg.get("terms_reviewed"))
    out = (t.dir / "reports") if a.data_dir else None
    exp = rc.now() + timedelta(hours=t.cfg["retention_hours"])
    notes = ["language is the broadcaster's stream-language setting; it is not the spoken language or audience location.",
             "view_count changes over time; compare a clip only with its own earlier rows.",
             f"Delete this file by its expiry: Twitch rows are kept {t.cfg['retention_hours']} h pending confirmation of the storage terms."]
    rule = f"Twitch: {t.cfg['retention_hours']} h (conservative default pending Developer Services Agreement review)"
    for name, rows, cols in (("twitch_clips", rc.read_rows(t.clips), CLIP_COLUMNS), ("twitch_streams", rc.read_rows(t.streams), STREAM_COLUMNS)):
        dest = rc.export("twitch", name, rows, cols, notes=notes, provenance="P1", retention_rule=rule, expires_at=exp,
                         share=share, dry_run=a.dry_run, out_dir=out)
        print(f"{len(rows)} rows -> {dest}")
    if not share:
        print("Kept local (twitch.share_exports is false or terms not reviewed). Don't upload these yet.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--data-dir", help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("categories")
    c.add_argument("query")

    def win(p):
        p.add_argument("--hours", type=int, default=24, help="clips created in the last N hours (default 24)")
        p.add_argument("--after", help="window start (YYYY-MM-DD or ISO)")
        p.add_argument("--before", help="window end")
        p.add_argument("--max", type=int, default=300, help="max clips per query (Twitch stops near 1000)")
        p.add_argument("--featured", type=lambda s: s.lower() == "true", help="true / false; omit for all")
        p.add_argument("--lang", help="keep only these broadcaster languages, e.g. en,es")

    cl = sub.add_parser("clips")
    g = cl.add_mutually_exclusive_group(required=True)
    g.add_argument("--game", help="category name, e.g. Roblox")
    g.add_argument("--game-id")
    g.add_argument("--broadcaster", help="channel login")
    win(cl)
    st = sub.add_parser("streams")
    g2 = st.add_mutually_exclusive_group(required=True)
    g2.add_argument("--game")
    g2.add_argument("--game-id")
    st.add_argument("--lang", help="broadcaster languages to request, e.g. en,es")
    st.add_argument("--max", type=int, default=100)
    w = sub.add_parser("watch")
    w.add_argument("--list")
    win(w)
    sub.add_parser("recheck")
    sub.add_parser("report")
    sub.add_parser("prune")
    a = ap.parse_args()
    t = Twitch(a)
    handlers = {"categories": cmd_categories, "clips": cmd_clips, "streams": cmd_streams, "watch": cmd_watch,
                "recheck": cmd_recheck, "report": cmd_report, "prune": lambda a, t: print(f"Pruned {t.prune()} rows.")}
    try:
        handlers[a.cmd](a, t)
    except rc.HttpError as e:
        if t.run:
            t.run.finish("failed", f"{e.status} {e.reason}")
        sys.exit(f"Twitch API error: {e.status} {e.reason}")


if __name__ == "__main__":
    main()
