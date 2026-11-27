# Slugshot Marketing Bank

> Historical snapshot. We have permission to use Apify for the toolkit's TikTok collection. A person reads Creative Center. See the [current data guide](../research-data.md).

Updated 24 November 2026 · Research scope: TikTok, YouTube Shorts, Instagram Reels · English and Spanish-language audiences

Slugshot is a Roblox PvP game built around creature-powered shots, transformations, and abilities. The initial campaign will focus on short-form videos that make the 1v1 gameplay clear and give individual slugs a recognisable personality. Reddit is a later research topic.

**Core creative direction — owner-approved, 24 November 2026:** Slugshot should feel like an entertainment account with a Roblox game behind it, not an account constantly advertising a game. Cultural relevance and humour are a primary marketing research priority, alongside gameplay and conversion. Research what the target audience actually finds funny now, then turn that understanding into original Slugshot content. See the Cultural intelligence section below. This direction is a strategic decision; the performance of individual formats is still untested.

**Bilingual campaign — owner decision, 24 November 2026:** Separate English and Spanish-language account streams, with localisation and independent cultural intelligence for each. Spanish-speaking markets include Latin America as well as Spain. Reuse the production infrastructure and visual assets wherever possible; do not treat Spanish as merely a translated English feed. See the bilingual strategy below.


**Roblox-first production — owner decision, 24 November 2026:** Most content is authentic gameplay or Roblox-native staged comedy, animation and storytelling. Short AI/anime/manga cutaways (normally 1–4 seconds) serve a narrative purpose, not substitute gameplay. Floppy never transforms or uses abilities, including fictional scenes. The updated Claude toolkit (`13adfd2` baseline) governs production details.

## Operating philosophy — automation first (owner decision, 24 November 2026)

This is the current operating policy and supersedes earlier manual-first handoff recommendations. The owner wants an ambitious, low-friction AI-assisted marketing workflow, not an enterprise-style approval process. **The command-line toolkit is Claude's interface, not the owner's interface.** A single natural-language request should initiate routine collection, processing, validation and delivery. Human input is reserved for meaningful decisions and interactions that genuinely cannot be delegated.

- Default to execution: Claude runs PowerShell/terminal and existing `ss` commands, selects appropriate collectors, manages local files, handles bounded retries, pagination, quota limits, routine configuration, imports, pruning and reports. Do not ask the owner to run commands or format tables that Claude can handle. ChatGPT designs research and interprets it; Claude owns operational execution; Gemini/Flow handles visual work.
- Be resourceful: investigate available APIs, browser capabilities, installed connectors, native exports, open-source tools and alternative permitted routes when they offer a material benefit. Prefer small working experiments to prolonged planning. Use free, reversible operations within the marketing workspace without repeatedly asking for approval. Missing documentation or uncertain metric semantics are reasons to investigate and label uncertainty, not automatic blockers.
- Be proportionate: report real limitations and keep working on the remaining sources if one fails. Do not invent additional restrictions or repeat resolved concerns. Respect actual access restrictions, applicable provider terms, privacy, rights and credential handling. Do not bypass authentication, rate limits or access controls; do not treat owner direction as provider permission. Where an access route is not established as permitted, use a supported alternative, ordinary manual inspection or native export and automate the downstream work.
- Creative Center is a core research source, not a reason to stall the project. Use supported access and native export options when available; Claude handles `cc-links`, `cc-paste`, `observe import`, validation and reporting. If a human page copy or sign-in is genuinely required, ask only for that smallest action, preferably grouped into one request. No claims of fully automated Creative Center collection until it has been demonstrated and permitted. No scheduled scraping or hidden endpoints.
- Preserve genuine boundaries: no new paid services, billing changes or further vidIQ credit use without an agreed budget; no publication, destructive operations, credential disclosure, or game-repo modifications/builds/Git changes without owner approval. Preserve provider-specific retention, transfer and metric restrictions, provenance, missing-value semantics and the Studio isolation guard. Routine local marketing research is not a consequential game change.
- Reuse the current toolkit. No new agent, dashboard, database, scheduler or orchestration service merely for convenience. Add a lightweight Claude research-operations skill and small glue only when useful. Prefer existing working tools; add capabilities when real bottlenecks justify them.
- Deliver one concise collection report with scope, sources, rows collected, failures, material caveats and paths to a clean shareable bundle (manifest and data dictionary included). Keep restricted/local-only data local. Use the connected shared workflow when available and permitted; until then, Claude prepares one clean bundle and the owner performs only the necessary transfer. Do not claim unattended sync is configured.

## Current research infrastructure and roadmap — 24 November 2026

Stage 4.4 is accepted and committed at marketing repo `13adfd2` (toolkit pack generated 19:26 UTC). Claude reports 20/20 full smoke checks, 7/7 research smoke checks and 27/27 offline tests. These are reported local results, not tests rerun by ChatGPT. YouTube bilingual sweep, pagination, creator uploads, comments, quota accounting, category flags and observation/context deduplication were live-tested. Wikipedia redirect deduplication, coverage logging, pacing and retries are implemented; Trends RSS expiry and public-observation scope deduplication are corrected. Wikimedia, Twitch, Roblox and Trends RSS collectors are live-tested. Google Trends Explore CSV and Creative Center clipboard parsing still need first real inputs; validate naturally during research, not a separate infrastructure phase. Google Trends alpha application submitted; access pending. TikTok Discovery API deferred for business eligibility; Twitch terms review confirmed by owner, local-only export gate and 24-hour retention remain unchanged. No Slugshot campaign results yet.

TinyFish's later interactive Creative Center test reached the US seven-day hashtag table, confirmed regional/industry and 7/30/90-day controls, and imported the displayed post/view figures into the observation importer. Detailed analytics prompted a separate login; authenticated detail access, native export and ongoing usage cost were not confirmed. This supersedes the earlier navigation-only extraction result, not a claim of general automated access.

Next: Stage 4.5.1 methodology; 4.5.2 existing skills/resource evaluation; 4.5.3 specialised research skills; 4.5.4 bilingual collection configurations; 4.5.5 bounded validation through real tasks. Stage 4.6 foundational studies and 4.7 knowledge banks follow. Stage 5 cross-AI handoff, 6 lightweight dashboard only if useful, 7 production preparation and 8 campaign remain later. The operational Claude skill is a small convenience refinement, not a new infrastructure stage or a blocker to Stage 4.5.

## How to add material

Drop a clip link, screenshot, creator profile, analytics export, or rough video idea into the marketing chat. For each external clip, capture the platform, creator, link, post date if visible, views and observation date, opening hook, and payoff. Include a line about what Slugshot could test. Keep missing metrics blank. When a clip's views change, add a dated observation to the existing entry.

Useful statuses for Slugshot ideas: **idea**, **filmed**, **published**, **reviewed**. Log platform stats separately for each upload, even when the same edit is cross-posted.

## Clip references

Counts are rounded public snapshots gathered on or around 20 November 2026 unless a different date is shown. Posts have had different amounts of time to gather views. These examples give us hooks to test.

| Platform | Reference | Public views or plays | What to test |
|---|---|---:|---|
| TikTok | [My Christmas Market release clip](https://www.tiktok.com/@real_mustard/video/7707992295664110861) · 14 Nov · 20s | 5.2M | Put the playable premise and release time in one short clip. [Source](https://ttanon.com/@real_mustard/video/7707992295664110861) |
| TikTok | [Infiltration Studio's two-player Christmas game](https://www.tiktok.com/@infiltrationstudio/video/7708120048161836301) · November | ~2M | Give the viewer a reason to send the clip to a friend. [Source](https://vosscore.com/trend/6afb72caceda48667063e3a0) |
| TikTok | [Throw Food for Animals “In This Town” story](https://ttanon.com/discover/in-this-town-roblox-story) · @zaylento.yt · 18 Nov | 2.9M | Build the story around a creature or mechanic that exists in the game. |
| TikTok | [RIVALS butterfly-knife 1v1 edit](https://urlebird.com/video/rivals-butterfly-knife-edit-1v1-ggs-7572739331345992990/) · @aixxilius | 1.4M | Make the duel's signature move the visual payoff. |
| TikTok | [RIVALS animated friend-clutch skit](https://ttanon.com/@dingus.the.animat) · 8 Feb · 13s | 966K | Use a friend dynamic to frame a clutch that a new viewer can understand. |
| YouTube Shorts | [SlingshotBwai challenges a top RIVALS player](https://www.youtube.com/shorts/el2qk6FCc-4) · 26 Sep | ~542K | Give the match one clear reason to watch, such as starter slug versus favourite slug. [Source](https://vidiq.com/youtube-stats/channel/@slingshotbwaii/videos/el2qk6FCc-4/) |
| YouTube Shorts | [ItsGuestCap's ground-is-forbidden story](https://vidiq.com/youtube-stats/channel/@itsguestreal/videos/) · 23 Oct · 2m 17s | 10.2M | Establish one rule upfront and build the story around breaking it. |
| YouTube Shorts | [ShazFrames’ cursed-ball choice](https://vidiq.com/youtube-stats/channel/@shazamframes/videos/) · 20 Oct · 52s | 1.79M | Pause a fight at a decision point and ask the viewer which slug they would take. |
| Instagram Reels | [Cardboard recreation of Don't Splash](https://www.instagram.com/reel/DfJPNyLOwl6/) · @sopa.stageart · 31 Oct | 5.1M | Turn one recognisable game rule into a short visual gag. [Source](https://shorti.ai/en/v/instagram_DfJPNyLOwl6?t=1) |
| TikTok | [Real Futbol X pre-launch edit](https://ttanon.com/@joinrfx/video/7705459088632728850) · @joinrfx · 7 Nov · 14s | 343K on 21 Nov | Compare a short, entertainment-led edit with an announcement that gives viewers a specific action. |
| TikTok | [Real Futbol X stress-test announcement](https://ttanon.com/@joinrfx/video/7705870606293536008) · @joinrfx · 8 Nov · 20s | 162K on 21 Nov | Keep the game name visible and give viewers a clear next step when a test is open. |

**Same-account comparison.** The Real Futbol X posts were published one day apart and had about a 2.1× difference in observed views. The clips also differ in length, content, and purpose. Use these as examples of two purposes to test for Slugshot, with public views available and stress-test signups unreported.

### Campaign benchmarks

- [Kill Streak launch](https://www.bloxclips.com/campaigns/kill-streak) · Agency reports 10M+ views in 10 days from 11,153 clips and 3,000+ creators. Closest genre reference for Slugshot. Player acquisition count was unreported.
- [Evade Halloween update](https://metaclip.app/case-studies/evade) · Vendor reports 1.7M+ views, with 93% from Reels and 910K+ from the top Reel. Existing game with a funded creator campaign.
- [Roblox horror campaign](https://www.inikus.com/case-studies/roblox-horror-game-campaign) · Agency reports 1M+ views in 30 days while peak concurrent players rose from roughly 700 to over 2,000. Unnamed game with an existing audience. The public figures do not isolate clip-driven plays.
- [29,287 Roblox promo posts](https://abondy.com/blog/roblox-game-marketing-on-tiktok-and-youtube-shorts) · Abondy's mostly small-account sample. Shorts 28 median views and 39.0% over 1,000 views. TikTok 90 and 1.2%. Reels 51 and 1.1%. Vendor reported some public Reels counts undercounted plays. View definitions differ, and the analysis contains no player-conversion data.

## Public trend tracking

### First snapshot · 21 November 2026

| Signal | Evidence | Slugshot decision |
|---|---|---|
| Rule-world Roblox stories and Huss | The displayed [TTAnon #inthistown sample](https://ttanon.com/discover/inthistown) had 16 posts from 14 creators dated 19–21 Nov, roughly 22M combined observed views and a sample median of 68.8K. The 12.8M and 6.0M posts supplied roughly 86% of those sampled views. [Huss breakout](https://ttanon.com/@synelite1/video/7710239627721887008) · [another Huss creator](https://ttanon.com/@wayne.blox/video/7710408898548698376) | Active in this indexed sample. Test one original rule-world story. Treat the specific sound/meme as optional and check rights in each app before using it. |
| Gameplay that reads quickly | [Wieldr’s 20:19 UTC snapshot](https://wieldr.app/trending/roblox) recorded about 10.74M TikTok views across five tracked creators for Throw Food For Animals, 2.53M across seven for Ragdoll Soccer, and 1.89M across five for Dandy’s World. These were videos published in the prior seven days for games the vendor already follows. | Pull individual clips next and code the opening and payoff before deciding why viewers engaged. Test a Slugshot round with a readable choice or reversal. |
| Character and game fandom | Dandy’s World appeared in the TikTok game snapshot and its [1.0 launch devlog](https://lootsheep.com/videos?lang=en) appeared in a public YouTube tracker. | Cross-check evidence on both platforms. Keep launch and fandom signals in context when selecting comparators for a new game. |

The TTAnon figures come from one displayed page using rounded public counts. It is a selected, changing sample and can overlap other keyword pages. Wieldr counts come from the tracker’s coverage. Game-player snapshots can be recorded for context when available. Attribution requires separate evidence.

### Repeatable scan

1. Find topics through [TikTok Creative Center](https://ads.tiktok.com/creative/creativeCenter/trends?region=GB), public Roblox trackers, and a fixed YouTube Shorts and Reels watchlist of comparable creators. Verify the country filter when using a regional chart. Record platform and coverage for each source.
2. Save one row per unique platform post ID. Record theme, creator, URL, published time, observed time and visible views, shares and comments. Add game name, observed opening and payoff, and whether the post appears official, creator-made or sponsored. Mark unobserved fields as unknown. A caption alone does not verify the exact edit.
3. Recheck the same posts after 24–48 hours and calculate views gained divided by elapsed hours. For independently collected public-web observations, compare with similarly aged posts and each creator’s recent median where comparable observations exist. For YouTube API-derived data, use only the permitted per-video calculations in the local toolkit; do not compute unapproved cross-video ratios or rankings. If only one observation is available, keep lifetime views and post age as a snapshot.
4. Summarize distinct creators, median, range, top-post share and any growth or cross-platform corroboration. Flag a possible emerging format when recent examples from multiple unrelated creators begin beating their usual reach. Call a breakout concentrated when a few clips explain most sampled views. Keep reach, view growth and player acquisition as separate observations.
5. Pick one testable Slugshot adaptation for each promising format. Preserve the viewer promise and write an original premise. Check the mechanic against the current build before it appears in gameplay marketing.

Use public sources for trend discovery and competitor reach. Retention and player conversion come from creator-side analytics or disclosed case studies. TikTok’s [Research API](https://developers.tiktok.com/products/research-api/) is aimed at eligible noncommercial/public-interest researchers. The local YouTube Data API collector is now implemented and live-tested; see the toolkit status below. Treat its policy limits and independently sourced web observations separately.

### Script-writing setup

Use Slugshot Short-Form Scripting to produce two or three honest openings, approximate timed beats, visuals, spoken lines and essential on-screen text. Read the script aloud and check it muted. A first-time viewer should understand the premise and see a payoff. The drafting workflow adapts craft ideas from [short-form-video-script](https://github.com/social-media-skills/skills/blob/main/skills/short-form-video-script/SKILL.md) and [humanize](https://github.com/harshaneel/humanize/blob/main/plugins/humanize/skills/humanize/SKILL.md), two MIT-licensed writing references. Use specific details and natural spoken rhythm. Treat precise platform-performance claims as hypotheses until verified. Floppy remains the non-transforming underdog, subject to current canon.

## Cultural intelligence and humour — core research priority

Agreed 24 November 2026. This is a living research stream, not a static list of jokes or an instruction to install more software. The owner considers this one of the most important aspects of the campaign. The existing Claude editing skill supplies general craft (cuts, timing, captions and audio); it does not establish what contemporary audiences find funny. ChatGPT must supply that changing cultural context through research and creative briefs. Gemini/Flow creates original visual performances; Claude assembles and edits them. No new agent, subscription, voice engine or integration is required at this stage. Voice selection, asset sourcing and real production tests remain deferred.

### Research beyond Roblox marketing

| Research stream | What to investigate | Proposed cadence during campaign |
|---|---|---|
| Streamer and creator culture | Viral reactions, catchphrases, character archetypes, running jokes, creator references and reaction formats | Every 2–3 days |
| Anime and fandom culture | Recognisable fight tropes, rivalries, transformations, dramatic entrances, aura edits, parodies and visual conventions | Every 2–3 days |
| Voiceover humour | Unexpected narrators, authentic Nigerian English or other specific African varieties, Jamaican Patwa, London slang, dramatic documentary voices, deadpan delivery and contrasting character voices | Daily discovery alongside memes/audio |
| Memes and internet humour | Absurdist humour, brainrot, recurring characters, reaction images, social situations, ironic edits, current slang and audience in-jokes | Daily |
| Trending audio and sound effects | Popular dialogue, sound cues, music, timing of audio jokes, edit grammar, and platform-specific commercial availability | Daily |
| Gaming culture and Roblox | Ranked stereotypes, overconfident opponents, starter-character challenges, friend dynamics and popular game/community references | Every 2–3 days |
| Own content results | Which cultural references, joke structures, voice styles and editing choices work for Slugshot; production effort and player acquisition where measurable | Daily after posting |

Cadences are proposals for the campaign, not active automations or mandatory quotas. Research both new and recurring formats. Prefer a public evidence sample spanning unrelated creators and relevant audience communities over a personalised feed, isolated viral post or AI assumption. Use TikTok Creative Center, Know Your Meme, public creator pages and public trend trackers (e.g. Trendhaus); use existing research tools only when useful. Verify links, dates, audio identity and regional relevance. Do not infer audience demographics from an accent or a single clip.

### Cultural reference log — reusable entry schema

| Field | Record |
|---|---|
| Reference ID / family | Stable ID, meme or format name, and category |
| Source | Platform, creator, original or earliest known example, URLs, and sample coverage |
| Timing | Published dates, observed dates, first seen, last checked, recheck date |
| Observable evidence | Views/likes/comments/shares when visible, multiple creators, comparable age, repeat observations; unknown fields remain blank |
| Trend state | Emerging / active / saturated / declining / evergreen / uncertain; explain evidence and audience fit |
| Cultural meaning | What knowledge the viewer needs, the joke's social context, and why it might resonate |
| Creative grammar | Setup, expectation, reversal, payoff, roles, visual framing, voice/dialect/delivery, audio and edit timing |
| Slugshot adaptation | Original scenario, approved characters, narrative job, required assets, how the game appears naturally |
| Rights and authenticity | Original/licensed audio and visuals, commercial platform availability, consent where needed, disclosure and non-endorsement checks |
| Experiment | One hypothesis, comparable alternative, intended outcome, estimated production effort, experiment ID and status |

Store references here as evidence is collected, deduplicate by post ID, and update dated observations rather than silently replacing counts. Use A/B/C/D/S evidence labels from our toolkit (official guidance, published research, creator practice/public cases, hypothesis, Slugshot results). Separate observed facts from interpretations. Apply YouTube API restrictions to API-derived data; follow the bank's existing data-handling rules. Public counts are not proof of retention, humour, demographics or game conversion.

### Creative starting points — hypotheses, not verified trends

| Concept family | Original Slugshot example | What to test |
|---|---|---|
| Streamer-inspired skit | An original overconfident, loud opponent reacts absurdly when a starter slug beats them in a verified match or a clearly fictional story; the owner mentioned IShowSpeed's barking/reactions as an illustrative cultural reference | Recognisable reaction grammar versus a generic angry opponent |
| Anime-inspired scene | Two formidable slugs receive a dramatic original shonen-style face-off, only for Floppy to interrupt it with a tiny hop | Familiar anime tension plus anticlimax versus a plain duel opening |
| Unexpected voiceover | An original scene narrated with authentic Jamaican Patwa, Nigerian English or another specific voice style; alternatively, a solemn nature-documentary narrator treating an ordinary slug as a great warrior | Voice and delivery versus ordinary narration, holding the scenario constant |
| Ironic aura farming | Floppy gets an elaborate cinematic entrance before an unimpressive hop (real recovery footage only if verified; otherwise fictional and labelled) | Contrast between grandeur and reality versus a conventional character introduction |
| Rule-world story | A fictional society values powerful slugs; the underdog persists with Floppy | Rule, consequence and twist versus direct gameplay framing |
| Character talent skit | A slug takes a disastrous karaoke or talent performance extremely seriously | Character-driven absurdity versus generic reaction humour |

Huss / In This Town has an existing dated sample in the Public trend tracking section. CaseOh karaoke, exaggerated angry reactions and other references discussed in the 24 November conversation are research leads, not verified performance claims in this section. Recheck their relevance near launch. Never hardcode temporary memes as permanent editing rules. Do not assume an accent or reference is intrinsically funny, or that popularity will translate to Slugshot players.

### Creative and production safeguards

- Build the joke from the situation, personality, timing and contrast; a cultural reference should add meaning rather than substitute for a payoff. Be specific about dialect and use natural, respectful delivery; do not make a nationality or ethnicity the punchline. Prefer consenting performers or appropriately licensed authentic voices where needed.
- Borrow the format grammar or broad tropes, not someone else's exact edit, copyrighted footage, music, character design, dialogue or distinctive scene wholesale. Use original slug characters and original dialogue. Avoid impersonating real streamers, cloning voices without consent, implying endorsements or attributing fabricated quotes. For literal references, assess rights and context before commercial use.
- Keep Slugshot canon and actual gameplay separate from fiction. Verify current mechanics, use real gameplay for feature claims, label fictional and synthetic scenes as needed. Floppy never transforms in canon. No "play now" until available.
- Choose sound effects and voice per joke; don't force a generic narrator or the same editing template into every skit. Trending audio must be cleared for commercial use on each platform; original/appropriately licensed audio only in cross-platform masters. Leave acquisition and voice testing to production preparation.
- Entertainment-first does not mean forgetting the game: make Slugshot characters/world memorable, and use appropriate game identification and a small CTA when it serves the concept. Test both reach and eventual player acquisition. Avoid forced meme references and unnecessary sales pressure.

### Handoff and learning loop

1. **ChatGPT:** discover cultural references, inspect representative examples, explain their joke mechanism and audience fit, propose original Slugshot adaptations, and write an approved script/beat plan. Record evidence and one testable hypothesis per variant.
2. **Gemini / Flow:** follow the brief's character references, visual performance, camera, reaction and timing directions; preserve design identity. Use real footage for gameplay and label generated fictional scenes.
3. **Claude Code:** use the supplied cultural brief and existing editing skill for cuts, zooms, comic timing, captions, voice, audio and scene assembly. Render variants and run technical checks. Do not treat a generic editing rule as proof a specific meme is funny.
4. **Owner:** approve authenticity, entertainment value, rights, visual quality, and publication. Gemini can provide a first-viewer critique, not an audience verdict.
5. **Results:** record platform-specific metrics and production minutes by experiment ID; compare similar posts and test alternative versions with one meaningful change where practical. Use repeated Slugshot results to refine cultural and creative hypotheses. No Slugshot results exist yet.

Each approved creative brief should include reference ID and date, source/evidence status, why the reference fits, original joke/setup/payoff, visual directions and character roles, voice/delivery, sound cue/timing, asset and rights requirements, fiction/gameplay status, test variant, and success metric. Claude should receive a fresh brief instead of having temporary references permanently added to its skill.

**Roadmap placement:** establish cultural research instructions and reusable brief format during ChatGPT configuration (Stage 3); define the transfer to Gemini and Claude during shared workflow (Stage 4); run actual reference research, voice/asset tests and sample edits during production preparation and campaign (Stages 6–7). Continue to Stage 2 Gemini now without reopening Claude infrastructure. No active monitoring schedule has been created by this decision.

## English and Spanish campaign — core audience strategy

Owner decision, 24 November 2026: operate distinct English and Spanish-language social accounts. The owner believes Slugterra has a particularly large Spanish-speaking audience; its relative size remains a research question, not an established audience ranking. WildBrain's [2026 distribution partnership announcement](https://www.wildbrain.com/trade-news/banijay-kids-family-and-wildbrain-expand-partnership-to-share-youtube-content) explicitly includes Slugterra in Latin American Spanish as well as English, and its [Spain-specific YouTube upload](https://www.youtube.com/watch?v=dPSlRI1hG0c) confirms separate Spanish-market distribution. The series is known as Bajoterra in Latin America and Slugterra in Spain ([Spanish title reference](https://es.wikipedia.org/wiki/Slugterra)). These are useful discovery signals, not proof of audience share or Slugshot demand. Research both names to understand the fandom, without implying that Slugshot is an official adaptation or using third-party characters, branding, footage or audio without appropriate rights.

### Two language streams, one production system

- Separate English and Spanish accounts across TikTok, Shorts and Reels where practical (six accounts if all three platforms are used for both languages). Keep the Slugshot brand and game names consistent; decide account handles later.
- Reuse clean gameplay, Flow scenes, visual effects and edit structures wherever the joke and timing translate. Localise narration, captions, on-screen text, hooks, descriptions, calls to action, audio and posting schedule. Change a joke or whole scene when the cultural reference does not travel.
- Start by testing broadly understandable Latin American Spanish while researching Spain separately; this is a hypothesis, not a decision to exclude European Spanish. Test region-specific language, voices and humour where evidence warrants. Avoid treating Spanish-speaking audiences as a single cultural group.
- Preserve natural spoken rhythm, comedic intent and character personality instead of translating word-for-word. Use natural Spanish writing and native/fluent reviewer checks where feasible, especially for slang and dialect. Keep an approved bilingual terminology glossary for game UI, ability names and recurring characters; do not rename original characters casually.
- Keep separate English/Spanish scripts and localised audio/captions, referencing the same concept ID. Adjust scene timings to fit each language's spoken delivery; do not simply replace subtitles over incompatible timing. Use the existing scene-marked script and assemble interfaces rather than building a second pipeline.

### Spanish cultural intelligence — independent research stream

Research Spanish-language Roblox, anime, streamer, meme, music and gaming culture with the same importance as English-language cultural intelligence. Look at Spain and Latin American markets (e.g. Mexico, Argentina, Colombia, Chile) as distinct discovery pools, not a presumed ranking. Use country/language filters where available, search in natural Spanish, and maintain separate creator watchlists. Use Slugterra/Bajoterra fandom search terms for audience discovery, not deceptive affiliation. Investigate creators, sounds, slang, catchphrases, regional jokes, visual trends and engagement context; do not assume an English trend has Spanish traction. Apply the existing cultural reference schema with `language`, `region`, `source_locale`, `localisation_notes` and `cross_language_fit` fields. Record whether a reference is broadly shared or region-specific, and validate with multiple independent examples where possible. Run original Spanish-first creative experiments alongside adapted English concepts; successful Spanish ideas can be adapted into English in reverse.

### Responsibilities and technical work (deferred to relevant stages)

| Environment | Bilingual responsibility |
|---|---|
| ChatGPT | Independent English/Spanish research, native-sounding scripts, translation/localisation, terminology, hooks and regional humour. |
| Gemini / Flow | Reusable language-neutral visual assets; region-appropriate scene concepts, spoken delivery only if supported and reviewed; review Spanish edits for clarity and character consistency. |
| Claude Code | Localised narration import/generation, subtitle timing, on-screen text, edits and export variants. Current documented Whisper `base.en` is English-only; later test a multilingual Whisper model or equivalent existing capability for Spanish. Spanish Kokoro voice quality/support and glossary handling are unverified; test or use recorded narration before committing. |
| Owner / fluent reviewer | Check authenticity, regional slang, pronunciation, rights, final edit and game facts. |

No new software or subscriptions required at this point. Stage 2: specify language-neutral scene generation and bilingual review requirements. Stage 3: establish localisation instructions and separate cultural discovery workflows. Stage 4: agree language/locale naming and paired handoffs. Stage 6: validate Spanish transcription, narration, captions, timing and character-name pronunciation with real test assets. These do not reopen Claude's completed infrastructure phase. Game localisation (UI, tutorial, store/experience description and player-facing text) is a separate game-development dependency worth checking before Spanish traffic is acquired; no claim that the game is already translated.

### Measurement and production volume

Keep each account and upload separate in analytics. Add language, intended region/locale, account, shared concept/experiment ID, adaptation type (translated, culturally adapted, or original), production minutes and platform-specific results to the future content log. Compare performance within language/platform first, using appropriately permitted metrics and similarly aged posts. Track retention, shares, follows and eventually language/account-specific Roblox Share Links where available. Avoid assuming a regional audience from language alone; use first-party geography data once available. Research relative fandom demand and acquisition potential before selecting the final market allocation.

The earlier target of 5–7 distinct edits per day is a planning hypothesis, not a commitment to produce 5–7 entirely new videos per language. If all 5–7 concepts are localised into two versions and cross-posted to three platforms, that would be 10–14 masters and 30–42 uploads per day (210–294 per week). Start with a smaller paired pilot; measure additional localisation effort, voice and caption quality and regional results before scaling. Reuse footage rather than doubling visual generation. Spanish-first jokes may justify their own footage.

## Slugshot experiments

| Format | Working hook or setup | What to capture | Status |
|---|---|---|---|
| Starter-slug challenge | “He brought his best slug. I brought Floppy.” | Match point and the whole exchange | Idea |
| One mechanic wins the round | “He thought that wall would save him.” | Enemy taking cover, wall breaking, outcome | Idea |
| Friend POV | “My duo said ‘trust me’ with one shot left.” | Voice line and both players' perspectives | Idea |
| Pick a slug | “Inferno or Rammstone here?” | Same decision point and both possible outcomes | Idea |
| In My World story | “Everyone gets a starter slug. My brother told me to swap mine before my first duel.” | Show the rule in action and settle it with a duel | Idea |
| Slug dance | Floppy keeps dancing through Inferno's transformation | Straight dance and punchline variants | Idea |
| Direct game pitch | “This Roblox game lets you shoot creatures that transform mid-fight.” | A readable transformation during a real fight and a Slugshot end card | Idea |

## Slugshot results

Suggested test cadence: 5–7 short edits a day, cross-posted to TikTok, Shorts, and Reels. This is a campaign planning assumption and can change with capture and editing capacity.

| Edit / hook | Platform | Published URL | Posted | 24h views | 7d views | Watch metric | Shares | Link-attributed new players | Notes |
|---|---|---|---|---:|---:|---|---:|---:|---|
| | | | | | | | | | |

Use the watch metric available for the platform and label it. For example, Shorts shows [engaged views and average percentage viewed](https://support.google.com/youtube/answer/12220281?hl=en-uk). Use [Roblox Share Links](https://create.roblox.com/docs/production/analytics/acquisition) for acquisition by platform where a link can be placed, and record new players at the level the link measures. Keep player totals blank until we have data.

## AI-assisted production

Updated workflow, 24 November 2026. A dedicated Claude Code marketing account now operates a separate local `slugshot-marketing` repository. ChatGPT remains the research and creative workspace; Gemini/Flow is the visual generation and footage analysis workspace. Codex and the game-development accounts remain separate. Keep scripts, evidence and results in this bank; the local repository holds production assets, jobs and tools. No Antigravity, extra subscriptions, paid API calls without approval, or custom marketing agent.

| Tool | Job | Handoff |
|---|---|---|
| ChatGPT | Research comparable posts and wider internet culture (memes, anime, streamers, voices and audio), check source metrics, draft hooks and dialogue, plan shots, and analyse Slugshot's analytics exports. | A brief with alternate openings, the payoff, the footage needed and the metric we want to test. |
| Roblox Studio and your recorder | Batch-record a few real matches and any staged shots the brief calls for. Start with the existing capture setup. | Real gameplay and any repeatable character or camera shots. |
| Gemini | Review a batch of match recordings and suggest timestamped clutches, fails and funny reactions. Verify the timestamps during editing. | Candidate clip windows with the setup, payoff and a suggested opening. |
| Google Flow | Turn original slug renders into short dance, reaction and story shots. Use matching reference images between shots. | Approved 9:16 cutaways that preserve the character's silhouette, colours and markings. |
| Claude Code | Edit, assemble, caption, narrate, mix audio, render variants, perform technical QC and collect public statistics. | Finished local MP4s, review clips, logs and permitted analytics exports. |
| Owner | Approve concepts, footage selection, creative quality, rights and publication. | Feedback and actual platform results. |

### First production test

Capture one Floppy-versus-favourite-slug duel. Edit the same gameplay as a challenge and as a direct introduction to how Slugshot works. Try a third edit that adds a short character shot to frame the match as a story. Use one clean master per edit and make alternate crops or openings when needed. Log production minutes and generation attempts along with performance so we can tell whether an AI-assisted edit earns its extra effort.

Historical reference only; re-check during Gemini setup. Flow's published Google AI Pro allowance was 1,000 credits per month on 21 November 2026. Omni Flash 1.2 charges one credit per second at 360p and three at 720p for the first 10 seconds. A six-second draft costs six credits at 360p, with Google listing zero upscale credits for clips up to ten seconds on Pro. Check the preview's silhouette and timing before rendering more takes.

Sources: [Flow model support](https://support.google.com/flow/answer/16352836?hl=en) · [Flow credits](https://support.google.com/flow/answer/16526234?hl=en) · [Flow references](https://support.google.com/flow/answer/16353334?co=GENIE.Platform%3DDesktop&hl=en) · [Gemini video uploads](https://support.google.com/gemini/answer/14903178?hl=en-GB)

## Decisions

- First shoot candidates: one Floppy underdog match, one cover-break finish (only once the mechanic is verified in the current build), and one slug dance with a punchline.
- Exact game name on-screen. Use release timing before launch and a play/search call to action once the game is available.
- Prioritise clips that show a full gameplay payoff. Use story and character clips to test another route to attention.


## Infrastructure record — 24 November 2026

### Roadmap and decisions

Historical setup snapshot below; the updated eight-stage roadmap and latest validation status at the end of this bank supersede its stage numbering and status.

| Stage | Status |
|---|---|
| 1. Claude Code local infrastructure | Complete, reported 13/13 smoke checks; API key rotation/restriction still outstanding unless owner confirms |
| 2. Gemini Pro and Flow | Next: configure persistent instructions, character consistency, footage analysis, visual prompts and video review |
| 3. ChatGPT | Partially configured: research/creative resources acquired; verify scripting skill, establish English/Spanish cultural intelligence, localisation and finalise creative workflow |
| 4. Shared workflow | Proposed manual file handoffs; standardise actual input/output contracts including language variants and assess only useful automation |
| 5. Dashboard | Not started; lightweight interface around working tools, not a new AI agent |
| 6. Production preparation | Deferred: real footage, voice, licensed audio, brand fonts, asset packs, real-world tests |
| 7. Campaign | Not started; no Slugshot posting results yet |

### Claude toolkit

Owner-supplied reports: initial Phase 2 commit `b95f08b`, creative editing and multi-scene refinement `cb709d4`, final permissions and documentation adjustment `ad25094`. The latest report states 13/13 smoke checks passed. These are reported results, not independently reproduced by ChatGPT. Tests used stand-ins, not real gameplay or genuine Flow output.

- Installed/reused: FFmpeg, Whisper, Kokoro-82M (separate Python environment), Remotion, MakeMyClip, OBS Studio, Kdenlive, Git, Python and Node. Exact pins in toolkit INVENTORY. No additional installation planned.
- Skills: official `remotion-best-practices` and project `slugshot-video-editing` (six references). Evidence labels A official, B published research, C creator practice, D hypotheses, S Slugshot results (none yet). Actual creative results can refine hypotheses, not override rights, truth or policy requirements.
- Seven format presets: PVP, PROMO, CHOICE, WORLD, SKIT, AISCENE, TEST. Single/multi-scene edits, animated captions, glossary correction, narration, audio mixing, variants, QC and frame strips available. Human review is required; timing is approximate and crossfades are not implemented.
- Commands run via `.\ss`: `doctor`, `smoke`, `import`, `voice`, `audio tidy/mix`, `caption`, `fixcaps`, `vertical`, `render`, `batch`, `assemble`, `candidates`, `sheet`, `qc`, `studio`, `clip`, `yt`, `export`. See COMMANDS in the toolkit pack for exact arguments.
- Game repo `../slugshot` may be read, inspected and copied; ask before changing its files, builds or Git state unless explicitly instructed. Restart Claude Code or reload settings for updated permissions. Credentials excluded from Git; direct MakeMyClip CLI blocked; destructive commands require confirmation. MCP approval is optional. No paid request or billing change without owner approval.

### Analytics and security

YouTube collector live-tested; key rotation and restriction to YouTube Data API v3 still unconfirmed after exposure. Keep the replacement only in ignored `.env`; `.env.example` contains placeholders. Per-video snapshots and permitted per-video arithmetic, 30-day retention handling; unapproved custom competitor scores disabled. TikTok and Instagram currently use validated manual CSV imports. Own-channel retention and Roblox acquisition await channels and published game.

Final owner instruction restored YouTube reports to `exports/share/` for internal AI analysis. This records owner permission, not independent confirmation of YouTube's terms for the precise third-party AI transfer. Review applicable restrictions before sending API-derived data to external AI services; do not publish it or retain API data beyond applicable rules. No support inquiry is required for infrastructure completion. Do not use this bank to permanently store raw API snapshots.

### Existing handoff contracts

- ChatGPT scripts: `jobs/scripts/*.md`; `[SCENE N - direction]` begins a scene, `#` lines are notes, other nonblank lines are spoken. `ss assemble` accepts JSON edit files with video/image/card scenes, script or narration, timing and audio options. `ss batch` accepts variant jobs. Actual examples in the combined toolkit pack.
- Gemini gameplay analysis: CSV header exactly `start,end,what_happens,why_a_stranger_could_care,emotion,best_format,hook_idea,payoff,confidence,potential_misinterpretation`. Time in M:SS or seconds; UNCERTAIN where appropriate. Analyse chunks; timestamp origin must match the input clip. Save CSV beside the recording and run `ss candidates` with recording and CSV. Human verifies `verified`, `keep`, `true_start`, `true_end` in index.csv; Gemini's descriptions are not proof of mechanics.
- Flow clips/stills: save approved MP4/PNG into `media/flow/`, named by scene. Verify silhouette, proportions, face and colours against approved reference renders; label generated scenes, never imply they are real gameplay. Use `ss assemble` or AISCENE preset. No direct Google connection currently exists; manual transfers are sufficient initially. Verify current regional features, credits and privacy settings in Gemini phase.
- Review: technical QC, Claude's creative editing skill, optional Gemini first-viewer pass, owner approval. Only publish after rights, disclosures and mobile viewing checks. No auto-publishing configured.

### Game truth snapshot (not permanent canon)

Source: Claude's `docs/game-truth.md`, checked at game commit `08fee46` (23 Nov 2026). Re-check current `status.md` and actual build before scripting or advertising mechanics. Slugshot is a Roblox creature-combat blaster game; not published at the snapshot. Floppy never transforms and has no abilities. Aquabeek Crashwave owner-approved; Mistbank rejected at snapshot. Inferno's Dragon's Breath/Fire Curtain built in range and being tuned. Other transformations, abilities and PvP require verified capture; Rammstone breaking cover/map not verified. Roster counts are plans, not promises. Fictional rules must be clearly labelled. Visual direction: Living Comic-Book Fantasy, bold charcoal ink, calm bases, selective glow.

### Deferred production checklist

Real OBS round and end-to-end test; clean approved slug references (front, three-quarter and profile); genuine Flow generation and assembly; listen to Kokoro and choose AI or human narration; acquire commercially licensed music and sound effects with `assets/LICENSES.csv`; choose brand fonts and end card; channel creation, own-channel analytics, Roblox share-link tracking after publication. These are not infrastructure blockers.

### Source registry

Keep the updated bank as the living decisions and research index, not a substitute for full source documents. Project source snapshots must be replaced manually when updated unless the product explicitly supports synchronisation.

| Source | Purpose |
|---|---|
| `Slugshot AI-Assisted Marketing Production System.pdf` | Foundational research and master prompts |
| `Slugshot-Claude-Toolkit-Docs.md` (expanded 24 Nov, final setup `ad25094`) | Full command reference, integration specification, inventory, creative editing skill and six references, game truth, deferred checklist, CLAUDE.md and three example jobs (16 distinct source documents) |
| `repo.txt` | Game repository pointer |
| `Slugshot-Marketing-Bank.md` | This living bank; prior research, hypotheses, decisions, roadmap and results |

The combined toolkit supersedes the earlier shorter toolkit pack. Individual uploads and ZIP are duplicate/reference archives, not necessary as separate Project Sources. Keep Claude's local copy of the bank aligned by supplying the updated file when needed; no automatic synchronisation has been established.


## Creator research infrastructure — earlier decision and test history, 24 November 2026

Historical snapshot: current implementation and automation-first policy are at the top of this bank.

**Owner decision following live plugin test:** vidIQ is useful but too credit-intensive for routine research. The small controlled test consumed 50 of 150 monthly credits (nine substantive calls); balance checked at 100 remaining, renewal 24 December. Do not use vidIQ as the main data pipeline. Use official APIs and free native exports for routine collection; reserve vidIQ for high-value concept/hook/format searches, selective breakout discovery and emerging audio that cannot easily be reproduced. Agree further credit spending with the owner. No new paid subscriptions.

Detailed dated evidence, queries, results, references, limitations and cost ledger: `Slugshot-Creator-Research-Validation.md` (24 Nov). This report preserves the test findings, not a permanent raw API-statistics archive. Follow each provider's retention/refresh, transfer and metric rules. The earlier infrastructure-audit summary is a planning input, not evidence of implemented additional APIs.

- vidIQ: English/Spanish Shorts and TikTok/Reels concept searches worked, including creative premise, first-three-second hook and format descriptions. Historical YouTube stats returned dated per-video velocity; audio search returned usage-growth signals. Weaknesses: 5 credits per discovery/history call, 10 for a video analysis, language noise, incomplete recent-velocity field, uncertain provider metric provenance and inferred audience demographics, no representative concept-level growth measure. Video breakdown worked in Spanish but not independently verified. Prefer Gemini for authorised video analysis.
- TinyFish: public search useful for dated meme origins and contextual references. Instagram page yielded likes/comments/date but not views; YouTube metadata without views; TikTok page error; Creative Center navigation only; Google Trends partial data/chart error. Not reliable bulk collection. Interactive browser untested. No measured usage balance.
- Huss specific joke, In This Town format, associated audio and broad Roblox animation are distinct entities with distinct lifecycles. The owner's saturation concern is a hypothesis; one successful or declining video, derivative templates or growing sound cannot establish a concept trend. Gather repeated dated observations, independent creator adoption, normal/failed examples and qualitative fatigue evidence. Use emerging/accelerating/established/saturated/declining/unknown labels only with explicit supporting evidence.
- Data standard: source URL/ID, creator, publication time, observation UTC, query/filter, language, intended locale vs observed geography, metric name/definition, missing values, provenance (first-party measured; first-party sampled/normalised; third-party reported/estimated; qualitative interpretation), confidence, rights and retention requirements. Keep A/B/C/D/S evidence labels. Do not treat AI demographic guesses or estimates as measured data.
- Claude next: investigate Twitch Helix, Google Trends official CSV/API eligibility, improve existing YouTube regional/language searches and dated exports, investigate Meta Business Discovery eligibility and actual competitor fields. TikTok remains a genuine bulk-data gap; assess legitimate free options. No unapproved scraping, purchases, API keys in chat, or prohibited YouTube aggregation/derived scores. Rotate/restrict previously exposed YouTube key before live use unless confirmed done.
- Google Drive connected and search tested; no Slugshot files found at that test. Shared folder, approved exports, permissions and retention lifecycle remain deferred to shared workflow. No automatic synchronisation or scheduled collection established.

### Updated roadmap (supersedes historical numbering above)

| Stage | Current status |
|---|---|
| 1 Claude production toolkit | Implemented, latest report 12 PASS / 1 WARN (Kokoro punctuation round-trip), not real production validated |
| 2 Gemini / Flow | Configured, reported dry-run validation; confirm privacy/approval settings before real uploads or generation |
| 3 Roblox-native filming | Implemented at stand-in level, game isolated; real actors, sets and OBS validation deferred; strict repeatability test one pair failed |
| 4 ChatGPT creator research infrastructure | 4.1 audit completed; 4.2 Drive connected; 4.3 exploratory plugin validation completed; 4.4 Claude data collection complete (13adfd2); 4.5 methodology/skills, 4.6 foundational studies, 4.7 knowledge banks pending |
| 5 Shared workflow | Deferred; language-specific handoffs, approved export folder and access |
| 6 Dashboard | Deferred, lightweight only |
| 7 Production preparation | Real footage, animations, bilingual voice/captions, asset packs, Flow and pilot validation |
| 8 Campaign | Not started; no S-rated Slugshot results |

Earlier Claude source: `Slugshot-Claude-Toolkit-Docs.md`, generated 24 Nov from marketing commit `3cd0496`; supersedes older `ad25094` setup record. Includes Roblox-native guard, Reel runner, smoke results, API policy and deferred checklist. Game snapshot `08fee46`; do not conflate stand-in tests with production.

### Additional source registry

| Source | Purpose |
|---|---|
| `Slugshot-Creator-Research-Validation.md` | Detailed dated vidIQ/TinyFish validation, cost ledger, reference URLs, verified limitations, revised architecture and concept lifecycle method |
| Latest committed `Slugshot-Claude-Toolkit-Docs.md` (13adfd2) | Authoritative implementation snapshot for Claude and Roblox-native filming |

The existing bank remains the master strategic index; refresh Project Sources and other local snapshots manually. No automated sync implied.

## Stage 4.5.3 implementation (Claude, 24 Nov 2026), local addendum

Claude implemented the research intelligence layer in the marketing repo:
- the `slugshot-research-analysis` skill;
- `ss analyze` (intake QC, statistics with denominators, same-item changes, sensitivity, trend dimensions with a lifecycle proposal, change points, outcome-blind coding with codebook v1.0 (now v1.1, with v1.0 archived; see docs/chatgpt-research-skills-v1.1.md), Wikidata/GDELT context);
- `ss evidence` (ledger + validator, EvidenceGuard V0.1 export);
- research templates;
- four pinned upstream skills: verifying-bibliography, surveying-literature, synthesis-fact-checking, hypothesis-generation.

Results:
- Tests: 51 offline research tests pass; the research smoke test passes; full regression in reports/smoke-test.md.
- Worked example ledger EXAMPLE-HUSS-SLUGTERRA (real data): Huss lifecycle unknown from one snapshot; es.wikipedia Slugterra attention change point 25 Sep 2026, median 41 → 26 daily views. Suggestive, single family.

Handoff: docs/chatgpt-handoff-4.5.3.md. Next: Stage 4.5.4 query families and watchlists (ChatGPT), then 4.5.5 validation through real tasks.
