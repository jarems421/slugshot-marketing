# Setup report: Claude Code production environment, phase 2

Date: 2026-11-24. Scope: the Claude Code side only (no Gemini/ChatGPT configuration, no dashboard, no custom agents). The game repo `../slugshot` was read but never modified.

## 1. Audit

| Area | Result |
|---|---|
| Software | All present and versions recorded in [docs/INVENTORY.md](../docs/INVENTORY.md). `ss doctor` and the smoke test verify them on demand. |
| Python deps | Two venvs: `.venv` (Whisper) and `.venv-tts` (Kokoro), each pinned in a requirements file. Kept separate so a TTS upgrade can't break transcription. |
| Node deps | Exact pins in `package.json` + `package-lock.json`. npm held back two install scripts: `ffmpeg-static` isn't needed (the system FFmpeg is used); `esbuild` works without it. |
| Skills / MCP | Added the official Remotion skill (reviewed, copied, source recorded). MakeMyClip MCP configured in `.mcp.json`. The MakeMyClip skill was deliberately not installed. |
| MakeMyClip confinement | MCP: refuses the game repo and `../.env.example` (tested). CLI: has no check of its own, so `ss clip` refuses absolute paths, other drives, `..` and links outside `media\` (tested). The `npm run clip` script was removed. `.claude/settings.json` denies direct `npx clip` / `node .../cli.js` calls and edits to `../slugshot` for Claude sessions. Remaining gap: a person typing `npx clip` by hand isn't stopped. |
| Secrets | The YouTube key had been saved in `.env.example`, which git tracks. It was moved to `.env` (ignored) before any commit, and the placeholder restored. Scanned all files to be committed: no keys. **The key's value appeared in the Claude Code session, so regenerate it.** |
| Git hygiene | Ignored: `.env`, venvs, `models/`, `media/`, `exports/`, `data/local/`, `out/`, `public/`, `vendor/`, asset binaries, QC logs. Nothing over 1 MB is tracked. |

## 2. Analytics

- Read the current YouTube Developer Policies, policy guide, Terms and quota page. Summary and decisions: [docs/youtube-api-policy.md](../docs/youtube-api-policy.md).
- **Disabled:** views compared with the creator's median for similar-age uploads (a ratio against an independently calculated average is listed as prohibited without approval), and the age buckets that fed it.
- **Kept:** per-video differences between two snapshots (`view_increase_since_prev`, `hours_since_prev`, `views_per_hour_since_prev`), `age_hours`, and a duration flag never called "Short".
- **Storage:** hard 30-day cap; `prune` can't be set higher.
- **Quota maths corrected:** search.list now has its own 100-calls/day bucket at 1 unit per call.
- **Exports for ChatGPT:** each report now comes with a `_README.md` data dictionary (source of every column, what blanks mean, what the numbers can't tell you).
- **Live test: PASS.** One `stats` call and one `discover` returned real data (3 quota units in total).

## 3. Research

Full table with licences and hardware: [docs/tool-research.md](../docs/tool-research.md). Installed: Kokoro-82M (narration) and the Remotion skill. Everything else uses FFmpeg, Remotion and MakeMyClip, which were already here. Considered and not used:

- **Rejected on licence:** XTTS-v2 and F5-TTS, because their weights are non-commercial.
- **Rejected as unofficial:** edge-tts, which uses a Microsoft service without permission.
- **Redundant:** auto-editor (MakeMyClip and FFmpeg already remove silence) and QCTools (more than needed).
- **Deferred:** Chatterbox (needs a 3 GB CUDA stack), DeepFilterNet (only if mic recordings are noisy) and PySceneDetect.

## 4. Pipeline improvements

| Improvement | How | Test |
|---|---|---|
| Terminology correction | `config/glossary.json` (26 Slugshot terms) drives Whisper hints, transcript correction (merges split words and keeps their timing) and TTS respelling; `ss fixcaps` re-applies it | 12/12 checks, including cases that must not change; caught "slug's Hoh" -> "Slugshot" on a real transcript |
| Whisper hallucinations | `hallucination_silence_threshold`, then drop segments with avg_logprob < -2 and words under 1% confidence (or instantaneous and under 5%); everything dropped is printed | invented endings seen in 4 of about 10 short test clips ("incred minerals are", "Holmes 30 March", "transition to a terminal"); all removed, no real words lost |
| Format templates | `config/formats.json`: PVP, PROMO, CHOICE, WORLD, SKIT, AISCENE, TEST; new template props for accent colour, caption height and a persistent label (fiction/AI disclosure) | rendered PVP/PROMO/CHOICE-style variants; CHOICE end card checked by eye |
| Variants from one asset set | `ss batch jobs\x.json` -> named masters + `variants_log.csv` | 3 variants in 97 s, all QC PASS after threshold tuning |
| Audio | `ss audio tidy` (pause trimming that keeps 150 ms breaths, speed, levelling) and `ss audio mix` (ducked music, timed SFX) | 12.7 s -> 10.4 s; music 13 dB lower under speech |
| QC | `ss qc`, automatic after `render`, `vertical` and `batch` | flags wrong size, codec, loudness, black opening, mid-video silence, frozen video; quiet end cards are not flagged |
| Render correctness | Remotion now outputs yuv420p BT.709 (was full-range `yuvj420p`) with the Free License flag | QC codec check PASS |

Bugs found and fixed along the way:

- `ss` split single arguments into separate characters.
- The QC parser missed freezes that run to the end of the file.
- The format preset's caption mode could overwrite the captions file path.
- An unsafe colon match in the path guard blocked caption text such as "Round 1: go".

## 5. Test results

[reports/smoke-test.md](smoke-test.md): 10 checks covering tools, glossary, Whisper, Kokoro round trip, audio tidy and mix, FFmpeg render + QC, Remotion render + QC, MakeMyClip, YouTube dry run and YouTube live.

## Limitations

- **Sample footage:** all renders so far use a 1422x430 Blender preview strip and synthetic narration. No real gameplay has been through the pipeline yet.
- **Caption correction:** big garbles (e.g. "Slug's Hotool kit" from sped-up audio) still get through; the low-confidence list flags them, so the read-through stays essential.
- **AI voice:** Kokoro is clear but its "energy" hasn't been judged by a person. Chatterbox is the upgrade path.
- **QC scope:** QC can't judge crop safety, caption accuracy, truthfulness, music rights or humour.
- **MakeMyClip guard:** the CLI guard and permission rules stop mistakes, not deliberate bypasses; MCP is the robust path.
- **YouTube data:** the API gives no retention, watch time or shares for other channels. Cross-creator comparison needs YouTube's approval. Sharing API CSVs with ChatGPT is a grey area in the policy.
- **Remotion licence:** the Free License stops applying if Slugshot becomes a company of more than 3 people.

## Needs you

1. Regenerate the YouTube key, restrict it to YouTube Data API v3, paste it into `.env`, then run `.\ss smoke`.
2. Approve the `makemyclip` MCP server when Claude Code asks (optional).
3. Set OBS's recording path and film 20 s of a real round; run it through `import`, `caption`, `render`.
4. Listen to the Kokoro samples (`media\vo\test_*.wav`) and choose AI or recorded narration.
5. Add licensed music/SFX and record them in `assets\LICENSES.csv`.
6. Optional: drop the research PDF file into `docs/`.

## Recommendations still missing from the Claude Code environment

- **Reference-render pack from Studio:** the research PDF's Flow pipeline needs clean slug stills. Capturing them needs the owner's Studio session or a dedicated capture place, so it's not done.
- **Own-channel analytics:** once the channel exists, add a YouTube Studio CSV import (and later the Analytics API with OAuth) to get retention and watch time.
- **Chatterbox:** install in a third venv with CUDA PyTorch if Kokoro proves too flat.
- **PySceneDetect:** add if 30-minute OBS sessions are slow to screen.
