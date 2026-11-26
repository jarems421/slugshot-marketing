"""Pool TikTok Actor runs, filter to the genre and write pool.csv."""

import argparse
import json
import re
import statistics
from pathlib import Path

from apify import download
from genre_common import DATA_DIR, preferred_track, rc, read_json

FORMAT = re.compile(
    r"\bin\s+(my|this|our)\s+(world|town|city|village|universe|school|family)\b"
    r"|#(inmyworld|inthistown|inmytown|inthisworld)",
    re.I,
)
CUE_START = re.compile(r"(\d+):(\d\d):(\d\d)\.\d+\s*-->|(\d+):(\d\d)\.\d+\s*-->")
FIELDS = (
    "id",
    "url",
    "creator",
    "creator_followers",
    "posted_at_utc",
    "observed_at_utc",
    "age_days",
    "duration_s",
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "caption",
    "sound",
    "sound_original",
    "roblox",
    "language",
    "transcript_source",
    "transcript_words",
    "transcript",
    "discovery_route",
    "apify_run_id",
)


def load_runs(data_dir):
    """Keep the newest observation of each post with its discovery routes."""
    posts = {}
    for items in sorted(data_dir.glob("apify-*/items.json")):
        receipt = read_json(items.with_name("run.json"))
        for item in read_json(items):
            if not item.get("id") or item.get("error"):
                continue
            previous = posts.get(item["id"])
            observed = receipt["finishedAt"]
            route = item.get("searchQuery") or item.get("input") or ""
            if previous is None or observed > previous["_observed"]:
                if previous:
                    route = f"{previous['_route']} | {route}"
                posts[item["id"]] = {
                    **item,
                    "_observed": observed,
                    "_run": receipt["id"],
                    "_route": route,
                }
    return list(posts.values())


def vtt_lines(text):
    """Extract captions at whole-second offsets, dropping consecutive repeated cues."""
    lines = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        match = CUE_START.search(block)
        if not match:
            continue
        if match[1]:
            seconds = int(match[1]) * 3600 + int(match[2]) * 60 + int(match[3])
        else:
            seconds = int(match[4]) * 60 + int(match[5])
        body = " ".join(
            line.strip()
            for line in block.splitlines()
            if line.strip() and "-->" not in line and not line.strip().isdigit()
        )
        body = re.sub(r"<[^>]+>", "", body).strip()
        if body and (not lines or lines[-1][1] != body):
            lines.append((seconds, body))
    return lines


def transcript(item, subtitles):
    """Read provided captions or fall back to a saved Whisper result."""
    track = preferred_track((item.get("videoMeta") or {}).get("subtitleLinks") or [])
    post_id = item["id"]
    lines, source = [], None
    if track:
        path = subtitles / f"{post_id}.vtt"
        if not path.exists():
            try:
                path.write_bytes(download(track["downloadLink"]))
            except (rc.HttpError, OSError, ValueError, KeyError) as error:
                print(rc.redact(f"subtitle fail {post_id}: {error}")[:180])
        if path.exists():
            lines = vtt_lines(path.read_text(encoding="utf-8", errors="replace"))
            source = f"{track.get('language')} {track.get('source')}"
    fallback = subtitles / f"{post_id}.whisper.json"
    if not lines and fallback.exists():
        whisper = read_json(fallback)
        lines = whisper["segments"]
        language = whisper.get("language") or ""
        source = (
            f"{'eng' if language == 'en' else language} Whisper-small (local)"
            if lines
            else None
        )
    return lines, source


def pool_rows(items, subtitles):
    """Normalise matching public posts with their timestamps and transcript source."""
    for item in items:
        caption = item.get("text") or ""
        tags = " ".join(
            "#" + (tag.get("name") or "") for tag in item.get("hashtags") or []
        )
        if any(
            item.get(field) for field in ("isSlideshow", "isAd", "isSponsored")
        ) or not FORMAT.search(f"{caption} {tags}"):
            continue
        observed, posted = (
            rc.parse_time(item["_observed"]),
            rc.parse_time(item.get("createTimeISO")),
        )
        age = (
            (observed - posted).total_seconds() / 86400 if observed and posted else None
        )
        cues, source = transcript(item, subtitles)
        author, music, video = (
            item.get(key) or {} for key in ("authorMeta", "musicMeta", "videoMeta")
        )
        yield {
            "id": item["id"],
            "url": item.get("webVideoUrl"),
            "creator": author.get("name"),
            "creator_followers": author.get("fans"),
            "posted_at_utc": item.get("createTimeISO"),
            "observed_at_utc": item["_observed"],
            "age_days": round(age, 1) if age is not None else None,
            "duration_s": video.get("duration"),
            "views": item.get("playCount"),
            "likes": item.get("diggCount"),
            "comments": item.get("commentCount"),
            "shares": item.get("shareCount"),
            "saves": item.get("collectCount"),
            "caption": caption,
            "sound": music.get("musicName"),
            "sound_original": music.get("musicOriginal"),
            "roblox": "roblox" in (caption + tags).lower(),
            "language": item.get("textLanguage"),
            "transcript_source": source,
            "transcript_words": sum(len(text.split()) for _, text in cues),
            "transcript": json.dumps(cues, ensure_ascii=False),
            "discovery_route": item["_route"],
            "apify_run_id": item["_run"],
        }


def main(argv=None):
    """Write the pool and report how many posts meet the age threshold."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--min-age-days", type=int, default=14)
    args = parser.parse_args(argv)
    items = load_runs(args.data_dir)
    if not items:
        parser.exit(1, "No Actor posts found under the data directory.\n")
    subtitles = args.data_dir / "subtitles"
    subtitles.mkdir(parents=True, exist_ok=True)
    rows = list(pool_rows(items, subtitles))
    rc.write_rows(args.data_dir / "pool.csv", FIELDS, rows)
    aged = [
        row
        for row in rows
        if row["age_days"]
        and row["age_days"] >= args.min_age_days
        and row["views"] is not None
    ]
    with_transcript = sum(row["transcript_words"] >= 15 for row in aged)
    print(
        f"{len(rows)} in-format posts; {len(aged)} aged >= {args.min_age_days} d; with transcript {with_transcript}"
    )
    if aged:
        views = [row["views"] for row in aged]
        print("views min/median/max", min(views), statistics.median(views), max(views))
        print(
            "aged <2k views:",
            sum(value < 2000 for value in views),
            "| creators:",
            len({row["creator"] for row in aged}),
        )


if __name__ == "__main__":
    main()
