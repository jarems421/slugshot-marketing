# Slugshot Marketing

**An AI-operated marketing production and research toolkit for *Slugshot*, a Roblox creature-combat PvP game in development.**

This repository is the working machinery behind Slugshot's short-form video marketing on TikTok, YouTube Shorts and Instagram Reels, in English and Spanish. It does two jobs:

1. **Make videos:** capture, narration, captions, vertical renders, multi-scene edits, automatic quality checks, and Roblox-native filming in an isolated copy of the game.
2. **Do research:** collect dated, labelled public data (YouTube, Google Trends, Wikipedia, Twitch, Roblox, TikTok Creative Center observations), check it, and turn it into findings that are traceable and evidence-led, rather than "AI vibes".

It is built to be **operated by an AI agent**. [Claude Code](https://code.claude.com/docs/en/overview) runs the toolkit from short natural-language instructions ("collect today's research", "is this meme still growing?", "make the Floppy duel edit"). ChatGPT designs research and writes scripts; Gemini/Flow analyses footage and generates visuals; the owner makes decisions and approves anything consequential.

> Status (24 Nov 2026): infrastructure is complete. That covers research collection, research intelligence, and the research configuration with a first validated pilot (Stage 4.5.5). The project is now in **active research and marketing**, and new infrastructure is added only when a specific decision needs it. Production validation with real gameplay and real posts hasn't started; the game is unreleased. See [docs/INVENTORY.md](docs/INVENTORY.md) for the status of every capability.
>
> Remaining milestones:
> 1. **Foundational marketing research and initial knowledge banks.** Bounded literature reviews and creative hypotheses, starting with short-form attention, curiosity, narrative comprehension and payoff.
> 2. **Commercial funnel.** Acquisition, attribution, activation, retention and monetisation: definitions and an implementation plan.
> 3. **Centralised dashboard.** A minimum viable view of research, experiments, content and player outcomes.

---

## How it fits together

```mermaid
flowchart LR
    Owner([Owner: decisions & approvals])
    GPT[ChatGPT: research design, culture, scripts]
    Gem[Gemini / Flow: footage analysis, visuals]
    subgraph Repo [This repo, run by Claude Code]
        Collect[Collectors: YouTube, Trends, Wikipedia, Twitch, Roblox, observations]
        Analyse[Analysis + evidence ledger]
        Bundle[(Research bundle zip)]
        Produce[Video production: captions, renders, assembly, QC]
        Roblox[Roblox-native filming: isolated place, scene runner]
    end
    Owner --> GPT
    GPT -- brief --> Collect --> Analyse --> Bundle --> GPT
    GPT -- approved script --> Produce
    Gem -- clips & timestamps --> Produce
    Roblox --> Produce
    Produce -- masters for review --> Owner
```

- **Claude** collects, validates, computes, edits and films. It runs commands itself: the `ss` CLI is Claude's interface, not the owner's.
- **ChatGPT** owns research methodology, cultural interpretation and creative strategy.
- **The owner** approves spending, publishing, destructive operations and changes to the game repository; everything else that is free and reversible is pre-approved.

## What it can do

### Video production
| Capability | Command |
|---|---|
| Import OBS captures with a naming convention | `ss import` |
| AI narration (Kokoro, local) or recorded voice clean-up, music ducking, SFX | `ss voice`, `ss audio` |
| Whisper captions with automatic correction of Slugshot terms | `ss caption`, `ss fixcaps` |
| 1080×1920 renders from format presets (Remotion), variants, multi-scene edits synced to a script | `ss render`, `ss batch`, `ss assemble` |
| Gemini-timestamped clip candidates, frame sheets, technical QC (loudness, black/frozen frames, codecs) | `ss candidates`, `ss sheet`, `ss qc` |
| Timeline editing through MakeMyClip (confined to `media/`) | `ss clip` |

Creative judgement (pacing, cuts, captions, audio, formats) lives in a Claude skill with evidence-labelled rules: [`.claude/skills/slugshot-video-editing`](.claude/skills/slugshot-video-editing/SKILL.md).

### Roblox-native filming
Staged scenes and skits are filmed in an **isolated marketing copy** of the game, with DataStores disabled. A hook enforces that Claude's Roblox Studio MCP calls can only touch that place. Declarative JSON scene specs drive a scene runner (camera presets, timed actions, VFX/sound cues) and give repeatable takes. Details: [roblox-native/README.md](roblox-native/README.md).

### Research data collection
| Source | What it gives | Command |
|---|---|---|
| YouTube Data API | bilingual searches, regional gaming charts, creator uploads (ordinary ones too), comments, confirmed Shorts, per-video history | `ss yt` |
| Google Trends | Trending Now feeds for 7 markets; importer for Explore CSVs | `ss trends` |
| Wikipedia | daily page views back to 2015 in English and Spanish, redirects resolved | `ss wiki` |
| Twitch | Roblox clips and live streams by broadcaster language | `ss twitch` |
| Roblox | player/visit/favourite snapshots for a small watchlist | `ss rbx` |
| TikTok Creative Center, vidIQ, TinyFish, manual | validated public observations with provenance; a guided Creative Center session (you press Ctrl+A, Ctrl+C; it does the rest) | `ss observe` |
| One instruction | run a profile, then a bundle for ChatGPT | `ss research collect`, `ss research bundle` |

### Research intelligence
Turning data into findings that can be checked:
- **Bundle intake QC:** what each dataset is, its scope, expiry, missingness, rounding and what it *cannot* answer.
- **Deterministic analysis:** statistics with explicit denominators, same-item repeated observations, sensitivity checks (is the finding fragile?), trend dimensions kept separate (heat, velocity, breadth, persistence, novelty, fit) with a rule-based lifecycle proposal, change-point detection on long series, Wikidata/GDELT context.
- **Outcome-blind qualitative coding:** creative features are coded before performance is revealed, so "it went viral" can't contaminate "it has a good hook".
- **Evidence ledger:** every claim carries a level (observation → derived statistic → pattern → interpretation → causal → recommendation), a support status (supported / partially supported / unsupported / indeterminate), a verbal strength (exploratory → experimental) and exact references to bundle rows or quoted passages. A validator catches common overclaims, for example one snapshot called "accelerating", a Spanish search called "Mexican viewers", correlation written as causation, or a blank read as zero.
- **Literature verification:** installed skills check that cited papers exist and match their DOIs, and survey a field (OpenAlex, Crossref, Semantic Scholar, arXiv, dblp).

Commands: `ss analyze`, `ss evidence`. Guides: [research methods](docs/research-methods.md), [evidence ledger](docs/research-evidence.md).

## Principles built into the code

- **Missing is unknown, never zero.** Rounded figures stay as displayed, with their numeric value alongside.
- **Provenance on every row** (P1 platform count, P2 index/rank, P3 third-party estimate, P4 interpretation) and a run log with the exact parameters sent.
- **Provider rules are enforced, not just documented:**
  - YouTube statistics expire after 30 days, including exported copies, and are never aggregated across channels or turned into scores.
  - Twitch data is kept 24 hours and stays local.
  - TikTok Creative Center is only read by a person (TikTok's terms bar automated collection).
- **No composite "viral scores".** Heat and confidence are different things.
- **Retrieval is not audience.** A video found with a Mexico filter says nothing about Mexican viewers.
- **Rigour serves experiments, not paralysis.** Suggestive evidence can justify a cheap 15-second test; only our own experiments can support causal claims.
- **Credentials stay in a git-ignored `.env`.** They are never printed or logged, and errors are redacted.

## Getting started

Requirements (Windows): Git, Python 3.13, Node 24, FFmpeg; OBS Studio and Kdenlive optional. Exact versions are in [docs/INVENTORY.md](docs/INVENTORY.md).

```powershell
git clone https://github.com/jarems421/slugshot-marketing.git
cd slugshot-marketing
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
py -3.13 -m venv .venv-tts; .venv-tts\Scripts\python -m pip install -r requirements-tts.txt   # optional AI narration
npm ci
copy .env.example .env    # then add YOUTUBE_API_KEY / TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET (all free tiers)
.\ss doctor               # tool check
.\ss smoke                # end-to-end smoke test -> reports\smoke-test.md
```

The Kokoro voice model and sample media aren't in the repo (they live in `models/` and `media/`, both git-ignored).

### Using it
With Claude Code open in this folder, ask in plain language:

```text
Collect today's research.
Research Spanish Roblox comedy.
Is the Huss meme still growing?
Analyse our latest research bundle.
Find academic research on short-form hooks and verify the key findings.
Make a vertical edit of this match with the PVP preset and captions.
```

Or run the commands directly: every `ss` command takes `-h`. Full reference: [docs/COMMANDS.md](docs/COMMANDS.md); walkthrough: [docs/OPERATIONS.md](docs/OPERATIONS.md).

## Repository layout

```
ss.ps1 / ss.cmd          the CLI entry point (PowerShell)
scripts/                 production pipeline, research collectors, analysis, evidence ledger
remotion/                Remotion compositions (vertical template, multi-scene story)
roblox-native/           isolated marketing place builder, Studio guard, scene runner, scene specs
.claude/skills/          Claude skills: video editing, Roblox production, research operations,
                         research analysis + installed upstream research skills
config/                  formats, glossary, research settings, query families, watchlists, codebook
research/                evidence-ledger schema, templates, upstream provenance
docs/                    commands, inventory, research guides, policies, game truth, handoffs
tests/                   offline tests and fixtures (fake data)
jobs/                    example edit, variant and script files
reports/                 latest smoke-test reports
data/templates/          import templates (raw research data in data/local/ is git-ignored)
```

Not in git: `.env`, `media/`, `exports/`, `data/local/`, `models/`, `out/`, `vendor/`.

## Documentation

| Topic | File |
|---|---|
| Every command | [docs/COMMANDS.md](docs/COMMANDS.md) |
| Operator walkthrough, folders, CSV schemas | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| Status of every capability | [docs/INVENTORY.md](docs/INVENTORY.md) |
| Research collectors, data contract, sharing rules | [docs/research-data.md](docs/research-data.md) |
| Research methodology (ChatGPT skills v1.1, authoritative) | [docs/chatgpt-research-skills-v1.1.md](docs/chatgpt-research-skills-v1.1.md) |
| Research methods / evidence ledger | [docs/research-methods.md](docs/research-methods.md) · [docs/research-evidence.md](docs/research-evidence.md) |
| Source audit and decisions | [docs/research-data-audit.md](docs/research-data-audit.md) |
| YouTube API rules | [docs/youtube-api-policy.md](docs/youtube-api-policy.md) |
| Flow and Gemini hand-offs | [docs/flow-and-gemini.md](docs/flow-and-gemini.md) |
| Game facts for marketing claims | [docs/game-truth.md](docs/game-truth.md) |
| ChatGPT handoff (Stage 4.5.3) | [docs/chatgpt-handoff-4.5.3.md](docs/chatgpt-handoff-4.5.3.md) |
| Stage 4.5.4 configuration and 4.5.5 pilot validation | [docs/stage-4.5.4-report.md](docs/stage-4.5.4-report.md) |
| Composio (read-only OAuth broker) | [docs/composio.md](docs/composio.md) |
| Agent brief and working rules | [CLAUDE.md](CLAUDE.md) |
| Strategy (Marketing Bank snapshot) | [docs/Slugshot-Marketing-Bank.md](docs/Slugshot-Marketing-Bank.md) |

## Testing

- `ss smoke` runs every capability once and writes a PASS / WARN / FAIL / BLOCKED report. Latest: 23/23 PASS ([reports/smoke-test.md](reports/smoke-test.md)).
- `ss smoke --research` runs only the research checks (about 30 s).
- Offline suites: `python -m unittest tests.test_research tests.test_analysis` (51 tests on fake fixtures, no network).

## Third-party components

| Component | Licence | Where |
|---|---|---|
| Remotion | [Remotion licence](https://www.remotion.dev/docs/license) (free tier for individuals and small teams) | npm |
| MakeMyClip editor | MIT | npm |
| OpenAI Whisper | MIT | pip |
| Kokoro-82M model via kokoro-onnx | Apache-2.0 (model) | pip, model downloaded separately |
| ruptures, SciPy | BSD | pip |
| Reel (roblox-reel) | MIT | `roblox-native/runtime/vendor/Reel/` |
| remotion-dev/skills: remotion-best-practices | as published by Remotion (see `SOURCE.txt`) | `.claude/skills/remotion-best-practices/` |
| claude-skills-research: verifying-bibliography, surveying-literature | MIT | `.claude/skills/` (licence in `_shared/`) |
| synthesis-skills: synthesis-fact-checking | CC0-1.0 | `.claude/skills/` |
| K-Dense scientific-agent-skills: hypothesis-generation | MIT | `.claude/skills/` |
| EvidenceGuard schema and evals | MIT | `research/upstream/evidenceguard/` |

Pinned commits and adaptations: [research/upstream/PROVENANCE.md](research/upstream/PROVENANCE.md).

Slugshot, its characters and its game design belong to the game's owner. No licence has been chosen yet for this repository's own code. Slugshot is an original game and is not affiliated with Slugterra or its rights holders.
