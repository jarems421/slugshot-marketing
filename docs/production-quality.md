# Production quality and workflow

Infrastructure is frozen. Prioritise reusable Roblox takes and finished English and Spanish videos. Use the [inventory](INVENTORY.md) for implementation status and the [production review archive](archive/production-quality-reviews-2026-11.md) for dated experiments, tool decisions and owner feedback.

## Master checklist

- Deliver 1080×1920 from native pixels. Film staged Roblox footage in film mode at 30 fps and decode with `ss roblox film`. Patch missing ranges until the decoder reports zero repeated frames. Inspect actual decoded frames.
- Give every shot, acting beat, camera move and sound a job in the script. Anchor changes to the dialogue, such as a Floppy push-in that lands on his name. Check mouth timing, reaction, eyeline and the held beat before a cut.
- Use inked characters, glowing caverns, restrained effects and legible Kalam captions. Test on a phone with sound off, then listen for intelligibility, pacing and mix.
- Keep visuals language-neutral where possible. Record, time and caption the English and Spanish reads independently.
- Verify the mechanics, rights and scene classification. Label staged fiction and AI scenes with the appropriate preset. Apply [game truth](game-truth.md) and record approved audio in the [licence register](../assets/LICENSES.csv).
- Use `ss qc` and `ss sheet`, watch the edit at speed and report the findings from the check. Put voice, humour, brand fit and the final watch in front of the owner. Follow the [publishing approval guide](dashboard/publishing.md).

## Workflow

1. Develop the script with the [script-writing skill](../.claude/skills/slugshot-script-writing/SKILL.md). Run `ss dialogue` to get the manifest, words, captions and timing. Review flagged lines by ear.
2. Stage and validate the scene in the isolated place. Direct the take and check framing before filming. See the [Roblox production skill](../.claude/skills/slugshot-roblox-production/SKILL.md).
3. Assemble the decoded footage with the dialogue manifest and resolve caption, label and audio issues. See the [video-editing skill](../.claude/skills/slugshot-video-editing/SKILL.md).
4. Confirm draft metadata, platform-specific text and rights before owner review. Use [Publish](dashboard/publishing.md) to record a post and its version. Record observations at comparable ages and use the [dashboard learning loop](dashboard/README.md) for the next brief.

## Flow and Gemini handoffs

- **Flow:** use approved reference stills for short original cutaways, preferably 9:16. Save MP4s or stills to `media/flow/`, check silhouette, proportions, expressions and colour against the reference, then set a visible AI scene label in `ss assemble` or use the AISCENE preset with `ss render`. Set scene volume to zero when generated audio clashes with narration. Check platform disclosure requirements during upload preparation.
- **Gemini gameplay review:** import the recording with `ss import`. Supply cleared footage and ask for a CSV with `start,end,what_happens,why_a_stranger_could_care,emotion,best_format,hook_idea,payoff,confidence,potential_misinterpretation`. Use M:SS or seconds and mark uncertain observations. Run `ss candidates <recording> <gemini.csv>`. Watch the padded clips, verify the source timecodes in `index.csv` and use the confirmed start and end times in the edit.
- Confirm cloud sharing permission for unreleased footage and third-party media. Check game facts directly before using a Gemini description of a mechanic.

## Open production work

- Capture a real PvP round through OBS and run the complete import, selection, caption, render and phone review. Use film mode for scripted scenes. Build more reusable acting and scene setups as scripts need them.
- Choose voices and audio by ear and record approvals. The sampled In My World TOP tier had a median voice pace of about 215 words per minute. Treat the [dated sample](archive/production-quality-reviews-2026-11.md#10-final-sample-review-2026-11-25) as a genre reference. Check comprehension and save room for the reversal.
- Finish brand assets and original or licensed music as needed. [Music brief](creative/music-brief.md)
- Run the first approved posts and validate the same-age measurement workflow on real data. Player-side metrics await launch.

[Earlier production checklist](archive/production-checklist.md) · [Original Flow and Gemini notes](archive/flow-and-gemini.md)
