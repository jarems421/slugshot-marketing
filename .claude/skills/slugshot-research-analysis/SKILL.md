---
name: slugshot-research-analysis
description: Turn Slugshot research data into traceable, evidence-led findings. Use after or during collection when asked to analyse a bundle, check whether a meme/trend/sound is growing, find evidence for or against a marketing hypothesis, research creators' recurring content mechanisms, compare new and old observations, code content outcome-blind, verify academic sources, or prepare findings for ChatGPT. Works with slugshot-research-operations (collection) and the evidence ledger.
---

# Slugshot research analysis

`slugshot-research-operations` collects; this skill makes the collected material mean something. Do the work yourself: run commands, read the data, write the ledger, and report. ChatGPT leads cultural interpretation and creative strategy, but contribute your own findings, hypotheses and creative ideas too. Just label them by evidence level.

References:
- `docs/chatgpt-research-skills-v1.1.md`: ChatGPT's authoritative methodology (Research Evidence v1.1, Content & Culture Intelligence, Literature & Source Verification, codebook v1.1, current operating decisions). If this skill disagrees with it, provider policy or game truth, the stricter rule wins.
- `docs/research-evidence.md`: ledger, claim levels, statuses, strength, the six dimensions.
- `docs/research-methods.md`: method rules and provider boundaries.
- `research/schemas/evidence-ledger.schema.json`.
- Templates in `research/templates/`.

## Workflow

1. **Frame it.**
   - Write the decision and question. Pick the depth: quick scan, standard or consequential.
   - Name the unit separately: post, creator, meme/joke, sound, format, genre or concept. Each has its own ID and its own lifecycle; a saturated joke doesn't disprove its parent format.
   - Quick scans keep the research contract implicit. Standard and consequential work starts a ledger: `ss evidence new <ID> --question "..."`, then fill in `contract` (construct, what is NOT evidence, rivals, negative controls, sampling plan, stop rule).
2. **Collect what's missing** via slugshot-research-operations. Prefer evidence from an independent source family, ordinary and failed examples alongside featured ones, and a second comparable observation over more of the same.
3. **Intake before values.** Run `ss analyze intake [bundle]`, a QC report covering:
   - providers, scope, dates, expiry and sharing status;
   - missingness, rounded values and unknown metric definitions;
   - duplicate discovery contexts vs real observations;
   - sample roles, CSV/JSON copy agreement, and what each source cannot answer.

   Fix or note every issue.
4. **Compute deterministically** (never estimate by eye):
   - `ss analyze describe FILE METRIC [--by COL] [--where COL=VAL]`: n, missing, median, quartiles, range, top-item share.
   - `ss analyze repeat FILE`: same-item changes between comparable observations; negative revisions are flagged.
   - `ss analyze sensitivity FILE METRIC --by COL`: leave-one-creator-out, drop top 1%, ordinary-only, older than 48 h. "Fragile" means report it as fragile.
   - `ss analyze trend TERM`: heat, velocity, breadth, persistence, novelty, context fit and Slugshot fit kept separate, plus a rule-based lifecycle proposal. One snapshot means unknown.
   - `ss analyze changepoints [--entity ID]`: only on long regular daily series (Wikipedia). Check any change point against news context.
   - `ss analyze context wikidata TERM` for identity and aliases (EN/ES). `ss analyze context gdelt TERM` for news-volume context; GDELT allows about one call per 5 s.
5. **Qualitative coding** (hooks, jokes, formats), using codebook `config/research/codebooks/slugshot-creative.json` (v1.1, ten codes, multi-label; v1.0 is in `codebooks/archive/` for the first pilot's annotations):
   - `ss analyze blind-packet FILE` strips metrics, ranks, sample role and creator. (`ss analyze sample SPEC` writes one directly.)
   - `ss analyze coding-packet BLIND.jsonl --name N [--keys a,b] [--coder gemini|owner]` writes the instructions for Gemini or a person from the codebook. It always includes all ten codes, the five beats (opening, complication, attempt, reversal, payoff) and the access vocabulary. Never hand-write a packet with a subset of codes.
   - Code each item: `present`, `absent` (needs real playback), `uncertain` or `unreviewed`. Record the access level and exact-quote or timestamped evidence. If you saw the outcomes first, set `blinded: false`.
   - `ss analyze join-annotations FILE ANNOTATIONS.jsonl [--codebook archive/...]` validates and joins outcomes, giving prevalence by sample role with denominators. Codes left out count as unreviewed and are listed. A code that's as common in ordinary items as in featured ones does not distinguish success.
   - You may do first-pass coding yourself from accessible text/transcripts or pages you can open. Mark what you actually viewed, and send ambiguous or culturally loaded items to ChatGPT or the owner.
   - Gemini's playback coding is Gemini-reported. A second Gemini (or Claude) session is a repeat check, not independent verification. Independent verification means a person, coding before seeing the first coder's notes.
   - When the codebook version changes, recode explicitly. Never relabel old annotations with the new version.
   - Spanish content: creator-declared audio language (`declared_audio_language` in sample specs) is a screening proxy, not proof of speech. Keep an unknown-language path (`["es", "unknown"]`) and confirm with playback where possible.
6. **Write the ledger**:
   - one atomic claim per row, with level O/D/P/I/C/R;
   - evidence items with the exact file, row selector and value, or source path and exact quote;
   - source family, scope, sample role, expiry;
   - support status and strength set separately; the six dimensions in words; rivals, counterevidence and the next discriminating test.

   Then run `ss evidence validate <ID> --bundle <dir> --fix-summary`. Fix every ERROR. For each REVIEW item, re-read the claim against its evidence (scope, period, population, role) and set `review.ai_reviewed: true` with a note. The deterministic checks catch shape, not meaning; your review is required.
7. **Decide usefully.** Fill `decision_memo`:
   - supported findings by claim ID;
   - uncertain-but-useful items;
   - the strongest counterevidence and what we don't know;
   - a creative hypothesis ("if [mechanism], then [Slugshot concept] should improve [our metric] because...");
   - the cheapest test.

   Suggestive evidence can justify a cheap 15-second test. It never justifies "this causes virality". Then `ss evidence card <ID>`, and `ss research bundle` (ledgers, cards and trend outputs travel in the zip).

## Natural-language requests → actions

| Request | Do |
|---|---|
| "Analyse our latest research bundle" | intake, then describe/repeat where meaningful, then a short ledger of what the data does and doesn't support |
| "Is this meme still growing?" | `trend TERM`; if only one snapshot, collect a comparable second one (cc-session / yt / trends rss) and say lifecycle is unknown until then; check breadth across creators |
| "Find evidence for and against this hypothesis" | ledger with the hypothesis and rivals; collect supporting AND contradicting evidence (negative controls, ordinary examples); hypothesis-generation skill for the prediction/rival matrix |
| "Research these creators' recurring mechanisms" | `yt creators` (uploads incl. ordinary) or observations → blind-packet → coding → join → prevalence vs ordinary |
| "Compare latest with previous observations" | `repeat` per file; only same item, same scope |
| "Find academic research on X and verify it" | surveying-literature skill (OpenAlex/Crossref/Semantic Scholar/arXiv/dblp); open the actual paper; quote the passage into a local text file and cite it with source_path + quote; verifying-bibliography for reference lists; synthesis-fact-checking for claims in articles or drafts |
| "Execute this ChatGPT brief" | operations skill for collection, then this workflow; return bundle + ledger |

Check the [methodology](../../../docs/research-methods.md) and [provider rules](../../../docs/research-data.md) before issuing a decision memo.
