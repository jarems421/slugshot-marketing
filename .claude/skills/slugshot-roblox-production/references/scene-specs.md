# Scene spec format

One JSON file per scene: `roblox-native/scenes/<group>/<id>.json`, where `id` equals the file name. Validated by `.\ss roblox validate` (`roblox-native/tools/scene.py`) and again at run time (`runtime/Scene/Canon.luau`). Working example: `scenes/smoke/smoke_floppy_standin.json`.

```json
{
  "id": "floppy_false_aura_001",
  "note": "one line: what this scene is for",
  "format": "vertical",
  "truth": {"mode": "staged_fiction", "source": "staged_runtime", "gameplay_mechanics": "none",
            "match_outcome": "n/a", "label": "Fictional story"},
  "set": {"kind": "place", "origin": [x, y, z], "yaw": 0},
  "marks": {"A": [-4, 0, 0, 90], "slug": [2, 0, -2, 0]},
  "actors": {
    "hero": {"kind": "clone", "asset": "Workspace.SomeRig", "mark": "A", "face": "floppy"},
    "floppy": {"kind": "clone", "asset": "Workspace.SlugGrove.Floppy", "identity": "floppy", "mark": "slug"}
  },
  "shots": [
    {"preset": "two_shot", "targets": ["hero", "floppy"], "duration": 1.5},
    {"preset": "slug_low_angle", "target": "floppy", "duration": 1.2}
  ],
  "timeline": [
    {"time": 0.5, "actor": "hero", "action": "face", "target": "floppy"},
    {"time": 1.6, "actor": "floppy", "action": "hop", "height": 1.5, "duration": 0.45},
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
- **actors**:
  - `kind` is `standin_humanoid` or `standin_slug` (part-built, tests only), or `clone` (copies a Model already in the place: `asset` = dotted path). Clones are anchored and their scripts disabled; they're puppets.
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

  Any shot can add `shake` (amplitude).
- **timeline**: beats at `time` seconds from the first frame. Each beat runs in its own thread.
  - Actions: `move_to` (mark, duration), `face` (target, duration), `hop` (height, duration), `animate` (an `animation` from library.json; its `markers` map to cues, e.g. FIRE -> sound).
  - `cue`: `{type: vfx, effect, actor}` or `{type: sound, sound}` (a library.json name).
  - `marker`: a named point printed with a Unix-ms timestamp; use CUTAWAY_OUT / CUTAWAY_IN for hybrid bridges.
- **capture**: `sample` = camera sampling interval (s) for repeatability checks.

## Adding things

- **New camera move:** add a preset in `runtime/Scene/Cameras.luau` and its name to `PRESETS` in `tools/scene.py`.
- **New action:** add it to `runtime/Scene/Actors.luau` and `ACTIONS` in `scene.py`.
- **New animation or sound:** add a `library.json` entry with id, rig, source, licence and `approved`. Don't add Floppy transform or ability animations.
- Keep everything data-driven; a scene should never need its own Luau.
