# Smoke test

Run 2026-11-24T02:51:03+00:00 by `.\ss smoke`. Outputs in `out/smoke/`.
WARN in a render check is about the sample footage (a dark 1422x430 preview strip), not the pipeline.

| Check | Result | Detail |
|---|---|---|
| Installed tools | **PASS** | git: git version 2.55.0.windows.3; node: v24.19.0; ffmpeg: ffmpeg version 9.1-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers; ffmpeg filters: all present; obs: installed; kdenlive: installed; kokoro venv: installed; kokoro model: present |
| Glossary corrections | **PASS** | 12 term-correction checks passed |
| Whisper transcription | **PASS** | glossary: 'slug's Hoh' -> 'Slugshot' / 27 words, 11 caption lines -> C:\Users\runni\slugshot marketing\out\smoke\narration.srt / Check these low-confidence words: Slugshot |
| Kokoro voice + Whisper round trip | **PASS** | Whisper heard: "He brought Inferno, I brought Floppy, Slugshot on Roblox" |
| Audio tidy + ducked mix | **PASS** | narration 12.7s -> tidied 10.4s; ducked music mix written |
| FFmpeg vertical render + QC | **PASS** | out\smoke\ffmpeg_vertical.mp4 13.1s |
| Remotion template render + QC | **PASS** | out\smoke\smoke.mp4 15.2s |
| MakeMyClip setup | **PASS** | clip doctor OK, workspace = media\ (whisper.cpp intentionally not installed) |
| YouTube collector dry run | **PASS** | discover -> stats -> report (+ data dictionary) on fake fixtures, no network |
| YouTube collector live call | **PASS** | 1/1 snapshots -> C:\Users\runni\slugshot marketing\out\smoke\yt_live\youtube_snapshots.csv (~1 units) |

## Manual checks (a person must do these)

- Watch `out/smoke/ffmpeg_vertical.mp4` and `out/smoke/remotion.mp4` on a phone: captions readable, in time with the voice, clear of the platform buttons; audio clean.
- Listen to `out/smoke/kokoro.wav`: is the voice good enough to use, or should narration be recorded?
- Read `out/smoke/narration.srt` against the narration; add new mishearings to config/glossary.json.
- Record 20 s of real gameplay in OBS and run it through `.\ss import`, `caption`, `render`.
