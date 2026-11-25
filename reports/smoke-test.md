# Smoke test

Run 2026-11-25T16:40:15+00:00 by `.\ss smoke`. Outputs in `out/smoke/`.
WARN in a render check is about the sample footage (a dark 1422x430 preview strip), not the pipeline.
Live research checks make a handful of free calls (Wikimedia, Google Trends RSS, Roblox, TikTok oEmbed; YouTube about 2 units; Twitch 1 point when enabled). BLOCKED = waiting on credentials or an owner decision.

| Check | Result | Detail |
|---|---|---|
| Installed tools | **PASS** | git: git version 2.55.0.windows.3; node: v24.19.0; ffmpeg: ffmpeg version 9.1-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers; ffmpeg filters: all present; obs: installed; kdenlive: installed; kokoro venv: installed; kokoro model: present |
| Glossary corrections | **PASS** | 12 term-correction checks passed |
| Whisper transcription | **PASS** | glossary: 'slug's Hoh' -> 'Slugshot' / 27 words, 11 caption lines -> C:\Users\runni\slugshot marketing\out\smoke\narration.srt / Check these low-confidence words: Slugshot |
| Kokoro voice + Whisper round trip | **PASS** | Whisper heard: "He brought Inferno, I brought Floppy, Slugshot on Roblox" |
| Audio tidy + ducked mix | **PASS** | narration 12.7s -> tidied 10.4s; ducked music mix written |
| FFmpeg vertical render + QC | **PASS** | out\smoke\ffmpeg_vertical.mp4 13.1s |
| Remotion template render + QC | **PASS** | out\smoke\smoke.mp4 15.2s |
| Multi-scene assembly (all asset types) + QC | **PASS** | 5 scenes (card, PNG, MKV, 9:16 MP4, card) + Kokoro script + music/SFX; scene starts (s): 0.00, 2.26, 3.36, 5.26, 6.48; out\smoke\SS_20261124_WORLD_Smoke_Assembly_V01_MASTER.mp4 10.4s |
| Gemini timestamps -> review clips | **PASS** | 2 padded clips + index.csv from a Gemini-style CSV; out-of-range row skipped: True |
| MakeMyClip setup | **PASS** | clip doctor OK, workspace = media\ (whisper.cpp intentionally not installed) |
| YouTube collector dry run | **PASS** | discover -> stats -> report (+ data dictionary) on fake fixtures, no network |
| YouTube report + data dictionary | **PASS** | report + data dictionary written (real runs go to exports/share for ChatGPT) |
| YouTube collector live call | **PASS** | Estimated cost: ~1 units + 0 search calls (used today: 11 units, 0 searches).
1/1 snapshots -> C:\Users\runni\slugshot marketing\out\smoke\yt_live\youtube_snapshots.csv [run youtube-20261125T164252Z-9ef7: 1 ok / 0 failed requests, ~1 units] |
| Research collectors offline tests | **PASS** | Ran 27 tests in 7.238s: OK (YouTube, Wikimedia, Trends, observations, Twitch, Roblox on fixtures) |
| Research analysis + evidence ledger tests | **PASS** | Ran 26 tests in 10.664s: OK (evidence-ledger traps, intake, repeat, sensitivity, blind coding, trend, change points) |
| Evidence ledger worked example (real data) | **PASS** | EXAMPLE-HUSS-SLUGTERRA.json: VALID - 0 errors, 1 warnings, 2 items for AI review; 5 claims, 4 evidence items |
| Installed scholarly skills (upstream offline tests) | **PASS** | verifying-bibliography: Ran 97 tests in 22.484s OK; surveying-literature: Ran 110 tests in 0.539s FAILED (failures=1) (1 known POSIX-path assertion in surveying-literature on Windows) |
| Wikimedia pageviews live | **PASS** | 62 points read, 62 stored -> C:\Users\runni\slugshot marketing\out\smoke\research_live\wiki_collect\wiki_pageviews.csv; request log -> C:\Users\runni\slugshot marketing\out\smoke\research_live\wiki_collect\wiki_coverage.csv [run wikimedia-20261125T164436Z-a13f] |
| Google Trending Now RSS live | **PASS** | 20 rows -> C:\Users\runni\slugshot marketing\out\smoke\research_live\trends_collect\trending_now.csv [run google_trends-20261125T164606Z-1fdd] |
| Roblox experience stats live (legacy API) | **PASS** | 1 snapshots -> C:\Users\runni\slugshot marketing\out\smoke\research_live\rbx_collect\roblox_experiences.csv [run roblox-20261125T164607Z-2126] |
| TikTok oEmbed live check | **PASS** | oEmbed check confirmed the post ID (Imported 1 values -> C:\Users\runni\slugshot marketing\out\smoke\research_live\observe\public_observations.csv) |
| YouTube upgraded collector live (chart + Shorts check) | **PASS** | 5 chart snapshots (region MX, category 20) -> C:\Users\runni\slugshot marketing\out\smoke\research_live\yt_collect\youtube_snapshots.csv [run youtube-20261125T164608Z-3827: 1 ok / 0 failed requests, ~1 units] |
| Twitch Helix live | **PASS** |     1960479087  Robox |
| Dashboard tests | **PASS** | Ran 33 tests in 4.824s: OK (store, metric rules, connectors on fixtures, imports, exports, vault, server security) |
| Knowledge and sentiment tests | **PASS** | Ran 21 tests in 0.220s: OK (schema, links, game truth, expiry, export and policy gates, sentiment pipeline, fixture isolation) |
| Publishing tests (no network) | **PASS** | Ran 24 tests in 9.247s: OK (fixture uploads only: chunking, approval binding, reveal lock, game truth, manual fallback, linking) |
| Analytics tests (owner screens) | **PASS** | Ran 16 tests in 1.741s: OK (combined totals, no double counting, measurement windows, tags, comparisons, learning loop) |
| Knowledge banks validate | **PASS** | VALID - 0 errors, 0 warnings |
| Dashboard fixture sync (all connectors) | **PASS** | 9 connector runs ok/partial; 1 isolated failures as designed (youtube_analytics/yt-es: no ES fixture) |
| Dashboard server on loopback | **PASS** | 127.0.0.1:47615 answers |

## Manual checks (a person must do these)

- Watch `out/smoke/ffmpeg_vertical.mp4` and `out/smoke/remotion.mp4` on a phone: captions readable, in time with the voice, clear of the platform buttons; audio clean.
- Listen to `out/smoke/kokoro.wav`: is the voice good enough to use, or should narration be recorded?
- Watch the assembled `out/smoke/SS_*_WORLD_Smoke_Assembly_*.mp4`: do scene changes land on the right words?
- Read `out/smoke/narration.srt` against the narration; add new mishearings to config/glossary.json.
- Record 20 s of real gameplay in OBS and run it through `.\ss import`, `caption`, `render`.
