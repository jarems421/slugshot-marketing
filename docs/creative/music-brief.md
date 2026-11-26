# Music brief: Slugshot story beds (26 Nov 2026)

## What the data says (genre convention, not an edge)

From Gemini listening to 31 TOP and 20 FLOP In My World videos, plus our loudness measures on all 50 TOP:
- A music bed is always present, about 8 dB under the voice, mostly mid tempo (about 100–120 BPM).
- Comedy beds are whimsical: pizzicato strings, marimba, playful plucks. Horror beds are drones and music boxes.
- The bed **shifts at the story's turn** (TOP 23/31, FLOP 15/20), often resolving warm at the end.

TOP and FLOP do this alike. Music won't make a video win, but a bed that's missing or wrong makes it read as off-genre.

## The Slugshot twist

The game's sound identity is "tactile cavern fantasy" (`../slugshot/docs/audio/sound-plan.md`): calm bases, small magical accents, crystal resonance, far water, a warm glow hum, soft damp creature sounds. Our beds keep the genre's whimsy and add that world: celesta and crystal-bell accents, water-drip percussion, a low glow hum, and a soft squishy percussion voice for the slugs. Bold and readable like the comic-book art, never busy.

## Room for the voice

The narrators being tested are deep, dry male voices (Algieba, Orus, Puck) and warm or bright female ones (Sulafat, Aoede, Kore), all at about 210 wpm. So:
- Instrumental only; no vocals or choirs.
- Keep the 1–4 kHz speech range sparse: melody in plucks and bells above it, warmth below it.
- No constant lead melody; short motifs with space between them.
- One shared key and tempo across the comedy, tension and resolve beds, so an edit can switch at the turn without a clash.

## The set

All in D (major for comedy and resolve, minor for tension and dread), instrumental and loop-friendly.

| ID | Use | Prompt core |
|---|---|---|
| M1 Cavern Curious | default comedy and story bed | 108 BPM whimsical, playful: pizzicato strings and marimba, celesta and crystal-bell accents, soft water-drip and squishy percussion, warm low hum; sparse, space for narration |
| M2 Cavern Sneak | the turn, rising stakes | same key and tempo as M1, turned sneaky: low pizzicato, ticking woodblock, cave drone underneath, occasional glassy shimmer |
| M3 Warm Glow | endings and heart beats | slow, warm: soft felt piano, gentle strings, a crystal shimmer, far water; resolving and tender |
| M4 Glow Dread | horror and rule-horror stories | slow and eerie: music box in D minor, deep cave drone, distant drips, a faint glassy whine, very sparse |
| M5 Arena Hype | showdowns, aura and Potential Man parody | 120 BPM comic-book epic: punchy drums, brass stabs, crystal hits, over-serious on purpose, with gaps for jokes |
| M6 Nature Doc | deadpan documentary narration | gentle orchestral wonder: strings and woodwinds, documentary calm, a little too majestic for a slug |
| M7 Full arc (longer) | a whole story in one track | 2 minutes: M1 feel → shifts to M2 at about 60% → resolves into M3 for the last 20 s |

## Production

Generated with Google Lyria via the Gemini API, only with the owner's approval. Each output carries Google's inaudible SynthID watermark. Check Google's current terms for commercial use before publishing. Every kept track goes in `assets/music/` and is logged in `assets/LICENSES.csv`. Placed in edits with `ss assemble` `music` at about −22 dB and ducked under speech.
