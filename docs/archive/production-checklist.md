# Deferred production checklist

Production work that happens once content-making starts. None of it blocks the infrastructure, which is complete and tested (`ss smoke`, 13 checks). Tick items off here as they're done.

## Footage

- [ ] **First gameplay recording.** Set OBS's recording path to `media\obs` (README, "OBS settings"), record a real 2-player round from the current build, then `ss import`.
- [ ] **Real-world chain test.** Run that recording through `ss candidates` (after a Gemini pass), `ss caption`, `ss render --format PVP` or `ss assemble`, then `ss qc` and `ss sheet`. Watch the result on a phone.
- [ ] **Reference-render pack for Flow.** Clean stills of Floppy, Inferno (both forms) and the other slugs from the research PDF's table: front, three-quarter and profile, neutral lighting. Copying existing renders from `../slugshot` is fine.
- [ ] **First Flow clip** made from those stills, checked frame by frame, assembled with the AISCENE label.

## Voice and audio

- [ ] **Voice selection.** Open `out\bench\review.html`: the same skit with Kokoro, Qwen3-TTS design and Qwen3-TTS clone, plus line-by-line players. Choose per character (or your own recordings); Claude records it in `config\cast.json` (`status: approved`).
- [ ] **Licensed music bed(s).** Add files to `assets\music\` and one row each in `assets\LICENSES.csv` (source, licence, platforms, commercial use). Trending sounds stay in-app on each platform.
- [x] **Sound-effects set** (2026-11-25): `ss sfx`, an original procedural set in the game's sound direction, logged in `assets\LICENSES.csv`. Owner to listen; replace with the game's own sounds when its library is approved.

## Look

- [x] **Brand font** (2026-11-25): Kalam Bold, the game's one font (owner, 2026-11-22), OFL, in `assets\brand\`; the Remotion template uses it. Owner to confirm it reads well in captions.
- [ ] **Brand end card.** Logo or title art for the end card, once it exists in the game repo or is designed.

## Roblox-native filming (`roblox-native/README.md`)

- [ ] **Animation library.** Original animations (Animation Editor or R15 Animation Capture) for the first skits and reactions, each approved and logged in `roblox-native/library/library.json` with its source and licence. No Floppy transform or ability animations.
- [ ] **Sets.** Named marks for lobby, arena and grove locations, as `place` sets in scene specs.
- [x] **Real slug actors** (2026-11-25): all seven species from `CombatAssets`, acting through the game's SlugIdle/FloppyFace. Player avatars still to do (`RegisterKeyframeSequence`, no upload).
- [x] **First production-quality staged take** (2026-11-25): film mode replaces OBS for staged scenes (frame-exact, native vertical). OBS stays for real gameplay.
- [ ] **Real PvP recording** and, if useful, multi-client staged gameplay and a replay recorder for second angles.
- [ ] **First skit and first hybrid bridge** (Roblox -> Flow cutaway -> Roblox), labelled.
- [ ] **OBS WebSocket automation**, once manual recording is routine.
- [ ] **Motion Tools licence.** Ask the author; until then it stays out.

## Results

- [ ] **First posts and the content log.** Record each upload in `data\local\platform_metrics.csv` with its `experiment_id`, then `ss export`.
- [ ] **Own-channel analytics.** Once the Slugshot channel exists, export retention and watch time from YouTube Studio into the content log.
- [ ] **Turn hypotheses into results.** When a pattern repeats across several posts, add it to the editing skill as an S-rule (`.claude/skills/slugshot-video-editing/`).
