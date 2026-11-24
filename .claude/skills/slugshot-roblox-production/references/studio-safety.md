# Studio safety

## The enforced boundary

`.claude/settings.json` runs `roblox-native/tools/studio_guard.py` before every `mcp__Roblox_Studio__*` tool call (except listing Studio windows, docs and skill lookups). The guard opens its own connection to Studio's MCP server and allows the call only if:

1. exactly one Studio window is open;
2. its file is `SlugshotMarketing.rbxlx`;
3. the call's `studio_id` is that window;
4. `ServerStorage.SlugshotMarketingMarker` equals the token in `roblox-native/studio/marker.json` (read in Edit, or Server during play).

Errors, timeouts and a failing hook all deny. Decisions are logged in `roblox-native/capture/logs/studio-guard.log`.

If you're denied: tell the owner what's open. Offer `.\ss roblox switch`, which only runs when the owner asks: it stops a playtest, saves (Ctrl+S, never publish) and closes other places, then opens the marketing place. Don't try any other route.

Also enforced:
- **Ask first:** asset insertion, AI generation, image upload, Open Cloud, sub-agent and skill-edit tools.
- **Deny:** starting `StudioMCP`/`mcp.bat` from a shell.

## Limits (say these plainly; never call the checklist the boundary)

- The guard covers Claude Code sessions in this repo only. Not Codex, ChatGPT desktop, sessions started in other folders, or a person in Studio.
- There's a sub-second gap between check and call.
- Once allowed, Luau runs with Studio's power inside the marketing place. The place is disposable: rebuild it with `.\ss roblox rebuild` (or `build` when Studio is closed).
- Shell deny rules match command text; indirect launches could evade them. Don't write any.

## The marketing place

- Built by `tools/make_marketing_place.py` from a snapshot of `../slugshot/build/SlugshotLobbyTraining.rbxlx` (hash and game commit in `studio/provenance.json`). Keeps the lobby, training arena, guns, slugs, VFX and lighting.
- Marketing-only patches: both `SettingsStore.connect()` return `MarketingIsolated` (no DataStores ever); the marker and provenance values sit in ServerStorage.
- The audit (`.\ss roblox audit`) found no HTTP requests, messaging, purchases, teleports, badges, analytics or dynamic code. `InsertService:LoadAsset` reads the game's own uploaded models (kept for fidelity).
- Never publish it. The `.rbxlx` files are git-ignored (they hold the game's private asset IDs).
- **New game build:** close Studio's marketing window, run `.\ss roblox build` (copies the current build, re-patches, keeps the marker), re-run the audit and read new findings before use.
