# Slugshot marketing — Claude Code implementation brief

## Mission
Set up a local, working production toolkit for one Roblox game. Do not build a new AI agent, SaaS, full dashboard, or custom video editor. Prefer existing public tools, a small number of scripts, and simple CSV/Markdown handoffs. ChatGPT is the research and scriptwriting workspace; Gemini/Flow analyses footage and generates scenes; this Claude Code workspace handles local installations, API collectors and repeatable editing. Leave the game repo and personal Codex configuration untouched. Use only the dedicated marketing Claude account. Do not require paid model API calls or new subscriptions.

## First session — do in order
1. Inspect existing Windows software and versions (Git, Python, Node, FFmpeg, OBS, Kdenlive) before installing anything. Review `setup/Slugshot-Marketing-Setup.cmd` and stage-2 notes; install missing requirements from verified official sources with user approval. Reuse existing tools. Keep local Python dependencies in a virtual environment and Node dependencies pinned in the workspace.
2. Install/test FFmpeg and Whisper; produce a captioned vertical MP4 from disposable sample footage and narration. Use actual timestamps and check captions manually. Use OBS for capture and Kdenlive as the manual fallback; Resolve Free is optional and not required if Kdenlive is enough.
3. Set up one Remotion 9:16 template with a clip, captions, hook text and optional end card. Use official Remotion docs, check licence eligibility, and test a local render. Review MakeMyClip's current README, licence, dependencies, install scripts and permissions before installing its Claude Code skill or configuring MCP. Restrict its media access to this workspace; do not grant access to the game or secrets. Test on copies of footage only. If MakeMyClip already solves the task, don't reinvent it. Avoid duplicate transcription pipelines unless a test justifies them.
4. Build the smallest useful YouTube Data API collector: keyword/recent upload discovery plus batched public statistics for selected video IDs, store dated snapshots in CSV or SQLite. Record ID, URL, title, creator/channel, published timestamp, observed UTC timestamp, views, likes, comments and source. Keep missing values null. Shorts identification may be approximate; avoid claiming all short-duration uploads are Shorts. For relative performance compare similarly aged uploads within each creator; for velocity compare repeat snapshots. Follow API quotas and terms, including applicable retention/refresh rules. Do not fabricate data or claim unavailable retention/share metrics. Keep TikTok and Instagram as manual/CSV imports initially; no unauthorized scraping or restricted research APIs. User must authorize API credentials in provider console; keep secrets in ignored `.env` or credential storage and use `.env.example` with placeholders only. Never print secrets. No paid requests without permission.
5. Provide simple commands for capture/import, caption/render, metric collection and export. Add a short README, `.gitignore`, dependencies and an actual smoke-test report with PASS/FAIL/BLOCKED. Optional local UI only if a working workflow needs it; use existing Remotion Studio or MakeMyClip timeline first. Do not add hosting, login, scheduling, database services or automatic posting.

## Handoffs
- ChatGPT: research/trends, approved scripts and creative briefs; user transfers exports and source updates between tools.
- Gemini: candidate clip timestamps and original Flow scenes; verify timestamps and character consistency.
- Local: keep raw footage, reference renders, projects, local data and credentials. Export only shareable CSV, scripts and test reports to ChatGPT. Do not commit large raw media or secrets.
- Sources: `docs/` contains the research PDF and an original bank snapshot. Replace the snapshot with the user's latest bank when supplied; never overwrite their master or claim synchronization. Game repo reference is for factual checking only, not development. Verify the current game before asserting mechanics; Floppy does not transform in the documented design. Label fictional/synthetic scenes where needed.

## Definition of done
- Installed tools/version list with missing items flagged.
- One real local vertical sample export (1080x1920 preferred) with readable captions, clean audio and no foreign watermark.
- One working public YouTube collector run, if user supplies authorized credentials locally; otherwise working dry-run/mock with an explicit blocked live check.
- README with exact commands, CSV schema, and next action. No elaborate dashboard needed.

## Links
- OBS https://obsproject.com/
- Kdenlive https://kdenlive.org/
- FFmpeg https://ffmpeg.org/
- Whisper https://github.com/openai/whisper
- Remotion https://www.remotion.dev/docs/ and https://www.remotion.dev/docs/license/pricing
- MakeMyClip https://github.com/MakeMyClip/editor
- Optional Resolve https://www.blackmagicdesign.com/uk/products/davinciresolve
- YouTube API https://developers.google.com/youtube/v3
- Claude Code https://code.claude.com/docs/en/overview

## Working notes for this workspace (added during setup, 2026-11-24)
- The game repo is at `../slugshot`. You may read, inspect and copy anything from it (docs, assets, renders, footage) into this workspace. Don't modify game files, run its build scripts or change its git state unless the owner explicitly asks; otherwise ask first. (Owner instruction, 2026-11-24.)
- Protections that stay on: no reading or printing `.env`; recursive deletes and destructive git commands ask first (`.claude/settings.json`); never commit secrets or raw media.
- Game claims go through `docs/game-truth.md`. Re-check `../slugshot/docs/status.md` before relying on it; it changes daily.
- Commands live in `ss.ps1` (see README). Raw media goes in `media/` (ignored); MakeMyClip is confined to `media/`. Use MakeMyClip through `ss clip` or its MCP server, never `npx clip` directly (its CLI ignores the workspace limit).
- One transcription engine: openai-whisper in `.venv`. Do not add whisper.cpp unless a test shows openai-whisper can't do a job. TTS (Kokoro) lives in `.venv-tts` so it can't break Whisper.
- New Slugshot names or mishearings go in `config/glossary.json`; new video looks go in `config/formats.json`. Fiction and AI scenes use the WORLD/SKIT/AISCENE presets, which keep a label on screen.
- YouTube collector: stay within `docs/youtube-api-policy.md` (30-day storage, per-video arithmetic only, no cross-channel ratios or rankings). Never print or commit the key; `.env.example` holds only the empty placeholder.
- Status of every capability is in `docs/INVENTORY.md`; update it when something changes. Command reference: `docs/COMMANDS.md`.
- For any editing, assembly or review decision, use the `slugshot-video-editing` skill (creative judgement) alongside `remotion-best-practices` (API). Label recommendations A/B/C/D/S as the skill describes; never give numeric quality grades; say what needs a person.
- YouTube public stats may be shared with AI tools (ChatGPT, Gemini) for internal analysis (owner decision, 2026-11-24). `ss yt report` writes to `exports/share/`. Don't publish the data.
- Money: never make a paid request or enable billing (APIs, cloud renders, subscriptions, paid models) without asking first. Free quotas (YouTube Data API) are fine.
- **Roblox first, AI-enhanced second** (owner decision, 2026-11-24): most videos are Roblox footage (real gameplay, staged scenes, skits, cinematics) filmed in `roblox-native/`; Flow/anime/manga cutaways are short additions. Use the `slugshot-roblox-production` skill for any Roblox filming or Studio MCP work. Studio MCP calls only on `SlugshotMarketing.rbxlx` (the hook enforces it); run `ss roblox switch` only when the owner asks; never publish the place or upload assets without approval.
- Bilingual EN/ES: one set of language-neutral visuals; narration, captions, on-screen text and joke timing are made per language downstream.
- Production work (gameplay capture, voice choice, music/SFX, brand fonts, real-world tests) is tracked in `docs/production-checklist.md`; it is not infrastructure.
