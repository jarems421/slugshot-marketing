"""Copy a recording (e.g. from OBS) into media/raw/ under the campaign naming convention.

  SS_YYYYMMDD_FORMAT_CONCEPT_HOOK_V01_RAW.ext   (date = today unless --date)

The source is copied, never moved or changed. Each import is logged to media/capture_log.csv
with the original path, size and duration so footage can be traced back later.
"""
import argparse
import csv
import json
import re
import shutil
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "media" / "raw"
LOG = ROOT / "media" / "capture_log.csv"


def part(s):
    return re.sub(r"[^A-Za-z0-9]", "", s.title()) if " " in s else re.sub(r"[^A-Za-z0-9]", "", s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--format", required=True, help="PVP, WORLD, SKIT, TREND, PROMO, CHOICE ...")
    ap.add_argument("--concept", required=True, help="e.g. FloppyUnderdog")
    ap.add_argument("--hook", default="Raw", help="e.g. BestSlug")
    ap.add_argument("--date", default=date.today().strftime("%Y%m%d"))
    ap.add_argument("--note", default="", help="build/commit filmed, who played, anything to remember")
    args = ap.parse_args()

    src = Path(args.source)
    RAW.mkdir(parents=True, exist_ok=True)
    base = f"SS_{args.date}_{args.format.upper()}_{part(args.concept)}_{part(args.hook)}"
    v = 1
    while (dest := RAW / f"{base}_V{v:02}_RAW{src.suffix.lower()}").exists():
        v += 1
    shutil.copy2(src, dest)

    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height",
                            "-of", "json", str(dest)], capture_output=True, text=True)
    info = json.loads(probe.stdout or "{}")
    vs = next((s for s in info.get("streams", []) if "width" in s), {})
    row = {"imported_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "file": dest.name, "source_path": str(src.resolve()), "bytes": dest.stat().st_size,
           "duration_s": round(float(info.get("format", {}).get("duration", 0)), 2) or "",
           "resolution": f"{vs.get('width')}x{vs.get('height')}" if vs else "", "note": args.note}
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"{dest} ({row['duration_s']}s {row['resolution']})")


if __name__ == "__main__":
    main()
