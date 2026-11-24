# Smoke test

Run 2026-11-24T19:16:35+00:00 by `.\ss smoke --research`. Outputs in `out/smoke/`.
WARN in a render check is about the sample footage (a dark 1422x430 preview strip), not the pipeline.
Live research checks make a handful of free calls (Wikimedia, Google Trends RSS, Roblox, TikTok oEmbed; YouTube about 2 units; Twitch 1 point when enabled). BLOCKED = waiting on credentials or an owner decision.

| Check | Result | Detail |
|---|---|---|
| Research collectors offline tests | **PASS** | Ran 27 tests in 10.936s: OK (YouTube, Wikimedia, Trends, observations, Twitch, Roblox on fixtures) |
| Wikimedia pageviews live | **PASS** | 19 points read, 19 stored -> C:\Users\runni\slugshot marketing\out\smoke\research_live\wiki_collect\wiki_pageviews.csv; request log -> C:\Users\runni\slugshot marketing\out\smoke\research_live\wiki_collect\wiki_coverage.csv [run wikimedia-20261124T191649Z-a036] |
| Google Trending Now RSS live | **PASS** | 20 rows -> C:\Users\runni\slugshot marketing\out\smoke\research_live\trends_collect\trending_now.csv [run google_trends-20261124T191651Z-8a29] |
| Roblox experience stats live (legacy API) | **PASS** | 1 snapshots -> C:\Users\runni\slugshot marketing\out\smoke\research_live\rbx_collect\roblox_experiences.csv [run roblox-20261124T191652Z-0e26] |
| TikTok oEmbed live check | **PASS** | oEmbed check confirmed the post ID (Imported 1 values -> C:\Users\runni\slugshot marketing\out\smoke\research_live\observe\public_observations.csv) |
| YouTube upgraded collector live (chart + Shorts check) | **PASS** | 5 chart snapshots (region MX, category 20) -> C:\Users\runni\slugshot marketing\out\smoke\research_live\yt_collect\youtube_snapshots.csv [run youtube-20261124T191653Z-66e4: 1 ok / 0 failed requests, ~1 units] |
| Twitch Helix live | **PASS** |     1960479087  Robox |
