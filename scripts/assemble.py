r"""Assemble a multi-scene vertical video from an edit file (Remotion `Story` composition).

  .\ss assemble jobs\edit-sample-story.json [--test]

Edit file (JSON), paths relative to this folder:
  {
    "concept": "FloppyBirthday", "hook_id": "Ep1", "format": "WORLD",   -> SS_<date>_WORLD_FloppyBirthday_Ep1_Vnn_MASTER.mp4
    "script": "jobs/scripts/floppy-birthday.md",    approved script; spoken lines become narration if no "narration"
    "voice": {"voice": "am_puck", "speed": 1.1},    Kokoro settings for the script
    "narration": "media/vo/recorded.wav",           OR your own recording (takes priority over "script")
    "tidy": true,                                   clean the voice first (pause trimming, levelling)
    "music": "assets/music/bed.mp3", "music_db": -6,     bed levelled to -16 LUFS, then this gain
    "sfx": [{"src": "assets/sfx/whoosh.wav", "at": 3.0}],     seconds on the final timeline
    "ambience": "out/takes/x_world.wav", "ambience_db": 0,   the world track from scripts/soundscape.py, from 0 s
    "captions": "auto",                             "auto" = transcribe the voice; or a checked .srt; or null
    "emphasis": ["Floppy", "Inferno"],              words always shown in the accent colour
    "hook": "In my world, your slug is your rank",
    "scenes": [
      {"kind": "card",  "text": "In my world...", "seconds": 1.5},
      {"kind": "image", "src": "media/flow/ref.png", "seconds": 2.5, "zoom": 1.1},
      {"kind": "video", "src": "media/raw/x.mkv", "trim_start": 12.0, "seconds": 3, "fit": "crop",
       "punch_at": [1.2], "volume": 0.3, "transition": "fade", "label": "AI-generated scene"}
    ]
  }
"dialogue": "out/dialogue/<id>/dialogue.json"   character dialogue from `ss dialogue`: its performed audio is the
    voice (never tidied: pauses are acting), its script-aligned words are the captions (speaker colours), and any
    "at" (SFX) may be a line anchor such as "L4.end+0.1". Replaces "script"/"narration"/"captions".
"sync": "script" times each scene to its [stage direction] block of the script (needs "captions": "auto"
and one block per scene); scene "seconds" are then ignored. Otherwise, if the narration is longer than
the scenes, the last picture scene is extended to cover it.
Anything not set comes from the format preset in config/formats.json. Spoken lines in a script are all
lines except blank ones, lines starting with '#', and [bracketed stage directions].
"""
import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import batch
import render

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
PY_TTS = ROOT / ".venv-tts" / "Scripts" / "python.exe"
FORMATS = json.loads((ROOT / "config" / "formats.json").read_text(encoding="utf-8"))
IMAGE = {".png", ".jpg", ".jpeg", ".webp"}
REMUX = {".mkv", ".flv", ".ts", ".avi"}


def sh(cmd):
    r = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"failed: {' '.join(map(str, cmd[:4]))} ...\n{(r.stderr or r.stdout)[-800:]}")
    return r.stdout


def duration(path):
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).strip())


def script_blocks(script):
    """Spoken text per [stage direction] block; text before the first direction is its own block."""
    blocks = [""]
    for line in Path(script).read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("#"):
            continue
        if re.match(r"\s*\[[^\]]*\]\s*$", line):
            if blocks[-1].strip():
                blocks.append("")
            continue
        blocks[-1] += " " + re.sub(r"\[[^\]]*\]", "", line).strip()
    return [b.strip() for b in blocks if b.strip()]


def spoken_lines(script):
    return " ".join(script_blocks(script))


def sync_to_script(scenes, script, words_json, voice_len):
    """Set each scene's length so it starts when its block of the script is spoken (from Whisper word times)."""
    blocks = script_blocks(script)
    if len(blocks) != len(scenes):
        raise SystemExit(f'"sync": "script" needs one script block per scene ({len(blocks)} blocks, {len(scenes)} scenes)')
    words = json.loads(Path(words_json).read_text(encoding="utf-8"))
    counts = [len(b.split()) for b in blocks]
    total = sum(counts)
    starts, before = [], 0
    for c in counts:  # map script word positions onto Whisper's words proportionally (merges/splits differ)
        idx = min(round(before / total * len(words)), len(words) - 1)
        starts.append(0.0 if before == 0 else words[idx]["startMs"] / 1000)
        before += c
    ends = starts[1:] + [voice_len + 0.4]
    for s, a, b in zip(scenes, starts, ends):
        s["seconds"] = round(max(b - a, 0.5), 2)
    print("scene starts (s): " + ", ".join(f"{t:.2f}" for t in starts))


ANCHOR = re.compile(r"^L(\d+)(?:\.(start|end))?\s*([+-]\s*[0-9.]+)?$")


def when(value, dialogue):
    """Seconds, or a dialogue line anchor ("L3", "L3.end-0.1")."""
    if isinstance(value, (int, float)):
        return float(value)
    m = ANCHOR.match(str(value).strip())
    if not m or not dialogue:
        raise SystemExit(f"can't resolve time {value!r} (line anchors need \"dialogue\")")
    line = {ln["n"]: ln for ln in dialogue["lines"]}[int(m.group(1))]
    return round(line[m.group(2) or "start"] + float((m.group(3) or "0").replace(" ", "")), 3)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edit_file")
    ap.add_argument("--test", action="store_true", help="mark the render as non-production for Remotion")
    ap.add_argument("--out-dir", help="write the video here instead of exports/ (and don't log it)")
    a = ap.parse_args()
    edit = json.loads(Path(a.edit_file).read_text(encoding="utf-8-sig"))
    fmt = edit.get("format", "WORLD").upper()
    preset = {k: v for k, v in FORMATS[fmt].items() if k != "description"}
    name = batch.next_name(date.today().strftime("%Y%m%d"), fmt, edit["concept"], edit.get("hook_id", "Edit"))
    work = ROOT / "out" / "assemble" / name
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    stage_dir = ROOT / "public" / name
    shutil.rmtree(stage_dir, ignore_errors=True)
    stage_dir.mkdir(parents=True)

    # 1. Voice: character dialogue, recorded narration, or the approved script through Kokoro.
    voice, dialogue = None, None
    if edit.get("dialogue"):
        dialogue = json.loads(Path(edit["dialogue"]).read_text(encoding="utf-8"))
        voice = Path(dialogue["audio"])
        flagged = [f"line {ln['n']}" for ln in dialogue["lines"] if ln.get("deviations")]
        print(f"dialogue: {dialogue['id']} ({dialogue['engine']}, {dialogue['duration']}s)"
              + (f"; performance differs from script on {', '.join(flagged)}" if flagged else ""))
    elif edit.get("narration"):
        voice = Path(edit["narration"])
    elif edit.get("script"):
        text = spoken_lines(edit["script"])
        opts = edit.get("voice", {})
        voice = work / "voice.wav"
        sh([PY_TTS, "scripts/voice.py", text, voice, "--voice", opts.get("voice", "am_puck"),
            "--speed", opts.get("speed", 1.1)])
        print(f"voice: Kokoro {opts.get('voice', 'am_puck')} from {edit['script']}")
    if voice and edit.get("tidy") and not dialogue:
        sh([PY, "scripts/audio.py", "tidy", voice, work / "voice_tidy.wav"])
        voice = work / "voice_tidy.wav"

    # 2. Captions from the clean voice (before music is added).
    captions = edit.get("captions")
    if dialogue:
        captions = str(Path(edit["dialogue"]).with_name("dialogue.words.json"))
    elif captions == "auto":
        if not voice:
            raise SystemExit('"captions": "auto" needs a script or narration')
        print(sh([PY, "scripts/caption.py", voice, "--out", work / "voice"]).strip())
        captions = str(work / "voice.srt")

    # 3. Mix: ducked music + SFX + the world track on the voice.
    mix = voice
    if voice and (edit.get("music") or edit.get("sfx") or edit.get("ambience")):
        cmd = [PY, "scripts/audio.py", "mix", work / "mix.wav", "--narration", voice]
        if edit.get("music"):
            cmd += ["--music", edit["music"], "--music-db", edit.get("music_db", -6)]
        sfx = [f"{s['src']}@{when(s['at'], dialogue)}" + (f"@{s['db']}" if "db" in s else "") for s in edit.get("sfx", [])]
        if edit.get("ambience"):
            # scripts/soundscape.py writes it at its own level (well under speech), so it goes in unchanged by default
            sfx.append(f"{edit['ambience']}@0@{edit.get('ambience_db', 0)}")
        if sfx:
            cmd += ["--sfx", *sfx]
        sh(cmd)
        mix = work / "mix.wav"

    # 4. Scenes: check files, remux recordings, stage everything under public/<name>/.
    scenes, picture_idx = [], None
    for i, s in enumerate(edit["scenes"]):
        scene = {"kind": s["kind"], "seconds": float(s["seconds"])}
        for src_key, dst_key in (("text", "text"), ("fit", "fit"), ("volume", "volume"), ("zoom", "zoom"),
                                 ("punch_at", "punchAt"), ("transition", "transition"), ("label", "label"),
                                 ("trim_start", "trimStartSeconds"), ("captions", "captions")):
            if src_key in s:
                scene[dst_key] = s[src_key]
        if s["kind"] != "card":
            src = Path(s["src"])
            if not src.exists():
                raise SystemExit(f"scene {i + 1}: missing file {src}")
            scene.setdefault("fit", preset["fit"])
            if s["kind"] == "image" and src.suffix.lower() not in IMAGE:
                raise SystemExit(f"scene {i + 1}: {src.name} is not an image")
            if s["kind"] == "video":
                if src.suffix.lower() in REMUX:  # OBS records MKV; Remotion wants MP4
                    remuxed = work / f"scene{i + 1}.mp4"
                    try:
                        sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-c", "copy", remuxed])
                    except SystemExit:
                        sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-c:v", "libx264",
                            "-crf", "16", "-c:a", "aac", remuxed])
                    src = remuxed
                left = duration(src) - float(s.get("trim_start", 0))
                if left < scene["seconds"] - 0.05:
                    print(f"warning: scene {i + 1} wants {scene['seconds']}s but {src.name} has {left:.1f}s "
                          f"after trim_start; the last frame will hold")
            target = stage_dir / f"scene{i + 1}{src.suffix.lower()}"
            shutil.copyfile(src, target)
            scene["src"] = f"{name}/{target.name}"
            picture_idx = i
        scenes.append(scene)

    if edit.get("sync") == "script":
        if not (edit.get("script") and edit.get("captions") == "auto"):
            raise SystemExit('"sync": "script" needs "script" and "captions": "auto"')
        sync_to_script(scenes, edit["script"], work / "voice.words.json", duration(voice))
    total = sum(s["seconds"] for s in scenes)
    if mix:
        need = duration(mix) + 0.4
        if need > total + 0.05 and picture_idx is not None:
            scenes[picture_idx]["seconds"] = round(scenes[picture_idx]["seconds"] + need - total, 2)
            print(f"note: narration is {need:.1f}s, scenes were {total:.1f}s; scene {picture_idx + 1} extended")
        shutil.copyfile(mix, stage_dir / "narration.wav")

    caption_prop = None
    if captions and dialogue:
        shutil.copyfile(captions, stage_dir / "captions.words.json")
        caption_prop = f"{name}/captions.words.json"
    elif captions:
        words = Path(captions).with_suffix("").with_suffix(".words.json")
        if preset.get("captions") == "words" and captions.endswith(".srt") and words.exists():
            shutil.copyfile(words, stage_dir / "captions.words.json")
            caption_prop = f"{name}/captions.words.json"
        else:
            shutil.copyfile(captions, stage_dir / "captions.srt")
            caption_prop = f"{name}/captions.srt"

    props = {
        "scenes": scenes, "narration": f"{name}/narration.wav" if mix else None, "captions": caption_prop,
        "emphasis": edit.get("emphasis", []), "hook": edit.get("hook", ""), "hookSeconds": edit.get("hook_seconds", 2.5),
        "accent": edit.get("accent", preset["accent"]), "captionTop": preset["captionTop"],
        "label": edit.get("label", preset["label"]), "endCard": edit.get("end_card", preset["endCard"]),
        "endCardTitle": edit.get("end_title", preset["endCardTitle"]),
        "endCardSubtitle": edit.get("end_subtitle", preset["endCardSubtitle"]), "endCardSeconds": 2,
    }
    fonts = ROOT / "public" / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    if not (fonts / "Kalam-Bold.ttf").exists():
        shutil.copyfile(ROOT / "assets" / "brand" / "Kalam-Bold.ttf", fonts / "Kalam-Bold.ttf")
    props_path = stage_dir / "props.json"
    props_path.write_text(json.dumps(props, indent=1), encoding="utf-8")
    (work / "props.json").write_text(json.dumps(props, indent=1), encoding="utf-8")  # kept for checking

    out, overall, results, dur = render.finish("Story", name, props_path, production=not a.test, out_dir=a.out_dir)
    # Which language's accounts the edit is for (the dashboard shows it on the video's card).
    Path(out).with_suffix(".meta.json").write_text(json.dumps({"language": edit.get("language", "en")}), encoding="utf-8")
    issues = "; ".join(f"{r['check']}: {r['detail']}" for r in results if r["status"] != "PASS")
    print(f"{out} ({dur:.1f}s, {len(scenes)} scenes) QC {overall}" + (f" - {issues}" if issues else ""))
    if overall != "FAIL":  # exports/ keeps only the latest version of each video (a failed render keeps the old one)
        for n in batch.archive_older(out, edit.get("language", "en")):
            print(f"archived older version {n} -> exports/archive/")
    if a.out_dir:
        sys.exit(2 if overall == "FAIL" else 0)
    batch.LOG.parent.mkdir(parents=True, exist_ok=True)
    new = not batch.LOG.exists()
    with batch.LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, batch.LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"rendered_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "edit_file": out.name, "format": fmt, "concept": edit["concept"],
                    "hook_id": edit.get("hook_id", "Edit"), "hook": edit.get("hook", ""),
                    "clip": f"{len(scenes)} scenes ({a.edit_file})", "narration": str(voice or ""),
                    "captions": captions or "", "duration_s": round(dur, 1), "qc": overall, "qc_issues": issues,
                    "experiment_id": ""})
    sys.exit(2 if overall == "FAIL" else 0)


if __name__ == "__main__":
    main()
