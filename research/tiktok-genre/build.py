"""Build TOP/MID/FLOP transcript files and the full CSV from pool.csv."""
import csv, json, math, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\runni\slugshot marketing\scripts")
import research_common as rc
ROOT = rc.DATA / "creative" / "tiktok-genre"
OUT = Path(r"C:\Users\runni\slugshot marketing\exports\share\research\tiktok-in-my-world-2026-11-26"); OUT.mkdir(parents=True, exist_ok=True)
MIN_AGE, MIN_WORDS, PER_CREATOR, N = 5, 15, 4, 50
def band(a):
    if a is None: return ""
    return next(b for lim, b in ((5, "0-5d (too new to judge)"), (7, "5-7d"), (14, "7-14d"), (30, "14-30d"), (90, "30-90d"), (1e9, "90d+")) if a < lim)
def i(x): return int(x) if x not in ("", None) else None
def rate(a, b): return round(a / b * 100, 2) if a is not None and b else None
rows = list(csv.DictReader(open(ROOT / "pool.csv", encoding="utf-8")))
for r in rows:
    r["age_days"] = float(r["age_days"]) if r["age_days"] else None
    for k in ("views", "likes", "comments", "shares", "saves", "creator_followers", "duration_s", "transcript_words"): r[k] = i(r[k])
    r["age_band"] = band(r["age_days"])
    r["like_rate_pct"] = rate(r["likes"], r["views"]); r["share_rate_pct"] = rate(r["shares"], r["views"])
    r["comment_rate_pct"] = rate(r["comments"], r["views"]); r["save_rate_pct"] = rate(r["saves"], r["views"])
    r["views_per_day"] = round(r["views"] / r["age_days"]) if r["views"] is not None and r["age_days"] else None
    r["tier"] = ""
eligible = [r for r in rows if r["age_days"] is not None and r["age_days"] >= MIN_AGE and r["views"] is not None and (r["transcript_words"] or 0) >= MIN_WORDS
            and r["roblox"] == "True" and (r["transcript_source"] or "").lower().startswith("eng")]
def take(cands, used):
    out, per = [], {}
    for r in cands:
        if r["id"] in used or per.get(r["creator"], 0) >= PER_CREATOR: continue
        out.append(r); per[r["creator"]] = per.get(r["creator"], 0) + 1; used.add(r["id"])
        if len(out) == N: break
    return out
used = set()
top = take(sorted(eligible, key=lambda r: -r["views"]), used)
flop = take(sorted(eligible, key=lambda r: r["views"]), used)
med = sorted(r["views"] for r in eligible)[len(eligible) // 2]
mid = take(sorted(eligible, key=lambda r: abs(math.log10(r["views"] + 1) - math.log10(med + 1))), used)
mid.sort(key=lambda r: -r["views"])
for name, tier in (("TOP", top), ("MID", mid), ("FLOP", flop)):
    for r in tier: r["tier"] = name
def fmt(n): return "—" if n is None else f"{n:,}"
def ts(s): return f"{s // 60:02d}:{s % 60:02d}"
def write_md(name, tier, blurb):
    vs = [r["views"] for r in tier]
    L = [f"# {name} tier: TikTok “In My World / In This Town” videos ({len(tier)})", "",
         blurb, "", f"Views in this tier: {fmt(min(vs))} to {fmt(max(vs))}. All posts are Roblox-tagged, have English speech and were at least {MIN_AGE} days old when observed (26 Nov 2026 UTC). "
         "Metrics are TikTok's public counts at that moment, collected through Apify. Transcripts are TikTok's own automatic speech-recognition subtitles. "
         "They are machine-made and unchecked, so slang, names and on-screen-only text may be wrong or missing. "
         "Rates are per 100 views. Follower counts are the creator's at observation, so big accounts start with an advantage.", ""]
    for n, r in enumerate(tier, 1):
        lines = json.loads(r["transcript"])
        L += [f"## {name}-{n:02d} · @{r['creator']} · {fmt(r['views'])} views", "",
              f"- URL: {r['url']}",
              f"- Posted {r['posted_at_utc'][:10]} · {r['age_days']:.0f} days old ({r['age_band']}) · {r['duration_s']} s · creator followers {fmt(r['creator_followers']) if r['creator_followers'] else '0 as returned (probably missing)'}",
              f"- Likes {fmt(r['likes'])} ({r['like_rate_pct']}%) · comments {fmt(r['comments'])} ({r['comment_rate_pct']}%) · shares {fmt(r['shares'])} ({r['share_rate_pct']}%) · saves {fmt(r['saves'])} ({r['save_rate_pct']}%) · ~{fmt(r['views_per_day'])} views/day",
              f"- Roblox-tagged: {'yes' if r['roblox'] == 'True' else 'no'} · sound: {r['sound'] or '—'}{' (original)' if r['sound_original'] == 'True' else ''}",
              f"- Caption: {r['caption'].strip() or '—'}", "", "Transcript:", ""]
        L += [f"[{ts(s)}] {t}" for s, t in lines] + [""]
    (OUT / f"{name}-50.md").write_text("\n".join(L), encoding="utf-8")
write_md("TOP", top, "The most-viewed eligible posts in the collected pool.")
write_md("MID", mid, f"The eligible posts closest to the pool's median view count ({fmt(med)}), on a log scale.")
write_md("FLOP", flop, "The least-viewed eligible posts: old enough to have had their chance, with real speech, and still little reach.")
cols = ["tier", "id", "url", "creator", "creator_followers", "posted_at_utc", "observed_at_utc", "age_days", "age_band", "duration_s", "views", "views_per_day",
        "likes", "like_rate_pct", "comments", "comment_rate_pct", "shares", "share_rate_pct", "saves", "save_rate_pct", "roblox", "language", "sound", "sound_original",
        "caption", "transcript_source", "transcript_words", "transcript_text", "discovery_route", "apify_run_id"]
with open(OUT / "ALL-POSTS.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, cols, extrasaction="ignore"); w.writeheader()
    for r in sorted(rows, key=lambda r: -(r["views"] or 0)):
        w.writerow({**r, "transcript_text": " ".join(t for _, t in json.loads(r["transcript"]))})
print("eligible", len(eligible), "median", med, "| top", len(top), top[-1]["views"], "| mid", len(mid), mid[-1]["views"], mid[0]["views"], "| flop", len(flop), flop[-1]["views"])
import collections; print("all bands", collections.Counter(r["age_band"] for r in rows))
for nm, t in (("top", top), ("mid", mid), ("flop", flop)): print(nm, "creators", len({r['creator'] for r in t}), "roblox", sum(r['roblox']=='True' for r in t), "median age", sorted(r['age_days'] for r in t)[25])

# ---- Untiered posts: reason + one navigable file per reason
import re, shutil
top_floor, flop_ceiling = top[-1]["views"], flop[-1]["views"]
mid_lo, mid_hi = min(r["views"] for r in mid), max(r["views"] for r in mid)
elig_ids = {r["id"] for r in eligible}
SECTIONS = {
 "A": ("NEW-UNDER-5-DAYS", "Too new to judge: under 5 days old",
       "Posted in the 5 days before collection, so their numbers are still moving. Use them to see what is being made right now and how posts do in their first hours and days, not as winners or flops. Grouped by age."),
 "B": ("NOT-ROBLOX", "Same format, not Roblox",
       "Captioned or tagged \"in my world / this town\" but not Roblox-tagged: other animation styles, live action, and different memes that share the phrase (for example \"in my world everyone's a pony\"). Useful to see which parts of the formula travel outside Roblox."),
 "C": ("NO-SPEECH", "Little or no speech",
       "No usable spoken transcript: music-only, text-on-screen stories, very short clips, or compilations too long to transcribe here. The caption is the main clue to what they are."),
 "D": ("NOT-ENGLISH", "Not English", "Spoken in another language. Transcripts are kept in the original language."),
 "E": ("CREATOR-CAP", "Would qualify, but the creator is already used 4 times",
       f"Each tier allows at most 4 posts per creator so one channel can't dominate. These posts' views fall inside a tier's range (FLOP up to {fmt(flop_ceiling)}, MID {fmt(mid_lo)} to {fmt(mid_hi)}, TOP {fmt(top_floor)} and up) but their creator was already used. Good for checking one creator's consistency."),
 "F": ("BETWEEN-TIERS", "Eligible, but between the tiers",
       f"Old enough, Roblox, English speech, but their views fall in the gaps: between FLOP ({fmt(flop_ceiling)} and below) and MID ({fmt(mid_lo)} and above), or between MID ({fmt(mid_hi)}) and TOP ({fmt(top_floor)}). Useful for checking a formula on the in-between cases."),
}
for r in rows:
    r["untiered_reason"] = ""
    if r["tier"]: continue
    eng = (r["transcript_source"] or "").lower().startswith("eng")
    if r["age_days"] is None or r["age_days"] < MIN_AGE: k = "A"
    elif r["roblox"] != "True": k = "B"
    elif (r["transcript_words"] or 0) < MIN_WORDS: k = "C"
    elif not eng: k = "D"
    elif r["id"] in elig_ids and (r["views"] >= top_floor or r["views"] <= flop_ceiling or mid_lo <= r["views"] <= mid_hi): k = "E"
    else: k = "F"
    r["untiered_reason"] = f"{k}. {SECTIONS[k][1]}"


def premise(r):
    cap = re.sub(r"#\S+", "", r["caption"] or "").strip(" .…-|")
    first = (json.loads(r["transcript"]) or [[0, ""]])[0][1]
    s = cap if len(cap) >= 12 else first or cap or "—"
    return (s[:110] + "…" if len(s) > 110 else s).replace("|", "/")


def subband(a):
    return "Under 1 day old" if a < 1 else "1 to 3 days old" if a < 3 else "3 to 5 days old"


def entry(r, label):
    lines = json.loads(r["transcript"])
    note = " (not transcribed: over 10 minutes)" if not lines and (r["duration_s"] or 0) > 600 else ""
    E = [f"## {label} · @{r['creator']} · {fmt(r['views'])} views", "",
         f"- What it is: {premise(r)}",
         f"- Why it isn't in a tier: {r['untiered_reason'][3:]}",
         f"- Age: {r['age_days']:.1f} days (posted {(r['posted_at_utc'] or '')[:10]}) · length {r['duration_s']} s · creator followers {fmt(r['creator_followers']) if r['creator_followers'] else '0 as returned (probably missing)'}",
         f"- Likes {fmt(r['likes'])} ({r['like_rate_pct']}%) · comments {fmt(r['comments'])} ({r['comment_rate_pct']}%) · shares {fmt(r['shares'])} ({r['share_rate_pct']}%) · saves {fmt(r['saves'])} ({r['save_rate_pct']}%) · ~{fmt(r['views_per_day'])} views/day",
         f"- Roblox-tagged: {'yes' if r['roblox'] == 'True' else 'no'} · language: {r['language'] or '—'} · transcript: {r['transcript_source'] or 'none' + note} · sound: {r['sound'] or '—'}",
         f"- Link: {r['url']}",
         f"- Caption: {r['caption'].strip() or '—'}", ""]
    E += (["Transcript:", ""] + [f"[{ts(s)}] {t}" for s, t in lines] if lines else ["Transcript: none."]) + [""]
    return E


for old in OUT.glob("OTHER-*.md"):
    old.unlink()
index = ["# Other posts: index", "",
         f"Everything collected (26 Nov 2026 UTC) that isn't in TOP-50, MID-50 or FLOP-50: {sum(1 for r in rows if not r['tier'])} posts, split by why they aren't in a tier. "
         "Each file starts with a table of contents (one line per post: what it is, age, views, length), then every post with its link, metrics and full transcript. "
         "'What it is' comes from the caption or, if that's empty, the opening line; the visuals were not reviewed. "
         "Transcripts are TikTok's automatic subtitles or, where TikTok had none, local Whisper (labelled on each post). Both are machine-made and unchecked.", "",
         "| File | Posts | What's in it |", "|---|---|---|"]
for k, (slug, title, blurb) in SECTIONS.items():
    g = sorted([r for r in rows if r["untiered_reason"].startswith(k + ".")], key=lambda r: -(r["views"] or 0))
    if not g:
        continue
    fn = f"OTHER-{k}-{slug}.md"
    index.append(f"| `{fn}` | {len(g)} | {title}. {blurb.split('. ')[0]}. |")
    order = ["Under 1 day old", "1 to 3 days old", "3 to 5 days old"] if k == "A" else [""]
    L = [f"# {k}. {title} ({len(g)} posts)", "", blurb, "", "Views are TikTok's public counts at collection. Sorted by views within each group.", "", "## Contents", ""]
    body, n = [], 0
    for sb in order:
        sub = [r for r in g if not sb or subband(r["age_days"]) == sb]
        if not sub:
            continue
        if sb:
            L += [f"### {sb} ({len(sub)})", ""]
            body += [f"# {sb}", ""]
        L += ["| ID | Creator | What it is | Age (d) | Views | Length (s) |", "|---|---|---|---|---|---|"]
        for r in sub:
            n += 1
            label = f"{k}-{n:03d}"
            L.append(f"| {label} | @{r['creator']} | {premise(r)} | {r['age_days']:.1f} | {fmt(r['views'])} | {r['duration_s']} |")
            body += entry(r, label)
        L.append("")
    (OUT / fn).write_text("\n".join(L + ["---", ""] + body), encoding="utf-8")
(OUT / "OTHER-00-INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
cols.insert(1, "untiered_reason")
with open(OUT / "ALL-POSTS.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, cols, extrasaction="ignore"); w.writeheader()
    for r in sorted(rows, key=lambda r: -(r["views"] or 0)):
        w.writerow({**r, "transcript_text": " ".join(t for _, t in json.loads(r["transcript"]))})
import collections
print(collections.Counter(r["untiered_reason"][:1] for r in rows if not r["tier"]))
print("untiered without transcript:", sum(1 for r in rows if not r["tier"] and not json.loads(r["transcript"])))
dl = Path.home() / "Downloads" / OUT.name
shutil.copytree(OUT, dl, dirs_exist_ok=True)
for old in dl.glob("OTHER-POSTS.md"):
    old.unlink()
print("copied to", dl)
