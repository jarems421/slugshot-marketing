# Slugshot Marketing production cleanup, November 2026

The cleanup is on `cleanup/production-pass`, based on `5ee3b75`. Five phase commits use the owner's existing Git identity. The branch was prepared in a separate worktree for review before merging.

## Documentation inventory and moves

| Classification | What stays current |
|---|---|
| Living reference | [README](../README.md), [command reference](../docs/COMMANDS.md), [operator guide](../docs/OPERATIONS.md), [inventory](../docs/INVENTORY.md), [game truth](../docs/game-truth.md), [knowledge banks](../docs/knowledge-banks.md), [dashboard guide and screenshots](../docs/dashboard/README.md), [creative references and music](../docs/creative/README.md), and the [handoff pack intro](../docs/pack-intro.md). |
| Policy | [Agent brief](../CLAUDE.md), [research data and provider boundaries](../docs/research-data.md), [YouTube API policy](../docs/youtube-api-policy.md), [Composio](../docs/composio.md), [audience-sentiment rules](../docs/audience-sentiment.md), [publishing](../docs/dashboard/publishing.md) and [credentials](../docs/dashboard/credentials-checklist.md). |
| Methodology | [Research methods](../docs/research-methods.md), [evidence ledger](../docs/research-evidence.md), [reference packs](../docs/creative/reference-packs.md) and [production quality](../docs/production-quality.md). The five Slugshot skills and their reference modules are operating guides. The installed hypothesis generation, Remotion, surveying, synthesis and bibliography skill trees retain their upstream methodology and provenance. |
| Dated stage, handoff or report | [Documentation archive](../docs/archive/) and [report archive](archive/). The three smoke reports stay at their stable paths. |

- The old agent brief moved to [CLAUDE-setup-brief-2026-11-24.md](../docs/archive/CLAUDE-setup-brief-2026-11-24.md). The replacement is about 850 words.
- The research audit and methodology snapshot, Stage 4.5.3 and 4.5.4 handoffs, strategy and creator validation snapshots, draft activation events, dashboard preparation notes and early tool review moved under [docs/archive](../docs/archive/README.md).
- The earlier Flow/Gemini handoff, production checklist and review log moved to the documentation archive. The current handoffs and quality checks are in [production quality](../docs/production-quality.md). The reference-pack pilot and original toolkit pack intro were preserved alongside their shorter replacements.
- Dashboard implementation, redesign and live integration validation, the setup and readiness reports, the old skill review and both superseded targeted smoke reports moved under [reports/archive](archive/). Historical screenshots point to the commit that contained them. The current smoke check filenames remain stable.
- Ten completed TikTok scripts moved to [the pilot script archive](../docs/archive/tiktok-genre/). They cover the Gemini ledger, review and listening passes, narrator experiments and voice measurements, and the audio and soundboard experiments. Retained tools and existing inputs are listed in [COMMANDS](../docs/COMMANDS.md#tiktok-genre-research).

## Conflicts resolved

| Area | Current rule or state |
|---|---|
| TikTok and Creative Center | We have permission for the toolkit's existing TikTok collection through Apify. A person reads Creative Center. Browser, clipboard and third-party import descriptions now reflect that boundary. Confirmation correspondence is outside the repository. |
| Infrastructure and ownership | The dashboard, commercial funnel and initial knowledge banks already exist. The infrastructure freeze governs current work. Only the owner approves posts, destructive changes, spending outside agreed caps and game-repo changes. |
| Posting visibility and reveal lock | The owner approves each upload in the dashboard by typing the handle. Public posting and the reveal lock are separate. The lock checks game references on non-private posts, and the owner confirms the video before public posting. |
| Platform metrics | Owner screens may label combined platform-reported counts. Share exports keep placements separate by platform, and comparisons use one platform and matched age windows. Missing metrics stay blank. |
| Twitch and causal claims | Twitch exports stay local unless provider permission is confirmed, the owner approves and the gate is enabled. Campaign causal claims require Slugshot's own controlled tests. Published research stays within its design and population. |
| Production | Native 1080×1920 staged footage uses film mode with zero repeated frames. OBS remains the real gameplay capture route. The dashboard records posting and comparison results. |
| Command and readiness claims | The command table includes references, the guided Creative Center session and hosting. Test counts follow the suites, and smoke counts distinguish production, research and dashboard runs. Readiness distinguishes validated connections and draft routes from a real approved post. |

## Code and validation

- TikTok helpers now use shared paths, single entry points and local fixtures for pagination, subtitle and transcription handling, sampling, export and narration measurements. The old and new builders produced six byte-identical files from a 175-post fixture. All nine retained command help screens worked without credentials.
- Paths use the checkout, the shell's FFmpeg lookup or the configured FFmpeg value. The MakeMyClip launcher was checked with a fixture CLI for confinement and FFmpeg selection. Roblox provenance records a portable source locator where possible.
- Ruff passed for maintained Python. Dead imports and assignments were removed, and fixture error responses confirmed that Gemini and Lyria error messages redact their key. The TikTok download tests check that the Bearer token is scoped to the Apify API.
- The handoff pack built successfully. A scan of 209 tracked Markdown files checked 426 relative links and found zero broken file or heading targets.

| Check | Baseline | Final |
|---|---|---|
| Project offline suites | 173 run, 172 passed, 1 FFmpeg calibration skipped | 183 run, 182 passed, 1 FFmpeg calibration skipped |
| Pinned scholarly offline suites | 207 run, 206 passed, 1 known Windows failure on a POSIX-path assertion | 207 run, 206 passed, 1 POSIX-path assertion explicitly skipped on Windows |
| `ss smoke --research` | 7 passed, 1 warning, 2 credential blocks | 7 passed, 1 warning, 2 credential blocks |
| `ss smoke --dashboard` | 6 passed, 1 warning | 6 passed, 1 warning |
| Ruff | Added in Phase 4 | Passed in the minimal Windows test environment |

The Phase 1–4 results matched the serial baseline. Initial parallel attempts shared ports and fixture paths, so the results above use the serial run. Before the fixture-path fix, publishing tests used disposable files inside the empty cleanup worktree. They now use an OS temporary directory. Existing SQLite fixture resource warnings appeared during unittest runs. The project suites run in separate processes to isolate fixture state. The final runner was exercised with the same minimal Python 3.13 dependencies as the GitHub workflow. The hosted workflow awaits a remote run. The final smoke reports show which checks used public providers, mocked fixtures or loopback. [Research smoke](smoke-test-research.md) · [Dashboard smoke](smoke-test-dashboard.md)

## Left alone

- The active video checkout, game repo, local credentials, media, private data and model files were kept outside this pass. The full production smoke report is the existing configured run. Repeating it here would need the real workspace's sample media and model setup. [Full production smoke](smoke-test.md)
- The research run lacked YouTube and Twitch credentials and the private evidence example. The dashboard run lacked the private knowledge bank. The tested dashboard server check was a loopback health request. No provider upload or paid Actor run was part of validation.
- The existing approval, reveal-lock, vault, Studio guard and provider checks remain in place. Vendor code stayed outside the cleanup. Link edits cover uninstalled upstream references and one Remotion heading. The separately edited Studio provenance file may need reconciliation when the branches are eventually merged.
