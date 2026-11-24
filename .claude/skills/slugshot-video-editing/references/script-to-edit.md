# From approved script to edit

## Script format the toolkit reads

Approved scripts arrive from ChatGPT as plain text (`jobs/scripts/*.md`):
- `[SCENE 2 - Floppy still, slow push in]` starts a scene block; the text inside the brackets is a direction, not spoken.
- Every other non-blank line is spoken. Lines starting with `#` are notes.
- One block per scene lets `ss assemble` time each scene to its spoken lines (`"sync": "script"`).

If a script has no scene directions, add them yourself before assembling, and tell the user what you split and why.

## Beat table (write this before building anything)

| t (s) | picture | words (spoken / on screen) | job of the beat | emphasis | sound |
|---|---|---|---|---|---|
| 0.0 | Floppy close-up vs Inferno | "He brought Inferno. I brought Floppy." | premise + stakes | Floppy | none: let the line land |
| 1.8 | first exchange, real gameplay | "I missed my first shot." | complication | missed | the shot's own audio |
| ... | | | | | |

Rules for the table:
- Each row's "job" must be one of: premise, stakes, complication, attempt, worse complication, reversal, payoff, CTA. Two rows with the same job back to back means one should go. **(B/C: story ladder in the research PDF)**
- The ladder: state -> complication -> attempted response -> worse complication -> reversal -> payoff. **(research PDF)**
- If a line describes something the picture already shows, cut the line or change the picture. "And then what happened next was crazy" is always cut. **(research PDF)**
- Causal links ("because", "so", "that was the mistake") hold the story together: keep them even when trimming. **(B/C)**
- Mark the payoff moment exactly. The edit is built backwards from it.

## Choosing pictures for beats

- **Real gameplay** for anything claiming "this happens in Slugshot". Use `ss candidates` on Gemini's timestamps to find moments, then a person picks them.
- **Stills** (reference renders, Flow frames) for story beats, with a slow push (`"zoom": 1.08-1.15`) so they aren't dead. **(D)**
- **Text cards** only for a world rule, a time jump or the final question. Captions are hidden on cards automatically, so the card must carry the whole spoken line.
- **One ending.** A closing question card and an end card asking a second question is two CTAs; keep one. With a question card, use the plain SLUGSHOT end card, or none.
- **AI/Flow clips** only in fiction formats, with a label, and never next to gameplay in a way that suggests the AI event happened in the game. **(A: disclosure rules; research PDF)**

## Timing

- Let `"sync": "script"` place scene starts from the narration's word timings, then adjust by hand only where a visual beat must land on a word (e.g. punch-in on "hops").
- Picture changes slightly **before** the word that names it reads as confident; slightly after reads as lagging. **(D)**
- Total length is whatever the payoff needs. There is no evidence-backed "perfect length". **(A/B: research PDF)** Cut anything after the payoff except the tiny CTA.
