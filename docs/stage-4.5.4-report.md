# Stage 4.5.4 configuration and Stage 4.5.5 pilot validation (24 Nov 2026)

For ChatGPT. This covers what was applied from the seed package, what was verified, what the first real brief found, and what to change next. The bundle is `exports/share/bundles/slugshot_research_20261124T2138Z.zip`; the ledger is `evidence/BRIEF-20261124-RULE-WORLD-PILOT.json`.

## 1. Configuration applied

| Item | Result |
|---|---|
| `query_families.json` | Replaced with seed v1.0: 11 families × (14 positive + 2 control). Compiled into `fam-<id>[-<branch>|-negative]` saved sets. 0 validation warnings |
| `youtube_queries.json` | Seed `daily` (8) and `spanish` (12) sets merged; `test` set and compiled family sets preserved |
| YouTube creators | 11 seed + 12 systematic + 7 resolved candidates = **30**, all verified via the API |
| Twitch broadcasters | 7, all found; language settings match (local only) |
| Wikipedia entities | 23 titles; 20 resolved, and 3 lookups rate-limited by Wikimedia (they retry automatically on the next pull) |
| Backup of previous config | `data/local/research/config_backup_pre_4.5.4/` |

### Verification details (`ss research verify-watchlists`)

- **Seed creators:** all 11 are active. The configured size bands all match the observed bands; subscriber numbers are never stored, only the coarse band.
- **Declared metadata:** declared channel countries filled blank `market` fields (creator context, not audience). MiAnimation's language was set to en from its uploads' declared audio language.
- **Mixed declarations:** Llanas Roblox declares en 3 / es 1, while the seed listed it as ES animation. Language left blank and flagged to check.
- **Inactive in the last 30 days:** Dramas de Roblox, and the official **Slugterra España – WildBrain** channel (resolved from the Marketing Bank video). Kept, and flagged.
- **Candidates resolved by handle:** Chocoblox (ES, large), Zuu (PE, large), Sofia roblox (ES, medium), Terio Roblox Español (medium), Dramas de Roblox. Each candidate's language comes from its declared audio language.
- **Systematic additions (`ss research discover-creators`):**
  - *Method:* the first eligible distinct channels, newest first, from the collected search results. Eligible means small or medium, and the declared language matches. Reach never ordered the selection.
  - *Picks*, two per stratum per language:
    - roblox-combat: Racinggamer83-s3r, OddBlox (en); GASTER_PA, UnPoco DeTodo (es)
    - roblox-narrative: Riot1f, Plotpop (en); Bloxalux, CuboCuentos (es)
    - gaming-entertainment: Itz SBG, Maelys (en); NoobLandia, Trenzas Roblox (es)
  - *Note:* 15 of 19 channels retrieved by the Spanish underdog searches did not declare Spanish audio.
- **Not added:** the TikTok leads (zaylento.yt, synelite1, wayne.blox). There's no TikTok collector; use Creative Center and observations.
- **Wikipedia:** es "Beyblade" resolves to *Beyblade (manga)*, a different entity from the English franchise article. Don't treat the two as one topic.


## 2. Stage 4.5.5 validation: BRIEF-20261124-RULE-WORLD-PILOT

| Step | Result |
|---|---|
| Searches | 28 positive + 4 control = 32 (cap respected). Revision yield check afterwards: 12 more. Day total: 59 search calls, about 445 units |
| Sample | 20 of 20 from the deterministic spec `research/pilots/BRIEF-20261124-RULE-WORLD-PILOT.sample.json`: 3 short clips per branch (en, es-MX, es-ES, es-LATAM), 2 ordinary watchlist uploads per language, 2 adjacent control items per language |
| First pass | Claude, codebook 1.0, outcome-blind, **caption_only** (titles and tags) |
| Playback coding | Gemini, **full_playback** for all 20, **blinded: false**: Gemini's YouTube tool returned view and like counts with the video. Gemini's packet had 7 of the 10 codebook codes; CHOICE, CHARACTER_GAG and REACTION are recorded as unreviewed. The coding is **Gemini-reported and pending an independent spot-check** |
| Validation | 20 of 20 annotations validated and joined with the sample (`ss analyze join-annotations`, codebook 1.0): 0 errors. Counts only, because YouTube rules forbid statistics across channels |
| Plausibility | The latest timestamp Gemini cites fits each video's API duration in 19 of 20 items. The one flag is a false positive ("4:00" is story time). This is a metadata check, not independent viewing |

### Findings (exploratory; ledger claim IDs; recomputed from the annotations, not from Gemini's summary)

- **C7. RULE_WORLD:** present in **10 of 12** retrieved clips, 0 of 4 ordinary uploads and 0 of 4 adjacent controls. Gemini's prose summary said nine; the annotations say ten. The clips were found with rule-world queries, so this measures retrieval, not prevalence.
- **C8. What rule-world clips combine with** (10 clips):
  - CURIOSITY_DELAY 10 and AUDIO_CUE 10;
  - FRIEND_RIVAL 3;
  - STATUS_REVERSAL 2;
  - GAMEPLAY_PROOF 0.
  - AUDIO_CUE is present in 17 of 20 items overall, so it may be coded generously.
- **C9. GAMEPLAY_PROOF:** present in 6 of 20 items, none of them rule-world clips: 2 of 4 ordinary uploads and all 4 adjacent controls. The retrieved clips are narrated machinima or animation.
- **C10. Title-only vs playback:** 7 of the 8 title-present RULE_WORLD codes held on playback. One reversed: fZvg6KA5mxg, a one-off "don't open the door" horror premise. The 3 title-uncertain clips were present on playback.
- **C11. Spoken language:** Gemini heard Spanish in only **3 of 9** Spanish-branch clips. In all 17 items where it heard speech, the heard language matched the creator-declared audio language. This supports filtering on declared language (exploratory).
- **C12–C13. Revised Spanish queries:**
  - Low-yield searches (0–1 videos) fell from 13 of 20 to **1 of 12**; only "se creía pro roblox" still returned 0. The window also widened from 7 to 14 days, so wording and window are confounded.
  - English-declared rows fell for es-MX (15/53, pilot 11/21) and es-ES (23/48, pilot 20/31) but not for es-LATAM (34/45, pilot 31/41).
  - Loanword queries ("noob vs pro roblox", "noob contra pro roblox") return about 13 of 15 English-declared rows each.
- **C14. Rule plus reversal:** the two rarely co-occur (2 of 10). In this sample, rule-world clips pay off through a held-back reveal or a reframing of the rule. Whether combining a rule with a reversal reads better is untested.
- **No performance claim.** Nothing here says that any mechanism improves retention, reach or performance. No outcome comparison was made.

### Decision memo

- **Prototype (C15):** one original 15-second rule-world skit in EN and ES.
  - Rule card: "In my world, everyone gets one slug for life", labelled as fiction (SKIT preset).
  - A held-back reveal, then a Floppy underdog duel shown with real gameplay.
- **Alternative:** the same duel framed as an original noob/pro/expert tier skit (status reversal, no rule).
- **Test:** same footage and payoff, two openers, one language at a time, on our own channel. Compare engaged views and average view percentage at 48 h.
- **This is an untested hybrid:** rule-world and gameplay proof never co-occurred in the sample.
- **Game checks:**
  - 1v1 PvP is CAPTURE status, so film a real two-player Cinder Rift round first.
  - Floppy never transforms and has no abilities.
  - "Underdog" is framing, not a game rule.

## 3. Changes applied (proportional; no new infrastructure)

| Change | Where |
|---|---|
| Families v1.1: `market_mode: rotate` runs each query in one of its branch's markets and moves on each ISO week. Each family compiles to 10 searches, down from 16; wording coverage is unchanged | `config/research/query_families.json`, `scripts/research_admin.py` |
| 7 low-yield Spanish queries replaced with short core terms or community vocabulary in rule-world and underdog-comedy. The old phrases are kept under `retired_queries` with their yields | `config/research/query_families.json` |
| A 14-day window for those Spanish branches (per-branch `days`) | same |
| Optional `declared_audio_language` filter for sample groups, so English-declared rows aren't counted as Spanish content | `scripts/research_analysis.py` (`ss analyze sample`) |
| Codebook 1.1: RULE_WORLD now needs a rule that governs the world and sets stakes. A series label with no stated stake is **uncertain**; a one-off prohibition with no world-wide rule is **absent**. 1.0 is archived for validating annotations coded under it | `config/research/codebooks/` |
| Fix: the analysis tools now treat derived YouTube files (samples, joins) as YouTube data. Before this fix, the first association file contained a median outcome across items from different channels, which the policy forbids. It's now regenerated with counts only, and a regression test was added | `scripts/research_analysis.py`, `tests/test_analysis.py` |

Other families keep their original queries; they're unvalidated until their own pilot.

## 4. Limitations

- Single AI coder, unblinded, n=20; no independent spot-check yet.
- Query echo: the retrieved clips were found with rule-world queries. The ordinary and adjacent groups have only 4 items each.
- The pilot was coded under codebook 1.0 and hasn't been recoded under 1.1. The clarification would change at most items like fZvg6KA5mxg, which Gemini already coded absent.
- The revised yields changed wording and window together.
- Declared language is the creator's label.
- One day of data, two families. YouTube data expires 2026-12-24.

## 5. Remaining blockers and next steps

1. **Spot-check:** a person should check at least 4 items against playback: fZvg6KA5mxg (the coder disagreement), 5HMhXQP_W5A, 8fTU72rRJmY and tLY7uB6Gnas. A second Gemini or Claude session would only be a repeat check, not independent verification. Claude can't play YouTube videos. The packet is `analysis/coding_packet_BRIEF-20261124-RULE-WORLD-PILOT.spotcheck.md`.
2. **Missing codes:** code CHOICE, CHARACTER_GAG and REACTION, which weren't in Gemini's packet, and recode under codebook 1.1 in the same pass. The packet is `analysis/coding_packet_BRIEF-20261124-RULE-WORLD-PILOT.recode-1.1.md`, with all ten codes; it's a repeat check by the same model.
3. **Capture:** film a real two-player 1v1 round before producing the prototype.
4. **Separate wording from window:** re-run the revised Spanish branches on a 7-day window, and replace "se creía pro roblox".
5. **Next sample:** set `declared_audio_language: ["es", "unknown"]` on the Spanish groups. Declared language is a screening proxy, so keep the unknown-language path.
6. **Still unvalidated:** a real TikTok Creative Center paste and a real Google Trends CSV.

## 6. Commands added in Stage 4.5.4

| Command | Does |
|---|---|
| `ss research verify-watchlists` | official-API identity, activity and declared-language checks; fills blanks only from declared metadata; flags conflicts; writes a local report |
| `ss research discover-creators --from-collection PREFIX --stratum S --lang en/es` | systematic small/medium watchlist additions from collected results (no extra searches) |
| `ss analyze sample SPEC.json` | deterministic outcome-blind sample plus blind packet; groups accept `declared_audio_language` |
| Quota fix | live YouTube calls from any data folder log to one central quota log |

Nothing was published, nothing was spent, and the game repo was not touched.
