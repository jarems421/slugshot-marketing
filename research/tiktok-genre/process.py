"""Pool all tiktok-genre runs, filter to the format, fetch subtitles, write pool.csv."""
import csv, json, re, sys, glob, statistics
from datetime import datetime, timezone
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import apify, research_common as rc
ROOT = rc.DATA / "creative" / "tiktok-genre"
SUBS = ROOT / "subtitles"; SUBS.mkdir(exist_ok=True)
FMT = re.compile(r"\bin\s+(my|this|our)\s+(world|town|city|village|universe|school|family)\b|#(inmyworld|inthistown|inmytown|inthisworld)", re.I)
def load():
    seen = {}
    for f in sorted(glob.glob(str(ROOT / "apify-*" / "items.json"))):
        run = json.load(open(f.replace("items.json", "run.json"), encoding="utf-8"))
        for it in json.load(open(f, encoding="utf-8")):
            if not it.get("id") or it.get("error"): continue
            it["_observed"] = run["finishedAt"]; it["_run"] = run["id"]; it["_route"] = it.get("searchQuery") or it.get("input") or ""
            prev = seen.get(it["id"])
            if prev is None or (it["_observed"] > prev["_observed"]):
                if prev: it["_route"] = prev["_route"] + " | " + it["_route"]
                seen[it["id"]] = it
    return list(seen.values())
def vtt_lines(text):
    out = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        m = re.search(r"(\d+):(\d\d):(\d\d)\.\d+\s*-->|(\d+):(\d\d)\.\d+\s*-->", block)
        if not m: continue
        secs = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) if m[1] else int(m[4]) * 60 + int(m[5])
        body = " ".join(l.strip() for l in block.split("\n") if l.strip() and "-->" not in l and not l.strip().isdigit())
        body = re.sub(r"<[^>]+>", "", body).strip()
        if body and (not out or out[-1][1] != body): out.append((secs, body))
    return out
def subtitle(it):
    links = (it.get("videoMeta") or {}).get("subtitleLinks") or []
    eng = [l for l in links if (l.get("language") or "").lower().startswith("eng")] or links[:1]
    if not eng: return None, None
    l = eng[0]; path = SUBS / f"{it['id']}.vtt"
    if not path.exists():
        try:
            tok = rc.env_value("APIFY_TOKEN")
            body, _ = rc.http(l["downloadLink"], headers={"Authorization": f"Bearer {tok}"})
            path.write_bytes(body if isinstance(body, bytes) else body.encode("utf-8"))
        except Exception as e:
            print("subtitle fail", it["id"], str(e)[:80]); return None, None
    return path, f"{l.get('language')} {l.get('source')}"
def main(min_age_days=14):
    rows = []
    for it in load():
        text = it.get("text") or ""; tags = " ".join("#" + (h.get("name") or "") for h in it.get("hashtags") or [])
        if it.get("isSlideshow") or it.get("isAd") or it.get("isSponsored"): continue
        if not FMT.search(text + " " + tags): continue
        obs = rc.parse_time(it["_observed"]); posted = rc.parse_time(it.get("createTimeISO"))
        age = (obs - posted).total_seconds() / 86400 if posted else None
        sub, src = subtitle(it)
        lines = vtt_lines(sub.read_text(encoding="utf-8", errors="replace")) if sub else []
        wj = SUBS / f"{it['id']}.whisper.json"
        if not lines and wj.exists():
            w = json.load(open(wj, encoding="utf-8")); lines = [tuple(x) for x in w["segments"]]
            lang = {"en": "eng"}.get(w.get("language"), w.get("language") or "")
            src = f"{lang} Whisper-small (local)" if lines else None
        a, m, v = it.get("authorMeta") or {}, it.get("musicMeta") or {}, it.get("videoMeta") or {}
        rows.append({"id": it["id"], "url": it.get("webVideoUrl"), "creator": a.get("name"), "creator_followers": a.get("fans"),
            "posted_at_utc": it.get("createTimeISO"), "observed_at_utc": it["_observed"], "age_days": round(age, 1) if age is not None else None,
            "duration_s": v.get("duration"), "views": it.get("playCount"), "likes": it.get("diggCount"), "comments": it.get("commentCount"),
            "shares": it.get("shareCount"), "saves": it.get("collectCount"), "caption": text, "sound": m.get("musicName"),
            "sound_original": m.get("musicOriginal"), "roblox": "roblox" in (text + tags).lower(), "language": it.get("textLanguage"),
            "transcript_source": src, "transcript_words": sum(len(b.split()) for _, b in lines),
            "transcript": json.dumps(lines, ensure_ascii=False), "discovery_route": it["_route"], "apify_run_id": it["_run"]})
    with open(ROOT / "pool.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
    aged = [r for r in rows if r["age_days"] and r["age_days"] >= min_age_days and r["views"] is not None]
    print(f"{len(rows)} in-format posts; {len(aged)} aged >= {min_age_days} d; with transcript {sum(1 for r in aged if r['transcript_words'] >= 15)}")
    if aged:
        vs = sorted(r["views"] for r in aged); print("views min/median/max", vs[0], statistics.median(vs), vs[-1])
        print("aged <2k views:", sum(1 for x in vs if x < 2000), "| creators:", len({r['creator'] for r in aged}))
main()
