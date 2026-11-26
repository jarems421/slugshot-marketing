"""Build TOP/MID/FLOP transcript packs and the full CSV from pool.csv."""

import argparse
import csv
import json
import math
import re
import shutil
from collections import Counter
from pathlib import Path
from statistics import median_high

from genre_common import DATA_DIR, PILOT_EXPORT, read_csv

MIN_AGE = 5
MIN_WORDS = 15
PER_CREATOR = 4
TIER_SIZE = 50
COUNT_FIELDS = (
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "creator_followers",
    "duration_s",
    "transcript_words",
)
COLUMNS = (
    "tier",
    "untiered_reason",
    "id",
    "url",
    "creator",
    "creator_followers",
    "posted_at_utc",
    "observed_at_utc",
    "age_days",
    "age_band",
    "duration_s",
    "views",
    "views_per_day",
    "likes",
    "like_rate_pct",
    "comments",
    "comment_rate_pct",
    "shares",
    "share_rate_pct",
    "saves",
    "save_rate_pct",
    "roblox",
    "language",
    "sound",
    "sound_original",
    "caption",
    "transcript_source",
    "transcript_words",
    "transcript_text",
    "discovery_route",
    "apify_run_id",
)


def age_band(age):
    """Label a post's age at the time it was observed."""
    if age is None:
        return ""
    bounds = (
        (5, "0-5d (too new to judge)"),
        (7, "5-7d"),
        (14, "7-14d"),
        (30, "14-30d"),
        (90, "30-90d"),
    )
    return next((label for limit, label in bounds if age < limit), "90d+")


def normalise(row):
    """Convert saved CSV counts to numbers and calculate within-post rates."""
    row = dict(row)
    age = row["age_days"] = float(row["age_days"]) if row["age_days"] else None
    for field in COUNT_FIELDS:
        row[field] = int(row[field]) if row[field] not in ("", None) else None
    views = row["views"]
    row["age_band"] = age_band(age)
    for count, rate in (
        ("likes", "like"),
        ("comments", "comment"),
        ("shares", "share"),
        ("saves", "save"),
    ):
        row[f"{rate}_rate_pct"] = (
            round(row[count] / views * 100, 2)
            if row[count] is not None and views
            else None
        )
    row["views_per_day"] = round(views / age) if views is not None and age else None
    row["tier"] = ""
    return row


def english_speech(row):
    return (row["transcript_source"] or "").lower().startswith("eng")


def eligible(row):
    return (
        row["age_days"] is not None
        and row["age_days"] >= MIN_AGE
        and row["views"] is not None
        and (row["transcript_words"] or 0) >= MIN_WORDS
        and row["roblox"] == "True"
        and english_speech(row)
    )


def take(candidates, used):
    """Fill one tier with distinct posts and at most four posts per creator."""
    chosen = []
    creator_counts = Counter()
    for row in candidates:
        if row["id"] in used or creator_counts[row["creator"]] >= PER_CREATOR:
            continue
        chosen.append(row)
        creator_counts[row["creator"]] += 1
        used.add(row["id"])
        if len(chosen) == TIER_SIZE:
            break
    return chosen


def select_tiers(rows):
    """Apply the historical TOP, FLOP and log-distance-to-median MID rules."""
    candidates = [row for row in rows if eligible(row)]
    if not candidates:
        return {"TOP": [], "MID": [], "FLOP": []}, None
    median = median_high(row["views"] for row in candidates)
    ordered = sorted(candidates, key=lambda row: row["views"])
    used = set()
    top = take(sorted(candidates, key=lambda row: -row["views"]), used)
    flop = take(ordered, used)
    mid = take(
        sorted(
            candidates,
            key=lambda row: abs(math.log10(row["views"] + 1) - math.log10(median + 1)),
        ),
        used,
    )
    mid.sort(key=lambda row: -row["views"])
    return {"TOP": top, "MID": mid, "FLOP": flop}, median


def fmt(value):
    return "—" if value is None else f"{value:,}"


def ts(seconds):
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def write_tier(output, name, tier, blurb, observed):
    """Render one tier in the reader-facing transcript format."""
    views = [row["views"] for row in tier]
    contents = [
        f"# {name} tier: TikTok “In My World / In This Town” videos ({len(tier)})",
        "",
        blurb,
        "",
        f"Views in this tier: {fmt(min(views, default=None))} to {fmt(max(views, default=None))}. All posts are Roblox-tagged, have English speech and were at least {MIN_AGE} days old when observed ({observed}). "
        "Metrics are TikTok's public counts at that moment, collected through Apify. Transcripts are TikTok's own automatic speech-recognition subtitles. "
        "They are machine-made and unchecked, so slang, names and on-screen-only text may be wrong or missing. "
        "Rates are per 100 views. Follower counts are the creator's at observation, so big accounts start with an advantage.",
        "",
    ]
    for n, row in enumerate(tier, 1):
        lines = json.loads(row["transcript"])
        contents += [
            f"## {name}-{n:02d} · @{row['creator']} · {fmt(row['views'])} views",
            "",
            f"- URL: {row['url']}",
            f"- Posted {(row['posted_at_utc'] or '')[:10]} · {row['age_days']:.0f} days old ({row['age_band']}) · {row['duration_s']} s · creator followers {fmt(row['creator_followers']) if row['creator_followers'] else '0 as returned (probably missing)'}",
            f"- Likes {fmt(row['likes'])} ({row['like_rate_pct']}%) · comments {fmt(row['comments'])} ({row['comment_rate_pct']}%) · shares {fmt(row['shares'])} ({row['share_rate_pct']}%) · saves {fmt(row['saves'])} ({row['save_rate_pct']}%) · ~{fmt(row['views_per_day'])} views/day",
            f"- Roblox-tagged: {'yes' if row['roblox'] == 'True' else 'no'} · sound: {row['sound'] or '—'}{' (original)' if row['sound_original'] == 'True' else ''}",
            f"- Caption: {row['caption'].strip() or '—'}",
            "",
            "Transcript:",
            "",
        ]
        contents += [f"[{ts(s)}] {t}" for s, t in lines] + [""]
    (output / f"{name}-50.md").write_text("\n".join(contents), encoding="utf-8")


def other_sections(top_floor, mid_lo, mid_hi, flop_ceiling):
    """Describe why posts were left outside the three tiers."""
    return {
        "A": (
            "NEW-UNDER-5-DAYS",
            "Too new to judge: under 5 days old",
            "Posted in the 5 days before collection, so their numbers are still moving. Use them to see what is being made right now and how posts do in their first hours and days, not as winners or flops. Grouped by age.",
        ),
        "B": (
            "NOT-ROBLOX",
            "Same format, not Roblox",
            'Captioned or tagged "in my world / this town" but not Roblox-tagged: other animation styles, live action, and different memes that share the phrase (for example "in my world everyone\'s a pony"). Useful to see which parts of the formula travel outside Roblox.',
        ),
        "C": (
            "NO-SPEECH",
            "Little or no speech",
            "No usable spoken transcript: music-only, text-on-screen stories, very short clips, or compilations too long to transcribe here. The caption is the main clue to what they are.",
        ),
        "D": (
            "NOT-ENGLISH",
            "Not English",
            "Spoken in another language. Transcripts are kept in the original language.",
        ),
        "E": (
            "CREATOR-CAP",
            "Would qualify, but the creator is already used 4 times",
            f"Each tier allows at most 4 posts per creator so one channel can't dominate. These posts' views fall inside a tier's range (FLOP up to {fmt(flop_ceiling)}, MID {fmt(mid_lo)} to {fmt(mid_hi)}, TOP {fmt(top_floor)} and up) but their creator was already used. Good for checking one creator's consistency.",
        ),
        "F": (
            "BETWEEN-TIERS",
            "Eligible, but between the tiers",
            f"Old enough, Roblox, English speech, but their views fall in the gaps: between FLOP ({fmt(flop_ceiling)} and below) and MID ({fmt(mid_lo)} and above), or between MID ({fmt(mid_hi)}) and TOP ({fmt(top_floor)}). Useful for checking a formula on the in-between cases.",
        ),
    }


def format_age(age):
    return f"{age:.1f}" if age is not None else "—"


def premise(row):
    cap = re.sub(r"#\S+", "", row["caption"] or "").strip(" .…-|")
    first = (json.loads(row["transcript"]) or [[0, ""]])[0][1]
    s = cap if len(cap) >= 12 else first or cap or "—"
    return (s[:110] + "…" if len(s) > 110 else s).replace("|", "/")


def subband(a):
    a = 0 if a is None else a
    return (
        "Under 1 day old"
        if a < 1
        else "1 to 3 days old"
        if a < 3
        else "3 to 5 days old"
    )


def entry(row, label):
    lines = json.loads(row["transcript"])
    note = (
        " (not transcribed: over 10 minutes)"
        if not lines and (row["duration_s"] or 0) > 600
        else ""
    )
    lines_md = [
        f"## {label} · @{row['creator']} · {fmt(row['views'])} views",
        "",
        f"- What it is: {premise(row)}",
        f"- Why it isn't in a tier: {row['untiered_reason'][3:]}",
        f"- Age: {format_age(row['age_days'])} days (posted {(row['posted_at_utc'] or '')[:10]}) · length {row['duration_s']} s · creator followers {fmt(row['creator_followers']) if row['creator_followers'] else '0 as returned (probably missing)'}",
        f"- Likes {fmt(row['likes'])} ({row['like_rate_pct']}%) · comments {fmt(row['comments'])} ({row['comment_rate_pct']}%) · shares {fmt(row['shares'])} ({row['share_rate_pct']}%) · saves {fmt(row['saves'])} ({row['save_rate_pct']}%) · ~{fmt(row['views_per_day'])} views/day",
        f"- Roblox-tagged: {'yes' if row['roblox'] == 'True' else 'no'} · language: {row['language'] or '—'} · transcript: {row['transcript_source'] or 'none' + note} · sound: {row['sound'] or '—'}",
        f"- Link: {row['url']}",
        f"- Caption: {row['caption'].strip() or '—'}",
        "",
    ]
    lines_md += (
        ["Transcript:", ""] + [f"[{ts(s)}] {t}" for s, t in lines]
        if lines
        else ["Transcript: none."]
    ) + [""]
    return lines_md


def reason(row, ranges):
    """Return the existing first applicable untiered reason."""
    if row["age_days"] is None or row["age_days"] < MIN_AGE:
        return "A"
    if row["roblox"] != "True":
        return "B"
    if (row["transcript_words"] or 0) < MIN_WORDS:
        return "C"
    if not english_speech(row):
        return "D"
    if eligible(row) and any(low <= row["views"] <= high for low, high in ranges):
        return "E"
    return "F"


def write_other(output, rows, tiers, observed):
    """Index and write the untiered posts, retaining the original section order."""
    top, mid, flop = tiers["TOP"], tiers["MID"], tiers["FLOP"]
    top_floor = top[-1]["views"] if top else None
    flop_ceiling = flop[-1]["views"] if flop else None
    mid_lo = mid[-1]["views"] if mid else None
    mid_hi = mid[0]["views"] if mid else None
    ranges = []
    if top:
        ranges.append((top_floor, math.inf))
    if mid:
        ranges.append((mid_lo, mid_hi))
    if flop:
        ranges.append((0, flop_ceiling))
    sections = other_sections(top_floor, mid_lo, mid_hi, flop_ceiling)
    grouped = {key: [] for key in sections}
    for row in rows:
        row["untiered_reason"] = ""
        if not row["tier"]:
            key = reason(row, ranges)
            row["untiered_reason"] = f"{key}. {sections[key][1]}"
            grouped[key].append(row)

    for old in (
        output / f"OTHER-{key}-{slug}.md"
        for key, (slug, _, _) in sections.items()
        if not grouped[key]
    ):
        old.unlink(missing_ok=True)
    count = sum(len(group) for group in grouped.values())
    index = [
        "# Other posts: index",
        "",
        f"Everything collected ({observed}) that isn't in TOP-50, MID-50 or FLOP-50: {count} posts, split by why they aren't in a tier. "
        "Each file starts with a table of contents (one line per post: what it is, age, views, length), then every post with its link, metrics and full transcript. "
        "'What it is' comes from the caption or, if that's empty, the opening line; the visuals were not reviewed. "
        "Transcripts are TikTok's automatic subtitles or, where TikTok had none, local Whisper (labelled on each post). Both are machine-made and unchecked.",
        "",
        "| File | Posts | What's in it |",
        "|---|---|---|",
    ]
    for key, (slug, title, blurb) in sections.items():
        group = sorted(grouped[key], key=lambda row: -(row["views"] or 0))
        if not group:
            continue
        filename = f"OTHER-{key}-{slug}.md"
        index.append(
            f"| {chr(96)}{filename}{chr(96)} | {len(group)} | {title}. {blurb.split('. ')[0]}. |"
        )
        bands = (
            ["Under 1 day old", "1 to 3 days old", "3 to 5 days old"]
            if key == "A"
            else [""]
        )
        contents = [
            f"# {key}. {title} ({len(group)} posts)",
            "",
            blurb,
            "",
            "Views are TikTok's public counts at collection. Sorted by views within each group.",
            "",
            "## Contents",
            "",
        ]
        body = []
        number = 0
        for band in bands:
            selected = [
                row for row in group if not band or subband(row["age_days"]) == band
            ]
            if not selected:
                continue
            if band:
                contents.extend([f"### {band} ({len(selected)})", ""])
                body.extend([f"# {band}", ""])
            contents.extend(
                [
                    "| ID | Creator | What it is | Age (d) | Views | Length (s) |",
                    "|---|---|---|---|---|---|",
                ]
            )
            for row in selected:
                number += 1
                label = f"{key}-{number:03d}"
                contents.append(
                    f"| {label} | @{row['creator']} | {premise(row)} | {format_age(row['age_days'])} | "
                    f"{fmt(row['views'])} | {row['duration_s']} |"
                )
                body.extend(entry(row, label))
            contents.append("")
        (output / filename).write_text(
            "\n".join(contents + ["---", ""] + body), encoding="utf-8"
        )
    (output / "OTHER-00-INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")


def build(pool, output):
    """Write the tier packs, untiered index and complete CSV."""
    rows = [normalise(row) for row in read_csv(pool)]
    tiers, median = select_tiers(rows)
    days = sorted(
        {row["observed_at_utc"][:10] for row in rows if row["observed_at_utc"]}
    )
    if days == ["2026-11-26"]:
        observed = "26 Nov 2026 UTC"
    else:
        observed = (
            " to ".join(dict.fromkeys(days[:1] + days[-1:])) + " UTC"
            if days
            else "observation date unavailable"
        )
    blurbs = {
        "TOP": "The most-viewed eligible posts in the collected pool.",
        "MID": f"The eligible posts closest to the pool's median view count ({fmt(median)}), on a log scale.",
        "FLOP": "The least-viewed eligible posts: old enough to have had their chance, with real speech, and still little reach.",
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, tier in tiers.items():
        for row in tier:
            row["tier"] = name
        write_tier(output, name, tier, blurbs[name], observed)
    write_other(output, rows, tiers, observed)
    with (output / "ALL-POSTS.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows, key=lambda row: -(row["views"] or 0)):
            writer.writerow(
                {
                    **row,
                    "transcript_text": " ".join(
                        text for _, text in json.loads(row["transcript"])
                    ),
                }
            )
    print(
        f"{len(rows)} posts | {sum(eligible(row) for row in rows)} eligible | median views {fmt(median)}"
    )
    print(" | ".join(f"{name}: {len(tier)}" for name, tier in tiers.items()))


def main(argv=None):
    """Build the transcript bank and copy it to Downloads by default."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, default=DATA_DIR / "pool.csv")
    parser.add_argument("--out", type=Path, default=PILOT_EXPORT)
    parser.add_argument(
        "--no-downloads",
        action="store_true",
        help="write only the requested output directory",
    )
    args = parser.parse_args(argv)
    build(args.pool, args.out)
    if not args.no_downloads:
        downloads = Path.home() / "Downloads" / args.out.name
        shutil.copytree(args.out, downloads, dirs_exist_ok=True)
        (downloads / "OTHER-POSTS.md").unlink(missing_ok=True)
        print(f"copied to {downloads}")


if __name__ == "__main__":
    main()
