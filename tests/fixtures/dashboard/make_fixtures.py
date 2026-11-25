"""Writes the dashboard connector fixtures (fake, deterministic, clearly labelled FIXTURE).

Shapes follow each provider's documented response format. Dates are relative placeholders ({{D-n}}) that the
fixture loader fills in at read time. Run: .venv\\Scripts\\python tests\\fixtures\\dashboard\\make_fixtures.py
"""
import json
import math
from pathlib import Path

D = Path(__file__).resolve().parent
DAYS = 28


def w(name, obj):
    (D / f"{name}.json").write_text(json.dumps(obj, indent=1), encoding="utf-8")


def wave(i, base, amp, phase=0.0):
    return round(base + amp * math.sin(i / 4 + phase) + i * base * 0.02)


# YouTube Data API + Analytics API
w("yt_channels", {"items": [{"id": "UCFIXTURE000000000000001", "snippet": {"title": "FIXTURE channel", "customUrl": "@fixture"},
                             "statistics": {"subscriberCount": "1240", "hiddenSubscriberCount": False},
                             "contentDetails": {"relatedPlaylists": {"uploads": "UUFIXTURE000000000000001"}}}]})
vids = [("FXyt0000001", "FIXTURE Floppy underdog duel", 3), ("FXyt0000002", "FIXTURE One slug for life (rule world)", 9),
        ("FXyt0000003", "FIXTURE Noob vs pro slug picks", 16)]
w("yt_playlist", {"items": [{"contentDetails": {"videoId": v, "videoPublishedAt": f"{{{{DT-{age}}}}}"}, "snippet": {"title": t}}
                            for v, t, age in vids]})
w("yt_daily", {"columnHeaders": [{"name": n} for n in ["day", "views", "estimatedMinutesWatched", "averageViewDuration",
                                                      "averageViewPercentage", "subscribersGained", "subscribersLost", "likes", "comments", "shares"]],
               "rows": [[f"{{{{D-{d}}}}}", wave(DAYS - d, 900, 300), wave(DAYS - d, 260, 80), 17, 71.5, wave(DAYS - d, 12, 5), 2,
                         wave(DAYS - d, 60, 20), 6, 9] for d in range(DAYS, 1, -1)]})
w("yt_videos", {"columnHeaders": [{"name": n} for n in ["video", "views", "estimatedMinutesWatched", "averageViewDuration",
                                                       "averageViewPercentage", "likes", "comments", "shares", "subscribersGained"]],
                "rows": [["FXyt0000001", 8400, 2380, 17, 82.4, 610, 44, 71, 96], ["FXyt0000002", 12100, 3120, 15, 68.0, 830, 75, 112, 140],
                         ["FXyt0000003", 3900, 1010, 16, 61.2, 240, 19, 22, 31]]})

# Instagram API with Instagram Login
w("ig_me", {"user_id": "17841400000000001", "username": "fixture_ig", "followers_count": 512, "media_count": 3})
w("ig_media", {"data": [
    {"id": "IGFX1", "caption": "FIXTURE reel: Floppy underdog", "media_type": "VIDEO", "media_product_type": "REELS",
     "permalink": "https://www.instagram.com/reel/FIXTURE1/", "timestamp": "{{DT-4}}"},
    {"id": "IGFX2", "caption": "FIXTURE reel: rule world", "media_type": "VIDEO", "media_product_type": "REELS",
     "permalink": "https://www.instagram.com/reel/FIXTURE2/", "timestamp": "{{DT-10}}"},
    {"id": "IGFX3", "caption": "FIXTURE reel: metric rejected", "media_type": "VIDEO", "media_product_type": "REELS",
     "permalink": "https://www.instagram.com/reel/FIXTURE3/", "timestamp": "{{DT-15}}"},
    {"id": "IGFX4", "caption": "FIXTURE photo (ignored)", "media_type": "IMAGE", "media_product_type": "FEED",
     "permalink": "https://www.instagram.com/p/FIXTURE4/", "timestamp": "{{DT-20}}"}], "paging": {"cursors": {"after": "x"}}})


def ig_ins(vals):
    return {"data": [{"name": k, "period": "lifetime", "values": [{"value": v}]} for k, v in vals.items()]}


w("ig_insights_IGFX1", ig_ins({"views": 5300, "reach": 4100, "likes": 380, "comments": 21, "shares": 40, "saved": 33,
                               "total_interactions": 474, "ig_reels_avg_watch_time": 9800, "ig_reels_video_view_total_time": 51940000}))
w("ig_insights_IGFX2", ig_ins({"views": 7600, "reach": 6200, "likes": 510, "comments": 37, "shares": 64, "saved": 48,
                               "total_interactions": 659, "ig_reels_avg_watch_time": 8700, "ig_reels_video_view_total_time": 66120000}))
w("ig_insights_IGFX3", {"_http_error": 400, "message": "FIXTURE: (#100) metric not supported for this media"})
w("ig_insights_IGFX3_views", ig_ins({"views": 1900}))
w("ig_insights_IGFX3_likes", ig_ins({"likes": 120}))
w("ig_account", {"data": [{"name": "views", "total_value": {"value": 410}}, {"name": "reach", "total_value": {"value": 300}},
                          {"name": "profile_links_taps", "total_value": {"value": 6}},
                          {"name": "follows_and_unfollows", "total_value": {"breakdowns": [{"dimension_keys": ["follow_type"],
                           "results": [{"dimension_values": ["FOLLOWER"], "value": 9}, {"dimension_values": ["NON_FOLLOWER"], "value": 2}]}]}}]})

# TikTok Display API
w("tt_user", {"data": {"user": {"open_id": "FIXTURE-open-id", "display_name": "FIXTURE", "username": "fixture_tt",
                                "follower_count": 2310, "following_count": 4, "likes_count": 18000, "video_count": 3}},
              "error": {"code": "ok", "message": ""}})
w("tt_videos", {"data": {"videos": [
    {"id": "7400000000000000001", "title": "FIXTURE Floppy underdog", "create_time": "{{TS-2}}", "share_url": "https://www.tiktok.com/@fixture_tt/video/7400000000000000001",
     "duration": 15, "view_count": 22400, "like_count": 1900, "comment_count": 88, "share_count": 140},
    {"id": "7400000000000000002", "title": "FIXTURE rule world", "create_time": "{{TS-8}}", "share_url": "https://www.tiktok.com/@fixture_tt/video/7400000000000000002",
     "duration": 16, "view_count": 41000, "like_count": 3300, "comment_count": 150, "share_count": 410}],
    "cursor": 0, "has_more": False}, "error": {"code": "ok", "message": ""}})

w("tt_user@es", {"data": {"user": {"open_id": "FIXTURE-open-id-es", "display_name": "FIXTURE ES", "username": "fixture_tt_es",
                                   "follower_count": 1480, "following_count": 2, "likes_count": 9100, "video_count": 1}},
                 "error": {"code": "ok", "message": ""}})
w("tt_videos@es", {"data": {"videos": [
    {"id": "7400000000000000101", "title": "FIXTURE ES: una babosa para toda la vida", "create_time": "{{TS-6}}",
     "share_url": "https://www.tiktok.com/@fixture_tt_es/video/7400000000000000101", "duration": 16, "view_count": 18300,
     "like_count": 1500, "comment_count": 97, "share_count": 120}], "cursor": 0, "has_more": False}, "error": {"code": "ok", "message": ""}})

# Roblox Analytics Query API (DailyActiveUsers first answers 202 / done:false, then the poll completes)


def series(base, amp, frac=False, start=DAYS, end=1):
    pts = []
    for d in range(start, end, -1):
        i = DAYS - d
        v = round(max(0.05, min(0.6, base + amp * math.sin(i / 3))), 3) if frac else max(0, wave(i, base, amp))
        pts.append({"time": f"{{{{D-{d}}}}}T00:00:00Z", "value": v, "status": "Valid"})
    return pts


def done(values):
    return {"path": "v1/universes/9990001/operations/metrics/FIXTURE", "done": True,
            "metadata": {"createdTime": "{{DT-0}}"}, "response": {"values": values}}


w("rbx_DailyActiveUsers.0", {"path": "v1/universes/9990001/operations/metrics/FIXTUREPOLL", "done": False})
w("rbx_DailyActiveUsers.1", done([{"breakdowns": [], "dataPoints": series(420, 120)}]))
w("rbx_DailyActiveUsers_IsNewUser", done([
    {"breakdowns": [{"dimension": "IsNewUser", "value": "true"}], "dataPoints": series(150, 60)},
    {"breakdowns": [{"dimension": "IsNewUser", "value": "false"}], "dataPoints": series(270, 70)}]))
w("rbx_ForwardD1Retention", done([{"breakdowns": [], "dataPoints": series(0.22, 0.05, True, DAYS, 2)}]))
w("rbx_ForwardD7Retention", done([{"breakdowns": [], "dataPoints": series(0.08, 0.02, True, DAYS, 8)}]))
w("rbx_ForwardD30Retention", {"_http_error": 400, "message": "FIXTURE: 2001 cohort too young"})
w("rbx_AverageSessionLengthMinutes", done([{"breakdowns": [], "dataPoints": series(11, 3)}]))
w("rbx_Visits", done([{"breakdowns": [], "dataPoints": series(640, 160)}]))
w("rbx_DailyRevenue", done([{"breakdowns": [], "dataPoints": series(900, 400)}]))
w("rbx_PayingUsers", done([{"breakdowns": [], "dataPoints": series(14, 6)}]))
w("rbx_PayingUsersCVR", done([{"breakdowns": [], "dataPoints": series(0.033, 0.01, True)}]))
w("rbx_UniqueUsersWithPlaySessions_AcquisitionSource", done([
    {"breakdowns": [{"dimension": "AcquisitionSource", "value": s}], "dataPoints": series(b, a)}
    for s, b, a in (("Home Recommendations", 180, 50), ("Search", 60, 20), ("Share Links", 40, 15), ("Friend Activity", 30, 10))]))
w("rbx_games", {"data": [{"id": 9990001, "name": "FIXTURE Slugshot", "playing": 37, "visits": 18450, "favoritedCount": 912}]})
print("fixtures written to", D)
