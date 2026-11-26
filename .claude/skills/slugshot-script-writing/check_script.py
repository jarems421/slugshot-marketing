"""Text signals for a draft Slugshot script (slugshot-script-writing skill). Signals, not a quality verdict.

  python .claude/skills/slugshot-script-writing/check_script.py DRAFT.txt [--seconds 90] [--caption "..."] [--format imw]

Reads plain text or the ss dialogue format (NAME (direction): line, [beat s]). Reports: words and length at genre
pace (a reference), speech rhythm, "not X, it's Y" pivots, the watch list (phrases that lean towards FLOP in the
26 Nov In My World bank), stock moves and names that make scripts sound alike, and the closest of the 631
collected posts (copies never reached TOP). With --format imw it also notes the genre's rule-line convention.
Nothing is blocked; a script can pass every signal and still be dull, or break one on purpose and be great.
"""
import argparse, csv, difflib, json, re, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
POOL = ROOT / "data/local/research/creative/tiktok-genre/pool.csv"
WPM = 210
# phrase: posts containing it among 150 tiered In My World transcripts, TOP/MID/FLOP (26 Nov 2026)
WATCH = {"suddenly": (5, 10, 11), "nobody knows why": (1, 1, 5), "i couldn't believe": (0, 3, 2), "something unbelievable": (0, 1, 2),
         "everything changed": (0, 0, 1), "subscribe": (0, 1, 6), "ranked": (0, 0, 3)}
STOCK_MOVES = {"you see": 37, "except me": 25, "but there's one thing": 8, "and that's when": 9}   # posts of 150 using them
STOCK_NAMES = {"Max": 17, "Leo": 17, "Mia": 12, "Theo": 11, "Sam": 8, "Lily": 6}
RULE = re.compile(r"\b(in|on) (this|my|our) (world|town|city|village|school|family)\b", re.I)
PIVOT = re.compile(r"\b(not (just|only) [^.?!]{1,40}?, (it's|it is|but)|(it|this|that) (isn't|wasn't|is not|was not) [^.?!]{1,40}?[,.;] (it's|it was|it is))", re.I)


def spoken(text):
    out = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or re.match(r"^\[(beat|overlap)", s, re.I):
            continue
        m = re.match(r"^([A-Z][A-Z0-9_ ]*?)\s*(?:\([^)]*\))?\s*:\s*(.+)$", s)
        out.append((m[1] if m else "NARRATOR", m[2] if m else s))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft", type=Path)
    ap.add_argument("--seconds", type=float, help="target length; reports the word budget at genre pace (a reference)")
    ap.add_argument("--caption", default="")
    ap.add_argument("--format", choices=["imw", "other"], default="other")
    a = ap.parse_args()
    lines = spoken(a.draft.read_text(encoding="utf-8"))
    text = " ".join(t for _, t in lines)
    low = text.lower()
    words = len(text.split())
    print("Signals, not a verdict.")
    print(f"Length: {words} words, about {words / WPM * 60:.0f} s at {WPM} wpm (In My World genre pace; a reference, not a target)")
    if a.seconds:
        budget = round(a.seconds * WPM / 60)
        print(f"  Target {a.seconds:.0f} s at genre pace is about {budget} words ({words - budget:+d}). A deliberately slower read is a valid choice.")
    narr = " ".join(t for who, t in lines if who.startswith("NARRATOR"))  # rhythm is about narration; quick dialogue is meant to be short
    sents = [s for s in re.split(r"(?<=[.!?])\s+", narr) if s.strip()]
    lens = [len(s.split()) for s in sents]
    if len(lens) >= 6:
        mid = sum(10 <= n <= 20 for n in lens) / len(lens)
        sd = statistics.pstdev(lens)
        tag = "samey: mix very short lines with longer ones" if mid >= 0.5 or sd < 2.5 else "varied"
        print(f"Narration rhythm: {len(lens)} sentences, {min(lens)}-{max(lens)} words, spread {sd:.1f}, {mid:.0%} in the 10-20 band ({tag})")
    pivots = [m.group(0) for m in PIVOT.finditer(text)]
    for p in pivots:
        print(f"PIVOT \"{p[:70]}\": say what the thing is")
    hits = [(p, c) for p, c in WATCH.items() if p in low]
    for p, c in hits:
        print(f"WATCH '{p}' (in {c[0]}/{c[1]}/{c[2]} TOP/MID/FLOP transcripts): replace with a concrete moment, not a synonym")
    echoes = [f"'{m}' ({n}/150 posts)" for m, n in STOCK_MOVES.items() if m in low]
    names = [f"{n} ({c}/150)" for n, c in STOCK_NAMES.items() if re.search(r"\b" + n + r"\b", text)]
    if echoes or names:
        print("SAME-AS-EVERYONE: " + ", ".join(echoes + names) + ". Fine if chosen; consider a fresher move or name")
    if text.count("—") or text.count("..."):
        print(f"TTS: {text.count(chr(8212))} em dashes, {text.count('...')} ellipses; use [beat] for pauses instead")
    if a.format == "imw":
        first = lines[0][1] if lines else ""
        print(("CONVENTION met" if RULE.search(first) else "CONVENTION broken") + f": rule line first (every tier does it; not an advantage): {first[:80]!r}")
    if a.caption:
        cap = re.sub(r"#\S+|@\S+", "", a.caption)
        rest = re.sub(r"^\W*(in (this|my|our) (town|world|city))", "", re.sub(r"[^\w\s]", "", cap).lower().strip()).strip()
        print(("OK    " if len(rest.split()) >= 3 else "CHECK ") + "Caption states the premise (In My World: TOP 43/50 vs FLOP 32/50)")
    if POOL.exists():
        rows = list(csv.DictReader(open(POOL, encoding="utf-8")))
        mine, best = low[:900], (0, None)
        for r in rows:
            t = " ".join(x for _, x in json.loads(r["transcript"])).lower()[:900]
            if not t:
                continue
            sm = difflib.SequenceMatcher(None, mine, t)
            if sm.real_quick_ratio() > best[0] and sm.quick_ratio() > best[0]:
                s = sm.ratio()
                if s > best[0]:
                    best = (s, r)
        s, r = best
        if r is not None:
            verdict = "COPY? " if s >= 0.6 else ("SIMILAR" if s >= 0.35 else "OK    ")
            print(f"{verdict} Closest of 631 collected posts: {s:.2f} to @{r['creator']} ({int(r['views']):,} views): {r['caption'][:60]!r}")
    print("Then critique it (references/critique.md): premise, predictability, humour, payoff, Slugshot fit.")


if __name__ == "__main__":
    main()
