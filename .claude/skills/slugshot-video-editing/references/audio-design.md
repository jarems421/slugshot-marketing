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
