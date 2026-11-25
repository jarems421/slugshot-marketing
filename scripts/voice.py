r"""Synthetic narration with Kokoro-82M (local, offline after the model download).

  .\ss voice "He brought Inferno. I brought Floppy." media\vo\test.wav --voice am_puck --speed 1.1
  .\ss voice --file scripts_in\floppy.txt media\vo\floppy.wav
  .\ss voice --list-voices

Game names are respelled from config/glossary.json ("say") so they are pronounced right.
Pauses: --sentence-pause / --clause-pause keep short breaths at meaning changes, which helps
fast narration stay understandable. Label AI voices where a platform requires it.
Runs in .venv-tts (kokoro-onnx, MIT; Kokoro-82M weights, Apache-2.0).
"""
import argparse
from pathlib import Path

import glossary

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "kokoro" / "kokoro-v1.0.onnx"
VOICES = ROOT / "models" / "kokoro" / "voices-v1.0.bin"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--file", help="read the script from a text file")
    ap.add_argument("--voice", default="am_puck", help="e.g. am_puck, am_michael, am_fenrir, af_heart, bm_george")
    ap.add_argument("--speed", type=float, default=1.1)
    ap.add_argument("--sentence-pause", type=float, default=0.18)
    ap.add_argument("--clause-pause", type=float, default=0.06)
    ap.add_argument("--list-voices", action="store_true")
    ap.add_argument("--batch", help="JSON list of {text, out, voice, speed, blend?} (scripts/dialogue.py); model loads once")
    a = ap.parse_args()

    import json

    import numpy as np
    import soundfile as sf
    from kokoro_onnx import Kokoro

    kokoro = Kokoro(str(MODEL), str(VOICES))
    if a.list_voices:
        print(", ".join(sorted(kokoro.get_voices())))
        return
    if a.batch:
        for job in json.loads(Path(a.batch).read_text(encoding="utf-8")):
            voice = job["voice"]
            if job.get("blend"):  # an original voice: a weighted mix of two style vectors
                (v1, w1), (v2, w2) = job["blend"]
                voice = kokoro.get_voice_style(v1) * w1 + kokoro.get_voice_style(v2) * w2
            samples, rate = kokoro.create(glossary.tts_text(job["text"]), voice=voice, speed=job.get("speed", 1.0),
                                          lang=job.get("lang", "en-us"))
            out = Path(job["out"])
            out.parent.mkdir(parents=True, exist_ok=True)
            sf.write(out, np.asarray(samples), rate)
            print(f"{out.name} {len(samples) / rate:.2f}s")
        return
    if a.file:
        a.out = a.out or a.text
        text = Path(a.file).read_text(encoding="utf-8")
    else:
        text = a.text
    if not text or not a.out:
        ap.error("give TEXT and OUT, or --file SCRIPT OUT")

    spoken = glossary.tts_text(text)
    samples, rate = kokoro.create(spoken, voice=a.voice, speed=a.speed, lang="en-us",
                                  sentence_pause=a.sentence_pause, clause_pause=a.clause_pause)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out, samples, rate)
    print(f"{out} ({len(samples) / rate:.1f}s, voice {a.voice}, speed {a.speed})")


if __name__ == "__main__":
    main()
