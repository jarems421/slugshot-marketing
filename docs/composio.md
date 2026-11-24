# Composio in the marketing toolkit

Composio (docs.composio.dev) brokers OAuth logins and API calls to over 1,800 apps. Here it's a thin, read-only add-on. It doesn't replace the research collectors or the evidence system: those stay on our own official-API keys, with their own retention and provenance rules.

## What's set up (24 Nov 2026)

| Item | State |
|---|---|
| Account | Composio Developer **Hobby** plan: free, hard-capped (usage pauses at the cap; no card, so no bill). About 100K tool calls a month, up to 20K on Composio-managed apps; 2,000 requests a minute |
| Key | `COMPOSIO_API_KEY` in the git-ignored `.env`; placeholder in `.env.example`; added to `research_common.redact()` so errors can't leak it |
| Client | `scripts/composio_check.py` (`ss composio status|test|audit`): REST v3 with the standard library and `x-api-key`. No SDK, CLI or plugin installed |
| Connected accounts | **0.** Nothing is authorised yet |
| Tested | Key accepted; reads of the toolkit catalogue, connected accounts and auth configs; one end-to-end tool execution (`HACKERNEWS_GET_ITEM_WITH_ID`, no-auth, read-only, 1 free call): PASS |

## Why REST, not the plugin, CLI or SDK

- **Claude Code plugin** (`composio@composio`): it installs the Composio CLI and logs in through a browser or a separate agent identity, not our project key. It installs at user scope, so every Claude session gets its tools and a `composio-cli` skill. We don't need it until we use connected accounts interactively. Revisit then, at project scope.
- **CLI:** the Windows build is experimental, and Composio says not to build integrations on it.
- **Python SDK:** a new dependency tree in `.venv`, which Whisper shares. Our research code is standard library only.
- **REST:** the same key, no installs, and every call is explicit and auditable.

## Toolkit audit (`ss composio audit` -> `data/local/composio/toolkit_audit.csv`)

| Toolkit | Login | Read-only tools | Useful for us |
|---|---|---|---|
| Instagram | Composio-managed OAuth (Instagram Login); needs a **Business or Creator** account | 9 of 16: user info, user/post insights, media, comments | **Yes:** our own Reels insights (reach, plays, saves, shares) for prototype tests. Today that's manual |
| YouTube | Composio-managed OAuth | 10 of 14: channel and video stats, our playlists, our captions | Partly. Public stats duplicate `ss yt`. No YouTube Analytics (retention, average view percentage), so it doesn't replace YouTube Studio exports |
| TikTok | **Own TikTok developer app needed** (client key and secret in the Composio dashboard; TikTok may review scopes) | 5 of 9: our profile, stats, video list | Our own posts' stats only. No public or trend research; Creative Center stays manual |
| Google Drive | Composio-managed OAuth | 21 of 51 | Handoffs: put bundles and packets in a Drive folder ChatGPT or Gemini can read. Note: Claude already has a Google Drive connector in this workspace (claude.ai), so this is only needed for scripted `ss` use |
| Google Sheets | Composio-managed OAuth | 10 of 36 | Read the owner's latest Marketing Bank from a Sheet instead of a pasted snapshot |
| Google Analytics | Composio-managed OAuth | 0 of 4 (account and audience listing only) | No: no report queries. We have no website to measure |
| Search Console | Composio-managed OAuth | 5 of 6 | No (no website) |
| Reddit | Composio-managed OAuth | 5 of 10 | Maybe, for community wording research, under Reddit's own Data API terms; ask first |
| Twitch | Composio-managed OAuth | 0 tools listed | No; `ss twitch` covers it |
| vidIQ MCP | vidIQ's own login or key | 40 of 61 | Uses **vidIQ credits**: only with an agreed budget |
| YouTube Transcript | third-party key | 7 of 9 | No: paid credits; captions need owner rights anyway |
| Roblox | own Open Cloud key | 180 of 347 | Not now: Studio MCP and `ss rbx` cover filming and stats; never give it the game's keys |
| Facebook, TikTok Ads, Metricool | various | various | No: no ads, no Page, no scheduler |

## What Composio could automate (once the owner authorises an account)

1. **Prototype measurement:** pull our own Instagram Reel insights (and TikTok post stats, once a TikTok app exists) at 48 h into a dated CSV for the C15 opener test. This replaces screenshots and manual copying. YouTube retention still comes from YouTube Studio's export.
2. **Handoffs:**
   - Upload `exports/share/bundles/*.zip` and Gemini packets to one Drive folder, instead of Downloads and manual uploads.
   - Read the Marketing Bank from Sheets.

Integrations we'd no longer need to build ourselves: Google OAuth (consent screen, tokens, refresh) for Drive and Sheets, Instagram Login OAuth, and TikTok token refresh.

## Rules

- **Read-only by default.** Only allow-listed read tools run. Composio's managed logins may grant broader permissions (YouTube upload, Instagram posting and DMs). Writing, posting, uploading, DMs and comment replies are publishing: ask first, every time.
- **Provider terms still apply** to data that comes through Composio (YouTube 30-day storage, no cross-channel aggregation). Label rows `source=composio:<toolkit>` with `observed_at_utc` and `run_id`, like our other collectors.
- **Data passes through Composio's servers.** Hobby doesn't include zero data retention. Don't send secrets, raw footage or the game repo.
- **Never pay.** Hobby can't bill. vidIQ credits, YouTube Transcript credits and other paid tools need approval.
- Connecting an account is an owner OAuth step. Claude creates the link only when the owner asks.

## Next action (owner)

To measure the prototype, decide whether to connect **Instagram** (needs a Business or Creator account) and/or **Google Drive/Sheets**. Claude then creates the connect link, and you approve it in the browser. TikTok first needs a TikTok for Developers app.
