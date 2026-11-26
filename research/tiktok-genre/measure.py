"""Measure words per minute and pauses in local narrator WAV takes."""

import argparse
import os
from pathlib import Path

from genre_common import write_json


def measure(result):
    """Summarise a Whisper result with word timestamps."""
    words = [word for segment in result["segments"] for word in segment["words"]]
    span = (words[-1]["end"] - words[0]["start"]) if words else 0
    gaps = [second["start"] - first["end"] for first, second in zip(words, words[1:])]
    return {
        "wpm": round(len(words) / span * 60) if span else None,
        "longest_gap": round(max(gaps), 2) if gaps else None,
        "gaps_over_0.3s": sum(gap > 0.3 for gap in gaps),
        "text": result["text"].strip(),
    }


def main(argv=None):
    """Measure each WAV in the caller's directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    import whisper

    model = whisper.load_model("small.en")
    results = {}
    for path in sorted(args.directory.glob("*.wav")):
        result = model.transcribe(
            str(path), fp16=False, word_timestamps=True, language="en"
        )
        row = results[path.name] = measure(result)
        print(
            path.name,
            row["wpm"],
            "wpm | longest gap",
            row["longest_gap"],
            "| gaps>0.3s",
            row["gaps_over_0.3s"],
        )
    write_json(args.directory / "measure.json", results)


if __name__ == "__main__":
    main()
