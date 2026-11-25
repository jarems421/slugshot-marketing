# Narration, music, SFX and silence

## Balance (what the toolkit does by default)

- Masters land at about -14 LUFS integrated, true peak ≤ -1 dBTP (`ss qc` checks). **(C: common platform loudness practice)**
- Voice is the priority. `ss audio mix` ducks music about 13 dB under speech (`--music-db -18` to `-24` for the bed). If you can't follow the words at low phone volume, the music is too loud. **(research PDF audio gate)**
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

- `ss sfx` makes the original procedural set in the game's "tactile cavern fantasy" direction (`../slugshot/docs/audio/sound-plan.md`): `cavern_bed`, `slug_land`, `floppy_burble`, `whoosh`, `crystal_tick`. It is logged in `assets/LICENSES.csv` and cleared for every platform. **(owner direction for the game; D for video)**
- Levels that worked in the benchmark:
  - `cavern_bed` as `music` at -30 dB (ducked under speech);
  - landings at -9 to -11 dB;
  - small character sounds at -10 dB.
  - Give each SFX its own level (`"db"`); one global SFX gain flattens the hierarchy.
- Anchor SFX to the script: `"at": "L6.end+0.55"`. Sounds land on actions (a landing, a smile), never as rhythm filler.
- The silence after a punchline stays silent. The bed may continue underneath; nothing new starts. **(D)**
- Listen on a phone speaker before calling a mix done (owner check).
