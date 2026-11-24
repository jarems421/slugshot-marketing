r"""Automated checks for a finished vertical master. PASS / WARN / FAIL per check.

  .\ss qc exports\SS_..._MASTER.mp4 [more files]      (also run automatically after render/vertical)

Checks: 1080x1920, 24-60 fps, H.264 + yuv420p, AAC audio present, length 3-180 s,
loudness -16..-12 LUFS, true peak <= -1 dBTP, near-black runs >= 0.5 s, frozen video >= 3 s (a 2 s end card is fine),
silence >= 1.5 s, first frame not black. A result file goes next to the video (.qc.json)
and a row is added to reports\qc_log.csv. These are technical checks only; still watch
every master on a phone (captions, crop, truth, rights).
"""
import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "reports" / "qc_log.csv"


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate,sample_rate:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def analyse(path, has_audio, duration):
    # Slugshot is set underground, so "black" means near-pure black, not just dark.
    vf = "blackdetect=d=0.5:pix_th=0.04,freezedetect=n=0.003:d=3"
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vf", vf]
    if has_audio:
        cmd += ["-af", "ebur128=peak=true:framelog=quiet,silencedetect=n=-45dB:d=1.5"]
    cmd += ["-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    num = lambda pat: float(m.group(1)) if (m := re.search(pat, err)) else None
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", err)]
    freezes = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", err)]
    if len(starts) > len(freezes):  # a freeze lasting to the end of the file never reports its duration
        freezes.append(round(duration - starts[-1], 2))
    return {
        "black": [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)],
        "freeze": [f for f in freezes if f >= 3],
        "silence": [(float(e) - float(d), float(d)) for e, d in
                    re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", err)],
        "lufs": num(r"Integrated loudness:\s+I:\s+(-?[\d.]+) LUFS"),
        "true_peak": num(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS"),
    }


def check(path):
    info = probe(path)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den or 1)
    an = analyse(path, a is not None, dur)
    results = []

    def add(name, status, detail):
        results.append({"check": name, "status": status, "detail": detail})

    size = (v.get("width"), v.get("height"))
    add("resolution", "PASS" if size == (1080, 1920) else "WARN" if size[1] and size[0] / size[1] == 9 / 16 else "FAIL",
        f"{size[0]}x{size[1]}")
    add("frame rate", "PASS" if 23.9 <= fps <= 60.1 else "WARN", f"{fps:.2f} fps")
    add("video codec", "PASS" if v.get("codec_name") == "h264" and v.get("pix_fmt") == "yuv420p" else "FAIL",
        f"{v.get('codec_name')} {v.get('pix_fmt')}")
    add("audio stream", "PASS" if a and a.get("codec_name") == "aac" else "FAIL",
        f"{a.get('codec_name')} {a.get('sample_rate')} Hz" if a else "no audio")
    add("length", "PASS" if 3 <= dur <= 180 else "WARN", f"{dur:.1f}s (Shorts allow up to 180 s)")
    if a:
        lufs, tp = an["lufs"], an["true_peak"]
        add("loudness", "FAIL" if lufs is None else "PASS" if -16 <= lufs <= -12 else
            "WARN" if -18 <= lufs <= -10 else "FAIL", f"{lufs} LUFS integrated (aim -14)")
        add("true peak", "PASS" if tp is not None and tp <= -1.0 else "WARN", f"{tp} dBTP")
        # A quiet ending (end card) is normal, so silence that runs to the end doesn't count.
        long_sil = [round(d, 1) for start, d in an["silence"] if d >= 1.5 and start + d < dur - 0.25]
        add("silence", "PASS" if not long_sil else "WARN", f"{len(long_sil)} gaps >= 1.5 s before the ending {long_sil[:3]}")
    blacks = an["black"]
    add("black frames", "PASS" if not blacks else "WARN", f"{len(blacks)} runs >= 0.5 s {blacks[:3]}")
    add("starts on picture", "FAIL" if blacks and blacks[0][0] < 0.05 else "PASS",
        "opens on black" if blacks and blacks[0][0] < 0.05 else "first frame has picture")
    add("frozen video", "PASS" if not an["freeze"] else "WARN", f"{len(an['freeze'])} freezes >= 3 s {an['freeze'][:3]}")

    overall = "FAIL" if any(r["status"] == "FAIL" for r in results) else \
        "WARN" if any(r["status"] == "WARN" for r in results) else "PASS"
    return overall, results, dur


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    worst = "PASS"
    LOG.parent.mkdir(exist_ok=True)
    new_log = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(["checked_at_utc", "file", "overall", "warnings_and_failures"])
        for file in a.files:
            path = Path(file)
            overall, results, dur = check(path)
            path.with_suffix(".qc.json").write_text(json.dumps({"file": path.name, "overall": overall,
                                                                "checks": results}, indent=1), encoding="utf-8")
            print(f"{overall:5} {path.name} ({dur:.1f}s)")
            for r in results:
                if r["status"] != "PASS":
                    print(f"   {r['status']:5} {r['check']}: {r['detail']}")
            w.writerow([datetime.now(timezone.utc).replace(microsecond=0).isoformat(), path.name, overall,
                        "; ".join(f"{r['check']}: {r['detail']}" for r in results if r["status"] != "PASS")])
            worst = max(worst, overall, key=["PASS", "WARN", "FAIL"].index)
    sys.exit(2 if worst == "FAIL" else 0)


if __name__ == "__main__":
    main()
