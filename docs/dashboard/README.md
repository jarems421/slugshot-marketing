# Slugshot dashboard

A personal marketing dashboard that runs on this PC: **Overview, Content, Publish, Roblox and Settings**. It shows our own accounts' analytics (official APIs and Buffer), our videos, and publishing. It runs only on this computer and never posts without the owner's approval. Built 2026-11-25; redesigned the same day for a simpler daily view.

**Principle (owner, 2026-11-25): show the minimum useful information by default; detail appears only when you click into a metric, account, video or section.** Research, knowledge banks, evidence ledgers, sentiment and experiments are still fully available to Claude (`ss kb`, `ss evidence`, `ss analyze`, `ss sentiment`, `/api/knowledge`, `/api/experiments`), but they are not pages any more.

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

Tests: `.\ss smoke --dashboard` (writes `reports/smoke-test-dashboard.md`) or `.venv\Scripts\python -m unittest tests.test_dashboard tests.test_publish tests.test_analytics`. Also `hosting status|test|cleanup` (Cloudinary).

## Pages

| Page | Shows by default | Click into |
|---|---|---|
| **Overview** | Total views (combined, platform-reported) with the change against the previous period; total followers (combined account counts) with the change; watch time as a secondary line; views per day; the accounts list. Filters: 7/30/90 days, all time or a custom range; platform; account; EN/ES. | **Views**: views over time, by platform (click to narrow), by account, watch time, average view duration, engagement, videos (views in range or to date), a collapsed *Compare similar videos*. **Followers**: growth over time, net change, gains and losses per account (where reported), videos that brought subscribers (YouTube only; others don't attribute). **An account**: its views, followers, watch time, engagement, trend and videos. |
| **Content** | **Concepts**: a gallery of produced videos on this PC that are waiting to be posted (thumbnails, length, language, status); language versions of one concept are grouped. **Published**: a gallery of posts, filterable by platform, account, language and date, sortable by newest, views or watch time; one video posted on several accounts is one card. | A concept: play it, see its file details, creative tags, where it's posted or queued, **Publish…**. A post: play it (if the edit is on this PC), open it on the platform, its numbers, readings at 24 h / 48 h / 7 d, history, the same video's other posts, the account's median, creative tags. |
| **Publish** | What needs you (drafts, failures, inbox and Buffer drafts), uploads in progress, posted jobs (collapsed), accounts (collapsed). | **New post**: pick a video from the gallery, preview, tick accounts (route per account under Advanced), create drafts. A draft: text and settings per platform, checks, approval (typed handle, TikTok declaration, reveal-lock confirmation). Route, file path and log are under Advanced. |
| **Roblox** | Before launch: one clean empty state listing what will appear. After: players now, daily, new and returning players, session length, D1 retention, revenue; players per day. | Retention (D1 line, cohort table), Acquisition (sources, share links), Monetisation (revenue, payers, payer conversion), Funnel (the seven stages, never divided into each other). |
| **Settings** | Collapsible sections: Appearance, Connected accounts, Service usage and quotas, Publishing, Credentials, Advanced and diagnostics. | Usage meters per service, labelled **Live** (provider-reported), **Estimate** (counted from our logs) or **Limit only** (published allowance; no usage API), with reset period, sign-in lifetimes and console links. |

Appearance: **System** is Jami's blue night (the owner's choice), **Dark** is black, **Light** is paper white. Jami's twinkling sky and shooting stars sit behind every page (ported from `components/constellation/NightSkyBackdrop.tsx`, `ShootingStars.tsx` and `lib/constellation/shooting-stars.ts`, read only); they can be switched off and stay still under reduced motion. Light mode uses opaque surfaces only: text on translucent layers lost ClearType antialiasing on Windows and looked grainy.

## Architecture

```
Edge app window / PWA ──HTTP (127.0.0.1 only, per-start token on writes)──► dashboard/server.py (Python standard library)
                                                                              │
     analytics.py (owner screens) · views.py (exports, Roblox, publishing) ◄── store.py: SQLite data/local/dashboard/slugshot.db (git-ignored)
                                                                              ▲
 sync.py ── connectors.py: YouTube Analytics · Instagram · TikTok Display · Roblox Analytics Query · Roblox public
 imports.py ── platform_metrics template (shared with `ss export`) · long template
 views.research() ── reads data/local/research/* and config/research/* in place (no copy)
 reports.py ── exports/share/dashboard/<snapshot>/ (safe) or data/local/dashboard/exports/ (private)
 vault.py ── DPAPI-encrypted tokens and keys in data/local/dashboard/vault/
```

**Why this stack:** the toolkit is Python standard library plus Node for Remotion. A standard-library server, SQLite and a build-free front end (one JS file, one CSS file, the Urbanist font vendored under SIL OFL) add **no new dependencies**, no build step and nothing to update. The design follows Jami (`jarems421/jami-flashcards`, read only): Urbanist, the violet accent, rounded panels and its night sky; the redesign uses 1 px borders, smaller radii and fewer nested containers. Thumbnails are cut locally with FFmpeg and cached in `data/local/dashboard/thumbs/`; videos play from `exports/` and `media/` only.

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

Owner screens (`analytics.py`, owner decision 2026-11-25):
- **Views are added across platforms**, labelled *combined, platform-reported*: not unique viewers, and each platform counts a view differently. **Followers** are combined account counts, not unique people. **Watch time** is added only over accounts that report it, and those accounts are named.
- YouTube periods come from daily analytics. TikTok and Instagram give lifetime totals per video, so a period's views are the growth between daily snapshots; views a video had before tracking began count only in *all time* (the period is marked partly measured).
- Each video's metric comes from one source: the native API first, then Buffer, then manual imports. Buffer only writes what the native API lacks, so nothing is counted twice.
- Missing stays missing (—), never 0. A comparison with the previous period appears only if both periods used the same basis, neither was partly measured, and, for daily reports, data began before the previous period and the previous period has at least 80% as many days with data. Otherwise no comparison is shown.
- Average view duration for a range uses the platform's daily figures where it reports them (YouTube): each day's average weighted by that day's views. Where only per-video lifetime averages exist (TikTok and Instagram via Buffer), the figure is labelled *lifetime*. The two are never blended.
- **Measurement windows:** videos are compared at 24 h (±6 h), 48 h (±8 h) and 7 days (±24 h) after posting; a reading outside the window is shown with a flag and left out of comparisons. Accounts with a video under 8 days old refresh every 4 hours so readings land close to those ages.
- **Comparisons** are within one platform (optionally one language) at one checkpoint, grouped by a creative tag; medians and ranges per group; groups under 3 videos are marked too small. Patterns across groups, not single viral videos.
- **Creative tags** (per concept): format and objective from the knowledge-bank vocabularies, hook and narrative codes from the creative codebook (`config/research/codebooks/slugshot-creative.json`), characters from the game's names in the caption glossary, humour and mechanism as knowledge-bank entry IDs.
- **Learning loop:** *Compare similar videos → Record finding* saves a **draft** knowledge-bank entry (bank `claims`, kind `observation`, evidence `owned_result`, linked to the concepts and optionally to an existing entry) in `data/local/research/knowledge/curated/owned_findings.jsonl`, checked by the bank's validator. `ss kb brief` then includes it for the next creative brief. Only the owner marks it approved.

Exports for AI tools (`views.py`, `reports.py`) keep platforms in separate files and never add across them; no conversion rates between funnel stages; player acquisition is never inferred from views and player numbers moving together.

## Synchronisation

Daily by default, every 4 hours for an account with a video under 8 days old (`young_refresh_hours`, `young_days`), and when the app opens if anything is due (Settings switch; `refresh_hours` 24, `stale_hours` 36). While the server runs it checks hourly; there is no OS scheduler. Manual: the refresh button or `ss dash sync`. Each connector × account runs separately: a failure is recorded with its message and the rest carry on. Requests retry with backoff on 429/5xx/network errors (never on 401/403, which mark the source "reconnect"); Roblox analytics queries that answer asynchronously are polled. Day-level data is re-read over the last 3 days and backfilled on first run (YouTube from `history_start`, Roblox 90 days, Instagram 7 days).

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
| Five pages, drill-downs, account pages, galleries, three appearances, star sky, phone layout | implemented; reviewed in screenshots with fixture data (populated) and the live database (empty states), `docs/dashboard/screens/` |
| Analytics rules, measurement windows, tags, comparisons, learning loop | implemented; 16 tests (`tests.test_analytics`) |
| Store, imports, exports, vault, server security; publishing | 33 and 27 tests |
| YouTube (EN, ES), TikTok (EN, ES), Buffer (TikTok EN/ES, Instagram EN) | **live-validated** 2026-11-25 (no posts yet, so only follower counts are live values) |
| Cloudinary hosting, Buffer draft creation from a hosted link | **live-validated** 2026-11-25 |
| Instagram API connector, Roblox Analytics | fixture-tested; Instagram deferred (Buffer covers it), Roblox waits for launch |
| Buffer post metrics, checkpoints, comparisons on real videos | need real posts |
| Activation stage | blocked: needs approved in-game events ([proposal](activation-events-proposal.md)) |

What the owner must do: [credentials-checklist.md](credentials-checklist.md).

## To revisit after real content is published

Known limits, left as they are on purpose (infrastructure is frozen); check them against real data:

- **Background refresh dependency.** The 4-hour refresh for young videos only runs while the dashboard server is running (it has no OS scheduler). If the PC is off or asleep around 24 h or 48 h after posting, that reading lands outside its window and is flagged rather than compared. If this happens often, decide whether to keep the server running after posting.
- **YouTube reporting delays.** YouTube Analytics usually lags by 1–3 days, and its most recent days fill in later. Ranges ending today undercount YouTube, and comparisons that include the last few days lean low. The 80% days-with-data rule catches large gaps, not this lag.
- **Small-sample comparisons.** Groups under 3 videos are flagged, but a median of 3–5 videos is still fragile. Treat comparisons as hypotheses for the next video, not conclusions, until groups are larger. Findings are saved as drafts with `exploratory` or `suggestive` strength for this reason.
- **Buffer pagination costs.** The Buffer sync reads sent posts 50 per request, up to 4 pages per account. With many posts and the 4-hour cadence, that could approach 4 requests × 3 accounts × 6 refreshes a day (about 2,100 a month) against the 3,000 free requests. Analytics pause below 150 left, so posting is protected. Watch the Buffer meter in Settings once posts accumulate.

## Integrations: adopted, deferred, rejected

| Option | Decision | Why |
|---|---|---|
| Official APIs direct (YouTube Analytics, Instagram Login, TikTok Display, Roblox Analytics Query) | adopted | free, owner-authorised, no third party sees private analytics |
| Existing `ss export` template, research store, evidence ledgers, `research_common` HTTP/redaction helpers | reused | one source of truth; nothing re-collected |
| Roblox legacy public games API | adopted (no key) | already live-validated in `ss rbx`; gives visits/playing/favourites |
| Composio | deferred | Instagram through it needs the same Meta OAuth, adds a third party and a plan cap; useful later only for a service with no direct API |
| TikTok API for Business / Business account | rejected for now | needs a Business account (Commercial Music Library only); the Display API plus Studio imports cover the need |
| Browser automation of Studio pages and account analytics collection outside authorised routes | rejected | provider terms |
| Google Drive / Claude Docs MCP for exports | deferred | files stay local; the owner uploads what they choose |
| Electron/Tauri app, hosting, login | rejected | the Edge app window and PWA give an app-style window with nothing to install or update |
| A charting or UI library | rejected | hand-drawn SVG charts (crosshair, tooltip, legend, table view) cover every chart here |
