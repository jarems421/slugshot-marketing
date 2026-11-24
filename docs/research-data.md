# Research data collection (Stage 4.4)

Built and tested 2026-11-24. This is the reference for the research collectors: what each one collects, the exact commands, the file schemas, what may go to ChatGPT, and what is still blocked. The decisions and evidence behind it are in [research-data-audit.md](research-data-audit.md). The YouTube rules are in [youtube-api-policy.md](youtube-api-policy.md).

**Split of work.** These collectors gather dated, raw, labelled data and nothing else. ChatGPT owns the query lists, watchlists and entity lists; it classifies concepts (emerging / accelerating / established / saturated / declining / unknown) and does all interpretation. The collectors never rank, score or classify, and never claim anything about fatigue, quality, demographics or conversion.

**How it's operated (automation first, 2026-11-24).** Claude runs everything below from a short instruction, using the `slugshot-research-operations` skill (`.claude/skills/slugshot-research-operations/`): it picks the collectors, runs them, handles quotas and errors, validates, builds one bundle and reports. The owner's part is reduced to what can't be delegated: Ctrl+A, Ctrl+C on Creative Center pages that Claude opens, an occasional sign-in, and uploading the bundle zip to ChatGPT. The command lists are Claude's reference; nothing here is scheduled.

## 1. Sources at a glance

| Source | Command | What you get | Language / region filters that really exist | Access | Status |
|---|---|---|---|---|---|
| YouTube Data API v3 | `ss yt` | dated public counts; regional most-popular gaming chart; creator uploads (ordinary ones included); comments; Shorts confirmation | `relevanceLanguage` = ranking hint only; `regionCode` = viewable in that country; creator-declared `defaultAudioLanguage` and channel `country` | API key (in `.env`, rotated and restricted, owner confirmed 2026-11-24) | **Live-validated** (chart, saved bilingual set, 2-page search, creator uploads, comments, Shorts check, quota log) |
| Wikimedia Pageviews | `ss wiki` | daily/monthly article views since 2015, en and es editions, redirects resolved | language edition only (not a country) | none | **Live-validated** |
| Google Trends: Trending Now RSS | `ss trends rss` | top trending searches per country (about 10 per feed), approximate traffic, start time, news links | country (search geography) | none | **Live-validated** (GB, US, MX, ES, AR, CO, CL) |
| Google Trends: Explore CSV | `ss trends import` | interest over time, by region, related/rising queries and topics, from files you download | whatever you chose in Explore (geo, subregion, window, category, search type) | manual download | **Tested on sample files** (the real file format must be confirmed with your first download) |
| Twitch Helix | `ss twitch` | clips (views, created time, broadcaster language) and live streams for Roblox or any category; broadcaster watchlist; repeat observations | broadcaster's stream-language setting | app credentials in `.env`; owner read the terms (24 h retention) | **Live-validated** |
| Roblox experience stats | `ss rbx` | current players, visits, favourites, votes, created/updated for up to 20 experiences | none | none (legacy API) | **Live-validated, experimental** |
| Public observations (TikTok, Instagram, Creative Center, vidIQ, TinyFish, manual) | `ss observe` | your or ChatGPT's observed values, validated, deduplicated by scope, with provenance; Creative Center link list and copy-paste parser | whatever the source showed (region filter, period, category) | none | **Tested** (fixtures and the 24 Nov Creative Center figures) |
| TikTok oEmbed | `ss observe import --oembed` | confirms a TikTok post exists and its ID matches. Since 2026-11-24 it returns **no author, title or stats** | none | none | **Live-validated** (limited use) |
| TikTok Discovery API | not built | see §7 | country filter | **requires a registered company**; see §7 | **Blocked (eligibility)** |
| Instagram Business Discovery | not built | competitor Business/Creator account counts incl. Reel `view_count` | none | needs a Slugshot Instagram professional account | **Deferred** |
| Google Trends API (alpha) | not built | see §8 | country and subregion | application | **Deferred** (apply if wanted) |

## 2. Commands

All run from the workspace: `.\ss <command>`. Add `-h` to any command for every option. Every collector also takes `--dry-run`, which uses fake fixtures with no network and no credentials.

```powershell
# One-instruction operations (what Claude runs for "collect today's research" and similar)
.\ss research collect --profile daily      # Trends 7 markets, YouTube Gaming charts per market, saved set 'daily', Twitch, creator/broadcaster lists, re-snapshots, Wikipedia, Roblox, then bundle
.\ss research collect --profile spanish    # MX ES AR CO CL; saved set 'spanish' or a labelled default 'roblox' search per market; Twitch es
.\ss research collect --profile refresh    # re-observe stored YouTube videos and Twitch clips, watchlists, Wikipedia, Roblox
.\ss research bundle                       # exports + prune + zip: exports\share\bundles\slugshot_research_<time>.zip
.\ss observe cc-session --regions US,GB,MX,ES,AR,CO,CL --periods 7 --category Games   # guided Creative Center (owner: Ctrl+A, Ctrl+C per page)

# Health
.\ss research status            # credentials present? (yes/no only), gates, stored rows, last runs, YouTube quota today
.\ss research prune             # apply every retention rule and delete expired exports
.\ss research runs              # the last runs and the exact parameters sent
.\ss smoke --research           # offline tests + small live checks -> reports\smoke-test-research.md (~20 s)

# YouTube (quota: 10,000 units/day + 100 search calls/day; budgets in config\research\settings.json)
.\ss yt discover "roblox pvp" --lang es --region MX --days 7            # 1 search call + 1 unit
.\ss yt discover "roblox humor" --lang es --region AR --after 2026-11-01 --before 2026-11-15 --pages 2
.\ss yt sweep --set test                                                 # every saved query in youtube_queries.json
.\ss yt chart --region MX                                                # most-popular Gaming chart for Mexico, 1 unit
.\ss yt creators --days 30                                               # every upload from youtube_creators.csv (1 unit / 50 videos)
.\ss yt comments --ids VIDEO1,VIDEO2 --max 20                            # 1 unit per video
.\ss yt stats --check-shorts                                             # re-snapshot the watchlist; confirm Shorts (1 unit per candidate)
.\ss yt report --history --comments                                      # -> exports\share\research\
.\ss yt quota                                                            # usage today (Pacific quota day)

# Wikipedia page views (free)
.\ss wiki resolve                                  # canonical titles, Wikidata IDs, redirects, other-language title
.\ss wiki pull --days 90                           # daily; or --granularity monthly --start 2015-07-01
.\ss wiki pull --all-redirects                     # also every known redirect (review known_redirects first)
.\ss wiki report

# Google Trends (free)
.\ss trends rss                                    # GB US MX ES AR CO CL (settings.json); or --geo MX,PE
.\ss trends import "$HOME\Downloads\multiTimeline.csv" --geo MX --window "past 12 months" --search-type web --downloaded-at 2026-11-24T18:00:00Z
.\ss trends imports                                # what's been imported
.\ss trends report

# Twitch (credentials in .env; 24 h retention)
.\ss twitch categories "Roblox"                    # Roblox = 23020
.\ss twitch clips --game Roblox --hours 24 --lang en,es --max 300
.\ss twitch clips --broadcaster somelogin --hours 72
.\ss twitch streams --game Roblox --lang es        # who is live in Spanish right now
.\ss twitch watch --hours 48                       # every broadcaster in twitch_broadcasters.csv
.\ss twitch recheck                                # new view counts for stored clips (run a few hours later)
.\ss twitch report                                 # LOCAL ONLY until twitch.share_exports = true

# Roblox experiences (legacy API; at most one run per 55 min)
.\ss rbx universe 2753915549                       # place ID (from roblox.com/games/<id>) -> universe ID
.\ss rbx games
.\ss rbx report

# Public observations (TikTok, Instagram, Creative Center, vidIQ, TinyFish, manual)
.\ss observe template --kind creative_center       # ready-to-fill CSV in data\local\research\observations\inbox\
.\ss observe check  file.csv                       # validate only
.\ss observe import file.csv --source creative_center --platform tiktok --entity-type hashtag --region US --period "7 days" --observed-at 2026-11-24
.\ss observe import chatgpt-table.md --source vidiq   # a Markdown table pasted from ChatGPT works as-is
.\ss observe list                                  # items with repeat observations
.\ss observe cc-links --periods 7,30 --open         # Creative Center hashtag pages per market + a session list
.\ss observe cc-paste page.txt --region US --period 7 --category Games   # copied page text -> checked CSV
.\ss observe report
```

## 3. The routine (no Claude needed)

A suggested rhythm. Nothing is scheduled; you run what you need.

| When | Run | Gives ChatGPT |
|---|---|---|
| Daily | `ss trends rss`, `ss yt sweep --set <set>`, `ss yt chart --region MX` (and other markets), `ss twitch clips --game Roblox --lang en,es` | what's new today, per market and language |
| 12–48 h later | `ss yt stats`, `ss twitch recheck` | a second observation of the same items, so per-item growth can be measured |
| Weekly | `ss yt creators`, `ss wiki pull`, `ss rbx games`, one set of Trends Explore downloads + `ss trends import` | creator baselines including ordinary uploads; fandom/game interest series; comparable-game player counts |
| Whenever you browse | paste what you saw into a CSV or Markdown table, then `ss observe import` | TikTok, Instagram and Creative Center evidence with provenance |
| Before uploading | every `report` command, then `ss research prune` | everything in `exports\share\research\`, with expired files removed |

Then upload the files in `exports\share\research\` (each CSV has a `_README.md` and a `.json` twin; `MANIFEST.csv` lists them) to ChatGPT. **Twitch reports stay in `data\local\research\twitch\reports\`** until `share_exports` is switched on (§6).

To change what is collected, edit `config\research\` (no code):

| File | What it controls |
|---|---|
| `settings.json` | budgets, Trends markets, Twitch gates and retention, Roblox limits, optional User-Agent contact |
| `youtube_queries.json` | named query sets: `query`, `lang`, `region`, `days` or `after`/`before`, `order`, `duration`, `max`, `pages`. Only a two-query `test` set exists now; ChatGPT writes the real bilingual sets |
| `youtube_creators.csv` | `channel_id` (UC…), `label`, `language_stream`, `notes` |
| `twitch_broadcasters.csv` | `login`, `label`, `language_stream`, `notes` |
| `wiki_entities.csv` | `entity_id`, `project` (en.wikipedia / es.wikipedia), `title`, `kind`, `notes`. Use the same `entity_id` for the same topic in both editions |
| `roblox_experiences.csv` | `universe_id`, `label`, `notes` (max 20) |

## 4. Data contract

Provider data stays in **separate files** (YouTube's no-merging rule; the other providers' terms differ). Every collector follows the same conventions:

- **Times:** ISO 8601 UTC with `+00:00` (provider values like `2026-11-20T15:00:00Z` are kept as given). `observed_at_utc` = when we read the value.
- **Missing = blank, never 0.** A real 0 stays 0.
- **`run_id`** on every row links to `data\local\research\runs.csv`, which holds the command, the exact parameters sent, requests that succeeded and failed, units used and rows written.
- **`expires_at_utc`** where a provider limits storage. `ss research prune` (and each collector's own runs) delete expired rows, and expired export files are deleted using `MANIFEST.csv`.
- **Provenance** (separate from the A/B/C/D/S evidence labels):

| Code | Meaning | Examples |
|---|---|---|
| P1 | first-party measured: the platform's own count, as returned or displayed (may be rounded) | YouTube API views, Twitch clip views, Wikimedia views, Roblox visits, a TikTok page's displayed likes, Creative Center post/view counts |
| P2 | first-party sampled or normalised: an index, rank or band | Google Trends 0–100, Trending Now traffic band, Creative Center rank, rank change |
| P3 | third-party reported or estimated | vidIQ views/VPH/breakout multiples, TTAnon/Wieldr figures |
| P4 | qualitative interpretation | hook, format description, a tool's or person's reading of a video |

**Language and region evidence never get merged.** Each file says exactly which kind it has:

| Concept | Where it appears | What it is NOT |
|---|---|---|
| Content language actually spoken | `content_language` + `language_evidence` in observations (only when a person or source recorded it) | never guessed from titles |
| Creator-declared language | YouTube `default_language`, `default_audio_language` | not verified speech |
| Broadcaster language setting | Twitch `language` | not verified speech or audience |
| Wikipedia language edition | `language_edition` | not a country |
| Ranking-language hint sent | YouTube `relevance_language_param` | not a filter |
| Creator location | YouTube channel `country_declared` (self-declared, often blank) | not audience |
| Search geography | Trends `geo` | not language or Roblox audience |
| Regional availability | YouTube `region_param` | not creator or audience location |
| A tool's region filter | observations `region` + `region_evidence=source_filter` | not audience geography |
| Actual audience geography | **nowhere**: only our own analytics can give it, after launch | |

## 5. Files and data dictionary

Raw stores (git-ignored) live in `data\local\research\<provider>\`. Exports go to `exports\share\research\<name>_<UTC time>.csv` with `.json` and `_README.md`. Every column is described in that README; the main ones are listed here.

### YouTube (`youtube_snapshots.csv`; report `youtube_report_*`, history `youtube_history_*`, comments `youtube_comments_*`)

Snapshot columns: `video_id, url, title, channel_id, channel_title, published_at, observed_at_utc, duration_s, duration_le_180s, shorts_status, shorts_evidence, views, likes, comments, category_id, default_language, default_audio_language, live_broadcast_content, tags, source, collection, query, region_param, relevance_language_param, published_after_param, published_before_param, category_requested, category_mismatch, run_id, expires_at_utc`.

- `shorts_status`: `confirmed_short` (the video is in the channel's auto-generated Shorts playlist, `UUSH…`); `not_in_shorts_playlist` (the playlist was read and the video isn't in it); `candidate` (3 minutes or shorter, not confirmed); `not_short_duration` (over 3 minutes); blank (unknown). The playlist is an undocumented YouTube convention read through the official API. Live tests: a known Short came back `confirmed_short`; 64 of 74 rows in the bilingual test run were confirmed; a channel without Shorts returned 404 and stayed `candidate`.
- **Category mismatches are kept and flagged.** In the 24 Nov Mexico and Spain Gaming charts (category 20), 2 of 19 videos had `category_id` 10 (Music). YouTube doesn't document why; one likely cause is a creator changing the category after the chart was built. Such rows are stored as returned with `category_mismatch=true`, and nothing is filtered out.
- **Rows vs observations vs contexts.** One stored row is written per discovery context. When the same video turns up in the MX and ES charts in the same minute, that's 2 rows but **1 observation** with the same numbers. The report has three columns for this:
  - `stored_rows`
  - `observations`: distinct moments; rows within `observation_merge_minutes`, default 10, count once
  - `discovery_contexts`: distinct collection/query/region/language combinations

  The history export marks same-moment rows `duplicate_context=true` and gives each row its `observation_moment`.
- **Growth** (`hours_since_prev`, `view_increase_since_prev`, `views_per_hour_since_prev`) is calculated only between two distinct observation moments at least `min_growth_hours` apart (default 1 h). Same-moment rows never produce growth. These columns are per-video arithmetic only; nothing compares videos or channels.
- Other report columns: `age_hours`, `first_seen_via`.
- Channels (`youtube_channels.csv`): `country_declared`, `default_language`, subscribers (blank when hidden), video count.
- Comments: `video_id, comment_id, published_at, like_count, reply_count, text, order_param, observed_at_utc`. **No author names or IDs** are stored.
- Quota log: one row per request, failed ones included, with the Pacific quota day.

Example (fixture data, fake):

```
video_id,...,shorts_status,shorts_evidence,views,likes,comments,...,first_seen_via,age_hours,snapshots,hours_since_prev,view_increase_since_prev,views_per_hour_since_prev
DRYRUN00002,...,confirmed_short,in the channel's Shorts playlist (UUSH),3100,,12,...,discover / roblox pvp / MX / es,80.9,3,...
```
(`likes` is blank because the fixture hides it, and it stays blank in the export.)

### Wikimedia (`wiki_pageviews.csv`, `wiki_resolved.csv`)

`entity_id, project, language_edition, article_title, title_role, canonical_title, page_id, wikidata_id, granularity, period_start, views, agent, access, observed_at_utc, run_id`. `title_role` is `canonical` or `redirect`: views of a redirect title are counted separately by Wikimedia, so es "Bajoterra" (a redirect to "Slugterra") gets its own rows. Canonical and redirect rows share `entity_id` and `wikidata_id`.

- **No double counting.** Each (edition, title) is fetched and stored once per date, even if it's listed twice or under two entities. A warning names the duplicate, and it's counted under the first entity. Re-pulling replaces the same period rather than duplicating it.
- **Missing, zero and failed are different** (`wiki_coverage.csv`, exported as `wikimedia_coverage_*`; one row per request):

| What you see | Meaning |
|---|---|
| a row with a number (including 0 if Wikimedia returns one) | the reported count |
| no row for a date, inside a request whose coverage `status` is `ok` | no views recorded that day (Wikimedia omits zero days) |
| coverage `status=no_data` | no views for the title in the whole window |
| coverage `status=failed` | the request failed: every date in that window is **unknown** |
| coverage `status=resolve_failed` | the title lookup failed (e.g. rate-limited), nothing was requested, so **unknown**. The next pull retries it automatically |
| coverage `status=not_found` | no such article on that wiki |

- **Topic totals (for ChatGPT).** For one edition and one date: sum `views` over rows with the same `entity_id`, `project` and `period_start`, across `title_role` canonical and redirect. Only do this where every title's window is `ok` (otherwise the total is a lower bound or unknown). Line up editions by `wikidata_id`, but report editions separately, never added together as if they were one country.
- **Which redirects.** By default only titles listed in `wiki_entities.csv` are pulled, so list the alias spellings you care about (e.g. es "Bajoterra" and "BajoTerra"). `ss wiki pull --all-redirects` adds every redirect Wikipedia knows (`known_redirects` in `wiki_resolved.csv`). Review that list first: Roblox's 49 redirects include separate subjects ("Robux", "MeepCity", "Roblox Innovation Awards") that would inflate a "Roblox" total. Live test: Slugterra with all redirects added en "List of Slugterra characters" (31 days), and es "BajoTerra" (27 days) outnumbered "Bajoterra" (20 days).
- Requests are paced and retried on 429/503. Wikimedia rate-limited a burst of about 60 requests live; those were logged as `failed`, not stored as zeros.

Example (live, open data): `roblox,en.wikipedia,en,Roblox,canonical,Roblox,18514671,Q692989,daily,2026-11-20,7201,user,all-access,...`

### Google Trends (`trending_now.csv`, `explore_values.csv`, `explore_imports.csv`)

- Trending Now: `geo, position, term, approx_traffic, approx_traffic_lower_bound, trend_started_at_utc, news_titles, news_urls, news_sources, observed_at_utc`. `position` is feed order, not an official rank. These are all searches in the country, not gaming searches. Rows are kept 90 days (a local choice: Google states no limit). Each export's `expires_at_utc` is its oldest row's expiry, so exported copies follow the same rule.
- Explore values (long format): `import_id, export_type, term, geo, geo_label, window, category, search_type, period, region_name, section, query, value_raw, value_numeric, value_kind, downloaded_at_utc`. `value_kind`: `index_0_100`, `less_than_one` ("<1"), `percent_increase` ("+250%"), `breakout`, `missing`. **Each `import_id` has its own 0–100 scale**; values from different downloads are never comparable as absolute numbers. `explore_imports.csv` records the file hash (re-imports are skipped), the `normalisation_scope` sentence, and warnings for anything you didn't specify (geo, search type, window, download time).

Example (fixture): `gt-0f6ce6f3eed5,interest_over_time,Bajoterra,MX,Mexico,2026-10-04 to 2026-10-18,All categories,web,2026-10-04,,,,<1,,less_than_one,...`

### Twitch (`twitch_clips.csv`, `twitch_streams.csv`)

Clips: `clip_id, url, broadcaster_id, broadcaster_name, video_id, game_id, language, title, view_count, created_at, duration_s, vod_offset, is_featured, observed_at_utc, collection, query, window_start, window_end, run_id, expires_at_utc`. Streams: `stream_id, user_id, user_login, user_name, game_id, game_name, language, title, viewer_count, started_at, is_mature, tags, observed_at_utc, query, run_id, expires_at_utc`. **Clippers' names and IDs aren't stored.** Rows expire after `retention_hours` (24). Twitch returns at most about 1,000 clips per query, and the collector splits windows longer than 7 days. Live test: 40 Roblox clips from the last 12 h, of which 33 were en/es (30 en, 3 es); 10 Spanish-language live Roblox streams.

### Roblox (`roblox_experiences.csv`)

`universe_id, label, root_place_id, name, creator_name, creator_type, playing, visits, favorited_count, up_votes, down_votes, max_players, genre, created_utc, updated_utc, observed_at_utc, source_stability(=legacy_unstable), run_id`. `playing` is a point-in-time concurrent figure and may not cover every place in a multi-place experience.

### Public observations (`public_observations.csv`)

Long format, one row per item × metric × observation: `obs_key, import_id, platform, entity_type, content_key, content_id, url, creator_handle, creator_name, title_or_name, published_at_utc, observed_at_utc, observed_precision, source, collected_via, provenance, region, region_evidence, period, category, metric, value_display, value_numeric, value_rounded, metric_definition, content_language, language_evidence, sample_role, concept_id, meme_id, sound_id, format_id, genre_id, notes, source_url, oembed_checked, imported_at_utc`.

**Input is forgiving:**
- CSV, TSV or a Markdown table pasted from ChatGPT. `[text](url)` links and `**bold**` are unwrapped.
- Column names are matched loosely: "Views", "View count", "Link", "Hashtag", "Observed", "Posted", "Creator" and similar all work.
- Only these are needed per row: something identifying the item (a URL, an ID, or a name/hashtag), an observation date, and a source. Options such as `--source`, `--platform`, `--entity-type`, `--region`, `--period`, `--category`, `--observed-at` and `--source-url` fill those for every row.
- Platform, entity type, IDs and handles are taken from URLs (TikTok posts, sounds, tags, profiles; Instagram reels and posts; YouTube watch, shorts and youtu.be; Twitch clips; Roblox games).

Metric columns: `rank, rank_change, views, likes, comments, shares, saves, posts, followers, plays, videos_using_sound, breakout_multiple, views_per_hour, engagement_rate`. Interpretation columns (stored as P4): `hook, format_description, interpretation, audience_note`.

**Strict about data:**
- Blanks, "-", "—" and "n/a" stay blank. "24.5K" is stored as shown and as 24500 with `value_rounded=true`.
- Ambiguous dates (03/04/2026), relative dates ("3 days ago"), dates in the future, unknown sources, non-numbers, and a URL that contradicts the platform are all errors that name the row and the fix.
- A file with any error is refused unless you pass `--skip-bad`.
- Ranks are always P2, `breakout_multiple` is P3, and interpretations are P4.
- `metric_definition` is `unknown` unless the row lists the metric in `metric_definitions_verified` (for example `views|posts`).
- **The duplicate key includes the observation's scope:** item, metric, source, observation time, `region`, `period` and `category`. So #huss at US/7 days, GB/7 days, US/30 days and US/7 days/Games on the same day are four observations. Exact repeats are skipped; a different value for the same key is reported as a conflict; the same item at a new time is kept as a repeat observation.
- Placeholder text ("—", "n/a", "unknown") means blank in **every** column, not just in metrics.

### Creative Center: guided session (the least the owner has to do)

What was investigated (2026-11-24):
- **Automated access:** not permitted (TikTok's commercial terms) and not technically available here: no browser-control tool (Claude in Chrome, built-in browser, computer use) is connected in this VS Code session.
- **Exports:** none seen on the page.
- **TinyFish (ChatGPT):** reached the US 7-day table, but detailed analytics needed a login.

So `ss observe cc-session` reduces the owner's part to two keystrokes per page. Claude opens each market/period page in the owner's normal browser and watches the clipboard. When the owner presses Ctrl+A, Ctrl+C, Claude:
1. saves the text;
2. parses rank, hashtag, posts and views;
3. imports the rows with region, period, category, URL and time;
4. opens the next page.

Clipboard text that doesn't parse as a hashtag list is ignored and not stored. The loop was tested with simulated copies; the real page layout is confirmed on the first real session.

### Creative Center: making the manual route quick

TikTok's terms rule out automated collection (§7), so the tools speed up the human steps instead. Nothing here fetches TikTok pages.

```powershell
.\ss observe cc-links --periods 7,30 --open          # opens the hashtag page for each market and period; writes a session list
# On each page: pick the industry (e.g. Games) if you want it, scroll so the rows load, Ctrl+A, Ctrl+C,
# paste into the .txt file named in the session list (data\local\research\observations\inbox\), save.
.\ss observe cc-paste data\local\research\observations\inbox\cc_US_7d_20261124.txt --region US --period 7 --category Games
#   -> parses rank, #hashtag, posts and views (English or Spanish UI; one value per line or "24.5K Posts")
#   -> prints a preview to compare with the page, writes a prefilled CSV (source, region, period, category, URL, time)
.\ss observe import data\local\research\observations\inbox\cc_US_7d_20261124.csv    # or add --import to cc-paste
```

- Values are kept exactly as displayed ("24.5K", "12,3K"). Anything the parser can't read stays blank and is listed in `notes` ("unparsed text: ...").
- The parser was built from the layout ChatGPT described and tested on fake samples. **Confirm it on your first real paste** by comparing the preview with the page.
- The observation time defaults to when the paste file was saved; pass `--observed-at` to set it.
- Only the hashtag URL pattern (`.../trends/hashtag?region=US&period=7`) is verified. For songs, creators and videos pages, copy the text the same way, then add rows with `ss observe import`.
- `sample_role` (`featured`, `ordinary`, `failed`, `unknown`) marks whether an example was picked because it did well, which helps reduce survivorship bias.
- `concept_id`, `meme_id`, `sound_id`, `format_id` and `genre_id` keep a specific joke, its audio, its story structure and its genre as separate entities (for example Huss, the Huss sound, In This Town, Roblox animation). ChatGPT fills them in.

The template is `data\templates\public_observations_template.csv`. The examples in `data\templates\examples\` are Creative Center hashtags (the 24 Nov US figures), an Instagram post via TinyFish, vidIQ rows, and a ChatGPT Markdown table.

Example row: `tiktok:hashtag:huss|views|creative_center|2026-11-24T00:00:00+00:00, …, tiktok, hashtag, …, #huss, …, day, creative_center, tiktok_creative_center, P1, US, source_filter, 7 days, …, views, 71.6M, 71600000, true, unknown, …`

## 6. What ChatGPT (and Google Drive) may receive

| Data | To ChatGPT for internal analysis | Google Drive | Notes |
|---|---|---|---|
| YouTube reports, history, comments | **Yes**: owner decision 2026-11-24 (the policy is silent on AI tools) | Only as a working copy that is deleted by its expiry date. Never in a permanent knowledge bank | 30-day limit applies to every copy (each export's README and MANIFEST show the date); no publishing |
| Wikimedia | Yes | Yes | open data |
| Google Trends RSS + Explore | Yes | Yes | Google's terms of service; values are relative |
| Twitch clips and streams | **Not yet**: reports stay local until `twitch.share_exports` is true | No | the owner confirmed the 24 h storage reading; onward transfer to third parties hasn't been reviewed. When it has, set `share_exports` to true, and copies still expire after 24 h |
| Roblox experience stats | Yes | Yes | legacy public endpoint; label as unstable |
| Public observations | Yes | Yes | figures were already seen in public pages or tools; vidIQ figures stay labelled P3 |
| Credentials, `.env`, `data\local\research\runs.csv` | **Never** | Never | runs.csv contains no secrets but is internal |

Rule of thumb: ChatGPT can keep **lessons, concepts and source references** permanently. It should not keep restricted raw statistics (YouTube, Twitch) beyond their expiry. Re-run the collector instead of reusing old numbers.

## 7. TikTok: findings (2026-11-24)

**Bottom line:** no legitimate, free, bulk source of TikTok trend or post statistics is open to us now. The Discovery API would be the best fit, but TikTok only onboards companies. The practical setup is: Creative Center and public pages viewed by a person (or by ChatGPT's TinyFish at the owner's discretion), recorded with `ss observe import`; vidIQ for selected concept and sound work; and own-account analytics after launch.

### Discovery API (TikTok API for Business, Organic API)

Read from TikTok's own documentation ([overview](https://business-api.tiktok.com/portal/docs?id=1825127469285442), [endpoint group](https://business-api.tiktok.com/gateway/docs/index?doc_id=1825119005427714)):

| Endpoint | Returns | Filters / limits | Authorisation |
|---|---|---|---|
| `/discovery/trending_list/` (popular hashtags) | top 200: `hashtag_id`, `hashtag_name`, `rank_position`, `rank_change` (incl. `NEW`), region+period `views` and `posts`, global lifetime views/posts, `top_country_list` (5), `trending_history` (up to 30 days: daily rank, daily views; null if under 1,000) | `country_code` (location codes incl. GB, US, MX, ES, AR, CO, CL, PE), `date_range` 1/7/30/120 days, industry `category_name` (incl. `GAMES` > `VIDEO_GAMES`) | **advertiser access token** from an authorised **ad account** |
| `/discovery/detail/` | the same per hashtag, plus `hashtag_status` and `audience_insights` (age bands 18-24, 25-34, 35+; TikTok-estimated) | same | advertiser token |
| `/discovery/video_list/` | top 20 videos per hashtag (up to 10 hashtags): `video_id`, `embed_url`, `share_url` only, **no statistics or dates** | country, date range | advertiser token |
| `/discovery/cml/trending_list/` | popular **Commercial Music Library** tracks: name, artist, genres, rank, 30-day rank history, preview URL | country, genre, 1/7/30/90 days | **TikTok account token** with Accounts API permissions |
| `/discovery/cml/video_list/` | top 20 videos per CML track (IDs and URLs only) | country | TikTok account token |
| `/discovery/trending/search/` and `/trending/search/keyword/` | 20 trending or recommended search keywords | optional personalisation; no country parameter documented | TikTok account token with `discovery.search.words`; the account must have **Advanced Access or be a Verified Business Account** |

**Eligibility.** This is the blocker:
- Developer registration requires a **verified company-domain email** and a **company website** on a domain the company owns. TikTok's page says: "Currently, we are unable to onboard personal accounts or individual developers" ([register as a developer](https://business-api.tiktok.com/portal/docs?id=1738855176671234)). Review takes about 3 business days.
- Each developer app is then reviewed (2–3 business days). Since 20 March 2026, an **Accounts API Access Application Form** is needed for any app that requests the TikTok Accounts scope, which the music and search-keyword endpoints use ([create a developer app](https://business-api.tiktok.com/portal/docs?id=1738855242728450)).
- Hashtag endpoints need an **ad account** to authorise the app. Creating an ad account doesn't itself require spending, but it is a TikTok For Business advertiser account.
- No price is documented. Quotas weren't stated on the endpoint pages.

**Fit.** The music endpoints cover only the Commercial Music Library (licensed tracks), not trending original sounds or meme audio. The video lists have no counts or dates. Audience ages are TikTok estimates (P2 at best), never facts.

**Recommendation: don't apply now.**
- Revisit once Slugshot has a company identity: a company domain, email and website.
- If that happens, the order would be: TikTok For Business account → developer registration → app with the Discovery scopes → ad-account authorisation → `ss tiktok` (about half a day's work, same pattern as Twitch).
- Applying as an individual, or presenting a personal site as a company, would breach TikTok's stated requirements.

### Other official TikTok products

| Product | Research operations | Verdict |
|---|---|---|
| **Creative Center** (ads.tiktok.com/creative) | trending hashtags, songs, creators and videos; regional filters (US and others), 7/30/120 days, industry filters incl. Games; detailed analytics need a login; no export seen | **Use manually, with helpers:** `ss observe cc-links` opens every market/period page, and `ss observe cc-paste` turns copied page text into a checked CSV (§5). Automated collection is **not recommended**: TikTok's commercial terms bar "use automated scripts to collect information from or otherwise interact with the TikTok Commercial Technology" ([Commercial Terms of Service](https://ads.tiktok.com/i18n/official/policy/commercial-terms-of-service); clause text via a September 2026 third-party capture, so confirm in a browser). Browser automation (Claude in Chrome, Playwright MCP, Chrome DevTools MCP) driving Creative Center would be that kind of automated collection, so **nothing was installed**. A person reading the page, or ChatGPT/TinyFish reading a single page at the owner's direction, is a judgement for the owner. Don't build scheduled or bulk browser extraction |
| **Creator Search Insights** (in the TikTok app / TikTok Studio) | search topics viewers want, with "content gap" labels, for logged-in creators | **Manual** via a Slugshot TikTok account; record with `--source creator_search_insights` (P2) |
| **TikTok One** (creator marketplace) | creator discovery and audience data for brands running creator campaigns | **Deferred**: aimed at paid creator campaigns; terms bar automated collection |
| **TikTok for Business MCP server** | about 400 tools for ad campaigns, reporting, audiences and creatives ([help page](https://ads.tiktok.com/resources/help/article/about-tiktok-for-business-mcp-server?lang=en)) | **Reject for research**: ads management only, no organic trend tools |
| TikTok "Social"/content MCP | no official one found | n/a |
| Display API / Login Kit | our own account's videos and stats after OAuth | **Later**, for Slugshot's own TikTok |
| Research API | public videos and accounts | **Ineligible**: academic/non-profit only, "independent of commercial interests" |
| Commercial Content API | ads library (EU) | **Reject**: ads, not organic trends |
| oEmbed | post exists + ID (no author/title/stats since this test) | **Optional check** in `ss observe` |

**Compared with ChatGPT's TinyFish.** TinyFish already reads single public pages for ChatGPT. A local browser integration would duplicate that and run into the same terms clause. Recommendation: keep TinyFish for one-off page reads you direct, keep vidIQ for selected TikTok concept and sound queries (credits only with owner approval), and send all of it through `ss observe import` so it gets provenance, dates and duplicate checks.

## 8. Google Trends API (alpha): if access is granted

**The owner has applied (application submitted, as of 2026-11-24); no access has been granted yet.** The application form is at [developers.google.com/search/apis/trends](https://developers.google.com/search/apis/trends). The page lists a 5-year rolling window, daily to yearly aggregation, country and subregion breakdowns, and **consistently scaled values** (not re-normalised 0–100 per request). Rising or related queries, quotas and price aren't stated. If approved:
1. Put the credential Google issues into `.env` (e.g. `GOOGLE_TRENDS_API_KEY=`), never into chat.
2. Add `trends api` to `scripts/trends_collect.py`. It writes the same long-format `explore_values.csv` with `export_type=api_timeseries`, `value_kind=api_scaled`, provenance P2 and an `import_id` per request batch, so manual CSV and API rows never mix scales.
3. Keep the manual CSV import for related and rising queries if the API doesn't provide them.

## 9. Credentials and accounts

| Item | Status | Owner action |
|---|---|---|
| `YOUTUBE_API_KEY` | present; owner confirmed rotated and restricted to YouTube Data API v3 (2026-11-24) | none. Keep billing off |
| `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET` | present; `terms_reviewed` set true on the owner's confirmation (24 h retention) | before sharing Twitch exports, check the agreement's onward-transfer terms, then set `twitch.share_exports` to true |
| `contact` in settings.json | empty | optional: a contact URL or address you're happy to send to Wikimedia/Google/Roblox in the User-Agent |
| Google Trends alpha | **application submitted** by the owner (2026-11-24) | wait for Google's reply; then follow §8 |
| TikTok Discovery | not possible as an individual | only with a company identity (§7) |
| Instagram Business Discovery | deferred | once a Slugshot Instagram Business/Creator account exists: link a Facebook Page, create a Meta app (Business), give it `instagram_basic`, `instagram_manage_insights` and `pages_read_engagement` in development mode, then ask Claude to build `ss ig` |

Credentials are read from `.env` at run time. They're never printed, logged or written to exports, and errors are redacted. `ss research status` only says present or missing.

## 10. Limits to state plainly

- No source gives competitors' retention, shares (except where a page shows them), reach or audience geography.
- YouTube search covers what YouTube chooses to return. `order=date` (the default now) reaches ordinary uploads better than `viewCount`, but it isn't a census, and selective discovery feeds can't serve as a denominator for "how many videos use format X".
- Trending Now gives about 10 terms per country per read, so repeated reads are needed for a picture of the week.
- The Explore CSV parser was built for Google's documented export layout and tested on sample files; confirm it with your first real download (it rejects files it can't read rather than guessing).
- Roblox's endpoint is legacy and may break. The collector stops and stores nothing if it does.
- Twitch retention is a conservative reading the owner confirmed on 2026-11-24, not a legal opinion.
