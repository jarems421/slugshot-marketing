r"""Generate Slugshot music beds with Google Lyria (Gemini API, paid; owner approved 2026-11-26, cap $0.50).

  python scripts/music_gen.py [M1 M2 ...]      default: all tracks in docs/creative/music-brief.md

Writes assets\music\<ID>-<name>.<ext>, logs each in assets\LICENSES.csv and a cost line in
data\local\spend\lyria.jsonl. Outputs carry Google's SynthID watermark. Check Google's terms before publishing.
"""
import base64, csv, json, sys, time, urllib.error, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_common import env_value
from gemini_tts import _find_audio

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "music"
LEDGER = ROOT / "data" / "local" / "spend" / "lyria.jsonl"
URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
CAP_USD = 0.50
COMMON = ("Instrumental only, no vocals, no choir. Leave the 1-4 kHz speech range sparse: short motifs with space between them, "
          "melody in plucks and bells, warmth below. Key of D. Loop-friendly start and end. A bed to sit under a fast spoken story narration.")
TRACKS = {
    "M1": ("cavern-curious", "lyria-3-clip-preview", 0.04, "108 BPM whimsical, playful story bed in D major: pizzicato strings and marimba, celesta and crystal-bell accents, soft water-drip and squishy percussion, a warm low glowing hum. Tactile cavern fantasy, comic-book charm, light and curious."),
    "M2": ("cavern-sneak", "lyria-3-clip-preview", 0.04, "108 BPM in D minor, the same playful cavern world turned sneaky and suspicious: low pizzicato strings, ticking woodblock, a soft cave drone underneath, an occasional glassy crystal shimmer. Rising stakes, still slightly comic."),
    "M3": ("warm-glow", "lyria-3-clip-preview", 0.04, "Slow, warm and tender in D major: soft felt piano, gentle strings, a faint crystal shimmer, distant water drops in a glowing cave. A resolving, heartfelt ending."),
    "M4": ("glow-dread", "lyria-3-clip-preview", 0.04, "Slow and eerie in D minor: a lonely music box melody, a deep cave drone, distant water drips, a faint glassy whine. Very sparse, creeping dread for a rule-horror story."),
    "M5": ("arena-hype", "lyria-3-clip-preview", 0.04, "120 BPM comic-book epic in D minor, deliberately over-serious: punchy drums, brass stabs, crystal impact hits, a heroic build with short gaps for jokes. A showdown in a glowing crystal arena."),
    "M6": ("nature-doc", "lyria-3-clip-preview", 0.04, "Gentle orchestral wonder in D major, nature-documentary calm: strings and woodwinds, soft harp, a sense of awe that is a little too majestic for its tiny subject."),
    "M7": ("full-arc", "lyria-3.5", 0.08, "A 2-minute instrumental story bed in D. 0:00-1:10 whimsical and playful at 108 BPM (pizzicato, marimba, celesta, water-drip percussion, warm cave hum); "
           "around 1:10 shift into a sneaky, suspenseful version in D minor (low pizzicato, ticking woodblock, cave drone); final 25 seconds resolve into warm, tender felt piano and strings with a crystal shimmer."),
}


def spent():
    if not LEDGER.exists():
        return 0.0
    return sum(json.loads(l)["usd"] for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip())


def generate(tid):
    name, model, usd, prompt = TRACKS[tid]
    if spent() + usd > CAP_USD:
        raise SystemExit(f"cap ${CAP_USD:.2f} would be passed (spent ${spent():.2f}); ask the owner")
    body = {"model": model, "input": [{"type": "user_input", "content": [{"type": "text", "text": prompt + " " + COMMON}]}],
            "response_format": {"type": "audio"}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"x-goog-api-key": env_value("GEMINI_API_KEY"), "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 503) and attempt < 3:
                time.sleep(20 * (attempt + 1)); continue
            raise SystemExit(f"Lyria failed ({e.code}): {msg}")
    audio = _find_audio(data)
    if not audio:
        raise SystemExit(f"no audio in response (keys: {sorted(data)[:8]})")
    raw = base64.b64decode(audio)
    ext = "wav" if raw[:4] == b"RIFF" else "mp3"
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{tid}-{name}.{ext}"
    path.write_bytes(raw)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "track": tid, "model": model, "usd": usd}) + "\n")
    log = ROOT / "assets" / "LICENSES.csv"
    rows = list(csv.DictReader(log.open(encoding="utf-8")))
    rel = path.relative_to(ROOT).as_posix()
    if rel not in {r["file"] for r in rows}:
        rows.append({"file": rel, "kind": "music", "source_url": f"Google Lyria ({model}) via Gemini API; prompt in scripts/music_gen.py",
                     "licence": "AI-generated for the owner (Google Gemini API terms; SynthID watermark)", "attribution_required": "no",
                     "allowed_platforms": "check Google terms before publishing", "commercial_ok": "check", "added": date.today().isoformat(),
                     "notes": f"{tid} {name}; owner-approved paid generation"})
        with log.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"{tid} {name}: {len(raw) // 1024} KB {ext} ({model}, ~${usd:.2f}; total ~${spent():.2f})", flush=True)


if __name__ == "__main__":
    for t in (sys.argv[1:] or list(TRACKS)):
        generate(t)
