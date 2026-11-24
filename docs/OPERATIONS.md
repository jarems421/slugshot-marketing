# Operator reference

The full command walkthrough, folders, CSV schemas and safety rails (formerly the README). The project overview is in the [README](../README.md).

This folder holds the local tools for Slugshot's short-form videos: capture import, AI or recorded narration, voiceover clean-up and music ducking, Whisper captions with Slugshot term correction, vertical renders from format presets, batches of variants, automated QC, and a YouTube statistics collector. Research and scripts happen in ChatGPT; footage screening and Flow scenes happen in Gemini. The brief is in [CLAUDE.md](../CLAUDE.md).

Before scripting any mechanic, check [docs/game-truth.md](game-truth.md). The game repo `../slugshot` can be read and copied from freely (docs, assets, renders); game files are only changed when you explicitly ask.

More detail: **[command reference](COMMANDS.md)** · [Flow and Gemini hand-offs](flow-and-gemini.md) · [inventory and status](INVENTORY.md) · [tool research](tool-research.md) · [YouTube API rules](youtube-api-policy.md) · [research data collectors](research-data.md) · [evidence ledger](research-evidence.md) · [research methods](research-methods.md) · [ChatGPT handoff 4.5.3](chatgpt-handoff-4.5.3.md) · [latest smoke test](../reports/smoke-test.md) · [readiness report](../reports/readiness-2026-11-24.md)

**Roblox first, AI-enhanced second.** Most videos are filmed in Roblox: real gameplay, plus staged scenes and skits in an isolated copy of the game (`.\ss roblox ...`, [roblox-native/README.md](../roblox-native/README.md)). Flow/anime/manga cutaways are short additions. English and Spanish versions share the same visual footage and differ in narration, captions, on-screen text and timing.

Creative editing judgement (pacing, cuts, captions emphasis, audio, formats, review) lives in the Claude Code skill `.claude/skills/slugshot-video-editing/`. Claude loads it for any Slugshot editing or review task, next to the official Remotion skill.

## How this is operated

Automation first (owner decision, 2026-11-24): these commands are **Claude's interface**. Give Claude Code a short instruction ("collect today's research", "research Spanish Roblox content", "research Creative Center", "execute this brief", "make the Floppy duel edit") and it runs the steps, handles errors and reports back. Research requests go through the `slugshot-research-operations` skill. Your part is decisions, creative judgement, approvals (spending, publishing, destructive or game-repo changes), and the few actions only you can do (a Creative Center copy: Ctrl+A, Ctrl+C on pages Claude opens; signing in; uploading the bundle zip to ChatGPT). The commands below are listed for reference.

## Commands

Run from this folder: `.\ss <command>` in PowerShell, or `ss <command>` in Command Prompt. Every script also takes `-h`.

```powershell
.\ss doctor                     # versions + setup checks
.\ss smoke                      # full smoke test -> reports\smoke-test.md

# 1. Capture: record in OBS, then copy into media\raw\ with the naming convention
.\ss import "C:\Users\runni\Videos\2026-11-25 17-02-11.mkv" --format PVP --concept FloppyUnderdog --hook BestSlug --note "build 08fee46, me vs Sam"

# 2. Narration: record your own, or generate one (label AI voices where platforms ask)
.\ss voice "He brought Inferno. I brought Floppy." media\vo\floppy.wav --voice am_puck --speed 1.1
.\ss audio tidy media\vo\floppy.wav media\vo\floppy_clean.wav --speed 1.05        # add --denoise for mic recordings
.\ss audio mix media\vo\floppy_mix.wav --narration media\vo\floppy_clean.wav --music assets\music\bed.mp3 --sfx assets\sfx\hit.wav@3.2

# 3. Captions: Whisper + automatic Slugshot term fixes; then read the .srt
.\ss caption media\vo\floppy_clean.wav          # -> .srt, .words.json; prints every fix and low-confidence word
.\ss fixcaps media\vo\floppy_clean.srt          # re-apply config\glossary.json after you add terms

# 4. Render (QC runs automatically afterwards)
.\ss render SS_20261125_PVP_FloppyUnderdog_BestSlug_V01_MASTER media\raw\SS_..._RAW.mkv --format PVP --narration media\vo\floppy_mix.wav --captions media\vo\floppy_clean.srt --hook "He brought Inferno. I brought Floppy."
.\ss batch jobs\sample-variants.json            # several hooks/formats from one set of assets
.\ss assemble jobs\edit-sample-story.json       # multi-scene: clips, stills, cards, script -> voice, music, SFX
.\ss candidates media\raw\X_RAW.mkv media\raw\X_RAW.gemini.csv   # Gemini timestamps -> review clips
.\ss sheet exports\SS_..._MASTER.mp4             # frame sheet for creative review
.\ss vertical <clip> <out.mp4> --narration ... --srt ... --hook "..."   # quick FFmpeg route, phrase captions
.\ss qc exports\SS_..._MASTER.mp4                # re-check any file
.\ss studio                                      # tweak the template in Remotion Studio

# MakeMyClip (silence removal, trims, reframing, export to Resolve/Premiere XML). Files must be under media\
.\ss clip ui

# 5. Research data and metrics (full guide: docs
esearch-data.md)
.\ss research collect --profile daily            # or spanish / refresh: runs the collectors, then bundles
.\ss research bundle                            # -> exports\share\bundles\slugshot_research_<time>.zip (for ChatGPT)
.\ss observe cc-session --periods 7 --category Games   # guided Creative Center: you press Ctrl+A, Ctrl+C on each page
.\ss research status                            # credentials present?, stored rows, quota today
.\ss analyze intake                             # QC of the newest bundle (also added to every bundle as INTAKE.md)
.\ss analyze trend huss                         # heat/velocity/breadth/persistence kept separate; lifecycle proposal
.\ss evidence validate EXAMPLE-HUSS-SLUGTERRA --bundle exports\share\research   # evidence ledger checks
.\ss yt discover "roblox pvp" --lang es --region MX --days 7   # 1 search call (100/day allowance) + 1 unit
.\ss yt chart --region MX                        # Mexico's most-popular Gaming chart, 1 unit
.\ss yt stats                                   # re-snapshot the watchlist: 1 unit per 50 videos
.\ss wiki pull; .\ss trends rss; .\ss twitch clips --game Roblox --lang en,es; .\ss rbx games
.\ss observe import notes.csv --source creative_center --platform tiktok --entity-type hashtag --region US --period "7 days" --observed-at 2026-11-24
.\ss yt report; .\ss wiki report; .\ss trends report; .\ss observe report   # -> exports\share
esearch\ (for ChatGPT)
.\ss research prune                             # retention rules, expired exports deleted
.\ss export                                     # check data\local\platform_metrics.csv -> exports\share\
```

## Formats (`config/formats.json`)

| Code | Use | Look |
|---|---|---|
| PVP | real gameplay duel | crop to fill, word-by-word captions, yellow accent |
| PROMO | direct game pitch | crop, end card "Roblox creature combat - in development" |
| CHOICE | "which slug?" decision | green accent, end card asks the question |
| WORLD | In My World story | blur fill, **"Fictional story"** label stays on screen |
| SKIT | character comedy/dance | blur fill, "Skit" label, no end card |
| AISCENE | Flow / AI clip | **"AI-generated scene"** label stays on screen |
| TEST | toolkit tests | "TEST - not gameplay" label |

Any flag (`--fit`, `--accent`, `--label`, `--end-title`, `--end-subtitle`, `--clip-volume`, `--no-end-card`) overrides the preset. In a batch file, put the same names on a variant (`fit`, `accent`, `label`, `endCardTitle`, `endCardSubtitle`, `clipVolume`, `endCard`).

## Captions and the glossary

`config/glossary.json` lists Slugshot names (slugs, abilities, places) with their usual mishearings and, where needed, a respelling for the voice generator. `ss caption` uses it three ways: as Whisper's spelling hints, to correct the transcript (merging split words such as "Slug's Hoe" into "Slugshot" with the right timing), and to list low-confidence words. Fuzzy matching only joins two or three words that are within a letter or two of a made-up name, so normal words ("sloppy", "slugs are hot") are left alone. Big garbles still get through. Read every `.srt` and add new mishearings to the glossary rather than fixing them by hand each time.

The PVP, PROMO and CHOICE presets use the `.words.json` file (word highlight). WORLD, SKIT and AISCENE use the `.srt`. Both come from the same corrected transcript; if you edit the `.srt` by hand, use a phrase-caption preset or re-run `ss caption`.

## QC (`ss qc`, automatic after renders)

FAIL: not H.264/yuv420p, no AAC audio, loudness outside -18..-10 LUFS, opens on black. WARN: not 1080x1920, odd frame rate, longer than 180 s, true peak above -1 dBTP, near-black for 0.5 s or more, frozen for 3 s or more, silence of 1.5 s or more before the ending. Results go to `<file>.qc.json` and `reports\qc_log.csv`. These checks are technical only: still watch every master on a phone for captions, crop, truth and rights.

## OBS settings (once)

Settings > Output > Recording: Recording Path = `C:\Users\runni\slugshot marketing\media\obs`, format MKV, encoder NVIDIA NVENC H.264, quality "High Quality". Settings > Video: 1920x1080, 60 fps. Keep the action in the middle third of the screen so the vertical crop doesn't cut it.

Manual fallback: in Kdenlive, create a 1080x1920 30 fps project, add the clip, import the checked `.srt` onto the subtitle track (Import Subtitle File) and render with the MP4-H264/AAC profile.

## Folders

| Path | Contents | In git? |
|---|---|---|
| `media/` | raw footage, voiceovers, MakeMyClip workspace | no |
| `exports/` | finished masters; `exports/share/` holds CSVs for ChatGPT (variants log, platform metrics, YouTube report) | no |
| `data/local/` | YouTube snapshots, watchlist, quota log, `platform_metrics.csv` | no |
| `models/` | Kokoro model files (325 MB + 28 MB) | no |
| `assets/` | your music, SFX, brand files (ignored) + `LICENSES.csv` (tracked) | licence list only |
| `config/` | `formats.json` presets, `glossary.json` terms | yes |
| `jobs/` | batch job files | yes |
| `data/templates/` | CSV template for hand-entered platform metrics | yes |
| `docs/` | brief sources, bank snapshot, game truth, policy, research, inventory | yes |
| `remotion/` | the 9:16 template (`Vertical` composition) | yes |
| `scripts/` | the Python commands behind `ss` | yes |
| `reports/` | smoke-test report | yes |
| `.claude/` | project skill (Remotion), permission rules | yes |
| `roblox-native/` | Roblox-native filming: runtime, scene specs, tools; the marketing place and takes stay local | code yes; `.rbxlx` and `capture/` no |
| `vendor/` | reviewed third-party source clones | no |

## CSV files

**Research data** (YouTube, Wikipedia, Google Trends, Twitch, Roblox, public observations): raw stores in `data/local/research/<provider>/`, exports in `exports/share/research/` with a `.json` copy, a `_README.md` data dictionary and `MANIFEST.csv` (expiry dates). Every schema is in [docs/research-data.md](research-data.md). Blank = unknown, never 0.

**`data/local/research/youtube/youtube_snapshots.csv`**: one row per video per collection run, with the search parameters that found it (`region_param`, `relevance_language_param`, date window), declared language and category, and `shorts_status`. Rows older than 30 days are deleted automatically (YouTube policy).

**`exports/share/research/youtube_report_<time>.csv`**: latest snapshot per video plus `age_hours`, `snapshots`, `hours_since_prev`, `view_increase_since_prev` and `views_per_hour_since_prev`. These derived columns compare the same video with itself, never with other videos or channels. A `_README.md` data dictionary is written next to it: give both to ChatGPT for internal analysis (don't publish the data). Comparing creators with their own averages was removed because YouTube's policies need approval for that ([details](youtube-api-policy.md)).

**`exports/share/variants_log.csv`**: one row per rendered variant (`edit_file, format, concept, hook_id, hook, clip, narration, captions, duration_s, qc, qc_issues, experiment_id`), ready to copy into the content log.

**`data/local/platform_metrics.csv`** (from `data/templates/platform_metrics_template.csv`): one row per upload per observation, typed in from TikTok, Instagram and YouTube Studio. `experiment_id, edit_file, format, hook_type, slug, platform, published_url, posted_at_utc, observed_at_utc, views, watch_metric_name, watch_metric_value, likes, comments, shares, saves, profile_visits, link_new_players, production_minutes, notes`. `ss export` adds `hours_since_post` and a `check` column.

## Safety rails

- `.env` holds the YouTube key and is git-ignored; `.env.example` must only ever hold `YOUTUBE_API_KEY=` with nothing after it.
- MakeMyClip: its MCP server and browser UI refuse files outside `media\` (tested). Its CLI doesn't check paths, so `ss clip` does, including absolute paths, other drives and links.
- `.claude/settings.json` (for Claude sessions here): blocks reading `.env` and calling the MakeMyClip CLI directly; asks before recursive deletes and destructive git commands. The game repo can be read and copied from; Claude asks before changing game files unless you explicitly request it. These rules guard against mistakes, not against you.
- Roblox Studio: Claude's Studio MCP calls are refused unless only `SlugshotMarketing.rbxlx` is open and its marker matches (a hook, tested live). The marketing place is never published.
- Money: nothing here costs anything. Claude asks before any paid request, billing change or subscription.
- Remotion renders use the Free License flag. If Slugshot becomes a company of more than 3 people, buy a company licence.

## Next actions

Infrastructure is complete (24 Nov 2026), and the project has moved on to active research and marketing. Don't build more infrastructure unless a specific decision needs it. The bilingual query families (families-1.1), watchlists and codebook v1.1 are in place, and the first pilot is validated ([stage-4.5.4-report.md](stage-4.5.4-report.md)).

Remaining milestones (methodology: [chatgpt-research-skills-v1.1.md](chatgpt-research-skills-v1.1.md)):
1. **Foundational marketing research and initial knowledge banks.** Bounded literature reviews and creative hypotheses, starting with short-form attention, curiosity, narrative comprehension and payoff.
2. **Commercial funnel.** Definitions and an implementation plan for acquisition, attribution, activation, retention and monetisation.
3. **Centralised minimum viable dashboard.** Research, experiments, content and player outcomes, built from existing tools.

Open items:
- Deferred until a production decision depends on it: the pilot's independent human spot-check (packet `data/local/research/analysis/coding_packet_BRIEF-20261124-RULE-WORLD-PILOT.spotcheck.md`). Stage 4.5.5 is closed; the v1.1 recode is integrated.
- Optional: approve the `makemyclip` MCP server when Claude Code asks.
- Before sharing Twitch exports: check Twitch's onward-transfer terms, then set `twitch.share_exports` to true.

Production work (gameplay capture, voice choice, music, SFX, brand fonts, real-world tests) is in the [deferred production checklist](production-checklist.md).
