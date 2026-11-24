# First use of the editing skill: review record

Video: `SS_20261124_WORLD_ToolkitStory_MultiScene` (toolkit test; stand-in assets, not gameplay). Review method: `.claude/skills/slugshot-video-editing/references/review-and-approval.md`, using `ss sheet` frames every 0.75 s and the `.srt`.

## V01 findings

| Gate | Finding | Fix in V02 |
|---|---|---|
| Captions | On text cards the captions repeated the card ("Would you pick Floppy?" twice) | Captions now hide on cards automatically (template change) |
| Clarity (muted) | The opening card said only "In my world..." while captions were hidden, so a muted viewer never learned the rule "everyone gets one slug" | Card carries the whole spoken line; skill rule added |
| CTA | A question card followed by a "WHICH SLUG?" end card: two asks | Plain SLUGSHOT end card |
| Clarity (phone) | Floppy tiny in the still (blur fit) | Crop fit + slower push; source footage is a tiny preview, so real footage should be chosen tighter |
| Truth | Floppy never transforms; the AI scene is labelled; everything is tagged TEST | none needed |
| Timing | Scene starts follow the script blocks (0.00, 2.32, 3.42, 5.36, 6.62 s); the punch-in lands on "hops" | none needed |

## What Claude could not judge

Whether the line delivery is charming or flat (Kokoro am_puck at 1.05x), whether the test-tone "music" and whoosh feel right (they're placeholders), and whether a stranger would find "So I made him a dream" intriguing or confusing. Those need a person watching on a phone.

## What this showed about the skill

The gate table caught three issues the technical QC couldn't (QC passed V01). Two became new rules in the skill (cards must carry the whole line; one ending). This is the intended loop: review, then fix, then a rule, until platform results replace the hypotheses.
