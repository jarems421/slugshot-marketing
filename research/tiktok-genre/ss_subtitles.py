"""Cache subtitle tracks returned by Social Scrapers Actors."""

import argparse
import time
from pathlib import Path

from genre_common import DATA_DIR, preferred_track, rc, read_json


def fetch_tracks(items, subtitles):
    """Save one track per video and return cached, missing and failed counts."""
    saved = missing = failed = 0
    for item in items:
        if item.get("dataType") != "video":
            continue
        destination = subtitles / f"{item['id']}.vtt"
        if destination.exists():
            saved += 1
            continue
        track = preferred_track(item.get("subtitles") or [])
        if not track:
            missing += 1
            continue
        try:
            body, _ = rc.http(track["url"], timeout=30)
            destination.write_bytes(body)
            saved += 1
        except rc.HttpError:
            failed += 1
        time.sleep(0.05)
    return saved, missing, failed


def main(argv=None):
    """Read saved Actor datasets and cache their subtitles."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+", type=Path)
    parser.add_argument("--subtitles", type=Path, default=DATA_DIR / "subtitles")
    args = parser.parse_args(argv)
    args.subtitles.mkdir(parents=True, exist_ok=True)
    items = (item for path in args.datasets for item in read_json(path))
    saved, missing, failed = fetch_tracks(items, args.subtitles)
    print(f"subtitles saved {saved} | none offered {missing} | failed {failed}")


if __name__ == "__main__":
    main()
