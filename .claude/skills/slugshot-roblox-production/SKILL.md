---
name: slugshot-roblox-production
description: Roblox-native filming for Slugshot marketing. Use when planning, staging, filming or capturing anything in Roblox Studio for Slugshot videos (staged scenes, comedy skits, dances, story scenes, cinematic shots, spectator/second-angle gameplay capture, Roblox-to-anime/manga bridge frames), when writing or validating scene specs, when using the Roblox Studio MCP tools from this repo, or when moving Roblox footage into the ss editing workflow. Pairs with slugshot-video-editing (creative judgement) and remotion-best-practices (template API).
---

# Slugshot Roblox-native production

**Roblox first, AI-enhanced second.** Most Slugshot videos are real Roblox footage: gameplay, staged Roblox scenes, Roblox-native comedy, characters and cinematics, filmed in an isolated copy of the game. Flow, manga and anime tools only add short cutaways (1-4 s) with a narrative job: exaggeration, fantasy, punchline setup.

Status: infrastructure validated with stand-ins (`roblox-native/README.md`). Animation libraries, finished sets, real PvP recording and campaign content are deferred to production preparation (`docs/production-checklist.md`).

## Hard rules

1. **Studio target.** Roblox Studio MCP tools may only act on `SlugshotMarketing.rbxlx`, and it must be the only Studio window open. A PreToolUse hook enforces this and fails closed. Never try to get around it: no launching `StudioMCP.exe`/`mcp.bat` yourself, no settings edits to loosen it. Details: [references/studio-safety.md](references/studio-safety.md).
2. **Game repo.** `../slugshot` may be read and copied from. Don't modify, build, commit or push it without the owner's explicit request. The only sanctioned exception is `ss roblox switch`, run when the owner asks: it stops a playtest, saves and closes whatever is open, and opens the marketing place.
3. **No publishing, uploads or spending** without approval: never publish the marketing place; asset insertion, AI generation, image upload, Open Cloud and sub-agent tools ask first.
4. **Truth classification on every scene and take.** Modes:
   - `authentic_gameplay`: real play. Captured, never staged by the runner.
   - `staged_gameplay`: real mechanics, scripted outcome.
   - `staged_fiction`: a story or skit; must carry a disclosure label.
   - `hybrid_bridge`: a Roblox shot built to cut to or from an AI cutaway; also labelled.

   Fields: `source`, `gameplay_mechanics` (real/none/fictional), `match_outcome` (organic/scripted/n/a). A scripted match is never presented as organic.
5. **Canon.** Re-check `docs/game-truth.md` and `../slugshot/docs/status.md` before showing a mechanic. **Floppy never transforms or uses abilities**: the validator and runtime both reject it. Don't invent abilities, maps or rules for gameplay modes; fiction is labelled.
6. **Rights.** Original or licensed animations, dances, sounds and assets only, recorded in `roblox-native/library/library.json` with source and licence. Don't copy a creator's recognisable choreography. RoPlay (non-commercial licence) and Motion Tools (no licence) must not be integrated.

## Workflow

1. **Brief to spec.** A creative brief (ChatGPT), or an edit idea, becomes a JSON scene spec in `roblox-native/scenes/<group>/<id>.json`. Format: [references/scene-specs.md](references/scene-specs.md). Reuse sets, marks, camera presets and library entries; don't hand-write one-off Luau.
2. **Validate**: `.\ss roblox validate`. Fix every error; never weaken a canon check to pass.
3. **Build into the place**: `.\ss roblox rebuild`. This saves and closes the marketing place, rebuilds it from the game snapshot with the runtime and all valid scenes, and reopens it.
4. **Film:** `list_roblox_studios`, then `start_stop_play(true)`, then `execute_luau` (Client) `require(game.ReplicatedStorage.SlugshotMarketing.Scene).runJson("<id>", {take = "<id>_v01"})`. Record with OBS (production) or Studio `video_capture` (previews; drops frames). Details and handoffs: [references/capture-and-handoff.md](references/capture-and-handoff.md).
5. **Check repeatability** when takes will be intercut: `.\ss roblox compare takeA.json takeB.json`.
6. **Into the toolkit**: `.\ss roblox import <take.json> <video>` trims to the take markers, runs `ss import`, and keeps the take manifest beside the footage. From there, everything is the existing workflow (`ss candidates`, `caption`, `assemble`, `render`, `batch`, `qc`, `sheet`) and the `slugshot-video-editing` skill.
7. **Human gates:** canon check, animation approval, recording approval, publication approval. Claude reports what it can't judge (performance, humour, whether it looks like Slugshot).

## Bilingual reuse

Film one language-neutral plate: no baked-in text, and dialogue only if the scene needs it. English and Spanish versions differ in narration, captions, on-screen text and joke timing, which are done downstream in `ss assemble` with separate scripts. When timing must differ per language, adjust scene beat times in a language-specific spec copy rather than stretching one edit.

## What's built vs deferred

- **Built:**
  - spec validation (structure, references, canon, truth);
  - the runner on Reel (MIT, commit 4b810e9) with set, marks, actors (stand-ins, clones of place models), timed actions (move_to, face, hop, animate), VFX/sound cues, markers and take manifests;
  - 9 camera presets;
  - reset per take, plus the take bridge into `ss import`.
- **Deferred:**
  - the animation library (Animation Editor and R15 Animation Capture, owner-approved);
  - facial expressions (only on rigs with FaceControls);
  - finished sets with named marks in the game environments;
  - real slug rigs as actors (clone from the place once spawned);
  - multi-client staged gameplay (StudioTestService);
  - OBS WebSocket automation (documented only);
  - a replay recorder (only if replay filming proves valuable).
