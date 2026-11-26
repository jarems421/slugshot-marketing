"""Estimate narrator gender for all TOP videos: speaker-fingerprint nearest centroid (Kokoro labelled refs) + pitch."""
import os
import shutil
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(project_root / "scripts"), str(project_root / "research" / "tiktok-genre")]
import research_common as rc

import csv, glob, json, os, subprocess, sys, tempfile
import numpy as np, librosa, soundfile as sf, torch
import voicelab
FF = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
ROOT = str(rc.ROOT); TT = os.path.dirname(os.path.abspath(__file__))
meta = {r["id"]: r for r in csv.DictReader(open(ROOT + r"\exports\share\research\tiktok-in-my-world-2026-11-26\ALL-POSTS.csv", encoding="utf-8-sig"))}
emb = voicelab.Embedder()
refs = sorted(glob.glob(TT + r"\refs\*.wav"))
R = torch.stack([emb.file(p) for p in refs]); lab = np.array([os.path.basename(p)[1] == "f" for p in refs])
def score(v, mask=None):
    m = np.ones(len(refs), bool) if mask is None else mask
    f = R[torch.tensor(m & lab)].mean(0); mm = R[torch.tensor(m & ~lab)].mean(0)
    return float(v @ f / f.norm() - v @ mm / mm.norm())  # >0 leans female
loo = [(score(R[i], np.arange(len(refs)) != i) > 0) == lab[i] for i in range(len(refs))]
print(f"leave-one-out accuracy on labelled refs: {sum(loo)}/{len(loo)}")
tmp = tempfile.mkdtemp(); out = []
def measure(src, a, b):
    w = os.path.join(tmp, "x.wav")
    subprocess.run([FF, "-v", "error", "-y", "-ss", str(a), "-to", str(b), "-i", src, "-ac", "1", "-ar", "24000", w], check=True)
    y, sr = sf.read(w)
    f0, vf, _ = librosa.pyin(y, fmin=65, fmax=450, sr=sr, frame_length=2048); f0 = f0[vf & ~np.isnan(f0)]
    return emb(y, sr), float(np.median(f0)) if len(f0) else None
v, hz = measure(ROOT + r"\exports\SS_20261126_WORLD_InMyWorldPick_SampleGemini_V06_MASTER.mp4", 0, 8.5)
print(f"check: our male Puck narrator score {score(v):+.3f}, {hz:.0f} Hz")
for p in sorted(glob.glob(ROOT + r"\media\research\tiktok-genre\top\*.mp4")):
    vid = os.path.basename(p)[:-4]; m = meta.get(vid)
    if not m or m["tier"] != "TOP": continue
    v, hz = measure(p, 2, 32); s = score(v)
    call = "female" if s > 0.02 and (hz or 0) > 165 else "male" if s < -0.02 and (hz or 999) < 230 else "unclear"
    out.append({"id": vid, "creator": m["creator"], "views": int(m["views"]), "url": m["url"], "score": round(s, 3), "median_hz": round(hz or 0), "estimate": call})
out.sort(key=lambda r: -r["views"])
for r in out: print(f"{r['estimate']:8} {r['score']:+.3f} {r['median_hz']:4} Hz  {r['views']:>10,}  @{r['creator']}")
from collections import Counter; print(Counter(r["estimate"] for r in out))
json.dump(out, open(TT + r"\gender_top.json", "w"), indent=1)
