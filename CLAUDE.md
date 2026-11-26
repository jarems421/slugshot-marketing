# Slugshot marketing agent brief

This Windows workspace produces English and Spanish short-form videos and runs marketing research for Slugshot. The current priority is reusable Roblox footage and finished content. Infrastructure is frozen. Reuse the toolkit, connectors and existing workflows. Make small, isolated fixes with regression coverage when the owner asks or a defect blocks production.

## Roles and approvals

- **Owner** sets strategy, directs creative work, judges the result and gives approvals.
- **Claude** runs the local workflow end to end, including collection, validation, file handoffs, editing and Roblox-native filming. Run `ss` yourself. Handle ordinary retries and quotas, and report evidence, blockers and decisions that need the owner.
- **ChatGPT** designs research, interprets culture and evidence, develops creative strategy and writes scripts.
- **Gemini / Flow** analyses footage and produces original visual cutaways. Verify timings, asset consistency and the scope of any media cleared for cloud review.

Routine free and reversible marketing work is pre-approved. Ask before spending money, enabling billing, using vidIQ credits outside an agreed budget, starting Deep Research, publishing, doing destructive work, or changing the game repo. Use existing owner-approved spending caps as written. Account connections require the owner's OAuth step. Use Composio read-only unless the owner approves a write. Respect provider terms, permissions, rate limits and retention. [Operator guide](docs/OPERATIONS.md)

## Protection and release

- Keep credentials in the ignored `.env` or the dashboard's Windows DPAPI vault. Never inspect `.env` directly or expose keys, tokens or raw media in chat, logs, exports or git. The tools read their own configuration. [Credentials checklist](docs/dashboard/credentials-checklist.md)
- The sibling `../slugshot` game repo is a read-only source for factual checks and copies. Changes, builds and git operations there require explicit approval. Verify claims against [game truth](docs/game-truth.md) and recheck the current game status before relying on it. Label fiction, skits and AI scenes using the appropriate presets.
- Use Studio MCP only on `SlugshotMarketing.rbxlx` and keep the isolation hook in place. Run `ss roblox switch` only when the owner asks. Studio publishing and asset uploads require explicit approval. Use MakeMyClip through `ss clip` or its configured MCP server, confined to `media/`. [Studio workflow](roblox-native/README.md)
- Prepare publishing drafts, checks and manual packages, or record a post the owner made by hand. Only the owner approves each upload in the dashboard by typing the account handle. Never call the approval endpoint or work around the gate. Keep the reveal lock on until the owner explicitly lifts it. Public entertainment posts require per-video owner confirmation. [Publishing rules](docs/dashboard/publishing.md)

## Research and evidence

Use the [research operations skill](.claude/skills/slugshot-research-operations/SKILL.md) for collection and bundling, and the [analysis skill](.claude/skills/slugshot-research-analysis/SKILL.md) for interpretation. Record provenance, timestamps and run IDs and keep provider data separate. Treat missing values as unknown. Apply the strictest applicable provider, methodology and game-truth rules. [Data and provider rules](docs/research-data.md) · [YouTube policy](docs/youtube-api-policy.md)

Put substantive findings in the evidence ledger with a claim level (O/D/P/I/C/R), support status, verbal strength and traceable references. Keep A/B/C/D/S creative-evidence labels separate from P1–P4 collection provenance. Use the current codebook and blind coding where applicable. A second session of the same model is a repeat check. Keep causal claims, qualitative readings and measured patterns distinct, and use suggestive findings to justify bounded tests. [Research methods](docs/research-methods.md) · [Evidence ledger](docs/research-evidence.md)

Run `ss kb brief` before a creative brief and `ss kb validate` after a knowledge-bank edit. Only the owner approves findings. Keep concepts and experiments in the dashboard store. Preserve the Stage 4.6 reports and audit, with corrections logged as AMD entries. [Knowledge banks](docs/knowledge-banks.md) · [Dashboard guide](docs/dashboard/README.md)

## Production quality

Lead with Roblox footage. Use Flow or other AI visuals as short additions. Share language-neutral footage across English and Spanish and make narration, captions, on-screen text and joke timing for each language.

Deliver native-pixel 1080×1920 masters. Capture Roblox-native footage in film mode and decode it with `ss roblox film` with zero repeated frames. Inspect the frames and listen to the edit before presenting it. Give every shot, acting beat, camera move and sound a job in the script, using dialogue line anchors for timing. Use the game's inked characters, glowing caverns and Kalam captions as the visual reference. Call out the judgement the owner still needs to make about humour, voice or feel. [Quality bar and review log](docs/production-quality.md)

Use the [script-writing skill](.claude/skills/slugshot-script-writing/SKILL.md) before production, the [Roblox production skill](.claude/skills/slugshot-roblox-production/SKILL.md) for filming or Studio work, and the [video-editing skill](.claude/skills/slugshot-video-editing/SKILL.md) alongside [Remotion best practices](.claude/skills/remotion-best-practices/SKILL.md) for editing and review.

## Where things live

- `ss.ps1` defines commands. [Command reference](docs/COMMANDS.md) · [Inventory and capability status](docs/INVENTORY.md)
- `scripts/` runs the pipeline and collectors. `roblox-native/`, `remotion/` and `dashboard/` hold the filming, render and dashboard tools.
- `config/glossary.json` holds game terms and corrections. `config/formats.json` holds video looks. `config/research/` holds query sets, watchlists and codebooks.
- Keep source footage in `media/`, models in `models/`, and private research and dashboard data in `data/local/`. Use `exports/share/` for cleared handoffs. Use `out/dashboard_demo/` for dashboard fixtures. [Data layout](docs/OPERATIONS.md#folders)
- Run the corresponding offline tests and `ss smoke --research` or `ss smoke --dashboard` after changes in those areas. [Testing](README.md#testing)

## Attribution

Use only the owner's name on commits, pull requests, tags and release notes. Omit AI co-author trailers and AI-generated signatures.
