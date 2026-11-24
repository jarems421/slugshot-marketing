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

## Grey areas

- **Sharing API data with ChatGPT, Gemini or other AI services: disabled.** The policies don't mention AI tools, and III.E.5 asks you to protect API data from unauthorised disclosure. Until that's clarified (e.g. through YouTube's API support or a compliance audit), `ss yt report` writes only to `data\local\reports\` (git-ignored, never `exports\share\`) with an "internal only" banner, and `ss export` no longer points to it. Your own analytics typed in from YouTube Studio, TikTok and Instagram are not API data and can still be shared through `ss export`.
- **Internal use.** Privacy-policy and terms-link requirements (III.A) are written for apps with users. A single-person internal script arguably isn't one. Using the API still means accepting the Terms.
- **Your own channel later.** Once Slugshot has its own channel, use YouTube Studio exports, or the YouTube Analytics API with OAuth, for your own videos. That is authorised data with different rules, and it includes retention and watch time. It isn't built yet.

## Live test: what's done and what needs you

Done on 2026-11-24 with the key in `.env`: one `stats` call and one `discover` call returned real public data (2 videos.list units and 1 search call).

Still needs you:
1. **Regenerate the key.** Its value was shown in this Claude Code session when it was saved in `.env.example`. Google Cloud Console > APIs & Services > Credentials > your key > Regenerate key, then paste the new value into `.env` (not `.env.example`).
2. **Restrict it.** On the same page: API restrictions > Restrict key > YouTube Data API v3 only. Application restrictions can stay "None" for a desktop script.
3. **Check there's no billing** on the project. Nothing here needs it.
4. Run `.\ss smoke` (1 unit) to confirm the new key, then start real collection:
   ```powershell
   .\ss yt discover "roblox pvp" --days 7 --short-only
   .\ss yt stats        # again 12-24 h later, so view_increase_since_prev has two snapshots
   .\ss yt report       # CSV + _README.md data dictionary in data\local\reports\ (internal only)
   ```
