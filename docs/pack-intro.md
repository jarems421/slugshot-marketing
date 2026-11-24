# Slugshot Claude Code toolkit: docs pack for ChatGPT and Gemini

{{GENERATED}} Paths in the text refer to the local workspace. Nothing here contains credentials or restricted API statistics: every YouTube and Twitch example is fake fixture data.

**Stage:** infrastructure is complete, including Roblox-native filming and (Stage 4.4) the research data collectors. Real production validation (real gameplay, real animations, real posts) hasn't started; it is listed in the production checklist below. Research methodology, query lists, watchlists, concept classification and interpretation now belong to ChatGPT; the collectors only gather dated, labelled data.

**What's new in this pack (Stage 4.4):**
- `docs/research-data.md`: the research collectors' commands, routine, schemas, sharing rules, and TikTok and Google Trends API findings.
- `docs/research-data-audit.md`: the audit, decisions and outcome.
- An updated YouTube API rules section and inventory.
- `reports/smoke-test-research.md`.

**Direction (owner decision, 2026-11-24): Roblox first, AI-enhanced second.**
- Most videos are Roblox footage: real gameplay, plus staged scenes, skits and cinematics filmed in an isolated copy of the game.
- Flow, anime and manga cutaways are short additions (1-4 s) with a narrative job.
- English and Spanish versions share one set of language-neutral visuals. Narration, captions, on-screen text and joke timing are made per language.

## Status at a glance

How to read the three groups:
- **Implemented:** the code or tool exists.
- **Smoke-tested:** it ran end to end on sample or stand-in material, and the result was checked.
- **Deferred:** production work. Nothing is built for it yet, and it doesn't block the infrastructure.

### Editing and analytics toolkit (`ss` commands)

| Capability | Implemented | Smoke-tested | Deferred production work |
|---|---|---|---|
| Capture import and naming (`ss import`) | yes | yes (MKV stand-in) | first real OBS gameplay session |
| AI narration, Kokoro (`ss voice`) | yes | yes (one warning: Whisper adds trailing ". ." on the round trip; words were correct) | choosing a voice, or recording your own |
| Voice clean-up, music ducking, SFX (`ss audio`) | yes | yes | licensed music and SFX files |
| Whisper captions + Slugshot glossary (`ss caption`, `fixcaps`) | yes | yes | real voice recordings |
| Single-clip render, presets, variants (`ss render`, `vertical`, `batch`) | yes | yes | real gameplay; phone review |
| Multi-scene assembly (`ss assemble`) | yes | yes (5 scenes, synced to the script) | Flow clips, real gameplay; pacing and humour judged by a person |
| Gemini timestamps to review clips (`ss candidates`) | yes | yes (sample CSV) | a real Gemini pass on a real session |
| Frame sheets, technical QC (`ss sheet`, `qc`) | yes | yes | n/a |
| Creative editing skill (`slugshot-video-editing`) | yes | used once on a sample edit | S-rules once platform results exist |
| MakeMyClip timeline editing (`ss clip`, MCP) | yes | yes (confined to `media\`) | n/a |
| YouTube public stats + report (`ss yt`) | yes | yes (live call) | n/a |
| YouTube bilingual searches, saved query sets, regional charts, creator uploads, comments, Shorts confirmation, budgets (`ss yt`) | yes | chart + Shorts check live; the rest on fixtures | ChatGPT's real query sets and creator lists |
| Wikipedia page views en/es (`ss wiki`) | yes | yes (live) | n/a |
| Google Trending Now RSS, 7 markets (`ss trends rss`) | yes | yes (live) | n/a |
| Google Trends Explore CSV import (`ss trends import`) | yes | sample files | first real download |
| Twitch clips and streams (`ss twitch`) | yes | yes (live) | onward-transfer check before sharing exports |
| Roblox experience stats, legacy API (`ss rbx`) | yes | yes (live) | n/a |
| Public observations importer: Creative Center, TikTok, Instagram, vidIQ, TinyFish (`ss observe`) | yes | yes | n/a |
| TikTok Discovery API, Instagram Business Discovery, Google Trends API | no | no | company identity / Slugshot Instagram account / alpha approval |
| Platform metrics export (`ss export`) | yes | yes (validation only) | first posts |
| Own-channel retention, Roblox acquisition | no | no | Slugshot channel; published game |

### Roblox-native production (`ss roblox`, `roblox-native/`)

| Capability | Implemented | Smoke-tested | Deferred production work |
|---|---|---|---|
| Isolated marketing place (snapshot of the game build, DataStores disabled, marker) | yes | yes (built, audited, opened in Studio) | n/a |
| Studio target guard: Claude's Studio MCP calls only on the marketing place | yes | yes (live deny and allow; piped tests) | n/a |
| Declarative JSON scene specs + validator (truth modes, canon) | yes | yes (smoke scene; negative tests rejected) | real scene library |
| Scene runner on Reel: sets, marks, actors, timed actions, VFX/sound cues, markers | yes | yes, with **stand-in actors only** | real slug rigs and avatars; finished sets |
| 9 camera presets | yes | yes (4 used in the smoke scene: two_shot, slug_low_angle, orbit_reveal, snap_zoom) | the other 5 are coded but not filmed yet |
| Reset per take, take manifests | yes | yes (6 takes) | n/a |
| Repeatability check (`ss roblox compare`) | yes | yes: one pair PASS; one pair missed the 50 ms target (56 ms cuts, 80 ms cues) | n/a |
| Take into the toolkit (`ss roblox import`) | yes | yes, with Studio's own recorder | first OBS recording of a take |
| Animation and sound registry (`library.json`) | format only (empty) | n/a | original animations, sounds, approvals |
| Facial expressions, multi-client staged gameplay, replay recorder | no | no | production preparation |
| OBS WebSocket automation | documented only | no | once manual recording is routine |

### Known limitations (summary; details in the sections below)
- **Studio guard scope:** it covers Claude Code sessions started in the marketing repo only. It doesn't cover Codex, ChatGPT desktop, sessions started elsewhere, or a person using Studio. There is a sub-second gap between the check and the call.
- **Not tested live:** the guard's two-windows-open and missing-marker cases (coded as denials).
- **Recording:** Studio's built-in video capture drops frames (about 27 fps, one 1.1 s stall). Use it for previews; final takes are recorded with OBS.
- **Repeatability:** takes are close enough to intercut by eye but not frame-exact (frame stalls of about 2 frames).
- **Stand-ins:** all Roblox-native tests used placeholder part-built actors; how real Slugshot characters look on camera is untested.
- **Switch helper:** `ss roblox switch` (closes the game place, opens the marketing place) needs the owner's approval each session.
- **Third-party code:** Motion Tools is on hold (no licence); RoPlay is excluded (non-commercial licence).

### Dependencies and licences added for Roblox-native work
- **Reel** (zAcherttp/roblox-reel, commit 4b810e9): MIT. Vendored unmodified; the only new dependency.
- **Not installed:**
  - CutsceneService (MIT), the fallback if Reel fails;
  - Motion Tools (no licence found);
  - RoPlay (non-commercial);
  - roblox-studio-agent-plugin (duplicates Studio's built-in MCP).
- No plugins were bought, nothing was published or uploaded, and no paid APIs were added.
