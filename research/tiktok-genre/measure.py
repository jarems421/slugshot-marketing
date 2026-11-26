import glob, os, sys, json, whisper
m = whisper.load_model("small.en")
res = {}
for p in sorted(glob.glob(sys.argv[1] + "/*.wav")):
    r = m.transcribe(p, fp16=False, word_timestamps=True, language="en")
    ws = [w for s in r["segments"] for w in s["words"]]
    span = ws[-1]["end"] - ws[0]["start"]
    gaps = [b["start"] - a["end"] for a, b in zip(ws, ws[1:])]
    long = sum(1 for g in gaps if g > 0.3)
    res[os.path.basename(p)] = {"wpm": round(len(ws) / span * 60), "longest_gap": round(max(gaps), 2), "gaps_over_0.3s": long, "text": r["text"].strip()}
    print(os.path.basename(p), res[os.path.basename(p)]["wpm"], "wpm | longest gap", res[os.path.basename(p)]["longest_gap"], "| gaps>0.3s", long)
json.dump(res, open(sys.argv[1] + "/measure.json", "w"), indent=1)
