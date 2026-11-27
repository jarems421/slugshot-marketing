"""Stage 1 of the sound-design measurement: Whisper word timings for each TOP video (where the speech is)."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(project_root / "scripts"), str(project_root / "research" / "tiktok-genre")]
import research_common as rc

import glob, json, os
import whisper
ROOT = str(rc.ROOT)
OUT = os.path.join(ROOT, r"data\local\research\creative\tiktok-genre\sound-design"); os.makedirs(OUT, exist_ok=True)
m = whisper.load_model("base.en")
for p in sorted(glob.glob(ROOT + r"\media\research\tiktok-genre\top\*.mp4")):
    dest = os.path.join(OUT, os.path.basename(p)[:-4] + ".words.json")
    if os.path.exists(dest):
        continue
    r = m.transcribe(p, fp16=False, word_timestamps=True, language="en", condition_on_previous_text=False)
    words = [[round(w["start"], 2), round(w["end"], 2), w["word"].strip()] for s in r["segments"] for w in s["words"]]
    json.dump(words, open(dest, "w", encoding="utf-8"))
    print(os.path.basename(p), len(words), "words", flush=True)
print("WORDS DONE", flush=True)
