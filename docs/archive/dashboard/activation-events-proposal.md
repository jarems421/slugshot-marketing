# Proposal: in-game activation events (for owner approval, not implemented)

**Status:** proposal only. Nothing in `../slugshot` or the live experience has been changed. Implementing it is game development, so it needs the owner's go-ahead, and it only produces data once the experience is published.

**Why:** the dashboard's Activation stage ("onboarding and first meaningful gameplay") has no data source. Roblox's own analytics give players, retention and revenue, but not how far a new player gets in their first session. Roblox's onboarding funnel does, and the Analytics Query API exposes it (`FunnelStepTotalCount`, `FunnelStepCompletionRate`, `FunnelUserOverallCompletionRate`; dimension `FunnelStep`), so the dashboard can read it with the same key.

## Proposed onboarding funnel (one-time per player)

`AnalyticsService:LogOnboardingFunnelStepEvent(player, step, stepName)`, server-side only, logged on success (not on attempt). Steps follow what the current build has (`docs/game-truth.md`; re-check `../slugshot/docs/status.md` before implementing):

| Step | Name | Logged when | Notes |
|---|---|---|---|
| 1 | Player Joined | `Players.PlayerAdded` | funnel anchor (not a duplicate of DAU) |
| 2 | Loading Done | loading screen dismissed | separates load failures from disinterest |
| 3 | Lobby Reached | character spawned in Slug Grove | |
| 4 | Slug Equipped | first slug loaded into the blaster | |
| 5 | First Shot | first slug fired | first meaningful action |
| 6 | Training Entered | through the training-arena portal | |
| 7 | First Hit | first slug hit on a target or dummy | |
| 8 | First Match | first PvP round started (when PvP ships) | leave out until matchmaking exists |

Optional, same budget: one recurring funnel `Session` (`LogFunnelStepEvent` with a per-session `funnelSessionId`) for returning players: Joined → First Shot → Round Played. Use custom fields (max 3, strings) for slug name, e.g. `CustomField01 = "Slug - Floppy"`, rather than more event names.

## Budget against Roblox's limits

1 onboarding funnel (of 10), 8 steps (of 100), 0-1 recurring funnels, 0 custom event names (of 100). Rate limit `120 + 20 × CCU` events/min is far above eight one-time events per new player. Studio play-tests aren't recorded; verify in the published experience's **View Events** panel; charts fill in about 24 h after the first event.

## Implementation plan (when approved)

1. Owner approves the step list (and whether step 8 waits for PvP).
2. In `../slugshot`, one server module `OnboardingAnalytics` with a `step(player, n)` guard (each step once per player, never trusting client step numbers); call sites at the eight points above.
3. Test in a private published build; check View Events.
4. Dashboard: add `FunnelStepTotalCount` with `breakdown: ["FunnelStep"]` to the Roblox connector (one query; the `onboarding_step_users` metric is already defined) and show the step drop-off on the Game page.

Source: Roblox AnalyticsService guidance via the Studio `rbx-instrument-analytics` skill (method signatures, limits and pitfalls) and the Analytics Query API metric list (create.roblox.com/docs/cloud/guides/analytics/metrics), read 2026-11-25.
