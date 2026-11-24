r"""Frame sheet for reviewing an edit: one frame every --every seconds, numbered with its time.

  .\ss sheet exports\SS_..._MASTER.mp4 [--every 1] [--width 216]

Writes <video>.sheet.jpg next to the video (git-ignored with the video). Claude reads it to check
hook, hierarchy, text on the action and payoff; a person still watches the video itself.
"""
import argparse
import math
import subprocess
from pathlib import Path

FONT = "C\\:/Windows/Fonts/arialbd.ttf"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--every", type=float, default=1.0)
    ap.add_argument("--width", type=int, default=216)
    a = ap.parse_args()
    video = Path(a.video)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(video)], capture_output=True, text=True, check=True).stdout)
    n = max(1, math.ceil(dur / a.every))
    cols = min(n, 8)
    rows = math.ceil(n / cols)
    out = video.with_suffix(".sheet.jpg")
    vf = (f"fps=1/{a.every},scale={a.width}:-2,"
          f"drawtext=fontfile='{FONT}':text='%{{pts\\:hms}}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,"
          f"tile={cols}x{rows}:padding=4:color=gray")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-vf", vf,
                    "-frames:v", "1", "-q:v", "3", str(out)], check=True)
    print(f"{out} ({n} frames, every {a.every}s)")


if __name__ == "__main__":
    main()
