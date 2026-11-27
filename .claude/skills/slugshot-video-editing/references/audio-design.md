# Narration, music, SFX and silence

## Balance (what the toolkit does by default)

- Masters land at about -14 LUFS integrated, true peak ≤ -1 dBTP (`ss qc` checks). **(C: common platform loudness practice)**
- Voice is the priority, but the bed must be heard. `ss audio mix` levels every bed to -16 LUFS, then applies `music_db` (default -6) and a gentle 3:1 duck: the bed sits about 9 dB under the voice, like genre videos (about 8 dB). The old 10:1 duck held it 13 dB under, and the owner heard only the narrator (2026-11-26). Measure, don't guess: bed under voice during speech should be 7-10 dB. If the words get hard to follow at low phone volume, the music is too loud. **(S: measured; research PDF audio gate)**
- Gameplay sound under narration: `clip_volume` about 0.2-0.35; louder only on the payoff hit, where the game's own sound sells it. **(D)**

## Narration

- Human voice is preferred when it's better; a consistent voice can become channel identity. AI voice (Kokoro) is for speed and tests, and is labelled where the platform requires. **(research PDF; A: disclosure rules)**
- `ss audio tidy` cuts long pauses to a 150 ms breath and can speed up slightly. Don't push past about 1.1x: comprehension falls when speech gets too fast, and pauses at clause boundaries help. **(B)**
- Read it aloud: if a line sounds written, rewrite it. **(research PDF rubric: natural speech)**

## Sound effects: only when motivated

Use an SFX when it:
- marks an on-screen event the game doesn't sound loud enough for (impact, transformation, a card landing);
- sharpens a punchline that's already funny (a tiny "boop" on Floppy's hop);
- signals a change of reality (a whoosh into a dream or an AI scene).

Don't use an SFX:
- on every cut;
- to make a weak joke "work";
- stacked on top of narration words (place them between words);
- if the file isn't in `assets/LICENSES.csv`.

**(D for all; the research PDF says devices must refresh information, emotion or clarity.)**

## Silence and comedy timing

- Setup -> short pause -> punchline. A beat of silence of about 0.3-0.8 s before the reveal lets the viewer predict, which makes the surprise land. Don't fill it with music swells or whooshes. **(D: classic comedy craft, untested here)**
- After the punchline, cut quickly. Explaining the joke kills it ("do not explain a joke after it lands": research PDF voice rules).
- Drop the music out for the payoff moment and bring it back for the CTA: contrast makes the moment feel bigger. **(D)**
- Suspense: hold on the bad position with only game audio before the comeback. **(D)**

## Music and trends

- Trending sounds go on in each platform's app (TikTok Commercial Music Library for business use; YouTube's Shorts library; Instagram's licensed options), never baked into the master. **(A)**
- A master may carry a licensed music bed when the edit needs it to work everywhere; otherwise export it with voice and game audio only, so platform audio can be added on top. **(A/D)**

## Character dialogue and voices (2026-11-25)

- Dialogue comes from `ss dialogue` (cast script → one performance per line → `dialogue.json`). In `ss assemble`, `"dialogue"` makes that the voice track and the timing source. It is **never** run through `audio tidy`: pauses are acting, and tidy would cut them to 150 ms. **(S: benchmark)**
- **Default engine: Gemini TTS** (owner enabled billing 2026-11-25; hard cap £7/month in `config/voice-budget.json`):
  - a fixed Google preset voice per character (`cast.json` gemini.voice, picked by ear via `ss audition`);
  - per-line delivery from the script's (direction) plus the character's base style;
  - inline `<laugh>`, `<sigh>`, `<gasp>`, `<short pause>` tags;
  - Spanish natively.
  - About $0.006 for a 30 s video. Read the deviation flags: it sometimes ad-libs (Floppy's "Mmm") or rambles (the Enceladus voice spoke a line twice and is rejected).
- Local Qwen (below) stays as the free offline fallback.
- **One fixed voice per character** (owner, 2026-11-25: "we need a set voice for each character"):
  - `ss cast` designs each character's reference once from `config/cast.json`: an expressive storytime-style sample, 3 candidates, the most distinct one kept, the others in `assets/voices/candidates/` to swap by ear.
  - `ss dialogue` (Qwen3-TTS clone mode, the default) speaks every line in that voice; 2 takes per line, the closer voice match kept. **(S)**
- Measured on the benchmark: design mode sounded the most human to the owner, but its lines of one character barely matched each other (fingerprint similarity about 0). Clone mode matched (0.2-0.56). The expressive reference carries design's naturalness into clone. Use `--mode design` only for experiments.
- Kokoro is for drafts and layout timing only: it garbled "Per shot".
- Voices are designed from text descriptions in `config/cast.json`. No cloning or imitation of real people, streamers or actors. Label AI voices where a platform requires it. **(A)**
- Read the deviation flags `ss dialogue` prints. A flagged line is either a performance fault (re-do it with `--only N`) or an ad-lib the owner may like (keep it and change the script line, so captions stay truthful).
- Paid voices (Gemini TTS about $0.02 a take; ElevenLabs needs a subscription) only after the owner chooses them by ear **and** approves a spending cap.

## Sound design kit (2026-11-25)

- `ss sfx` makes the original procedural set in the game's "tactile cavern fantasy" direction (`../slugshot/docs/audio/sound-plan.md`): `cavern_bed`, `slug_land`, `floppy_burble`, `whoosh`, `crystal_tick`, `finger_snap`, `blaster_shot`, `footstep`. Comedy and story accents added 2026-11-26: `boing`, `slide_up`, `slide_down`, `cartoon_pop`, `sub_boom`, `riser`, `tension_sting`, `record_scratch`, `sparkle_reveal`. It is logged in `assets/LICENSES.csv` and cleared for every platform. **(owner direction for the game; D for video)**
- **House bed (owner pick, 26 Nov 2026): `assets/music/M2a-cavern-sneak-chill-nature-subtle.wav`.** Scene beds S01–S11 (upbeat-fun, tense, mystery, sad, wholesome, showdown, victory, silly, dread, awkward, chase; same palette, 92 BPM, keys fitted to the house bed) are cut in where the story calls for them, never on a fixed cycle; calm ones also have `-nature-subtle.wav`. Narrator voice: Gemini Algieba, deep and dry (owner pick, `config/cast.json`).
- Earlier beds (26 Nov 2026, owner-approved Lyria generation, `scripts/music_gen.py`; brief in `docs/creative/music-brief.md`), in `assets/music/`: M1 cavern-curious (default comedy bed), M2 cavern-sneak (the turn), M3 warm-glow (ending), M4 glow-dread (horror), M5 arena-hype (showdown and aura parody; busiest, so mix it lower), M6 nature-doc, M7 full-arc (2 min: curious, sneaky, warm). Switch the bed at the story's turn, as genre videos do. Lyria outputs carry SynthID; check Google's terms before publishing (LICENSES.csv says "check"). The owner picks favourites by ear.
- `scripts/sfx_library.py` curates 70 CC0 Kenney sounds into `assets/sfx/library/<category>/`: impacts, crystal, foley, ui-pops, cartoon-zips and scifi-goo. CC0 needs no attribution. The listening reel and index are in the owner's Downloads (`slugshot-audio-kit`).
- What TOP In My World videos do (Gemini listening to 31 TOP videos, 26 Nov 2026): about 5 effects per video, mostly impacts, whooshes and foley on actions, clustered at the turn; meme sounds are only about 9% of effects; the music bed shifts at the turn in most. **(C, Gemini-reported)**
- Levels that worked in the benchmark:
  - `cavern_bed` as `music` at -30 dB (ducked under speech);
  - landings at -9 to -11 dB;
  - small character sounds at -10 dB.
  - Give each SFX its own level (`"db"`); one global SFX gain flattens the hierarchy.
- Anchor SFX to the script: `"at": "L6.end+0.55"`. Sounds land on actions (a landing, a smile), never as rhythm filler.
- Soundboard bank (real meme sounds, owner-accepted takedown risk; TikTok entertainment posts only, never with the game named): `data/local/research/creative/soundboard/bank.csv`, files in `media/meme/soundboard/`. Pick by scene job, clean clips only.
- **Bed changes follow the energy (owner, 2026-11-27):** rising (calm to tense) may switch sharply on the beat; falling (tense to calm) always sinks away gradually (about 3 s under the new bed). Cut beds together with `scripts/music_beds.py plan.json`, never a fixed short crossfade.
- **No SFX by default (owner, 2026-11-26).** After pilot 01 the owner asked for a clean slate: music only, then they choose the sound language (e.g. a fart on a Floppy impact or a fail). Don't add stings or meme sounds until the owner has chosen them. The Looney Tunes signature over the Inferno miss "didn't fit at all".
- The silence after a punchline stays silent. The bed may continue underneath; nothing new starts. **(D)**
- Listen on a phone speaker before calling a mix done (owner check).

## World sound (2026-11-27)

Owner critique: spatial ambience, crowd audio and environmental sounds. Every Roblox-native scene can now have a world track built from its spec and its take:
- `python scripts/soundscape.py <scene_id> roblox-native/capture/takes/<take>.json out/takes/<take>_world.wav`, then `"ambience": "out/takes/<take>_world.wav"` in the `ss assemble` edit (mixed from 0 s, unducked, at its own level; `"ambience_db"` to trim).
- The track contains:
  - ambience per place (cavern air, waterfalls, drips, crickets, crystal shimmer; room tone, the cavern through the walls and a clock indoors; clinks and lantern hum at the market);
  - crowd murmur that follows the picture (louder as more extras are on screen and near the lens, panned to where they stand), from the take manifest's camera samples (keep `capture.sample`);
  - the crowd's `ambient.reactions` as heard cheers, gasps, laughs and scatters, sized to the crowd;
  - foley from the action: footsteps of walkers near the camera, slug landings, cloth on pick-ups.
- Levels: the bed sits around -35 to -40 dBFS with no normalisation, so a quiet room stays quiet; the final mix's loudness pass lifts everything together.
- Crowd voices: `scripts/crowd_audio.py` (Gemini TTS, generated once into `assets/sfx/crowd/<kind>/`, 58 takes from 12 voices the cast doesn't use, logged in LICENSES.csv; inside the monthly cap). `python scripts/crowd_audio.py demo OUT.wav` plays murmur, a cheer, a gasp and a laugh.
- Deterministic per scene, so every re-render matches. The owner judges the crowd sound by ear.
