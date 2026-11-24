"""Check the hand-entered platform metrics and write a shareable copy for ChatGPT.

Input:  data/local/platform_metrics.csv (start from data/templates/platform_metrics_template.csv;
        one row per upload per observation, copied from TikTok/Instagram/YouTube Studio analytics)
Output: exports/share/platform_metrics_YYYYMMDD.csv with hours_since_post added. Problems are listed;
        rows with problems are still exported, flagged. Your own numbers typed in from the platforms'
        analytics are fine to share; YouTube Data API reports are not included (internal only).
"""
import csv
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "local" / "platform_metrics.csv"
TEMPLATE = ROOT / "data" / "templates" / "platform_metrics_template.csv"
PLATFORMS = {"tiktok", "youtube", "instagram"}
NUMERIC = ["views", "likes", "comments", "shares", "saves", "profile_visits", "link_new_players", "production_minutes"]


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def main():
    if not SRC.exists():
        SRC.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TEMPLATE, SRC)
        sys.exit(f"Created {SRC} from the template. Fill it in (keep unknown values blank) and run again.")

    with SRC.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        expected = TEMPLATE.read_text(encoding="utf-8").splitlines()[0].split(",")
        missing = [c for c in expected if c not in (reader.fieldnames or [])]
        if missing:
            sys.exit(f"{SRC} is missing columns: {', '.join(missing)}")
        rows = [r for r in reader if r.get("experiment_id") and not r["experiment_id"].startswith("EXAMPLE")]

    problems = []
    for n, r in enumerate(rows, 2):
        issues = []
        if r["platform"].strip().lower() not in PLATFORMS:
            issues.append(f"platform '{r['platform']}'")
        for c in NUMERIC:
            v = r[c].replace(",", "").strip()
            if v and not v.isdigit():
                issues.append(f"{c} '{r[c]}' is not a whole number")
            r[c] = v
        if r["watch_metric_value"] and not r["watch_metric_name"]:
            issues.append("watch_metric_value without watch_metric_name")
        try:
            posted, observed = parse_time(r["posted_at_utc"]), parse_time(r["observed_at_utc"])
            r["hours_since_post"] = round((observed - posted).total_seconds() / 3600, 1) if posted and observed else ""
        except ValueError:
            issues.append("dates must look like 2026-11-25T17:00:00Z")
            r["hours_since_post"] = ""
        r["check"] = "; ".join(issues)
        if issues:
            problems.append(f"row {n}: {r['check']}")

    out_dir = ROOT / "exports" / "share"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out = out_dir / f"platform_metrics_{stamp}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, expected + ["hours_since_post", "check"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {out}")
    for p in problems:
        print("CHECK", p)


if __name__ == "__main__":
    main()
