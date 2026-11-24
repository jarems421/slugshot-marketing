"""Transcribe narration (or a clip's own audio) with openai-whisper.

Writes next to --out (default: alongside the input):
  <name>.srt          short phrase captions for FFmpeg, Kdenlive and platform uploads
  <name>.words.json   word timings in Remotion's Caption format (startMs/endMs/text...)
  <name>.whisper.json Whisper's raw result, for checking

Game terms are fixed automatically from config/glossary.json (every change is printed), and the
glossary also feeds Whisper's spelling hints. Still read the SRT before using it.
"""
import argparse
import json
from pathlib import Path

import glossary

MAX_WORDS = 3
MAX_SECONDS = 1.4


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def phrases(words):
    """Group words into short on-screen phrases, breaking at punctuation."""
    group = []
    for w in words:
        group.append(w)
        text = w["word"].strip()
        too_long = w["end"] - group[0]["start"] >= MAX_SECONDS
        if len(group) >= MAX_WORDS or too_long or text[-1:] in ".,!?;:":
            yield group
            group = []
    if group:
        yield group


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="audio or video file")
    ap.add_argument("--out", help="output path stem (default: input path without extension)")
    ap.add_argument("--model", default="base.en", help="whisper model (tiny.en, base.en, small.en, ...)")
    ap.add_argument("--prompt", default=glossary.whisper_prompt(),
                    help="spelling hints passed as Whisper's initial prompt (default: glossary terms)")
    args = ap.parse_args()

    import whisper  # imported late so --help works without loading torch

    src = Path(args.input)
    stem = Path(args.out) if args.out else src.with_suffix("")
    stem.parent.mkdir(parents=True, exist_ok=True)

    model = whisper.load_model(args.model, device="cpu")
    result = model.transcribe(str(src), word_timestamps=True, fp16=False,
                              initial_prompt=args.prompt, condition_on_previous_text=False,
                              hallucination_silence_threshold=0.5)  # drops invented words over gaps
    stem.with_suffix(".whisper.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    # Whisper sometimes invents words over silence. Real speech here scores about -0.1 avg_logprob;
    # invented segments score far lower, and invented words come out near-zero confidence.
    words, ghosts = [], []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            p = w.get("probability", 1)
            invented = seg.get("avg_logprob", 0) < -2.0 or p < 0.01 or (p < 0.05 and w["end"] - w["start"] <= 0.05)
            (ghosts if invented else words).append(w)
    if ghosts:
        print("dropped invented words:", " ".join(w["word"].strip() for w in ghosts))
    if not words:
        raise SystemExit(f"No speech found in {src}")
    words, fixes = glossary.fix_words(words)
    for old, new in fixes:
        print(f"glossary: '{old}' -> '{new}'")

    srt = []
    for i, g in enumerate(phrases(words), 1):
        text = "".join(w["word"] for w in g).strip()
        srt.append(f"{i}\n{srt_time(g[0]['start'])} --> {srt_time(g[-1]['end'])}\n{text}\n")
    stem.with_suffix(".srt").write_text("\n".join(srt), encoding="utf-8")

    # Remotion @remotion/captions Caption[]: text keeps its leading space so pages join naturally.
    captions = [{
        "text": w["word"],
        "startMs": round(w["start"] * 1000),
        "endMs": round(w["end"] * 1000),
        "timestampMs": round((w["start"] + w["end"]) * 500),
        "confidence": round(w.get("probability", 0), 3),
    } for w in words]
    stem.with_suffix(".words.json").write_text(json.dumps(captions, indent=1), encoding="utf-8")

    low = [c["text"].strip() for c in captions if c["confidence"] < 0.5]
    print(f"{len(words)} words, {len(srt)} caption lines -> {stem.with_suffix('.srt')}")
    if low:
        print("Check these low-confidence words:", ", ".join(low))


if __name__ == "__main__":
    main()
