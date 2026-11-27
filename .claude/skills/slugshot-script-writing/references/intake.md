# Intake: the owner's video, drawn out in full (owner rule, 2026-11-27)

The owner describes each video in as much detail as they can. Claude then asks about everything still missing or
ambiguous, until the owner says it's enough, so the script, the picture and the sound match with no guesswork.
Claude generates premises, lines or drafts **only when the owner asks**; otherwise the ideas are the owner's.

## How to run it

1. Read the owner's description twice. List what is decided, what is implied, and what is missing.
2. Ask in rounds of 3–4 questions, multiple choice where the options are clear (`AskUserQuestion`), free text where
   taste matters (a line's wording, a joke, a look). Never ask what the description already answers.
3. After each round, play back the decisions in one short paragraph so the owner can correct them.
4. Keep going until every box below is filled or the owner says stop; then write the brief.

## The checklist (every box filled before filming)

- **Premise and job:** the one-line rule or situation; why someone keeps watching; the payoff; what the viewer should feel at the end; the marketing job (see marketing-fit.md); the caption (it states the premise).
- **Length and language:** target seconds; English, Spanish or both (Spanish timing and jokes made separately).
- **Every line:** speaker; exact words (the owner's own where they gave them); delivery direction; what is on screen while it's said; where the laugh lands; pauses, overlaps and interruptions.
- **Every scene:** set or location (hub plaza, grove, arena, bedroom, classroom, wild cavern, market, or a new one to build); light and mood; who is there and where they stand; what the background is doing (empty, busy hangout, ring of watchers, scatter, vignettes such as a show-off or runaway slug); props and what's done with them (held slugs, hand-offs, sitting).
- **Camera:** what each shot shows and why: wide to establish places and groups, medium for lines, gestures and reactions, close only for a punchline or tension; slug POV rides, split screens, slow motion; how we travel between places (dip through black or seen travelling).
- **Acting:** each character's emotion per beat; signature mannerisms to lean on or hold back (Kai's big gestures, Raf's hype, Mira's deadpan, Juno's stillness, Floppy's drowsy dignity); reactions and interruptions that sell the joke.
- **Sound:** the music bed per section and every energy change (sharp going up, gradual coming down); SFX moments, including the owner's soundboard picks and where they land; crowd sound (murmur, cheers, gasps) and moments of silence.
- **Truth and limits:** game facts used (check game-truth.md; Floppy never transforms and deals 7 damage); fiction label; the reveal lock (don't name the game); anything that must not happen.

## Hold it to what works (research guardrails)

Check the idea against [format-in-my-world.md](format-in-my-world.md) (or the format module that fits) and
`ss kb brief` while interviewing, not after. When the owner drifts from what the data supports, say so plainly,
show the evidence, and offer a version that keeps their idea inside what works. The owner decides; a deliberate
break goes in the brief with the reason.

| If the idea... | Say | Offer |
|---|---|---|
| copies or reskins an existing video | No TOP post copied an earlier one; 3 MID and 6 FLOP did | keep their engine, change the world and the turn |
| rests on stock fantasy, ranks or power levels | generic fantasy leans to flops (TOP 3–6 vs FLOP 13–14 of 50) | a concrete everyday rule with slugs in it |
| has generic, unvoiced narration | specific voiced narration: TOP 1 vs FLOP 11 for generic prose | rewrite in a voice with a point of view |
| has a vague caption ("Part 3", "In this town…") | the caption states the premise: TOP 43 vs FLOP 32 of 50 | a caption that says the rule |
| narrates slowly or sparsely | the genre runs ~210 wpm, narration from frame one covering ~90%, a steady bed | trim words or tighten pauses |
| runs long | TOP median 109 s; none over 240 s reached TOP | cut to the strongest 60–170 s |
| is a numbered sequel or asks for subscribes | sequels lost 3–18x reach; subscribe bait appears only in MID and FLOP | a standalone story in the shared world |

These are associations, not guarantees (CONFIRMED vs TEST labels in the module). Our own posted results override them once we have them.

## The brief: `jobs/briefs/<id>.md`

1. Title, caption, format and job, length, language.
2. Beat table: time, line, speaker + direction, shot, set, acting, background, sound.
3. The cast script in `ss dialogue` format.
4. Deliberate breaks from the research, with reasons; game-truth claims; what needs the owner's ear.

The owner confirms the brief before filming. The scene spec and the edit are built from it line by line, and any
change during production goes back into the brief.
