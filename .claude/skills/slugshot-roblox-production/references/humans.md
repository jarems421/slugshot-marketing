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
- **Painted faces** (owner, 2026-11-26: "actual facial features" like top Roblox videos): our own kit drawn by
  `roblox-native/tools/faces.py` (7 eyes, 5 brows, 11 mouths; `face_style` boy|girl), uploaded with owner approval as
  private decals (IDs only in ignored `studio/face-assets.json`, inlined into the runtime by the place builder). Three
  layers switch per frame from the `express` channels (`smile`, `react`, `angry`, `squint`, new `smirk`), blinks,
  glances and the dialogue mouth. Without the kit the old part-drawn face is the fallback.
- **Looks**: Roblox catalog clothing and hair applied by ID in Studio (owner choice: catalog fits; nothing bought).
  They are other creators' designs, so check each on the rig for brand logos (a North Face puffer and a Guess top were
  dropped). Pick hair that keeps the face clear: long bangs hid the painted eyes. Some layered hair doesn't attach to
  R6; check in a still. The server builds the rig (`CreateHumanoidModelFromDescription` is server-only).

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
- Holding (owner, 2026-11-26): a slug sits on one hand (`hand` right|left, palm out to the side) or a shoulder
  (`shoulder`, `shoulder_left`); two-handed holds were dropped (the slug floated between the hands).
- Slug shots (owner: "the slug actually shooting and transforming ... a special moment"): `shoot` with `slug` and
  `target` launches that species from the muzzle and plays the game's own SlugTransformation (twirl, glow, swap to
  <Slug>Transformed, hit, turn back), replayed from scene time (Shots.luau). Floppy never transforms: he tumbles.
  Pair it with the `slug_shot` camera (rides beside the slug; keep it on the open side, away from walls) and end that
  shot right after the hit. One shot per beat; no generic muzzle flash.
- The game's blaster model points its barrel along the handle's +Z, so the hold turns it about the grip.
- R6 has no fingers: a "snap" is an arm flick timed to `assets/sfx/finger_snap.wav`.
- Rehearse without rebuilding: `scene.py json ID`, or patch the built spec in the playtest through
  `_G.SlugshotSceneSpecs[id]` (Scene.load prefers it), then `Scene.still`.

## Filming notes
- Wait for the lobby: the game's HubArt builds the cavern for about two minutes after play starts. Scene.film now waits
  for `workspace.HubSolidParts`, preloads and looks through every shot first (`warmup_s` in the manifest); takes started
  earlier filmed walls appearing (owner: background "flashes from dark to light").
- `take.py film` matches frames filled from patch recordings to the first recording's lighting (smooth per-pixel gain
  from nearby shared frames), so patches no longer flash.

## Owner checks still needed
- Whether R6 humans with drawn faces fit the brand (an R15 / dynamic-head route would need its own decision).
- Character looks, names and voices (KAI, MIRA, RAF, JUNO in `config/cast.json` are drafts; not game canon).
- Walk feel, gesture timing and comedy beats are first passes.

## Slug-shot cutscenes (owner, 2026-11-26: the V04 shot was "too zoomed in ... not slowed down ... no emphasis")
- `slowmo` in a spec: `[{from, until, rate, ramp}]` (scene seconds or line anchors). Scene.film films video time and maps it
  back to scene time; the world's particles and the game's transformation slow with it. Segments must sit in a dialogue
  gap (scene.py refuses spoken words inside one). After decoding, `take.py warp <take.json> <dialogue.json>` writes a
  dialogue with that much silence inserted; point the edit's `dialogue` at it. SFX `at` numbers are video seconds.
- `split` shot: `views: [top, bottom]` (any shot entries). The take films view 1; a second `Scene.film` pass with
  `layer = "b"` and `first/last` round the split (manifest `splits`) films view 2 under its own take name; then
  `take.py split <take.json> <take.mp4> <layer_b.mp4>` composites them behind a slanted divider that rises in and
  carries on off the top. Built for the owner's duel idea (two shooters, two slugs, faces side by side, screens rejoin).
- `slug_cam` preset (`target` = shooter): `mode "orbit"` sweeps `sweep {from,to}` degrees round the flying slug (90 =
  head-on; head-on fits a 9:16 frame, a profile of a transformed form doesn't), best with `clock: "output"` so it keeps
  moving through slow motion; `mode "pan"` is locked off beside the path and turns to follow (`lead` negative aims
  short of the target, where the hit throws the form back).
- `fx`: `flash` (a lit ColorCorrection, warm tint) and `shake`, at the impact (impact = launch + flight; check it in a
  still). Find a clear firing lane first: in the lobby the plaza north of the group is open floor.
- Floppy's right lid is driven as the mirror of his left (Actors.floppyFaceSetup twins); the old per-side depths left it
  higher with a dip at its inner corner.
- Slug hops: a damped spring (crouch, push-off stretch, airborne stretch, an impact splat on landing, head on a looser
  spring behind). `move_to` with `gait: "hop"` (`hops`, `hop_time`, `gap`, `height`) moves only while airborne.
- Hair check: fluffy cuts with long fringes hide the painted eyes; test in a still at close-up size before filming.

## Owner review of V06 (2026-11-26) and what changed
- **Blur was Roblox's frame-rate manager.** Takes render at ~15 fps, so its automatic mode lowered texture resolution
  mid-take: clothing went blocky for a few frames ("randomly everything goes blurry"). Scene.film now turns it off (and
  fixes mesh detail) for the take, and renders a few unstamped frames after every cut so the new view's textures load.
  Same frames re-filmed: V06 blocky, V07 sharp. take.py also keeps the sharpest held copy of each frame and lists
  frames whose detail dips (advisory; fast motion can trip it).
- **Split screen is for duels only** (two shooters firing at each other). A single slug shot is one unbroken camera:
  `slug_cam` `mode: "ride"` close while the slug twirls, easing out as the glow hides the swap so the transformed form
  fits the 9:16 frame (distance sized from the form), then in again for the landing.
- **The game's own impact and burrow are reused, not re-created.** The marketing build patches ImpactFx, FloppyRecovery
  and SlugTransformation to take their clock, Debris, tweens and randomness from `SlugshotMarketing.FilmTime` (straight
  through to the real services outside a take), so Shots.luau calls the game's contact sweep, the form's "hit" ending and
  the fall/wriggle/hop/burrow recovery on scene time. The ride camera follows the slug's body after the hit and stays
  above the floor while it burrows. Test: `scenes/humans/shot_test.json`.
- **In My World structure** is narrator-led (~210 wpm, narration from frame one, one quick 1-2 s illustrative shot per
  sentence), not character dialogue scenes. The humans demo's script was a placeholder; judge production on a real script.

## Lessons from pilot 01 (most_feared_slug, 2026-11-26; 43 shots, 95 s)
- `slug_cam` follows the shooter's FIRST shot unless `shot: N` (1-based, in timeline order) says which one.
- A slug held in the shooter's hand when a ride starts puts the camera inside it: end `hold`s before a shot and re-hold after.
- Off-camera teleports go 1-2 frames BEFORE the cut, never on or after it: a shot is framed from where actors stand at its first frame (V02: a teleport 0.01 s late framed the arena shot on the hub).
- A held slug eases back to its own ground mark when the hold ends; hand-offs between holders must sit exactly on a cut.
  A shot is framed at its start, so start a hold a few frames before the cut, never on it.
- `face` targets must not form a cycle (A faces B and B faces A, or A faces B faces C faces A): stack overflow (hit twice). Always face marks (where the other person stands), never actors.
- `static_wide` with several targets came out blocked or black; `two_shot` and `over_shoulder` (back 2.6, offset 1.6) were reliable.
- Rides: keep the flight lane clear of set dressing and bystanders (the plaza west of the duel lane is open; the east has posts).
  Cut a ride just after the hit; lingering lets it settle into a body or the floor.
- Off-camera repositioning: `move_to` with `duration: 0.02` exactly on a cut.
- One contact run checks every shot: prepare once, step `st.frame(t)` through each shot's midpoint while `video_capture` records,
  then pick held frames by stability. Studio's PreloadAsync can hang while its TexturePack uploads 429; Scene.film now caps it at 45 s.
- Throughput: first narrator-led 95 s video took about 2 h, mostly 6 rebuilds (about 5 min each, cavern build) and two film passes
  (hold 2 then hold 4, about 25 min) for 0 repeated frames.

## Lessons from pilot 01 V02 (2026-11-26)
- **Camera collision is on for every framed shot** (init.luau `unblock`): the camera slides toward its subject until no solid, visible part is in between, so wide shots stay wide where there's room and never go black inside rock. Rides and splits are exempt. `opts.no_unblock` turns it off for a test.
- **Instant moves must finish a frame before the cut** they hide behind; scene.py now rejects late ones. This one mistake caused most of V02's black and empty shots (each was framed on the actor's old spot).
- `two_shot` places its camera at a fixed side of the two actors with no regard for scenery, and takes only actors. Prefer `over_shoulder` or a wide `close_up` with a chosen `side`.
- Matching stills to shots by counting held frames fails when a shot is black. Record checks with `ss roblox rec`, or check fewer shots per run in a known order.
