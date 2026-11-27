"""Recompute the objective numbers in Gemini's In My World report from our own files (2026-11-26 bank)."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(project_root / "scripts"), str(project_root / "research" / "tiktok-genre")]
import research_common as rc

import csv, json, re, statistics as st, difflib
from pathlib import Path
ROOT = rc.ROOT
EXP = ROOT / "exports/share/research/tiktok-in-my-world-2026-11-26"
pool = {r["id"]: r for r in csv.DictReader(open(ROOT / "data/local/research/creative/tiktok-genre/pool.csv", encoding="utf-8"))}
rows = {r["id"]: r for r in csv.DictReader(open(EXP / "ALL-POSTS.csv", encoding="utf-8-sig"))}
label = {}  # TOP-01 / A-156 / E-014 -> id
for f in EXP.glob("*.md"):
    cur = None
    for line in open(f, encoding="utf-8"):
        m = re.match(r"## ((?:TOP|MID|FLOP)-\d+|[A-F]-\d{3}) ", line)
        if m: cur = m[1]
        m = re.match(r"- (?:URL|Link): \S+/video/(\d+)", line)
        if m and cur: label[re.sub(r"^([A-F])-0*(\d)", r"\1-\2", cur) if cur[1] == "-" else cur] = m[1]; label[cur] = m[1]; cur = None
def R(lbl): return rows[label[lbl]]
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def text(i): return " ".join(t for _, t in json.loads(pool[i]["transcript"])) if i in pool else ""
tiers = {t: [r for r in rows.values() if r["tier"] == t] for t in ("TOP", "MID", "FLOP")}
out = []
def say(claim, gem, ours, verdict): out.append((claim, gem, ours, verdict)); print(f"[{verdict}] {claim}\n    Gemini: {gem}\n    Ours:   {ours}")
def med(t, k, f=num, keep=lambda v: v is not None):
    v = [f(r[k]) for r in tiers[t]]; v = [x for x in v if keep(x)]; return st.median(v) if v else None
def rate(t, num_k):
    v = [int(r[num_k]) / int(r["views"]) * 100 for r in tiers[t] if r[num_k] not in ("", None) and int(r["views"])]
    return round(st.median(v), 2)
for k, g in (("likes", "10.19/4.99/3.75"), ("shares", "0.70/0.29/0.14"), ("saves", "0.82/0.66/0.51"), ("comments", "0.05/(n.s.)/0.12")):
    ours = "/".join(f"{rate(t, k)}" for t in tiers)
    say(f"median {k} rate % TOP/MID/FLOP", g, ours, "CHECK")
fz = {t: st.median([int(r["creator_followers"]) for r in tiers[t] if r["creator_followers"] not in ("", "0")]) for t in tiers}
say("median non-zero followers TOP/MID/FLOP", "34,300/13,100/2,931", "/".join(f"{int(v):,}" for v in fz.values()), "CHECK")
vpf = {t: st.median([int(r["views"]) / int(r["creator_followers"]) for r in tiers[t] if r["creator_followers"] not in ("", "0")]) for t in tiers}
say("median views per follower", "40.82x/4.46x/0.99x", "/".join(f"{v:.2f}x" for v in vpf.values()), "CHECK")
def spearman(xs, ys):
    rk = lambda v: {i: r for r, i in enumerate(sorted(range(len(v)), key=lambda i: v[i]))}
    a, b = rk(xs), rk(ys); n = len(xs)
    ra = [a[i] for i in range(n)]; rb = [b[i] for i in range(n)]
    ma, mb = st.mean(ra), st.mean(rb)
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** .5
allt = sum(tiers.values(), [])
nz = [r for r in allt if r["creator_followers"] not in ("", "0")]
say("Spearman followers vs views (150, non-zero)", "0.603", f"{spearman([int(r['creator_followers']) for r in nz], [int(r['views']) for r in nz]):.3f} (n={len(nz)})", "CHECK")
for k, g in (("shares", "0.587"), ("likes", "0.549"), ("comments", "-0.382")):
    say(f"Spearman {k} rate vs views", g, f"{spearman([int(r[k]) / int(r['views']) for r in allt], [int(r['views']) for r in allt]):.3f}", "CHECK")
def route(r):
    d = r["discovery_route"]; s = "in my" in d or "in this" in d or "#" in d or d.startswith("in "); c = "None" in d or d == "" or "|" in d
    return d
def band_share(t, lo, hi): return sum(lo <= float(r["age_days"]) < hi for r in tiers[t]) / 50 * 100
say("share 5-7 days old TOP/MID/FLOP", "30%/8%/14%", "/".join(f"{band_share(t, 5, 7):.0f}%" for t in tiers), "CHECK")
wpm = {t: st.median([int(r["transcript_words"]) / int(r["duration_s"]) * 60 for r in tiers[t]]) for t in tiers}
say("median words/min (words/duration)", "218/219/231", "/".join(f"{v:.0f}" for v in wpm.values()), "CHECK")
say("median duration s", "109/120/114", "/".join(f"{med(t, 'duration_s'):.0f}" for t in tiers), "CHECK")
sub = {t: [r for r in tiers[t] if re.search(r"subscrib", text(r["id"]), re.I)] for t in tiers}
say("transcripts saying 'subscribe' TOP/MID/FLOP", "0/0/6", "/".join(str(len(v)) for v in sub.values()), "CHECK")
for t, v in sub.items():
    for r in v: print("      subscribe:", t, r["creator"], r["views"], re.search(r".{0,60}subscrib.{0,40}", text(r["id"]), re.I)[0])
rule = {t: sum(bool(re.match(r"\s*(in (this|my|our) (world|town|city|village|universe))", text(r["id"]), re.I)) for r in tiers[t]) for t in tiers}
say("first words are 'In this/my town/world' TOP/MID/FLOP", "46/46/46 (92%)", "/".join(map(str, rule.values())), "CHECK")
def band_top(lo, hi):
    b = [r for r in allt if lo <= int(r["duration_s"]) <= hi]; return f"{sum(r['tier'] == 'TOP' for r in b)}/{len(b)} TOP"
say("duration bands: share TOP among tiered", "46-75s 44.8%; 76-115s 31.6%; >170s 14.3% (3/21); >240s 0/12",
    f"46-75s {band_top(46, 75)}; 76-115s {band_top(76, 115)}; >170s {band_top(171, 99999)}; >240s {band_top(241, 99999)}", "CHECK")
def sim(a, b): return difflib.SequenceMatcher(None, text(a)[:1500].lower(), text(b)[:1500].lower()).ratio()
for a, b, g in (("TOP-32", "FLOP-49", "same volcano story, 172x"), ("TOP-21", "MID-36", "MID-36 = story 1 of TOP-21, 66.7x drop"),
                ("TOP-08", "MID-30", "beat-for-beat reskin burger->cow, 139x")):
    ra, rb = R(a), R(b)
    say(f"{a} vs {b}", g, f"text similarity {sim(ra['id'], rb['id']):.2f}; views {int(ra['views']):,} vs {int(rb['views']):,} ({int(ra['views']) / max(1, int(rb['views'])):.0f}x)", "CHECK")
# verbatim reposts: best match elsewhere in the 631
ids = list(pool)
for lbl in ("FLOP-06", "FLOP-08", "FLOP-23", "FLOP-34", "FLOP-45", "FLOP-49", "MID-49", "FLOP-38", "FLOP-42"):
    i = label[lbl]; t0 = text(i)[:800].lower()
    best = max((difflib.SequenceMatcher(None, t0, text(j)[:800].lower()).quick_ratio(), j) for j in ids if j != i and text(j))
    s = difflib.SequenceMatcher(None, t0, text(best[1])[:800].lower()).ratio()
    say(f"{lbl} repost?", "verbatim_repost", f"closest other post similarity {s:.2f} (@{rows[best[1]]['creator']}, {int(rows[best[1]]['views']):,} views, posted {rows[best[1]]['posted_at_utc'][:10]} vs {rows[i]['posted_at_utc'][:10]})", "CHECK")
for lbl, g in (("TOP-43", "916.4k"), ("E-14", "91.3k"), ("MID-23", "51.2k"), ("TOP-14", "3.3M"), ("TOP-11", "4.1M"), ("TOP-50", "545.2k"), ("TOP-10", "4.8M"), ("TOP-42", "919.1k"), ("TOP-02", "14.0M"), ("E-1", "5.1M"),
               ("A-156", "2.0M zaylento screen time"), ("A-266", "26.8M K-pop"), ("A-150", "8.2M neck/NO"), ("A-152", "6.2M letter S"), ("A-271", "4.1M Indonesian"), ("A-2", "1.3M comment section"), ("A-267", "6.7M almost happens")):
    if lbl in label:
        r = R(lbl); say(f"{lbl} views", g, f"{int(r['views']):,} @{r['creator']} — {(r['caption'] or text(r['id']))[:70]}", "CHECK")
    else: say(f"{lbl} views", g, "label not found", "CHECK")
A = [r for r in rows.values() if r["untiered_reason"].startswith("A")]
say("OTHER-A >=500k / >=1M", "48 / 37", f"{sum(int(r['views']) >= 500000 for r in A)} / {sum(int(r['views']) >= 1000000 for r in A)} (n={len(A)})", "CHECK")
big = [r for r in A if int(r["views"]) >= 500000]
huss = [r for r in big if re.search(r"huss|\b6[ -]?7\b|six seven|tung", (r["caption"] + " " + text(r["id"])), re.I)]
say("Huss/6-7/Tung share of OTHER-A >=500k", "22.9%", f"{len(huss)}/{len(big)} = {len(huss) / len(big) * 100:.1f}% (keyword match)", "CHECK")
json.dump(label, open(ROOT / "data/local/research/gemini/label_map.json", "w"), indent=0)
