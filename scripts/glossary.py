"""Slugshot glossary: correct game terms in captions, and respell them for TTS.

  python scripts/glossary.py fix <file.srt|file.words.json> [...]   correct files in place
  python scripts/glossary.py test                                    self-check

Matching works on whole words, ignoring case and punctuation, and can merge several
words into one (Whisper's "the Slug's Hoe" -> "the Slugshot", keeping the timings).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY = ROOT / "config" / "glossary.json"


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def load():
    terms = json.loads(GLOSSARY.read_text(encoding="utf-8"))["terms"]
    patterns = []  # (normalised tokens, canonical term), longest first so "boon doc" beats "boon"
    for t in terms:
        for variant in [t["term"], *t.get("misheard", [])]:
            toks = [norm(w) for w in variant.replace("-", " ").split()]
            patterns.append(([x for x in toks if x], t["term"]))
            joined = norm(variant)
            if len(toks) > 1:  # also match it written as one word ("slugshot", "boondoc")
                patterns.append(([joined], t["term"]))
    patterns.sort(key=lambda p: -len(p[0]))
    return terms, patterns


def whisper_prompt():
    terms, _ = load()
    return ", ".join(t["term"] for t in terms)


def tts_text(text):
    """Replace terms with their 'say' respellings (only terms that have one)."""
    terms, _ = load()
    for t in terms:
        if "say" in t:
            text = re.sub(rf"\b{re.escape(t['term'])}\b", t["say"], text, flags=re.I)
    return text


def distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def fuzzy(window, term):
    """2-3 words that, joined, are within one letter of a coined term (two for long ones).
    Single words are never fuzzy-matched, so real words like 'sloppy' stay as they are."""
    joined, target = "".join(window), norm(term)
    if len(window) < 2 or len(target) < 7 or abs(len(joined) - len(target)) > 2:
        return False
    return distance(joined, target) <= (1 if len(target) < 10 else 2)


def fix_tokens(tokens):
    """tokens: list of display strings (may carry leading spaces and punctuation).
    Returns [(start_index, end_index_exclusive, new_text)] for each replacement, non-overlapping."""
    terms, patterns = load()
    fuzzy_patterns = [(n, t["term"]) for t in terms for n in (3, 2)]
    keys = [norm(t) for t in tokens]
    out, i = [], 0
    while i < len(tokens):
        for pat, term in patterns + fuzzy_patterns:
            exact = isinstance(pat, list)
            n = len(pat) if exact else pat
            if (keys[i:i + n] == pat) if exact else (i + n <= len(keys) and fuzzy(keys[i:i + n], term)):
                first, last = tokens[i], tokens[i + n - 1]
                lead = re.match(r"^\s*", first).group(0)
                trail = re.search(r"[^\w']*$", last).group(0)
                new = lead + term + trail
                if new != "".join(tokens[i:i + n]) and new.strip() != " ".join(t.strip() for t in tokens[i:i + n]):
                    out.append((i, i + n, new))
                i += n
                break
        else:
            i += 1
    return out


def fix_words(words, key="word"):
    """Correct a list of Whisper/Remotion word dicts in place-style; returns (new_list, changes)."""
    reps = fix_tokens([w[key] for w in words])
    if not reps:
        return words, []
    new, changes, j = [], [], 0
    for a, b, text in reps:
        new.extend(words[j:a])
        merged = dict(words[a])
        merged[key] = text
        for end_key in ("end", "endMs"):
            if end_key in merged:
                merged[end_key] = words[b - 1][end_key]
        for p in ("probability", "confidence"):
            if p in merged:
                merged[p] = min(w.get(p, 1) for w in words[a:b])
        new.append(merged)
        changes.append(("".join(w[key] for w in words[a:b]).strip(), text.strip()))
        j = b
    new.extend(words[j:])
    return new, changes


def fix_line(line):
    tokens = re.findall(r"\s*\S+", line)
    new, changes = fix_words([{"w": t} for t in tokens], key="w")
    return "".join(t["w"] for t in new), changes


def fix_file(path):
    path = Path(path)
    changes = []
    if path.suffix == ".json":
        words = json.loads(path.read_text(encoding="utf-8"))
        words, changes = fix_words(words, key="text")
        path.write_text(json.dumps(words, indent=1), encoding="utf-8")
    else:
        lines = []
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if "-->" in line or line.strip().isdigit() or not line.strip():
                lines.append(line)
                continue
            fixed, c = fix_line(line)
            lines.append(fixed)
            changes += c
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for old, new in changes:
        print(f"  {path.name}: '{old}' -> '{new}'")
    return changes


def test():
    cases = {
        "This is a test render for the Slug's Hoe toolkit.": "This is a test render for the Slugshot toolkit.",
        "He brought inferno, I brought floppy!": "He brought Inferno, I brought Floppy!",
        "Ram stone or aqua beak here?": "Rammstone or Aquabeek here?",
        "Play slug shot on Roblocks.": "Play Slugshot on Roblox.",
        "Boon dock heals in the slug grove.": "Boon Doc heals in the Slug Grove.",
        "A slug that floats.": "A slug that floats.",
        "the slug's Hoh toolkit": "the Slugshot toolkit",
        "That was sloppy play.": "That was sloppy play.",
        "Aqua beak and frost crawlers": "Aquabeek and Frostcrawler",
        "slugs are hot today": "slugs are hot today",
    }
    ok = True
    for src, want in cases.items():
        got, _ = fix_line(src)
        ok &= got == want
        print(("PASS " if got == want else "FAIL ") + f"{src!r} -> {got!r}")
    words = [{"word": " the", "start": 1.4, "end": 1.6}, {"word": " Slug's", "start": 1.6, "end": 1.9},
             {"word": " Hoe", "start": 1.9, "end": 2.2}, {"word": " Toolkit.", "start": 2.2, "end": 2.7}]
    new, _ = fix_words(words)
    timing_ok = [w["word"] for w in new] == [" the", " Slugshot", " Toolkit."] and new[1]["end"] == 2.2
    print(("PASS " if timing_ok else "FAIL ") + "merged word keeps start 1.6 / end 2.2")
    print("PASS" if tts_text("Slugshot and Aquabeek") == "Slug-shot and Aqua-beak" else "FAIL", "TTS respelling")
    return ok and timing_ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        for f in sys.argv[2:]:
            fix_file(f)
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.exit(0 if test() else 1)
    else:
        print(__doc__)
