# Publishing

The dashboard's **Publish** page puts our own videos on our own accounts through the platforms' official APIs, with a manual route wherever an API can't do it. Code: `dashboard/publish.py`; tests: `tests/test_publish.py` (fixtures only).

**Nothing is published without the owner.** Every API upload waits for the owner to approve it in the dashboard by typing the account handle. The approval covers that exact file (its SHA-256 fingerprint) and that exact text and settings; editing either cancels it. Claude prepares drafts and manual packages (`ss publish`) and never approves.

## Accounts

| ID | Platform | Handle | Language | Routes |
|---|---|---|---|---|
| `yt-en` | YouTube | @Ronin_JT | EN | API upload, manual |
| `yt-es` | YouTube | @Roni_JTes | ES | API upload, manual |
| `tt-en` | TikTok | @.roni_jt | EN | Buffer (preferred), upload to inbox, Direct Post, manual |
| `tt-es` | TikTok | @es.roni_jt | ES | Buffer (preferred), upload to inbox, Direct Post, manual |
| `ig-en` | Instagram (Creator) | @1roni_jt | EN | Buffer (preferred), API (both need a public URL), manual |
| `ig-es` | Instagram | not created yet | ES | inactive until it exists |

Handles live in `config/dashboard/settings.json` and in the dashboard's account settings. To add Spanish Instagram later, set `active: true` and its handle.

## Visibility and the reveal lock (separate since 2026-11-25)

Two settings in `config/dashboard/settings.json` → `publishing`:

- **`public_posting`** (on): posts others can see (YouTube public or unlisted, TikTok via Buffer or inbox, Instagram) are allowed. When it's off, YouTube stays private and TikTok Direct Post stays "Only me". Turning it off after an approval blocks that upload.
- **`reveal_lock`** (on): the game's identity stays hidden, whatever the visibility.
  - Text that names the game (`reveal_terms`: "Slugshot"/"Slug Shot", Roblox game or share links) **blocks** any post others can see. On a private post it's only a warning.
  - For any post others can see, the owner ticks a confirmation at approval: "Nothing names or shows the game (title, logo, place link or anything that identifies it)". The dashboard can't check pictures, so this is the owner's call. The approval records it.
  - Only the owner turns the lock off. An approval made under one lock setting is void under the other.

Entertainment posts can be public while the game stays unnamed. Add character or place names to `reveal_terms` if they would give it away.

**TikTok's own limit:** our TikTok app isn't audited, so its Direct Post only allows "Only me" on a **private** account (`tiktok_app_audited: false`). Both our TikTok accounts are public, so Direct Post is blocked. Public TikTok posts go **via Buffer** (Buffer's TikTok app is audited) or **upload to inbox** (you choose who can view in the app).

**Account guard:** before anything is sent, the upload checks that the stored token still belongs to that account (YouTube channel ID or handle, TikTok `creator_info` username, Buffer channel handle). Signing in with the wrong account is refused at connection time.

## Routes, as of 2026-11-25 (official docs)

| Route | How it works | Owner sets up | Limits that matter |
|---|---|---|---|
| **YouTube API** | Data API v3 `videos.insert`, resumable upload in 8 MiB chunks. A dropped connection resumes from the last byte YouTube confirms. Sends title, description, tags, category Gaming (20), language, visibility, made-for-kids and altered/synthetic content. | The existing Google OAuth client, plus the `youtube.upload` scope ([checklist](credentials-checklist.md), step 1b) | Separate upload quota: 100 `videos.insert` calls per day, 1 unit each. The docs say uploads from unverified projects are *not* forced to private. Files up to 256 GB. |
| **TikTok inbox** | Content Posting API, upload only (`/v2/post/publish/inbox/video/init/`, chunked `FILE_UPLOAD`). TikTok notifies the account, and the owner finishes the caption, privacy and post in the app. | `video.upload` scope on our TikTok app | At most 5 pending inbox shares per 24 h, and 6 requests a minute per token. TikTok returns no video ID, so paste the link back with **Mark as posted**. |
| **TikTok Direct Post** | `/v2/post/publish/video/init/` after `creator_info/query`. | `video.publish` scope | Until TikTok audits our app: posts are `SELF_ONLY`, the account must be **private** while posting, and at most 5 users post per 24 h. Around 15 posts a day per creator. Up to 10 minutes and 4 GB; 360–4096 px; 23–60 fps. |
| **Instagram API** | Instagram Login (`graph.instagram.com`): a REELS container from `video_url`, a status check once a minute for at most 5 minutes, then `media_publish`. | A token with `instagram_business_content_publish` ([checklist](credentials-checklist.md), step 2b) | **No local file upload with Instagram Login.** Resumable upload (`rupload.facebook.com`) is only for Facebook Login for Business. Meta needs a public HTTPS link to the file, and we don't host one. 100 API posts per 24 h. Reels: MP4/MOV, H.264/HEVC, AAC ≤48 kHz, 3 s–15 min, ≤300 MB, ≤1920 px wide, 23–60 fps. Also blocked by the reveal lock. |
| **Buffer** (TikTok, Instagram) | GraphQL `createPost` (`mode: shareNow`, or a Buffer draft with `saveToDraft`), then `post` status polling; the post link gives the platform video ID. Re-checks the live Buffer channel (platform and handle) before posting. A retry follows the post Buffer already accepted and never creates a second one. | `BUFFER_API_KEY`, plus Cloudinary for hosting (see below) | **No file upload in Buffer's API**: Buffer fetches the video from a link. The dashboard hosts the approved file on Cloudinary for it, or uses an https link you paste. Free plan (live 2026-11-25): 3 channels (all used), 10 scheduled posts, daily posting limit 25 per TikTok and 50 for Instagram, 3,000 API requests per 30 days. Buffer posts with the account's own privacy (normally public). |
| **Manual** (any platform) | `data/local/publish/<job>/` gets `title.txt`/`description.txt`/`tags.txt` or `caption.txt`, plus `CHECKLIST.md` with the steps. The owner posts it in YouTube Studio, TikTok Studio or the Instagram app, then pastes the link into **Mark as posted**. | Nothing | None |

### Hosting for Buffer (Cloudinary, free plan)

`dashboard/hosting.py`; limits in `publishing.hosting` (settings).

1. Only after the owner approves a Buffer job, and only the exact file the approval bound (same SHA-256), is the file uploaded.
2. The upload uses delivery type `authenticated` under `slugshot-publish/<hash>`. Buffer gets a signed link to the original. Nobody can fetch it without that link or request transformations from it. The link is never logged, stored or exported.
3. One copy per file: TikTok EN/ES and Instagram posts of the same file share it, and retries overwrite rather than duplicate.
4. The copy is deleted (with CDN invalidation) when every Buffer job using it is **done**. Deleting a job also releases it.
   - Live check 2026-11-25: Buffer keeps pointing at our link (it doesn't copy the file), so the copy must outlive any Buffer draft or queued post.
   - Jobs still pending, failed or waiting as a Buffer draft keep it.
   - A daily cleanup deletes copies left only by failed or draft jobs older than 72 h, and uploads that never finished.
   - Settings → Hosting and quotas → **Clean up** does it on demand.
5. Free-tier guard, checked before every upload: at most 95 MB per video (the free plan allows 100 MB) and at most 5 files hosted at once. Uploads stop at 60% of credits, storage or bandwidth. Compress locally first: no transformations are ever requested.
6. **Settings → Hosting and quotas** shows Cloudinary credits, storage and bandwidth, the hosted files, and Buffer's remaining API requests. Buffer analytics pause below 150 requests left, and posting stops below 10.

Cloudinary free plan (docs, 2026-11-25): 25 credits per rolling 30 days. One credit is 1 GB storage, 1 GB video bandwidth or 1,000 transformations; each upload counts as 1 transformation. Over the limit, the account is disabled, not billed. No card is needed.

Live check with the neutral test card: `.\ss dash hosting test`. It uploads, fetches through the signed link, checks that a tampered link is refused, then deletes. `.\ss dash hosting status|cleanup`.

### TikTok's required posting screen

The Direct Post form follows TikTok's Content Sharing Guidelines:

- It shows the creator's nickname from `creator_info`.
- Privacy comes from a dropdown of the options TikTok offers for that account, with no default.
- Comments, Duet and Stitch start off, and anything the account has disabled is greyed out.
- Commercial content disclosure starts off. When it's on, you must choose "Your brand" (labelled *Promotional content*) and/or "Branded content" (labelled *Paid partnership*; this can't be private).
- An AI-generated content label (`is_aigc`) is available.
- The preview is shown.
- The declaration "By posting, you agree to TikTok's Music Usage Confirmation" must be ticked (the branded version adds the Branded Content Policy).
- There's a notice that processing can take a few minutes.
- Nothing is sent to TikTok before the owner consents.

## Workflow

1. **Content → Local renders → Register** the edited video as a version (`CON-…-EN-V01`).
2. **Publish → New post**:
   - choose the version, the video file and an optional experiment variant;
   - tick the accounts and pick each account's route.

   This creates one draft per account.
3. **Open each draft**:
   - Watch the preview (a 9:16 frame with the caption).
   - Edit that platform's text and settings, then **Save and re-check**.
   - The checks cover file size, length, frame rate, resolution, text limits, made-for-kids, privacy, the reveal lock, game truth (e.g. never "Floppy does nothing"), AI-label reminders and the QC result.
4. **Approve**: type the account's handle (and tick TikTok's declaration), then press **Approve and upload**. The upload runs in the background, and the job shows its progress and log.
5. **On success**:
   - the post is recorded in `uploads`, linked to the version and therefore the concept;
   - if an experiment variant was chosen, the version is added to that variant;
   - it appears under **Content**, and analytics syncs attach metrics to it.

   A TikTok inbox draft or a manual post is linked once the owner pastes its link.

Failures leave the job **Failed** with the reason. **Retry** reuses the approval only if nothing changed.

## Commands (Claude's side)

```
.\ss publish accounts                                   # routes and upload credentials (yes/no)
.\ss publish new --asset CON-X-EN-V01 --video exports\SS_....mp4 --accounts yt-en,tt-en --route tt-en=inbox [--experiment EXP-… --variant B] [--fields '{"caption": "…"}']
.\ss publish list [--state draft]
.\ss publish check PUB-…                               # the same checks as the approve box
.\ss publish package PUB-…                             # manual package
.\ss publish mark-posted PUB-… --url https://…          # record a post made by hand
```

There's no approve command. Approval happens only in the dashboard, by the owner.

## Safety

- Video files must be inside `exports/` or `media/`. The preview endpoint serves only those, with byte ranges, on loopback.
- Tokens come from the existing vault (DPAPI) and refresh through the analytics connectors. They're never logged or shown, and job logs hold no tokens or URLs with credentials.
- Connecting for uploads adds the upload scope to the same connection the analytics already use (`include_granted_scopes`), so analytics keep working.
- No scheduling, no automatic posting, no posting through Composio or any third party, no paid services.

## Status

| Part | State |
|---|---|
| Drafts, checks, approval binding, manual packages, linking to versions and experiments, Publish page, CLI | built; fixture-tested (14 tests) |
| Connections (YouTube EN/ES with upload scope, TikTok EN/ES Sandbox with `video.upload` + `video.publish`, Buffer's 3 channels) | **live-validated** 2026-11-25: identity, scopes, token refresh ([report](../../reports/archive/live-integration-validation-2026-11-25.md)) |
| YouTube resumable upload, TikTok inbox and Direct Post, Buffer post, Instagram container flow | built and fixture-tested; **authorised but untested live**: two test drafts wait for the owner (`PUB-20261125-071008-yt-en` private YouTube, `PUB-20261125-071008-tt-en` TikTok inbox) |
| Instagram local-file upload | **blocked** by the platform for Instagram Login. Options: a public HTTPS link the owner controls, or a Facebook Login for Business integration (needs a Facebook Page linked to the account; not built, per the feature freeze). Manual posting covers it |
| TikTok public Direct Post | blocked until TikTok audits the app (optional; the inbox route needs no public visibility) |

Sources: developers.google.com/youtube/v3/docs/videos/insert, …/guides/using_resumable_upload_protocol, …/determine_quota_cost; developers.tiktok.com/doc/content-posting-api-get-started, …-reference-direct-post, …-reference-upload-video, content-sharing-guidelines, content-posting-api-media-transfer-guide, login-kit-desktop; developers.facebook.com/docs/instagram-platform/content-publishing, …/instagram-graph-api/reference/ig-user/media, …/overview. TikTok's scopes overview returned 403 when it was read, so whether `video.upload` needs an audit isn't documented on the pages we could read; the developer portal shows it.
