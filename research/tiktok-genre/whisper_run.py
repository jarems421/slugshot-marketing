"""Transcribe permitted local TikTok videos with Whisper small."""

import argparse
import os
import time
from pathlib import Path

from genre_common import DATA_DIR, MEDIA_DIR, rc, write_json


def usable_segments(result):
    """Keep nonempty cues below the original no-speech threshold."""
    return [
        [int(segment["start"]), segment["text"].strip()]
        for segment in result["segments"]
        if segment["text"].strip() and segment.get("no_speech_prob", 0) < 0.8
    ]


def main(argv=None):
    """Transcribe MP4s whose local transcript is missing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=MEDIA_DIR)
    parser.add_argument("--subtitles", type=Path, default=DATA_DIR / "subtitles")
    args = parser.parse_args(argv)
    args.subtitles.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    import whisper

    model = whisper.load_model("small")
    files = sorted(args.source_dir.glob("*.mp4"))
    for index, path in enumerate(files, 1):
        destination = args.subtitles / f"{path.stem}.whisper.json"
        if destination.exists():
            continue
        start = time.monotonic()
        try:
            result = model.transcribe(
                str(path), fp16=False, verbose=None, condition_on_previous_text=False
            )
            segments = usable_segments(result)
            write_json(
                destination,
                {
                    "language": result.get("language"),
                    "model": "openai-whisper small",
                    "segments": segments,
                },
            )
            print(
                f"{index}/{len(files)} {path.stem} {result.get('language')} {len(segments)} segs {time.monotonic() - start:.0f}s",
                flush=True,
            )
        except Exception as error:
            print(
                rc.redact(f"{index}/{len(files)} {path.stem} FAIL {error}")[:180],
                flush=True,
            )


if __name__ == "__main__":
    main()
