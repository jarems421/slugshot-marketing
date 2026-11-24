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
| `makemyclip` | MCP server (stdio) | `.mcp.json` | 8 timeline tools; media confined to `media\` (tested). Approve it when Claude Code asks |
| Permission rules | project settings | `.claude/settings.json` | deny edits to `../slugshot` and direct MakeMyClip CLI calls |
| Roblox Studio, Blender, Google Drive MCPs | user-level, already present | outside this repo | not used by the toolkit; the owner's Studio session was left alone |

## Capabilities

| Capability | Command | Status | Notes |
|---|---|---|---|
| Tool check | `ss doctor` | Tested | |
| Smoke test | `ss smoke` | Tested | `reports/smoke-test.md` |
| Capture import + naming | `ss import` | Tested (unit) | real OBS capture not yet done |
| AI narration | `ss voice` | Experimental | 5 voices generated; Whisper understood every game name. A person must judge if it's good enough |
| Voiceover clean-up | `ss audio tidy` | Tested | denoise optional; check speed-ups on a phone |
| Music ducking + SFX | `ss audio mix` | Tested | with a synthetic test tone; no licensed music yet |
| Transcription | `ss caption` | Tested | CPU base.en; hallucination guard on |
| Game-term correction | automatic in `ss caption`; `ss fixcaps` | Tested | 26 terms; exact + cautious fuzzy matching; misses big garbles (e.g. "Slug's Hotool kit"), which the low-confidence list flags |
| FFmpeg quick render | `ss vertical` | Tested | phrase captions + hook, auto QC |
| Remotion template + presets | `ss render --format X` | Tested | 7 presets in `config/formats.json`; word highlight, labels, end cards |
| Variants from one asset set | `ss batch jobs\x.json` | Tested | 3 variants, logged to `exports/share/variants_log.csv` |
| Automated QC | `ss qc`; automatic after renders | Tested | technical only; phone review still required |
| Template tweaking | `ss studio` | Implemented | opens Remotion Studio in the browser |
| Agent timeline editing | `ss clip ...` / MCP | Tested | CLI path guard + MCP confinement |
| YouTube discovery and snapshots | `ss yt discover/stats` | Tested live | 30-day storage, policy-limited metrics (`docs/youtube-api-policy.md`) |
| YouTube report for ChatGPT | `ss yt report` | Tested | CSV + `_README.md` data dictionary |
| TikTok / Instagram metrics | `ss export` | Implemented | manual entry into the CSV template; validated |
| Real gameplay sample | n/a | **Outstanding** | needs your OBS capture |
| YouTube key hygiene | n/a | **Outstanding** | regenerate and restrict the key (see policy doc) |
| Licensed music / SFX library | `assets/` | **Outstanding** | add files plus a row in `assets/LICENSES.csv` |
| Own-channel analytics (retention etc.) | n/a | **Outstanding** | YouTube Studio exports now; Analytics API with OAuth later |
| Dashboard | n/a | Not started (by request) | |
