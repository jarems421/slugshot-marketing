# Inventory and capability status

Last updated 2026-11-24. Infrastructure phase complete; production work is in [production-checklist.md](production-checklist.md). Command details: [COMMANDS.md](COMMANDS.md).

## Software

| Item | Version | Location | How it's used |
|---|---|---|---|
| Git | 2.55.0 | system | version control |
| Python | 3.13.15 | system; venvs `.venv` and `.venv-tts` | scripts |
| openai-whisper | 20250625 (torch 2.15 CPU) | `.venv` (`requirements.txt`) | `ss caption` |
| kokoro-onnx + Kokoro-82M v1.0 | 0.6.1 | `.venv-tts` (`requirements-tts.txt`), `models/kokoro/` (not in git) | `ss voice` |
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
| `slugshot-video-editing` | project skill (ours) | `.claude/skills/slugshot-video-editing/` | creative editing judgement: pacing, cuts, zooms, captions, audio, format playbooks, review gates; evidence-labelled A/B/C/D/S |
| `makemyclip` | MCP server (stdio) | `.mcp.json` | 8 timeline tools; media confined to `media\` (tested). Approve it when Claude Code asks |
| Permission rules | project settings | `.claude/settings.json` | blocks reading `.env` and direct MakeMyClip CLI calls; asks before recursive deletes and destructive git commands. The game repo is readable and copyable; changes to game files need the owner's request (CLAUDE.md) |
| Roblox Studio MCP (built-in) | user-level, already present | `%LOCALAPPDATA%\Roblox\mcp.bat` | used for Roblox-native filming, **only on the marketing place**: a PreToolUse hook (`roblox-native/tools/studio_guard.py`) denies every call unless that place is the only one open and its marker matches; Roblox-service tools ask first |
| Blender, Google Drive MCPs | user-level, already present | outside this repo | not used by the toolkit |

## Capabilities

Readiness: **Tested** = runs end to end, checked by the smoke test or a recorded test. **Human approval** = works, but its creative output must be judged by a person before anything is published. **Waits on footage/channel** = can't be fully proven until real gameplay or a Slugshot channel exists.

| Capability | Command | Tested | Human approval | Waits on footage/channel |
|---|---|---|---|---|
| Tool check / smoke test | `ss doctor`, `ss smoke` | yes (13/13) | n/a | n/a |
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
| YouTube public stats | `ss yt` | yes (live) | n/a | n/a |
| YouTube reports | `ss yt report` | yes | n/a | written to `exports/share/` for ChatGPT (sharing approved by the owner) |
| Platform metrics for ChatGPT | `ss export` | yes (validation) | n/a | **first posts** |
| Own-channel retention/watch time | none | no | n/a | **Slugshot channel** (Studio exports, later Analytics API) |
| Roblox acquisition (share links) | none | no | n/a | **published game** |
| Dashboard | none | not started (by request) | n/a | n/a |
| Isolated Roblox marketing place | `ss roblox build/rebuild/audit` | yes (audit, live Studio session) | n/a | n/a |
| Studio target guard | hook, `ss roblox guard` | yes (live deny and allow) | n/a | n/a |
| Scene specs + runner (stand-ins) | `ss roblox validate`, `Scene.runJson` | yes (smoke scene, 6 takes) | **performance, humour, look** | real animations, sets, slug rigs |
| Take repeatability | `ss roblox compare` | yes (one PASS; one at 56 ms cuts / 80 ms cues vs a 50 ms target) | n/a | n/a |
| Roblox take into the toolkit | `ss roblox import` | yes (Studio capture) | n/a | first OBS recording of a take |
| Animation library, finished sets, real PvP filming | none | no (production work) | **every animation and set** | production preparation |

Infrastructure: complete, including Roblox-native filming ([roblox-native/README.md](../roblox-native/README.md)). Remaining setup: regenerate and restrict the YouTube key; optionally approve the `makemyclip` MCP server.

Production items (gameplay recording, voice selection, licensed music, SFX, brand fonts, real-world production tests) are deferred to [production-checklist.md](production-checklist.md). They don't block the infrastructure.
