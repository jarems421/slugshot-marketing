"""Public YouTube statistics collector (YouTube Data API v3, API key only).

  discover QUERY   search uploads in a date window (search.list: 1 call per page from its own 100-calls/day
                   allowance) + their stats (videos.list: 1 unit per 50 IDs); new IDs join the watchlist
  sweep            run a saved query set from config/research/youtube_queries.json (bilingual, per region)
  chart            a region's most-popular chart, gaming by default (videos.list chart=mostPopular: 1 unit/page)
  creators         every upload in a window from the channels in config/research/youtube_creators.csv, via
                   uploads playlists (1 unit per 50 videos): ordinary videos too, not just hits
  comments         top-level public comments for given videos (commentThreads.list: 1 unit per page)
  stats            re-snapshot IDs (--ids, --ids-file, or the watchlist): 1 unit per 50 IDs
  report           latest snapshot per video + change since the previous snapshot of the SAME video
                   (--history adds every stored snapshot, long format) -> exports/share/research/
  quota            units and search calls used today (quota day = US Pacific) against the budgets
  prune            delete stored rows older than --days (at most 30)

Policy limits (YouTube API Services Developer Policies, checked 2026-11-24; see docs/youtube-api-policy.md):
- Statistics are kept at most 30 days (III.E.4.b): every run prunes older rows, exports carry an expiry.
- Only simple per-video arithmetic is calculated (view increase, views/hour between two snapshots).
  Cross-channel comparisons, rankings, ratios to averages/medians and scores are NOT calculated
  (III.E.4.h and the policy guide's "Acceptable metrics"); they would need YouTube's approval.
- No merging with non-YouTube data inside these files.
- Comments: text, time and like/reply counts only; no author names or channel IDs; 30-day limit.
- No caption or video downloads (captions.download needs edit rights on the video).

Language and region are recorded exactly as sent: `relevance_language_param` only biases ranking (it is
not the content language); `region_param` only means "viewable in that country" (not creator location,
not audience). `default_audio_language` is what the creator declared, often blank.
Shorts: `shorts_status` is confirmed_short only when the video is in the channel's auto-generated Shorts
playlist (UUSH...); duration alone gives `candidate`. That playlist is an undocumented YouTube convention
read through the official API, so treat confirmed_short as strong evidence, not a guarantee.
--dry-run reads tests/fixtures/ (fake IDs) and writes to data/local/research/dryrun/youtube/; no network.
"""
import argparse
import csv
import json
import re
import sys
from datetime import timedelta
from pathlib import Path

import research_common as rc

ROOT = rc.ROOT
API = "https://www.googleapis.com/youtube/v3/"
FIXTURES = ROOT / "tests" / "fixtures"
FIELDS = ["video_id", "url", "title", "channel_id", "channel_title", "published_at", "observed_at_utc",
          "duration_s", "duration_le_180s", "shorts_status", "shorts_evidence", "views", "likes", "comments",
          "category_id", "default_language", "default_audio_language", "live_broadcast_content", "tags",
          "source", "collection", "query", "region_param", "relevance_language_param", "published_after_param",
          "published_before_param", "category_requested", "category_mismatch", "run_id", "expires_at_utc"]
CHANNEL_FIELDS = ["channel_id", "title", "custom_url", "country_declared", "default_language", "published_at",
                  "subscribers", "subscribers_hidden", "video_count", "observed_at_utc", "run_id", "expires_at_utc"]
COMMENT_FIELDS = ["video_id", "comment_id", "published_at", "updated_at", "like_count", "reply_count", "text",
                  "order_param", "observed_at_utc", "run_id", "expires_at_utc"]
QUOTA_FIELDS = ["quota_day_pt", "observed_at_utc", "run_id", "command", "endpoint", "bucket", "units", "ok", "error"]
MAX_STORE_DAYS = 30
REPORT_COLUMNS = [
    # (column, source, meaning) - written to the data dictionary next to each report
    ("video_id", "YouTube", "YouTube video ID"),
    ("url", "YouTube", "watch URL built from the ID"),
    ("title", "YouTube", "title at the latest snapshot"),
    ("channel_id", "YouTube", "channel ID"),
    ("channel_title", "YouTube", "creator/channel name"),
    ("published_at", "YouTube", "upload time, UTC"),
    ("observed_at_utc", "local", "when the latest snapshot was taken"),
    ("duration_s", "YouTube", "length in seconds"),
    ("duration_le_180s", "derived", "true if the upload is 3 minutes or shorter; NOT proof it is a Short"),
    ("shorts_status", "derived", "confirmed_short (in the channel's Shorts playlist) / not_in_shorts_playlist / "
                                 "candidate (3 min or shorter, not checked) / not_short_duration (over 3 min) / blank"),
    ("shorts_evidence", "local", "how shorts_status was decided"),
    ("views", "YouTube", "public view count at the latest snapshot (YouTube counts a Shorts view when playback starts)"),
    ("likes", "YouTube", "public like count; blank when hidden"),
    ("comments", "YouTube", "public comment count; blank when disabled"),
    ("category_id", "YouTube", "YouTube category (20 = Gaming)"),
    ("default_language", "YouTube", "language of title/description as declared by the creator; often blank"),
    ("default_audio_language", "YouTube", "spoken language as declared by the creator; often blank. Not verified"),
    ("first_seen_via", "local", "collection, query, region_param and relevance_language_param of the first snapshot"),
    ("age_hours", "derived", "hours between upload and the latest snapshot"),
    ("category_requested", "local", "category the chart was asked for (charts only)"),
    ("category_mismatch", "derived", "true when YouTube returned a video whose category_id differs from category_requested "
                                     "(kept as returned, not filtered out)"),
    ("stored_rows", "local", "rows stored for this video (one per discovery context: the same moment can appear twice)"),
    ("observations", "local", "distinct observation moments: rows within observation_merge_minutes of each other count once"),
    ("discovery_contexts", "local", "distinct collection/query/region/language combinations that returned this video"),
    ("hours_since_prev", "derived", "hours between the last two distinct observation moments (blank if under min_growth_hours)"),
    ("view_increase_since_prev", "derived", "views at the latest moment minus views at the previous moment"),
    ("views_per_hour_since_prev", "derived", "view_increase_since_prev / hours_since_prev"),
]
HISTORY_COLUMNS = [
    ("video_id", "YouTube", "YouTube video ID"),
    ("channel_title", "YouTube", "creator/channel name"),
    ("published_at", "YouTube", "upload time, UTC"),
    ("observed_at_utc", "local", "when this snapshot was taken"),
    ("views", "YouTube", "public view count at this snapshot"),
    ("likes", "YouTube", "public like count; blank when hidden"),
    ("comments", "YouTube", "public comment count; blank when disabled"),
    ("collection", "local", "discover / chart / creators / stats"),
    ("query", "local", "search text, when the snapshot came from a search"),
    ("region_param", "local", "regionCode sent (viewable-in country), blank if none"),
    ("relevance_language_param", "local", "relevanceLanguage sent (ranking hint only), blank if none"),
    ("category_mismatch", "derived", "true when a chart returned a video outside the requested category"),
    ("observation_moment", "local", "the merged observation time this row belongs to (rows within observation_merge_minutes share one)"),
    ("duplicate_context", "local", "true when another row of the same video has the same observation_moment (same numbers, "
                                   "different discovery context); use one of them for growth"),
    ("run_id", "local", "collection run (see runs.csv)"),
]
POLICY_NOTES = [
    "'YouTube' columns are YouTube's public numbers; 'derived' columns are simple per-video arithmetic.",
    "Views are public counts, not reach, retention, watch time or shares (the API doesn't give those for other people's videos).",
    "Videos differ in age and audience; use this to spot formats and hooks worth testing, not to rank creators. "
    "No cross-channel scores or rankings are included (YouTube policy).",
    "region_param = 'viewable in that country' and relevance_language_param = a ranking hint. Neither says where the "
    "creator or the audience is, or what language the video is in.",
    "Rows older than 30 days are deleted to follow YouTube's storage rules; delete this export by its expiry date.",
]


class Store:
    def __init__(self, dry_run, data_dir=None):
        self.dry_run = dry_run
        self.data_dir = data_dir
        self.dir = Path(data_dir) if data_dir else rc.DATA / ("dryrun" if dry_run else "") / "youtube"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.snapshots = self.dir / "youtube_snapshots.csv"
        self.channels = self.dir / "youtube_channels.csv"
        self.comments = self.dir / "youtube_comments.csv"
        self.watchlist = self.dir / "youtube_watchlist.txt"
        # Google counts every call against one key, so live runs share one quota log even with --data-dir.
        self.quota = self.dir / "quota_log.csv" if dry_run else rc.DATA / "youtube" / "quota_log.csv"
        self.quota.parent.mkdir(parents=True, exist_ok=True)

    def read(self):
        return rc.read_rows(self.snapshots)

    def append(self, rows):
        rc.append_rows(self.snapshots, FIELDS, rows)

    def watch(self, ids):
        known = set(self.watched())
        add = [i for i in dict.fromkeys(ids) if i not in known]
        with self.watchlist.open("a", encoding="utf-8") as f:
            f.writelines(i + "\n" for i in add)
        return len(add)

    def watched(self):
        return [l.strip() for l in self.watchlist.read_text(encoding="utf-8").splitlines() if l.strip()] \
            if self.watchlist.exists() else []

    def used_today(self):
        day = rc.pacific_day(rc.now())
        rows = [r for r in rc.read_rows(self.quota) if r.get("quota_day_pt") == day]
        units = sum(int(r["units"] or 0) for r in rows if r["bucket"] == "default")
        searches = sum(int(r["units"] or 0) for r in rows if r["bucket"] == "search")
        return units, searches


class Api:
    """Every request (successful or not) is logged to quota_log.csv; failures still cost quota."""

    def __init__(self, store, run, dry_run):
        self.store, self.run, self.dry_run = store, run, dry_run

    def get(self, endpoint, params, fixture=None):
        bucket = "search" if endpoint == "search" else "default"
        log = {"quota_day_pt": rc.pacific_day(rc.now()), "observed_at_utc": rc.iso(rc.now()), "run_id": self.run.id,
               "command": self.run.command, "endpoint": endpoint + ".list", "bucket": bucket, "units": 1}
        try:
            if self.dry_run:
                path = FIXTURES / (fixture or f"youtube_{endpoint}.json")
                if not path.exists():
                    path = FIXTURES / "research" / (fixture or f"youtube_{endpoint}.json")
                data = json.loads(path.read_text(encoding="utf-8"))
                if "_error" in data:
                    raise rc.HttpError(data["_error"]["code"], data["_error"]["reason"])
            else:
                body, _ = rc.http(API + endpoint, {**params, "key": api_key()})
                data = json.loads(body)
            self.run.ok += 1
            log.update(ok="true", error="")
            return data
        except rc.HttpError as e:
            self.run.failed += 1
            log.update(ok="false", error=f"{e.status} {e.reason}"[:200])
            raise
        finally:
            self.run.units += 1
            rc.append_rows(self.store.quota, QUOTA_FIELDS, [log])


def api_key():
    key = rc.env_value("YOUTUBE_API_KEY")
    if not key:
        sys.exit("BLOCKED: no YOUTUBE_API_KEY. Copy .env.example to .env and add a key (see README). "
                 "Use --dry-run to test without one.")
    return key


def check_budget(store, units, searches, force=False):
    cfg = rc.settings()["youtube"]
    used_u, used_s = store.used_today()
    over = []
    if used_u + units > cfg["daily_unit_budget"]:
        over.append(f"units {used_u}+{units} > budget {cfg['daily_unit_budget']}")
    if used_s + searches > cfg["daily_search_budget"]:
        over.append(f"search calls {used_s}+{searches} > budget {cfg['daily_search_budget']}")
    print(f"Estimated cost: ~{units} units + {searches} search calls (used today: {used_u} units, {used_s} searches).")
    if over and not force:
        sys.exit("Stopped before any request: " + "; ".join(over) +
                 ". Wait for the Pacific-midnight reset, lower --max/--pages, or raise the budget in config/research/settings.json.")


def seconds(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return None
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def expiry():
    return rc.iso(rc.now() + timedelta(days=MAX_STORE_DAYS))


def video_rows(api, ids, ctx, shorts=None):
    """ctx: collection/query/region/lang/after/before. shorts: {video_id: (status, evidence)} from playlists."""
    rows, observed = [], rc.iso(rc.now())
    ids = list(dict.fromkeys(ids))
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        data = api.get("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(batch), "maxResults": 50})
        rows += [video_row(v, observed, ctx, api, shorts) for v in data.get("items", [])]
    return rows


def video_row(v, observed, ctx, api, shorts=None):
    sn, st = v.get("snippet", {}), v.get("statistics", {})
    dur = seconds(v.get("contentDetails", {}).get("duration"))
    status, evidence = (shorts or {}).get(v["id"], ("", ""))
    if not status:
        if dur is None:
            status, evidence = "", "duration unknown"
        elif dur > 180:
            status, evidence = "not_short_duration", "longer than 3 minutes (Shorts are at most 3 minutes)"
        else:
            status, evidence = "candidate", "3 minutes or shorter; Shorts playlist not checked"
    return {
        "video_id": v["id"],
        "url": f"https://www.youtube.com/watch?v={v['id']}",
        "title": sn.get("title", ""),
        "channel_id": sn.get("channelId", ""),
        "channel_title": sn.get("channelTitle", ""),
        "published_at": sn.get("publishedAt", ""),
        "observed_at_utc": observed,
        "duration_s": "" if dur is None else dur,
        "duration_le_180s": "" if dur is None else str(dur <= 180).lower(),
        "shorts_status": status,
        "shorts_evidence": evidence,
        "views": st.get("viewCount", ""),  # absent when hidden/unavailable: left blank
        "likes": st.get("likeCount", ""),
        "comments": st.get("commentCount", ""),
        "category_id": sn.get("categoryId", ""),
        "category_requested": ctx.get("category", ""),
        "category_mismatch": ("" if not ctx.get("category") or not sn.get("categoryId")
                              else str(sn.get("categoryId") != ctx["category"]).lower()),
        "default_language": sn.get("defaultLanguage", ""),
        "default_audio_language": sn.get("defaultAudioLanguage", ""),
        "live_broadcast_content": sn.get("liveBroadcastContent", ""),
        "tags": "|".join(sn.get("tags", [])[:30]),
        "source": "dry_run_fixture" if api.dry_run else "youtube_data_api_v3:videos.list",
        "collection": ctx.get("collection", ""),
        "query": ctx.get("query", ""),
        "region_param": ctx.get("region", "") or "",
        "relevance_language_param": ctx.get("lang", "") or "",
        "published_after_param": ctx.get("after", "") or "",
        "published_before_param": ctx.get("before", "") or "",
        "run_id": api.run.id,
        "expires_at_utc": expiry(),
    }


def check_shorts(api, rows):
    """For candidates only: is the video in its channel's Shorts playlist? 1 unit per candidate."""
    for r in rows:
        if r["shorts_status"] != "candidate" or not r["channel_id"].startswith("UC"):
            continue
        pl = "UUSH" + r["channel_id"][2:]
        try:
            data = api.get("playlistItems", {"part": "id", "playlistId": pl, "videoId": r["video_id"], "maxResults": 1},
                           fixture="youtube_playlistItems_check.json")
            if data.get("items"):
                r.update(shorts_status="confirmed_short", shorts_evidence="in the channel's Shorts playlist (UUSH)")
            else:
                r.update(shorts_status="not_in_shorts_playlist", shorts_evidence="not in the channel's Shorts playlist (UUSH)")
        except rc.HttpError as e:
            r["shorts_evidence"] = ("channel has no Shorts playlist (404); duration only" if e.status == 404 else
                                    f"Shorts playlist check failed ({e.status}); duration only")


def window(a):
    """Explicit --after/--before (dates or ISO times) win over --days. Returns RFC 3339 strings."""
    after = rc.parse_time(a.after) if getattr(a, "after", None) else rc.now() - timedelta(days=a.days)
    before = rc.parse_time(a.before) if getattr(a, "before", None) else None
    fmt = lambda d: d.isoformat().replace("+00:00", "Z") if d else ""
    return fmt(after), fmt(before)


def search(api, q, ctx, max_results, pages, order, duration):
    params = {"part": "id", "type": "video", "q": q, "maxResults": min(max_results, 50), "order": order,
              "publishedAfter": ctx["after"]}
    if ctx.get("before"):
        params["publishedBefore"] = ctx["before"]
    if ctx.get("region"):
        params["regionCode"] = ctx["region"]
    if ctx.get("lang"):
        params["relevanceLanguage"] = ctx["lang"]
    if duration and duration != "any":
        params["videoDuration"] = duration  # YouTube's filter: short = under 4 minutes, not "is a Short"
    ids, token = [], None
    for _ in range(pages):
        if token:
            params["pageToken"] = token
        data = api.get("search", params)
        ids += [it["id"]["videoId"] for it in data.get("items", []) if it.get("id", {}).get("videoId")]
        token = data.get("nextPageToken")
        if not token or len(ids) >= max_results * pages:
            break
    return ids, params


def collect_search(api, store, q, lang, region, after, before, max_results, pages, order, duration, check, label=""):
    ctx = {"collection": "discover" + (f":{label}" if label else ""), "query": q, "lang": lang, "region": region,
           "after": after, "before": before}
    ids, params = search(api, q, ctx, max_results, pages, order, duration)
    rows = video_rows(api, ids, ctx)
    if check:
        check_shorts(api, rows)
    store.append(rows)
    api.run.rows += len(rows)
    added = store.watch(ids)
    return rows, added, {k: v for k, v in params.items() if k != "part"}


def start(store, command, params, a):
    if not a.dry_run:
        api_key()  # fail early, before any budget use
    run = rc.Run("youtube", command, params, a.dry_run, a.data_dir)
    return Api(store, run, a.dry_run)


def finish(api, msg):
    api.run.finish("ok" if not api.run.failed else "partial")
    print(msg + f" [run {api.run.id}: {api.run.ok} ok / {api.run.failed} failed requests, ~{api.run.units} units]")


def cmd_discover(a, store):
    after, before = window(a)
    searches = a.pages
    check_budget(store, -(-a.max * a.pages // 50) + (a.max * a.pages if a.check_shorts else 0), searches, a.force_budget)
    api = start(store, "discover", vars_of(a), a)
    rows, added, sent = collect_search(api, store, a.query, a.lang, a.region, after, before, a.max, a.pages, a.order,
                                       "short" if a.short_only else a.duration, a.check_shorts)
    finish(api, f"{len(rows)} snapshots -> {store.snapshots} ({added} new on watchlist). Sent: {json.dumps(sent, ensure_ascii=False)}")


def cmd_sweep(a, store):
    cfg = rc.load_json_config("youtube_queries.json")["sets"]
    if a.set not in cfg:
        sys.exit(f"No query set '{a.set}'. Sets: {', '.join(cfg)} (config/research/youtube_queries.json)")
    items = cfg[a.set]
    pages = lambda q: q.get("pages", 1)
    units = sum(-(-q.get("max", 25) * pages(q) // 50) for q in items)
    if a.check_shorts:  # worst case: every result is a <=3-minute candidate needing a 1-unit playlist check
        units += sum(q.get("max", 25) * pages(q) for q in items)
    check_budget(store, units, sum(pages(q) for q in items), a.force_budget)
    api = start(store, f"sweep:{a.set}", {"set": a.set, "items": items}, a)
    total = 0
    for q in items:
        a.days, a.after, a.before = q.get("days", 7), q.get("after"), q.get("before")
        after, before = window(a)
        try:
            rows, added, sent = collect_search(api, store, q["query"], q.get("lang"), q.get("region"), after, before,
                                               q.get("max", 25), pages(q), q.get("order", "date"), q.get("duration", "any"),
                                               a.check_shorts, label=q.get("id", ""))
            total += len(rows)
            print(f"  {q.get('id', q['query'])}: {len(rows)} videos (lang={q.get('lang')}, region={q.get('region')})")
        except rc.HttpError as e:
            print(f"  {q.get('id', q['query'])}: FAILED {e.status} {e.reason}")
    finish(api, f"{total} snapshots from {len(items)} saved queries -> {store.snapshots}")


def cmd_chart(a, store):
    check_budget(store, a.pages, 0, a.force_budget)
    api = start(store, "chart", vars_of(a), a)
    ctx = {"collection": f"chart:mostPopular:cat{a.category}", "query": "", "region": a.region, "lang": "",
           "category": a.category}
    params = {"part": "snippet,statistics,contentDetails", "chart": "mostPopular", "regionCode": a.region,
              "maxResults": min(a.max, 50)}
    if a.category:
        params["videoCategoryId"] = a.category
    rows, token, observed = [], None, rc.iso(rc.now())
    for _ in range(a.pages):
        if token:
            params["pageToken"] = token
        data = api.get("videos", params, fixture="youtube_chart.json")
        rows += [video_row(v, observed, ctx, api) for v in data.get("items", [])]
        token = data.get("nextPageToken")
        if not token:
            break
    if a.check_shorts:
        check_shorts(api, rows)
    store.append(rows)
    api.run.rows = len(rows)
    store.watch([r["video_id"] for r in rows])
    finish(api, f"{len(rows)} chart snapshots (region {a.region}, category {a.category or 'all'}) -> {store.snapshots}")


def creator_ids(a):
    if a.channels:
        return [c.strip() for c in a.channels.split(",") if c.strip()]
    path = Path(a.list) if a.list else rc.CONFIG / "youtube_creators.csv"
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [r["channel_id"].strip() for r in csv.DictReader(f) if r.get("channel_id", "").strip()]


def playlist_ids(api, playlist, after_dt, cap, fixture):
    """Walk a playlist newest-first until uploads are older than the window or `cap` items. Returns IDs, or None
    when the playlist doesn't exist."""
    ids, token = [], None
    while len(ids) < cap:
        params = {"part": "contentDetails", "playlistId": playlist, "maxResults": 50}
        if token:
            params["pageToken"] = token
        try:
            data = api.get("playlistItems", params, fixture=fixture)
        except rc.HttpError as e:
            if e.status == 404:
                return None
            raise
        stop = False
        for it in data.get("items", []):
            cd = it.get("contentDetails", {})
            pub = rc.parse_time(cd.get("videoPublishedAt", ""))
            if pub and pub < after_dt:
                stop = True
                break
            ids.append(cd.get("videoId"))
        token = data.get("nextPageToken")
        if stop or not token:
            break
    return [i for i in ids[:cap] if i]


def cmd_creators(a, store):
    chans = creator_ids(a)
    if not chans:
        sys.exit("No channels: add channel IDs (UC...) to config/research/youtube_creators.csv or pass --channels.")
    pages = -(-a.max_per_channel // 50)
    check_budget(store, -(-len(chans) // 50) + len(chans) * pages * (2 if a.shorts else 1)
                 + -(-len(chans) * a.max_per_channel // 50), 0, a.force_budget)
    api = start(store, "creators", vars_of(a) | {"channels": chans}, a)
    after_s, before_s = window(a)
    after_dt = rc.parse_time(after_s)
    before_dt = rc.parse_time(before_s) if before_s else None
    observed, chan_rows, all_ids, shorts = rc.iso(rc.now()), [], [], {}
    for i in range(0, len(chans), 50):
        data = api.get("channels", {"part": "snippet,contentDetails,statistics", "id": ",".join(chans[i:i + 50])})
        for c in data.get("items", []):
            sn, st = c.get("snippet", {}), c.get("statistics", {})
            chan_rows.append({"channel_id": c["id"], "title": sn.get("title", ""), "custom_url": sn.get("customUrl", ""),
                              "country_declared": sn.get("country", ""), "default_language": sn.get("defaultLanguage", ""),
                              "published_at": sn.get("publishedAt", ""),
                              "subscribers": "" if st.get("hiddenSubscriberCount") else st.get("subscriberCount", ""),
                              "subscribers_hidden": str(bool(st.get("hiddenSubscriberCount"))).lower(),
                              "video_count": st.get("videoCount", ""), "observed_at_utc": observed, "run_id": api.run.id,
                              "expires_at_utc": expiry()})
            uploads = c.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "UU" + c["id"][2:])
            try:
                ids = playlist_ids(api, uploads, after_dt, a.max_per_channel, "youtube_playlistItems_uploads.json") or []
            except rc.HttpError as e:
                print(f"  {c['id']}: uploads playlist failed ({e.status} {e.reason})")
                continue
            all_ids += ids
            if a.shorts and ids:
                try:
                    sh = playlist_ids(api, "UUSH" + c["id"][2:], after_dt, a.max_per_channel, "youtube_playlistItems_shorts.json")
                except rc.HttpError:
                    sh = None
                for vid in ids:
                    if sh is None:
                        continue
                    shorts[vid] = (("confirmed_short", "in the channel's Shorts playlist (UUSH)") if vid in sh else
                                   ("not_in_shorts_playlist", "Shorts playlist read for the same window; video not in it"))
            print(f"  {sn.get('title', c['id'])}: {len(ids)} uploads in window")
    rc.append_rows(store.channels, CHANNEL_FIELDS, chan_rows)
    ctx = {"collection": "creators", "query": "", "after": after_s, "before": before_s}
    rows = video_rows(api, all_ids, ctx, shorts)
    if before_dt:
        rows = [r for r in rows if rc.parse_time(r["published_at"]) and rc.parse_time(r["published_at"]) < before_dt]
    store.append(rows)
    api.run.rows = len(rows)
    store.watch([r["video_id"] for r in rows])
    finish(api, f"{len(rows)} uploads from {len(chan_rows)} channels -> {store.snapshots}; channel facts -> {store.channels}")


def cmd_comments(a, store):
    ids = parse_ids(a, store)
    per = a.max or rc.settings()["youtube"]["comments_per_video"]
    check_budget(store, len(ids) * -(-per // 100), 0, a.force_budget)
    api = start(store, "comments", vars_of(a) | {"ids": ids}, a)
    observed, rows = rc.iso(rc.now()), []
    for vid in ids:
        try:
            data = api.get("commentThreads", {"part": "snippet", "videoId": vid, "maxResults": min(per, 100),
                                              "order": a.order, "textFormat": "plainText"})
        except rc.HttpError as e:
            print(f"  {vid}: no comments collected ({e.status} {e.reason})")  # e.g. comments disabled
            continue
        for t in data.get("items", [])[:per]:
            top = t["snippet"]["topLevelComment"]
            s = top["snippet"]
            # Deliberately no authorDisplayName / authorChannelId: we only need the language people use.
            rows.append({"video_id": vid, "comment_id": top["id"], "published_at": s.get("publishedAt", ""),
                         "updated_at": s.get("updatedAt", ""), "like_count": s.get("likeCount", ""),
                         "reply_count": t["snippet"].get("totalReplyCount", ""), "text": s.get("textDisplay", ""),
                         "order_param": a.order, "observed_at_utc": observed, "run_id": api.run.id, "expires_at_utc": expiry()})
    rc.append_rows(store.comments, COMMENT_FIELDS, rows)
    api.run.rows = len(rows)
    finish(api, f"{len(rows)} comments from {len(ids)} videos -> {store.comments}")


def parse_ids(a, store):
    ids = a.ids.split(",") if a.ids else (
        Path(a.ids_file).read_text(encoding="utf-8").split() if a.ids_file else store.watched())
    ids = [i.strip() for i in ids if i.strip()]
    if not ids:
        sys.exit("No IDs: pass --ids, --ids-file, or run discover first.")
    return list(dict.fromkeys(ids))


def cmd_stats(a, store):
    ids = parse_ids(a, store)
    check_budget(store, -(-len(ids) // 50) + (len(ids) if a.check_shorts else 0), 0, a.force_budget)
    api = start(store, "stats", {"ids": len(ids), "check_shorts": a.check_shorts}, a)
    rows = video_rows(api, ids, {"collection": "stats"})
    if a.check_shorts:
        check_shorts(api, rows)
    store.append(rows)
    api.run.rows = len(rows)
    finish(api, f"{len(rows)}/{len(ids)} snapshots -> {store.snapshots}")
    if len(rows) < len(ids):
        print("Missing IDs are private, deleted or mistyped; nothing was recorded for them.")


def num(x):
    return int(x) if x not in ("", None) else None


def moments(snaps, merge_minutes):
    """Group one video's rows into observation moments: a row within merge_minutes of the moment's first row joins it.
    Returns a list of lists (oldest first). The same numbers seen via two contexts (MX chart, ES chart) are one moment."""
    groups = []
    for s in snaps:
        t_s = rc.parse_time(s["observed_at_utc"])
        if groups and (t_s - rc.parse_time(groups[-1][0]["observed_at_utc"])).total_seconds() <= merge_minutes * 60:
            groups[-1].append(s)
        else:
            groups.append([s])
    return groups


def cmd_report(a, store):
    cfg = rc.settings()["youtube"]
    merge_min, min_gap = cfg.get("observation_merge_minutes", 10), cfg.get("min_growth_hours", 1.0)
    by_video = {}
    for r in store.read():
        by_video.setdefault(r["video_id"], []).append(r)
    out, history, oldest = [], [], None
    for vid, snaps in by_video.items():
        snaps.sort(key=lambda r: r["observed_at_utc"])
        groups = moments(snaps, merge_min)
        last, first = groups[-1][-1], snaps[0]
        t_first = rc.parse_time(first["observed_at_utc"])
        oldest = t_first if oldest is None or t_first < oldest else oldest
        t_last = rc.parse_time(last["observed_at_utc"])
        pub = rc.parse_time(last["published_at"])
        row = {k: last.get(k, "") for k, _, _ in REPORT_COLUMNS}
        known = [s for s in snaps if s.get("shorts_status") in ("confirmed_short", "not_in_shorts_playlist")]
        if known:  # a later plain re-snapshot shouldn't erase an earlier playlist check
            row["shorts_status"], row["shorts_evidence"] = known[-1]["shorts_status"], known[-1]["shorts_evidence"]
        row["category_mismatch"] = "true" if any(s.get("category_mismatch") == "true" for s in snaps) else last.get("category_mismatch", "")
        row["first_seen_via"] = " / ".join(x for x in (first.get("collection", ""), first.get("query", ""),
                                                       first.get("region_param", ""), first.get("relevance_language_param", "")) if x)
        row["age_hours"] = round((t_last - pub).total_seconds() / 3600, 1) if pub else ""
        row["stored_rows"] = len(snaps)
        row["observations"] = len(groups)
        row["discovery_contexts"] = len({(s.get("collection", ""), s.get("query", ""), s.get("region_param", ""),
                                          s.get("relevance_language_param", "")) for s in snaps})
        row.update(hours_since_prev="", view_increase_since_prev="", views_per_hour_since_prev="")
        # Only per-video differences over time, between two distinct observation moments at least min_gap hours
        # apart; rows from the same moment (two contexts) never produce growth. Nothing is compared across videos.
        if len(groups) > 1:
            cur, prev = groups[-1][-1], groups[-2][-1]
            hours = (rc.parse_time(cur["observed_at_utc"]) - rc.parse_time(prev["observed_at_utc"])).total_seconds() / 3600
            if hours >= min_gap and num(cur["views"]) is not None and num(prev["views"]) is not None:
                increase = num(cur["views"]) - num(prev["views"])
                row.update(hours_since_prev=round(hours, 2), view_increase_since_prev=increase,
                           views_per_hour_since_prev=round(increase / hours, 1))
        out.append(row)
        for g in groups:
            for s in g:
                history.append({**s, "observation_moment": g[0]["observed_at_utc"],
                                "duplicate_context": str(len(g) > 1).lower()})
    out.sort(key=lambda r: (r["channel_title"], r["published_at"]))
    expires = (oldest + timedelta(days=MAX_STORE_DAYS)) if oldest else None
    out_dir = store.dir / "reports" if a.data_dir else None
    common = dict(provenance="P1", retention_rule="YouTube API statistics: at most 30 days (Developer Policies III.E.4)",
                  expires_at=expires, share=True, dry_run=a.dry_run, out_dir=out_dir)
    # Sharing public stats with AI tools for internal analysis is approved by the owner (2026-11-24).
    dest = rc.export("youtube", "youtube_report", out, REPORT_COLUMNS, notes=POLICY_NOTES +
                     ["duration_le_180s does not mean the video is a Short; use shorts_status."], **common)
    print(f"{len(out)} videos -> {dest} (+ .json and _README.md data dictionary)")
    if a.history:
        history.sort(key=lambda r: (r["video_id"], r["observed_at_utc"]))
        dest = rc.export("youtube", "youtube_history", history, HISTORY_COLUMNS, notes=POLICY_NOTES +
                         ["One row per stored snapshot (long format). Compare a video only with its own earlier rows."], **common)
        print(f"{len(history)} snapshots -> {dest}")
    if a.comments and not rc.settings().get("sentiment", {}).get("raw_comment_export_to_ai", False):
        print("Comment text is not exported to exports/share: sentiment.raw_comment_export_to_ai is false in "
              "config/research/settings.json. Use `ss sentiment` to code comments locally and export coded summaries.")
    elif a.comments:
        rows = rc.read_rows(store.comments)
        cols = [("video_id", "YouTube", "video the comment is on"), ("comment_id", "YouTube", "comment ID"),
                ("published_at", "YouTube", "when the comment was posted, UTC"),
                ("like_count", "YouTube", "likes on the comment at observation"),
                ("reply_count", "YouTube", "replies at observation"), ("text", "YouTube", "comment text (plain)"),
                ("order_param", "local", "relevance or time ordering requested"),
                ("observed_at_utc", "local", "when it was read")]
        dest = rc.export("youtube", "youtube_comments", rows, cols, notes=POLICY_NOTES + [
            "Public comments with no author names or IDs. Use for wording and language, not for audience demographics."], **common)
        print(f"{len(rows)} comments -> {dest}")


def cmd_quota(a, store):
    cfg = rc.settings()["youtube"]
    u, s = store.used_today()
    print(f"Quota day {rc.pacific_day(rc.now())} (US Pacific): {u}/{cfg['daily_unit_budget']} units budget "
          f"(Google limit 10,000), {s}/{cfg['daily_search_budget']} search calls (Google limit 100).")


def prune(store, days):
    cutoff = rc.now() - timedelta(days=days)
    removed = 0
    for path, fields in ((store.snapshots, FIELDS), (store.channels, CHANNEL_FIELDS), (store.comments, COMMENT_FIELDS)):
        rows = rc.read_rows(path)
        keep = [r for r in rows if rc.parse_time(r["observed_at_utc"]) >= cutoff]
        if len(keep) != len(rows):
            rc.write_rows(path, fields, keep)
        removed += len(rows) - len(keep)
    return removed


def vars_of(a):
    return {k: v for k, v in vars(a).items() if k not in ("cmd", "data_dir", "dry_run", "force_budget") and v not in (None, False)}


def main():
    sys.stdout.reconfigure(errors="replace")  # titles contain emoji the Windows console can't encode
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="use tests/fixtures, write to data/local/research/dryrun")
    ap.add_argument("--data-dir", help=argparse.SUPPRESS)  # smoke test writes elsewhere
    ap.add_argument("--force-budget", action="store_true", help="run even if it would pass the daily budget in settings.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def win(p, days=7):
        p.add_argument("--days", type=int, default=days, help=f"published within the last N days (default {days})")
        p.add_argument("--after", help="published on/after (YYYY-MM-DD or ISO time); overrides --days")
        p.add_argument("--before", help="published before (YYYY-MM-DD or ISO time)")

    d = sub.add_parser("discover", help="search uploads in a date window")
    d.add_argument("query")
    win(d)
    d.add_argument("--lang", help="relevanceLanguage, e.g. en or es (ranking hint, not a filter)")
    d.add_argument("--region", help="regionCode, e.g. GB, MX (viewable in that country)")
    d.add_argument("--max", type=int, default=25, help="results per page (max 50)")
    d.add_argument("--pages", type=int, default=1, help="search pages (1 search call each)")
    d.add_argument("--order", choices=["date", "viewCount", "relevance", "rating"], default="date",
                   help="date (default) keeps ordinary uploads; viewCount only finds winners")
    d.add_argument("--duration", choices=["any", "short", "medium", "long"], default="any")
    d.add_argument("--short-only", action="store_true", help="same as --duration short (YouTube's under-4-minute filter)")
    d.add_argument("--check-shorts", action="store_true", help="confirm Shorts via the channel's Shorts playlist (1 unit per candidate)")
    sw = sub.add_parser("sweep", help="run a saved query set")
    sw.add_argument("--set", default="test")
    sw.add_argument("--check-shorts", action="store_true")
    c = sub.add_parser("chart", help="regional most-popular chart")
    c.add_argument("--region", required=True)
    c.add_argument("--category", default="20", help="video category ID (20 = Gaming; '' = all)")
    c.add_argument("--max", type=int, default=50)
    c.add_argument("--pages", type=int, default=1)
    c.add_argument("--check-shorts", action="store_true")
    cr = sub.add_parser("creators", help="uploads from the channel watchlist")
    cr.add_argument("--list", help="CSV with a channel_id column (default config/research/youtube_creators.csv)")
    cr.add_argument("--channels", help="comma-separated channel IDs instead of the list")
    win(cr, 30)
    cr.add_argument("--max-per-channel", type=int, default=50)
    cr.add_argument("--no-shorts", dest="shorts", action="store_false", help="skip the Shorts-playlist check")
    cm = sub.add_parser("comments", help="top-level public comments")
    cm.add_argument("--ids")
    cm.add_argument("--ids-file")
    cm.add_argument("--max", type=int, help="comments per video (default from settings.json)")
    cm.add_argument("--order", choices=["relevance", "time"], default="relevance")
    s = sub.add_parser("stats", help="re-snapshot known videos")
    s.add_argument("--ids", help="comma-separated video IDs")
    s.add_argument("--ids-file")
    s.add_argument("--check-shorts", action="store_true")
    r = sub.add_parser("report", help="export for ChatGPT")
    r.add_argument("--history", action="store_true", help="also export every stored snapshot (long format)")
    r.add_argument("--comments", action="store_true", help="also export stored comments")
    sub.add_parser("quota", help="today's usage against the budgets")
    p = sub.add_parser("prune")
    p.add_argument("--days", type=int, default=MAX_STORE_DAYS, choices=range(1, MAX_STORE_DAYS + 1),
                   metavar=f"1-{MAX_STORE_DAYS}")
    a = ap.parse_args()

    store = Store(a.dry_run, a.data_dir)
    if a.cmd not in ("prune", "quota", "report"):
        removed = prune(store, MAX_STORE_DAYS)
        if removed:
            print(f"Pruned {removed} rows older than {MAX_STORE_DAYS} days.")
    handlers = {"discover": cmd_discover, "sweep": cmd_sweep, "chart": cmd_chart, "creators": cmd_creators,
                "comments": cmd_comments, "stats": cmd_stats, "report": cmd_report, "quota": cmd_quota,
                "prune": lambda a, s: print(f"Pruned {prune(s, a.days)} rows.")}
    try:
        handlers[a.cmd](a, store)
    except rc.HttpError as e:
        sys.exit(f"YouTube API error: {e.status} {e.reason}")


if __name__ == "__main__":
    main()
