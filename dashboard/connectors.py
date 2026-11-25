"""Platform connectors: our own accounts only, through official, owner-authorised APIs.

Each connector reads one account and writes observations. A connector failure is caught by sync.py and
never stops the others. Fixture mode (tests, `ss dash demo`) replays tests/fixtures/dashboard/*.json and
makes no network calls. No scraping, no credential extraction, nothing that bypasses a login or limit.

| connector          | API                                         | credential                                   |
|--------------------|---------------------------------------------|----------------------------------------------|
| youtube_analytics  | YouTube Analytics API v2 + Data API v3      | OAuth (Desktop client), per channel           |
| instagram          | Instagram API with Instagram Login (Graph)  | long-lived user token (Meta app dashboard)    |
| tiktok             | TikTok Display API v2                       | OAuth (Login Kit), per account                |
| buffer             | Buffer GraphQL API (TikTok, Instagram)      | personal API key (BUFFER_API_KEY)             |
| roblox_analytics   | Roblox Open Cloud Analytics Query API       | API key with universe.analytics:read          |
| roblox_public      | Roblox legacy public games API              | none (universe ID only)                       |
"""
import json
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import research_common as rc  # noqa: E402

from . import vault  # noqa: E402
from .store import ROOT, now_iso, settings  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "dashboard"
RETRY_STATUS = {0, 429, 500, 502, 503, 504}


class NeedsAuth(Exception):
    """Credentials missing, expired or revoked: the owner has to (re)connect."""


class Ctx:
    """Per-run HTTP helper: retries with backoff, counts requests, replays fixtures in fixture mode."""

    def __init__(self, fixture=False, sleep=time.sleep, tries=4):
        self.fixture, self.sleep, self.tries = fixture, sleep, tries
        self.variant = ""
        self.ok = self.failed = 0
        self.calls = {}
        self.last_headers = {}

    def call(self, key, url, params=None, headers=None, data=None, json_body=None):
        if self.fixture:
            n = self.calls.get(key, 0)
            self.calls[key] = n + 1
            # Lookup order: per-language variant (key@es), numbered sequence (key.0), key, then key minus its last _part.
            parts = key.split("_")
            names = ([f"{key}@{self.variant}"] if self.variant else []) + [f"{key}.{n}"] + \
                ["_".join(parts[:i]) for i in range(len(parts), 1, -1)]
            if self.variant and self.variant != "en":
                names = names[:1]  # other-language accounts only use their own fixtures
            path = next((FIXTURES / f"{x}.json" for x in names if (FIXTURES / f"{x}.json").exists()), None)
            if path is None:
                self.failed += 1
                raise rc.HttpError(404, f"no fixture {key}")
            body = json.loads(fixture_text(path.read_text(encoding="utf-8")))
            if isinstance(body, dict) and "_http_error" in body:
                self.failed += 1
                raise rc.HttpError(body["_http_error"], body.get("message", "fixture error"))
            self.ok += 1
            return body
        h = dict(headers or {})
        if json_body is not None:
            data = json.dumps(json_body).encode()
            h["Content-Type"] = "application/json"
        delay = 2
        for attempt in range(self.tries):
            try:
                raw, self.last_headers = rc.http(url, params, h, data, timeout=40, user_agent="SlugshotDashboard/1.0 (owner's own accounts)")
                self.ok += 1
                return json.loads(raw or b"{}")
            except rc.HttpError as e:
                self.failed += 1
                if e.status in (401, 403):
                    raise
                if e.status not in RETRY_STATUS or attempt == self.tries - 1:
                    raise
                self.sleep(delay)
                delay *= 2


def fixture_text(text):
    """Fixtures carry relative dates so they stay current: {{D-3}} a date, {{DT-3}} an ISO time, {{TS-3}} a Unix time."""
    import re
    today = datetime.now(timezone.utc).date()

    def sub(m):
        d = today - timedelta(days=int(m.group(2)))
        at = datetime(d.year, d.month, d.day, 15, tzinfo=timezone.utc)
        return {"D": d.isoformat(), "DT": at.isoformat().replace("+00:00", "Z"), "TS": str(int(at.timestamp()))}[m.group(1)]
    return re.sub(r"\{\{(DT|D|TS)-(\d+)\}\}", sub, text)


def _day(d):
    return d.isoformat() if isinstance(d, date) else str(d)[:10]


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _obs(platform, account, entity_type, entity_id, metric, value, period_type, start, end, source, run_id, **kw):
    return {"platform": platform, "account_id": account["account_id"], "entity_type": entity_type, "entity_id": entity_id,
            "metric": metric, "value": value, "period_type": period_type, "period_start": start, "period_end": end,
            "observed_at_utc": kw.pop("observed", now_iso()), "source": source, "run_id": run_id, **kw}


def same_handle(a, b):
    return (a or "").strip().lstrip("@").lower() == (b or "").strip().lstrip("@").lower()


def backfill_start(store, connector, account, default_days):
    """Incremental window: re-read the last 3 days (late data), or backfill on the first run."""
    last = store.q("""SELECT MAX(period_start) d FROM observations WHERE source=? AND account_id=? AND period_type='day'""",
                   (connector, account["account_id"]))[0]["d"]
    today = datetime.now(timezone.utc).date()
    if last:
        return max(date.fromisoformat(last) - timedelta(days=3), today - timedelta(days=default_days))
    return today - timedelta(days=default_days)


class Connector:
    name = ""
    platform = ""
    label = ""
    route = ""          # how the owner connects: oauth / token / key / none
    capabilities = {}   # metric id -> 'api' | 'manual' | 'unavailable'

    def credential_state(self, account):
        """'ready', or a short reason it isn't."""
        return "ready"

    def sync(self, store, account, ctx, run_id):
        raise NotImplementedError


# ---------------------------------------------------------------- YouTube
class YouTubeAnalytics(Connector):
    name, platform, label, route = "youtube_analytics", "youtube", "YouTube Analytics API", "oauth"
    scopes = ["https://www.googleapis.com/auth/yt-analytics.readonly", "https://www.googleapis.com/auth/youtube.readonly"]
    capabilities = {"views": "api", "watch_time_minutes": "api", "avg_view_duration_s": "api", "avg_view_pct": "api",
                    "likes": "api", "comments": "api", "shares": "api", "followers": "api", "followers_gained": "api",
                    "followers_lost": "api", "impressions": "manual", "link_taps": "manual"}
    DAILY = {"views": "views", "estimatedMinutesWatched": "watch_time_minutes", "averageViewDuration": "avg_view_duration_s",
             "averageViewPercentage": "avg_view_pct", "subscribersGained": "followers_gained",
             "subscribersLost": "followers_lost", "likes": "likes", "comments": "comments", "shares": "shares"}

    def credential_state(self, account):
        if not (vault.secret("YOUTUBE_OAUTH_CLIENT_ID") and vault.secret("YOUTUBE_OAUTH_CLIENT_SECRET")):
            return "needs OAuth client"
        return "ready" if vault.has(f"oauth_youtube_{account['account_id']}") else "not connected"

    def token(self, account, ctx):
        if ctx.fixture:
            return "FIXTURE"
        key = f"oauth_youtube_{account['account_id']}"
        t = vault.get(key)
        if not t:
            raise NeedsAuth("not connected")
        if t.get("expires_at", 0) > time.time() + 60:
            return t["access_token"]
        try:
            r = ctx.call("", "https://oauth2.googleapis.com/token", data={
                "client_id": vault.secret("YOUTUBE_OAUTH_CLIENT_ID"), "client_secret": vault.secret("YOUTUBE_OAUTH_CLIENT_SECRET"),
                "refresh_token": t["refresh_token"], "grant_type": "refresh_token"})
        except rc.HttpError as e:
            raise NeedsAuth(f"token refresh failed ({e.status}); reconnect") from None
        t.update(access_token=r["access_token"], expires_at=time.time() + int(r.get("expires_in", 3600)))
        vault.put(key, t)
        return t["access_token"]

    def sync(self, store, account, ctx, run_id):
        h = {"Authorization": f"Bearer {self.token(account, ctx)}"}
        rows, src = [], self.name
        ch = ctx.call("yt_channels", "https://www.googleapis.com/youtube/v3/channels",
                      {"part": "snippet,statistics,contentDetails", "mine": "true"}, h)
        items = ch.get("items") or []
        if not items:
            raise NeedsAuth("no channel on this Google account")
        c = items[0]
        if account.get("external_id") and account["external_id"] != c["id"]:
            raise NeedsAuth(f"connected channel {c['id']} is not {account['external_id']}; reconnect with the right channel")
        got = c["snippet"].get("customUrl", "")
        if not account.get("external_id") and account.get("handle") and got and not same_handle(got, account["handle"]):
            raise NeedsAuth(f"connected channel is {got}, not @{account['handle'].lstrip('@')}; reconnect with the right channel")
        if not account.get("external_id"):
            store.x("UPDATE accounts SET external_id=?, handle=? WHERE account_id=?",
                    (c["id"], c["snippet"].get("customUrl", ""), account["account_id"]))
        stats = c.get("statistics", {})
        today = datetime.now(timezone.utc).date()
        if not stats.get("hiddenSubscriberCount"):
            rows.append(_obs("youtube", account, "account", account["account_id"], "followers",
                             _num(stats.get("subscriberCount")), "point", _day(today), _day(today), src, run_id,
                             note="YouTube rounds public subscriber counts"))
        # Register uploads (most recent 100).
        uploads_pl = c.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        vids, token_ = [], None
        for page in range(2):
            if not uploads_pl:
                break
            pl = ctx.call(f"yt_playlist{'_' + str(page) if page else ''}", "https://www.googleapis.com/youtube/v3/playlistItems",
                          {"part": "snippet,contentDetails", "playlistId": uploads_pl, "maxResults": 50,
                           **({"pageToken": token_} if token_ else {})}, h)
            for it in pl.get("items", []):
                vid = it["contentDetails"]["videoId"]
                vids.append(vid)
                store.save_upload({"platform": "youtube", "platform_video_id": vid, "account_id": account["account_id"],
                                   "url": f"https://www.youtube.com/shorts/{vid}", "title": it["snippet"].get("title", ""),
                                   "published_at_utc": it["contentDetails"].get("videoPublishedAt") or it["snippet"].get("publishedAt", ""),
                                   "source": src})
            token_ = pl.get("nextPageToken")
            if not token_:
                break
        start = backfill_start(store, src, account, (today - date.fromisoformat(
            settings()["connectors"]["youtube_analytics"]["history_start"])).days)
        rep = ctx.call("yt_daily", "https://youtubeanalytics.googleapis.com/v2/reports",
                       {"ids": "channel==MINE", "startDate": _day(start), "endDate": _day(today), "dimensions": "day",
                        "metrics": ",".join(self.DAILY)}, h)
        cols = [c_["name"] for c_ in rep.get("columnHeaders", [])]
        for r in rep.get("rows", []) or []:
            rec = dict(zip(cols, r))
            for api_m, m in self.DAILY.items():
                if api_m in rec:
                    rows.append(_obs("youtube", account, "account", account["account_id"], m, _num(rec[api_m]),
                                     "day", rec["day"], rec["day"], src, run_id))
        hist = settings()["connectors"]["youtube_analytics"]["history_start"]
        per = ctx.call("yt_videos", "https://youtubeanalytics.googleapis.com/v2/reports",
                       {"ids": "channel==MINE", "startDate": hist, "endDate": _day(today), "dimensions": "video",
                        "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained",
                        "sort": "-views", "maxResults": 200}, h)
        cols = [c_["name"] for c_ in per.get("columnHeaders", [])]
        for r in per.get("rows", []) or []:
            rec = dict(zip(cols, r))
            uid = store.save_upload({"platform": "youtube", "platform_video_id": rec["video"], "account_id": account["account_id"],
                                     "url": f"https://www.youtube.com/shorts/{rec['video']}", "source": src})
            for api_m, m in {**self.DAILY, "views": "views"}.items():
                if api_m in rec and api_m not in ("subscribersLost",):
                    rows.append(_obs("youtube", account, "upload", uid, m, _num(rec[api_m]), "lifetime", hist, _day(today),
                                     src, run_id))
        return store.put_obs(rows)


# ---------------------------------------------------------------- Instagram
class Instagram(Connector):
    name, platform, label, route = "instagram", "instagram", "Instagram API with Instagram Login", "token"
    capabilities = {"views": "api", "reach": "api", "likes": "api", "comments": "api", "shares": "api", "saves": "api",
                    "watch_time_minutes": "api", "avg_view_duration_s": "api", "followers": "api",
                    "followers_gained": "api", "followers_lost": "api", "link_taps": "api", "profile_visits": "manual"}
    MEDIA = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions"]
    REELS = ["ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]
    MAP = {"views": ("views", 1), "reach": ("reach", 1), "likes": ("likes", 1), "comments": ("comments", 1),
           "shares": ("shares", 1), "saved": ("saves", 1), "ig_reels_avg_watch_time": ("avg_view_duration_s", 1 / 1000),
           "ig_reels_video_view_total_time": ("watch_time_minutes", 1 / 60000)}

    def base(self):
        return f"https://graph.instagram.com/{settings()['connectors']['instagram']['api_version']}"

    def credential_state(self, account):
        return "ready" if vault.has(f"token_instagram_{account['account_id']}") else "not connected"

    def token(self, account, ctx):
        if ctx.fixture:
            return "FIXTURE"
        key = f"token_instagram_{account['account_id']}"
        t = vault.get(key)
        if not t:
            raise NeedsAuth("no token")
        if time.time() - t.get("refreshed_at", 0) > 86400:  # long-lived tokens refresh after 24 h, for 60 more days
            try:
                r = ctx.call("", "https://graph.instagram.com/refresh_access_token",
                             {"grant_type": "ig_refresh_token", "access_token": t["access_token"]})
                t.update(access_token=r["access_token"], refreshed_at=time.time(),
                         expires_at=time.time() + int(r.get("expires_in", 5184000)))
                vault.put(key, t)
            except rc.HttpError as e:
                if t.get("expires_at", 0) < time.time():
                    raise NeedsAuth(f"token expired ({e.status}); paste a new one") from None
        return t["access_token"]

    def insights(self, ctx, key, url, metrics, params):
        """Ask for all metrics at once; if Instagram rejects one, ask one by one and mark the rejects unavailable."""
        try:
            d = ctx.call(key, url, {**params, "metric": ",".join(metrics)})
            return {m["name"]: m for m in d.get("data", [])}, []
        except rc.HttpError as e:
            if e.status != 400:
                raise
        got, missing = {}, []
        for m in metrics:
            try:
                d = ctx.call(f"{key}_{m}", url, {**params, "metric": m})
                got.update({x["name"]: x for x in d.get("data", [])})
            except rc.HttpError as e:
                if e.status != 400:
                    raise
                missing.append(m)
        return got, missing

    @staticmethod
    def value(m):
        if "total_value" in m:
            return _num(m["total_value"].get("value"))
        vals = m.get("values") or []
        return _num(vals[-1].get("value")) if vals else None

    def sync(self, store, account, ctx, run_id):
        tok = self.token(account, ctx)
        b, rows, src = self.base(), [], self.name
        today = datetime.now(timezone.utc).date()
        me = ctx.call("ig_me", f"{b}/me", {"fields": "user_id,username,followers_count,media_count", "access_token": tok})
        if not account.get("external_id"):
            store.x("UPDATE accounts SET external_id=?, handle=? WHERE account_id=?",
                    (str(me.get("user_id", "")), me.get("username", ""), account["account_id"]))
        rows.append(_obs("instagram", account, "account", account["account_id"], "followers",
                         _num(me.get("followers_count")), "point", _day(today), _day(today), src, run_id))
        media, after = [], None
        for page in range(3):
            d = ctx.call(f"ig_media{'_' + str(page) if page else ''}", f"{b}/me/media",
                         {"fields": "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count",
                          "limit": 50, "access_token": tok, **({"after": after} if after else {})})
            media += d.get("data", [])
            after = (d.get("paging") or {}).get("cursors", {}).get("after") if (d.get("paging") or {}).get("next") else None
            if not after:
                break
        for m in media:
            if m.get("media_type") != "VIDEO" and m.get("media_product_type") != "REELS":
                continue
            uid = store.save_upload({"platform": "instagram", "platform_video_id": m["id"], "account_id": account["account_id"],
                                     "url": m.get("permalink", ""), "title": (m.get("caption") or "")[:120],
                                     "published_at_utc": m.get("timestamp", ""), "source": src})
            wanted = self.MEDIA + (self.REELS if m.get("media_product_type") == "REELS" else [])
            got, missing = self.insights(ctx, f"ig_insights_{m['id']}", f"{b}/{m['id']}/insights", wanted, {"access_token": tok})
            for api_m, (metric, scale) in self.MAP.items():
                if api_m in got:
                    v = self.value(got[api_m])
                    rows.append(_obs("instagram", account, "upload", uid, metric, None if v is None else round(v * scale, 3),
                                     "lifetime", "", _day(today), src, run_id))
                elif api_m in missing:
                    rows.append(_obs("instagram", account, "upload", uid, metric, None, "lifetime", "", _day(today), src,
                                     run_id, status="unavailable", note="Instagram rejected this metric for this media"))
        # Account totals for each complete day missing from the last 7.
        start = backfill_start(store, src, account, 7)
        d = start
        while d < today:
            since = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
            got, _ = self.insights(ctx, f"ig_account_{_day(d)}", f"{b}/me/insights",
                                   ["views", "reach", "profile_links_taps", "follows_and_unfollows"],
                                   {"period": "day", "metric_type": "total_value", "since": since, "until": since + 86400,
                                    "access_token": tok})
            for api_m, metric in (("views", "views"), ("reach", "reach"), ("profile_links_taps", "link_taps")):
                if api_m in got:
                    rows.append(_obs("instagram", account, "account", account["account_id"], metric,
                                     self.value(got[api_m]), "day", _day(d), _day(d), src, run_id))
            fu = got.get("follows_and_unfollows")
            for br in ((fu or {}).get("total_value", {}).get("breakdowns") or [{}])[0].get("results", []):
                kind = (br.get("dimension_values") or [""])[0]
                metric = {"FOLLOWER": "followers_gained", "NON_FOLLOWER": "followers_lost"}.get(kind)
                if metric:
                    rows.append(_obs("instagram", account, "account", account["account_id"], metric, _num(br.get("value")),
                                     "day", _day(d), _day(d), src, run_id))
            d += timedelta(days=1)
        return store.put_obs(rows)


# ---------------------------------------------------------------- TikTok
class TikTok(Connector):
    name, platform, label, route = "tiktok", "tiktok", "TikTok Display API", "oauth"
    scopes = ["user.info.basic", "user.info.stats", "video.list"]
    # user/info fields by the scope that unlocks them. Asking for one field without its scope fails the whole call (401).
    FIELDS = {"user.info.basic": "open_id,display_name", "user.info.stats": "follower_count,following_count,likes_count,video_count",
              "user.info.profile": "username"}
    capabilities = {"views": "api", "likes": "api", "comments": "api", "shares": "api", "followers": "api",
                    "avg_view_duration_s": "manual", "completion_rate": "manual", "watch_time_minutes": "unavailable",
                    "saves": "manual", "profile_visits": "manual", "followers_gained": "manual"}

    def credential_state(self, account):
        if not (vault.secret("TIKTOK_CLIENT_KEY") and vault.secret("TIKTOK_CLIENT_SECRET")):
            return "needs developer app"
        return "ready" if vault.has(f"oauth_tiktok_{account['account_id']}") else "not connected"

    def token(self, account, ctx):
        if ctx.fixture:
            return "FIXTURE"
        key = f"oauth_tiktok_{account['account_id']}"
        t = vault.get(key)
        if not t:
            raise NeedsAuth("not connected")
        if t.get("expires_at", 0) > time.time() + 60:
            return t["access_token"]
        try:
            r = ctx.call("", "https://open.tiktokapis.com/v2/oauth/token/", data={
                "client_key": vault.secret("TIKTOK_CLIENT_KEY"), "client_secret": vault.secret("TIKTOK_CLIENT_SECRET"),
                "grant_type": "refresh_token", "refresh_token": t["refresh_token"]})
        except rc.HttpError as e:
            raise NeedsAuth(f"token refresh failed ({e.status}); reconnect") from None
        t.update(access_token=r["access_token"], refresh_token=r.get("refresh_token", t["refresh_token"]),
                 expires_at=time.time() + int(r.get("expires_in", 86400)))
        if r.get("refresh_expires_in"):
            t["refresh_expires_at"] = time.time() + int(r["refresh_expires_in"])
        vault.put(key, t)
        return t["access_token"]

    def granted(self, account, ctx):
        if ctx.fixture:
            return set(self.scopes) | {"video.publish"}
        return set(((vault.get(f"oauth_tiktok_{account['account_id']}") or {}).get("scope") or "").split(","))

    def username(self, user, granted, ctx, h):
        """The account's @username: user.info.profile if granted, else creator_info (video.publish), else ''."""
        if user.get("username"):
            return user["username"]
        if "video.publish" in granted:
            try:
                r = ctx.call("tt_creator", "https://open.tiktokapis.com/v2/post/publish/creator_info/query/", None, h, json_body={})
                return (r.get("data") or {}).get("creator_username", "")
            except rc.HttpError:
                return ""
        return ""

    def sync(self, store, account, ctx, run_id):
        h = {"Authorization": f"Bearer {self.token(account, ctx)}"}
        rows, src = [], self.name
        today = _day(datetime.now(timezone.utc).date())
        granted = self.granted(account, ctx)
        fields = ",".join(f for s, f in self.FIELDS.items() if s in granted)
        u = ctx.call("tt_user", "https://open.tiktokapis.com/v2/user/info/", {"fields": fields}, h)
        user = (u.get("data") or {}).get("user") or {}
        if account.get("external_id") and user.get("open_id") and user["open_id"] != account["external_id"]:
            raise NeedsAuth("this token belongs to a different TikTok account; reconnect with the right one")
        if not account.get("external_id") and user.get("open_id"):
            name = self.username(user, granted, ctx, h)
            if name and account.get("handle") and not same_handle(name, account["handle"]):
                raise NeedsAuth(f"connected TikTok account is @{name}, not @{account['handle'].lstrip('@')}; reconnect with the right one")
            store.x("UPDATE accounts SET external_id=?, handle=? WHERE account_id=?",
                    (user["open_id"], name or account.get("handle", ""), account["account_id"]))
        rows.append(_obs("tiktok", account, "account", account["account_id"], "followers", _num(user.get("follower_count")),
                         "point", today, today, src, run_id))
        cursor = None
        for page in range(5):
            body = {"max_count": 20, **({"cursor": cursor} if cursor else {})}
            d = ctx.call(f"tt_videos{'_' + str(page) if page else ''}", "https://open.tiktokapis.com/v2/video/list/?" +
                         urllib.parse.urlencode({"fields": "id,title,create_time,share_url,duration,view_count,like_count,comment_count,share_count"}),
                         None, h, json_body=body)
            data = d.get("data") or {}
            for v in data.get("videos", []):
                uid = store.save_upload({"platform": "tiktok", "platform_video_id": v["id"], "account_id": account["account_id"],
                                         "url": v.get("share_url", ""), "title": v.get("title", ""), "duration_s": v.get("duration"),
                                         "published_at_utc": datetime.fromtimestamp(int(v["create_time"]), timezone.utc).isoformat() if v.get("create_time") else "",
                                         "source": src})
                for api_m, m in (("view_count", "views"), ("like_count", "likes"), ("comment_count", "comments"), ("share_count", "shares")):
                    rows.append(_obs("tiktok", account, "upload", uid, m, _num(v.get(api_m)), "lifetime", "", today, src, run_id))
            cursor = data.get("cursor")
            if not data.get("has_more"):
                break
        return store.put_obs(rows)


# ---------------------------------------------------------------- Buffer
BUFFER = "https://api.buffer.com"


BUFFER_SYNC_RESERVE = 150  # analytics stop below this many requests left in Buffer's 30-day window; posting keeps 10


def buffer_quota(store, headers):
    """Record Buffer's rate-limit headers (x-ratelimit-*) for the Settings page and the reserve checks."""
    h = {k.lower(): v for k, v in (headers or {}).items()}
    if store is not None and "x-ratelimit-remaining" in h:
        store.set_pref("buffer_quota", {"limit": int(h.get("x-ratelimit-limit") or 0), "remaining": int(h["x-ratelimit-remaining"]),
                                        "reset_unix": int(h.get("x-ratelimit-reset") or 0), "at": now_iso()})


def buffer_gql(ctx, key, query, variables=None, token=None, store=None):
    """One GraphQL call. GraphQL errors arrive as HTTP 200 with `errors`; they're raised as HttpError(400)."""
    tok = "FIXTURE" if ctx.fixture else (token or vault.secret("BUFFER_API_KEY"))
    if not tok:
        raise NeedsAuth("add BUFFER_API_KEY")
    try:
        r = ctx.call(key, BUFFER, None, {"Authorization": f"Bearer {tok}"}, json_body={"query": query, "variables": variables or {}})
    except rc.HttpError as e:
        if e.status in (401, 403):
            raise NeedsAuth(f"Buffer refused the API key ({e.status}); make a new one in Buffer → Settings → API") from None
        raise
    buffer_quota(store, ctx.last_headers)
    if r.get("errors"):
        raise rc.HttpError(400, "; ".join(x.get("message", "") for x in r["errors"])[:200])
    return r.get("data") or {}


class Buffer(Connector):
    """Buffer's GraphQL API (personal key, free plan) for our TikTok and Instagram channels.

    Reads per-post metrics of posts Buffer sent; Buffer returns nothing for posts made elsewhere. To avoid
    counting a video twice, it only writes metrics no other connector provides for that account (TikTok:
    reach and watch time; Instagram: everything, unless the Instagram API connector is connected). A post
    whose metrics Buffer hasn't computed yet (metricsUpdatedAt null) writes nothing: Buffer reports 0 there.
    Live-checked 2026-11-25: 3,000 requests per 30 days on Free (1,000 per channel), insights limited to 31 days.
    Requests per sync: one per account, plus two the first time (organization and channel lookup, cached in prefs).
    """
    name, platform, label, route = "buffer", "", "Buffer API", "key"
    platforms = ("tiktok", "instagram")
    capabilities = {"reach": "api", "watch_time_minutes": "api", "avg_view_duration_s": "api"}  # what it adds beyond the native APIs
    MAP = {"views": ("views", 1), "reach": ("reach", 1), "reactions": ("likes", 1), "comments": ("comments", 1),
           "shares": ("shares", 1), "saves": ("saves", 1), "totalTimeWatched": ("watch_time_minutes", 1),
           "averageTimeWatched": ("avg_view_duration_s", 1)}
    ONLY = {"tiktok": {"reach", "watch_time_minutes", "avg_view_duration_s"}}  # the TikTok Display API has the rest
    POSTS = """query($o: OrganizationId!, $c: [ChannelId!], $after: String) { posts(first: 50, after: $after,
      input: {organizationId: $o, filter: {channelIds: $c, status: [sent]}}) { edges { node { id externalLink sentAt text
      metricsUpdatedAt metrics { type value unit } } } pageInfo { hasNextPage endCursor } } }"""

    def credential_state(self, account):
        return "ready" if vault.secret("BUFFER_API_KEY") else "needs API key"

    def channel(self, store, account, ctx, fresh=False):
        """(organization_id, channel) for this account, checked against its platform and handle."""
        key = f"buffer_channel_{account['account_id']}"
        cached = None if fresh else store.pref(key)
        if cached:
            return cached["organization_id"], cached
        orgs = buffer_gql(ctx, "buffer_account", "query { account { organizations { id } } }", store=store).get("account", {}).get("organizations") or []
        for o in orgs:
            chans = buffer_gql(ctx, "buffer_channels", """query($o: OrganizationId!) { channels(input: {organizationId: $o}) {
                id name service isLocked isDisconnected } }""", {"o": o["id"]}, store=store).get("channels") or []
            for ch in chans:
                if ch["service"] == account["platform"] and same_handle(ch["name"], account.get("handle")):
                    if ch.get("isDisconnected") or ch.get("isLocked"):
                        raise NeedsAuth(f"Buffer channel @{ch['name']} is disconnected or locked; reconnect it in Buffer")
                    c = {"organization_id": o["id"], "id": ch["id"], "name": ch["name"], "service": ch["service"]}
                    store.set_pref(key, c)
                    return o["id"], c
        raise NeedsAuth(f"no Buffer channel for {account['platform']} @{(account.get('handle') or '').lstrip('@')}")

    def sync(self, store, account, ctx, run_id):
        q = store.pref("buffer_quota") or {}
        if not ctx.fixture and q.get("remaining") is not None and q["remaining"] < BUFFER_SYNC_RESERVE:
            return 0, f"skipped: {q['remaining']} Buffer requests left this window; kept for posting"
        org, ch = self.channel(store, account, ctx)
        native = CONNECTORS.get(account["platform"])
        allowed = self.ONLY.get(account["platform"])
        if account["platform"] == "instagram" and native and native.credential_state(account) == "ready":
            allowed = set()  # the Instagram API connector already writes these
        rows, after, today = [], None, _day(datetime.now(timezone.utc).date())
        from .publish import VIDEO_ID
        import re
        for page in range(4):
            d = buffer_gql(ctx, f"buffer_posts{'_' + str(page) if page else ''}", self.POSTS,
                           {"o": org, "c": [ch["id"]], "after": after}, store=store).get("posts") or {}
            for e in d.get("edges", []):
                p = e["node"]
                vid = next((m.group(1) for rx in VIDEO_ID[account["platform"]] for m in [re.search(rx, p.get("externalLink") or "")] if m), None)
                if not vid or not p.get("metricsUpdatedAt"):
                    continue  # no platform link to join on, or Buffer hasn't computed metrics yet (it would say 0)
                known = store.q("SELECT 1 FROM uploads WHERE platform=? AND platform_video_id=?", (account["platform"], vid))
                uid = store.save_upload({"platform": account["platform"], "platform_video_id": vid, "account_id": account["account_id"],
                                         "url": "" if known else p["externalLink"], "title": "" if known else (p.get("text") or "")[:120],
                                         "published_at_utc": "" if known else p.get("sentAt") or "", "source": self.name})  # never overwrite the native record
                for m in p.get("metrics") or []:
                    metric, scale = self.MAP.get(m.get("type"), (None, 1))
                    if not metric or (allowed is not None and metric not in allowed):
                        continue
                    v = _num(m.get("value"))
                    rows.append(_obs(account["platform"], account, "upload", uid, metric, None if v is None else v * scale,
                                     "lifetime", "", today, self.name, run_id, observed=p["metricsUpdatedAt"],
                                     note="via Buffer; Buffer marks its metrics API experimental"))
            pi = d.get("pageInfo") or {}
            after = pi.get("endCursor") if pi.get("hasNextPage") else None
            if not after:
                break
        return store.put_obs(rows)


# ---------------------------------------------------------------- Roblox
class RobloxAnalytics(Connector):
    name, platform, label, route = "roblox_analytics", "roblox", "Roblox Analytics Query API", "key"
    capabilities = {"dau": "api", "new_users": "api", "d1_retention": "api", "d7_retention": "api", "d30_retention": "api",
                    "avg_session_min": "api", "visits": "api", "revenue_robux": "api", "paying_users": "api",
                    "payer_cvr": "api", "unique_play_users": "api", "link_visits": "manual", "onboarding_step_users": "needs game events"}
    QUERIES = [("DailyActiveUsers", "dau", None), ("DailyActiveUsers", "dau", "IsNewUser"),
               ("ForwardD1Retention", "d1_retention", None), ("ForwardD7Retention", "d7_retention", None),
               ("ForwardD30Retention", "d30_retention", None), ("AverageSessionLengthMinutes", "avg_session_min", None),
               ("Visits", "visits", None), ("DailyRevenue", "revenue_robux", None), ("PayingUsers", "paying_users", None),
               ("PayingUsersCVR", "payer_cvr", None), ("UniqueUsersWithPlaySessions", "unique_play_users", "AcquisitionSource")]
    BASE = "https://apis.roblox.com/analytics-query-api"
    NEW_VALUES = {"true", "new", "1", "newuser", "new_user"}

    def credential_state(self, account):
        if not account.get("external_id"):
            return "needs universe ID"
        return "ready" if vault.secret("ROBLOX_ANALYTICS_API_KEY") else "needs API key"

    def query(self, ctx, key, uid, body, h):
        r = ctx.call(key, f"{self.BASE}/v1/universes/{uid}/metrics", None, h, json_body=body)
        polls = 0
        while not r.get("done", True):
            polls += 1
            if polls > 20:
                raise rc.HttpError(504, "analytics query still running after 20 polls")
            ctx.sleep(min(2 * polls, 10)) if not ctx.fixture else None
            r = ctx.call(key, f"{self.BASE}/{r['path']}", None, h)
        if r.get("error"):
            raise rc.HttpError(400, f"{r['error'].get('code')}: {r['error'].get('message', '')}")
        return (r.get("response") or {}).get("values", [])

    def sync(self, store, account, ctx, run_id):
        uid = account.get("external_id")
        if not uid:
            raise NeedsAuth("set the universe ID in Settings")
        h = {"x-api-key": "FIXTURE" if ctx.fixture else vault.secret("ROBLOX_ANALYTICS_API_KEY")}
        today = datetime.now(timezone.utc).date()
        start = backfill_start(store, self.name, account, settings()["connectors"]["roblox_analytics"]["backfill_days"])
        rows, errors = [], []
        for api_m, metric, breakdown in self.QUERIES:
            body = {"metric": api_m, "granularity": "OneDay", "startTime": f"{_day(start)}T00:00:00Z",
                    "endTime": f"{_day(today)}T00:00:00Z", **({"breakdown": [breakdown]} if breakdown else {})}
            try:
                series = self.query(ctx, f"rbx_{api_m}{'_' + breakdown if breakdown else ''}", uid, body, h)
            except rc.HttpError as e:
                if e.status in (401, 403):
                    raise NeedsAuth(f"Roblox refused the key ({e.status}): check universe.analytics:read for this universe") from None
                errors.append(f"{api_m}: {e.status}")
                continue
            for s in series:
                bd = (s.get("breakdowns") or [{}])[0] if s.get("breakdowns") else {}
                for p in s.get("dataPoints", []):
                    day = p["time"][:10]
                    note = {"Projected": "projected by Roblox", "NotStatisticallySignificant": "not statistically significant"}.get(p.get("status", ""), "")
                    rows.append(_obs("roblox", account, "experience", uid, metric, _num(p.get("value")), "day", day, day,
                                     self.name, run_id, breakdown_dim=bd.get("dimension", ""),
                                     breakdown_value=bd.get("displayValue") or bd.get("value", ""), note=note))
                    if breakdown == "IsNewUser" and str(bd.get("value", "")).lower() in self.NEW_VALUES:
                        rows.append(_obs("roblox", account, "experience", uid, "new_users", _num(p.get("value")), "day", day,
                                         day, self.name, run_id, note=note))
        n = store.put_obs(rows)
        if errors and not rows:
            raise rc.HttpError(500, "; ".join(errors))
        return (n, "; ".join(errors)) if errors else n


class RobloxPublic(Connector):
    name, platform, label, route = "roblox_public", "roblox", "Roblox public games API (legacy)", "none"
    capabilities = {"visits": "api", "playing": "api", "favorites": "api"}

    def credential_state(self, account):
        return "ready" if account.get("external_id") else "needs universe ID"

    def sync(self, store, account, ctx, run_id):
        uid = account.get("external_id")
        if not uid:
            raise NeedsAuth("set the universe ID in Settings")
        d = ctx.call("rbx_games", "https://games.roblox.com/v1/games", {"universeIds": uid})
        today = _day(datetime.now(timezone.utc).date())
        rows = []
        for g in d.get("data", []):
            for api_m, m in (("visits", "visits"), ("playing", "playing"), ("favoritedCount", "favorites")):
                rows.append(_obs("roblox", account, "experience", uid, m, _num(g.get(api_m)), "point", today, today,
                                 self.name, run_id, provenance="P1", note="legacy public API; may change"))
        return store.put_obs(rows)


CONNECTORS = {c.name: c for c in (YouTubeAnalytics(), Instagram(), TikTok(), Buffer(), RobloxAnalytics(), RobloxPublic())}
BY_PLATFORM = {"youtube": ["youtube_analytics"], "instagram": ["instagram", "buffer"], "tiktok": ["tiktok", "buffer"],
               "roblox": ["roblox_analytics", "roblox_public"]}
