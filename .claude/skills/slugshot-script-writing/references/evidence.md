# Evidence behind the script rules (26 Nov 2026)

Source: 631 TikTok In My World / In This Town posts (Apify, one snapshot on 26 Nov 2026). Tiers are 50 posts each: TOP 545k–19.9M views, MID 15.2k–151k, FLOP 196–7.6k. All tier posts are Roblox-tagged, English, at least 5 days old, with at most 4 per creator. Ledger: `data/local/research/evidence/IMW-GEMINI-VERIFY.json`.

## Objective measures (our recomputation; Gemini's figures matched)

| Measure | TOP / MID / FLOP |
|---|---|
| Median like rate | 10.2% / 5.0% / 3.8% |
| Median share rate | 0.70% / 0.28% / 0.14% |
| Median non-zero followers | 34,300 / 13,100 / 2,931 (account size explains much of the gap) |
| Median views per follower | 40.8x / 4.5x / 1.0x |
| Words per minute | 218 / 221 / 231 (a genre convention: pace doesn't separate tiers) |
| Median length | 109 / 120 / 114 s |
| Rule line in first 10 s | 45 / 46 / 46 of 50 (a genre convention, not an advantage) |
| Caption states the premise | 43 / 34 / 32 of 50 |
| Copies an earlier post (>=90% text match) | 0 / 3 / 6 |
| Spoken "subscribe" | 0 / 1 / 6 |
| 5–7 days old (age confound) | 30% / 8% / 14% |

## Interpretive codes: Gemini (could see tiers) vs two blind coders

| Code | ChatGPT blind | Claude blind | Gemini |
|---|---|---|---|
| Novelty 4–5 | 26 / 20 / 19 | 29 / 23 / 20 | 45 / 27 / 23 |
| Any humour | 40 / 33 / 32 | 31 / 27 / 23 | 30 / 25 / 17 |
| Generic fantasy | 6 / 8 / 13 | 3 / 13 / 14 (p=0.006) | 0 / 7 / 12 |
| Generic AI prose | 1 / 8 / 11 (p=0.004) | 7 / 10 / 12 | 3 / 10 / 11 |
| Power/rank premise | 1 / 2 / 7 | 1 / 1 / 5 | 2 / 6 / 11 |
| Flat/abrupt ending | 1 / 5 / 2 | 3 / 8 / 7 | 0 / 6 / 11 |
| Dry deadpan humour | 15 / 5 / 8 | 17 / 15 / 15 | 10 / 6 / 1 |

The blind coders agree moderately with each other (kappa 0.43–0.74; novelty within 1 point on 145/150). Read: Gemini's interpretive gaps were inflated by about 2x. Generic fantasy and AI prose survive. Novelty and humour lean the right way, modestly. Flat endings and deadpan humour don't replicate as dividers.

## Narration and sound (measured on the 50 TOP videos)

- **Pace:** median 215 wpm; our V06 narrator ran at about 100 wpm with 0.6–0.8 s gaps (the "bland" problem).
- **Music bed:** about 8 dB under the voice (middle half 6–10 dB), around 112 BPM, continuous.
- **Stingers:** sudden hits average about 0.6 per minute, so they're accents, not a stream.
- **Narrator gender:** couldn't be measured (music masks the fingerprint). Almost all TOP narrators sit in the male pitch range, so a female narrator would be a point of difference to test.

## Limits

One snapshot; account size and post age confound the tiers; transcripts are automatic speech recognition with no visuals; retention isn't observable; copy detection only sees our 631 posts.
