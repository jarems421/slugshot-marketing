# Humour and cultural references

Adapted from the marketing bank's safeguards (docs/Slugshot-Marketing-Bank.md, "Cultural intelligence and humour"). What's currently funny changes, and ChatGPT supplies dated cultural briefs. This module covers how to use them.

## Humour comes from the situation

- The laugh should come from **premise, character and timing**, not from a reference pasted on. A meme should add meaning to a scene that already works without it.
- **Mechanisms that suit our cast:**
  - contrast (grand build-up, tiny payoff: an aura entrance, then Floppy's hop);
  - deadpan understatement;
  - status reversal;
  - escalation to absurd;
  - a character taking something stupid completely seriously;
  - the literal reading of a figure of speech;
  - the callback;
  - the wrong answer: the viewer knows the answer, the character doesn't, and the consequence is the punchline (format-memes.md, "Wrong answer, get him");
  - the straight-faced crossover: a famous boast or edit style moved onto the wrong subject and played completely seriously (format-memes.md, "I wasn't born yet"). The owner's view: these "almost always work when executed precisely", so timing is the whole job.
- **Timing:** a short pause before the punchline (`[beat]`), the punchline as the shortest line nearby, and nothing after it that explains it. If you have to explain it, cut it or rebuild the setup.
- **Predictable jokes:** if the viewer can finish the line, either subvert the last word or cut to the reaction instead.

## Cultural references and memes

- Use a reference only with a **dated** brief that says what knowledge the viewer needs, why it fits, and whether it's emerging, active or saturated. Never assert a trend is current from memory.
- **Borrow the grammar, not the property.** That means the meme's setup, expectation and reversal, rebuilt with our characters, voices and lines. Never someone's exact audio, footage, dialogue or character.
- **Prefer one reference per video.** Stacked memes often read as trying too hard. That's a preference, not a limit: when the crossover itself is the joke (two memes colliding, or a meme dropped into the wrong genre), combine them deliberately, and make sure each one earns its place.
- **Slang:** only in a character whose voice it fits (Raf, maybe Inferno). Never in the narrator by default. Forced slang ages fast and reads as adults imitating kids.
- **Late meme copies flop.** In our data, a straight copy of the huss template got 6.5k against the 19.9M original. Flip the meme (new POV, new genre, Slugshot twist), don't repeat it.
- **Real people:** parody the *format* of a famous moment, performed by our characters, never an impersonation of the person.

## Sound in the script (TEST; observed in TOP In My World videos, 26 Nov 2026)

Gemini listened to 31 of the 50 TOP videos. These are its reports, cross-checked with our own loudness measures on all 50.

- **Music bed under everything:** present in 31/31, mostly mid-tempo, about 8 dB under the voice. Comedy beds are whimsical (pizzicato, marimba); horror beds are drones and music boxes. **It shifts at the turn** in 23/31, often resolving warm at the end. Mark the shift in the script: `# music: shift to tense at the reveal`.
- **Sound effects:** a median of 5 per video (0–20), mostly impacts, whooshes, foley and character vocal lines tied to on-screen action. They cluster **at the turn** (41%) and in world-building examples, rarely on the hook.
- **Meme sounds are seasoning:** only 16 of 181 effects were a recognisable meme sound (huss chant, vine boom, Tung Tung Sahur, "ka-ching", "what"). One well-placed meme sting beats a stream of them. Use original or cleared versions only.
- **Narrators:** 31/31 sounded male and 29/31 like AI TTS. An AI voice is normal for the genre, and a female narrator would stand out (TEST it).
- **Sound is a CONVENTION, not an edge.** The same check on 20 FLOP videos found the same picture: a bed in 20/20, a shift at the turn in 15/20, male AI narrators 20/20, and *more* effects (median 9 vs 5 in TOP). More effects don't help; place a few on real actions and on the turn.
- Write the joke so it works without the sound, then mark where a sting or shift helps (`# sting: boom on "eleven hours"`).
- **The kit:** our original accents via `ss sfx` (boing, slides, pop, sub_boom, riser, tension_sting, record_scratch, sparkle_reveal and the cavern set) and 70 CC0 sounds in `assets/sfx/library/` (impacts, crystal, foley, UI pops, cartoon zips, sci-fi and goo). Name the sound in the note so the edit can find it. Music beds M1–M7 are in `assets/music/` (brief: docs/creative/music-brief.md). Mark the bed and where it switches, e.g. `# music: M1, switch to M2 at "Then the coin stopped"`.

## Needs a person

Whether something is funny, current or cringe can't be settled by a model. Say which lines need the owner's ear.

## Soundboard bank (26 Nov 2026; owner decision)

- **What's in it:** 539 real soundboard and meme sounds (TikTok soundboard posts and Cuffem clips), each cut to its own file in `media/meme/soundboard/`.
- **Index:** `data/local/research/creative/soundboard/bank.csv` (owner copy: Downloads `slugshot-audio-kit\soundboard-bank\BANK.md`), with Gemini's description of how each sounds, what it's used for, the scenes it fits, and whether it's clean.
- **Signature sound (owner pick):** `SIGNATURE-whistle-donk-fart.wav`. A slide-whistle build-up, a smooth donk, a short pause, a fart. Use it for hype that deflates: a big attempt that flops, an entrance that fizzles. Save it for the moment that earns it; overuse kills a signature.
- **How to place one:** pick by the scene's job (fail, shock, awkward, reveal, hype, transition), write it as `# sfx: <file> on "<word>"`, and keep one strong sting per beat.
- **Limits** (the owner accepted the takedown risk): TikTok entertainment posts only; never in a post that names the game; clean clips only; names and descriptions are Gemini's and need checking by ear.
