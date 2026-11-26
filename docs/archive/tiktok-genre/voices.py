"""Measure narration voices in TOP TikToks vs our V06 narrator: pitch, pitch range, loudness swings, speaker fingerprints."""
import os
import shutil
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(project_root / "scripts"), str(project_root / "research" / "tiktok-genre")]
import research_common as rc

import glob, json, os, subprocess, sys, tempfile
import numpy as np, librosa, soundfile as sf
FF = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
ROOT = str(rc.ROOT)
items = {}
for f in glob.glob(ROOT + r"\data\local\research\creative\tiktok-genre\apify-top15-*\items.json"):
    for it in json.load(open(f, encoding="utf-8")): items[it["id"]] = it
clips = [(items[os.path.basename(p)[:-4]]["authorMeta"]["name"], p, 3, 33) for p in sorted(glob.glob(ROOT + r"\media\research\tiktok-genre\top\*.mp4"))]
clips.append(("OURS (Gemini Puck)", ROOT + r"\exports\SS_20261126_WORLD_InMyWorldPick_SampleGemini_V06_MASTER.mp4", 0, 8.5))
tmp = tempfile.mkdtemp()
def wav(src, start, end):
    out = os.path.join(tmp, f"{abs(hash(src))}.wav")
    subprocess.run([FF, "-v", "error", "-y", "-ss", str(start), "-to", str(end), "-i", src, "-ac", "1", "-ar", "24000", out], check=True)
    return out
rows, paths = [], []
for name, src, a, b in clips:
    w = wav(src, a, b); paths.append(w)
    y, sr = sf.read(w)
    f0, vflag, _ = librosa.pyin(y, fmin=65, fmax=450, sr=sr, frame_length=2048)
    f0 = f0[vflag & ~np.isnan(f0)]
    st = 12 * np.log2(f0 / np.median(f0))
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]; db = 20 * np.log10(rms + 1e-6)
    loud = db[db > np.percentile(db, 40)]
    rows.append((name, np.median(f0), np.percentile(st, 90) - np.percentile(st, 10), np.std(st), np.std(loud), vflag.mean()))
print(f"{'voice':22} {'median Hz':>9} {'pitch range st':>14} {'pitch sd st':>11} {'loud sd dB':>10} {'voiced':>6}")
for r in rows: print(f"{r[0][:22]:22} {r[1]:9.0f} {r[2]:14.1f} {r[3]:11.2f} {r[4]:10.1f} {r[5]:6.2f}")
import voicelab, torch
emb = voicelab.Embedder()
vecs = voicelab.center([emb.file(p) for p in paths])
names = [c[0][:10] for c in clips]
print("\nfingerprint similarity (centred; ~0.5+ = likely same voice, <0.1 = different)")
print(" " * 11 + " ".join(f"{n[:5]:>5}" for n in names))
for n, a in zip(names, vecs): print(f"{n:10} " + " ".join(f"{float(a @ b):5.2f}" for b in vecs))
