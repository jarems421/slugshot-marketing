---
name: slugshot-roblox-production
description: Roblox-native filming for Slugshot marketing. Use when planning, staging, directing, filming or capturing anything in Roblox Studio for Slugshot videos (dialogue skits, reaction scenes, story and lore scenes, cinematic shots, staged gameplay, Roblox-to-anime/manga bridge frames), when writing or validating scene specs, when directing character acting or cameras, when using the Roblox Studio MCP tools from this repo, or when moving Roblox footage into the ss editing workflow. Pairs with slugshot-video-editing (creative judgement, visual direction) and remotion-best-practices (template API).
---

# Slugshot Roblox-native production

Follow the [production quality bar](../../../docs/production-quality.md) and [Studio safety](references/studio-safety.md).

Set a truth class on each scene and take. Use staged_gameplay, staged_fiction or hybrid_bridge, with the required label on fiction and bridges. Use authentic_gameplay only for a captured match. Check the [game facts](../../../docs/game-truth.md) before staging any mechanic. Record original or licensed material in the scene library or asset licence register.

## Workflow

1. **Script first.** `jobs/dialogue/<id>.txt` (cast script) → `.\ss dialogue <file>`.
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

## Places, crowds and framing (2026-11-27)

- **Sets**: the hub plaza, Slug Grove and training arena, plus temporary locations (`bedroom`, `classroom`, `wild_cavern`, `market`) via `"set": {"kind": "location", "location": "<name>"}`, which bring their own named marks. Spots, origins and how to add a location: [references/sets.md](references/sets.md).
- **Background life**: an `ambient` block adds dressed extras and slugs (a busy hangout for talking scenes; nobody, a ring of watchers or a scatter for duels), the grove's recreated residents, and crowd `reactions` anchored to script lines. Format: [references/scene-specs.md](references/scene-specs.md).
- **Floors**: saved floor maps keep extras off cracks; the runtime grounds every actor on solid floor. `ss roblox validate` warns about hero marks on a crack.
- **Framing**: wider by default (`wide`, `medium`, close-ups only for reactions and tension, marked `tight`). Fix every validator framing warning before filming: [references/directing.md](references/directing.md).

## Bilingual reuse

One language-neutral performance per language: each language gets its own dialogue manifest, and the same spec re-times to it (copy the spec, change `dialogue`). No baked-in text.
