# Inventory and capability status

Last updated 2026-11-26 (production quality pass: docs/production-quality.md). Infrastructure phase complete; production work is in [production quality and next steps](production-quality.md). Command details: [COMMANDS.md](COMMANDS.md).

## Software

| Item | Version | Location | How it's used |
|---|---|---|---|
| Git | 2.55.0 | system | version control |
| Python | 3.13.15 | system; venvs `.venv` and `.venv-tts` | scripts |
| openai-whisper | 20250625 (torch 2.15 CPU) | `.venv` (`requirements.txt`) | `ss caption` |
| ruptures + scipy | 1.1.10 + 1.18.1 (BSD) | `.venv` (`requirements.txt`) | `ss analyze changepoints` |
| Qwen3-TTS 1.7B VoiceDesign + Base | qwen-tts 0.1.1, torch 2.8.0+cu128 (Apache-2.0) | `.venv-voicelab` (not in git; weights in the Hugging Face cache) | `ss dialogue --engine qwen`; 3.94 GiB peak VRAM on the RTX 3070 |
| kokoro-onnx + Kokoro-82M v1.0 | 0.6.1 | `.venv-tts` (`requirements-tts.txt`), `models/kokoro/` (not in git) | `ss voice` |
| demucs (htdemucs_ft) | 4.0.1 (reuses `.venv-voicelab` torch 2.8 CUDA via a .pth) | `.venv-demucs` (not in git) | music/voice separation, e.g. lifting a genre bed from under narration: `.venv-demucs/Scripts/python -m demucs --two-stems=vocals -n htdemucs_ft -o <out> <file.wav>` (added 2026-11-26) |
| Node | 24.19.0 | system | Remotion, MakeMyClip |
| FFmpeg | 9.1 full (gyan.dev) | winget `Gyan.FFmpeg` | everything media |
| OBS Studio | 32.2.2 | system | capture |
| Kdenlive | 26.08.3 | winget `KDE.Kdenlive` (per-user) | manual editing |
| Remotion | 4.0.546 (exact pin) | `node_modules` | `ss render`, `ss batch`, `ss studio` |
| MakeMyClip editor | 0.5.2 (exact pin) | `node_modules` | `ss clip`, MCP |
| DaVinci Resolve | not installed | n/a | optional; Kdenlive covers manual editing |

## Repositories (reviewed, not executed)

| Repo | Commit | Where | Why |
|---|---|---|---|
| MakeMyClip/editor | e090b42 | `vendor/makemyclip` (ignored) | source review before installing the npm package |
| remotion-dev/skills | 89c8afa | `vendor/remotion-skills` (ignored) | source of the installed Remotion skill |
| zAcherttp/roblox-reel | 4b810e9 | `roblox-native/runtime/vendor/Reel/` (tracked, MIT, unmodified) | camera takes for Roblox-native filming |
| CutsceneService | 059a60d | `vendor/` (ignored) | MIT; fallback if Reel fails, not installed |
| Motion Tools | 7ff9b0b | `vendor/` (ignored) | no licence found: deferred |
| RoPlay | b7ea47a | `vendor/` (ignored) | non-commercial licence: excluded |
| roblox-studio-agent-plugin | 57d7204 | `vendor/` (ignored) | duplicates the built-in Studio MCP: not installed |

## Claude Code skills and MCP servers (this project)

| Item | Type | File | Notes |
|---|---|---|---|
| `remotion-best-practices` | project skill | `.claude/skills/remotion-best-practices/` | official Remotion guidance, Markdown only (see `SOURCE.txt`) |
| `slugshot-roblox-production` | project skill (ours) | `.claude/skills/slugshot-roblox-production/` | Roblox-native filming: truth modes, canon, scene specs, Studio safety, capture and hand-off into `ss` |
| `slugshot-research-analysis` | project skill (ours) | `.claude/skills/slugshot-research-analysis/` | evidence-led analysis: intake, statistics, trend dimensions, outcome-blind coding, evidence ledger, literature verification routing |
| `verifying-bibliography`, `surveying-literature` (+ `_shared/scholarly`) | project skills (upstream, MIT) | `.claude/skills/` | claude-skills-research 9d990c1, path-patched to project-local; offline tests 206/207 (one POSIX-path assertion fails on Windows); live DOI check OK |
| `synthesis-fact-checking` | project skill (upstream, CC0) | `.claude/skills/` | synthesis-skills 62a0a54, Markdown only |
| `hypothesis-generation` | project skill (upstream, MIT) | `.claude/skills/` | K-Dense scientific-agent-skills c21d13b, stdlib CLIs, no network |
| `slugshot-research-operations` | project skill (ours) | `.claude/skills/slugshot-research-operations/` | runs research collection from a short instruction: intents, brief execution, Creative Center session, error handling, bundle and report, approval boundaries |
| `slugshot-video-editing` | project skill (ours) | `.claude/skills/slugshot-video-editing/` | creative editing judgement: pacing, cuts, zooms, captions, audio, format playbooks, review gates; evidence-labelled A/B/C/D/S |
| `makemyclip` | MCP server (stdio) | `.mcp.json` | 8 timeline tools; media confined to `media\` (tested). Approve it when Claude Code asks |
| Permission rules | project settings | `.claude/settings.json` | blocks reading `.env` and direct MakeMyClip CLI calls; asks before recursive deletes and destructive git commands. The game repo is readable and copyable; changes to game files need the owner's request (CLAUDE.md) |
| Roblox Studio MCP (built-in) | user-level, already present | `%LOCALAPPDATA%\Roblox\mcp.bat` | used for Roblox-native filming, **only on the marketing place**: a PreToolUse hook (`roblox-native/tools/studio_guard.py`) denies every call unless that place is the only one open and its marker matches; Roblox-service tools ask first |
| Blender, Google Drive MCPs | user-level, already present | outside this repo | not used by the toolkit (Blender evaluated 2026-11-25: deferred, see production-quality.md) |

## Capabilities

Readiness: **Tested** = runs end to end, checked by the smoke test or a recorded test. **Human approval** = works, but its creative output must be judged by a person before anything is published. **Waits on footage/channel** = can't be fully proven until real gameplay or a Slugshot channel exists.

| Capability | Command | Tested | Human approval | Waits on footage/channel |
|---|---|---|---|---|
| Tool check / smoke test | `ss doctor`, `ss smoke` | 13 toolkit, 10 research and 7 dashboard checks | n/a | n/a |
| Capture import + naming | `ss import` | yes (MKV stand-in) | n/a | first real OBS session |
| AI narration (Kokoro) | `ss voice`, `assemble` with `script` | yes | **voice quality and energy** | n/a |
| Voice clean-up, ducking, SFX | `ss audio tidy/mix` | yes | **music/SFX choice and feel** | licensed music/SFX files |
| Transcription + term correction | `ss caption`, `ss fixcaps` | yes | read every `.srt` | real voice recordings |
| Single-clip render + presets | `ss render`, `ss vertical` | yes | **phone review** | real gameplay |
| Variants | `ss batch` | yes (3 variants) | which variant to post | real gameplay |
| Multi-scene assembly (MP4, MKV, PNG, WAV, script, cards) | `ss assemble` | yes (5 scenes, script-synced) | **pacing, story, humour** | Flow clips, real gameplay |
| Gemini timestamps to review clips | `ss candidates` | yes (sample CSV) | person picks moments | real Gemini output on a real session |
| Frame sheet for review | `ss sheet` | yes | n/a | n/a |
| Technical QC | `ss qc` (automatic) | yes | n/a | n/a |
| Creative editing judgement | `slugshot-video-editing` skill | used once (see `reports/skill-review-2026-11-24.md`) | **always: funny, energy, clarity to a stranger** | rules become S-rated only with platform results |
| Template tweaking | `ss studio` | launches | n/a | n/a |
| Agent timeline editing | `ss clip`, MCP | yes (confinement) | n/a | n/a |
| YouTube public stats | `ss yt` | yes (live, incl. Stage 4.4 chart + Shorts check) | n/a | n/a |
| YouTube bilingual searches, saved query sets, regional charts, creator uploads, comments, quota budget | `ss yt sweep/chart/creators/comments/quota` | live (bounded tests 2026-11-24: sweep, 2-page search, creators, comments, chart, Shorts check, quota reconciliation) | n/a | ChatGPT's real query sets and creator watchlists |
| Wikipedia page views (en/es, redirects) | `ss wiki` | yes (live) | n/a | n/a |
| Google Trending Now RSS (7 markets) | `ss trends rss` | yes (live) | n/a | n/a |
| Google Trends Explore CSV import | `ss trends import` | sample files only | n/a | **your first real Explore download** |
| Twitch clips/streams | `ss twitch` | yes (live: clips, streams, recheck) | n/a | owner check of onward transfer before `share_exports` |
| Roblox experience stats (legacy, experimental) | `ss rbx` | yes (live) | n/a | n/a |
| Public observations import (Creative Center, TikTok, Instagram, vidIQ, TinyFish) + Creative Center link list and paste parser | `ss observe` | yes (fixtures + 24 Nov Creative Center figures); oEmbed live; paste parser on fake samples only (confirm with a real paste) | n/a | n/a |
| Research housekeeping | `ss research status/prune/runs` | yes | n/a | n/a |
| Research analysis (intake QC, stats, repeat, sensitivity, trend dimensions, change points, blind coding, Wikidata/GDELT) | `ss analyze` | yes (24 offline tests; live: intake on real bundles, 11-year Wikipedia change points, Wikidata; GDELT live once, then rate-limited) | coding and interpretation | n/a (first real coded sample: the 24 Nov pilot) |
| Watchlist verification + systematic creator discovery + deterministic sampling | `ss research verify-watchlists/discover-creators`, `ss analyze sample` | yes (live: 30 channels, 7 broadcasters, 23 wiki titles; pilot sample 20/20, Gemini playback joined under v1.0 and v1.1; families-1.1, codebook 1.1) | ChatGPT owns query families and strata | n/a (Stage 4.5.5 closed; independent human spot-check deferred until a production decision needs it) |
| Coding packets for Gemini or a person (all codes, five beats, access vocabulary, from the codebook) | `ss analyze coding-packet` | yes (offline test; pilot recode and spot-check packets written) | a person for the independent spot-check (deferred) | n/a (v1.1 recode integrated) |
| Evidence ledger + validator + EvidenceGuard export | `ss evidence` | yes (traps suite; real worked ledger EXAMPLE-HUSS-SLUGTERRA valid inside a bundle) | AI/owner review of REVIEW items | n/a |
| Composio (OAuth broker, read-only) | `ss composio status/test/audit` | yes (key accepted; 1 no-auth read-only tool PASS; audit of 15 toolkits) | owner OAuth approval per account (Instagram, Drive/Sheets); TikTok needs its own developer app | 0 connected accounts |
| One-instruction research operations (skill `slugshot-research-operations`; `ss research collect --profile daily/spanish/refresh`, `ss research bundle`) | `ss research` | yes (live end-to-end: spanish profile, 15 steps OK, bundle of 8 datasets) | n/a | n/a ('daily', 'spanish' and fam-* sets in place) |
| Guided Creative Center session (opens pages; imports on Ctrl+A, Ctrl+C) | `ss observe cc-session` | loop tested with simulated copies | n/a | **first real session** confirms the page layout |
| TikTok Discovery API, Instagram Business Discovery, Google Trends API | none | no | n/a | company identity (TikTok); Slugshot Instagram account; alpha approval |
| TikTok genre bank via Apify (`clockworks/tiktok-scraper`: search, hashtags, creator back catalogues, subtitles, permitted downloads) | `research/tiktok-genre/*.py` (scripts, not `ss`) | yes (live 2026-11-26: 631 in-format posts, TOP/MID/FLOP-50 with transcripts) | Apify use approved for this toolkit's TikTok collection | Apify Free credit: about $0.60 left until 25 Dec |
| Vertex AI for Gemini TTS | none | key, service account and role work (2026-11-26) | n/a | **not used**: on Vertex, `gemini-3.8-flash-tts` speaks delivery directions aloud (no separate style field); retest later |
| YouTube reports | `ss yt report` | yes | n/a | written to `exports/share/` for ChatGPT (sharing approved by the owner) |
| Platform metrics for ChatGPT | `ss export` | yes (validation) | n/a | **first posts** |
| Personal dashboard: Overview (+ views, followers and account drill-downs), Content (Concepts, Published), Publish, Roblox, Settings; redesigned 2026-11-25 | `ss dash` / Desktop shortcut | yes: 33 + 23 + 14 unit tests, `ss smoke --dashboard`, screenshots in three appearances and phone width, live empty states | owner reads; approves posts | Buffer metrics, checkpoints and comparisons need real posts |
| Own-channel analytics: YouTube Analytics API (OAuth), TikTok Display API (OAuth), Buffer API (TikTok + Instagram post metrics) | `ss dash sync` | **live-validated 2026-11-25** for yt-en, yt-es, tt-en, tt-es and Buffer's 3 channels (no posts yet, so only followers are live values); Instagram API connector fixture-tested, deferred | owner OAuth / Buffer key | first posts |
| Roblox Analytics Query API (players, new players, D1/D7/D30, revenue, payers, acquisition source) + public games API | `ss dash sync` | Analytics: fixture-tested; public games connector live-validated on a public experience | API key with `universe.analytics:read` | **published game** |
| Roblox share links, TikTok Studio, Instagram app and YouTube Studio figures | `ss dash import` / Settings | yes (validation, dedup, row errors) | owner copies figures | first posts / published game |
| Campaign snapshot for ChatGPT/Claude/Gemini (safe-to-share, credential scan) | `ss dash export` | yes | owner uploads | n/a |
| Activation (onboarding funnel) | none | proposal only ([activation-events-proposal.md](archive/dashboard/activation-events-proposal.md)) | **owner approval (game change)** | published game |
| Foundational research and knowledge banks (milestone 1) | literature skills, `ss evidence` | built: six Gemini reports audited and Stage 4.7 knowledge banks built 2026-11-25 (1,037 entries, 0 validation errors) | owner approves individual entries; live evidence comes from producing videos | audit outputs local in `data/local/research/stage-4.6/`; export `exports/share/research-4.6-audit/`; ledger `AUDIT-STAGE46-PLATFORM` |
| External research-report audit (extract IDs/DOIs/URLs, dedupe, Crossref DOI check, URL reachability, figure checks in cited sources, claim register) | `python scripts/research_audit.py all`; `… claims --checks FILE`; `python scripts/research_audit_register.py` | yes (run on the Stage 4.6 reports, 25 Nov 2026) | figure checks are text matches; meaning needs review | sources read from git-ignored `research/sources/` |
| Knowledge banks (16 banks, validator, filters, briefs, export; dashboard learning loop and export) | `ss kb …` | yes (21 tests in `tests.test_knowledge`; real banks validate) | owner approval per entry (`approved`) | `docs/knowledge-banks.md` |
| Audience sentiment coding | `ss sentiment …` | yes: fixture-tested and one live YouTube sample coded (2026-11-25) | Claude codes; ambiguous items go to a person | owner confirmed the YouTube derived-metrics approval (2026-11-25); reference field to fill in; `docs/audience-sentiment.md` |
| Publishing (Publish page: drafts, per-platform text, preview, checks, owner approval by typed handle; YouTube resumable upload, TikTok inbox and Direct Post, Instagram container; manual packages; links posts to versions and experiments) | `ss publish …` (drafts only) / dashboard | fixture-tested (27 tests in `tests.test_publish`); connections live-validated; Cloudinary hosting and Buffer draft creation live-validated; **no live post yet** (six test jobs await the owner) | **owner approves every upload in the dashboard**; public posting on, reveal lock on (game unnamed, owner confirms each public video) | upload permissions per account ([credentials-checklist.md](dashboard/credentials-checklist.md)); Instagram local upload not offered by Instagram Login ([publishing.md](dashboard/publishing.md)) |
| Isolated Roblox marketing place | `ss roblox build/rebuild/audit` | yes (audit, live Studio session) | n/a | n/a |
| Studio target guard | hook, `ss roblox guard` | yes (live deny and allow) | n/a | n/a |
| Scene specs + runner (stand-ins) | `ss roblox validate`, `Scene.runJson` | yes (smoke scene, 6 takes) | **performance, humour, look** | real animations, sets, slug rigs |
| Take repeatability | `ss roblox compare` | yes (one PASS; one at 56 ms cuts / 80 ms cues vs a 50 ms target) | n/a | n/a |
| Real slug actors with acting (SlugIdle/FloppyFace, mouths from dialogue, eyelines, size-aware cameras) | scene specs `kind: slug` | **real assets** (Floppy, Rammstone filmed 2026-11-25) | **performance, look** | n/a |
| Human actors (R6 like the game's players: gaits, gestures and emotes, drawn faces that talk, blaster aim and fire, holding slugs) | scene specs `kind: human` | **real assets** (humans_demo filmed 2026-11-26, 871/871 frames) | **look, performance, humour** | n/a |
| Film mode: deterministic, frame-stamped, chunked, native 1080x1920 at 30 fps | `Scene.film`, `ss roblox film` | **real assets**: 4 takes, 0 repeated frames | n/a | n/a |
| Character dialogue (cast script, per-line voices, script-aligned captions, deviation flags) | `ss dialogue` | yes (Gemini with optional performance auditions, Kokoro, Qwen design and clone) | **voice choice** | n/a |
| Original procedural SFX set | `ss sfx` | yes (in the benchmark mix) | **sound feel** | n/a |
| Roblox take into the toolkit | `ss roblox import` | yes (Studio capture) | n/a | first OBS recording of a take |
| Finished set marks and real PvP filming | see [production quality](production-quality.md) | production work | owner creative review | first gameplay round |

Infrastructure is frozen. The dashboard, commercial funnel and initial knowledge banks are built. Current work is content production, account validation and small fixes. See the [agent brief](../CLAUDE.md) for approvals.

Production items (gameplay recording, voice selection, licensed music, SFX, brand fonts, real-world production tests) are deferred to [production quality and next steps](production-quality.md). They don't block the infrastructure.
