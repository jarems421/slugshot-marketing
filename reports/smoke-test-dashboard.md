# Smoke test

Run 2026-11-26T12:14:01+00:00 by `.\ss smoke --dashboard`. Outputs in `out/smoke/`.
WARN in a render check is about the sample footage (a dark 1422x430 preview strip), not the pipeline.
Live research checks make a handful of free calls (Wikimedia, Google Trends RSS, Roblox, TikTok oEmbed; YouTube about 2 units; Twitch 1 point when enabled). BLOCKED = waiting on credentials or an owner decision.

| Check | Result | Detail |
|---|---|---|
| Dashboard tests | **PASS** | Ran 33 tests in 4.173s: OK (store, metric rules, connectors on fixtures, imports, exports, vault, server security) |
| Knowledge and sentiment tests | **PASS** | Ran 21 tests in 0.462s: OK (schema, links, game truth, expiry, export and policy gates, sentiment pipeline, fixture isolation) |
| Publishing tests (no network) | **PASS** | Ran 27 tests in 16.677s: OK (fixture uploads only: chunking, approval binding, reveal lock, game truth, manual fallback, linking) |
| Analytics tests (owner screens) | **PASS** | Ran 16 tests in 8.950s: OK (combined totals, no double counting, measurement windows, tags, comparisons, learning loop) |
| Knowledge banks validate | **WARN** | no knowledge banks on this machine (data/local/research/knowledge) |
| Dashboard fixture sync (all connectors) | **PASS** | 9 connector runs ok/partial; 1 isolated failures as designed (youtube_analytics/yt-es: no ES fixture) |
| Dashboard server on loopback | **PASS** | 127.0.0.1:47615 answers |
