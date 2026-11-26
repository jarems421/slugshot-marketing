"""Stage 2 of the sound-design measurement (run in .venv-voicelab): music bed vs voice level, sudden hits
(likely sound effects), silent drops and bed tempo, for each TOP video. Rough signal measures, not identification:
a "hit" is a sharp onset well above the local level; music, laughs and shouted words can also trigger one."""
import os
import shutil
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(project_root / "scripts"), str(project_root / "research" / "tiktok-genre")]
import research_common as rc

import csv, glob, json, os, subprocess, tempfile
import numpy as np, librosa, soundfile as sf
ROOT = str(rc.ROOT)
FF = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
DIR = os.path.join(ROOT, r"data\local\research\creative\tiktok-genre\sound-design")
meta = {r["id"]: r for r in csv.DictReader(open(ROOT + r"\exports\share\research\tiktok-in-my-world-2026-11-26\ALL-POSTS.csv", encoding="utf-8-sig"))}
SR, HOP = 22050, 512
tmp = tempfile.mkdtemp()
rows = []
for wj in sorted(glob.glob(DIR + r"\*.words.json")):
    vid = os.path.basename(wj).split(".")[0]
    words = json.load(open(wj, encoding="utf-8"))
    w = os.path.join(tmp, "a.wav")
    subprocess.run([FF, "-v", "error", "-y", "-i", ROOT + rf"\media\research\tiktok-genre\top\{vid}.mp4", "-ac", "1", "-ar", str(SR), w], check=True)
    y, _ = sf.read(w)
    dur = len(y) / SR
    t = librosa.frames_to_time(np.arange(1 + len(y) // HOP), sr=SR, hop_length=HOP)
    db = 20 * np.log10(librosa.feature.rms(y=y, hop_length=HOP)[0] + 1e-6)[:len(t)]
    speech = np.zeros(len(t), bool)
    for s, e, _ in words:
        speech[(t >= s - 0.1) & (t <= e + 0.1)] = True
    gaps = db[~speech]
    voice_db = float(np.median(db[speech])) if speech.any() else None
    bed_db = float(np.percentile(gaps, 50)) if len(gaps) > 20 else None
    # sharp onsets clearly above the surrounding level (2 s median) = candidate hits
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    peaks = librosa.util.peak_pick(env, pre_max=10, post_max=10, pre_avg=40, post_avg=40, delta=np.percentile(env, 98) * 0.5, wait=15)
    local = np.array([np.median(db[max(0, p - 43):p + 43]) for p in peaks])
    jump = np.array([db[min(p + 3, len(db) - 1)] for p in peaks]) - local
    hits = [float(t[p]) for p, j in zip(peaks, jump) if j > 8]
    hits_in_gap = [h for h in hits if not speech[min(int(h * SR / HOP), len(speech) - 1)]]
    # silent drops: >= 0.35 s below -45 dB after the first word (hard cuts to silence)
    quiet = db < -45
    drops, run = 0, 0
    for q, tt in zip(quiet, t):
        run = run + 1 if q and words and tt > words[0][0] else 0
        if run == int(0.35 * SR / HOP):
            drops += 1
    # whole-track beat estimate: the bed drives it when there is one, so it's a rough guide only
    tempo = float(np.atleast_1d(librosa.beat.beat_track(y=y, sr=SR, hop_length=HOP)[0])[0]) if bed_db and bed_db > -45 else None
    m = meta.get(vid, {})
    first_word = words[0][0] if words else None
    rows.append({"id": vid, "creator": m.get("creator"), "views": m.get("views"), "duration_s": round(dur, 1),
                 "first_word_s": first_word, "voice_db": round(voice_db, 1) if voice_db is not None else None,
                 "bed_db": round(bed_db, 1) if bed_db is not None else None,
                 "voice_minus_bed_db": round(voice_db - bed_db, 1) if None not in (voice_db, bed_db) else None,
                 "speech_share": round(float(speech.mean()), 2), "hits": len(hits), "hits_per_min": round(len(hits) / dur * 60, 1),
                 "hits_between_words": len(hits_in_gap), "hits_first_5s": sum(h < 5 for h in hits),
                 "hits_last_15pct": sum(h > dur * 0.85 for h in hits), "silent_drops": drops, "tempo_bpm": round(tempo) if tempo else None,
                 "hit_times": " ".join(f"{h:.1f}" for h in hits)})
    print(vid, rows[-1]["hits_per_min"], "hits/min | voice-bed", rows[-1]["voice_minus_bed_db"], "dB | drops", drops, flush=True)
with open(os.path.join(DIR, "sound_design_top50.csv"), "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, list(rows[0])); wr.writeheader(); wr.writerows(rows)
def med(k):
    v = [r[k] for r in rows if r[k] is not None]
    return f"{np.median(v):.1f} (middle half {np.percentile(v, 25):.1f}-{np.percentile(v, 75):.1f})"
for k in ("first_word_s", "voice_minus_bed_db", "speech_share", "hits_per_min", "hits_first_5s", "hits_last_15pct", "silent_drops", "tempo_bpm"):
    print(f"{k:20} median {med(k)}")
