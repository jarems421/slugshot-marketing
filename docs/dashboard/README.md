# Slugshot dashboard

A personal marketing dashboard that runs on this PC: Overview, Content, Research, Game and Experiments, plus Settings. It reads the toolkit's existing research outputs, our own accounts' analytics (through official APIs once authorised) and manual imports. It never posts, never runs in the cloud and is only reachable from this computer. Built 2026-11-25.

## Open it

| How | What happens |
|---|---|
| **Desktop / Start-menu shortcut "Slugshot Dashboard"** (create once with `.\ss dash install`) | starts the server in the background (no console window) if it isn't running, opens an app window |
| `.\ss dash` | same, from a terminal |
| Install as an app | in the app window: `…` → Apps → Install Slugshot (a PWA); pin it to the taskbar from Start |
| `.\ss dash stop` | stops the background server |

The server listens on `http://127.0.0.1:47615/` only. If that port is taken it stops with a clear message instead of sharing it (change `port` in `config/dashboard/settings.json`, then update the OAuth redirect URIs).

## Commands (`.\ss dash <command>`)

| Command | Does |
|---|---|
| `open` (default) | start if needed, open the app window |
| `sync [names]` | refresh now: every connected account, or e.g. `youtube_analytics`, `yt-es`, `roblox` |
| `status` | each source: credential state, freshness, last success; credentials shown as yes/no only |
| `import <file.csv> [--check] [--skip-bad]` | manual metrics (validated; `--check` stores nothing) |
| `export [--detail overview\|detailed] [--local] [--start --end --platform --language]` | campaign snapshot for ChatGPT/Claude/Gemini |
| `install` | Desktop and Start-menu shortcuts |
| `demo` / `stop --demo` | fixture data in a separate database on port 47616, labelled FIXTURE on every page |
| `serve` | run the server in the foreground (debugging) |
| `publish …` (also `.\ss publish …`) | publishing drafts, checks, manual packages, recording hand-made posts; approval only in the app ([publishing.md](publishing.md)) |

Tests: `.\ss smoke --dashboard` (writes `reports/smoke-test-dashboard.md`) or `.venv\Scripts\python -m unittest tests.test_dashboard tests.test_publish`.

## Pages

- **Overview**: views, followers and watch time **per platform** (never added together), new players, latest complete D1 cohort, revenue; views per day by platform; players per day; accounts with freshness; recent uploads. Filters: 7/28/90 days, platform, EN/ES.
- **Content**: published uploads with views, likes, average view duration and % viewed; concepts with their EN/ES versions; local renders from `exports/` (with QC) that can be registered as versions. Sorting by views is only offered within one platform. Click an upload for its detail: every metric with its source, metrics the platform doesn't offer marked as such, snapshots over time, the same version on other platforms, linked experiments.
- **Research**: findings from the evidence ledgers (level O/D/P/I/C/R, support status, verbal strength; recommendations and interpretations first), research collection runs, decision memos, Google Trending Now, watchlists, recent public observations with provenance, and the **knowledge banks** (Stage 4.7; [docs/knowledge-banks.md](../knowledge-banks.md)): a Knowledge browser with search and filters (bank, evidence label, review status, format, language, due or stale) and an entry drawer (statement, boundaries, transfer assumption, game truth, ledger claims, links, history); Opportunities with separate dimensions; coded Audience sentiment samples; Due for review. The demo (fixture) dashboard reads `tests/fixtures/knowledge/` only.
- **Game**: the seven measurement stages (Discovery, Engagement, Interest, Acquisition, Activation, Retention, Monetisation), each in its own population and window, primary metrics first and the rest behind "More"; players per day, D1 by cohort, revenue per day, acquisition sources (average per day), share links, cohort table.
- **Experiments**: hypothesis, the one change, primary metric and read time, stop rule and threshold, variants linked to versions, each linked upload's reading nearest the read time, results, limitations, decision, next action. Seeded with `EXP-20261124-OPENER` (rule-world vs tier-skit opener) from the Stage 4.5.4 decision memo, status *proposed*, no results. Each experiment shows the hypothesis family that links to it, and a **Hypothesis families** panel lists the 17 families (T01–T17) with their gates; experiments stay the single source of truth here.
- **Publish**: our accounts (five active; Spanish Instagram later) with their upload readiness and **Connect for uploads**; a queue of drafts and uploads; **New post** (version, video file, optional experiment variant, accounts and route per account). A draft shows a 9:16 preview, that platform's text and settings (YouTube title, description, tags, visibility, made-for-kids, synthetic content; TikTok caption, TikTok's required posting controls, AI label; Instagram caption, feed sharing), the checks, and the approval box (type the handle). Manual drafts make a package and take the link back. Details: [publishing.md](publishing.md).
- **Settings**: connections and their health, connect/disconnect (optionally deleting that source's data), refresh now and the daily-refresh switch, manual import (checked before anything is stored), export, theme, app credentials (write-only), accounts (EN/ES, handles, IDs).

## Architecture

```
Edge app window / PWA ──HTTP (127.0.0.1 only, per-start token on writes)──► dashboard/server.py (Python standard library)
                                                                              │
     views.py (all metric rules) ◄── store.py: SQLite data/local/dashboard/slugshot.db (git-ignored)
                                                                              ▲
 sync.py ── connectors.py: YouTube Analytics · Instagram · TikTok Display · Roblox Analytics Query · Roblox public
 imports.py ── platform_metrics template (shared with `ss export`) · long template
 views.research() ── reads data/local/research/* and config/research/* in place (no copy)
 reports.py ── exports/share/dashboard/<snapshot>/ (safe) or data/local/dashboard/exports/ (private)
 vault.py ── DPAPI-encrypted tokens and keys in data/local/dashboard/vault/
```

**Why this stack:** the toolkit is Python standard library plus Node for Remotion. A standard-library server, SQLite and a build-free front end (one JS file, one CSS file, the Urbanist font vendored under SIL OFL) add **no new dependencies**, no build step and nothing to update. The design follows Jami (`jarems421/jami-flashcards`, read only): its night-navy and paper-white token sets, Urbanist, 1.5 px bordered panels at the 28 px shell radius, icon-bubble sidebar with label and description, tracked uppercase eyebrows, the four-step elevation scale and 160/260/430 ms motion. Chart colours for platform identity passed the dataviz palette validator on both surfaces.

### Identifiers

| ID | Example | Meaning |
|---|---|---|
| `account_id` | `yt-en`, `tt-es`, `rbx-slugshot` | one of our accounts (`config/dashboard/settings.json`) |
| `concept_id` | `CON-FLOPPY-UNDERDOG` | a creative idea, language-neutral |
| `asset_id` | `CON-FLOPPY-UNDERDOG-ES-V01` | one edited video of a concept in one language |
| `upload_id` | `UPL-youtube-<video id>` | one platform upload of a version |
| `experiment_id` | `EXP-20261124-OPENER` | variants link to `asset_id`s, so one version on three platforms is one unit measured three times |

### Observation contract (`observations` table, long format)

`platform, account_id, entity_type (account|upload|experience), entity_id, metric, value, status, period_type (day|window|lifetime|point), period_start, period_end, breakdown_dim, breakdown_value, observed_at_utc, source, provenance, run_id, expires_at_utc, note`

- **Missing** = no row. **Unavailable** = a row with `status=unavailable` (the provider refused or doesn't offer that metric). **Zero** = a value of 0. **Stale** = read from `observed_at_utc` against `refresh_hours`/`stale_hours`.
- `day` and `window` readings of the same period replace each other (late corrections, deduplication); `lifetime` and `point` readings keep every snapshot (growth between snapshots).
- Metric definitions, units, kinds and stages: `config/dashboard/metrics.json`. Kinds: `count` (summed over days within one account/platform), `daily` (people who recur across days, e.g. daily players: shown per day or as an average, never summed), `rate` (never summed; retention is per cohort), `level` (latest reading), `money` (Robux as reported).

### Rules the code enforces

- No sums across platforms, anywhere. EN + ES accounts of one platform may be added (same owner, same platform).
- No conversion rates between funnel stages; viewers can only be followed into the game through a tracked share link.
- Views are ranked only within one platform; YouTube "% viewed" and TikTok "watched full video" are labelled as different measures.
- TikTok has no daily views through its API: its totals are shown as *lifetime*, never mixed with period counts.
- Player acquisition is never inferred from views and player numbers moving together.

## Synchronisation

Daily by default, and when the app opens if anything is due (Settings switch; `refresh_hours` 24, `stale_hours` 36). While the server runs it checks hourly; there is no OS scheduler. Manual: the refresh button or `ss dash sync`. Each connector × account runs separately: a failure is recorded with its message and the rest carry on. Requests retry with backoff on 429/5xx/network errors (never on 401/403, which mark the source "reconnect"); Roblox analytics queries that answer asynchronously are polled. Day-level data is re-read over the last 3 days and backfilled on first run (YouTube from `history_start`, Roblox 90 days, Instagram 7 days).

## Imports

For figures no authorised API gives us (TikTok Studio, Instagram app, YouTube Studio exports, Roblox share links and funnels):

- `data/templates/platform_metrics_template.csv` (the same file `ss export` checks), one row per upload per observation; optional extra columns `account_id, language, concept_id, asset_id, platform_video_id`. It creates the concept, version and upload from the edit-file name and URL.
- `data/templates/dashboard_metrics_long_template.csv`, one row per value: `date_start,date_end,platform,account_id,entity_type,entity_id,metric,value,breakdown_dim,breakdown_value,note`.

Strict like `ss observe`: "22.4K" is stored as 22400 and flagged rounded; bad dates, future observations, unknown metrics or accounts, and non-numbers are errors naming the row; a file with errors is refused unless you choose to import only the good rows; the same file is never imported twice.

## Exports for ChatGPT, Claude and Gemini

`ss dash export` (or Settings → Export) writes individually readable files, no ZIP: `README.md` (how to read it, sources and freshness, per-platform summary, game stages, experiments, research summary, missing data and limitations, file list), `metric_definitions.csv`, `sources.csv`, `accounts.csv`, `content_<platform>.csv`, `experiments.json/.csv`, `research_findings.csv`, and with `--detail detailed` `observations_<platform>.csv`. Safe-to-share mode applies `sharing` in `config/dashboard/settings.json`, removes local media paths, keeps providers in separate files, and scans every file for credential values (the export is deleted if one appears). Nothing is uploaded anywhere: the owner attaches the files.

## Security and privacy

Loopback only; Host-header check (DNS rebinding); cross-origin requests refused; every write needs the token embedded in the page at each server start; exclusive port binding; static files can't escape `dashboard/static/`; credentials are write-only through the API and stored with Windows DPAPI; the database, vault, logs and exports live in git-ignored folders (`data/local/`, `exports/`, `out/`), checked by a test. Fixture data only exists in `out/dashboard_demo/` and is labelled on every page.

## Status

| Part | Status |
|---|---|
| All seven pages, filters, drawers, themes, phone layout | implemented, visually reviewed (dark, light, 600 px) |
| Store, metric rules, imports, exports, vault, server security | implemented, 30 unit tests pass |
| YouTube Analytics, Instagram, TikTok, Roblox Analytics connectors | **fixture-tested** (documented response shapes); live use waits on the checklist |
| Roblox public games connector | **live-validated** (2026-11-25, read a public experience into a throwaway database); our own game isn't published |
| Research page | live on the real research store |
| Launcher, background start, exclusive port | tested |
| Publishing (Publish page, `ss publish`) | built; **fixture-tested** (14 tests); live uploads wait on the upload permissions and the owner's approval of each job |
| Activation stage | blocked: needs approved in-game events ([proposal](activation-events-proposal.md)) |

What the owner must do: [credentials-checklist.md](credentials-checklist.md).

## Integrations: adopted, deferred, rejected

| Option | Decision | Why |
|---|---|---|
| Official APIs direct (YouTube Analytics, Instagram Login, TikTok Display, Roblox Analytics Query) | adopted | free, owner-authorised, no third party sees private analytics |
| Existing `ss export` template, research store, evidence ledgers, `research_common` HTTP/redaction helpers | reused | one source of truth; nothing re-collected |
| Roblox legacy public games API | adopted (no key) | already live-validated in `ss rbx`; gives visits/playing/favourites |
| Composio | deferred | Instagram through it needs the same Meta OAuth, adds a third party and a plan cap; useful later only for a service with no direct API |
| TikTok API for Business / Business account | rejected for now | needs a Business account (Commercial Music Library only); the Display API plus Studio imports cover the need |
| TikTok/Instagram scraping, browser automation of Studio pages | rejected | provider terms |
| Google Drive / Claude Docs MCP for exports | deferred | files stay local; the owner uploads what they choose |
| Electron/Tauri app, hosting, login | rejected | the Edge app window and PWA give an app-style window with nothing to install or update |
| A charting or UI library | rejected | hand-drawn SVG charts (crosshair, tooltip, legend, table view) cover every chart here |
