import json, glob, os, sys, time
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import whisper
SRC = r"C:\Users\runni\slugshot marketing\media\research\tiktok-genre"
OUT = r"C:\Users\runni\slugshot marketing\data\local\research\creative\tiktok-genre\subtitles"
m = whisper.load_model("small")
files = sorted(glob.glob(SRC + r"\*.mp4"))
for n, f in enumerate(files, 1):
    vid = os.path.basename(f)[:-4]; dest = os.path.join(OUT, vid + ".whisper.json")
    if os.path.exists(dest): continue
    t = time.time()
    try:
        r = m.transcribe(f, fp16=False, verbose=None, condition_on_previous_text=False)
        segs = [[int(s["start"]), s["text"].strip()] for s in r["segments"] if s["text"].strip() and s.get("no_speech_prob", 0) < 0.8]
        json.dump({"language": r.get("language"), "model": "openai-whisper small", "segments": segs}, open(dest, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"{n}/{len(files)} {vid} {r.get('language')} {len(segs)} segs {time.time()-t:.0f}s", flush=True)
    except Exception as e:
        print(f"{n}/{len(files)} {vid} FAIL {str(e)[:100]}", flush=True)
print("WHISPER DONE", flush=True)
