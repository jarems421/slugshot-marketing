"""Gemini listening pass: sound effects, music bed and narrator voice for TOP In My World videos.

  python research/tiktok-genre/gemini_listen.py [--limit N] [--cap-usd 0.50]

Audio-only (mono 32 kbps) sent inline to gemini-3.8-flash; JSON per video saved to
data/local/research/creative/tiktok-genre/listen/. Gemini-reported (P4): names of meme sounds are its guess.
"""
import os
import shutil
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(project_root / "scripts"), str(project_root / "research" / "tiktok-genre")]
import research_common as rc

import argparse, base64, csv, glob, json, os, subprocess, sys
ROOT = str(rc.ROOT)
FF = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
OUT = os.path.join(ROOT, r"data\local\research\creative\tiktok-genre\listen"); os.makedirs(OUT, exist_ok=True)
MODEL = "gemini-3.8-flash"
USD_IN_AUDIO, USD_IN_TEXT, USD_OUT = 1.0 / 1e6, 0.5 / 1e6, 3.0 / 1e6   # conservative estimates; actual billing may be lower
PROMPT = """Listen to this short TikTok story video's audio (a narrated Roblox "In This Town / In My World" story).
Return JSON only, with this shape:
{"narrator": {"gender_impression": "male|female|unclear", "likely_tts": "yes|no|unsure", "style": "<5-12 words>"},
 "music": {"present": true|false, "description": "<genre, mood, instruments>", "tempo": "slow|mid|fast", "changes_at": [{"t": seconds, "what": "<change>"}]},
 "sfx": [{"t": seconds, "sound": "<what you hear, e.g. whoosh, boom, record scratch, crowd laugh>", "meme_name": "<well-known meme sound name, or 'unknown'>", "confidence": "high|medium|low", "story_moment": "hook|world-building|turn|punchline|ending|other"}],
 "notes": "<one sentence on how sound supports the story>"}
List every distinct sound effect (not speech, not the steady music). If you are not confident a sound is a specific named meme sound, set meme_name to "unknown". Do not guess."""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=50); ap.add_argument("--cap-usd", type=float, default=0.50); ap.add_argument("--tier", default="TOP")
    a = ap.parse_args()
    key = rc.env_value("GEMINI_API_KEY")
    meta = {r["id"]: r for r in csv.DictReader(open(os.path.join(ROOT, r"exports\share\research\tiktok-in-my-world-2026-11-26\ALL-POSTS.csv"), encoding="utf-8-sig"))}
    vids = sorted((p for p in glob.glob(ROOT + r"\media\research\tiktok-genre\*\*.mp4") if meta.get(os.path.basename(p)[:-4], {}).get("tier") == a.tier),
                  key=lambda p: -int(meta[os.path.basename(p)[:-4]]["views"]))[: a.limit]
    spent = 0.0
    for p in vids:
        vid = os.path.basename(p)[:-4]; dest = os.path.join(OUT, vid + ".json")
        if os.path.exists(dest):
            continue
        mp3 = os.path.join(OUT, vid + ".mp3")
        subprocess.run([FF, "-v", "error", "-y", "-i", p, "-vn", "-ac", "1", "-b:a", "32k", mp3], check=True)
        body = {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(open(mp3, "rb").read()).decode()}}, {"text": PROMPT}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
        raw, _ = rc.http(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent", headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                         data=json.dumps(body).encode(), timeout=180)
        d = json.loads(raw); os.remove(mp3)
        u = d.get("usageMetadata", {})
        aud = sum(x.get("tokenCount", 0) for x in u.get("promptTokensDetails", []) if x.get("modality") == "AUDIO")
        cost = aud * USD_IN_AUDIO + (u.get("promptTokenCount", 0) - aud) * USD_IN_TEXT + (u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)) * USD_OUT
        spent += cost
        text = "".join(x.get("text", "") for x in d["candidates"][0]["content"]["parts"])
        try: res = json.loads(text)
        except json.JSONDecodeError: res = {"raw": text}
        res.update(_id=vid, _views=int(meta[vid]["views"]), _model=MODEL, _usage=u, _est_usd=round(cost, 5))
        json.dump(res, open(dest, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"{vid} {int(meta[vid]['views']):>11,} | sfx {len(res.get('sfx', []))} | est ${cost:.4f} (total ${spent:.3f})", flush=True)
        if spent >= a.cap_usd:
            print("cap reached; stopping"); break


if __name__ == "__main__":
    main()
