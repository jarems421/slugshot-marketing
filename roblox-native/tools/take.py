r"""Bridge Roblox-native takes into the marketing toolkit.

  python roblox-native/tools/take.py compare <take1.json> <take2.json>
      repeatability: cut-time and cue-time differences, camera pose differences at matching times
  python roblox-native/tools/take.py import <take.json> <video.mp4> [--capture-manifest manifest.json]
      trims the recording to the take's start..end markers and runs `ss import` (media/raw/ naming),
      then writes media/raw/<name>.take.json (truth classification + markers) beside the footage

  python roblox-native/tools/take.py film <take.json> <video.mp4> [more.mp4 ...] [--out file.mp4]
      a Scene.film take (frame-stepped, index-stamped) -> exact 30 fps upright 1080x1920 from native pixels
  python roblox-native/tools/take.py split <take.json> <take.mp4> <layer_b.mp4> [--out file.mp4]
      composites a take's split shots: its own view on top, the decoded layer "b" pass below a slanted divider
  python roblox-native/tools/take.py warp <take.json> <dialogue.json> [--out-dir DIR]
      a take with slow motion: the dialogue (audio, lines, caption words) with each segment's extra seconds of
      silence inserted, so it lines up with the video (point the edit's "dialogue" at the result)

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
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-fps_mode", "passthrough", "-frames:v", "12000",  # takes may wait minutes for the lobby before the card
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
    if take.get("quality") == "unlocked":
        print("WARNING: filmed at Studio's Automatic quality: passes can be lit differently and flicker when mixed; "
              "start takes from Studio MCP so Scene.film can lock the quality level")
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

    # Pass 1: stamps, and how much detail each recorded copy holds. Roblox streams textures at lower resolution now and
    # then; a frame caught then shows blocky clothing while the rest is sharp (owner, 2026-11-26: "randomly everything
    # goes blurry"). Detail is measured per tile of the picture (edge energy at half size), so a soft patch shows up.
    cw = (round(h * 16 / 9) // 2) * 2 if take.get("portrait", True) else (round(h * 9 / 16) // 2) * 2
    cx0 = (w - cw) // 2
    TX, TY = 6, 4

    hw, hh2 = w // 2, h // 2  # pass 1 reads frames at half size (fast; the stamp squares and tiles survive it)
    half = [(x // 2, y // 2) for x, y in centres]

    def half_index(img):
        luma = [float(img[y - 1:y + 2, x - 1:x + 2].mean()) for x, y in half]
        white, black = luma[0], luma[1]
        if white - black < 120:
            return None
        cut = (white + black) / 2
        return sum(1 << b for b, v in enumerate(luma[2:]) if v > cut)

    def tiles(img):
        a = img[:, cx0 // 2:(cx0 + cw) // 2].astype(np.float32)
        lap = np.abs(a[1:-1, 1:-1] * 4 - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:])
        hh, ww = lap.shape[0] // TY, lap.shape[1] // TX
        edges = lap[:hh * TY, :ww * TX].reshape(TY, hh, TX, ww).mean(axis=(1, 3)).ravel() + 0.05
        # the broad picture of each tile (6x6 blocks): motion changes it, a texture dropping detail doesn't
        th, tw = hh // 6, ww // 6
        broad = a[:th * 6 * TY, :tw * 6 * TX].reshape(TY * 6, th, TX * 6, tw).mean(axis=(1, 3)).astype(np.uint8)
        return edges, broad

    copies = {}  # index -> {video number: [(frame number, tiles)]}
    total = 0
    for vi, video in enumerate(videos):
        x0, y0 = geoms[vi][0], geoms[vi][1]
        dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-fps_mode", "passthrough",
                                "-vf", f"crop={w}:{h}:{x0}:{y0},scale={hw}:{hh2}:flags=area",
                                "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
        n = 0
        while True:
            buf = dec.stdout.read(hw * hh2)
            if len(buf) < hw * hh2:
                break
            img = np.frombuffer(buf, np.uint8).reshape(hh2, hw)
            idx = half_index(img)
            if idx is not None and idx < frames:
                e, b = tiles(img)
                copies.setdefault(idx, {}).setdefault(vi, []).append((n, e, b))
            n += 1
        dec.wait()
        total += n

    def score(t):
        return float(np.log(t).sum())

    # Each index: the sharpest copy in the earliest recording that has it (later recordings fill gaps, as before).
    best, alt, detail, broad, later = {}, {}, {}, {}, {}
    for idx, by in copies.items():
        first = min(by)
        fn, t, bt = max(by[first], key=lambda c: score(c[1]))
        best[idx] = (len(by[first]), first, fn)
        detail[idx], broad[idx] = t, bt.astype(np.float32)
        for vi in sorted(by):
            if vi != first:
                ofn, ot, ob = max(by[vi], key=lambda c: score(c[1]))
                later.setdefault(idx, []).append((vi, ofn, ot, ob))
                if first == 0:
                    alt.setdefault(vi, {})[idx] = ofn

    # Soft frames: a tile with much less detail than the frames either side, which agree with each other, while its
    # broad picture is unchanged (a texture caught at low resolution, not motion).
    def is_soft(i):
        prev = [detail[j] for j in (i - 2, i - 1) if j in detail]
        nxt = [detail[j] for j in (i + 1, i + 2) if j in detail]
        if not prev or not nxt or i - 1 not in broad or i + 1 not in broad:
            return False
        p_, n_ = np.mean(prev, axis=0), np.mean(nxt, axis=0)
        rp, rn, agree = detail[i] / p_, detail[i] / n_, p_ / n_
        bad = (rp < 0.72) & (rn < 0.72) & (agree > 0.8) & (agree < 1.25) & (np.minimum(p_, n_) > 1.0)
        if not bad.any():
            return False
        moved = np.abs(broad[i] - (broad[i - 1] + broad[i + 1]) / 2).reshape(TY, 6, TX, 6).mean(axis=(1, 3)).ravel()
        return bool((bad & (moved < 4)).any())

    soft = []
    for i in sorted(detail):
        if not is_soft(i):
            continue
        # a re-filmed copy that isn't soft replaces it
        for vi, ofn, ot, ob in later.get(i, []):
            keep_t, keep_b = detail[i], broad[i]
            detail[i], broad[i] = ot, ob.astype(np.float32)
            if not is_soft(i):
                best[i] = (1, vi, ofn)
                break
            detail[i], broad[i] = keep_t, keep_b
        else:
            soft.append(i)

    # a layer pass ("b" views of split shots) films only its own range
    expected = range(take.get("first", 0), take.get("last", frames - 1) + 1) if take.get("layer") else range(frames)
    missing = [i for i in expected if i not in best]
    if not best:
        raise SystemExit("no stamped frames found: was the frame stamp hidden?")

    # Passes of one take can be lit a little differently (owner, 2026-11-26: patched frames flashed lighter in the
    # cavern's upper half). Each frame filled from a later recording is matched to the first recording with a smooth
    # per-pixel gain, learnt from up to four nearby indices both recordings hold.
    def frame_at(vi, fn):
        g = geoms[vi]
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(videos[vi]), "-fps_mode", "passthrough",
                              "-vf", f"select=eq(n\\,{fn}),crop={w}:{h}:{g[0]}:{g[1]}", "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32)

    def blur(img):
        from PIL import Image
        small = [np.asarray(Image.fromarray(img[..., c]).resize((max(w // 48, 2), max(h // 48, 2)), Image.BOX))
                 for c in range(3)]
        return np.stack([np.asarray(Image.fromarray(s).resize((w, h), Image.BICUBIC)) for s in small], -1)

    gains, cache = {}, {}
    for i, (_, vi, _) in sorted(best.items()):
        if vi == 0:
            continue
        near = sorted((j for j in alt.get(vi, {}) if best.get(j, (0, 0))[1] == 0 and abs(j - i) <= 20),
                      key=lambda j: abs(j - i))[:4]
        if not near:
            continue
        key = (vi, tuple(near))
        if key not in cache:
            ref = sum(blur(frame_at(0, best[j][2])) for j in near)
            got = sum(blur(frame_at(vi, alt[vi][j])) for j in near)
            cache[key] = np.clip((ref + 4) / (got + 4), 0.6, 1.6)
        gains[i] = cache[key]
    if gains:
        print(f"  matched {len(gains)} patched frame(s) to the first recording's lighting")

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
            if i in gains:
                img = np.frombuffer(last, np.uint8).reshape(h, w, 3).astype(np.float32) * gains[i]
                last = np.clip(img, 0, 255).astype(np.uint8).tobytes()
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
    if soft:
        print(f"  soft (texture caught streaming): {ranges(soft)}  re-film them the same way; the sharper copy wins")
    return 0 if not missing and not soft else 2


def split(take_path, main, layer, out):
    """Split shots (Cameras.luau): the take's view on top and the "b" pass's view below a slanted ink divider. The
    divider rises from the bottom edge as the split opens and carries on up off the top as it closes, so the bottom
    view (the slug) fills the frame for the next shot. Each view is shifted so its middle stays centred in its panel."""
    import numpy as np
    take = load(take_path)
    splits = take.get("splits") or []
    if not splits:
        raise SystemExit(f"{take_path}: no split shots")
    fps, W, H = take.get("fps", 30), 1080, 1920
    size = W * H * 3

    def reader(v):
        return subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(v), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                stdout=subprocess.PIPE)

    ra, rb = reader(main), reader(layer)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    rows, cols = np.mgrid[0:H, 0:W]
    ink, light = np.array([24, 22, 28], np.uint8), np.array([255, 240, 220], np.uint8)

    def ease(u):
        u = min(max(u, 0.0), 1.0)
        return u * u * (3 - 2 * u)

    n, done = 0, 0
    while True:
        a, b = ra.stdout.read(size), rb.stdout.read(size)
        if len(a) < size:
            break
        sp = next((x for x in splits if x["first"] <= n <= x["last"]), None)
        if sp and len(b) == size:
            A = np.frombuffer(a, np.uint8).reshape(H, W, 3)
            B = np.frombuffer(b, np.uint8).reshape(H, W, 3)
            tau, span = (n - sp["first"]) / fps, (sp["last"] - sp["first"] + 1) / fps
            p = 1 - 0.5 * ease(tau / sp["open"]) - 0.5 * ease((tau - (span - sp["close"])) / sp["close"])
            line = p * H - sp["slant"] * H * (cols / W - 0.5)  # the divider's row at each column
            ya = np.clip(rows - round((p * H - H) / 2), 0, H - 1)  # top view, its middle centred above the line
            yb = np.clip(rows - round(p * H / 2), 0, H - 1)  # bottom view, its middle centred below it
            frame = np.where((rows < line)[..., None], A[ya, cols], B[yb, cols])
            if 0 < p < 1:
                d = np.abs(rows - line)
                frame[d < 8] = ink
                frame[d < 2.5] = light
            a = frame.astype(np.uint8).tobytes()
            done += 1
        enc.stdin.write(a)
        n += 1
    enc.stdin.close()
    enc.wait()
    for r in (ra, rb):
        r.stdout.close()
        r.kill()
    print(f"{out}: {n} frames, {done} composited from {len(splits)} split shot(s)")
    return 0


def warp(take_path, dialogue_path, out_dir):
    """Slow motion lengthens the video by each segment's `extra` seconds (Scene.film records them). Segments sit in
    dialogue gaps (scene.py checks), so the dialogue only needs that much silence inserted at each segment's start."""
    import numpy as np
    take, dlg = load(take_path), load(dialogue_path)
    segs = sorted(take.get("warp") or [], key=lambda w: w["from"])
    if not segs:
        raise SystemExit(f"{take_path}: no slow motion")

    def shift(t):
        return t + sum(w["extra"] for w in segs if t >= w["from"] - 1e-6)

    src = ROOT / dlg["audio"]
    out_dir.mkdir(parents=True, exist_ok=True)
    rate = 48000
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.float32)
    parts, at = [], 0
    for w in segs:
        cut = int(round(w["from"] * rate))
        parts += [audio[at:cut], np.zeros(int(round(w["extra"] * rate)), np.float32)]
        at = cut
    parts.append(audio[at:])
    wav = out_dir / "dialogue.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", "-",
                    "-c:a", "pcm_s16le", str(wav)], input=np.concatenate(parts).tobytes(), check=True)
    for ln in dlg["lines"]:
        ln["start"], ln["end"] = round(shift(ln["start"]), 3), round(shift(ln["end"]), 3)
    dlg["duration"] = round(shift(dlg["duration"]), 3)
    dlg["audio"] = wav.resolve().relative_to(ROOT).as_posix()
    dlg["warped_by"] = take["take"]
    (out_dir / "dialogue.json").write_text(json.dumps(dlg, indent=1), encoding="utf-8")
    words = load(Path(dialogue_path).with_name("dialogue.words.json"))
    for x in words:
        k = shift(x["startMs"] / 1000) - x["startMs"] / 1000
        for key in ("startMs", "endMs", "timestampMs"):
            if key in x:
                x[key] = int(round(x[key] + k * 1000))
    (out_dir / "dialogue.words.json").write_text(json.dumps(words, indent=1), encoding="utf-8")
    print(f"{out_dir / 'dialogue.json'}: {len(segs)} slow segment(s), +{sum(w['extra'] for w in segs):.2f}s "
          f"of silence; duration {dlg['duration']}s")
    return 0


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
    s = sub.add_parser("split", help="composite a take's split shots with its layer b pass")
    s.add_argument("take")
    s.add_argument("main")
    s.add_argument("layer")
    s.add_argument("--out")
    w = sub.add_parser("warp", help="dialogue for a take with slow motion")
    w.add_argument("take")
    w.add_argument("dialogue")
    w.add_argument("--out-dir")
    i = sub.add_parser("import")
    i.add_argument("take")
    i.add_argument("video")
    i.add_argument("--capture-manifest")
    i.add_argument("--video-start-ms", type=float)
    a = ap.parse_args()
    if a.cmd == "compare":
        sys.exit(compare(a.a, a.b))
    if a.cmd == "split":
        t = load(a.take)
        sys.exit(split(a.take, a.main, a.layer, Path(a.out) if a.out else ROOT / "out" / "takes" / f"{t['take']}_split.mp4"))
    if a.cmd == "warp":
        t = load(a.take)
        d = Path(a.dialogue)
        sys.exit(warp(a.take, d, Path(a.out_dir) if a.out_dir else d.parent / "warped" / t["take"]))
    if a.cmd == "film":
        t = load(a.take)
        sys.exit(film(a.take, [Path(v) for v in a.video], Path(a.out) if a.out else ROOT / "out" / "takes" / f"{t['take']}.mp4", a.crf))
    do_import(a.take, a.video, a.capture_manifest, a.video_start_ms)


if __name__ == "__main__":
    main()
