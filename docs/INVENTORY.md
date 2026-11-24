# Inventory and capability status

Last updated 2026-11-24. Status: **Tested** = run end to end here with checked output. **Implemented** = built, partly exercised. **Experimental** = works, quality not yet judged by a person. **Outstanding** = not done / needs you.

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

## Claude Code skills and MCP servers (this project)

| Item | Type | File | Notes |
|---|---|---|---|
| `remotion-best-practices` | project skill | `.claude/skills/remotion-best-practices/` | official Remotion guidance, Markdown only (see `SOURCE.txt`) |
| `slugshot-video-editing` | project skill (ours) | `.claude/skills/slugshot-video-editing/` | creative editing judgement: pacing, cuts, zooms, captions, audio, format playbooks, review gates; evidence-labelled A/B/C/D/S |
| `makemyclip` | MCP server (stdio) | `.mcp.json` | 8 timeline tools; media confined to `media\` (tested). Approve it when Claude Code asks |
| Permission rules | project settings | `.claude/settings.json` | deny edits to `../slugshot` and direct MakeMyClip CLI calls |
| Roblox Studio, Blender, Google Drive MCPs | user-level, already present | outside this repo | not used by the toolkit; the owner's Studio session was left alone |

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
| YouTube reports | `ss yt report` | yes | n/a | **internal only**; sharing with AI services disabled pending policy clarity |
| Platform metrics for ChatGPT | `ss export` | yes (validation) | n/a | **first posts** |
| Own-channel retention/watch time | none | no | n/a | **Slugshot channel** (Studio exports, later Analytics API) |
| Roblox acquisition (share links) | none | no | n/a | **published game** |
| Dashboard | none | not started (by request) | n/a | n/a |

Outstanding actions for you: regenerate and restrict the YouTube key; first OBS capture; licensed music/SFX in `assets/LICENSES.csv`; approve the `makemyclip` MCP server if wanted.
