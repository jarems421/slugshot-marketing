# Command reference

Run from the workspace folder: `.\ss <command>` (PowerShell) or `ss <command>` (cmd). Add `-h` to any command for every option. Paths can be relative to the workspace.

| Command | Does | Inputs | Outputs | Limits |
|---|---|---|---|---|
| `doctor` | versions and setup check | none | console | none |
| `smoke` | runs every capability once (13 checks) | `media\sample\` | `reports\smoke-test.md`, `out\smoke\` | ~5 min; 1 YouTube quota unit |
| `import <file> --format F --concept C --hook H [--note]` | copies a recording into `media\raw\` with the naming convention | any video/audio | `media\raw\SS_<date>_F_C_H_Vnn_RAW.<ext>`, row in `media\capture_log.csv` | copies, never moves |
| `voice "<text>" <out.wav>` / `voice --file script.md <out.wav>` | Kokoro AI narration with glossary pronunciations | text | WAV (24 kHz) | CPU; quality needs a person's ear; label AI voice where required |
| `audio tidy <in> <out> [--denoise] [--speed 1.05]` | voice clean-up: high-pass, denoise, long pauses cut to 150 ms, levelling | WAV/MP3/M4A | WAV 48 kHz, -16 LUFS | speed-ups above ~1.1x hurt comprehension |
| `audio mix <out> --narration VO [--music BED] [--sfx f@sec ...]` | ducked music bed + timed SFX under the voice | audio files | WAV, -14 LUFS | only licensed files (`assets\LICENSES.csv`) |
| `caption <audio/video>` | Whisper transcript, glossary fixes, invented-word filter | audio or video | `.srt`, `.words.json`, `.whisper.json` | CPU base.en; read the `.srt`; big garbles can slip through |
| `fixcaps <file.srt/.words.json>` | re-applies `config\glossary.json` | caption files | files corrected in place | glossary terms only |
| `vertical <clip> <out.mp4> [--narration --srt --hook --fit --start --duration]` | quick FFmpeg 1080x1920 render + QC | one clip | MP4 + `.qc.json` | phrase captions only; no presets |
| `render <name> <clip> --format F [--narration --captions --hook ...]` | Remotion template (one clip) + QC | one clip, optional VO/captions | `exports\<name>.mp4` + `.qc.json` | one clip; use `assemble` for scenes |
| `batch <jobs\x.json>` | several variants (hooks/formats) from one asset set | job file | masters + `exports\share\variants_log.csv` | ~30 s per 13 s variant |
| `assemble <jobs\edit.json> [--test]` | **multi-scene** edit: video (MP4/MOV/MKV), stills (PNG/JPG/WEBP), text cards, script -> voice or recorded WAV, tidy, music, SFX, captions, emphasis, punch-ins, push-ins, fades, per-scene labels, scenes synced to the script | edit file | `exports\SS_..._MASTER.mp4`, log row, working files in `out\assemble\` | no crossfades (cuts and fade-from-black); a scene longer than its clip holds the last frame |
| `candidates <video> <gemini.csv> [--pad 5]` | cuts Gemini's timestamped moments with padding and burned-in source timecode | recording + CSV with `start,end` | `media\candidates\<video>\NN_*.mp4` + `index.csv` | nothing is chosen automatically |
| `sheet <video> [--every 1]` | frame sheet for creative review | video | `<video>.sheet.jpg` | stills only; watch the video too |
| `qc <video> ...` | technical checks | MP4 | console, `.qc.json`, `reports\qc_log.csv` | technical only |
| `studio` | Remotion Studio (Vertical and Story compositions) | none | browser | uses files staged in `public\` |
| `clip <args>` | MakeMyClip CLI (silence removal, trims, reframe, export to Resolve/Premiere XML) | files under `media\` | MakeMyClip workspace in `media\` | paths outside `media\` refused |
| `yt discover/stats/report/prune` | public YouTube stats (key in `.env`) | queries / IDs | `data\local\youtube_snapshots.csv`; report + data dictionary in `exports\share\` | 30-day storage; per-video maths only; free quota only (ask before anything paid); share for internal analysis, don't publish |
| `export` | checks hand-entered platform metrics, writes a shareable copy | `data\local\platform_metrics.csv` | `exports\share\platform_metrics_<date>.csv` | numbers must be typed in from each platform's analytics |

## Edit file keys (`assemble`)

Top level: `concept`, `hook_id`, `format` (preset), `script` or `narration`, `voice` {`voice`, `speed`}, `tidy`, `sync` ("script"), `music`, `music_db`, `sfx` [{`src`, `at`}], `captions` ("auto" / path / null), `emphasis` [words], `hook`, `label`, `end_card`, `end_title`, `end_subtitle`, `accent`.

Scenes: `kind` (video/image/card), `src`, `text`, `seconds`, `trim_start`, `fit` (crop/blur/contain), `volume`, `zoom`, `punch_at` [s], `transition` (cut/fade), `label`, `captions` (true/false).

Examples: `jobs\edit-sample-story.json`, `jobs\sample-variants.json`; script format: `jobs\scripts\sample-story.md`.
