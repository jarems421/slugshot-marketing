r"""Bridge Roblox-native takes into the marketing toolkit.

  python roblox-native/tools/take.py compare <take1.json> <take2.json>
      repeatability: cut-time and cue-time differences, camera pose differences at matching times
  python roblox-native/tools/take.py import <take.json> <video.mp4> [--capture-manifest manifest.json]
      trims the recording to the take's start..end markers and runs `ss import` (media/raw/ naming),
      then writes media/raw/<name>.take.json (truth classification + markers) beside the footage

  python roblox-native/tools/take.py film <take.json> <video.mp4> [more.mp4 ...] [--out file.mp4]
      a Scene.film take (frame-stepped, index-stamped) -> exact 30 fps upright 1080x1920 from native pixels

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


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True).stdout
    w, h = out.strip().split(",")[:2]
    return int(w), int(h)


def ranges(ids):
    """[1, 2, 3, 7] -> "1-3, 7" (for Scene.film patch passes)."""
    out, start = [], None
    for i, n in enumerate(ids):
        if start is None:
            start = n
        if i == len(ids) - 1 or ids[i + 1] != n + 1:
            out.append(f"{start}-{n}" if n != start else f"{n}")
            start = None
    return ", ".join(out)


def calibrate(video):
    """(x, y, w, h) of the viewport in a recording: the bounding box of the magenta calibration card Scene.film shows
    first, found on a quarter-size pass and refined on that frame at full size; the whole frame if there is none."""
    import numpy as np
    w, h = probe(video)
    qw, qh = w // 4, h // 4
    # passthrough: window recordings are variable frame rate; without it the rawvideo output duplicates frames and
    # n no longer matches select's decoded-frame number.
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-fps_mode", "passthrough", "-frames:v", "900",
                            "-vf", f"scale={qw}:{qh}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    found, n = None, 0
    while True:
        buf = dec.stdout.read(qw * qh * 3)
        if len(buf) < qw * qh * 3:
            break
        img = np.frombuffer(buf, np.uint8).reshape(qh, qw, 3).astype(int)
        mask = (img[..., 0] > 200) & (img[..., 1] < 70) & (img[..., 2] > 200)
        if mask.mean() > 0.25:
            found = n
            break
        n += 1
    dec.kill()
    dec.stdout.close()
    dec.wait()
    if found is None:
        return 0, 0, w, h
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-fps_mode", "passthrough",
                          "-vf", f"select=eq(n\\,{found})", "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    img = np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(int)
    mask = (img[..., 0] > 200) & (img[..., 1] < 70) & (img[..., 2] > 200)
    ys, xs = np.nonzero(mask)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    return x0, y0, (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2


def film(take_path, videos, out, crf):
    """Film-mode recordings (Scene.film) -> exact 30 fps, upright 1080x1920 footage from native pixels.

    Every recorded frame carries its scene frame index in a stamp of squares down the left edge (two
    references, then the bits). Pass 1 reads only that strip from every recording; for each index the middle
    frame of its longest run, in any recording, is chosen. Pass 2 decodes the chosen frames and encodes once.
    Studio's recorder caps at 30 s and stalls now and then, so a long scene is filmed in chunks and any missed
    range is re-filmed (Scene.film with first/last) and passed here as another recording; later
    recordings only fill indices the earlier ones lack, so a patch recording may hold other takes' patches. Missing indices
    repeat the previous frame and are listed as ranges to re-film."""
    import numpy as np
    take = load(take_path)
    st, (vw, vh) = take["stamp"], take["viewport"]
    frames = take["frames"]
    # Each recording's viewport rectangle: the magenta calibration card (window recordings from tools/rec.py), or
    # the whole frame (Studio's own recorder captures only the viewport).
    geoms = [calibrate(v) for v in videos]
    gw, gh = geoms[0][2], geoms[0][3]
    for v, g in zip(videos, geoms):
        if abs(g[2] - gw) > 4 or abs(g[3] - gh) > 4:
            raise SystemExit(f"{v}: viewport {g[2]}x{g[3]} differs from the first recording's {gw}x{gh}")
    geoms = [(x, y, gw, gh) for x, y, _, _ in geoms]
    w, h = gw, gh
    sx, sy = w / vw, h / vh
    strip_w = (int((st["x"] + st["size"]) * sx) + 7) // 2 * 2  # even: FFmpeg rounds odd crop widths
    centres = [(round((st["x"] + st["size"] / 2) * sx), round((st["y"] + k * (st["size"] + st["gap"]) + st["size"] / 2) * sy))
               for k in range(st["bits"] + 2)]
    r = 3

    def index(img):
        luma = [float(img[y - r:y + r + 1, x - r:x + r + 1].mean()) for x, y in centres]
        white, black = luma[0], luma[1]
        if white - black < 120:
            return None
        cut = (white + black) / 2
        return sum(1 << b for b, v in enumerate(luma[2:]) if v > cut)

    # Pass 1: stamps only (a narrow grey strip decodes fast).
    best = {}  # index -> (run length, video number, frame number)
    total = 0
    filled = set()  # indices the earlier recordings already had: later ones (patch passes) only fill gaps

    def keep(idx, run, vi):
        if idx is None or idx >= frames or (vi > 0 and idx in filled):
            return False
        return len(run) > best.get(idx, (0,))[0]

    for vi, video in enumerate(videos):
        x0, y0 = geoms[vi][0], geoms[vi][1]
        dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-fps_mode", "passthrough",
                                "-vf", f"crop={strip_w}:{h}:{x0}:{y0}",
                                "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
        n, run_idx, run = 0, None, []
        while True:
            buf = dec.stdout.read(strip_w * h)
            if len(buf) < strip_w * h:
                break
            idx = index(np.frombuffer(buf, np.uint8).reshape(h, strip_w))
            if idx != run_idx:
                if keep(run_idx, run, vi):
                    best[run_idx] = (len(run), vi, run[len(run) // 2])
                run_idx, run = idx, []
            run.append(n)
            n += 1
        if keep(run_idx, run, vi):
            best[run_idx] = (len(run), vi, run[len(run) // 2])
        dec.wait()
        filled = set(best)
        total += n

    missing = [i for i in range(frames) if i not in best]
    if not best:
        raise SystemExit("no stamped frames found: was the frame stamp hidden?")

    # Pass 2: walk every recording forward once, writing the chosen frame for each index in order.
    portrait = take.get("portrait", True)
    cw = (round(h * 16 / 9) // 2) * 2
    vf = (f"crop={cw}:{h}:{(w - cw) // 2}:0,transpose=2,scale=1080:1920:flags=lanczos" if portrait
          else f"crop={(round(h * 9 / 16) // 2) * 2}:{h},scale=1080:1920:flags=lanczos")
    out.parent.mkdir(parents=True, exist_ok=True)
    readers = [{"proc": subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(v), "-fps_mode", "passthrough",
                                          "-vf", f"crop={w}:{h}:{g[0]}:{g[1]}",
                                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                         stdout=subprocess.PIPE), "at": -1, "buf": None} for v, g in zip(videos, geoms)]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                            "-r", str(take.get("fps", 30)), "-i", "-", "-vf", vf, "-c:v", "libx264", "-preset", "slow",
                            "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                           stdin=subprocess.PIPE)
    size, last = w * h * 3, None
    for i in range(frames):
        if i in best:
            _, vi, fn = best[i]
            rd = readers[vi]
            while rd["at"] < fn:
                rd["buf"] = rd["proc"].stdout.read(size)
                rd["at"] += 1
            last = rd["buf"]
        if last is None:  # leading frames missing: use the first chosen frame
            _, vi, fn = best[min(best)]
            rd = readers[vi]
            while rd["at"] < fn:
                rd["buf"] = rd["proc"].stdout.read(size)
                rd["at"] += 1
            last = rd["buf"]
        enc.stdin.write(last)
    enc.stdin.close()
    enc.wait()
    for rd in readers:
        rd["proc"].stdout.close()
        rd["proc"].kill()
    print(f"{out}: {frames} frames from {total} recorded in {len(videos)} recording(s); repeated {len(missing)}")
    if missing:
        print(f"  re-film: {ranges(missing)}  (Scene.film with {{first = A, last = B}}, then pass all recordings)")
    return 0 if not missing else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("film", help="decode a film-mode take into exact 30 fps vertical footage")
    f.add_argument("take")
    f.add_argument("video", nargs="+", help="one or more recordings of this take (chunks, patch passes)")
    f.add_argument("--out", help="default out/takes/<take>.mp4")
    f.add_argument("--crf", type=int, default=14)
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
    if a.cmd == "film":
        t = load(a.take)
        sys.exit(film(a.take, [Path(v) for v in a.video], Path(a.out) if a.out else ROOT / "out" / "takes" / f"{t['take']}.mp4", a.crf))
    do_import(a.take, a.video, a.capture_manifest, a.video_start_ms)


if __name__ == "__main__":
    main()
