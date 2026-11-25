r"""High-quality recording of the marketing Studio window (Windows Graphics Capture through FFmpeg `gfxcapture`).

  python roblox-native/tools/rec.py start media/takes/<take>.mkv     (blocks; run it in the background)
  python roblox-native/tools/rec.py stop

Why: Studio's own video_capture encodes the viewport at about 6 Mbps (fine detail smears), stops at 30 s and loses
its files when play restarts. This records only the Studio window whose title names SlugshotMarketing (not the
screen: other windows on top are not captured), without the cursor, near-lossless (x264 CRF 8, 4:4:4), for as long
as the take runs. Scene.film shows a magenta calibration card first, so `take.py film` crops to the viewport.
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STOP = ROOT / "capture" / "rec.stop"
TITLE = "SlugshotMarketing.*Roblox Studio"


def start(out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    STOP.parent.mkdir(parents=True, exist_ok=True)
    STOP.unlink(missing_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-filter_complex",
           f"gfxcapture=window_title='{TITLE}':capture_cursor=0:max_framerate=60,hwdownload,format=bgra,format=yuv444p",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "8", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    print(f"recording {out}", flush=True)
    while proc.poll() is None and not STOP.exists():
        time.sleep(0.2)
    if proc.poll() is None:
        proc.stdin.write(b"q")
        proc.stdin.flush()
        proc.wait(timeout=60)
    STOP.unlink(missing_ok=True)
    print(f"stopped {out} (exit {proc.returncode})", flush=True)
    return proc.returncode


def stop():
    STOP.parent.mkdir(parents=True, exist_ok=True)
    STOP.write_text("stop")
    print("stop requested")


if __name__ == "__main__":
    if sys.argv[1:2] == ["start"] and len(sys.argv) > 2:
        sys.exit(start(sys.argv[2]))
    elif sys.argv[1:2] == ["stop"]:
        stop()
    else:
        print(__doc__)
