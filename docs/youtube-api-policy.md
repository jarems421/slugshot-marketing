# YouTube API: what the collector may do

Checked 2026-11-24 against the official pages: [Developer Policies](https://developers.google.com/youtube/terms/developer-policies), the [policy guide](https://developers.google.com/youtube/terms/developer-policies-guide), the [API Services Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service) and the [quota cost page](https://developers.google.com/youtube/v3/determine_quota_cost). This is a careful reading, not legal advice. Re-check when Google updates the pages.

## What the rules say

| Topic | Rule | Source |
|---|---|---|
| Storing statistics | Statistics from public (non-authorised) data may not be stored for more than 30 days. Stored data must then be deleted or refreshed, and kept reasonably current. | Policies III.E.4.b, d, e |
| Derived metrics | "must not ... access or use API Data to create new or derived data or metrics", unless approved. | III.E.4.h |
| What counts as acceptable | Metrics that use only YouTube data combined by simple maths (adding, subtracting, dividing). Examples given: average daily views, subscribers gained or lost, total views across a group, graphs of increase in views. | Policy guide, "Acceptable metrics" |
| Prohibited without approval | Custom "scores" from independently calculated averages or ratios; ranking or tracking views between different channels; merging YouTube data with other data. | Policy guide |
| Aggregation | "Do not aggregate API Data except ... channels that are under the same content owner." | III.E.2.a |
| Approval route | Long storage and extra derived metrics need the API Compliance Audit; the newer "derived metrics and data storage" permission is only for audited developers who applied. | Policy guide |
| Credentials | Don't share the API key with any third party. | III.D.1.4 |
| Projects | One Google Cloud project per API client. Don't split quota across projects. | III.D.3, guide |
| Quota | search.list has its own bucket of 100 calls a day at 1 unit each. videos.list costs 1 unit from the 10,000-unit daily pool. Resets at midnight Pacific. | Quota cost page |

## What the collector does

| Item | Status | Why |
|---|---|---|
| Dated snapshots of views, likes, comments | **On**, kept 30 days max, pruned on every run | III.E.4.b |
| `view_increase_since_prev`, `hours_since_prev`, `views_per_hour_since_prev` (same video, two snapshots) | **On** | Subtraction and division of one video's YouTube numbers, like "increase in views" in the acceptable list |
| `age_hours` (upload time to snapshot) | **On** | Time arithmetic on one video |
| `duration_le_180s` | **On**, never called "Short" | A plain length test; the API does not say what is a Short |
| Views compared with the same creator's median for similar-age uploads | **Removed** | A ratio against an independently calculated average, which the guide lists as prohibited without approval. The original brief asked for this; the policy wins |
| Age buckets, cross-channel rankings, scores | **Removed / never built** | Ranking or tracking between channels is prohibited |
| Merging YouTube rows with TikTok/Instagram rows | **Not done**. Platform metrics go in a separate CSV | Merging with other data is prohibited |
| Search parameters (`region_param`, `relevance_language_param`, date window, query) stored on every row and in `runs.csv` | **On** (Stage 4.4) | Records what was asked; no metric is derived from them |
| Regional most-popular chart (`ss yt chart`) | **On** | `videos.list chart=mostPopular`: YouTube's own chart, stored as dated snapshots, not re-ranked |
| Creator uploads via uploads playlists (`ss yt creators`) | **On** | Collects ordinary uploads too; numbers are still only compared per video |
| `shorts_status` from the channel's Shorts playlist (`UUSH…`) | **On** | A classification read through the official API (an undocumented playlist convention), not a metric |
| Public comments (`ss yt comments`) | **On**: text, time, like/reply counts; **no author names or IDs**; 30 days | API data like any other (III.E.4); personal data minimised |
| Captions or video downloads | **Not built** | `captions.download` needs edit permission on the video; downloading media is against YouTube's Terms |
| Every export carries an expiry date (oldest snapshot + 30 days) in its README and `exports\share\research\MANIFEST.csv`; `ss research prune` deletes expired copies | **On** | The 30-day limit applies to exported copies too |

## Grey areas

- **Sharing API data with ChatGPT, Gemini or other AI tools: allowed for internal analysis (owner decision, 2026-11-24).** The policies don't mention AI tools; III.E.5 asks you to protect API data from unauthorised disclosure. The owner has decided that sharing public stats with AI tools for internal analysis is acceptable. `ss yt report` writes to `exports\share\research\` with its data dictionary and expiry date. Copies in ChatGPT or Drive should be deleted by that date, and none should be kept in a permanent knowledge bank. Don't publish the data, and never share the API key.
- **Money.** Everything here uses YouTube's free quota. Never enable billing, buy quota or make any paid request without asking the owner first.
- **Internal use.** Privacy-policy and terms-link requirements (III.A) are written for apps with users. A single-person internal script arguably isn't one. Using the API still means accepting the Terms.
- **Your own channel later.** Once Slugshot has its own channel, use YouTube Studio exports, or the YouTube Analytics API with OAuth, for your own videos. That is authorised data with different rules, and it includes retention and watch time. It isn't built yet.

## Live tests

- 2026-11-24 (Stage 1): one `stats` call and one `discover` call returned real public data.
- 2026-11-24 (Stage 4.4): the owner confirmed the key was **regenerated and restricted to YouTube Data API v3** after the earlier exposure. Then: a Mexico Gaming `chart` (1 unit), a Shorts-playlist check (a known Short came back `confirmed_short`; a channel with no Shorts playlist returned 404 and stayed `candidate`; the failed request was counted against quota), and the smoke test's 1-unit `stats` call. All passed.

Keep billing off on the Google Cloud project; nothing here needs it. Commands and the routine are in [research-data.md](research-data.md).
