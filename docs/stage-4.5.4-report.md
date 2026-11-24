# Stage 4.5.4 configuration and first Stage 4.5.5 pilot (24 Nov 2026)

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

## 2. Pilot: BRIEF-20261124-RULE-WORLD-PILOT

| Step | Result |
|---|---|
| Searches | 28 positive + 4 control = 32 (cap respected). Day total 47 search calls and about 290 units of 3,000 |
| Sample | 20 of 20 (deterministic spec `research/pilots/BRIEF-20261124-RULE-WORLD-PILOT.sample.json`): 3 short clips per branch (en, es-MX, es-ES, es-LATAM), 2 ordinary watchlist uploads per language, 2 adjacent control items per language |
| Coding | Codebook v1.0, outcome-blind (blinded: true), **caption_only**: titles and tags only. Claude can't play YouTube videos (downloading breaks YouTube's terms; captions need owner rights). So no `absent` codes, and GAMEPLAY_PROOF and AUDIO_CUE are unreviewed. The 4-item pilot found one ambiguity: "In My World..." can be a series label rather than a rule that sets stakes. Proposal: add a RULE_WORLD note "series label without a stated stake = uncertain" in codebook v1.1 (not changed locally) |
| Playback coding | `analysis/gemini_packet_BRIEF-20261124-RULE-WORLD-PILOT.md`: 20 URLs + codebook + JSONL format for Gemini. When Gemini's annotations come back, Claude validates and joins them (`ss analyze join-annotations`) |

### Findings (all exploratory, ledger IDs)

- **C1.** Titles state an explicit fictional rule in **8 of 12** retrieved clips. Rival explanation: the clips were found with rule-world queries (the query echoes itself), and the ordinary uploads couldn't be coded from titles. So this is not prevalence (**C2**).
- **C3.** **regionCode barely changes results** for the same query:
  - GB vs US: identical 15/15, 15/15 and 7/7, and 14/16 on the fourth query;
  - AR / CO / CL: 11/12 and 12/15.
  - Market branches that repeat one query on several regions mostly duplicate searches.
- **C4.** The four branches retrieved **disjoint** video sets (0 shared videos between any pair).
- **C5.** Spanish-branch rows mostly **declare English audio**: es-ES 20/31, es-LATAM 31/41, es-MX 11/21. These are declarations, not verified speech.
- **C6.** **13 of 20 Spanish searches returned 0 or 1 videos.** Long native phrases ("se confió y perdió roblox", "iba de sobrado y perdió roblox") returned none in the 7-day Shorts window. Broader core terms ("noob contra pro roblox", "historias de roblox con reglas") returned full pages.
- **C7.** The primary hypothesis (rule + status reversal → readable payoff) is **indeterminate** until playback coding is done.
- **C8 (recommendation).** Prototype one original 15-second rule-world skit, EN and ES:
  - rule card "In my world, everyone gets one slug for life", then a Floppy underdog duel won with real gameplay (no transformation);
  - against a plain challenge opener on the same footage.
- **C9 (recommendation).** Revise the Spanish families.

## 3. Recommended changes to the configuration (ChatGPT)

1. **Spanish families:** replace long phrase queries with short core terms plus community vocabulary. Consider widening Spanish `days` to 14 for low-volume constructs.
2. **Markets:** run one market per identical query (e.g. US only for en, AR only for es-LATAM) and rotate the market between runs. Spend the saved searches on more wording variants. Region differences come from wording, not regionCode.
3. **Language check:** treat a Spanish-branch result as Spanish content only if its declared audio is es, or after playback confirms it. Claude can filter on `default_audio_language` in sampling.
4. **Codebook v1.1:** clarify RULE_WORLD for series-label titles; consider adding a code for streamer reaction (seen in ordinary items).
5. **Next validation steps:**
   - Gemini playback coding of the 20 items;
   - a second like-for-like observation of the same families in 3–7 days (for any lifecycle reading);
   - a real Creative Center paste and a real Trends Explore CSV (both still unvalidated).

## 4. New commands (added for this stage)

| Command | Does |
|---|---|
| `ss research verify-watchlists` | official-API identity, activity and declared-language checks; fills blanks only from declared metadata; flags conflicts; writes a local report |
| `ss research discover-creators --from-collection PREFIX --stratum S --lang en/es` | systematic small/medium watchlist expansion from collected results (no extra searches) |
| `ss analyze sample SPEC.json` | deterministic outcome-blind sample + blind packet |
| Quota fix | live YouTube calls from any data folder now log to one central quota log (test runs earlier today had been invisible to the budget check; backfilled) |

Nothing was published, nothing was spent, and the game repo was not touched.
