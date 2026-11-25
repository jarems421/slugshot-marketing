# Dashboard redesign and learning loop: 2026-11-25

The final usability and design pass before content production. Principle: the minimum useful information by default, and detail only when you click into it. Guide: [docs/dashboard/README.md](../docs/dashboard/README.md). Screenshots: [docs/dashboard/screens/](../docs/dashboard/screens/) (`fixture-*` populated with test data, `live-*` the real current state).

## What changed

| Area | Now |
|---|---|
| Navigation | Overview, Content, Publish, Roblox, Settings. Research and Experiments are no longer pages; their systems, data and CLI are unchanged. |
| Overview | Combined views and followers, with the change against the previous period. Watch time is a secondary line. Views per day and the accounts list. Filters: 7/30/90 days, all time, custom; platform; account; language. |
| Drill-downs | **Views**: trend, platform and account breakdowns (click to narrow), watch time, average view, engagement, videos, compare similar videos. **Followers**: growth, net change, gains and losses, subscriber attribution (YouTube only). **Account** pages. |
| Content | **Concepts**: a gallery of local videos waiting to post, grouped by concept with language versions, played in the app. The render registry is folded in: an unregistered render is registered the first time it's published. **Published**: a filterable, sortable gallery of posts. One video on several accounts is one card, and each post keeps its own analytics. |
| Publish | What needs you, uploads in progress, posted (collapsed), accounts (collapsed). New post picks from the video gallery. Route, file and log are under Advanced. Every safety check is unchanged (server-side). |
| Roblox | A clean empty state before launch. After launch: KPI strip, players per day, collapsible retention, acquisition, monetisation and funnel. |
| Settings | Collapsible sections. Service usage and quotas for Cloudinary, Buffer, YouTube, TikTok, Google sign-in, Twitch and Composio, each figure labelled Live, Estimate or Limit only. |
| Appearance | System = blue night (owner's choice), Dark = black, Light = paper white with opaque surfaces. Jami's night sky and shooting stars are ported from its components, can be switched off, and respect reduced motion. |

## Light-mode text

The grainy look came from text drawn on translucent layers: panels, nav and top bar used `rgba(…, 0.82)` plus gradient overlays. Chromium on Windows then falls back from ClearType to greyscale antialiasing, which makes Urbanist's thin strokes fuzzy. Fixed with opaque surfaces everywhere in light mode, slightly heavier body text (500) and darker secondary text. It isn't a colour change.

## Measurement decisions (made independently; easy to change)

- Previous-period comparisons appear only when every account was measured the same way in both periods. Otherwise none is shown.
- TikTok and Instagram period views come from daily snapshots. A video first tracked long after posting counts only in "all time" and marks the period "partly measured".
- Follower change uses the platform's gained/lost figures where reported, otherwise the difference in counts. If the first reading falls inside the range, it's "since first reading".
- Average view duration is the views-weighted average of each video's own reported average. Total watch time ÷ total views mixed videos with and without watch-time data.
- Checkpoint tolerances: 24 h ±6 h, 48 h ±8 h, 7 days ±24 h. Accounts with a video under 8 days old refresh every 4 hours so readings land in those windows. Buffer cost: about 1 request per account per refresh.
- Characters for tags come from the game's names in the caption glossary. The characters knowledge bank holds guidance, not names.

## Fixes found on the way

- Buffer overwrote a video's native title when it joined an existing record. It now only names videos it records first.
- `ss kb brief` skipped the whole claims bank, so our own findings could never reach a brief. It now includes claims whose evidence is `owned_result`.
- `ss dash demo` failed while a demo server held its database. It now stops the demo server first; the live server is never touched.
- The fixture generator still wrote the old `@fixture` YouTube handle.

## Tests

- Unit tests: 145 pass in one run (`test_publish`, `test_dashboard`, `test_knowledge`, `test_analysis`, `test_research`, `test_analytics`).
- `ss smoke`: 30/30. `--research`: 10/10. `--dashboard`: 7/7.

## Still needs real content

- Buffer post metrics, readings at 24 h / 48 h / 7 days and comparisons all need real posts.
- The first end-to-end run is: produce → approve → publish → collect → tag → compare → finding. It's verified on fixtures, but a live run needs the owner to approve a first real post in the dashboard.
- Six test drafts are still in Publish: YouTube EN/ES private, TikTok EN inbox, and Buffer drafts for TikTok EN/ES and Instagram EN.
