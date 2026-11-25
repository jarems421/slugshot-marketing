# Live integration validation: 2026-11-25

Accounts: YouTube @Ronin_JT (`yt-en`) and @Roni_JTes (`yt-es`); TikTok @.roni_jt (`tt-en`) and @es.roni_jt (`tt-es`), Sandbox app; Buffer free plan with both TikToks and Instagram @1roni_jt. Instagram's direct API is deferred. No credential was printed, logged or exported: an export leak check found none of the 22 stored secret values in the share export. Nothing was uploaded or posted.

Status labels: **live** = exercised against the real API today; **fixture** = tested offline against documented shapes; **authorised, untested** = permission granted but not exercised (needs owner approval); **blocked**; **unavailable**.

## Connections

| Check | yt-en | yt-es | tt-en | tt-es | Buffer |
|---|---|---|---|---|---|
| Identity | live: channel UCNaue-L…, @ronin_jt | live: UCN3aCQP…, @roni_jtes | live: `creator_info` username .roni_jt, nickname "Roni" | live: es.roni_jt, "Roni.es" | live: 1 organisation; channels 1roni_jt (Instagram business), .roni_jt and es.roni_jt (TikTok) |
| Scopes | yt-analytics.readonly, youtube.readonly, youtube.upload | same | user.info.basic, user.info.stats, video.list, video.upload, video.publish | same | personal key; Buffer's TikTok channels hold video.publish, video.insights, user.insights; Instagram holds content_publish and manage_insights |
| Token refresh | live: forced refresh OK, refresh token and all 3 scopes kept | live: same | refresh path unchanged (access token 24 h; refresh-expiry now recorded at the next refresh) | same | key expiry isn't readable through the API (set when the key was made) |
| Dashboard sync | live: ok | live: ok | live: ok (was **failing**, see fixes) | live: ok (was failing) | live: ok, 3 channels |

## Accessible metrics (all accounts have 0 posts)

| Platform | Live values today | Available once posts exist | Not available |
|---|---|---|---|
| YouTube (Analytics API) | followers 0 (a real zero) | daily views, watch time, avg view duration and %, likes, comments, shares, subscribers gained/lost; per-video lifetime | impressions and CTR (Studio import) |
| TikTok (Display API) | followers 0 (a real zero) | per-video views, likes, comments, shares | watch time, completion, saves, profile visits from this API |
| TikTok via Buffer | none stored (Buffer reports 0 with `metricsUpdatedAt: null`: not real zeros) | Buffer lists views, shares, reach, watch time (min), avg watch time (s) | saves (not in Buffer's TikTok set) |
| Instagram via Buffer | none stored | views, reach, likes (reactions), comments, shares, saves, watch time, avg watch time | followers |

Zero and no data stay distinct. YouTube returns no rows for days without activity, and those stay blank. The Buffer connector stores nothing for a post until Buffer has computed its metrics. A computed 0 is stored as 0.

Duplicates: TikTok views, likes, comments and shares come only from the TikTok API. Buffer adds only reach and watch time for TikTok. Buffer rows join the same upload through the post's link.

Buffer limits (live): 3,000 requests per 30 days on Free (rate-limit headers); insights limited to the last 31 days ("Free-plan Insights are limited to the last 31 days of history"); 3 channels (all used); 10 scheduled posts; daily posting limit 25 per TikTok channel and 50 for Instagram. The sync costs 1 request per account (3 the first time, for the channel lookup): about 90 a month. This validation used 24.

Documented but untested: Buffer marks per-post metrics "experimental", refreshed about daily. Buffer only returns posts that Buffer sent. Whether the free plan fills TikTok post metrics is unverified: the TikTok channels show only the `publish` product, while Instagram also has `analyze`.

## Publishing readiness

| Route | Status |
|---|---|
| YouTube API upload (private/unlisted/public) | authorised, untested. Test draft `PUB-20261125-071008-yt-en` (6 s neutral card, private) passes its checks |
| TikTok upload to inbox | authorised, untested (Sandbox). Test draft `PUB-20261125-071008-tt-en` passes its checks; Sandbox inbox delivery isn't documented on the pages we could read |
| TikTok Direct Post | **blocked**: the app is unaudited, so only "Only me" on a private account, and both accounts are public |
| Buffer post (TikTok, Instagram) | built and fixture-tested; **blocked on a public video link** (Buffer's API has no file upload) |
| Instagram API | deferred (Meta device security); manual package still available |
| Manual packages | fixture-tested |

## Fixes in this session

1. **TikTok sync failed (HTTP 401):** the connector asked for `username`, which needs `user.info.profile`, and that scope isn't granted. It now asks only for fields its granted scopes unlock. It reads the handle from `creator_info`, and no longer blanks the handle.
2. **Wrong-account guard:** first syncs and OAuth callbacks now check the handle and channel. A callback that would put one account in another's slot (e.g. EN TikTok as ES) is refused before anything is stored. Every upload re-checks the live identity before sending.
3. **Reconnect could drop upload permission:** a TikTok reconnect for analytics replaced the token with analytics-only scopes. Reconnects now ask again for every scope already held.
4. **Visibility vs reveal lock:** these are now separate settings (see publishing.md).
5. **Buffer integration:** connector, publish route, fixtures, 6 new tests. Also fixed a sharing-rule gap: Buffer rows now respect their platform's sharing rule.

Tests: `tests.test_dashboard` 33, `tests.test_publish` 20, `tests.test_knowledge` 21, all OK; `ss smoke --dashboard` PASS. A known ordering issue predates this work: importing `test_publish` before `test_dashboard` in one run fixes the vault path early, and the vault test fails.

## Video hosting for Buffer (not built; needs approval)

Live schema: `createPost` takes `assets: [{video: {url, thumbnailUrl, metadata}}]`, and there is no upload mutation. Buffer's docs ask for a public, stable https link.

- **Recommended: a short-lived link served from this PC.** The dashboard serves the one approved file from loopback at a random path. Cloudflare's free quick tunnel (`cloudflared`, no account) exposes only that path. It opens at approval and closes once Buffer reports the post sent or failed. Nothing is stored with a third party, and the link dies afterwards. Costs: installing `cloudflared` (official Cloudflare build), and a public but unguessable link for a few minutes. Buffer's fetch timing isn't documented, so `shareNow` only, with no queued posts.
- Other options:
  - Cloudflare R2 with presigned links: free tier, but needs a card on file.
  - Google Drive "anyone with link": viewer and redirect pages are unlikely to work as a direct file link, and the file stays public until unshared.
  - A public GitHub repo: permanent and indexed, which breaks the reveal lock.
- Until then: paste any https link you control into the job, or post from the Buffer composer or the manual package.

## Needs the owner

- Approve (or not) the two test drafts in **Publish**.
- Choose a video host for Buffer (see below).
- Check the Google OAuth consent screen is **In production**, not Testing. In Testing, refresh tokens expire after 7 days.
- Note the Buffer key's expiry date.

## Addendum: Cloudinary hosting for Buffer (same day)

Cloudflare tunnels were dropped at the owner's request; Cloudinary (free plan) now hosts approved videos for Buffer. See publishing.md → "Hosting for Buffer".

| Capability | Status |
|---|---|
| Cloudinary authentication | **blocked**: `CLOUDINARY_CLOUD_NAME` in `.env` isn't the cloud name (HTTP 401 "cloud_name mismatch"). The key and secret are present |
| Upload, signed-link fetch, deletion, usage readout | built, fixture-tested; the live run waits on the fix (`.\ss dash hosting test`, neutral test card only) |
| Approve → host → Buffer → record → delete; one copy shared across accounts; no duplicate post on retry; duplicate file per account refused; abandoned-copy cleanup; free-tier guard | fixture-tested (4 new tests) |
| Buffer API quota monitoring | **live**: 2,972 of 3,000 left after today's work; shown in Settings |
| Buffer analytics after real posts | **unconfirmed**: there are no posts yet. The connector is ready, and the first Buffer post will show which metrics Buffer fills |
| Test-order vault failure | fixed: the vault path was frozen at import (`vault.root()` now reads it per call). All 130 tests pass in one run, in the order that used to fail |

End-to-end test drafts (none run; each needs the owner's approval):

| Job | Account | Route | Result if approved |
|---|---|---|---|
| PUB-20261125-071008-yt-en | YouTube EN | API | private video |
| PUB-20261125-080949-yt-es | YouTube ES | API | private video |
| PUB-20261125-071008-tt-en | TikTok EN | upload to inbox | TikTok inbox draft (Sandbox) |
| PUB-20261125-080949-tt-en | TikTok EN | Buffer, draft mode | Buffer draft; not posted |
| PUB-20261125-080949-tt-es | TikTok ES | Buffer, draft mode | Buffer draft; not posted |
| PUB-20261125-080949-ig-en | Instagram EN | Buffer, draft mode | Buffer draft; not posted |

The three Buffer jobs share one Cloudinary copy of `media/_integration_test/buffer_test_1080x1920.mp4`. While they're Buffer drafts the copy stays, because Buffer may fetch it when the draft is posted. Deleting the jobs (and the drafts in Buffer) removes it. A real public post via Buffer would be public on TikTok or Instagram, so that test is left to the owner.

Regression: unit tests 130/130 OK (dashboard 33, publishing 23, knowledge 21, analysis and research modules); `ss smoke`, `--research`, `--dashboard` all PASS.

## Final live validation (after the cloud name fix)

| Capability | Result |
|---|---|
| Cloudinary authentication + usage readout | **live**: Free plan, 25 credits per 30 days, 0% used, video cap 100 MB |
| Upload (authenticated delivery), signed-link fetch | **live**: neutral test card, 110,572 bytes, link answered |
| Tampered signed link | **live**: refused (HTTP 401) |
| Deletion | **live**: Admin API 404 and link 404. The CDN can keep serving a cached copy for a short while (seen once), so the self-test now polls |
| Buffer fetches the hosted video and accepts a draft | **live**: TikTok EN and Instagram drafts created; Buffer read 109,956 bytes, 6.0 s, 1080×1920, status "ready". Both test drafts deleted (DeletePostSuccess) |
| Buffer keeps using our link | **live finding**: the draft's asset still points at the Cloudinary link (Buffer doesn't copy it), so a hosted copy must stay until the post is sent. The release rules already keep it for Buffer drafts and pending jobs |
| Abandoned-copy cleanup | **live**: the unused test copy was deleted by `cleanup` |
| Duplicate-post guard | verified on a copy of the live database with uploads disabled: same file on the same account refused; same file on another account allowed |
| Five accounts | **live** sync ok: yt-en, yt-es, tt-en, tt-es (TikTok API) and tt-en, tt-es, ig-en (Buffer) |
| Buffer API quota | 2,963 of 3,000 left in the 30-day window |

Fixed: Instagram EN showed "not connected" on the Publish page (only its deferred direct API was checked); it now shows ready via Buffer.

Regression: 131 unit tests OK in one run; `ss smoke` 28/28, `--research` 10/10, `--dashboard` 6/6 PASS. Cloudinary holds no files after the tests.
