# Audience sentiment and opportunities (Stage 4.7)

**Why:** popularity says what's being made; comments say what some viewers are tired of, miss, or want instead. Fatigue with a format can be a creative opening (parody, expectation reversal), and it can also make any reference unappealing. The output is a written judgement, never a score.

## Sources and gates (`config/research/settings.json` → `sentiment`)

| Source | Route | Status |
|---|---|---|
| YouTube API comments (`ss yt comments`) | `ss sentiment packet --youtube --ids …` | **On**: `youtube_api_derived_metrics_accepted: true`, based on the owner's statement (25 Nov 2026) that the derived-metrics amendment was accepted with the API key. Add Google's confirmation to `youtube_amendment_reference` |
| Public pages a person copies (TikTok, Instagram, YouTube web, Reddit, DevForum) | `ss sentiment packet --paste FILE --platform …` | **On**: manual only; no scraping, browser bots or logged-in automation |
| Our own accounts after launch | Instagram API comments (dashboard connection), YouTube own-channel API, TikTok Studio by hand | later |
| Reddit / DevForum automated access | — | **Off**: Reddit needs API approval and blocks agents; DevForum terms not reviewed |

The policy basis is Google's [derived-metrics policy](https://developers.google.com/youtube/terms/derived-metrics-policy) (updated 14 Sep 2026). It allows NLP sentiment on API comments for clients that accepted the amendment. Derived results may be kept for up to 36 months; comment text keeps the 30-day rule; inferring protected attributes such as age is not allowed. See ledger `AUDIT-STAGE46-PLATFORM:C15`.

Always on:
- comment text lives only in a packet that expires (`ss sentiment prune` deletes it);
- handles are scrubbed and no usernames are stored;
- no demographics are inferred;
- per-video and per-thread counts only (`cross_channel_aggregate: false`);
- `raw_comment_export_to_ai: false`, so comment text never goes to `exports/share` (ChatGPT or Gemini), and `ss yt report --comments` refuses until the owner changes it;
- Claude codes comments locally in this workspace.

## Workflow

```powershell
.\ss yt comments --ids VID1,VID2 --max 30                    # 1 unit per video
.\ss sentiment packet --youtube --ids VID1,VID2 --target "Huss / In This Town format" --selection "relevance order; 2 ordinary + 2 featured clips"
# or: .\ss sentiment packet --paste pasted.txt --platform tiktok --locator URL --target "..." --selection "first 20 visible"
# Claude (or a person) codes each item in <name>.annotations.jsonl using <name>.md (built from the codebook)
.\ss sentiment join <packet>.jsonl <packet>.annotations.jsonl --notes "our own paraphrase"
.\ss sentiment list ; .\ss sentiment prune
```

## Codebook (`config/research/codebooks/slugshot-sentiment.json`, v0.2)

**Eleven multi-label codes**, each marked present, absent, uncertain or unreviewed:
APPRECIATION, CRITICISM, FATIGUE, CRINGE, AUTHENTICITY_AI, NOSTALGIA_FORMAT, REQUEST_ALT, HUMOUR_APPRECIATION, PLAY_INTENT, DISAGREEMENT, PARODY_SIGNAL.

**Item fields:**
- `stance`: positive, negative, mixed, neutral or unclear;
- `target`: one or more of format, sound, meme, creator, game, brand, other_commenter, unclear;
- `irony`: literal, ironic or unclear;
- `language`: as observed in the text.

**Subtypes, recorded only when the code is present:**
- PLAY_INTENT: information_request ("what game?" is interest, not intent), release_interest, expressed_play_intent or ambiguous;
- FATIGUE: intensity;
- AUTHENTICITY_AI: suspicion vs assertion.

Emoji and ambiguous irony (for example "es cine", "me muero") stay *uncertain* unless the context settles them.

## Reading samples

A sample is one read of one target. Commenters are self-selected, so the read describes what some commenters wrote: not the audience, not prevalence, not a lifecycle. A few contradictory comments and ordinary clips matter more than top comments. A two-date comparison helps with fatigue claims, but you don't need one to try a cheap hook.

Popularity, velocity, persistence, saturation, sentiment, fatigue and Slugshot fit stay separate on cultural and opportunity cards.

Opportunity cards can start as owner hypotheses with no samples (example: `OPP-HUSS-NO-HUSS`, "Relax. No Huss."). Use original or rights-cleared audio (never ripped audio or cross-platform reuse of the trend sound), and aim the parody at the format, never at a creator.
