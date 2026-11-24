# Creative review and approval

## 1. Technical (automatic)

`ss qc` runs after every render: size, codec, loudness, peaks, black, frozen or silent stretches. A FAIL blocks; a WARN needs a reason.

## 2. Claude's review (do this for every edit, and write it down)

Run `ss sheet <video>` (one frame per second, plus the scene starts if it's an assembled edit) and read the `.srt`. Then answer, briefly and specifically:

| Gate | Question | How Claude checks |
|---|---|---|
| Truth | Is every gameplay claim implemented or clearly fictional? | script and captions vs `docs/game-truth.md`; labels present on fiction/AI scenes |
| Hook | Would a non-Slugshot viewer know why to care in the first 2-3 s? | first two frames + first caption page |
| Clarity | Is the conflict clear muted, on a phone? | frame sheet at phone size; captions cover every line |
| Payoff | Does the video visibly resolve the opening promise? | locate the payoff frame; it must exist |
| Beats | Does every beat change something? | beat table vs frames; flag repeats |
| Hierarchy | One focal point per frame; text never on the action? | frame sheet |
| Captions | Names spelled right, emphasis on the right words, no duplicates with cards? | `.srt` + frames |
| Audio | Voice clear over music; silence before the punchline? | loudness from QC; listen if possible, otherwise flag for a person |
| CTA | Tiny, after the payoff, true to launch state? | last 3 s |
| Character | Slugs match approved designs; Floppy doesn't transform? | frames vs reference stills |

The research PDF's script rubric also applies: natural speech, specificity, energy, clarity, character, tension, progression, payoff, humour, sales pressure, truth. Score **observable failures**, not "AI-ness", and **never give a numeric grade**. The model grading itself proves nothing.

## 3. What needs a person (always say which apply)

- Is it **funny / exciting / satisfying**? Claude can't judge this.
- Does the **voice** sound energetic and natural (especially Kokoro)?
- Does the **music** fit and feel right?
- **Phone test**: watch it once start to finish on a phone, muted and unmuted.
- **Rights and disclosures** on each platform at upload time.
- Final publish decision. Nothing publishes automatically.

## 4. When to use Gemini as a "first viewer" (optional, before posting)

Use it when a format is new, a story is complex, or you're unsure the premise is clear. Upload the master and ask:
> "You've never heard of this game. Describe what you understood at 2 seconds, at the midpoint and at the end. Where would you have scrolled away and why? What did you think the video was promising? Describe only what you can see and hear; say UNCERTAIN otherwise."

Compare the answers with the intended promise. Treat mismatches as questions for a person, not verdicts. Gemini can misread game state and timing (research PDF). Don't upload YouTube API data to Gemini (internal only, see `docs/youtube-api-policy.md`).

## 5. After posting

Platform results (retention curve, stayed-to-watch, shares, Roblox share-link players) beat every rule here. Record them against the variant's `experiment_id`. When a pattern repeats across several posts in the same format and platform, add it to this skill as an **S** rule, with the evidence, and demote any rule it contradicts.
