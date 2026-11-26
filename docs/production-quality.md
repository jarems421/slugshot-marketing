# Production quality pass (2026-11-25)

Response to the owner's Production Quality & Creative Direction handoff. Labels on every claim: **observed** (seen or measured here), **reported** (a source's own claim, not verified), **owner** (needs the owner's ears or eyes).

## 1. What changed, in one paragraph

Our videos can now be made from a cast script with real slug rigs, and nothing is re-timed by hand:

- `ss dialogue` turns a cast script into original character voices plus one timing manifest.
- Scene specs anchor their cuts and acting beats to that manifest's lines.
- The Roblox runner is one deterministic engine. It poses the game's own rigs through the game's own acting code (`SlugIdle`, `FloppyFace`), drives mouths and eyelines from the voice, and films frame by frame.
- `ss roblox film` turns the recording into exact 30 fps, native-resolution 1080x1920.
- `ss assemble` takes the same manifest for speaker-coloured captions and line-anchored sound.

The first benchmark short was made three times (three voices) with this chain. Every frame is present.

## 2. Decision register (external candidates and alternatives)

Reviewed read-only on 2026-11-25. Shallow clones are in `vendor/review-20261125/` (git-ignored). Nothing from these kits was executed or installed.

| Candidate | Version / licence (checked) | Decision | Why |
|---|---|---|---|
| **laSenu/roblox-in-this-town** | b135266, MIT | **Selectively adapt (ideas only)** | Its core architecture is the single most useful idea in the set: "the voice is the clock", one frame function that's a pure function of t, and stills strips. We adopted the principles in our own runner. Its R6/face-decal cast system doesn't fit slug rigs. The `rbxasset://textures` local-image trick is noted for player-avatar faces later. |
| Harishisonline/rblx-animates-skill | 77e9f64, MIT code; assets per ASSET_LICENSES (Poly Haven CC0, OFL fonts) | Useful reference only | Blender pipeline with an ElevenLabs dependency and an episode-length focus (reported). Our rigs and acting code live in Roblox, so a Blender re-host adds cost and risk to rig fidelity for no proven gain. |
| BetaVersionHQ/beta-version-blox-studio | 7142ea3, MIT | Useful reference only | Speech-synced Blender shots (reported). We get speech sync natively: mouth envelopes from the performed audio drive real mouth bones in Studio. |
| SyphoDev-yt/roblox-ai-skills | 5aad881; custom free licence (no resale; credit if shared) | Reference only (no install) | Confirms the no-upload playback route `KeyframeSequenceProvider:RegisterKeyframeSequence`. Its R6/R15 keyframe tooling doesn't transfer to slug bone rigs. Kept in mind for player avatars. |
| 1nird/animations-cutscenes-skill | 46740e2, **no licence** | Reference only | Same `RegisterKeyframeSequence` route; good cinematography notes (180° line, 30° rule). No licence, so no code. |
| adnvli/vfxskill | f17b9a6, MIT | Defer | Useful when we stage original VFX. Real game VFX must stay authentic, so not needed for dialogue skits. |
| NoCodeHack engine | repo 404 | Reject | Unavailable; we won't run downloaded installers. |
| Larpniverse kit | paid | Reject (not purchased) | Owner rule: no paid kits. |
| Roblox Studio Agent Plugin | 57d7204 (earlier review) | Already covered | Built-in Studio MCP plus our guard. |
| **Game's own `SlugIdle` / `FloppyFace`** (`../slugshot`, read only) | owner's code | **Integrate (call, don't copy)** | The best acting system available: owner-reviewed performances per slug (breathing, looks, blinks, mouth bones, smiles, Rammstone's angry face). They're already in the marketing place, so the runner calls them. This beats generating new animation. |
| **Qwen3-TTS 1.7B** (VoiceDesign + Base) | qwen-tts 0.1.1, Apache-2.0; torch 2.8.0+cu128; peak VRAM 3.94 GiB, model load about 75 s | **Integrate (isolated `.venv-voicelab`)** | Original voices from text descriptions (no cloning of real people), a delivery instruction per line, native Spanish. Observed: all 6 lines intelligible including "Per shot", where Kokoro failed. About 4 s of GPU per second of audio on the 3070. Free. Voice choice is **owner**. |
| Kokoro-82M (existing) | kokoro-onnx 0.6.1, Apache-2.0 weights | Keep as fast fallback | Observed: "Per shot" transcribed blind as "Harshad" (pitch-shifted voice); flatter delivery. Very fast. |
| Gemini TTS | about $20 per 1M audio tokens, 25 tokens/s (Cloud pricing pages, inconsistent snapshots) | Defer (ask first) | Roughly $0.02 per 30 s take, about $1-3/month at our cadence. Needs a billing-enabled Cloud project; a consumer subscription doesn't cover it. Only worth it if the owner prefers it over Qwen by ear. |
| ElevenLabs | API about $0.10 per 1k characters (reported); commercial rights need a subscription | Reject for now | A subscription is outside the agreed budget, and the local route already fixes the intelligibility problem. |
| faster-whisper | MIT | Defer | For scripted lines the script is the text. Whisper only checks and times short clips, and CPU `small.en` takes seconds. It earns its CUDA/cuDNN setup only for long real recordings. |
| WhisperX | BSD-2 | Defer | Its forced alignment duplicates what script-aligned Whisper timing gives us on clean per-line audio. Heavy dependencies. Revisit for owner voice recordings with overlaps. |
| Blender (existing MCP) | present, unused | Defer | Real-rig fidelity is already exact in Studio. Blender earns a test only for shots Studio can't render (stylised impact frames, painted backgrounds). |
| Flow / Gemini inserts | existing plan | Unchanged | Short labelled cutaways. Reference stills can now be pulled from the same deterministic scenes (`Scene.still`). |
| OBS | 32.2.2 | Kept for real gameplay only | Staged scenes no longer need it: film mode plus `video_capture` is frame-exact. Real PvP play still needs OBS. |
| MakeMyClip | 0.5.2 | Unchanged | Not needed for this chain. |
| Remotion | 4.0.546 | Extended in place | Dialogue captions, Kalam font, label position. |

## 3. Capability and gap assessment

| Capability | Implemented | Stand-in tested | Real-asset tested | Owner-approved quality |
|---|---|---|---|---|
| Real slug actors (all 7 species via `CombatAssets`) | yes | n/a | yes (Floppy, Rammstone filmed; Aquabeek posed) | **owner** |
| Acting: idle, smile, react, angry, lean, squint, blink, look, auto-eyeline to speaker | yes | n/a | yes (Floppy, Rammstone) | **owner** |
| Speech-driven mouth and nod | yes | n/a | yes, subtle; mouth size on each rig still to tune by eye | **owner** |
| Deterministic frame engine (preview, film, still) | yes | n/a | yes: 4 full takes, 0 repeated frames after patches | n/a |
| Native-resolution vertical (camera roll) | yes | n/a | yes: 2368x1104 viewport, 1962x1104 crop, rotated to 1104x1962, scaled to 1080x1920 | n/a |
| Dialogue-anchored timing (`L3.end+0.2`) | yes | n/a | yes: one scene re-timed to 3 voices | n/a |
| Size-aware cameras (close_up, push_in, over_shoulder) | yes | n/a | yes | **owner** |
| Character voices (Kokoro, Qwen design, Qwen clone) | yes | n/a | yes | **owner** (none selected) |
| Script-aligned captions plus deviation check | yes | n/a | yes (it caught a real fault and an ad-lib) | read the flags |
| Speaker-coloured Kalam captions, phone-safe label | yes | n/a | yes | **owner** |
| Original procedural SFX set | yes | n/a | yes (in the benchmark mix) | **owner** (listen on a phone) |
| Transitions beyond cut/fade (whip, impact frame, freeze, J/L) | no | | | deferred until a script needs one (in-camera whip_pan exists) |
| Player avatars acting (R6) | no | | | next: `RegisterKeyframeSequence` route |
| Spanish | engines support it | | | not yet tested |

## 4. Benchmark results (observed)

Script: `jobs/dialogue/floppy-seven.txt`. Scene: `roblox-native/scenes/bench/bench_floppy_seven*.json`. Edits: `jobs/bench/`. Outputs: `out/bench/` (open `out/bench/review.html`).

| Voice | Length | Script deviations flagged | Synthesis time | Frames complete | QC |
|---|---|---|---|---|---|
| Kokoro | 12.0 s | 2 ("seven" with base.en; "Per shot" heard as "Harshad" even blind) | about 15 s total | 358/358 | PASS |
| Qwen design | 16.5 s | 1 (ad-libbed "Heh, heh") | 48.5 s for 11.8 s of speech | 492/492 | PASS |
| Qwen clone | 14.7 s | 0 | 40.2 s for 10.1 s of speech | 439/439 | PASS |

Capture facts (observed):

- Studio's recorder stops at 30.0 s.
- It drops frames: 784 drops in one 30 s capture. The median gap was 33 ms, 1% of gaps were over 240 ms, and one stall lasted 1.7 s.
- Its temporary files vanish when the playtest restarts.

Film mode handles all three: each frame is held and stamped, recorded in chunks of 25 s or less, and missed ranges are patched. Before this pass, a 7 s stand-in test lost 125 frames at about 27 fps, and vertical output was a 621-px crop upscaled.

`screen_capture` without camera arguments didn't show the play viewport reliably (it showed a stale or edit view). Use short `video_capture` grabs as the truth.

Costs incurred: **$0** (all local). No paid APIs, no purchases, no uploads, nothing published.

## 5. Limitations and honest gaps

- I can't hear the voices or judge comedy. Voice choice, humour and "does it feel like our world" are the owner's calls.
- Mouth movement is subtle on slugs with painted mouths (by design of the rigs); it may need a bigger gain per species once watched.
- The establishing over-the-shoulder shot is serviceable, not striking. Better staging needs real set marks in the grove and arena.
- Qwen design mode varies identity a little between lines (by design: a fresh voice per line from a description). Clone mode is consistent but takes less direction. This is an **owner** listening call.
- Film mode slows ambient world motion only through particle `TimeScale`. Scripted world animation (the lava gloop) runs on its own clock, so it plays about 2x fast in film footage. It's hardly visible in close-ups but could show in wide shots.

## 6. Workflow for the first real videos

1. **Brief to cast script** (ChatGPT drafts, owner approves): `jobs/dialogue/<id>.txt`, using `NAME (direction): line` and `[beat 0.8]`.
2. `.\ss dialogue jobs\dialogue\<id>.txt --engine qwen --mode clone`. Read any flagged lines; re-do one with `--only N`.
3. **Scene spec** in `roblox-native/scenes/<group>/<id>.json`. Point `dialogue` at the manifest, anchor shots (`until`) and beats (`time`) to lines, and follow the direction rules in the production skill. Then `.\ss roblox validate`.
4. `.\ss roblox rebuild`, start play, check stills, then **film in chunks**. Copy each recording to `media/takes/` at once. Run `.\ss roblox film <take.json> <chunks...>`, and patch any ranges it lists.
5. **Edit file** `jobs/<id>.json` with `"dialogue"`, the take as the scene, the ambience bed and line-anchored SFX. Then `.\ss assemble ... --test`, `ss sheet`, and watch it.
6. **Owner review** (funny? voice? look?), then publishing through the dashboard as before.

Infrastructure freeze still applies. The next improvements should come from real videos: player-avatar acting, grove/arena set marks, per-species mouth gains and the first transition a script actually needs.

## 7. Revision 2 (2026-11-25, after the owner's first review)

Owner verdict on the benchmark:
- The **Qwen design voices sound the most human**, but the voices change between lines.
- The resolution is acceptable, but the **slug animation looks choppy**: Floppy's face glitched, Rammstone jittered while talking, and the background slugs hopped "really, really quick".
- Scripts are the owner's job; the toolkit should make good In My World videos and good animation with all our assets.

What we found and changed (observed):

| Problem | Cause (measured or seen) | Fix |
|---|---|---|
| Voices change between lines | Fingerprint similarity after removing what all voices share: design-mode lines of one character barely match (Floppy -0.04 to -0.09: effectively different voices), while clone mode holds (Floppy 0.21-0.50, Rammstone 0.45-0.56; every cross-character pair negative) | `ss cast` designs one **expressive** reference per character (3 candidates; the one most distinct from the other characters wins; the rest are kept to swap by ear), then every line is cloned from it, 2 takes per line with the closer voice match kept. Clone mode is now the default |
| Floppy's face glitching | Three writers on his face bones: SlugIdle, my overlays and the game's FloppyFace/FloppyIdle, which run on real time and raced ahead of the held film frames | Actors are never named "Floppy", so the game scripts skip them. His face is driven by a port of FloppyFace with the same constants, as a pure function of scene time |
| Rammstone jittering while talking | Mouth followed raw loudness frame by frame: worst mouth jerk 0.024 studs/frame² | Zero-phase smoothing of the mouth; a slower curve for nods; every bone reset each frame so nothing accumulates. Re-measured under held frames: mouth 0.010, head 0.0069 to 0.0041 |
| Background slugs hopping fast | The grove residents (`HubArt.GroveSlugs`, about 18 slugs) are animated by the game on real time; film mode holds each frame about 6 renders, so they ran about 3-4x fast | They leave the world during takes; scenes place their own background slugs, which follow scene time |
| Choppy hops | Squash snapped on at landing | Eased anticipation, parabolic arc, landing squash that eases in and settles with a damped wobble |
| Studio reopened in a 1088x624 window (would have meant upscaled footage) | Window state after `ss roblox rebuild` | Rebuild now maximises the window; `Scene.film` refuses viewports under 1000 px high |

Asset issues the owner raised (diagnosed; fixes belong in the game repo, so they await the owner's go-ahead):
- **Floppy's right eye, white sliver at the upper outer corner.** Not present at rest. It appears whenever the lids are posed, including the game's own default (lid 0.03, 16° droop), and is worse with droop: the lid doesn't fully cover the eyeball at that corner. Fix: the lid mesh or its weights at that corner (Blender), or a per-eye lid correction in FloppyFace and our port. The game shows it too.
- **Rammstone's armour from below:** his meshes are single-sided (`DoubleSided=false`), so looking up into the armour shell shows through it. Fix: double-sided or closed armour mesh on re-export. Exact spot to confirm with the owner.

Later in revision 2:
- **Blocky shadows on faces** (owner): Roblox's shadow map is too coarse for creature close-ups, and the actors' own horns and spikes shadowed their faces. Takes now set `Lighting.ShadowSoftness` to 1 (was 0.2; restored afterwards), actors don't cast shadows, and each slug carries a soft, shadowless fill light in front of its face (`fill` per actor; 0 turns it off). Rammstone's stepped neck and armour shadows were gone in the re-check.
- **Fixed voices:** `ss cast` built 9 characters, about 18 minutes on the 3070. On the In My World sample every line matched the script, with a voice match to its character's reference of 0.97-0.99.
- **In My World sample:** `exports/SS_20261125_WORLD_InMyWorldPick_Sample_V01_MASTER.mp4` (dashboard Content). 669/669 frames, QC pass. Known flaw: a background slug (Phosphoro) sits between the camera and the group in the opening shot; restage it before reuse.
- **Floppy's eye:** a red tint test proved the white sliver is the `EyeL` mesh's texture (the cream area outside the off-centre outer ring) showing past the lowered lid. Moving the eyeball back hid it but opened a bright gap under the lid, so the fix belongs in the texture: paint the region outside the outer ring dark. Blocker: the live texture (`118843830887527`, referenced by `private-assets/floppy/FloppyAsset.luau` and `materials.rbxmx`) doesn't match any built file found (`slugshot-slug-pipeline`, `slugshot-integration` and `slugshot-pvp-ui` hash differently), so its generator must be found before re-uploading, or the approved eye could change subtly.

## 8. Revision 3 (2026-11-25, owner's review of the In My World sample)

| Owner note | Cause (observed) | Fix |
|---|---|---|
| "All the slugs are floating" | Slug imports carry an invisible `RootPart` block about 1.4 studs below the body; grounding used it. Turning off actor shadows (revision 2) also removed contact shadows, as the game's grove also does | Actors stand on their `root` bone, the authored floor and the body's lowest point for every species (measured). Sole-to-ground after the fix: 0.000 for all 7. Visible heights are 1.3-1.8 studs (was 2.81), so framing follows the real body |
| Floppy's lids "connected to the sides of his eyes" | "Asleep" pushed the lids 0.08 down, past the game's designed range, stretching the lid skin into the corners | Sleepiness now closes the lids along the game's own closing path (a part-closed blink, up to 0.88) |
| Floppy's drool bending left | Talking dropped his jaw 0.05 (game range is about 0.008-0.04), pulling the drool, which hangs from that lip | Talk jaw 0.016. The bend is still slightly visible mid-line: watch it |
| Inferno's smile, middle line too low | Our clone left his tooth divider (`*MouthLine`) opaque; the game keeps it at 0.15. His excited `react` stretched the grin | Divider at 0.15 transparency; Inferno's react halved in the scene |
| Aquabeek's cheeks puff on head turns | Head-bone yaw (up to about 24°) twists cheek weights | Eyelines turn the whole body for 75%; the head bone adds at most 7° |
| Voices "lifeless" compared with TikTok AI storytime voices | Clone copies the reference's delivery, and the references were designed calm and unhurried | All 9 references redesigned for high-energy storytime delivery (punchy emphasis, emotional swings, exclamations), personalities kept. Cloud option (Gemini TTS: per-line style direction and fixed named voices) proposed to the owner, as free-tier availability for TTS isn't confirmed |
- **Gemini TTS adopted** (owner enabled billing; cap £7/month, enforced by `config/voice-budget.json` and a spend ledger). Free tier measured at 10 requests/day for `gemini-3.8-flash-tts`, too few for production. The In My World sample re-voiced in 84 s for about $0.006, then refilmed with every animation fix: `exports/SS_20261125_WORLD_InMyWorldPick_SampleGemini_V01_MASTER.mp4`, 904/904 frames, QC pass.
- **Studio guard fix:** Studio's reported mode can lag a play start, so the marker read hit the Edit datamodel during play and denied calls (fail-closed, but it interrupted filming several times). It now reads the same marker in the other datamodel when one is unavailable; the token must still match.
- **Throttled renders:** Studio dropped to 10-16 fps while unfocused, so film mode used hold 2 (still every frame captured). Pick hold so a chunk of about 150 frames stays under the recorder's 30 s cap.

## 9. Revision 4 (2026-11-25, owner's screenshots of V02)

| Owner's point | Cause found | Fix |
| --- | --- | --- |
| Shadows jitter and jump between frames when the video plays (smooth when scrubbing) | The floating islands that cast the moving sun shadows (`hub-well-isles`), lamp pulses and lava run on the game's own clock (HubMotion); a take is posed on scene time and decoded from several passes, so each frame showed the islands somewhere else | Marketing patch: HubMotion follows `workspace.FilmClock`, which the runner sets from scene time (`world.clock` picks the cycle). Same scene time = identical islands (checked), so every pass agrees. Lamp shadows are back on (the earlier "flashing" was this clock, not the shadow budget); `look.local_shadows: false` still turns them off |
| Inferno's smile line sits too low | The game's InfernoTeeth reshapes the divider from the lip bones; on a staged actor it landed behind his teeth, only its edge peeking out along the bottom | Inferno actors stand in a `SlugShots` folder, which InfernoTeeth skips: the authored divider runs across the middle of the grin (checked) |
| Aquabeek's face looks weird, soft cheek | Floppy's own glow (range 5) lit her face with a soft green spot; she had no front fill (no PrimaryPart) | Staged slugs' glow capped at 2.2 studs; the fill hangs off the RootPart when there is no PrimaryPart; hers comes from higher up, so its reflection on her glossy skin sits on top of her head |
| Aquabeek's mouth too short | Corners sat at the rest width | Corners 0.022 out (about a fifth longer); also in the game's SlugIdle |
| White specks (Aquabeek), green specks (Floppy's belly), Floppy's eye corner, Aquabeek's belly line | Hidden faces of inner layers poke through (found by casting rays at the live meshes). Floppy's left spiral ran off its image, and a belly line stopped part-way. | The game's `tools/slugs/repair_textures.py` builds the repaired maps. The marketing place uses the approved private uploads through the ignored `roblox-native/studio/asset-overrides.json`. |
| Rammstone's armour gap from below | Single-sheet plates, undersides culled | `DoubleSided` on his plates (runner and game) |
| Shadows still jumping (checked after the owner's go-ahead) | Studio's Automatic graphics quality lit the two recording passes differently (one without lamps, glows or sparkles) and the decoder alternated between them | Scene.film locks quality Level21 for the take; the most complete pass is decoded first. V03 measured: 911/911 frames, frame-to-frame jumps only at the 7 cuts, Inferno's hop and the crystals' twinkle (was about 100 jumps) |

## 10. Final sample review (2026-11-25)

- **Floppy.** The belly-edge repair samples the visible surface texel by texel, so the same hidden face can match cream belly and green skin. The repaired spiral stays within the texture. Both maps were regenerated and checked against the private upload receipts and the staged actor.
- **Aquabeek.** The belly outline and scales follow one pattern in body coordinates. The peak sits lower below the lips. Pale remnants of the original crown were cleared from the blue base colour and emissive map before feathering the new outline. The repaired crown exterior had zero pale or emitting texels out of 60,863 examined. The rounded peak and continuous scales were visible from both shot angles in Studio. The lip colour was reprojected across atlas seams and the normal and roughness maps soften the lip reflections.
- **Front contact outline.** The floor cut through Floppy's visible sole by about 0.012 studs at the front close-up. The scene runner now grounds from the lower of the authored root and visible meshes. A 0.003-stud clearance kept the edge intact in the Studio comparison.
- **Portal continuity.** Film mode suspends the wall-clock swirl particles while retaining the portal surface glow. Studio showed 12 enabled swirl emitters before filming, zero during, and 12 after restoration. The 24 replacement frames received a broad lighting grade matched to their neighbours within each shot. The grade preserves the captured pose and texture detail.
- **Voices.** The narrator uses the first Gemini version's direction. Rammstone and Floppy have stronger line directions. This sample used three candidates per line. Future runs default to one take and can request a performance audition with `--takes 3`. The timed transcript flagged only Floppy's opening groan. The owner judges the voices and performance.
- **V04 picture check.** The decoder recovered all 914 frames at 30 fps with zero repeats. A 914-frame brightness comparison found the ten strongest in-shot differences in Inferno's intentional hop. The reviewed close-ups show a continuous front outline on Floppy and a clean blue edge around Aquabeek's belly peak.
- **Dashboard master.** `SS_20261125_WORLD_InMyWorldPick_SampleGemini_V04_MASTER.mp4` passed every technical check at 1080 × 1920, 30 fps, 30.5 seconds, −14.0 LUFS and −2.8 dBTP. The captioned contact sheet confirmed the story label and speaker captions. The local dashboard opened V04 first and served its video stream.

## 11. V05 (2026-11-26)

- **Floppy's right eye.** The model's right socket sat up to 0.021 units off the mirrored left one at its outer-lower corner, so the rim curved into the eye. The game's `tools/slugs/repair_floppy_socket.py` mirrors it (gap now under 0.010). The owner approved the model upload; the marketing place swaps Floppy's model ID through the private overrides, which now match bare IDs in script source too (his model loads at runtime from `model = ID`). Checked in Studio: the right eye's lower edge matches the left.
- **Rammstone's voice.** Charon with a deep, gruff American direction (Algenib was rejected: "sounds weird, a bit British").
- **Picture.** 919/919 frames, no repeats. One patched frame came out slightly darker and was replaced by the average of its neighbours; frame-to-frame jumps only at the planned cuts and Inferno's hop. Master passes QC.
- **V06 (2026-11-26).** Floppy's right upper lid had hard dark stripes painted on (texture, not lighting: unchanged with the normal map off); his right socket and lid are now repainted from the mirrored left one in body coordinates (game `repair_textures.py`, `mirror_right_socket`). Floppy's thick inverted-hull ink shell is hidden on staged actors so he has the same thin Highlight outline as every other slug (owner: it "cuts and breaks"). 919/919 frames; one missed frame blended from its neighbours, one held before a cut; QC pass.

## 12. Human actors (2026-11-26)

- **What.** A `human` actor kind for staged scenes, next to the slugs: blocky R6 people like the game's players, walking, running and sprinting with eased starts and stops, gestures and emotes layered over locomotion, eyelines and turns, a drawn ink face (blinks, glances, brows, smile, talking mouth), the game's blaster (equip, two-handed aim, recoil, muzzle flash, holster), and holding a slug. Details: `.claude/skills/slugshot-roblox-production/references/humans.md`.
- **Demo.** `SS_20261126_WORLD_HumansDemo_HumanActors_V01_MASTER.mp4` (internal; placeholder script): Kai and Mira walk and talk, Mira stops in disbelief, Kai snaps, Floppy hops into his hands, Raf runs in, Juno sprints in and fires, Kai facepalms when Floppy wants five more minutes. 871/871 frames, 0 repeated, QC pass. Four new Gemini voices (draft) at a few cents.
- **Needs the owner's eyes and ears.** Whether R6 humans with drawn faces suit the brand; character looks and voices; the walk; comedy timing. Known limits: no fingers (snap is sound plus arm flick), no slug projectile or hit reaction yet in staged shots, emote motions are Roblox's generic ones.

