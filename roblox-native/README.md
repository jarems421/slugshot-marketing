# Roblox-native production (Slugshot marketing)

**Roblox first, AI-enhanced second.** Most Slugshot videos are real Roblox footage: gameplay, staged scenes, Roblox-native comedy, characters and cinematics, filmed in an isolated copy of the game. Flow and other AI tools add short anime/manga/cinematic cutaways only.

Status (2026-11-25): **real slug actors, deterministic film mode and dialogue-driven acting, tested with real assets** (benchmark skit filmed with 3 voices, 0 repeated frames; `docs/production-quality.md`). Status 2026-11-24: infrastructure validated with stand-ins. Claude's working instructions are in the skill `.claude/skills/slugshot-roblox-production/`.

## Commands

| Command | Does |
|---|---|
| `.\ss roblox validate [files]` | checks every scene spec: structure, references, presets, actions, library entries, timing, truth rules, canon |
| `.\ss roblox list` | lists scenes with truth mode and length |
| `.\ss roblox audit` | read-only risk audit of the marketing place (`--json out.json` for the full list) |
| `.\ss roblox build` | rebuilds `studio/SlugshotMarketing.rbxlx` with Studio's marketing window closed (`--source` to use the snapshot instead of the current game build) |
| `.\ss roblox rebuild` | saves and closes the marketing window, rebuilds from the snapshot with the runtime and all valid scenes, reopens it |
| `.\ss roblox switch` | **only when the owner asks:** stops a playtest, saves and closes the open place(s), opens the marketing place |
| `.\ss roblox guard` | runs the Studio target check once and prints the verdict |
| `.\ss roblox compare a.json b.json` | repeatability check between two take manifests (cuts/cues within 50 ms, camera within 0.05 studs / 0.5 deg) |
| `.\ss roblox import take.json video --capture-manifest m.json` (or `--video-start-ms N`) | trims the recording to the take, runs `ss import`, writes `<raw>.take.json` beside it (real-time takes and OBS) |
| `.\ss roblox film take.json rec1.mp4 [rec2.mp4 ...]` | decodes a film-mode take (frame-stamped chunks and patches) into exact 30 fps, native-resolution 1080x1920 in `out/takes/`; lists any frame ranges to re-film |

## Layout

| Path | Contents | In git? |
|---|---|---|
| `studio/` | `SlugshotMarketing.rbxlx` (built place), `.source.rbxlx` (game snapshot), `marker.json`, `provenance.json` | place files no (they hold the game's private asset IDs); json yes |
| `runtime/Scene/` | our Luau engine: `init` (prepare a scene as a pure function of time; drivers `run`, `film`, `still`), `Cameras` (12 presets, portrait roll), `Actors` (real slugs via the game's SlugIdle/FloppyFace, acting tracks, dialogue mouths and eyelines), `Canon` (truth and canon checks) | yes |
| `runtime/vendor/Reel/` | Reel, unmodified (MIT, `SOURCE.txt` records commit 4b810e9) | yes |
| `scenes/<group>/*.json` | declarative scene specs | yes |
| `library/library.json` | animation and sound registry (empty: real animations are production work) | yes |
| `tools/` | Python: build, audit, guard, switch, scene validation, take compare/import | yes |
| `baseline/` | game repo state before this work (HEAD, status hash, build hash) and the source audit | yes |
| `capture/` | take manifests and guard log | no |

## The marketing place

`studio/SlugshotMarketing.rbxlx` is built by `tools/make_marketing_place.py` from a snapshot of the game's integrated place:
- **Source:** `../slugshot/build/SlugshotLobbyTraining.rbxlx` (read only). SHA-256 and game commit are in `studio/provenance.json` (game 08fee46). It keeps the real lobby, training arena, guns, slugs, VFX, HUD and lighting.
- **Marketing-only patches:**
  - both `SettingsStore.connect()` return `nil, "MarketingIsolated"` before any DataStore call (the game already skips DataStores in unpublished files; this holds even if the copy were opened from a published universe);
  - `ServerStorage.SlugshotMarketingMarker` holds the token in `studio/marker.json`, and `SlugshotMarketingProvenance` records the source;
  - `ReplicatedStorage.SlugshotMarketing` holds the runtime (Reel, Scene, Library, Scenes). Only specs that pass validation are injected.
- **Audit** (639 instances, 183 scripts):
  - `asset_by_id` x20: `InsertService:LoadAsset` of the game's own uploaded models. These are reads, kept for fidelity.
  - `persistent_data` x2: the patched `GetDataStore` lines, unreachable.
  - No HTTP requests, cross-server messaging, purchases, teleports, badges, analytics, live config or dynamic code.
- **Never publish this place.** Open it as a local file only.

## Safety boundary (enforced, not just procedural)

A `PreToolUse` hook (`tools/studio_guard.py`, wired in `.claude/settings.json`) runs before **every** Roblox Studio MCP tool call made by Claude Code in this repo, including Luau execution, edits, play mode, input simulation, capture and saves. It opens its own connection to Studio's MCP server and allows the call only if:
1. exactly one Studio window is open;
2. its file is `SlugshotMarketing.rbxlx`;
3. the call targets that window's `studio_id`;
4. `ServerStorage.SlugshotMarketingMarker` matches the token (read in Edit, or Server during play).

Otherwise the call is denied. Errors, timeouts and a crashed hook also deny (`onFailure: block`). Exempt: listing Studio windows, Roblox docs and skill lookups. Decisions are logged to `capture/logs/studio-guard.log`.

Tested live:
- a `get_studio_state` call was denied while the game's TempRange place was open;
- `inspect_instance` was allowed on the marketing place;
- piped tests: a wrong `studio_id`, a call without one and unreadable input were all denied; the correct id was allowed. Each check takes about 0.2 s.
- Not tested live: two windows open at once, or a missing marker. Both are coded as denials.

Also in `.claude/settings.json`:
- **Ask first:** asset insertion, AI generation, image upload, Open Cloud, sub-agent and skill-edit tools (they reach Roblox services under your account).
- **Deny:** starting `StudioMCP.exe` or `mcp.bat` from a shell (that would bypass the hook).

**Limits of this boundary.**
- It covers Claude Code sessions started in this repository. It does not cover other MCP clients (Codex, ChatGPT desktop), sessions started in other folders (such as the game repo), or a person using Studio directly.
- There is a short gap between the check and the call. Switching places in that fraction of a second isn't guarded.
- Shell deny rules match command text. A script written to launch StudioMCP indirectly could evade them; the skill forbids it.
- The check confirms which place is open, not what the code does once allowed. Inside the marketing place, Luau runs with Studio's normal power, so keep the place disposable: it can always be rebuilt.
- `ss roblox switch` saves and closes whatever Studio has open (owner-approved helper). It needs per-session approval, because a local allow rule for it was refused by Claude Code's safety classifier.

## Scene specs and the runner

**2026-11-25:** the runner is now one deterministic engine. Every frame is computed from scene time, so preview, film and still show the same picture, and Reel supplies only the shot maths, cyc and UI clearing. Dialogue-anchored timing, real slug actors and film mode are described in the production skill (`references/scene-specs.md`, `references/capture-and-handoff.md`, `references/directing.md`). The 2026-11-24 notes below describe the first, stand-in version.

The spec format is in the skill (`references/scene-specs.md`). In short:
- `truth` block;
- `set` (cyc void or a place origin) and `marks` (relative positions + yaw);
- `actors` (stand-ins, or clones of models in the place);
- `shots` (camera presets, in order);
- `timeline` beats (actions, VFX/sound cues, markers);
- `capture` settings.

`Scene.runJson(id, {take=...})`, run in the Client datamodel during a playtest:
1. builds the set and actors in Reel's setup;
2. plays the shots as a Reel take with timed beats;
3. samples the camera;
4. destroys everything in cleanup (the reset);
5. returns the take manifest: truth, Reel marks with Unix-ms timestamps, cues, markers, camera samples.

Camera presets: `static_wide`, `two_shot`, `orbit_reveal`, `dolly_in`, `slug_low_angle`, `reaction_closeup`, `follow`, `snap_zoom`, `whip_pan`, each with optional shake. Shots are built when they start, so fixed framings use actor positions at that cut.

Truth modes:
- `staged_gameplay`, `staged_fiction` and `hybrid_bridge` can be staged;
- `authentic_gameplay` is refused by the runner, since real play is only captured;
- fiction and hybrid need an on-screen label.

Canon: Floppy never transforms or uses abilities. Both the validator and the runtime reject it (negative test passed).

## Test results (2026-11-24)

Smoke scene `smoke_floppy_standin`: 7 s, stand-in hero and Floppy, 4 shots, hop, VFX burst, move, markers.

| Test | Result |
|---|---|
| Validation, negative test (Floppy `transform`) | rejected, as intended |
| Takes 1 vs 2 (before lazy shots) | PASS: cuts worst 15 ms, cues 10 ms, camera 0.006 studs / 0.03 deg |
| Takes 4 vs 5 (current runner) | **FAIL against the strict target:** cuts worst 56 ms, cues 80 ms, camera 0.04 studs / 0.3 deg. Caused by a client frame stall (about 2.4 frames). Still close enough to intercut by eye, but not frame-exact. |
| Reset between takes | set and actors destroyed, camera and UI restored, next take starts identical |
| Studio `video_capture` | works: 2368x1104, about 27 fps, but 125 dropped frames and a 1.1 s client stall in one take. Fine for previews, not final footage |
| Clock alignment | the capture manifest's `creation_timestamp_ms` matches Reel's marks; trims land on the first frame |
| `ss roblox import` | 3 takes imported to `media/raw/SS_20261124_STAGED_SmokeFloppyStandin_Take_V01..V03_RAW.mp4` with `.take.json`; ending one frame early drops a lobby frame that came back after the restore |
| Look | real lobby lighting, HUD and environment in shots; stand-ins are placeholders |

## Recording

- **OBS (production):** see the skill's `references/capture-and-handoff.md`. Note when recording starts (Unix ms) and pass `--video-start-ms`.
- **Studio `video_capture`:** for previews and tests only.
- **Automated OBS (not built):** OBS WebSocket (built into OBS 28+, password-protected). Planned sequence: validate -> OBS start -> run take -> wait for end mark -> OBS stop -> `ss roblox import`. Build it once manual recording is routine.

## Third-party decisions

| Project | Licence | Decision |
|---|---|---|
| Reel (zAcherttp/roblox-reel, 4b810e9) | MIT | **used**, vendored unmodified for the pilot |
| CutsceneService (059a60d) | MIT | fallback if Reel fails; not installed |
| Motion Tools (7ff9b0b) | none found | **deferred** until the licence is clarified with the author |
| RoPlay (b7ea47a) | non-commercial | **excluded** |
| roblox-studio-agent-plugin (57d7204) | reviewed | not installed: duplicates the built-in Studio MCP |

Source clones are in `../vendor/` (git-ignored). No plugins were bought or installed.

## Opening the place by hand

1. Save game work and close the game place. Only the marketing place may be open during marketing MCP work.
2. File > Open from File > `C:\Users\runni\slugshot marketing\roblox-native\studio\SlugshotMarketing.rbxlx`.
3. The Studio MCP server must be enabled (Assistant > ... > Settings > MCP Servers); it already is on this machine.

## Deferred (production preparation)

- **Animation library:** original animations (Animation Editor, R15 Animation Capture), the owner's approval per entry, and `library.json` rows with licence.
- **Facial expressions** on rigs that have FaceControls.
- **Finished sets** with named marks in lobby, arena and grove locations.
- **Real slug rigs** as actors (clone from the place once spawned in Edit).
- **Real PvP recording** and multi-client staged gameplay (StudioTestService).
- **Replay recorder** for second angles of real play.
- **Flow cutaways, skits and campaign content.**
- **OBS WebSocket automation.**
- **Motion Tools licence** question.
