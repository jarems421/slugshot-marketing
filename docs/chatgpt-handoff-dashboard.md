# Dashboard handoff for ChatGPT and Gemini (25 Nov 2026)

For ChatGPT's research skills (v1.1) and Gemini. It explains what the new dashboard measures, how its snapshot files are structured, and what each AI owns from here. Full technical reference: [dashboard/README.md](dashboard/README.md).

## 1. What changed

Milestones 2 (commercial funnel) and 3 (centralised dashboard) are built as one local app on the owner's PC. It holds:

- our own accounts' analytics: YouTube EN/ES, Instagram EN/ES, TikTok EN/ES and the Roblox experience;
- the existing research store and evidence ledgers (read in place, nothing re-collected);
- a content registry;
- experiment records.

**Live platform data has not arrived yet.** The connectors are tested on fixtures, and the owner still has to authorise each account. The game is unpublished. Until data arrives, every snapshot says so in its README and its `sources.csv`.

## 2. Snapshots you will receive

The owner runs `ss dash export` and uploads the folder's files one by one (there is no ZIP). Each snapshot contains:

| File | What it is |
|---|---|
| `README.md` | how to read the snapshot, window and filters, sources and freshness, per-platform summary, the seven funnel stages, experiments, research summary, missing data, excluded data |
| `metric_definitions.csv` | metric id, label, kind, unit, stage, platforms, definition |
| `sources.csv` | each connector × account: credential state, freshness, last success, last error |
| `accounts.csv` | account ids (`yt-en`, `tt-es`, `rbx-slugshot`, …), platform, language |
| `content_<platform>.csv` | one row per upload: concept, version (language), format, hook, slug, published time, latest values per metric (`unavailable` where the provider doesn't offer it) |
| `experiments.json` / `.csv` | every experiment with variants, linked uploads and the reading nearest the read time |
| `research_findings.csv` | ledger claims: level, support status, verbal strength, text |
| `observations_<platform>.csv` (detailed export only) | every observation in the window, long format, with source, provenance, run id and notes |

## 3. Reading rules (enforced in the code; please keep them in analysis)

- **Never add or rank across platforms.** Each platform counts a view differently, and one person can follow several accounts. EN + ES accounts of one platform may be added.
- **Period vs lifetime.** TikTok's API gives only lifetime totals per video; they are labelled `lifetime` and never mixed with period counts.
- **Kinds:**
  - `count`: may be summed over days within one account.
  - `daily`: daily players, payers. These are never summed, because people return on several days; use per-day values or the average.
  - `rate`: never summed. Retention is per first-day cohort.
  - `level`: the latest reading.
- **No conversion rates between funnel stages.** Discovery, Engagement and Interest are measured on social platforms, and Acquisition onwards in Roblox. These are different populations and windows. A viewer can only be followed into the game through a tracked share link (one link per account or campaign). Rising views alongside rising players is not acquisition evidence.
- **Missing, unavailable and zero are different.** Blank = not collected; `unavailable` = the provider refused or doesn't offer it; 0 = reported zero.
- YouTube "average % viewed" and TikTok "watched full video" are different measures.
- Roblox values carry Roblox's own notes ("projected", "not statistically significant") where Roblox marks them.

## 4. The commercial funnel as measured

| Stage | Measured by | Source |
|---|---|---|
| Discovery | views, reach | YouTube Analytics, Instagram insights, TikTok Display API (lifetime) |
| Engagement | watch time, avg view duration, avg % viewed, likes, comments, shares, saves | same; TikTok watch metrics by manual import from TikTok Studio |
| Interest | followers, followers gained/lost, link taps, profile visits | same; profile visits mostly manual |
| Acquisition | new players, players by Roblox acquisition source, share-link visits and new players | Roblox Analytics Query API; share links by manual import |
| Activation | onboarding funnel steps | **not measured yet**: needs approved in-game events ([proposal](dashboard/activation-events-proposal.md)) |
| Retention | daily players, D1/D7/D30 by cohort, session length, visits | Roblox Analytics Query API |
| Monetisation | revenue (Robux), payers, payer conversion (Roblox's own ratio) | Roblox Analytics Query API |

## 5. Experiments

`EXP-20261124-OPENER` (rule-world opener vs tier-skit opener) is recorded as **proposed**, from the Stage 4.5.4 decision memo. It has no results.

**ChatGPT: please set the decision threshold** before posting. The current settings are:

- primary metric: average % viewed;
- read time: 48 h after posting;
- stop rule: one reading at 48 h;
- design: one language at a time; the same footage and payoff, with two openers.

Variants link to versions (language-specific edits), not to uploads. One version posted to three platforms is one unit measured three times, never three experiments.

## 6. Extension points for the foundational research

- **Knowledge banks:** Markdown files in `research/knowledge/` (shareable) or `data/local/research/knowledge/` (private) appear on the Research page automatically.
- **Gemini Deep Research (six investigations):** the integration needs no new infrastructure. Turn each investigation's findings into:
  - an evidence ledger (`ss evidence`), so its claims keep their levels and support status;
  - knowledge-bank Markdown;
  - where a finding suggests a cheap test, an experiment record.
- **Gemini footage analysis:** unchanged (`docs/flow-and-gemini.md`).

## 7. Sharing

Snapshots apply `sharing` in `config/dashboard/settings.json`. Own-account analytics are included (the owner's data; this extends the 24 Nov sharing decision and is pending the owner's confirmation). Local media paths are removed, and every file is scanned for credentials. Treat the data as internal: don't publish it, and delete copies when a newer snapshot replaces them.
