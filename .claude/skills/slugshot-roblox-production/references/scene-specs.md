# Scene spec format

One JSON file per scene: `roblox-native/scenes/<group>/<id>.json`, where `id` equals the file name. Validated by `.\ss roblox validate` (`roblox-native/tools/scene.py`) and again at run time (`runtime/Scene/Canon.luau`). Working examples: `scenes/bench/bench_floppy_seven.json` (real slugs, dialogue-anchored) and `scenes/smoke/smoke_floppy_standin.json` (stand-ins).

```json
{
  "id": "floppy_false_aura_001",
  "note": "one line: what this scene is for",
  "format": "vertical",
  "truth": {"mode": "staged_fiction", "source": "staged_runtime", "gameplay_mechanics": "none",
            "match_outcome": "n/a", "label": "Fictional story"},
  "dialogue": "out/dialogue/floppy-false-aura/dialogue.json",
  "set": {"kind": "place", "origin": [x, y, z], "yaw": 0},
  "marks": {"A": [-4, 0, 0, 90], "slug": [2, 0, -2, 0]},
  "actors": {
    "rammstone": {"kind": "slug", "species": "Rammstone", "mark": "A", "face": "floppy", "phase": 2.3},
    "floppy": {"kind": "slug", "species": "Floppy", "mark": "slug", "face": "rammstone"}
  },
  "shots": [
    {"preset": "over_shoulder", "from": "floppy", "target": "rammstone", "until": "L1.end+0.2"},
    {"preset": "slug_low_angle", "target": "floppy", "duration": 1.2}
  ],
  "timeline": [
    {"time": 0.5, "actor": "rammstone", "action": "face", "target": "floppy"},
    {"time": 1.6, "actor": "floppy", "action": "hop", "height": 0.3, "duration": 0.45},
    {"time": 1.8, "cue": {"type": "vfx", "effect": "burst", "actor": "floppy"}},
    {"time": 2.4, "marker": "CUTAWAY_OUT"}
  ],
  "capture": {"ui": "hidden", "sample": 0.5}
}
```

## Fields

- **truth**: required.
  - `mode`: `staged_gameplay`, `staged_fiction` or `hybrid_bridge`. `authentic_gameplay` is rejected, because real play is captured, not staged.
  - Fiction and hybrid scenes need `label` (the on-screen disclosure).
  - `staged_gameplay` can't have an `organic` outcome.
- **set**:
  - `cyc`: Reel's studio void, for tests. It defaults far from the game world; the copied place has huge art high up (the hub storm).
  - `place`: an origin in the game world (preferred for real scenes; keeps Slugshot's look).
- **marks**: `[x, y, z, yawDegrees]`, relative to the set origin. Name them for their job (A, B, slug_hero, reaction_left, camera_low). The same skit then works on another set by changing the marks.
- **dialogue** (optional): path (from the repo root) to an `ss dialogue` manifest. It is inlined at build time. Each line's speaker drives that actor's mouth and nods, and listeners look at the speaker.
- **Times anchored to the dialogue**:
  - Any timeline `time` may be `"L3"`, `"L3.start+0.2"` or `"L3.end-0.1"`.
  - A shot may say `"until": "L2.end+0.3"` instead of `duration`.
  - Anchors resolve when the spec is built, so changing the voice re-times the scene.
- **actors**:
  - `kind`:
    - `slug` (real rig: `species` Floppy, Inferno, Aquabeek, Rammstone, Tormato, BoonDoc, Phosphoro; performed by the game's SlugIdle/FloppyFace; species sets canon identity);
    - `clone` (any Model in the place: `asset` = dotted path; a puppet);
    - `standin_humanoid` / `standin_slug` (tests only).
  - Options:
    - `phase` (seconds into the idle loop, so two slugs don't breathe in sync);
    - `auto_look` (false to stop looking at speakers);
    - `outline` (false to drop the ink);
    - `ground` (false to keep the mark's own height; otherwise actors stand on whatever is below the mark);
    - `scale`.
  - `identity` (e.g. `floppy`) turns on the canon rules for that actor.
  - `face`: an actor or mark to look at on spawn.
- **shots**: played in order, and the take lasts their total. Each shot is built when it starts, so fixed framings use where actors are at that cut.

  | preset | key options |
  |---|---|
  | static_wide | target or targets, distance, height, fov |
  | two_shot | targets [a, b], distance, height |
  | orbit_reveal | target, radius, height, from, to (degrees) |
  | dolly_in | target, from_distance, to_distance, height |
  | slug_low_angle | target, distance, height (low), fov |
  | reaction_closeup | target, distance, aim (head height) |
  | follow | target, offset [x, y, z] |
  | snap_zoom | target, fov, fov_end, snap (seconds): the punch-in |
  | whip_pan | from, to |
  | close_up | target, size (frame height in actor heights; 1.0-1.5), side (deg off the face axis), eye, headroom, fov |
  | push_in | target, from_size, size, side, eye, headroom, fov |
  | over_shoulder | from (foreground actor), target, back, offset, shoulder (1/-1), eye, fov |

  Any shot can add `shake` (amplitude).
- **timeline**: beats at `time` seconds from the first frame. Each beat runs in its own thread.
  - Actions:
    - `move_to` (mark, duration; turns toward the path);
    - `face` (target, duration);
    - `hop` (height in actor heights, duration: anticipation, arc, landing squash);
    - `express` (`set`: smile, react, angry, look_up, squint, lean, open; `ease` seconds);
    - `look` (target actor/mark, or "none");
    - `blink`;
    - `animate` (a library.json animation id; Humanoid/AnimationController rigs).
  - Everything is a pure function of scene time: stills, previews and filmed takes match.
  - `cue`: `{type: vfx, effect, actor}` or `{type: sound, sound}` (a library.json name).
  - `marker`: a named point printed with a Unix-ms timestamp; use CUTAWAY_OUT / CUTAWAY_IN for hybrid bridges.
- **capture**: `sample` = camera sampling interval (s) for repeatability checks.

## Adding things

- **New camera move:** add a preset in `runtime/Scene/Cameras.luau` and its name to `PRESETS` in `tools/scene.py`. Presets read actors as they stand at the shot's start (`ctx.frame/head/height`).
- **New acting channel:** `Actors.luau` (`ch` and `pose`) and `CHANNELS` in `scene.py`.
- **New action:** add it to `runtime/Scene/Actors.luau` and `ACTIONS` in `scene.py`.
- **New animation or sound:** add a `library.json` entry with id, rig, source, licence and `approved`. Don't add Floppy transform or ability animations.
- Keep everything data-driven; a scene should never need its own Luau.
