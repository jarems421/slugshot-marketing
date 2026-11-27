# Stage 4.4: research data collection audit and plan

> Historical audit. We have permission to use Apify for the toolkit's TikTok collection. A person reads Creative Center. See the [current data guide](../research-data.md).

Written 2026-11-24, before any code changes. It covers the existing YouTube collector, every proposed source, the smallest implementation worth building, and what the owner has to set up. Facts were checked against official pages on this date unless a line says otherwise. Where only third-party or forum sources were available, the line says so. This is a careful reading of the terms, not legal advice.

Live checks run for this audit, with no credentials: Wikimedia pageviews (Slugterra en/es, Bajoterra es), Google Trends "Trending Now" RSS (GB, ES, MX) and the Roblox `games.roblox.com/v1/games` endpoint all returned real data. No YouTube, Twitch, Meta, TikTok or vidIQ calls were made.

## 1. Audit of what exists

`scripts/yt_collect.py` (303 lines, standard library only, run as `ss yt`):

| Capability asked for | Current state | Gap |
|---|---|---|
| EN / ES queries | `discover QUERY` takes any query text | No `relevanceLanguage`. No saved query sets, so each language/region query is typed by hand |
| Country | `--region` (default `GB`) sent as `regionCode` | `regionCode` only means "viewable in that country" (official docs). It is not the creator's country or the audience. The value isn't stored with the snapshot, only the query text |
| Date windows | `--days N` -> `publishedAfter` | No `publishedBefore`, so no fixed or historical windows |
| Recent discovery | Yes: `search.list`, then `videos.list` | `search.list` has only 100 calls a day, and sorting by view count only finds the winners (survivorship bias) |
| Creator watchlists | A flat list of video IDs (`youtube_watchlist.txt`) | No list of channels. A creator's ordinary uploads are never collected |
| Per-video snapshots | Yes: views, likes, comments, duration, 30-day pruning, blank when missing | Doesn't store `defaultAudioLanguage`, `defaultLanguage`, `categoryId` or tags. No run ID |
| Permitted comparisons | Same video, previous snapshot only | Fine. It is the policy limit. `report` drops all history except the last two snapshots |
| Quota | Logs estimated units | No daily budget check before a run |
| CSV / JSON exports | CSV report with a data dictionary | No JSON. No long-format export of observations |
| Comments | None | `commentThreads.list` costs 1 unit and is allowed. It needs its own retention rules |
| Captions | None | **Not obtainable** for other people's videos: `captions.download` requires OAuth and edit permission on the video. Reject. Use Gemini on authorised viewing instead |
| Policy safeguards | 30-day storage, per-video maths only, no cross-channel scores, no merging | Keep all of them unchanged |
| Key exposure | Documented as outstanding in `youtube-api-policy.md` | **Still unconfirmed.** No live collection until the owner confirms rotation and restriction |

Other existing pieces: `scripts/export_metrics.py` validates hand-entered metrics for **our own** uploads (`platform_metrics.csv`). There is no template for **public observations of other people's posts** (TikTok, Instagram, vidIQ, TinyFish). `data/local/` currently holds only dry-run data.

## 2. Source-by-source assessment

Decision key: **Adopt** = build now. **Test** = build small and check it with real data before relying on it. **Defer** = useful, but blocked on an account or approval. **Reject** = not legitimate, not sustainable or not worth it.

### 2.1 YouTube Data API v3 (extend the existing collector): Adopt

| Item | Finding |
|---|---|
| Contributes | Bulk, dated, first-party public counts for EN and ES Roblox content. Regional "most popular" charts. Full upload histories for creators on a watchlist, including their ordinary videos. Viewer comments for reading the language people use |
| Fields | Video: id, title, description, tags, channelId/Title, publishedAt, categoryId, `defaultLanguage` and `defaultAudioLanguage` (declared by the creator), duration, viewCount, likeCount, commentCount. Channel: title, `country` (declared by the creator, often blank), uploads playlist ID, subscriber/video counts. Comment thread: text, like count, published time, reply count |
| EN / ES | `relevanceLanguage=en/es` (a ranking hint, not a filter, per the docs). `regionCode` = viewable in that country. `videos.list chart=mostPopular&regionCode=MX&videoCategoryId=20` = that region's popular gaming chart (1 unit). None of these show where the audience is |
| Access | The existing API key. No OAuth needed for public data |
| Cost / quota | Free. 10,000 units/day; `search.list` has its own 100 calls/day; `videos`, `channels`, `playlistItems` and `commentThreads` cost 1 unit each; `captions.list` 50 ([quota table](https://developers.google.com/youtube/v3/determine_quota_cost)) |
| History | Only from our own repeated snapshots, kept at most 30 days. No historical view series exists in the API |
| Policy | Unchanged: [Developer Policies](https://developers.google.com/youtube/terms/developer-policies) III.E.4 (30 days, no derived scores), III.E.2.a (no aggregation across owners). Comments are API data too: 30-day limit, plus personal-data minimisation (store no author channel IDs) |
| Complexity | Low. Same file, same patterns |
| Docs | [search.list](https://developers.google.com/youtube/v3/docs/search/list) · [videos.list](https://developers.google.com/youtube/v3/docs/videos/list) · [playlistItems](https://developers.google.com/youtube/v3/docs/playlistItems/list) · [commentThreads](https://developers.google.com/youtube/v3/docs/commentThreads/list) · [captions.download](https://developers.google.com/youtube/v3/docs/captions/download) |

Pulling a creator's uploads through their uploads playlist costs 1 unit per 50 videos and doesn't touch the 100-call search allowance. That makes a creator watchlist the cheapest way to collect ordinary and failed examples, which reduces survivorship bias.

### 2.2 Twitch Helix: Test (after the owner registers an app)

| Item | Finding |
|---|---|
| Contributes | Streamer culture: which Roblox moments viewers clip, who streams Roblox in EN/ES right now, and clip view growth over hours |
| Fields | Get Clips: id, url, broadcaster id/name, clipper id/name, video_id, game_id, **language**, title, **view_count**, **created_at**, duration, vod_offset, is_featured. Get Streams: user, game, language, title, viewer_count, started_at. Search Categories gives the Roblox `game_id` |
| EN / ES | `language` is the broadcaster's chosen stream language, returned on each clip. Get Streams accepts a `language` filter; Get Clips can only be filtered by language after download. No country or audience data |
| Access | Twitch account with 2FA, an app registered in the developer console, client-credentials (app) token. No user OAuth needed for public clips and streams |
| Cost / quota | Free. Points bucket per app (the docs show `Ratelimit-Limit: 800` per minute as a sample header); about 1,000 results maximum per clips query, split by time window |
| History | Clips can be queried by `started_at`/`ended_at` windows, so past clips are reachable. Only current view counts exist; growth has to come from our own repeat snapshots |
| Policy | The [Developer Services Agreement](https://legal.twitch.com/legal/developer-agreement/) text couldn't be fetched automatically (it is rendered by script). Twitch staff on the [developer forum](https://discuss.dev.twitch.com/t/storage-of-data-from-twitch-api/63884) (July 2025) refer to a 24-hour storage limit for data about users who haven't authorised your app through OAuth. **Plan: keep Twitch snapshots at most 24 hours by default**, which still allows 2–3 observations per clip. The owner should read the live agreement and confirm before any longer retention. Don't download clip media |
| Complexity | Low to medium: a token step, otherwise the same pattern as YouTube |
| Docs | [API reference](https://dev.twitch.tv/docs/api/reference/) · [Get Clips](https://dev.twitch.tv/docs/api/reference/clips) · [rate limits](https://dev.twitch.tv/docs/api/guide/) · [register an app](https://dev.twitch.tv/docs/authentication/register-app/) |

### 2.3 Google Trends

| Route | Contributes | Access / cost | Decision |
|---|---|---|---|
| **Official Trends API (alpha)** | 5-year rolling window, daily to yearly aggregation, country and sub-region, consistently scaled values (not 0–100 per request), many terms at once. Rising or related queries are **not mentioned** on the page | Invite-only alpha with an application form; no published price, quotas or criteria. Google prioritises "a clear use case", readiness to start, and willingness to give feedback ([official page](https://developers.google.com/search/apis/trends)). Third-party reports say approvals are slow and patchy | **Apply (owner), don't depend on it** |
| **Trending Now RSS** (`trends.google.com/trending/rss?geo=XX`) | Daily trending searches per country with approximate traffic ("500+"), start time and linked news. It is the Export > RSS option on Trends' own Trending Now page. Tested live for GB, ES and MX | No key, free | **Adopt**: snapshot GB, US, MX, ES, AR, CO, CL |
| **Explore CSV download** (manual) | Interest over time, interest by sub-region, related and rising queries and topics, for any term, geo and window | Free, manual in the browser | **Adopt as a manual import** with recorded terms, geo, window and download time. Each download is scaled 0–100 against its own terms and window, so numbers from different downloads must not be compared |
| pytrends and similar unofficial libraries | Same data through private endpoints | Unofficial; the repo was archived in 2025; 429 blocks | **Reject** (fragile and not an approved route) |

Trending Now covers all searches, not just gaming. It shows what is culturally loud in a country this week, not Roblox demand. Sub-region interest exists only in the manual CSV or the alpha API.

### 2.4 Wikimedia Pageviews API: Adopt (new, not in the brief)

| Item | Finding |
|---|---|
| Contributes | Free, daily, historical interest series for fandoms, games, anime, streamers and memes that have articles, split by **language edition**. The best free historical signal available for Slugterra/Bajoterra |
| Fields | project, article, timestamp, views, with daily or monthly granularity; agent=user excludes known bots |
| EN / ES | Per wiki edition (en, es). **An edition is not a country**: es.wikipedia readers include Spain and Latin America together. Live check: es.wikipedia "Slugterra" had 1,194–1,653 views a month (May–Oct 2026), and "Bajoterra" (a redirect title) only 5–12. Redirect titles must therefore be resolved to their target before anyone reads them as low interest |
| Access / cost | No key. A descriptive User-Agent is required. Free |
| History | Daily data from July 2015 |
| Policy | Wikimedia [API etiquette](https://wikitech.wikimedia.org/wiki/Analytics/AQS/Pageviews); pageview data is published as open data |
| Docs | [Pageviews API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html) |

### 2.5 Instagram (Meta Graph API, Business Discovery): Defer until Slugshot has an Instagram professional account

| Item | Finding |
|---|---|
| Contributes | Public stats on competitor and creator posts, Reels included, for accounts we name |
| Fields | Target account: username, followers_count, media_count and other public profile fields. Each post: id, `like_count`, `comments_count` and **`view_count`**. Meta says the view count "includes both paid and organic metrics", so it is not organic reach. Also timestamp, caption, permalink and media_product_type (check against the IG Media reference). Missing: shares, saves, retention, reach, audience |
| Which accounts | **Targets must be Business or Creator accounts.** Personal accounts and age-gated accounts return nothing. Many small creators use personal accounts, so coverage will be patchy |
| Access | Our **own** Instagram Business or Creator account linked to a Facebook Page, a Meta developer app, and a Facebook User token with `instagram_basic`, `instagram_manage_insights` and `pages_read_engagement` ([reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery)). For an app used only by its own admins in development mode, App Review is normally not needed; confirm in the app dashboard |
| Competitor vs own | Business Discovery = other accounts' **public** counts. Our own Reels' reach, watch time and shares come from Instagram Insights, under different rules. Keep the two in separate files |
| Cost / quota | Free. Business Use Case rate limits apply (shown in the app dashboard) |
| History | Current counts only, so build series from our own snapshots |
| Policy | Meta Platform Terms: data minimisation, delete on request or when no longer needed, no selling or transfer. To be read in full before the build |
| Complexity | Medium, mostly account setup. The code is small |
| Docs | [Business Discovery guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery) · [IG Media](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/) · [Platform Terms](https://developers.facebook.com/terms/) |

### 2.6 TikTok: no sustainable free bulk source exists

| Option | What it gives | Decision |
|---|---|---|
| Research API | Public videos, users, comments and hashtags, with history | **Reject.** For academic and non-profit researchers only, "independent of commercial interests" ([official page](https://developers.tiktok.com/products/research-api/)). Game marketing is commercial, and a personal university affiliation doesn't change that |
| Commercial Content API | Ads and commercial content in the EU (an ad library) | **Reject** for organic trends. It covers ads only |
| Display API / Login Kit | Videos and stats for **accounts that log in to our app** | **Defer** to the own-account stage (use it for our own TikTok analytics) |
| oEmbed (`tiktok.com/oembed?url=`) | Title, author name and handle, thumbnail for one public URL. No stats | **Test (optional)**: checks the canonical ID and author on manually logged rows |
| Creative Center (trends, sounds, hashtags, creators) | Regional top hashtags, songs and creators, 7–120 day windows, some trend curves | **Adopt as a manual workflow.** No public API; parts need a login. Record observations in the public-observations CSV |
| vidIQ TikTok/Reels concept search and sound tracker | Concept, hook and format discovery; sound growth | **Keep for selective use** (existing decision; no new credits without owner approval) |
| Unofficial libraries (e.g. TikTok-Api), Apify-style scrapers | Bulk public stats | **Reject**: unauthorised automated access and fragile |

Conclusion: nothing legitimate and free replaces vidIQ for TikTok. The workable mix is manual Creative Center and public-page observations in a validated CSV, selective vidIQ, and the Display API for our own account later.

### 2.7 Roblox public experience stats: Test (small watchlist, labelled unstable)

| Item | Finding |
|---|---|
| Contributes | Current players and total visits for comparable experiences (Rivals, Throw Food for Animals and others), so a TikTok spike can be set next to the game's player count at the same time |
| Fields | `games.roblox.com/v1/games?universeIds=`: name, playing, visits, favoritedCount, created, updated, maxPlayers, genre. Votes come from `/v1/games/votes`. Tested live |
| Access / cost | No key, free |
| Policy | It is a **legacy** web API: Roblox says legacy APIs "can incorporate breaking changes without notice" and are not recommended for production ([official page](https://create.roblox.com/docs/cloud/legacy)). Open Cloud requires a key and gives no public stats for other people's experiences. Plan: small watchlist (≤20 universes), at most hourly, labelled "legacy/unstable", stop if it breaks |
| History | None from the API; build series from our own snapshots. `playing` may count the root place only (older DevForum report) |
| Charts / discovery feed | Undocumented internal endpoints. **Reject** |

### 2.8 Other sources

| Source | Contribution | Access / terms | Decision |
|---|---|---|---|
| Reddit Data API | Community discussion on Roblox, anime and memes | Since late 2025 every new API app needs explicit approval under the [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy); commercial use needs separate written approval (third-party reports cite high prices) | **Defer.** Read manually; apply only if a clear need appears |
| Know Your Meme | Meme origins, dates, variants | No public API; manual reference | **Manual only** (log as P4 context) |
| AniList GraphQL | Anime popularity and trending lists | Free API; commercial-use terms need checking | **Defer.** Wikipedia pageviews cover the main anime signal |
| Jikan (MyAnimeList) | Same data | Unofficial scraper of MAL | **Reject** |
| Twitch/YouTube Python SDKs (twitchAPI, google-api-python-client) | Convenience wrappers | Licence OK | **Reject**: the standard library already covers the calls |
| yt-dlp to get captions or media from others' videos | Transcripts | Against YouTube's Terms | **Reject** |
| Public datasets (Kaggle "YouTube trending" etc.) | Historical background | Stale; often scraped | **Reject** for decisions |
| Google Drive (connected to ChatGPT) | Moving exports | Already connected | **Defer** to Stage 5 (shared workflow) |

## 3. Data contract

Provider files stay **separate**, as YouTube's no-merging rule and the other providers' terms require. Every collector follows the same column conventions so ChatGPT reads every file the same way:

| Column | Meaning |
|---|---|
| `provider`, `platform` | e.g. `youtube_data_api_v3` / `youtube`; `manual_creative_center` / `tiktok` |
| `content_id`, `url` | Canonical platform ID (the deduplication key) and URL |
| `creator_id`, `creator_name` | As the platform gives them |
| `published_at_utc`, `observed_at_utc` | ISO 8601 UTC. Observed = when we read it |
| `run_id` | Links each row to `runs.csv`: command, query, every filter actually sent, provider version, units used |
| `content_language`, `language_evidence` | `declared_by_creator` / `stream_language_setting` / `wiki_edition` / `human_verified` / blank. Never guessed from title text |
| `region`, `region_evidence` | `viewable_in` (YouTube regionCode) / `chart_region` / `search_geo` (Trends) / `creator_declared_country` / blank. Audience geography is never recorded for other people's content |
| raw metric columns | Exactly as the provider returns them, blank when missing (never 0) |
| `provenance` | P1 first-party measured, P2 first-party sampled or normalised (Trends 0–100), P3 third-party reported or estimated (vidIQ), P4 qualitative |
| `expires_at_utc` | When the row must be refreshed or deleted (YouTube 30 days; Twitch 24 hours pending confirmation; open data none) |

Each export ships with a `_README.md` data dictionary (as `ss yt report` already does) listing metric definitions, supported filters and limitations. Optional `concept_id`, `meme_id`, `sound_id` and `format_id` columns in the public-observations CSV keep the joke, the sound, the format and the genre as separate entities. Filling them in is ChatGPT's research work (Stage 4.5), not a collector job.

## 4. Smallest coherent implementation

Everything uses Python's standard library (no new dependencies), runs as ordinary `ss` commands, and has a `--dry-run` with fixtures plus a smoke check. Nothing is scheduled.

| # | Build | Commands (proposed) | Needs from owner |
|---|---|---|---|
| 1 | **YouTube upgrade**: `--lang` (relevanceLanguage), explicit `--region`, `--before`; region, language and filters logged in `runs.csv`; store declared language and category; `chart` (regional most-popular gaming); `creators` (channel watchlist via uploads playlists: cheap, includes ordinary videos); `comments` (top N threads, text only, 30-day expiry); `sweep` runs a saved EN/ES query set from `config/research/youtube_queries.json` against a daily search budget; `report --json` plus a long-format observations export (still per-video maths only) | `ss yt discover/chart/creators/comments/sweep/stats/report` | **Rotate and restrict the key first** |
| 2 | **Wikimedia pageviews**: entity list per edition (en/es), redirects resolved, daily series | `ss wiki pull` | nothing |
| 3 | **Google Trends**: Trending Now RSS snapshots for GB, US, MX, ES, AR, CO, CL; validated import of manual Explore CSVs with their metadata | `ss trends rss`, `ss trends import <csv> --terms --geo --window` | nothing (optional alpha application) |
| 4 | **Public-observations CSV** for TikTok, Instagram, vidIQ and TinyFish rows with provenance P1–P4 and concept fields; validator in the style of `ss export`; optional TikTok oEmbed check | `ss observe check` | nothing |
| 5 | **Twitch**: Roblox clips by time window (EN/ES by language), stream snapshots by language, broadcaster watchlist; 24-hour retention by default | `ss twitch clips/streams/prune` | Twitch app (below) |
| 6 | **Roblox experience watchlist** (legacy endpoint, small, labelled) | `ss rbx games` | nothing |
| — | Instagram Business Discovery | not built until an account exists | later |

Order: 1–4 first (no new accounts; 2–4 can be tested live today, 1 once the key is rotated), then 5 when Twitch credentials exist, then 6. Updates to `docs/INVENTORY.md`, `docs/COMMANDS.md`, `youtube-api-policy.md`, a new `docs/research-data.md` (schemas and filter support per provider) and `reports/smoke-test.md` with PASS/FAIL/BLOCKED per collector.

Not built: a dashboard, scheduling, Drive sync, a database service, AI agents, any paid tool, scrapers, captions of others' videos, cross-channel scores.

## 5. What the owner needs to do

1. **YouTube key (required before any live YouTube run).** Google Cloud Console > APIs & Services > Credentials > the key > *Regenerate key*. Put the new value in `.env` as `YOUTUBE_API_KEY=` (never in chat or `.env.example`). Then *API restrictions* > *Restrict key* > *YouTube Data API v3* only. Check *Billing* shows no linked account. Tell Claude "key rotated and restricted"; Claude will run one 1-unit check without printing the key.
2. **Twitch app (for item 5).** Use a Twitch account with a verified email and 2FA. At [dev.twitch.tv/console](https://dev.twitch.tv/console) > *Register Your Application*: unique name (e.g. "Slugshot Research Local"), OAuth Redirect URL `http://localhost`, category *Analytics Tool*, client type *Confidential*. Copy the Client ID, press *New Secret*, and add both to `.env` as `TWITCH_CLIENT_ID=` and `TWITCH_CLIENT_SECRET=`. Then open the [Developer Services Agreement](https://legal.twitch.com/legal/developer-agreement/) in a browser and check the clause on storing data about users who haven't authorised your app. Tell Claude what it says, so the retention period can be set correctly (24 hours until then).
3. **Google Trends alpha (optional).** On [developers.google.com/search/apis/trends](https://developers.google.com/search/apis/trends) use *Apply for the alpha*. Use case to state truthfully: weekly comparison of a small fixed set of game, fandom and meme terms across GB, US, MX, ES, AR, CO and CL, for internal marketing research, starting immediately, with feedback offered. Don't count on approval.
4. **Instagram (later, once a Slugshot Instagram account exists).** Make it a Business or Creator account and link it to a Facebook Page. Create a Meta developer account and an app (type *Business*), add the Instagram product (Facebook Login), and give the app those three permissions for your own user in development mode. Ask Claude to test then. Don't do this before the account exists.
5. **Nothing needed** for Wikimedia, Trends RSS, manual Trends CSV, Roblox or the public-observations CSV.

No step needs billing, a purchase or vidIQ credits. Account-creation steps are listed for the owner; Claude won't create accounts or authorise OAuth.

## 6. Handover after the build

Claude builds and tests items 1–4 (and 5–6 when unblocked), writes the smoke report, and then stops. ChatGPT owns query lists, watchlists, entity lists, concept classification (emerging / accelerating / established / saturated / declining / unknown) and all interpretation. The owner runs the commands (`ss yt sweep`, `ss wiki pull`, `ss trends rss`, ...) and uploads `exports/share/` to ChatGPT. Claude is needed again only if a provider changes or a new source is approved.

## 7. Outcome (implemented 2026-11-24, same day)

The owner approved the plan with additions (bilingual query sets, comment collection, Shorts confirmation, quota budgets, an easy observation importer, Twitch, Roblox, and further TikTok investigation). What was built and how it tested is in [research-data.md](../research-data.md); the short version:

| Component | Result | Evidence |
|---|---|---|
| YouTube upgrade (`ss yt`): `--lang`, `--region`, `--after/--before`, saved query sets, regional chart, creator uploads, comments without authors, `shorts_status`, budget check before each run, every request logged (failures too), CSV + JSON + long-format history, export expiry | **PASS, live** for chart + Shorts check + stats; sweep/creators/comments on fixtures | owner confirmed key rotated and restricted; a known Short confirmed via the Shorts playlist |
| Wikimedia (`ss wiki`) | **PASS, live** | es "Bajoterra" resolved as a redirect to "Slugterra" (Wikidata Q9338576); redirect views stored separately; missing days not zero-filled |
| Trending Now RSS (`ss trends rss`) | **PASS, live** in GB, US, MX, ES, AR, CO, CL (about 10 terms each) | |
| Explore CSV import (`ss trends import`) | **PASS on sample files**; needs the first real download to confirm the format | per-download scale kept by `import_id`; "<1", Breakout and +% kept as labels |
| Twitch (`ss twitch`) | **PASS, live**: 40 Roblox clips in 12 h (33 en/es), 10 Spanish live streams, recheck | owner confirmed the 24 h storage reading; exports local-only until onward transfer is reviewed |
| Roblox (`ss rbx`) | **PASS, live** (legacy endpoint) | at most hourly, max 20 experiences |
| Observations (`ss observe`) | **PASS**: CSV/TSV/Markdown, URL ID extraction, rounding kept, duplicates/conflicts/repeats, clear errors | the 24 Nov Creative Center figures import as P1 rounded values with unknown rank left blank |
| TikTok oEmbed | **PASS, live**, but TikTok now returns **only the embed and post ID** (no author/title/stats), so it's an existence/ID check only | |

Corrections to §2.6 (TikTok) after reading TikTok's own docs: the **Discovery API** (TikTok API for Business → Organic API) exists and is well matched to trend research. It offers top-200 hashtags by country, period and industry (Games), with views, posts, rank change and 30-day daily history; Commercial Music Library tracks; videos per hashtag or track (IDs only); and trending search keywords. But TikTok "can't onboard personal accounts or individual developers" (company-domain email and company website required). Hashtag endpoints need an ad-account authorisation; music and keyword endpoints need the Accounts API application form and Advanced Access or a Verified Business Account. Decision: **blocked by eligibility; revisit if Slugshot gets a company identity.** Creative Center stays manual: TikTok's commercial terms bar automated collection from its commercial technology, so no browser automation (Claude in Chrome, Playwright, DevTools MCP) was installed. TikTok's for-Business MCP server covers ads management only. Full detail: [research-data.md §7](../research-data.md#7-tiktok-collection-routes).

## 8. Review corrections (ChatGPT review of the exports, 2026-11-24)

| Finding | Fix | Verified by |
|---|---|---|
| Wikipedia: redirect/canonical linkage, double-counting risk, missing vs zero vs failed, no topic-total guidance, dictionary not received | Each (edition, title) is fetched once and duplicates are warned about. New request log `wiki_coverage.csv` / `wikimedia_coverage_*` records ok, no_data, failed, resolve_failed and not_found. Failed title lookups are kept and retried (a live rate-limited lookup had been dropped silently before this fix). Pacing and backoff added after a live 429 on about 60 requests. `--all-redirects` is opt-in, with a warning that redirects can be separate subjects. Topic-total method in research-data.md §5. Combined `DATA_DICTIONARY.md` in the share folder, rebuilt on every export | unit tests (duplicate alias, 503, 404, returned 0, failed lookup); live: Slugterra all-redirects; real re-pull with all 5 titles ok |
| YouTube: category-10 video in a category-20 chart | Kept as returned; `category_requested` and `category_mismatch` added | live: 2 of 19 MX/ES Gaming-chart videos flagged |
| YouTube: one video in MX and ES at the same time counted as two snapshots | Report now has `stored_rows`, `observations` (merged within 10 min) and `discovery_contexts`; history has `observation_moment` and `duplicate_context` | unit test; live export |
| YouTube: same-timestamp rows could produce growth | Growth only between distinct moments at least `min_growth_hours` (1 h) apart | unit test (0.5 h gives none, 3 h gives growth); live (38 min gives none) |
| YouTube: live coverage of saved sets, creators, comments, pagination, failures, missing metrics, quota | Bounded live run: sweep (2 searches, 50 videos, 50 Shorts checks), 2-page search, 2 creators (14 uploads), comments (7, plus a bad ID that failed with 404), 3 hidden like counts left blank. runs.csv and quota_log.csv agree exactly. **Bug fixed:** the sweep's pre-run estimate left out Shorts-check units (estimated 2, used 54) | live, about 66 units |
| Observations: scope missing from the duplicate key | Key now includes region, period and category. Placeholder text ("—", "n/a") is blank in all columns (it had been stored as a category) | unit test: #huss in 4 scopes on one day, then a re-import skipped 4 duplicates |
| Trends RSS export had no expiry | Export expiry = oldest row's 90-day local expiry | unit test; live manifest |
| Creative Center should be easier | `ss observe cc-links` (opens pages for every market and period, plus a session list) and `ss observe cc-paste` (copied page text to a previewed, prefilled CSV). No automated access, per TikTok's terms | unit tests on fake English and Spanish layouts; **needs one real paste to confirm the layout** |
| Twitch terms | Owner confirmed review; 24 h retention and local-only exports unchanged | n/a |
| Google Trends API | Owner has applied; integration plan unchanged (research-data.md §8) | n/a |
