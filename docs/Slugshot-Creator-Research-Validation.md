# Slugshot — creator research infrastructure validation

**Date:** 24 November 2026 · Stage 4.3 · Controlled exploratory test, not a representative market study.

**Decision:** Use vidIQ selectively, not as the routine data collector. The owner considers 50 credits for a small test too expensive relative to the monthly allowance. Prioritise official APIs, native exports, and free public research. No purchases, new subscriptions, publishing, new API setup or further credits authorised in this record.

**Historical test record:** sections 1–6 preserve the Stage 4.3 test and its recommendations. The subsequent Stage 4.4 outcome and current execution policy are recorded in §7; they supersede historical operational status.

## 1. Scope and evidence

Test questions: can we discover recent Roblox videos and reusable creative formulas, distinguish momentum from accumulated popularity, find English and Spanish examples, extract video structure, and independently verify dates and statistics? Can we recognise saturation of a specific joke rather than abandon an underlying format? Tested vidIQ's research features, then TinyFish search and fetch. Not an exhaustive test of either product. No own-channel data exists; no content was published.

Evidence labels remain A (official), B (published research), C (creator practice), D (hypothesis), S (Slugshot measured). Additionally distinguish P1 first-party measured counts, P2 first-party sampled/normalised signals, P3 third-party reported/estimated values (with exact metric provenance when known), P4 qualitative interpretation. A provider returning a number does not establish that it is current or measured directly. Missing means unknown, not zero. Never infer viewer geography or demographics from title language, account location or AI descriptions. All vidIQ figures below are provider-reported test observations on 24 November, not independent platform confirmations. Keep dated audit evidence only as permitted by provider terms; refresh/delete restricted statistics and do not use this report as a permanent raw API archive. No YouTube Data API collection was performed in this test.

## 2. vidIQ test ledger

| Operation | Query / scope | Cost | Result |
|---|---|---:|---|
| Recent Shorts EN | Roblox; English titles; after Nov 17; recentVph; 12 rows | 5 | Relevant animation, games and challenges, but generic results and repeat creators |
| Recent Shorts ES | Same, Spanish titles | 5 | Relevant Spanish gaming; language false positives |
| IG/TikTok concept EN | Roblox gaming comedy, character skits, gameplay surprises and meme formats; EN descriptions; after Nov 10; 5/platform | 5 | Detailed concept, hook, format, metrics and source URLs |
| IG/TikTok concept ES | Roblox humor, memes, situaciones de jugadores, animaciones y jugadas sorprendentes; ES descriptions; same window; 5/platform | 5 | Useful Spanish examples; adjacent games also returned |
| Small-channel YT outliers | Roblox EN Shorts this week, max 250K subscribers, 8 results | 5 | Smaller creator breakouts; irrelevant art entry; not evidence of present momentum |
| Historical video stats | GH'S video 0w10o6CLxps, daily, Nov 21–24 | 5 | Four dated observations with views/likes/comments/VPH |
| Rising ES keywords | Roblox gaming memes and games; week; ES; limit 12 | 5 | Only GTA 6 en vivo and Vegetta, weak Roblox relevance |
| Rising TikTok sounds | Roblox gaming memes; rising; six returned of nine | 5 | Usage growth, examples, niche fit; no regional filter in this operation |
| Individual Spanish TikTok breakdown | @sebasgb572 video 7708074478366100754 | 10 | Completed, timestamped dialogue and visual structure; not independently watched |
| **Total** | **Nine substantive calls** | **50** | Balance verified 150 → 100; resets 24 Dec 2026 |

Balance checks and job-status polling cost zero. Costs observed/documented on test date, not guaranteed future pricing. At 5 credits per discovery call the 150-credit allowance funds at most 30 such calls/month; 10-credit video analyses reduce that. This is a significant constraint for regular bilingual monitoring. No more calls were made after this test. Do not repeat tests or spend credits without a reason and owner-approved budget.

### Discovery and history: selected references

| Reference | Published | Reported views | Format or research purpose |
|---|---|---:|---|
| [GH'S Roblox in 2026](https://youtube.com/shorts/0w10o6CLxps) | 21 Nov | 7.36M | Animation; individual historical velocity test |
| [GH'S Prime Roblox](https://youtube.com/shorts/YtE84zauy38) | 18 Nov | 4.90M | Then/now nostalgia candidate; same creator, not independent replication |
| [CorlBlox Loudest Emoji Match](https://youtube.com/shorts/q8rLAfIXv94) | 17 Nov | 3.67M | Game challenge |
| [Alguien quiere jugar Roblox?](https://youtube.com/shorts/o6H2a2x4YTA) | 17 Nov | 2.87M | Spanish discovery |
| [Bioma vs Tocino](https://youtube.com/shorts/9z6CGuLYLrI) | 18 Nov | 2.58M | Spanish creature/game comparison |
| [Catown rarest Rivals weapon](https://youtube.com/shorts/GiyM1kx8Z18) | 23 Nov | 89.1K | Rarity curiosity; close genre fit |
| [Funny Roblox luxury egg](https://youtube.com/shorts/rCxILSeP1I8) | 22 Nov | 37.2K | Smaller channel; loss/reversal; provider 5.2x breakout |
| [Roblox King4233](https://youtube.com/shorts/Ujn4mozxz2k) | 20 Nov | 45.1K | Provider 9.5x breakout but only 0.2 VPH in outlier output; metric semantics need checking |

GH'S dated velocity (provider field `vph`): 21 Nov 15:20 UTC 159,191; 22 Nov 00:37 152,926; 23 Nov 00:32 45,078; 24 Nov 00:38 19,800. First-to-last reduction ~87.6%. One video's measured/reported trajectory is not a format-level trend. Recent-velocity search supports `recentVph` sorting, but returned rows expose `vph` rather than the exact recentVph value, and values resemble lifetime averages; do not interpret them as current-hour counts without confirmation. Outlier tool uses creator-relative metrics that are provider-derived; do not duplicate unapproved metrics from YouTube API data.

### TikTok/Instagram concept examples

| Reference | Date | Provider-reported views / breakout | Formula suggested by provider analysis |
|---|---|---|---|
| [Dale's Tales glow-up](https://www.instagram.com/reel/DgBr0SKAPo4) | 22 Nov UTC | 3.7M / 9.4x | Personal struggle → progression → audience choice; interactive serial storytelling |
| [elsoialex GTA claim](https://www.instagram.com/reel/Df_PR91u6Fk) | 21 Nov | 3.6M / 1322.1x | Extraordinary claim → investigate → reveal; topical gaming commentary |
| [eldiamantecarll infinite throw](https://www.instagram.com/reel/Dfojxn2IPXG) | 12 Nov | 1.4M / 1127.7x | Low-probability game outcome, visible escalating stakes and facecam reaction; only 200 reported followers, verify |
| [sebasgb572 lone wolf](https://www.tiktok.com/@sebasgb572/video/7708074478366100754) | 14 Nov | 199.4K / 5.2x | Relatable social situation → contrasting personalities → repeated attempts → deadpan rejection |
| [giansitotv_ word chain](https://www.instagram.com/reel/DgD3l54tB-6) | 22 Nov | 27.1K / 8.3x | Gameplay challenge and friend reaction |
| [scumsszy bad connection](https://www.tiktok.com/@scumsszy/video/7710740086706441502) | 21 Nov | 191.8K / 8.9x | Unexpected gameplay malfunction and comedic reaction |
| [dingolul horror skit](https://www.tiktok.com/@dingolul/video/7709975276989598998) | 19 Nov | 416.6K / 1.7x | Scripted game-based mystery |
| [storytelling101tv one sentence](https://www.instagram.com/reel/Df7-jrdyp1f) | 19 Nov | 45.5K / 11.6x | Fictional rule and disruptive antagonist |
| [vistny anime-football move](https://www.tiktok.com/@vistny/video/7706337222647106836) | 10 Nov | 58.9K / 15x | Mechanic tutorial with dramatic anime audio; rights check |

These are candidate formulas, not proven rising trends. Avoid copying scripts, assets or copyrighted audio. Search results included irrelevant Fortnite/GTA examples and dubious follower counts (including zero); validate before conclusions. The provider's hook, format, audience and production effort descriptions are generated interpretations, not measured audience data. No competitor retention, true conversion or country-level viewer data was obtained. At least two independent examples are needed even for a preliminary pattern; collect ordinary/failed examples too.

The sebasgb572 watch operation returned ~20.37 seconds and a Spanish dialogue/visual breakdown. 0–4s: friendly avatar approaches an uninterested character; 4–10s: increasingly blunt responses; 10–19s: repetition of contrasting personalities. Output is a useful structural hypothesis, not verified by actual human playback. TikTok page fetch subsequently failed. Gemini remains preferred for detailed analysis of authorised accessible video; do not obtain media by bypassing access restrictions.

### Rising audio and the Huss distinction

Provider tracked 10–23 Nov: [LUNATIC – Slowed](https://www.tiktok.com/music/x-7704417201616766977), 7.3x usage growth, 273 videos/day, 14% sampled niche fit; [Numbers](https://www.tiktok.com/music/x-6732119861989738498), 2.6x, 214/day, 13%; [tleBot original sound](https://www.tiktok.com/music/x-7689314587900103454), 1.2x, 81/day, 17%. Usage and estimated views/hr cover all videos using the sound, not just Roblox. The chart covers a selected ~400-sound daily universe, not all TikTok; results do not establish regional growth or licensing. Example [friends gaming vs partying](https://www.tiktok.com/@returnofmxnster/video/7709326876799405325) reported 2.5M views.

Numbers examples: [synelite1 Huss basketball story](https://www.tiktok.com/@synelite1/video/7710239627721887008), 20 Nov, 16.5M; [lileggy38 Cracking Place](https://www.tiktok.com/@lileggy38/video/7706667212848811294), 10 Nov, 5.7M; [kr.editzx0 Christmas present rule](https://www.tiktok.com/@kr.editzx0/video/7705333606012505351), 7 Nov, 3.8M. **Correction:** the earlier chat table included an incorrect synelite1 URL; the link here is the returned provider URL. Separate specific Huss joke, associated sound, In This Town rule-world structure and broader Roblox animation. Growth of one is not proof of growth of another. Saturation/decline of Huss is an owner concern and hypothesis, not established by this test.

## 3. TinyFish controlled test

Search and public-page extraction only; full interactive browser was not tested. No attempt to bypass logins, errors or access restrictions.

| Target | Result | Consequence |
|---|---|---|
| [TikTok Creative Center](https://ads.tiktok.com/creative/creativeCenter/trends) | Redirected to new site; navigation only, login prompt; no trend table | Native manual use or approved access; no bulk extractor demonstrated |
| [Google Trends Mexico Roblox/Bajoterra](https://trends.google.com/trends/explore?date=today%201-m&geo=MX&q=Roblox,Bajoterra) | Some regional/rising-query text; main chart errored | Official CSV/manual chart or approved API; no numerical trend inference from partial fetch |
| GH'S YouTube Short | Title, description and tags; no views/date | Use existing official API collector rather than browser extraction |
| Dale's Tales Instagram | Caption, timestamp 22 Nov 02:01:51 UTC, ~185.1K likes, 476 comments and some visible comments; no views; playback error | Partial first-party-page verification; 3.7M view count unconfirmed; local date in page description 21 Nov differs from UTC |
| sebasgb572 TikTok | Site maintenance/error, no useful data | Stop at access failure; provider analysis not independently validated |
| EN/GB recent Huss search | Dated remixes, cultural documentation, commercial template | Useful cultural context, not representative metrics |
| ES/MX recent Roblox meme search | Mixed native Spanish, translated English, unrelated GTA content, missing dates | Query refinement and human verification needed; no market-level inference |

Context sources surfaced: [Know Your Meme Huss entry](https://knowyourmeme.com/memes/huss-huss-huss-in-this-town-everybody-goes-out-partying-except-me), [20 Nov meme roundup](https://knowyourmeme.com/editorials/the-weekly-meme-roundup-pterodactyl-in-mexico-huss-town-robert-pattinson-and-more), [commercial Huss template](https://makeviral.ai/templates/huss-huss-huss-ai-trend). Third-party claims not independently verified. Template availability and remix proliferation may suggest saturation, not proof of falling demand. TinyFish can help contextual discovery and source verification, but test does not justify reliance for bulk social analytics. No TinyFish credit/usage balance was measured; do not assume unlimited free usage.

## 4. Revised architecture and next steps

| Gap | Preferred method | Status |
|---|---|---|
| Bulk recent/daily YouTube data | Existing Claude `ss yt` official collector; improve explicit language/region query logging, compliant per-video history | Implemented base; enhancements proposed |
| Historical search interest and regional signals | Google Trends official CSV; API if approved | Proposed, no setup yet |
| Streamer culture and clips EN/ES | Twitch Helix, investigate terms and access | Proposed |
| Instagram public stats | Business Discovery eligibility/fields verification; native public observations where permitted | Investigate; no assumption that competitor Reel views available |
| TikTok discovery and sound history | Native Creative Center, public research, selective vidIQ, evaluate legitimate free providers | Partial; genuine gap remains |
| Creative formulas | ChatGPT source research, Gemini audiovisual analysis, selective vidIQ concept/hook/format searches | Existing; vidIQ 5 credits/query |
| Data handoff | Google Drive connected and search tested (no Slugshot matches); local CSV manual handoff initially | Folder/permissions/sync deferred to shared workflow |
| Competitor retention and demographics | Not available; own analytics after launch | Deferred |

Use ordinary web search and TinyFish selectively for cultural context. Use vidIQ for hard-to-reproduce high-value operations, particularly concept/hook/format discovery across TikTok/Reels, selective rising audio and unusual outliers. Reserve expensive 10-credit video analyses for exceptional cases. Routine official API statistics should not consume vidIQ credits. No new paid tools or scraping. Investigate provider terms before collection, exports, retention, AI transfer and derived metrics; owner permission alone does not resolve third-party terms. Do not permanently store restricted API snapshots in a knowledge bank or Drive. No API credentials leave local approved secret storage. Verify exposed YouTube key rotated/restricted before new live runs.

## 5. Concept lifecycle research protocol (proposed)

Unit of research is a reusable concept, not just a viral upload. Maintain canonical platform ID/URL, creator, concept ID, distinct meme/sound/format identifiers, language, intended region, actual region evidence if available, publication time and observation UTC, source/provenance, metric definition, permitted time series, classification confidence, qualitative audience feedback, rights and adaptation notes. Separate platform-specific datasets and restricted data; do not merge YouTube API data or create prohibited cross-channel metrics. Archive durable qualitative lessons and source references; refresh or delete time-limited metrics. Never convert estimated audience demographics into facts.

Classify emerging, accelerating, established, saturated, declining or unknown. Seek independent creator adoption, recent new examples, comparable-age performance when permitted, repeated dated observations, changing upload frequency, negative/ordinary examples, audience fatigue signals and search/audio evidence. Distinguish a video's decay from format-level decline. Selective discovery feeds are biased and not a denominator for population growth. Keep uncertain cases unknown. Example: Huss may be overused even if rule-world storytelling remains valuable; measure before claiming either is rising or falling. No formula has yet been validated by Slugshot's own posting results.

## 6. Readiness decision

Stage 4.3 exploratory validation complete; country-specific performance and reliable metric reconciliation not proven. Next Stage 4.4: agree a single Claude implementation brief, investigate Twitch, Google Trends, YouTube improvements and Meta eligibility. Then standardise research methods and source bank before foundational studies. No campaign production, dashboard, new custom agents, automation, installation or billing changes were performed. Preserve 100 remaining vidIQ credits for genuinely valuable targeted queries; agree budget before further substantive use.


## 7. Subsequent implementation and execution policy

## Current research infrastructure and roadmap — 24 November 2026

Stage 4.4 is accepted and committed at marketing repo `13adfd2` (toolkit pack generated 19:26 UTC). Claude reports 20/20 full smoke checks, 7/7 research smoke checks and 27/27 offline tests. These are reported local results, not tests rerun by ChatGPT. YouTube bilingual sweep, pagination, creator uploads, comments, quota accounting, category flags and observation/context deduplication were live-tested. Wikipedia redirect deduplication, coverage logging, pacing and retries are implemented; Trends RSS expiry and public-observation scope deduplication are corrected. Wikimedia, Twitch, Roblox and Trends RSS collectors are live-tested. Google Trends Explore CSV and Creative Center clipboard parsing still need first real inputs; validate naturally during research, not a separate infrastructure phase. Google Trends alpha application submitted; access pending. TikTok Discovery API deferred for business eligibility; Twitch terms review confirmed by owner, local-only export gate and 24-hour retention remain unchanged. No Slugshot campaign results yet.

TinyFish's later interactive Creative Center test reached the US seven-day hashtag table, confirmed regional/industry and 7/30/90-day controls, and imported the displayed post/view figures into the observation importer. Detailed analytics prompted a separate login; authenticated detail access, native export and ongoing usage cost were not confirmed. This supersedes the earlier navigation-only extraction result, not a claim of general automated access.

Next: Stage 4.5.1 methodology; 4.5.2 existing skills/resource evaluation; 4.5.3 specialised research skills; 4.5.4 bilingual collection configurations; 4.5.5 bounded validation through real tasks. Stage 4.6 foundational studies and 4.7 knowledge banks follow. Stage 5 cross-AI handoff, 6 lightweight dashboard only if useful, 7 production preparation and 8 campaign remain later. The operational Claude skill is a small convenience refinement, not a new infrastructure stage or a blocker to Stage 4.5.

## Operating philosophy — automation first (owner decision, 24 November 2026)

This is the current operating policy and supersedes earlier manual-first handoff recommendations. The owner wants an ambitious, low-friction AI-assisted marketing workflow, not an enterprise-style approval process. **The command-line toolkit is Claude's interface, not the owner's interface.** A single natural-language request should initiate routine collection, processing, validation and delivery. Human input is reserved for meaningful decisions and interactions that genuinely cannot be delegated.

- Default to execution: Claude runs PowerShell/terminal and existing `ss` commands, selects appropriate collectors, manages local files, handles bounded retries, pagination, quota limits, routine configuration, imports, pruning and reports. Do not ask the owner to run commands or format tables that Claude can handle. ChatGPT designs research and interprets it; Claude owns operational execution; Gemini/Flow handles visual work.
- Be resourceful: investigate available APIs, browser capabilities, installed connectors, native exports, open-source tools and alternative permitted routes when they offer a material benefit. Prefer small working experiments to prolonged planning. Use free, reversible operations within the marketing workspace without repeatedly asking for approval. Missing documentation or uncertain metric semantics are reasons to investigate and label uncertainty, not automatic blockers.
- Be proportionate: report real limitations and keep working on the remaining sources if one fails. Do not invent additional restrictions or repeat resolved concerns. Respect actual access restrictions, applicable provider terms, privacy, rights and credential handling. Do not bypass authentication, rate limits or access controls; do not treat owner direction as provider permission. Where an access route is not established as permitted, use a supported alternative, ordinary manual inspection or native export and automate the downstream work.
- Creative Center is a core research source, not a reason to stall the project. Use supported access and native export options when available; Claude handles `cc-links`, `cc-paste`, `observe import`, validation and reporting. If a human page copy or sign-in is genuinely required, ask only for that smallest action, preferably grouped into one request. No claims of fully automated Creative Center collection until it has been demonstrated and permitted. No scheduled scraping or hidden endpoints.
- Preserve genuine boundaries: no new paid services, billing changes or further vidIQ credit use without an agreed budget; no publication, destructive operations, credential disclosure, or game-repo modifications/builds/Git changes without owner approval. Preserve provider-specific retention, transfer and metric restrictions, provenance, missing-value semantics and the Studio isolation guard. Routine local marketing research is not a consequential game change.
- Reuse the current toolkit. No new agent, dashboard, database, scheduler or orchestration service merely for convenience. Add a lightweight Claude research-operations skill and small glue only when useful. Prefer existing working tools; add capabilities when real bottlenecks justify them.
- Deliver one concise collection report with scope, sources, rows collected, failures, material caveats and paths to a clean shareable bundle (manifest and data dictionary included). Keep restricted/local-only data local. Use the connected shared workflow when available and permitted; until then, Claude prepares one clean bundle and the owner performs only the necessary transfer. Do not claim unattended sync is configured.

## Stage 4.5.3 implementation (Claude, 24 Nov 2026), local addendum

Claude implemented the research intelligence layer in the marketing repo:
- the `slugshot-research-analysis` skill;
- `ss analyze` (intake QC, statistics with denominators, same-item changes, sensitivity, trend dimensions with a lifecycle proposal, change points, outcome-blind coding with codebook v1.0, Wikidata/GDELT context);
- `ss evidence` (ledger + validator, EvidenceGuard V0.1 export);
- research templates;
- four pinned upstream skills: verifying-bibliography, surveying-literature, synthesis-fact-checking, hypothesis-generation.

Results:
- Tests: 51 offline research tests pass; the research smoke test passes; full regression in reports/smoke-test.md.
- Worked example ledger EXAMPLE-HUSS-SLUGTERRA (real data): Huss lifecycle unknown from one snapshot; es.wikipedia Slugterra attention change point 25 Sep 2026, median 41 → 26 daily views. Suggestive, single family.

Handoff: docs/chatgpt-handoff-4.5.3.md. Next: Stage 4.5.4 query families and watchlists (ChatGPT), then 4.5.5 validation through real tasks.
