# Stage 4.5.3 handoff to ChatGPT

> **Historical (Stage 4.5.3).** Superseded where it differs by [chatgpt-research-skills-v1.1.md](chatgpt-research-skills-v1.1.md) and [stage-4.5.4-report.md](stage-4.5.4-report.md): the codebook is now v1.1 (v1.0 archived), query families are families-1.1, and the test query sets have been replaced.

This is for ChatGPT's three research skills (Research Evidence, Content & Culture Intelligence, Literature & Source Verification). It describes what Claude actually implemented and tested on 24 Nov 2026, and how to work with it. Detail lives in the linked docs, which are all in the Claude toolkit pack.

## 1. Division of work (unchanged)

Claude:
- collects, validates, computes and bundles;
- does first-pass analysis and coding;
- writes and checks evidence ledgers.

ChatGPT:
- designs research, query families and watchlists;
- interprets culture;
- synthesises across bundles;
- leads creative strategy.

Owner: decisions, approvals, and the Creative Center copy (Ctrl+A, Ctrl+C).

## 2. What Claude can now do from one instruction

| Instruction (examples) | What happens |
|---|---|
| "Collect today's research" / "Research Spanish Roblox content" | collector profiles → bundle with an intake QC report |
| "Analyse our latest bundle" | intake → statistics with denominators → a short ledger of what the data supports and doesn't |
| "Is this meme still growing?" | trend dimensions kept separate, plus a lifecycle proposal (unknown without repeated comparable observations); collects a second observation if needed |
| "Find evidence for and against this hypothesis" | ledger with hypothesis, rivals and negative controls; supporting and contradicting evidence; prediction/rival matrix (hypothesis-generation skill) |
| "Research these creators' recurring mechanisms" | uploads including ordinary ones → outcome-blind packet → coding with your codebook v1.0 → prevalence by featured / ordinary / failed |
| "Compare latest with previous observations" | same-item, same-scope changes only; negative revisions flagged |
| "Find academic research on X and verify it" | surveying-literature + verifying-bibliography (installed, live-tested); passages saved and quoted exactly; synthesis-fact-checking for claims in drafts |
| "Execute this research brief" | brief → config → collection → analysis → bundle + ledger + decision memo |

## 3. Bundle format (`exports/share/bundles/slugshot_research_<UTC>.zip`)

| File | Contents |
|---|---|
| `INTAKE.md` / `INTAKE.json` | **Read first.** Per dataset: provider, rows, provenance, expiry, dictionary and CSV/JSON agreement, missingness per column, rounded values, unknown metric definitions, sample roles, duplicate discovery contexts vs observations, category mismatches, scope values, what the source **cannot answer**; plus issues |
| `BUNDLE_SUMMARY.md` | collection steps, runs, files, caveats |
| `DATA_DICTIONARY.md`, `MANIFEST.csv` | every column; expiry and sharing status per file |
| `<kind>_<UTC>.csv` / `.json` / `_README.md` | data (YouTube report/history/comments, Wikipedia page views + coverage, Trending Now, Explore imports, Roblox, public observations). Twitch stays local |
| `evidence/<ID>.json` / `.md` / `.evidenceguard.json` | ledgers, claim cards, EvidenceGuard-format audit |
| `analysis/trend_<term>.json` | trend dimension tables |

## 4. Evidence ledger: use these exact names

The schema is `research/schemas/evidence-ledger.schema.json`; the full guide is `docs/research-evidence.md`.

**Claims:**
- `level`: O, D, P, I, C or R.
- `support_status`: supported, partially_supported, unsupported, indeterminate.
- `strength`: exploratory, suggestive, supported_descriptive, convergent, experimental.
- `dimensions`: directness, coverage, temporal, independence, robustness, counterevidence, each {rating: strong | adequate | weak | none | unknown, note}.

**Evidence:**
- `source_family`: youtube, tiktok, instagram, twitch, roblox, google_search, wikimedia, news, literature, owned_experiment, qualitative_review, community_reference, other.
- `actual_role`: EvidenceGuard roles plus platform_metric, third_party_estimate, normalised_index, qualitative_coding, experiment_result, literature_finding, search_record.
- `provenance`: P1–P4.
- `locator` takes one of two forms:
  - a bundle row: `file` + `where{col: value}` + `column` + `value`. Claude checks it against the CSV; a newer re-export of the same kind is accepted and noted.
  - an exact passage: `source_path` + `quote`, checked word for word.
- `item`, `metric`, `observed_at`, `scope{}`, `series_points` let the validator see repeated comparable observations.

**Rules worth knowing:**
- `unsupported` means the cited evidence fails to justify the claim, or contradicts it. Overclaims recorded as unsupported or indeterminate are valid audit entries, not errors.
- Lifecycle words need two comparable observations or a dated series.
- Audience words can't rest on retrieval scope.
- "Convergent" needs two source families.
- Causal wording outside level C is an error.

Validator output has three tiers:
- ERROR: must fix;
- WARN: weakness to note;
- REVIEW: a judgement for an AI or person; set `review.ai_reviewed: true` after checking.

## 5. Analysis capabilities

All in `ss analyze`; methods in `docs/research-methods.md`.

| Capability | What it does |
|---|---|
| intake | QC of a bundle |
| describe | n, missing, median, quartiles, range, top-item share; refuses YouTube aggregation across channels |
| repeat | same-item changes; per-hour rates; negative revisions flagged |
| sensitivity | leave-one-creator-out, drop top 1%, ordinary-only, older than 48 h → robust or fragile |
| trend | heat, velocity, breadth, persistence, novelty, context fit, Slugshot fit, plus lifecycle proposal and rules |
| changepoints | ruptures PELT on long daily Wikipedia series |
| blind-packet, join-annotations | outcome-blind coding with codebook v1.0 (multi-label present/absent/uncertain/unreviewed, access levels, `blinded` flag, exact-quote evidence) |
| context wikidata | entity identity and EN/ES aliases |
| context gdelt | news-volume context for spikes; GDELT throttles to about 1 call per 5 s |

## 6. Recommended changes to ChatGPT's skills (from implementing them)

1. **Change points.** The guide says "deferred until enough history". We have it: 11 years of daily Wikipedia views. `changepoints` runs only on series of 28 days or more; keep "check news context first".
   - Example: es.wikipedia Slugterra fell from a median of 41 to 26 daily views at 25 Sep 2026 (one family, suggestive).
2. **Installed tools.** The Literature skill says "no claim of installed upstream tools unless confirmed". It's now confirmed: verifying-bibliography and surveying-literature (claude-skills-research 9d990c1, MIT, project-local) pass their offline tests. A live check verified the three DOIs in your reports and flagged a fabricated reference UNVERIFIED.
3. **Unsupported vs indeterminate.** Your v1.1 definition is adopted exactly in the validator.
4. **Codebook v1.0 is the local codebook** (`config/research/codebooks/slugshot-creative.json`). Bump `version` when you revise it; annotations must quote it.
5. **Extra tools you can ask Claude to use:**
   - **synthesis-fact-checking** (CC0): checking marketing copy or articles before publication.
   - **hypothesis-generation** (K-Dense, MIT): prediction/rival matrices, falsification controls, preregistration scaffolds for our own experiments.
6. **Ledger contents.** Put numbers you use in `values{}` or `analysis_spec`, so the traceability check passes.
7. **Evidence expiry.** Ledgers citing YouTube or Twitch data inherit the expiry. Keep durable lessons qualitative in the Marketing Bank; re-run collection rather than reusing old numbers.

## 7. Stage 4.5.4 starter structures (filled in by ChatGPT)

| What | File | Contents now |
|---|---|---|
| Query families | `config/research/query_families.json` | Per family: construct, etic core, layers (core, alias, slang, format_phrase, need_language, community_vocabulary, negative, adjacent_culture), native branches (en, es-MX, es-ES, es-LATAM) with markets and lang, negative_controls, collection settings. One starter family (underdog comedy). `ss research families --compile` writes YouTube saved sets `fam-<id>[-<branch>|-negative]` and warns when a Spanish branch just copies English |
| Creator watchlist | `config/research/youtube_creators.csv` | `channel_id, label, language_stream, market, stratum, size_band, selection_reason, notes` (strata e.g. roblox-shortform, roblox-longform, gaming-entertainment, meme-comedy, animation-story, anime-manga, es-gaming, slugterra-fandom; include mid-size and ordinary creators) |
| Broadcaster watchlist | `config/research/twitch_broadcasters.csv` | same columns with `login` |
| Wikipedia topics | `config/research/wiki_entities.csv` | use `ss analyze context wikidata` for aliases; list redirect spellings explicitly |
| Briefs | `research/templates/research-brief.md` | |
| Decision memo | `research/templates/decision-memo.md` | |
| Literature search log | `research/templates/prisma-lite-search-log.csv` | |

## 8. Known limits

- **Creative Center:** a person reads the page. We have permission to use Apify for the toolkit's TikTok collection. [Current collection guide](research-data.md#7-tiktok-findings-2026-11-24)
- **Google Trends Explore import:** tested on sample files only.
- **TikTok Discovery API:** not available (companies only).
- **Competitors' metrics:** no retention or audience geography from any source. Slugshot has no own-channel results yet, so nothing is "experimental" strength.
- **GDELT:** rate-limits aggressively; one call per 5 s, retried automatically.
