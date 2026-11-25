---
name: slugshot-video-editing
description: Creative editing judgement for Slugshot short-form videos (TikTok, Shorts, Reels). Use when planning, assembling, editing, reviewing or critiquing any Slugshot video or script; deciding hooks, pacing, cuts, zooms, transitions, caption emphasis, comedy timing, SFX, music and narration balance; choosing between PvP gameplay, promo, fiction, meme, character and AI-scene approaches; or judging whether an edit works. Complements remotion-best-practices, which covers the Remotion API itself.
---

# Slugshot video editing and production

The toolkit already does the technical half (cut, caption, zoom, mix, render, QC). This skill is the other half: **why** a cut lands where it does, which word deserves emphasis, when silence beats a sound effect, and whether the result is worth posting. The research PDF's position governs: use general principles as priors and Slugshot's own results as the final authority. No single hook, length or technique is proven to win everywhere.

## Evidence labels (use them when you explain a decision)

- **A**: official platform or Roblox guidance (TikTok, YouTube, Meta, Roblox docs).
- **B**: published research (curiosity, narrative transportation, speech rate, virality).
- **C**: creator practice or public case studies: useful, not proven.
- **D**: our working hypothesis: test it before trusting it.
- **S**: a Slugshot result. None exist yet. When results arrive in the content log, they override A-D for Slugshot.

Say which label a recommendation rests on. Never present C or D as fact.

## Quality bar (owner rules, 2026-11-25)

1. **Pixels and frames.** Masters are 1080x1920 from native pixels: Roblox-native footage comes from film mode (`ss roblox film`, 0 repeated frames). Never upscale a centre crop of landscape footage when a native take is possible. Inspect frames (`ss sheet`) before showing anyone.
2. **Story-matched picture.** Every shot, push-in, reaction and sound is motivated by the script beat it sits on, and timed to the dialogue (line anchors), not to whatever clip was handy. A random idle snippet or a pretty shot with no job is cut.
3. **Identity.** It should look like our world: inked characters, glowing caverns, the Kalam font, one accent colour at a time. See [references/visual-direction.md](references/visual-direction.md). Generic Roblox-story styling (default baseplates, random meme fonts, constant shake) is a fail.

## Non-negotiables before any creative choice

1. **Truth gate.** Check every gameplay claim against `docs/game-truth.md` and re-check `../slugshot/docs/status.md` (read and copy freely; ask before changing game files). Floppy never transforms. Nothing is published, so no "play now". Fiction and AI shots carry a label (WORLD, SKIT and AISCENE presets) and are never cut into gameplay in a way that implies they happened. **(A: Roblox ad standards and platform AI-disclosure rules; research PDF)**
2. **Rights.** Trending sounds are added in each platform's app; only files listed in `assets/LICENSES.csv` go into masters. **(A)**
3. **One video, one promise.** Write down in one sentence what the viewer is promised in the first seconds and where it pays off. If you can't, the edit isn't ready.

## Workflow

1. **Interpret the script**: [references/script-to-edit.md](references/script-to-edit.md). Turn it into a beat table: time, picture, words, job of the beat, emphasis, sound.
2. **Pick the playbook** for the format: [references/format-playbooks.md](references/format-playbooks.md).
3. **Make the decisions**: pacing and cuts in [references/pacing-cuts-zooms.md](references/pacing-cuts-zooms.md); captions and layout in [references/captions-and-hierarchy.md](references/captions-and-hierarchy.md); voice, music, SFX and silence in [references/audio-design.md](references/audio-design.md).
4. **Build** with the toolkit (commands in `docs/COMMANDS.md`):
   - character dialogue: `ss dialogue` → Roblox scene (slugshot-roblox-production) → `ss assemble` with `"dialogue"`, line-anchored `"sfx"` and the `cavern_bed` ambience (worked example: `jobs/bench/floppy-seven-qwenclone.json`);
   - one clip: `ss render --format X`;
   - several scenes, stills, cards or a script: `ss assemble jobs\<edit>.json` (use `"sync": "script"` so scenes follow the narration);
   - several hooks: `ss batch`.
5. **Check**: `ss qc` (technical) and `ss sheet <video>` (frames to look at). Then use the creative review in [references/review-and-approval.md](references/review-and-approval.md), which also says what needs a person or Gemini.
6. **Record the hypothesis.** Every variant in `exports/share/variants_log.csv` should map to one question (e.g. "underdog hook vs direct pitch"), so results can teach something.

## The ten rules that matter most

1. The first beat shows visual evidence plus understandable stakes, not an intro. Surface the proposition within ~3 s, the hook within 6 s. **(A: TikTok creative guidance; "one-second hook" is C)**
2. Reveal the premise, delay the resolution. Too vague and too concrete both lose. **(B: curiosity-gap meta-analysis)**
3. Every beat must change something: a new fact, danger, relationship, attempt, reversal or payoff. Cut or merge beats that don't. **(B/C: research PDF)**
4. A cut, zoom, SFX or caption earns its place only by adding information, emotion or clarity. No ritual "pattern interrupts" every two seconds. **(A: TikTok frames these as optional techniques; D)**
5. The payoff must be visible on screen, not described. If the narration says "watch this", show it. **(research PDF rubric)**
6. Make it understandable muted on a phone: captions, readable action, nothing important under the platform buttons. **(A: safe areas; research PDF clarity gate)**
7. Emphasise the words that carry new information (names, stakes, the reversal), at most one or two per caption page. **(D)**
8. Hold a short silence before a punchline or reveal instead of covering it with music or a whoosh. **(D: standard comedy craft, untested here)**
9. Narration: write tighter first, then speed up modestly (≤ about 1.1x), keeping micro-pauses at meaning changes. **(B: comprehension drops at high rates; pauses help)**
10. The CTA is tiny and comes after the payoff: "Slugshot on Roblox", "Would you pick Floppy?". Never interrupt the story to sell. **(research PDF; A: Roblox advises leading into gameplay)**

## What Claude can and can't judge

Claude can reliably check: structure against the script, truth claims, caption text and timing, scene timing against narration, text overlapping action (from frames), loudness and technical faults. Claude can't reliably judge: whether it's funny, whether the energy feels right, whether a stranger "gets it" in two seconds, or whether the music works. Those need a person, and sometimes a Gemini first-viewer pass (see the review reference). Say so plainly in every review rather than giving a confident verdict.
