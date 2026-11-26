# Human actors

Added 2026-11-26 (owner: "humans ... coexist with slug actors", directed from a description, no manual animation).
Code: `roblox-native/runtime/Scene/Humans.luau` (client), `roblox-native/runtime/CastServer.server.luau` (server half,
built into the marketing place only). Demo: `roblox-native/scenes/humans/humans_demo.json`, job `jobs/humans/humans-demo.json`.

## Why it is built this way
- **R6 blocky rigs**: the game spawns players as R6 (`../slugshot/docs/decisions/0008-r6-rig.md`, owner's "final verdict"),
  so marketing humans look like real players. Motion is written in the game's R15 pose terms and folded onto R6 with the
  game's own `chord` / `toR6` (ported), so the game's clips, Roblox emotes and authored poses all share one path.
- **Deterministic**: every part is anchored and placed by our own forward kinematics from scene time. No AnimationTracks,
  no physics, so held film frames, patches and stills agree, as for slugs.
- **Faces drawn from parts** (eyes, brows, a two-piece mouth) on the head's curve: blink, glance before the head turns,
  raised/knitted brows (`react`/`angry`), smile/frown (`smile`), mouth from the dialogue envelope. Our ink, no uploads.
  (EditableImage decals did not render in this place.)
- **Looks** come from free Roblox-owned catalog items applied by ID in Studio (`library.json` `humans`): nothing bought,
  uploaded or published. The server builds the rig (`CreateHumanoidModelFromDescription` is server-only).

## Moves (`library.json` `human_moves`)
- Game clips: `stand`, `run`, `sprint`, plus private retargets present in the marketing place (`flinch`, `land`, `jump`,
  `aim_settle`). Private Mixamo clip data stays in the game's private module; never copy it into this repo.
- Roblox-owned default animations (`wave`, `point_emote`, `cheer`, `laugh`, `dance`) and free Roblox emotes
  (`salute`, `shrug`, `hello`, `tilt`, `applaud`, `cower`, `confused`, `agree`, `disagree`, `happy`, `sad`), loaded by ID
  at runtime and sampled at scene time; their data is not stored here.
- Authored (`keys`, degrees in the game's axes): `walk` (classic block walk; the R15 walk folds badly onto block legs),
  `explain` (talking hands, loop), `disbelief`, `snap`, `facepalm`, `think`, `arms_crossed`, `hands_up`, `nod`,
  `head_shake`, `reload`. Add new ones the same way; check them in a still before filming.
- `mask`: full, upper, arms, right_arm, left_arm, head. Gestures layer over walking when masked to the upper body.

## Directing notes (learnt on the demo)
- Space people about 4-5 studs apart; at 2.5 their shoulders cross when they turn to each other.
- A two-person walk needs a front-diagonal follow (`follow` with `offset` and `look`) to fit 9:16.
- Keep entrances out of earlier shots' backgrounds (start marks behind the camera).
- Holding: hands sit low and in front; scale the slug to taste (`scale` on the slug actor) so it never hides the face.
- R6 has no fingers: a "snap" is an arm flick timed to `assets/sfx/finger_snap.wav`.
- Rehearse without rebuilding: `scene.py json ID`, or patch the built spec in the playtest through
  `_G.SlugshotSceneSpecs[id]` (Scene.load prefers it), then `Scene.still`.

## Owner checks still needed
- Whether R6 humans with drawn faces fit the brand (an R15 / dynamic-head route would need its own decision).
- Character looks, names and voices (KAI, MIRA, RAF, JUNO in `config/cast.json` are drafts; not game canon).
- Walk feel, gesture timing and comedy beats are first passes.
