"""Shared paths and file helpers for the TikTok genre tools."""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import research_common as rc  # noqa: E402

DATA_DIR = rc.DATA / "creative" / "tiktok-genre"
MEDIA_DIR = rc.ROOT / "media" / "research" / "tiktok-genre"
PILOT_EXPORT = rc.SHARE / "tiktok-in-my-world-2026-11-26"


def read_json(path):
    """Read a saved Actor dataset, input or transcript."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value, *, indent=1):
    """Write a UTF-8 dataset or receipt."""
    Path(path).write_text(
        json.dumps(value, indent=indent, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def preferred_track(tracks):
    """Prefer an English caption track, falling back to the first offered track."""
    return next(
        (
            track
            for track in tracks
            if (track.get("language") or "").lower().startswith("eng")
        ),
        tracks[0] if tracks else None,
    )


def read_csv(path):
    """Read a plain UTF-8 or Excel-compatible UTF-8 CSV."""
    with Path(path).open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))
