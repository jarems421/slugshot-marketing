"""The In My World sample as audio with each of six narrators at TOP pace; character lines unchanged."""
import os
import shutil
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(project_root / "scripts"), str(project_root / "research" / "tiktok-genre")]
import research_common as rc

import json, subprocess, sys
from pathlib import Path
import gemini_tts
ROOT = rc.ROOT
FF = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
WORK = ROOT / "out" / "voices" / "narrator-test-2026-11-26" / "in-story"; WORK.mkdir(parents=True, exist_ok=True)
DL = Path.home() / "Downloads" / "narrator-voice-test-2026-11-26" / "in-story"; DL.mkdir(parents=True, exist_ok=True)
LINES = ROOT / "out" / "dialogue" / "imw-pick-gemini" / "lines"
OPEN = "In my world, every slug picks its partner on the day it hatches. Some pick fire. Some pick water. And some... just pick a nap."
CLOSE = "And that was the day he picked me."
takes = {t["file"][:-4]: t for t in json.load(open(WORK.parent / "takes.json"))}
factor = dict(l.split() for l in open(WORK.parent / "factors.txt"))
def ff(*a): subprocess.run([FF, "-v", "error", "-y", *map(str, a)], check=True)
TRIM = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"
import dialogue  # passage splitting: one request per voice for both narrator passages
for name, t in takes.items():
    raw = WORK / f"{name}_both.raw.wav"
    if not raw.exists():
        gemini_tts.speak(OPEN + " " + CLOSE, t["voice"], t["style"] + " Brief pause before 'just pick a nap'. "
                         "Then a clear pause before the final line, which lands warm with a small smile.", raw)
    secs = float(subprocess.run([FF.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", raw], capture_output=True, text=True).stdout)
    words, dev = dialogue.align(OPEN + " " + CLOSE, dialogue.transcribe([raw], [OPEN + " " + CLOSE], "small.en")[0], 0.0)
    cut = dialogue.split_points(words, [len(OPEN.split()), len(CLOSE.split())])
    if dev or not cut:
        print(f"{name}: read didn't split cleanly ({dev}); skipped", flush=True)
        continue
    parts = []
    for tag, a, b in (("open", 0.0, cut[0]), ("close", cut[0], secs)):
        fast = WORK / f"{name}_{tag}.wav"
        ff("-i", raw, "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-af", f"{TRIM},atempo={factor[name]},aresample=24000", "-ac", "1", fast)
        parts.append(fast)
    seq = [(parts[0], 0.3), (LINES / "05_AQUABEEK.wav", 0.25), (LINES / "06_RAMMSTONE.wav", 0.35), (LINES / "07_FLOPPY.wav", 0.45), (parts[1], 0.8)]
    inputs, chain = [], []
    for i, (p, gap) in enumerate(seq):
        inputs += ["-i", p]
        chain.append(f"[{i}:a]aresample=24000,aformat=channel_layouts=mono,{TRIM},apad=pad_dur={gap}[a{i}]")
    inputs += ["-stream_loop", "-1", "-i", ROOT / "assets" / "sfx" / "cavern_bed.wav"]
    n = len(seq)
    fc = ";".join(chain) + ";" + "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[v];[{n}:a]aresample=24000,aformat=channel_layouts=mono,volume=-30dB[m];[v][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[o]"
    out = DL / f"{name}_in-story.mp3"
    ff(*inputs, "-filter_complex", fc, "-map", "[o]", "-ar", "44100", "-b:a", "192k", out)
    dur = subprocess.run([FF.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip()
    print(f"{name}: {float(dur):.1f} s -> {out.name}", flush=True)
print(f"month spend ${gemini_tts.month_spend():.4f}")
