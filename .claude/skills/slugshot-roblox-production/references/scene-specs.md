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
- **ambient** (2026-11-27): background life, expanded by `tools/ambient.py` into ordinary `amb_*` marks, actors and beats before validation (seeded, so every pass and patch matches; the runtime sees nothing new). Full format in the module docstring.
  - Pick the crowd for the scene (owner, 2026-11-27): talking scenes get a busy hangout all around; a duel gets nobody, a `ring` of watchers, or a crowd that scatters when it starts.
  - `seed`, `clear` (hero marks), `clear_radius` (default 5), `avoid` ([[x, z], ...], 2.5 studs).
  - `groups`: `{zone: [x1, z1, x2, z2], people, slugs, activities: [stroll|chat|watch], focus, until}`, or `{activities: ["ring"], focus, people, slugs, radius, open: [from, to]}` (the open arc is where the camera looks in; 0 degrees = +z from the focus, may wrap). An orbit_reveal at angle o sits at ring angle about 163 + o: check a still.
  - `reactions`: `{at (seconds or line anchor), kind: cheer|gasp|flinch|point|laugh|turn|scatter, focus, who: all|people|slugs, hold, spread}`. Nearest react first; each interrupts that extra's own routine for `hold` seconds (scatter: for good; people run, slugs hop away) and turns them to the focus.
  - `residents: {near, radius, max}`: the game's grove slugs (`library/grove.json`, world studs) recreated as our actors at their real spots.
  - Extras wear the `extras_wardrobe` in library.json (free Roblox-made shirts, trousers and hair; never a cast outfit). Slugs hop at one even stride (1.6 studs per hop).
  - Every spot and walk is checked against the floor maps (`library/floors/*.json`, `tools/floormap.py`): no cracks, pits or ledges. `scene.py validate` also warns when a hero mark is on one.
  - Extras don't block the camera's collision check: keep zones on the far side of the heroes, and check stills. `close_up` `size` is in actor heights (3 = about 20 studs away).
  - Vignettes (2026-11-27): tiny background stories with a start and an end, in `groups.activities` alongside stroll/chat/watch: `show_off` (someone holds a slug up, friends come over, point and laugh), `runaway` (a slug hops off, its owner runs after it and picks it up), `training` (pointing a slug through a trick; a cheer when it works, a facepalm when not), `trade` (a hand-off between two people, then an `agree`), `browse` (wander between spots, think, point). Reactions still interrupt them.
- **acting** (2026-11-27): an automatic acting pass (`tools/acting.py`) after anchors are resolved. Named humans get their `library.json humans.<id>.mannerisms` (Kai proud and leaning in, Raf bouncy, Mira deadpan with arms crossed, Juno still): a baseline expression and slow posture sway, nods on the speaker's longest words while listening, an in-character reaction at line end, a talk gesture on their own longer lines, idle mannerisms in gaps of 2.5 s or more, and interruption acting where lines overlap (`[overlap]`: the cut-off speaker's mouth stays open and they look at the interrupter, who leans in and points). It never touches a span the author already acted. Seeded per scene. Opt out with `"acting": false` on the scene or an actor.
- Physical interactions: a hand-off is two overlapping `hold`s (the giver's eases out as the receiver's eases in); a pick-up is a walk to the slug, a `face`, then the `hold`. Sitting is the `sit` gesture on a location's `seat_*` mark. `scene.py validate` warns when a hold starts with the item more than 3.5 studs from the holder (it would float in).
- Floors (runtime, 2026-11-27): actors stand on the highest solid floor under a 0.85-stud footprint, at marks and on every step between them, so feet bridge narrow cracks and ride over bumps instead of sinking.
- Cameras can target a mark as well as an actor (`orbit_reveal` around a place).

## Adding things

- **New camera move:** add a preset in `runtime/Scene/Cameras.luau` and its name to `PRESETS` in `tools/scene.py`. Presets read actors as they stand at the shot's start (`ctx.frame/head/height`).
- **New acting channel:** `Actors.luau` (`ch` and `pose`) and `CHANNELS` in `scene.py`.
- **New action:** add it to `runtime/Scene/Actors.luau` and `ACTIONS` in `scene.py`.
- **New animation or sound:** add a `library.json` entry with id, rig, source, licence and `approved`. Don't add Floppy transform or ability animations.
- Keep everything data-driven; a scene should never need its own Luau.
