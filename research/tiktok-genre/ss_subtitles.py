"""Fetch the (expiring) TikTok subtitle tracks returned by the socialscrapers Actors for one or more runs."""
import glob, json, os, sys, time
sys.path.insert(0, r"C:\Users\runni\slugshot marketing\scripts")
import research_common as rc
ROOT = rc.DATA / "creative" / "tiktok-genre"
SUBS = ROOT / "subtitles"; SUBS.mkdir(exist_ok=True)
got = miss = fail = 0
for f in sys.argv[1:]:
    for x in json.load(open(f, encoding="utf-8")):
        if x.get("dataType") != "video":
            continue
        dest = SUBS / f"{x['id']}.vtt"
        if dest.exists():
            got += 1; continue
        subs = x.get("subtitles") or []
        eng = [s for s in subs if (s.get("language") or "").lower().startswith("eng")] or subs[:1]
        if not eng:
            miss += 1; continue
        try:
            body, _ = rc.http(eng[0]["url"], timeout=30)
            dest.write_bytes(body); got += 1
        except rc.HttpError:
            fail += 1
        time.sleep(0.05)
print(f"subtitles saved {got} | none offered {miss} | failed {fail}")
