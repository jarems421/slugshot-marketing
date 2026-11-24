r"""Bridge Roblox-native takes into the marketing toolkit.

  python roblox-native/tools/take.py compare <take1.json> <take2.json>
      repeatability: cut-time and cue-time differences, camera pose differences at matching times
  python roblox-native/tools/take.py import <take.json> <video.mp4> [--capture-manifest manifest.json]
      trims the recording to the take's start..end markers and runs `ss import` (media/raw/ naming),
      then writes media/raw/<name>.take.json (truth classification + markers) beside the footage

Clock: Reel marker `at` and Studio video_capture's creation_timestamp_ms are both Unix ms on this
machine. For an OBS recording, pass --video-start-ms (when OBS started recording), or trim by hand.
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PY = sys.executable


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def compare(a, b):
    ta, tb = load(a), load(b)
    cuts = lambda t: [m["elapsed"] for m in t["marks"] if m["kind"] in ("cut", "end")]
    ca, cb = cuts(ta), cuts(tb)
    print(f"takes {ta['take']} vs {tb['take']} ({ta['scene']})")
    if len(ca) != len(cb):
        print(f"FAIL different number of cuts: {len(ca)} vs {len(cb)}")
        return 1
    worst_cut = max(abs(x - y) for x, y in zip(ca, cb))
    cues = lambda t: [(c["name"], c["elapsed"]) for c in t["cues"]]
    qa, qb = cues(ta), cues(tb)
    same_cues = [n for n, _ in qa] == [n for n, _ in qb]
    worst_cue = max((abs(x[1] - y[1]) for x, y in zip(qa, qb)), default=0)
    # Camera poses where both takes sampled within 20 ms of each other (Reel shots are pure functions of time).
    pairs, d_pos, d_ang = 0, 0.0, 0.0
    for sa in ta["camera"]:
        for sb in tb["camera"]:
            if sa["t"] > 0 and sa["t"] == sb["t"] and abs(sa["elapsed"] - sb["elapsed"]) < 0.02:
                pairs += 1
                d_pos = max(d_pos, math.dist(sa["pos"], sb["pos"]))
                dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(sa["look"], sb["look"]))))
                d_ang = max(d_ang, math.degrees(math.acos(dot)))
    ok = same_cues and worst_cut < 0.05 and worst_cue < 0.05 and pairs > 0 and d_pos < 0.05 and d_ang < 0.5
    print(f"cuts {len(ca)}: worst difference {worst_cut * 1000:.0f} ms")
    print(f"cues {'same order' if same_cues else 'DIFFERENT'}: worst difference {worst_cue * 1000:.0f} ms")
    print(f"camera: {pairs} matched samples, worst {d_pos:.3f} studs / {d_ang:.2f} degrees")
    print("PASS repeatable" if ok else "FAIL not repeatable within 50 ms / 0.05 studs / 0.5 degrees")
    return 0 if ok else 1


def do_import(take_path, video, capture_manifest, video_start_ms):
    take = load(take_path)
    marks = {m["kind"]: m["at"] for m in take["marks"]}
    if capture_manifest:
        video_start_ms = load(capture_manifest)["creation_timestamp_ms"]
    if video_start_ms is None:
        raise SystemExit("need --capture-manifest (Studio video_capture) or --video-start-ms (OBS)")
    start = max(0.0, (marks["start"] - video_start_ms) / 1000)
    # Stop one frame before the end marker: by then Reel has given the camera and HUD back.
    end = (marks.get("end", take["ended_ms"]) - video_start_ms) / 1000 - 1 / 30
    trimmed = ROOT / "out" / f"{take['take']}.mp4"
    trimmed.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                    "-i", str(video), "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "aac", str(trimmed)],
                   check=True)
    fmt = {"staged_fiction": "STAGED", "staged_gameplay": "STAGEDPLAY", "hybrid_bridge": "HYBRID"}.get(
        take["truth"]["mode"], "ROBLOX")
    concept = "".join(w.title() for w in take["scene"].split("_"))
    r = subprocess.run([PY, str(ROOT / "scripts" / "import_capture.py"), str(trimmed), "--format", fmt,
                        "--concept", concept, "--hook", "Take", "--note",
                        f"roblox-native take {take['take']} ({take['truth']['mode']}; {take['truth'].get('label', '')})"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        raise SystemExit(r.stderr)
    raw = Path(r.stdout.strip().split(" (")[0])
    side = raw.with_suffix(".take.json")
    shutil.copyfile(take_path, side)
    print(f"{raw}  (trimmed {start:.3f}-{end:.3f}s of the recording; take manifest {side.name})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    i = sub.add_parser("import")
    i.add_argument("take")
    i.add_argument("video")
    i.add_argument("--capture-manifest")
    i.add_argument("--video-start-ms", type=float)
    a = ap.parse_args()
    if a.cmd == "compare":
        sys.exit(compare(a.a, a.b))
    do_import(a.take, a.video, a.capture_manifest, a.video_start_ms)


if __name__ == "__main__":
    main()
