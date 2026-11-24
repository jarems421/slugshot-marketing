---
name: slugshot-research-operations
description: Run Slugshot's research data collection end to end from a short instruction ("collect today's research", "research Spanish Roblox content", "refresh our watchlists", "research Creative Center", "execute this research brief from ChatGPT"). Picks the collectors, runs them, handles errors and quotas, validates, bundles for ChatGPT and reports. Use for any research collection, import or export task in this workspace.
---

# Slugshot research operations

The `ss` toolkit is **Claude's interface, not the owner's**. When the owner gives a research instruction, run everything yourself: choose the collectors, run the commands, deal with ordinary errors, organise the files, build the bundle, and report. Don't ask the owner to run commands, format tables or move files you can handle. Use sensible defaults instead of asking.

Reference: `docs/research-data.md` (sources, schemas, sharing rules), `docs/COMMANDS.md`. ChatGPT owns methodology, query design and interpretation; this skill only executes and reports. Never rank, score or classify concepts.

## Intent → what to run

| Owner says | Run |
|---|---|
| "Collect today's research" | `.\ss research collect --profile daily` |
| "Research Spanish Roblox content" | `.\ss research collect --profile spanish` (MX, ES, AR, CO, CL; uses ChatGPT's saved YouTube set `spanish`, merged in Stage 4.5.4) |
| "Refresh our watchlists" | `.\ss research collect --profile refresh` (re-snapshots stored YouTube videos and Twitch clips, creator and broadcaster lists, Wikipedia, Roblox) |
| "Research Creative Center" | the Creative Center procedure below |
| "Execute this research brief" | the brief procedure below |
| "Bundle what we have" / "send it to ChatGPT" | `.\ss research bundle` |
| "What's the status?" | `.\ss research status` and `.\ss research runs` |

Targeted runs (single sources) are fine whenever they fit the request better: `ss yt discover/chart/creators/comments`, `ss wiki pull`, `ss trends rss`, `ss twitch clips/streams`, `ss rbx games`, `ss observe import`. Add `-h` to any command for its options.

## After collection: analysis

Anything that asks what the data *means* goes to the `slugshot-research-analysis` skill. That covers analysing a bundle, checking whether a trend is growing, finding evidence for or against something, coding creators' mechanisms, comparing observations, or academic verification. The skill gives intake QC, deterministic statistics, trend dimensions, outcome-blind coding and the evidence ledger (`ss analyze ...`, `ss evidence ...`).

- Every `ss research bundle` automatically adds an `INTAKE.md`/`INTAKE.json` QC report and any ledgers (`evidence/`) and trend outputs (`analysis/`).
- For a brief, finish with a ledger and decision memo, not only a data dump.
- Query families (families-1.1): ChatGPT edits `config/research/query_families.json`. Run `ss research families --compile` to turn them into YouTube saved sets named `fam-<id>[-<branch>]`. `market_mode: rotate` gives each query one retrieval country, rotating each ISO week, so recompile at the start of a week. Spanish branches may set their own `days`. When comparing yields, change wording or window, not both at once.
- Coding for a brief: build the packet with `ss analyze coding-packet` (all ten codes; see the analysis skill). Gemini gets it through the owner; a person's spot-check uses `--keys` and `--coder owner`.

## Executing a ChatGPT research brief

1. Read the brief. Map each requested item to a collector; note anything no source can supply (e.g. audience geography, competitors' retention) and say so in the report rather than approximating it.
2. Put the brief's lists into config, not code:
   - YouTube queries: add a set named `brief-YYYYMMDD` to `config/research/youtube_queries.json` (`query`, `lang`, `region`, `days` or `after`/`before`, `order`, `duration`, `max`), then run `ss yt sweep --set brief-YYYYMMDD --check-shorts`.
   - Creators, broadcasters, Wikipedia topics, Roblox experiences: append to the CSVs in `config/research/`, keeping existing rows. Resolve Roblox place IDs with `ss rbx universe <placeId>`, and YouTube handles to channel IDs via a `discover`/`videos` lookup.
   - Observation tables from ChatGPT (CSV or Markdown): save them under `data/local/research/observations/inbox/` and run `ss observe import` with `--source` and the scope options (`--region --period --category --observed-at`).
3. Run, then `ss research bundle`, then report.
4. If the brief would exceed the YouTube daily budget (`ss yt quota`), run what fits, schedule nothing, and report what's left for tomorrow.

## Creative Center (core source; the owner's browser does the access)

There's no permitted automated access: TikTok's commercial terms bar automated scripts collecting from its commercial tools, and no browser-control tool is connected in VS Code sessions. So keep the owner's part to one grouped action:

1. Start the guided session yourself, in the background: `.\ss observe cc-session --regions US,GB,MX,ES,AR,CO,CL --periods 7 --category Games` (add `30` to periods if asked).
2. Ask the owner, once: "Creative Center is opening in your browser. On each page: pick Games if it isn't selected, scroll once, press Ctrl+A then Ctrl+C. I'll handle the rest." If a login wall appears, ask them to sign in once in that browser.
3. The session watches the clipboard, ignores anything that isn't a hashtag list, saves the copied text to the inbox, parses and imports it (scope, URL and time filled in), opens the next page, and prints a summary. Skipped pages are reported, not retried endlessly.
4. Check the parsed previews look sane (ranks increasing, values like 24.5K / 60.1M). If the real page layout parses badly, fix `parse_cc_text` in `scripts/observe.py` against the saved `.txt`, then re-import with `ss observe cc-paste <file> --region .. --period .. --import`.
5. If ChatGPT/TinyFish already collected Creative Center rows, import their table directly with `--source creative_center --collected-via tinyfish_via_chatgpt`.

## Handling problems (keep going; report at the end)

- One collector failing never stops the others (`research collect` continues by design).
- YouTube budget stop: run the remaining non-YouTube steps and report the remaining quota. Don't raise the budget past Google's free limits, and never enable billing.
- Rate limits (429): the collectors already pace and retry; if a step still fails, rerun that step once later in the session.
- Roblox "wait until 55 min": expected, report as skipped.
- Twitch BLOCKED: report it; Twitch exports stay local while `twitch.share_exports` is false.
- A Google Trends Explore CSV the parser rejects: inspect the file and fix the parser for the real format, then import.

## Bundle and report

`ss research bundle` writes `exports/share/bundles/slugshot_research_<time>.zip` (newest export of each kind, MANIFEST, DATA_DICTIONARY, BUNDLE_SUMMARY). Report to the owner in a few lines:
- the scope collected;
- rows per source (from BUNDLE_SUMMARY);
- what failed or was skipped, and why;
- material caveats (e.g. default query used, a parser that isn't confirmed yet);
- the bundle path.

The owner uploads the zip to ChatGPT. Don't claim any automatic sync exists. Google Drive is connected to Claude (claude.ai connector). Composio is set up read-only but has no accounts authorised (`docs/composio.md`). Uploading research data to Drive is a shared-workflow decision, and YouTube/Twitch copies would have to be deleted by their expiry, so don't upload without the owner asking. Reuse native connectors first, and check Composio before building any new OAuth integration.

Only send the newest corrected bundle. Superseded bundles stay out of `exports/share/` (see `docs/stage-4.5.4-report.md`), and the owner manages deletion of copies uploaded to chats.

## Pre-approved vs ask first

Pre-approved (just do it): free API calls within budgets, local file and config changes in this workspace, imports, exports, prune, bundles, opening pages in the owner's browser, reading clipboard text that parses as research data.

Ask first:
- spending money, paid APIs or subscriptions, or any vidIQ credits without an agreed budget;
- publishing anything;
- destructive operations beyond the collectors' own retention pruning;
- changes to the game repo `../slugshot`;
- sharing Twitch exports;
- anything that would bypass a login, rate limit or access control.

Never print credentials. Keep the YouTube policy limits (30 days, per-video maths only), provenance labels, blank-not-zero, and the Studio guard.
