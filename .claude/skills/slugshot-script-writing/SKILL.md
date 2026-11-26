---
name: slugshot-script-writing
description: Write, revise, humanise or critique any Slugshot short-form script (TikTok, Shorts, Reels) before production. Covers premise generation, hooks, story progression, character voice and dialogue, humour and cultural references, how the game fits the entertainment, and pre-production script review. Includes format modules (In My World / In This Town, with verified findings from a 631-post TikTok bank; memes and recreations as that research lands). Use when drafting, punching up, checking or choosing between scripts, or when turning a script into the ss dialogue format. Pairs with slugshot-video-editing (script-to-edit and finished-video review) and slugshot-roblox-production (filming).
---

# Slugshot script writing (v2.1, 26 Nov 2026)

This skill covers the words before production: what the video is about, how it's told, who says what, why it's funny, and why it's worth filming. Editing decisions and finished-video review belong to slugshot-video-editing (`references/script-to-edit.md`, `references/review-and-approval.md`).

The aim is exceptional, original, entertaining videos that make Slugshot's world and slugs memorable. The aim is **not** average scripts that tick boxes. Research tells us where the floor is and which traps to avoid. It doesn't tell us how to be brilliant, so leave room for that.

## How to read the guidance

Every piece of guidance carries one of four labels. Keep them distinct.

- **MUST**: truth, originality and IP, audience suitability, publishing rules. Never trade these for a laugh.
- **CONFIRMED**: an association that survived blind checking in our data, e.g. copies never reached TOP and generic AI prose leans towards flops. Follow it. It's still association, not cause.
- **CONVENTION**: what a format does in every tier, hits and flops alike. It makes the video read as that format. Use it by default, break it on purpose, and never credit it for a result.
- **TEST / JUDGEMENT**: plausible patterns, formulas and craft advice. They're options and tools, not requirements. A good reason beats any of them, so write the reason down.

Our own posted results override all of the above once they exist.

## MUST (non-negotiable)

1. **Game truth.** No gameplay claim unless `docs/game-truth.md` allows it; re-check `../slugshot/docs/status.md` for anything mechanical. Floppy is the weakest slug, not useless: it deals 7 damage, never "does nothing" and never transforms. Fiction carries the on-screen "Fictional story" label. Generated or AI scenes are never presented as gameplay.
2. **Originality and IP.**
   - Original premises and dialogue. No copied or reskinned scripts.
   - Borrow a format's grammar, never someone's exact edit, lines, characters, footage or music.
   - No impersonating real streamers, no cloned voices, no fake endorsements or invented quotes.
3. **Audience suitability (kids to 18).**
   - No sexual innuendo, slurs or swearing.
   - Mild toilet and slapstick humour is fine.
   - Never make a nationality, ethnicity, disability or body the punchline.
   - Dialect and accents are delivered with respect, by appropriate voices.
4. **Publishing.**
   - Don't name the game while `publishing.reveal_lock` is on.
   - No "play now" until the game is out.
   - Trending audio only if it's cleared on each platform; masters use original or licensed audio.
   - Species names are the owner's call.

## Process (diverge, choose, draft, humanise aloud, critique)

1. **Brief.** Know the format, the marketing job (see [references/marketing-fit.md](references/marketing-fit.md)), the cast and the length range. If there's a cultural or meme brief from ChatGPT, use it. Don't invent trends.
2. **Diverge (when you need to).** With no strong idea yet, write a spread of one-line premises from several engines in [references/craft.md](references/craft.md), including a couple that break the format's usual moves, and don't judge yet; 8–12 is a useful default. With an idea that's already exceptional, skip ahead. At most, sketch one or two alternatives to check it really is the best version.
3. **Choose 1–2.** Ask: is it specific and original, can a viewer picture it in seconds, does it make a slug or the world memorable, and is there a payoff you can already see? Keep one safe option and one bold one.
4. **Draft** the chosen premise with the format module as a menu of moves, not a sequence. Write 2–3 honest openings and pick in critique.
5. **Humanise aloud.** Read every line as the character would say it ([references/voice-and-dialogue.md](references/voice-and-dialogue.md)). Rewrite anything nobody would actually say. Let humour come from the situation ([references/humour.md](references/humour.md)).
6. **Critique** with [references/critique.md](references/critique.md): what's weak, predictable, forced or generic, and what's unusual on purpose and worth protecting. Then run the checker as a final signal pass (it measures text, not quality):
   `python .claude/skills/slugshot-script-writing/check_script.py DRAFT.txt --seconds 90 --caption "..." [--format imw]`
7. **Handoff** in the format below. Flag anything deliberately unconventional, so nobody "fixes" it towards the average.

## Format modules

- **In My World / In This Town:** [references/format-in-my-world.md](references/format-in-my-world.md). It holds verified findings, conventions and cautions, plus the evidence ([references/evidence.md](references/evidence.md)) and Gemini's formula routes as TEST ([references/formulas.md](references/formulas.md)).
- **Memes, powerscaling humour, streamer-moment recreations:** [references/format-memes.md](references/format-memes.md) (research in progress; general craft applies meanwhile).
- **Anything else** (gameplay skits, character comedy, aura parodies, documentary voice): use the core process and craft. Don't import another format's findings.

## Handoff format (production-ready)

Return, in this order:
1. **Title.**
2. **Caption.**
3. **Format and marketing job.**
4. **Target length and word count.**
5. **The script** in `ss dialogue` format:
   - `NARRATOR (direction): line`
   - `CHARACTER (direction): line`
   - `[beat 0.25]` for pauses; `[overlap 0.2]` for interruptions.

   Speakers come from `config/cast.json`. Put delivery in the (direction), never in the spoken words.
6. **Optional visual notes** per beat (what's on screen), useful for Roblox staging.
7. **A 4-line note:**
   - what it's doing (and the label: CONFIRMED / CONVENTION / TEST);
   - what it deliberately breaks, and why;
   - game-truth claims (or "none");
   - what needs the owner's ear: humour, voice, feel.
