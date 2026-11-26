---
name: slugshot-roblox-production
description: Roblox-native filming for Slugshot marketing. Use when planning, staging, directing, filming or capturing anything in Roblox Studio for Slugshot videos (dialogue skits, reaction scenes, story and lore scenes, cinematic shots, staged gameplay, Roblox-to-anime/manga bridge frames), when writing or validating scene specs, when directing character acting or cameras, when using the Roblox Studio MCP tools from this repo, or when moving Roblox footage into the ss editing workflow. Pairs with slugshot-video-editing (creative judgement, visual direction) and remotion-best-practices (template API).
---

# Slugshot Roblox-native production

**Roblox first, AI-enhanced second.** Most Slugshot videos are real Roblox footage, filmed in an isolated copy of the game:
- gameplay;
- staged scenes and Roblox-native comedy;
- characters and cinematics.

Flow, manga and anime tools only add short cutaways (1-4 s) with a narrative job.

Status (2026-11-25): the deterministic performance engine is built and real-asset tested. Real slug rigs act through the game's own `SlugIdle`/`FloppyFace` code, mouths and eyelines follow the dialogue, and takes are filmed frame by frame at native resolution. Results, register and limits: `docs/production-quality.md`.

## Quality bar (owner rules, 2026-11-25: non-negotiable)

1. **Resolution and completeness.**
   - Vertical footage comes from **film mode** (rolled camera, native pixels, exact 30 fps) and `ss roblox film`, never from a centre crop of a landscape recording.
   - A take is usable only when the decoder reports **0 repeated frames**. Patch missing ranges; don't accept duplicates.
   - Always check the decoded footage (contact sheet or frames) before showing anyone.
2. **Story-matched performance, never random snippets.**
   - Every shot and every acting beat has a job in the script: who matters now, what they feel, what changes.
   - Anchor cuts and beats to dialogue lines (`"until": "L3.end+0.3"`, `"time": "L6.end+0.4"`). Don't eyeball seconds.
   - "This is Floppy": the camera pushes in *as* his name is said; he turns and smiles *on* the beat.
   - Never use an idle loop as a stand-in for acting, and never use a shot just because it looks nice.
3. **Look before you claim.** Judge from real frames (`video_capture` grabs; `screen_capture` without camera arguments is unreliable in play mode). Say what needs the owner: humour, voice, "does it feel like our world".

## Hard rules

1. **Studio target.**
   - Studio MCP tools may only act on `SlugshotMarketing.rbxlx`, and it must be the only Studio window open.
   - A PreToolUse hook enforces this and fails closed. Never get around it: no launching `StudioMCP.exe`/`mcp.bat`, no settings edits.
   - Details: [references/studio-safety.md](references/studio-safety.md).
2. **Game repo.**
   - `../slugshot` may be read and copied from. Never modify, build, commit or push it.
   - `ss roblox switch` runs only when the owner asks. `ss roblox rebuild`, with only the marketing place involved, is the normal workflow.
3. **No publishing, uploads or spending** without approval. Never publish the marketing place. Asset insertion, AI generation, image upload, Open Cloud and sub-agent tools ask first.
4. **Truth classification on every scene and take.**
   - `staged_gameplay`, `staged_fiction` (label) or `hybrid_bridge` (label). `authentic_gameplay` is captured, never staged.
   - A scripted outcome is never presented as organic.
5. **Canon.**
   - Re-check `docs/game-truth.md` and `../slugshot/docs/status.md` before showing a mechanic.
   - **Floppy never transforms or uses abilities.** Validator and runtime reject it; a `slug` actor's species sets its canon identity.
   - Floppy deals 7 damage: never "does nothing".
   - Fantasy or "what if" feats are unmistakable fiction, labelled, and never a new canon power.
6. **Rights.**
   - Original or licensed assets only, recorded in `roblox-native/library/library.json` or `assets/LICENSES.csv`.
   - No copied franchise designs, footage, music or dialogue. Slugterra is a feeling to evoke, not a source to copy.

## Workflow

1. **Script first.** `jobs/dialogue/<id>.txt` (cast script) → `.\ss dialogue <file> --engine qwen --mode clone`.
   - Read the flagged deviations. Re-do one line with `--only N`.
   - The manifest `out/dialogue/<id>/dialogue.json` is the single timing source.
2. **Direct the spec.**
   - Write `roblox-native/scenes/<group>/<id>.json` with `"dialogue"` pointing at the manifest. Format: [references/scene-specs.md](references/scene-specs.md).
   - Apply [references/directing.md](references/directing.md): shot choice, the 180° line, eyelines, vertical framing, acting beats, comic timing.
3. **Validate**: `.\ss roblox validate`. Fix every error; never weaken a canon check.
4. **Build**: `.\ss roblox rebuild`, then `start_stop_play(true)` and wait about 7 s for the game to load.
5. **Look at stills**:
   - `execute_luau` (Client): `Scene.still("<id>", t)`.
   - Then a 1-2 s `video_capture` to see the real viewport. Fix framing before filming.
6. **Film**: [references/capture-and-handoff.md](references/capture-and-handoff.md).
   - In short: chunks of ≤ about 170 frames, each inside its own `video_capture`, via `Scene.start("film", id, {first, last, hold = 6})`.
   - **Copy each recording to `media/takes/` immediately**: Studio deletes its capture folder when play restarts.
7. **Decode**: `.\ss roblox film <take.json> <chunk1.mp4> <chunk2.mp4> ...`. Patch any listed range with another `first/last` pass and decode again with all recordings.
8. **Edit**: `ss assemble` with `"dialogue"` (slugshot-video-editing skill), then `ss sheet` and watch.
9. **Human gates**: canon check, performance and voice approval, publication approval.

## Actors and acting (what's available)

- **Real slugs**: `{"kind": "slug", "species": "Floppy|Inferno|Aquabeek|Rammstone|Tormato|BoonDoc|Phosphoro"}`.
  - Clones the rig from `ReplicatedStorage.CombatAssets` (icon pose).
  - Inked with a charcoal Highlight, performed by `SlugIdle`. Floppy's face comes through `FloppyFace`.
- **Acting channels** (`express`, eased): `smile`, `react` (each slug's in-character "notice" answer), `angry` (Rammstone's grimace), `look_up`, `squint` (Floppy's lids), `lean`, `open` (mouth).
  - Plus `look` (eyeline), `face` (turn), `move_to`, `hop` (anticipation, arc, landing squash) and `blink`.
- **Automatic**:
  - mouths follow each line's loudness;
  - talkers nod on stressed syllables;
  - listeners look at whoever is speaking (turn off per actor with `"auto_look": false`).
- **Faces per species**:
  - Floppy: eyes, lids, gaze, mouth.
  - Aquabeek: eyes, lids, mouth.
  - Rammstone and Boon Doc: mouth only (painted eyes); they act with head and body.
  - Tormato: spinning eyes, mouth.
  - Inferno: shaped mouth bones not yet driven.
  - Phosphoro: no face bones.
- **Humans** (2026-11-26): `{"kind": "human", "human": "kai|mira|raf|juno"}` (or an inline `look`). Blocky R6 like the game's players (owner's R6 ADR). Details and the move list: [references/humans.md](references/humans.md).
  - `move_to` takes `gait`: walk, run, sprint, back. Feet follow distance travelled; starts and stops ease.
  - `gesture` (a `human_moves` entry, over a body `mask`), `aim` / `point` (at an actor or mark), `shoot`, `equip` / `holster` (needs `"blaster": true|false`; `loaded` picks the slug in the chamber), `hold` (a slug in one or both hands, `facing` holder|out).
  - The same `express` channels, `look`, `face`, dialogue mouths, nods and auto eyelines as slugs; an inked face drawn from parts blinks, glances and talks.

## Bilingual reuse

One language-neutral performance per language: each language gets its own dialogue manifest, and the same spec re-times to it (copy the spec, change `dialogue`). No baked-in text.
