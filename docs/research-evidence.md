# Evidence ledger (Stage 4.5.3)

Implemented 2026-11-24. This is a machine-checkable record of what we claim and what supports it. Claude and ChatGPT both write ledgers; the owner never fills in forms.

| What | Where |
|---|---|
| Schema | `research/schemas/evidence-ledger.schema.json` |
| Validator and tools | `scripts/evidence.py` (`ss evidence`) |
| Ledgers | `data/local/research/evidence/<ID>.json` (local; they cite restricted data with expiry). Copied into every research bundle under `evidence/` |
| Worked example | `EXAMPLE-HUSS-SLUGTERRA` (real data, in the 24 Nov bundles) |
| Upstream | statuses, evidence roles, access statuses and the seven finding types come from EvidenceGuard V0.1 (MIT, commit 4ef6e60; `research/upstream/evidenceguard/`) |

## Commands

```powershell
.\ss evidence new TREND-HUSS-01 --question "Is Huss still being adopted in US/MX gaming content?"
.\ss evidence validate TREND-HUSS-01 --bundle exports\share\research --fix-summary   # deterministic checks
.\ss evidence card TREND-HUSS-01                  # claim cards + decision memo -> .md next to the ledger
.\ss evidence export-evidenceguard TREND-HUSS-01  # the same audit in EvidenceGuard V0.1 format
```

## Structure

A ledger holds:

| Part | Contents |
|---|---|
| `decision` | `decision_id`, question, decision threshold |
| `contract` | primary question, construct, what is NOT evidence, markets, languages, platforms, window, hypotheses, rival hypotheses, negative controls, sampling plan, stop rule |
| `evidence[]` | one item per piece of evidence |
| `claims[]` | one atomic proposition each |
| `decision_memo` | see below |
| `limitations` | free text |

### Evidence items

| Field | Meaning |
|---|---|
| `evidence_id` | stable ID (E1, E2, ...) |
| `source_family` | the data-generating process: youtube, tiktok, instagram, twitch, roblox, google_search, wikimedia, news, literature, owned_experiment, qualitative_review, community_reference, other. **Several tools relaying one platform's number are one family** (YouTube API + vidIQ's YouTube views = youtube) |
| `actual_role` | EvidenceGuard roles (observed_result, estimate, forecast, target, definition, requirement, expert_opinion, contextual_background, method_or_design, other) plus platform_metric, third_party_estimate, normalised_index, qualitative_coding, experiment_result, literature_finding, search_record |
| `provenance` | P1 platform count, P2 index/rank/band, P3 third-party estimate, P4 interpretation |
| `access_status` | full, partial, metadata_only, inaccessible |
| `item`, `item_type`, `metric`, `observed_at`, `scope{}` | what was observed, when, and under which filters (region, period, category, query, region_param, relevance_language_param, language_edition, ...) |
| `series_points` | when one item of evidence is a dated series |
| `metric_definition` | verified, approximate, unknown |
| `sample_role` | featured, ordinary, failed, counterexample, unknown |
| `expires_at` | provider retention of the cited data |
| `locator` | `file` + `where{col: value}` + `column` + `value` (a bundle row), or `source_path` + `quote` (an exact passage of a saved source), or `url`, or `note` |

### Claims

| Field | Meaning |
|---|---|
| `claim_id`, `claim_text` | exact bounded wording, one proposition |
| `level` | **O** observation, **D** derived statistic, **P** descriptive pattern, **I** interpretation, **C** causal claim, **R** recommendation. A recommendation does not need a causal claim: a cheap test can rest on suggestive evidence |
| `support_status` | **supported** (the exact claim, within its scope); **partially_supported** (a narrower material part); **unsupported** (the cited evidence fails to justify it, or contradicts it); **indeterminate** (missing, inaccessible or ambiguous: we can't tell). Indeterminate is not false |
| `strength` | **exploratory** (one source or snapshot, convenience sample); **suggestive** (repeated or several observations agree, but selection/measurement alternatives remain); **supported_descriptive** (defined construct, planned sample, repeated comparable measurements, negative cases sought); **convergent** (methods with different biases agree: at least two independent families); **experimental** (our own controlled test) |
| `dimensions{}` | directness, coverage, temporal, independence, robustness, counterevidence, each rated strong / adequate / weak / none / unknown with a note. **No numeric confidence score anywhere** |
| other | `evidence_refs[]` (evidence or earlier claim IDs), `counterevidence_refs[]`, `rival_hypotheses[]`, `missingness`, `analysis_spec`, `values{}`, `causal_basis`, `next_discriminating_test`, `findings[]` (EvidenceGuard types), `review{ai_reviewed, reviewer, notes}` |

### Decision memo

`recommend`, `supported_findings[]`, `uncertain_but_useful[]`, `counterevidence[]`, `unknown[]`, `creative_hypothesis`, `cheapest_test`.

## What the validator checks (deterministic)

**Errors:**
- **Structure:** required fields, legal values, duplicate IDs, references that point nowhere.
- **Row resolution:** the cited row exists in the bundle file, and the stated value matches the cell (rounding-aware).
- **Blanks:** a blank cell cited as 0.
- **Quotes:** a quote that isn't an exact passage of the saved source.
- **Support:** supported or partially supported claims without evidence; unsupported claims with no evidence at all.
- **Causal wording** ("drives", "causes", "boosts", "proves", "because of", ...) in a non-causal claim; a level-C claim with no experiment or stated causal basis. (Vocabulary from K-Dense hypothesis-generation `lint_causal_claims.py`, MIT, plus Slugshot additions.)
- **Lifecycle wording** ("accelerating", "declining", "saturated", ...) without two comparable observations (same item, metric and scope; or a dated series).
- **One item's trajectory** used for a claim about a trend, meme, format or sound.
- **Audience, fan or demand wording** backed only by retrieval or edition scope (region_param, language edition, tool filter) or only by Wikipedia.
- **Generalising** ("most", "typical", "usually") from featured examples only.
- **Strength:** "convergent" with fewer than two independent source families; "experimental" without owned-experiment evidence; "supported_descriptive" without repeated observations.

**Warnings:**
- expired evidence;
- P3-only support for observations;
- unknown metric definitions;
- numbers in the claim that can't be traced to a cited value or the analysis spec;
- recommendations with no test.

**Review items** (for Claude/ChatGPT to judge and mark `review.ai_reviewed`):
- several items from one family;
- missing rival explanations;
- counterevidence alongside full support;
- hedged wording;
- audit records of overclaims;
- general semantic fit.

**Deliberately allowed:**
- Claims recorded as `unsupported` or `indeterminate` may contain overclaiming wording. They are the audit of what we do *not* accept.
- Hedged claims ("whether X is rising is unknown") go to review instead of erroring.

## Example (real, abridged)

> **C1 [O]** Creative Center displayed 71.6M views and 24.4K posts for #huss (US, 7-day filter, captured 24 Nov 2026). Status supported, strength exploratory. Temporal: none (one snapshot). Independence: none (TikTok only). Definition: unknown.
>
> **C2 [P]** Whether Huss adoption is rising or declining is unknown: one Creative Center snapshot and no Trending Now appearance in seven markets. Next test: re-capture US and MX in 3–4 days; code 20 recent posts outcome-blind for gaming context.
>
> **C3 [P]** The Spanish Wikipedia "Slugterra" article has a change point on 25 Sep 2026 (median 41 → 26 daily views) in an 11-year daily series. Suggestive; rivals: routing change, seasonality, general Wikipedia decline.
>
> **C5 [R]** Before using Bajoterra nostalgia in Spanish content, get an independent source family (Google Trends Explore MX/ES/AR, a YouTube sample).
