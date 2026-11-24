r"""Cut Gemini's candidate moments out of a long recording so a person can check them quickly.

  .\ss candidates media\raw\SS_..._RAW.mkv media\raw\SS_..._RAW.gemini.csv [--pad 5]

The CSV needs `start` and `end` columns (seconds, M:SS, or H:MM:SS, decimals allowed); every other
column Gemini gives (what_happens, format, hook_idea, confidence, ...) is copied to the index.
Each moment is cut with --pad seconds either side (the research says to watch 5 s before and after,
because Gemini's timestamps can be off), the original timecode is burned in, and
media\candidates\<recording>\index.csv lists every clip with blank `verified`/`keep`/`true_start`/
`true_end` columns for the human scrub. Nothing is selected automatically.
"""
import argparse
import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT = "C\\:/Windows/Fonts/arialbd.ttf"


def seconds(t):
    parts = [float(p) for p in str(t).strip().split(":")]
    total = 0.0
    for p in parts:
        total = total * 60 + p
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("csv")
    ap.add_argument("--pad", type=float, default=5)
    a = ap.parse_args()
    video = Path(a.video)
    length = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                   str(video)], capture_output=True, text=True, check=True).stdout)
    with open(a.csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows or not {"start", "end"} <= set(rows[0]):
        raise SystemExit("The CSV needs 'start' and 'end' columns (see docs/flow-and-gemini.md).")
    out_dir = ROOT / "media" / "candidates" / video.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for i, r in enumerate(rows, 1):
        s, e = seconds(r["start"]), seconds(r["end"])
        if e <= s or s >= length:
            print(f"skip row {i}: start {r['start']} / end {r['end']} not inside the {length:.0f}s recording")
            continue
        cs, ce = max(0.0, s - a.pad), min(length, e + a.pad)
        out = out_dir / f"{i:02d}_{int(s // 60)}m{s % 60:04.1f}s.mp4"
        # Burned-in source timecode, plus a marker while inside Gemini's own start-end range.
        vf = (f"drawtext=fontfile='{FONT}':text='%{{pts\\:hms\\:{cs}}}':x=30:y=30:fontsize=42:fontcolor=white:"
              f"box=1:boxcolor=black@0.6:boxborderw=8,"
              f"drawtext=fontfile='{FONT}':text='GEMINI MOMENT':x=30:y=90:fontsize=36:fontcolor=yellow:"
              f"box=1:boxcolor=black@0.6:boxborderw=8:enable='between(t,{s - cs},{e - cs})'")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{cs:.3f}", "-to", f"{ce:.3f}",
                        "-i", str(video), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                        "-c:a", "aac", str(out)], check=True)
        index.append({"clip": out.name, "gemini_start": r["start"], "gemini_end": r["end"],
                      "clip_covers": f"{cs:.1f}-{ce:.1f}s", **{k: v for k, v in r.items() if k not in ("start", "end")},
                      "verified": "", "keep": "", "true_start": "", "true_end": "", "notes": ""})
        print(f"{out.name}  ({cs:.1f}-{ce:.1f}s)")
    if index:
        with (out_dir / "index.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(index[0]))
            w.writeheader()
            w.writerows(index)
        print(f"{len(index)} clips -> {out_dir}  (fill in verified/keep/true_start/true_end in index.csv)")


if __name__ == "__main__":
    main()
