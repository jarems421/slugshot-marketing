"""Summarise narration pace by tier in a built TikTok genre bank."""

import argparse
import json
import statistics
from pathlib import Path

from genre_common import DATA_DIR, PILOT_EXPORT, read_csv


def rates(rows, transcripts, tier):
    """Measure words per minute from cue starts, excluding the final cue's words."""
    pace, two_million = [], []
    for row in rows:
        if row["tier"] != tier:
            continue
        cues = json.loads(transcripts[row["id"]]["transcript"])
        if len(cues) < 4:
            continue
        words = sum(len(text.split()) for _, text in cues[:-1])
        span = cues[-1][0] - cues[0][0]
        if span >= 10:
            pace.append(words / span * 60)
        if tier == "TOP" and int(row["views"]) >= 2_000_000:
            two_million.append(words / max(span, 1) * 60)
    return pace, two_million


def main(argv=None):
    """Read the pool and built bank and print a pace summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posts", type=Path, default=PILOT_EXPORT / "ALL-POSTS.csv")
    parser.add_argument("--pool", type=Path, default=DATA_DIR / "pool.csv")
    args = parser.parse_args(argv)
    rows = read_csv(args.posts)
    transcripts = {row["id"]: row for row in read_csv(args.pool)}
    for tier in ("TOP", "MID", "FLOP"):
        pace, popular = rates(rows, transcripts, tier)
        if len(pace) < 2:
            print(f"{tier} {len(pace)} usable posts (need at least two for quartiles)")
        else:
            first, _, third = statistics.quantiles(pace, n=4)
            print(
                f"{tier} {len(pace)} speech WPM median {statistics.median(pace):.0f}, "
                f"middle half {first:.0f}-{third:.0f}, min {min(pace):.0f} max {max(pace):.0f}"
            )
        if popular:
            print(
                f"   TOP posts >=2M views: {len(popular)} median {statistics.median(popular):.0f}"
            )


if __name__ == "__main__":
    main()
