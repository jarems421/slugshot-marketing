r"""Render several variants from one set of assets, named and logged for experiments.

  .\ss batch jobs\floppy-underdog.json [--only BestSlug] [--test]

Job file (JSON):
  {
    "concept": "FloppyUnderdog",          one word, used in file names
    "clip": "media/raw/....mkv",           shared footage (under media/)
    "narration": "media/vo/vo.wav",        optional, shared
    "captions": "media/vo/vo.srt",         optional, shared (checked by hand)
    "variants": [
      {"format": "PVP",    "hook_id": "BestSlug",   "hook": "He brought Inferno. I brought Floppy."},
      {"format": "PROMO",  "hook_id": "DirectPitch", "hook": "This Roblox game shoots slugs"},
      {"format": "CHOICE", "hook_id": "PickOne",    "hook": "Inferno or Floppy?", "accent": "#7cff9b"}
    ]
  }
Any per-variant key other than format/hook_id/hook is a template override (fit, accent, label,
clipVolume, endCard, endCardTitle, endCardSubtitle, narration, captions, clip).

Each variant -> exports\SS_<date>_<FORMAT>_<concept>_<hook_id>_Vnn_MASTER.mp4 (+ .qc.json), and a
row in exports\share\variants_log.csv (ready to copy into the platform metrics sheet).
"""
import argparse
import csv
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import render

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "exports" / "share" / "variants_log.csv"
LOG_FIELDS = ["rendered_at_utc", "edit_file", "format", "concept", "hook_id", "hook", "clip", "narration",
              "captions", "duration_s", "qc", "qc_issues", "experiment_id"]


def next_name(day, fmt, concept, hook_id):
    base = f"SS_{day}_{fmt.upper()}_{concept}_{hook_id}"
    v = 1
    while (ROOT / "exports" / f"{base}_V{v:02}_MASTER.mp4").exists():
        v += 1
    return f"{base}_V{v:02}_MASTER"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job_file")
    ap.add_argument("--only", help="render just this hook_id")
    ap.add_argument("--test", action="store_true", help="mark renders as non-production for Remotion")
    a = ap.parse_args()
    spec = json.loads(Path(a.job_file).read_text(encoding="utf-8"))
    day = date.today().strftime("%Y%m%d")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    new_log = not LOG.exists()
    worst = "PASS"
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, LOG_FIELDS)
        if new_log:
            w.writeheader()
        for var in spec["variants"]:
            if a.only and var["hook_id"] != a.only:
                continue
            var = dict(var)
            fmt, hook_id, hook = var.pop("format"), var.pop("hook_id"), var.pop("hook", "")
            clip = var.pop("clip", spec["clip"])
            narration = var.pop("narration", spec.get("narration"))
            captions = var.pop("captions", spec.get("captions"))
            name = next_name(day, fmt, spec["concept"], hook_id)
            print(f"rendering {name} ...", flush=True)
            out, overall, results, dur = render.render_one(name, clip, fmt, narration, captions, hook,
                                                           production=not a.test, **var)
            issues = "; ".join(f"{r['check']}: {r['detail']}" for r in results if r["status"] != "PASS")
            print(f"   QC {overall}" + (f" - {issues}" if issues else ""))
            w.writerow({"rendered_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                        "edit_file": out.name, "format": fmt.upper(), "concept": spec["concept"], "hook_id": hook_id,
                        "hook": hook, "clip": clip, "narration": narration or "", "captions": captions or "",
                        "duration_s": round(dur, 1), "qc": overall, "qc_issues": issues, "experiment_id": ""})
            worst = max(worst, overall, key=["PASS", "WARN", "FAIL"].index)
    print(f"log: {LOG}")
    sys.exit(2 if worst == "FAIL" else 0)


if __name__ == "__main__":
    main()
