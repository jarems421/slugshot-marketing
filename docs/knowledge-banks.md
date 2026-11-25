# Knowledge banks (Stage 4.7)

Built 2026-11-25. These are private, local, structured research memory. Entries point to evidence, which lives in the [evidence ledgers](research-evidence.md); the banks don't copy it. There are no numeric confidence values or composite scores.

## Where things live

| What | Where | In Git? |
|---|---|---|
| Banks | `data/local/research/knowledge/` (`curated/`, `generated/`, `sentiment/`); override the location with `SLUGSHOT_KB_DIR` | no (private strategy) |
| Rendered views | `data/local/research/knowledge/INDEX.md`, `views/<bank>.md` (from `ss kb render`; never edit by hand) | no |
| Library and CLI | `scripts/kb.py` (`ss kb`) | yes |
| Test fixtures | `tests/fixtures/knowledge/` (the dashboard demo reads these, never the real banks) | yes |
| Source reports and audit | `research/sources/stage-4.6/` (immutable) and `data/local/research/stage-4.6/` | no |

## Banks and IDs

| Bank | Prefix | Holds |
|---|---|---|
| inventory | `INV-` | every item extracted from the six Gemini reports (582), with original text and line locators. Nothing is dropped |
| sources | `WRK-` | one entry per work (by DOI, or per evidence entry without one). Each carries `family_id`, `lineage_id` and the preliminary `cluster_ids`; evidence ↔ work is many-to-many |
| claims | `CLM-` | the 107 report claims. Separate fields for bibliographic check, figure presence, contextual review, design, directness, support, strength, transfer assumption, access and reviewer. The report's own support and strength are kept as metadata only |
| amendments | `AMD-` | versioned corrections (DOIs, sources found later, game truth); the audit itself is never edited |
| mechanisms | `MECH-` | the 11 cross-domain mechanisms, revised after the 4.7 review |
| hooks, narrative, humour, audiovisual | `HOOK-`, `NARR-`, `HUM-`, `AV-` | bounded craft principles (applications, not validated effects) |
| characters | `CHAR-` | character rules; **game-truth references are mandatory** |
| funnel | `FUN-` | cognitive journey vs commercial stages, plus dated platform facts (each cites ledger claims, re-check after 90 days) |
| culture | `CULT-` | dated cultural cards with seven separate dimensions and a `review_by` date |
| sentiment | `SENT-` | coded audience-comment samples (see [audience-sentiment.md](audience-sentiment.md)) |
| opportunities | `OPP-` | creative openings, including owner hypotheses marked unvalidated |
| hypotheses | `HYP-` | the 17 test families; all 51 original hypothesis IDs are kept as aliases. **Experiments live in the dashboard** (`EXP-…`); a family links to them with `experiment_refs` |
| decisions | `DEC-` | append-only decision history |

Concepts likewise stay in the dashboard (`CON-…`). The banks reference them and never keep a second copy.

## Entry fields that keep things honest

- `evidence_label`: what kind of evidence. Values: established, adjacent, verified_platform, owned_result, application, untested, owner_hypothesis, observed, inventory.
- `review_status`: draft → reviewed → approved (needs an owner entry in `history`) → retired. **Review is not evidence.**
- `support_status` and `strength`: the v1.1 vocabulary. `experimental` is reserved for our own tests.
- `shelf_life`, `observed_at`, `review_by`: freshness is shown as fresh, due (within 14 days), stale or evergreen.
- `boundaries`, `rivals`, `transfer_assumption`, `game_truth[]`, typed `links[]`, `report_aliases[]`.

## Validation (`ss kb validate`)

Errors for:
- missing or invalid fields, unknown enum values, duplicate IDs, or an ID prefix that doesn't match its bank;
- bad dates, or an expiring entry without `observed_at` or `review_by`;
- an evidence-backed entry without references or support;
- ledger `claim_refs` that don't resolve, or links or sources that point nowhere;
- character entries without game truth, or game-truth rows or labels that don't match `docs/game-truth.md`;
- hypotheses without scope, design or comparator;
- `approved` without an owner in the history;
- `experimental` strength outside owned results;
- sentiment entries that break policy (unknown source, comment text past expiry, cross-channel YouTube aggregation without the amendment, usernames).

Warnings for stale entries and for causal wording without a causal basis.

## Commands

```powershell
.\ss kb validate
.\ss kb find floppy --format SKIT            # text and filters: --bank --objective --format --lang --character --stage --evidence --status --due --all
.\ss kb show CHAR-001                       # entry with ledger claims, links and inbound references
.\ss kb brief "Floppy vs Inferno standoff" --character floppy --format SKIT   # inputs for a creative brief
.\ss kb due                                 # stale or due entries
.\ss kb stats ; .\ss kb render
.\ss kb export                              # exports\share\knowledge\<stamp>\ (no comment text, no raw inventory)
.\ss kb migrate --audit data\local\research\stage-4.6   # rebuild generated banks; curated files are untouched
```

The dashboard's Research page has a Knowledge browser (search and filters), Opportunities, Audience sentiment and Due for review. Experiments shows each experiment's hypothesis family and the full family list. `ss dash export` includes `knowledge.jsonl` through the same export gate.

## Everyday use (keep it light)

concept → `ss kb brief` → optional quick cultural check (`ss sentiment`, trends) → brief → produce → owner-approved publish → read results in the dashboard → add a `DEC-` entry or an owned result.

No formal research or experiment per video by default. Tests are a learning portfolio, not gates.
