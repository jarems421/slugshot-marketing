# Research methods (synced with ChatGPT research skills v1.1, 24 Nov 2026)

These are the working rules that sit between collection (`slugshot-research-operations`) and decisions (`slugshot-research-analysis`, ChatGPT's research skills). They are condensed from ChatGPT's Research Evidence v1.1, Content & Culture Intelligence and Literature & Source Verification skills (local copy: [chatgpt-research-skills-v1.1.md](chatgpt-research-skills-v1.1.md)), and they match those skills. Where they differ, the stricter rule wins. The aim is to prevent false certainty, not to slow down cheap experiments.

## 1. Start from the decision

A research contract has these parts:
- decision → question → construct (what we actually care about);
- unit (post, creator, meme/joke, sound, format, genre, concept);
- observable measures, and what does NOT answer the question;
- a bounded sample and how items entered it;
- rival hypotheses and negative controls;
- valid comparisons;
- a stop rule and an action threshold.

Choose a depth:
- **Quick scan:** the contract is implicit; give the answer, the strongest evidence, a caveat and the next step.
- **Standard:** write the contract into a ledger.
- **Consequential:** freeze comparisons before seeing outcomes and keep a search log.

Post-hoc discoveries are exploratory until they are seen again.

## 2. Inference ladder

**O** observation → **D** derived statistic → **P** descriptive pattern → **I** interpretation → **C** causal claim → **R** recommendation.

- Each step up needs evidence the step below doesn't provide.
- Causal claims come from Slugshot's own controlled tests, or from a design with stated assumptions.
- **R does not require C:** a cheap 15-second test can proceed on suggestive evidence.

## 3. Independence = data-generating process

Count confirmations by **source family**, not by number of pages or tools.
- YouTube API views and a vidIQ screen showing the same views are one family.
- Five articles repeating one announcement are one origin.
- Google search interest and Wikipedia page views are more independent (different behaviours), though one outside event can move both. Check news context (`ss analyze context gdelt`).
- This follows the source-independence graph in synthesis-fact-checking (CC0, installed) and the triangulation literature (Lawlor, Tilling & Davey Smith 2016, doi:10.1093/ije/dyw314): agreement means most when the methods have different biases.

## 4. Sampling and selection

Platform feeds, search results and charts are selected by algorithms, so they are not random samples.
- Record why each item was visible: search, chart, watchlist, recommendation, chosen competitor, successful exemplar, ordinary, failed, counterexample.
- Include ordinary and weak or failed examples. Featured examples must never become the denominator for claims about normal content.
- Build queries for both precision and recall, in layers: core terms → aliases → native slang → format phrases → need language → community vocabulary → negative terms → adjacent culture (`config/research/query_families.json`).
- Don't use inferential statistics to make population claims from convenience samples. A standard error doesn't fix an unknown selection mechanism. (The Digital Behavioral Data guides from GESIS cover this; they are CC BY-NC, so they're referenced, not copied.)

## 5. Quantitative analysis

**Default tools:**
- counts with explicit denominators;
- medians, quartiles and ranges for heavy-tailed metrics;
- missingness;
- same-item changes over actual elapsed time;
- sensitivity checks: leave one creator out, drop the top 1%, ordinary-only, an alternative window, an alternative query.

If a reasonable alternative specification flips the result, report it as **fragile** rather than picking the version we like. This follows specification-curve logic (Simonsohn, Simmons & Nelson 2020, doi:10.1038/s41562-020-0912-z).

**Not allowed:**
- rounded counts treated as exact;
- negative revisions read as negative demand;
- overlapping windows summed;
- separately normalised Google Trends downloads spliced together;
- YouTube aggregation across channels;
- composite scores of any kind.

**Change points** (`ruptures`) are only for long, regular, comparable series. Today that means Wikipedia daily page views (11 years). Check each change point against news context before interpreting it.

**Own experiments:**
- one main change;
- a predefined metric, window and comparator;
- randomise or block where feasible;
- record effort, confounds and null results;
- report uncertainty intervals, not "significant / not significant" (ASA statement on p-values).

## 6. Trends and culture

Keep these separate:
- **heat:** displayed intensity;
- **velocity:** comparable changes;
- **breadth:** distinct creators and communities;
- **persistence:** repeated windows;
- **novelty and context:** reuse vs new meaning;
- **Slugshot fit:** a separate judgement.

Lifecycle labels:

| Label | Requires |
|---|---|
| emerging | repeated comparable observations of rising adoption, still with limited breadth |
| accelerating | rising across repeated comparable observations, and in breadth |
| established | sustained, broad use without evidence of acceleration |
| saturated | high volume AND evidence of falling novelty |
| declining | repeated comparable falls, not one old post slowing |
| unknown | the default; **one snapshot is always unknown** |

- A specific joke, its sound, its story format and its genre are different entities. (Huss ≠ the Huss sound ≠ In This Town ≠ Roblox animation.)
- Heat and confidence are different things: "high heat, low confidence" is a normal result.

## 7. Qualitative coding

- Use the codebook in `config/research/codebooks/slugshot-creative.json` (v1.1, ten codes): multi-label, with states present / absent / uncertain / unreviewed. v1.0 is archived in `codebooks/archive/`, and only for annotations coded under it.
- RULE_WORLD (v1.1) needs a rule that governs the story world and sets stakes for a character. A series label without a stated rule or stake is uncertain. A one-off warning without a world-wide rule, or a game tutorial, is absent.
- Pilot the codebook, then freeze its version. When the version changes, recode explicitly; never relabel old annotations.
- Code outcome-blind where practical (`ss analyze blind-packet` hides metrics, ranks, sample role and creator).
- Packets for Gemini or a person come from `ss analyze coding-packet`. They carry all ten codes, all five beats (opening, complication, attempt, reversal, payoff) and the access vocabulary.
- Record the access level actually used: full_playback, excerpt, caption_only, provider_description or inaccessible. "Absent" needs real playback.
- Join outcomes only after freezing, and compare how common each code is in featured vs ordinary items (`ss analyze join-annotations`). Codes left out count as unreviewed.
- One model coding twice, or a second session of the same model, is a repeat check, not two independent coders. Independent verification means a person coding before seeing the first coder's notes. Send ambiguous or culturally loaded items to a person.

This method is adapted from Social Research Agent Kit (MIT), as described in `research/upstream/PROVENANCE.md`.

## 8. English and Spanish

- Keep a shared **etic** core: underdog, status reversal, creature choice, friend/rival, gameplay proof.
- Write **emic** branches natively for en, es-MX, es-ES and es-LATAM. Don't translate query lists.
- Keep these separate:
  - retrieval parameters (region_param, relevance_language_param);
  - creator-declared language;
  - broadcaster language setting;
  - Wikipedia edition;
  - creator location;
  - search geography;
  - audience geography (only our own analytics, after launch).
- Creator-declared audio language is a screening proxy, not proof of speech. When a sample filters on it, keep an unknown-language path, and confirm with playback where possible.
- Retrieval country (`region_param`) barely changed results in the 24 Nov pilot. Families-1.1 run each query in one rotating country, and vary wording instead.
- Never infer ethnicity or nationality from language.

## 9. Literature and source verification

The order of checks is: identity → metadata → claim-to-passage → study design → truth. The tools:
- **surveying-literature** for discovery;
- **verifying-bibliography** for checking a reference list (OpenAlex, Crossref, Semantic Scholar, dblp, arXiv; both installed project-locally);
- **synthesis-fact-checking** for claims in drafts and articles.

Metadata checks prove a paper exists, not that it says what we claim. Open the paper, save the passage, and cite it with `source_path` + `quote` so the validator can check it word for word. For substantial searches, keep a PRISMA-lite log (`research/templates/prisma-lite-search-log.csv`, after PRISMA-S doi:10.1186/s13643-020-01542-z).

## 10. Provider boundaries (short form; full detail in research-data.md)

| Provider | Boundary |
|---|---|
| YouTube | per-video history only, no cross-channel aggregation or scores, 30-day expiry for data and derived artefacts; region and language parameters are retrieval context |
| Google Trends | indices are relative within one download; Trending Now covers all topics with approximate bands |
| Wikimedia | edition ≠ country; views ≠ people or fans |
| Creative Center | displayed and rounded figures with unknown definitions; manual or guided clipboard only |
| Twitch | local only |
| Roblox | counters ≠ acquisition |
| vidIQ | P3; no credits without a budget |
