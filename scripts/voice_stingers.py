r"""Slugshot soundboard: short reaction lines in each character's fixed Gemini voice (owner 2026-11-26: TikTok
soundboard-style effects, but ours; never a real streamer's clips or voice).

  python scripts/voice_stingers.py [NAME ...]      default: every line below that isn't rendered yet

Writes assets\sfx\voice\<NAME>_<slug>.wav (trimmed, 48 kHz) and logs each in assets\LICENSES.csv.
Lines are drafts for the owner's ear; edit LINES and re-run with the NAME to re-record that character.
"""
import csv
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemini_tts import speak, style_for

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "sfx" / "voice"
SHORT = "One short reaction line on its own, like a soundboard clip: say only these words, once, no lead-in"
LINES = {
    "NARRATOR": [("Oh no.", "dry, deadpan"), ("Meanwhile.", "flat, a beat of comic timing"), ("Plot twist.", "dry, a hint of a smile"),
                 ("Moments later.", "documentary deadpan"), ("Anyway.", "moving on, totally unbothered"), ("That did not go well.", "deadpan understatement")],
    "FLOPPY": [("...oh.", "tiny, sleepy realisation"), ("Wait, what?", "slow, confused"), ("I'm cooked.", "drowsy, resigned"),
               ("Huh?", "sleepy, puzzled"), ("Seven damage!", "drowsy but proud")],
    "RAMMSTONE": [("HUH?!", "loud, outraged disbelief"), ("Get him!", "loud, commanding"), ("Oh, it's OVER.", "cocky, gloating"),
                  ("Nah. Nah nah nah.", "loud, refusing"), ("What did you just say?", "slow, menacing, comic")],
    "AQUABEEK": [("Wow.", "flat, unimpressed sarcasm"), ("Incredible.", "deadpan sarcasm"), ("No.", "flat, final"), ("Be serious.", "unimpressed")],
    "RAF": [("LET'S GOOO!", "huge hype, shouting with joy"), ("Yooo!", "hyped, surprised"), ("Clip that!", "excited, pointing"),
            ("He's actually HIM!", "hyped disbelief")],
    "MIRA": [("Absolutely not.", "dry, quick"), ("Okay, and?", "unbothered, dry"), ("We're so back.", "dry but pleased")],
}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:28]


def main():
    cast = json.loads((ROOT / "config" / "cast.json").read_text(encoding="utf-8"))["characters"]
    only = set(sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    log = ROOT / "assets" / "LICENSES.csv"
    rows = list(csv.DictReader(log.open(encoding="utf-8")))
    known = {r["file"] for r in rows}
    for name, lines in LINES.items():
        if only and name not in only:
            continue
        g = cast[name]["gemini"]
        for text, direction in lines:
            path = OUT / f"{name}_{slug(text)}.wav"
            if path.exists() and not only:
                continue
            raw = path.with_suffix(".raw.wav")
            speak(text, g["voice"], style_for(g, f"{SHORT}. {direction}"), raw)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af",
                            "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                            "afade=t=in:d=0.005,loudnorm=I=-16:TP=-1.5", "-ar", "48000", str(path)], check=True)
            raw.unlink()
            rel = path.relative_to(ROOT).as_posix()
            if rel not in known:
                rows.append({"file": rel, "kind": "sfx", "source_url": f"Gemini TTS prebuilt voice {g['voice']} via scripts/voice_stingers.py",
                             "licence": "AI voice generated for the owner (Google Gemini API terms); original line", "attribution_required": "no",
                             "allowed_platforms": "all (label AI voice where a platform requires)", "commercial_ok": "check",
                             "added": date.today().isoformat(), "notes": f"{name} soundboard line: {text}"})
                known.add(rel)
            print(path.name, flush=True)
    with log.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
