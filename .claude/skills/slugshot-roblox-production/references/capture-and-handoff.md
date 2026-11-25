# Capture and handoffs

## Filming a staged scene (production route, marketing place only)

Film mode is how staged footage is made. It is deterministic, native-resolution vertical, and exact to the frame.

**Preferred recorder (2026-11-25): `ss roblox rec`.** Studio's own recorder encodes at about 6 Mbps, which smeared close-up detail (owner: slugs "look low quality up close"). Instead:

```
.\ss roblox rec start media\takes\<take>_g01.mkv     (run in the background)
execute_luau(Client): Scene.start("film", "<id>", {hold = 2}); poll until not _G.SlugshotTake.running
.\ss roblox rec stop
save the manifest (_G.SlugshotTake.json minus "camera") to roblox-native/capture/takes/<take>.json
.\ss roblox film roblox-native\capture\takes\<take>.json media\takes\<take>_g01.mkv [g02 ...] --crf 12
```

- It records only the Studio window whose title names SlugshotMarketing (Windows Graphics Capture, not the screen; never use gdigrab, which records the owner's desktop). It runs without the cursor, at x264 CRF 8 4:4:4, with no 30 s cap.
- Scene.film shows a magenta calibration card first, so the decoder crops to the viewport.
- A full take at hold 2 missed about 10% of frames. A second full pass at hold 4 plus one hold-8 patch brought that to 0 repeated (decode passes all recordings; later ones only fill gaps).
- Masters render at Remotion CRF 14 (about 13 Mbps). The Studio-recorder route below still works as a fallback.

```
list_roblox_studios                     -> the marketing window's id (changes on every reopen)
start_stop_play(is_start=true); execute_luau(Client): task.wait(7)   -- the game finishes loading
execute_luau(Client): Scene.still("<id>", t) for key moments, then a 1-2 s video_capture to SEE them
for each chunk (<= ~170 frames; the recorder stops at 30.0 s):
  video_capture(is_start=true)
  execute_luau(Client):
    local Scene = require(game.ReplicatedStorage.SlugshotMarketing.Scene)
    Scene.start("film", "<id>", {take = "<take>", hold = 6, first = A, last = B, preroll = 1.5})
    -- poll until not _G.SlugshotTake.running, return a summary
  video_capture(is_start=false)  -> copy the mp4 to media/takes/<take>_<n>.mp4 AT ONCE
save the full-take manifest (frames, stamp, viewport, truth, marks) to roblox-native/capture/takes/<take>.json
.\ss roblox film roblox-native\capture\takes\<take>.json media\takes\<take>_0.mp4 media\takes\<take>_1.mp4 ...
  -> out/takes/<take>.mp4: 1080x1920, 30 fps. If it lists "re-film: 125-128", run one more chunk with
     first/last covering it and decode again with all recordings (later recordings only fill gaps).
```

Why it works:
- Scene frame i (t = i/30) is held for `hold` rendered frames, with its index stamped in squares at the viewport's left edge (outside the picture).
- The decoder keeps the best recorded frame of each index from any recording, so drops and stalls cost nothing.
- The camera is rolled a quarter turn so the 9:16 frame lies along the viewport's long side, giving native pixels and no upscaling.
- World particles are slowed to scene time while filming.

Measured (2026-11-25):
- the recorder stops at 30.0 s;
- it dropped 784 frames in one capture, with gaps over 240 ms 1% of the time and one 1.7 s stall;
- its temp folder is deleted when play restarts;
- 4 full takes decoded with 0 repeated frames after chunking and one 4-frame patch.

Facts to remember:
- `screen_capture` without camera arguments didn't show the play viewport; use `video_capture` grabs as the truth.
- The player's avatar must stay in the world (the lobby's presentation follows it); the runner hides it and parks it under the set (the game draws a blaster holster on its back outside the character model, which showed as black blobs).
- Local lights lose their shadows during takes (Roblox reassigns a few shadow maps as the camera moves, so shadows flashed on the slugs); `look.local_shadows: true` keeps them.
- Camera.Focus follows the shot, or Roblox drops detail on distant set pieces and small actors.
- The camera is re-applied at the last render priority each frame, so game camera scripts can't move it.

`Scene.run(id, {speed})` is a real-time preview of the same frames (fine for checking motion by eye, not for final footage).

## Real gameplay (OBS)

- Organic PvP can't be staged, so it is recorded with OBS:
  - scenes "Slugshot Gameplay" and "Slugshot Clean Stage";
  - Ctrl+Shift+G hides Roblox's top bar.
- Then `.\ss roblox import <take.json> <obs.mkv> --video-start-ms <ms>` or `ss import`.
- OBS WebSocket automation stays deferred: staged scenes no longer need OBS.

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
