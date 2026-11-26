# Smoke test

Run 2026-11-26T12:14:39+00:00 by `.\ss smoke --research`. Outputs in `out/smoke/`.
WARN in a render check is about the sample footage (a dark 1422x430 preview strip), not the pipeline.
Live research checks make a handful of free calls (Wikimedia, Google Trends RSS, Roblox, TikTok oEmbed; YouTube about 2 units; Twitch 1 point when enabled). BLOCKED = waiting on credentials or an owner decision.

| Check | Result | Detail |
|---|---|---|
| Research collectors offline tests | **PASS** | Ran 27 tests in 17.262s: OK (YouTube, Wikimedia, Trends, observations, Twitch, Roblox on fixtures) |
| Research analysis + evidence ledger tests | **PASS** | Ran 26 tests in 16.362s: OK (evidence-ledger traps, intake, repeat, sensitivity, blind coding, trend, change points) |
| Evidence ledger worked example (real data) | **WARN** | worked example ledger not present (it lives in data/local, not git) |
| Installed scholarly skills (upstream offline tests) | **PASS** | verifying-bibliography: Ran 97 tests in 22.345s OK; surveying-literature: Ran 110 tests in 0.355s OK (skipped=1) |
| Wikimedia pageviews live | **PASS** | 78 points read, 78 stored -> out\smoke\research_live\wiki_collect\wiki_pageviews.csv; request log -> out\smoke\research_live\wiki_collect\wiki_coverage.csv [run wikimedia-20261126T121654Z-edb7] |
| Google Trending Now RSS live | **PASS** | 20 rows -> out\smoke\research_live\trends_collect\trending_now.csv [run google_trends-20261126T121700Z-9063] |
| Roblox experience stats live (legacy API) | **PASS** | 1 snapshots -> out\smoke\research_live\rbx_collect\roblox_experiences.csv [run roblox-20261126T121702Z-4075] |
| TikTok oEmbed live check | **PASS** | oEmbed check confirmed the post ID (Imported 1 values -> out\smoke\research_live\observe\public_observations.csv) |
| YouTube upgraded collector live (chart + Shorts check) | **BLOCKED** | no YOUTUBE_API_KEY in .env |
| Twitch Helix live | **BLOCKED** | BLOCKED: TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET not in .env. Register an app at https://dev.twitch.tv/console (see docs/research-data.md, Twitch). --dry-run works without credentials. |
