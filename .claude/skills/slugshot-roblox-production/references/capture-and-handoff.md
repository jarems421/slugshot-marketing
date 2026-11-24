# Capture and handoffs

## Running a take (MCP, marketing place only)

```
list_roblox_studios                     -> the marketing window's id (changes on every reopen)
start_stop_play(is_start=true)
execute_luau(Client): wait for Players.LocalPlayer.Character, then
  return require(game.ReplicatedStorage.SlugshotMarketing.Scene).runJson("<id>", {take="<id>_v01"})
start_stop_play(is_start=false)         when done
```

- `runJson` yields until the take ends and returns the manifest: truth block; Reel marks (start, cut, end with elapsed and Unix-ms `at`); cues and markers; camera samples.
- Save the manifest to `roblox-native/capture/takes/<take>.json`.
- Large manifests: return a summary (start/end `at`) if the response would be huge.
- Each take builds its set and actors in setup and destroys them in cleanup, so the next take starts identical. Reel restores the camera and UI.

## Recording

- **OBS (production):**
  - two scenes, "Slugshot Gameplay" (window, game audio, optional HUD) and "Slugshot Clean Stage" (tightly cropped viewport, no overlays);
  - press Ctrl+Shift+G in the playtest to hide Roblox's top bar, which scripts can't hide;
  - record and note when recording started (Unix ms), then `.\ss roblox import <take.json> <obs.mkv> --video-start-ms <ms>`.
  - Replay Buffer suits organic play; full start/stop suits staged takes.
- **Studio `video_capture` (previews/tests):**
  - call it with `is_start=true` before `runJson` and `false` after;
  - it returns an mp4 plus a manifest with `creation_timestamp_ms` on the same clock as the marks, so use `.\ss roblox import <take.json> <video.mp4> --capture-manifest <manifest.json>`;
  - measured: 2368x1104 at about 27 fps, with dropped frames and a 1.1 s client stall in one take. Not for final footage.
- **Automated OBS (future, not built):** OBS WebSocket (built into OBS 28+, use authentication). Sequence: validate scene -> OBS start -> run take -> wait for end mark -> OBS stop -> `ss roblox import`. Build it only after manual recording is routine.

## Into the existing toolkit

- `ss roblox import` trims to start..end (stopping one frame early, before the HUD returns) and calls `ss import`.
- The result is named `media/raw/SS_<date>_<STAGED|STAGEDPLAY|HYBRID>_<Concept>_Take_Vnn_RAW.mp4`, with `<same>.take.json` beside it.
- Then: `ss sheet` (review), `ss candidates` (Gemini CSV for long sessions), `ss caption` / `ss assemble` (scripts, VO, captions, music), `ss render` / `ss batch` (presets; WORLD/SKIT/AISCENE keep labels), `ss qc`.
- Real gameplay sessions go through Gemini with the existing header: `start,end,what_happens,why_a_stranger_could_care,emotion,best_format,hook_idea,payoff,confidence,potential_misinterpretation`.

## Hybrid Roblox -> anime/manga -> Roblox

- Stage the Roblox shot with a **bridge frame**: clean silhouette, held pose, readable position. Add markers `CUTAWAY_OUT` and `CUTAWAY_IN` in the timeline.
- Export the bridge frame (`ffmpeg -ss <t> -frames:v 1`) as the reference still for Flow/Manga tools. The cutaway comes back into `media/flow/` and is assembled as an `AISCENE`-labelled scene between the two Roblox parts.
- Truth mode `hybrid_bridge` with a label. The cutaway is fantasy, never gameplay.

## Gameplay modes

- **authentic_gameplay:** real players or clients, real outcomes. The runner may only position a spectator camera; it never scripts outcomes. Second angles of the same live moment need a replay recorder, which is deferred.
- **staged_gameplay:** real mechanics with a scripted setup or outcome (e.g. a StudioTestService multi-client demo). Its metadata must say `match_outcome: scripted`, and it is never captioned as an organic match.
