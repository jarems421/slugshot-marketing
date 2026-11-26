# Voice, dialogue and humanisation (for spoken short-form)

The goal is lines people would actually say, in voices you can tell apart, that are fun to hear. The goal is not to pass AI detectors. This module adapts the craft parts of **humanize** (harshaneel/humanize, MIT, © 2026 Harshaneel Gokhale) for voiced scripts. Its detector-specific rules (curly quotes, semicolons, statistical targets) are left out, because TTS and viewers don't care about them.

## Read it aloud, as the character

- If it's awkward to say in one breath, rewrite it. Contractions, fragments and run-ons are fine; it's speech.
- **Rhythm:** mix very short lines with longer ones. "Then the coin stopped." after a long run lands harder than three medium sentences in a row. Avoid long stretches of same-length sentences (humanize, lever 2).
- **Specific beats general**, every time: a number, a name, a prop, an exact action. "Nobody liked him" → "He's eaten lunch alone for seven years." (humanize, lever 5)
- **Say what the thing is.** Cut "not just X, it's Y" and "it isn't X, it's Y" pivots, including poetic ones (humanize, hard rule 5).
- **Break symmetry.** Neat triplets, matched pairs and repeated sentence openings (anaphora) read machine-made. Make the third item weird, longer or cut it (humanize, creative register).
- **No assistant voice** in narration: no recaps, no "Let me tell you about…", no moral spelled out at the end, no "And that's when I realised…" doing the work a moment should do (humanize, lever 9).
- **Watch-list words in our data** lean towards flops: "suddenly", "nobody knows why", "I couldn't believe", "something unbelievable", "ranked", "subscribe". The fix is a concrete moment, not a synonym. Swapping "suddenly" for "out of nowhere" is the same tell.
- **TTS craft:**
  - Delivery goes in the (direction), never in the line.
  - Avoid em dashes and ellipses as pacing hacks; use a `[beat]` instead.
  - Write numbers as they should be said ("seven damage").
  - Names should be easy to say and spell.

## Dialogue

- **People don't explain what both of them know.** Let the viewer catch up from context.
- **Reactions are short and specific.** "Ugh… five more minutes." beats "I am very tired and don't want to get up."
- **Interruptions and overlaps** (`[overlap 0.2]`) make exchanges feel alive. Use them for arguments and hype.
- **Understatement** often gets the laugh: the bigger the event, the smaller the line ("It had kept my skateboard.").
- **Give the last word to the funniest character,** not the most important one.
- Keep exchanges tight: 2–4 lines, then back to the story.

## Cast voice sheet (`config/cast.json`; personas are drafts)

| Character | Voice in a line | Avoid |
|---|---|---|
| FLOPPY | drowsy, slow, dead-serious dignity; few words, total self-belief | being powerful, transforming, "doing nothing" |
| RAMMSTONE | loud, cocky, short fuse; brags, then cracks when rattled | being genuinely menacing |
| AQUABEEK | one dry line that lands; the smartest in the room | speeches |
| INFERNO | quick, excitable, flares up and cools down in one exchange | sustained anger |
| TORMATO | bouncy, chaotic, changes topic mid-sentence | coherence |
| BOONDOC | gentle, fussy healer; the grown-up; nods along | sarcasm |
| PHOSPHORO | small, curious, "wait, why?"; delighted by facts | cynicism |
| KAI | Floppy's proud, overconfident partner; fast talker; loves a reveal | doubting Floppy |
| MIRA | dry, deadpan comeback | hype |
| JUNO | cool ace; few words, big entrance | chatter |
| RAF | loud hype man, always arriving mid-sentence | calm |
| NARRATOR / NARRATOR_F | the storyteller. Voice and gender are being tested; tone set per script | sounding like an announcer |

**Character-specific vocabulary:** each speaker should have 1–2 verbal habits, e.g. Kai's "watch this", Mira's flat "great", Floppy's slow "mm" before every line. Keep them light and consistent across videos so viewers recognise them.

## Natural-language check (before the checker)

1. Can you hear who's speaking without the name tag?
2. Is there one line you'd quote to a friend?
3. Did any line explain the joke?
4. Would a 13-year-old say this out loud without cringing?
