"""Soundboard bank (owner 2026-11-26): every distinct soundboard / meme sound effect, cut to its own file, with
Gemini's description of how it sounds and the context it's used in, for placing in Slugshot edits.

  python research/tiktok-genre/soundboard.py          sources: soundboard-search items (post audio) + Cuffem clips

Files: media/meme/soundboard/<source>_<n>_<slug>.wav (ignored; third-party audio, owner accepted takedown risk,
TikTok entertainment posts only, never in posts naming Slugshot). Bank: data/local/research/creative/soundboard/bank.csv
and the owner's Downloads. Descriptions, names and contexts are Gemini-reported (P4): verify by ear.
"""
import base64, csv, glob, json, os, re, subprocess, sys
sys.path.insert(0, r"C:\Users\runni\slugshot marketing\scripts")
import research_common as rc
ROOT = r"C:\Users\runni\slugshot marketing"
MEDIA = os.path.join(ROOT, r"media\meme\soundboard"); DATA = os.path.join(ROOT, r"data\local\research\creative\soundboard")
DL = r"C:\Users\runni\Downloads\slugshot-audio-kit\soundboard-bank"
for d in (MEDIA, DATA, os.path.join(DATA, "raw"), DL): os.makedirs(d, exist_ok=True)
PROMPT = """This is the audio of a TikTok post about soundboard / meme sound effects{extra}.
Post caption: {caption!r}. Its transcript, if any: {transcript!r}.
List every DISTINCT soundboard or meme sound effect you hear (not ordinary talking, not background music unless the music sting IS the meme sound).
JSON only: {{"sounds": [{{
 "start": seconds, "end": seconds,
 "name": "<the well-known name if you are confident (e.g. 'vine boom', 'bruh'), else a short descriptive name>",
 "name_confidence": "high|medium|low",
 "sounds_like": "<precise description: timbre, pitch, length, onomatopoeia, e.g. 'a deep reverberant BOOM, 1 s'>",
 "has_words": "<the exact words if any, else ''>",
 "clean": true|false,
 "used_for": "<the comedic job and the context it's used in, from this post and common meme use, e.g. 'after someone says something stupid'>",
 "energy": "low|mid|high",
 "scenarios": ["<2-4 short scene types it fits, e.g. 'awkward pause', 'fail', 'reveal', 'transition'>"]}}]}}
Times to 0.1 s. Don't merge different sounds. If you aren't sure of a well-known name, say so with low confidence."""


def gemini(mp3, prompt):
    body = {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(open(mp3, "rb").read()).decode()}}, {"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    raw, _ = rc.http("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                     headers={"x-goog-api-key": rc.env_value("GEMINI_API_KEY"), "Content-Type": "application/json"}, data=json.dumps(body).encode(), timeout=240)
    t = "".join(x.get("text", "") for x in json.loads(raw)["candidates"][0]["content"]["parts"])
    try: return json.loads(t).get("sounds", [])
    except Exception: return []


def subtitles(x, tok):
    ls = (x.get("videoMeta") or {}).get("subtitleLinks") or []
    if not ls: return ""
    try:
        b, _ = rc.http(ls[0]["downloadLink"], headers={"Authorization": "Bearer " + tok})
        return " ".join(l.strip() for l in b.decode("utf-8", "replace").splitlines() if l.strip() and "-->" not in l and not l.startswith("WEBVTT") and not l.strip().isdigit())[:600]
    except Exception: return ""


def sources():
    tok = rc.env_value("APIFY_TOKEN")
    it = json.load(open(sorted(glob.glob(ROOT + r"\data\local\research\creative\tiktok-genre\apify-soundboard-search-*\items.json"))[-1], encoding="utf-8"))
    for x in sorted({x["id"]: x for x in it}.values(), key=lambda x: -(x.get("playCount") or 0)):
        url = (x.get("musicMeta") or {}).get("playUrl"); raw = os.path.join(DATA, "raw", x["id"] + ".mp3")
        video = os.path.join(ROOT, r"media\meme\soundboard-src", x["id"] + ".mp4")  # TikTok's sound CDN mostly answers 403; the post video works
        if os.path.exists(video):
            raw = video
        elif url and not os.path.exists(raw):
            try: b, _ = rc.http(url, timeout=60); open(raw, "wb").write(b)
            except Exception as e: print("skip", x["id"], e); continue
        if os.path.exists(raw):
            yield x["id"], raw, x.get("text") or "", subtitles(x, tok), x.get("webVideoUrl"), x.get("playCount"), ""
    for p in sorted(glob.glob(ROOT + r"\media\meme\cuffem\*.mp4")):
        yield "cuffem-" + os.path.basename(p)[:-4], p, "Cuffem livestream clip", "", "", None, " (a clip of the streamer Cuffem's livestream with his stream soundboard)"


def main():
    bank_path = os.path.join(DATA, "bank.csv")
    rows = list(csv.DictReader(open(bank_path, encoding="utf-8"))) if os.path.exists(bank_path) else []
    done = {r["source"] for r in rows}
    for sid, path, caption, transcript, link, views, extra in sources():
        if sid in done: continue
        mp3 = os.path.join(DATA, "raw", sid + ".q.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-b:a", "96k", "-t", "90", mp3], check=True)
        sounds = gemini(mp3, PROMPT.format(extra=extra, caption=caption[:300], transcript=transcript)); os.remove(mp3)
        for n, s in enumerate(sounds, 1):
            try: a, b = max(0.0, float(s["start"]) - 0.08), float(s["end"]) + 0.15
            except Exception: continue
            if b - a < 0.1 or b - a > 20: continue
            slug = re.sub(r"[^a-z0-9]+", "-", str(s.get("name", "sound")).lower()).strip("-")[:30] or "sound"
            f = f"{sid}_{n:02d}_{slug}.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.2f}", "-to", f"{b:.2f}", "-i", path, "-vn", "-ac", "2", "-ar", "48000",
                            "-af", "afade=t=in:d=0.01,areverse,afade=t=in:d=0.03,areverse", os.path.join(MEDIA, f)], check=True)
            rows.append({"file": f, "source": sid, "source_link": link or "", "source_views": views or "", "start": a, "end": round(b, 2),
                         "name": s.get("name", ""), "name_confidence": s.get("name_confidence", ""), "sounds_like": s.get("sounds_like", ""),
                         "has_words": s.get("has_words", ""), "clean": s.get("clean", ""), "used_for": s.get("used_for", ""),
                         "energy": s.get("energy", ""), "scenarios": "; ".join(s.get("scenarios", []) or []), "reported_by": "gemini-3.8-flash (P4)"})
        if not sounds:
            rows.append({"file": "", "source": sid, "source_link": link or "", "name": "(no distinct sounds reported)", "reported_by": "gemini-3.8-flash (P4)"})
        print(f"{sid}: {len(sounds)} sounds", flush=True)
        with open(bank_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, ["file", "source", "source_link", "source_views", "start", "end", "name", "name_confidence", "sounds_like", "has_words",
                                    "clean", "used_for", "energy", "scenarios", "reported_by"]); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
