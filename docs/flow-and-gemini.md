# Bringing in Google Flow clips and Gemini timestamps

Both are manual hand-offs: you download or copy from the Google app, then one command takes over. Nothing here connects to Google.

## Flow clips and stills

1. In Flow, generate from approved reference stills (Ingredients/Frames). In the UK, Flow can't edit uploaded videos, so don't upload gameplay to restyle it. Pick 9:16 where the shot allows.
2. Download the MP4 (or a PNG frame) into `media\flow\`. Name it after the scene, e.g. `media\flow\floppy_dream_v1.mp4`.
3. Check it frame by frame against the reference stills: same silhouette, proportions, face and colours; Floppy never transforms. Reject any drift.
4. Use it in an edit file as an AI scene, always labelled:
   ```json
   {"kind": "video", "src": "media/flow/floppy_dream_v1.mp4", "seconds": 3, "fit": "crop",
    "transition": "fade", "label": "AI-generated scene"}
   ```
   or render a whole AI clip with `ss render <name> media\flow\x.mp4 --format AISCENE`.
5. Add the AI disclosure on each platform when you upload.

Flow clips usually carry their own generated audio. Set `"volume": 0` on the scene if it clashes with the narration.

## Gemini gameplay analysis

1. Record a session in OBS, then run `ss import <recording> --format PVP --concept Session --hook Raw`.
2. Upload that file to Gemini (15-30 minute chunks are safer than an hour). Use the research PDF's gameplay-analysis prompt, adding this line at the end:
   > Also return your candidates as CSV in a code block with exactly these columns:
   > `start,end,what_happens,why_a_stranger_could_care,emotion,best_format,hook_idea,payoff,confidence,potential_misinterpretation`
   > Times as M:SS or seconds. Use UNCERTAIN where unsure.
3. Save the CSV next to the recording, e.g. `media\raw\SS_..._RAW.gemini.csv`.
4. Cut the candidates:
   ```powershell
   .\ss candidates media\raw\SS_..._RAW.mkv media\raw\SS_..._RAW.gemini.csv
   ```
   Each moment becomes a short clip with 5 s either side, the original timecode burned in, and "GEMINI MOMENT" shown inside Gemini's range.
5. Watch every clip. In `media\candidates\<recording>\index.csv`, fill in `verified`, `keep`, `true_start` and `true_end` (Gemini's times can be off; the burned-in timecode gives the real ones).
6. Build edits from the kept moments using the true times (`trim_start` and `seconds` in an edit file, or `--start`/`--duration` in `ss vertical`).

Gemini never makes the final selection, and its descriptions of what an ability "did" are not evidence of a mechanic. Check `docs/game-truth.md`.

Privacy: unreleased footage goes to Google when you upload it. Check the Gemini activity setting first (see the research PDF). Don't give Gemini or ChatGPT the YouTube API reports from `data\local\reports\`.
