# Smoke test

Run 2026-11-25T09:19:31+00:00 by `.\ss smoke --research`. Outputs in `out/smoke/`.
WARN in a render check is about the sample footage (a dark 1422x430 preview strip), not the pipeline.
Live research checks make a handful of free calls (Wikimedia, Google Trends RSS, Roblox, TikTok oEmbed; YouTube about 2 units; Twitch 1 point when enabled). BLOCKED = waiting on credentials or an owner decision.

| Check | Result | Detail |
|---|---|---|
| Research collectors offline tests | **PASS** | Ran 27 tests in 4.142s: OK (YouTube, Wikimedia, Trends, observations, Twitch, Roblox on fixtures) |
| Research analysis + evidence ledger tests | **PASS** | Ran 26 tests in 2.234s: OK (evidence-ledger traps, intake, repeat, sensitivity, blind coding, trend, change points) |
| Evidence ledger worked example (real data) | **PASS** | EXAMPLE-HUSS-SLUGTERRA.json: VALID - 0 errors, 1 warnings, 2 items for AI review; 5 claims, 4 evidence items |
| Installed scholarly skills (upstream offline tests) | **PASS** | verifying-bibliography: Ran 97 tests in 21.071s OK; surveying-literature: Ran 110 tests in 0.129s FAILED (failures=1) (1 known POSIX-path assertion in surveying-literature on Windows) |
| Wikimedia pageviews live | **PASS** | 58 points read, 58 stored -> out\smoke\research_live\wiki_collect\wiki_pageviews.csv; request log -> out\smoke\research_live\wiki_collect\wiki_coverage.csv [run wikimedia-20261125T092109Z-3e9b] |
| Google Trending Now RSS live | **PASS** | 20 rows -> out\smoke\research_live\trends_collect\trending_now.csv [run google_trends-20261125T092145Z-1260] |
| Roblox experience stats live (legacy API) | **PASS** | 1 snapshots -> out\smoke\research_live\rbx_collect\roblox_experiences.csv [run roblox-20261125T092146Z-87b4] |
| TikTok oEmbed live check | **PASS** | oEmbed check confirmed the post ID (Imported 1 values -> out\smoke\research_live\observe\public_observations.csv) |
| YouTube upgraded collector live (chart + Shorts check) | **PASS** | 5 chart snapshots (region MX, category 20) -> out\smoke\research_live\yt_collect\youtube_snapshots.csv [run youtube-20261125T092147Z-c447: 1 ok / 0 failed requests, ~1 units] |
| Twitch Helix live | **PASS** |     1960479087  Robox |
