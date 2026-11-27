r"""The world's sound for a filmed scene (owner, 2026-11-27: "spatial ambience, crowd audio and environmental sounds").

  python scripts/soundscape.py <scene_id> <take_manifest.json> <out.wav>

Reads the scene spec (expanded the way the runtime films it: crowds, reactions, acting) and the take manifest's
camera samples, and writes one stereo track to mix under dialogue and music (`"ambience"` in an ss assemble edit):

- ambience for the place: cavern air, far or near waterfalls, drips, crickets and crystal shimmer (hub, grove,
  wild cavern), room tone and a ticking clock indoors, clinks and lantern hum at the market, wind on the arena;
- crowd murmur that follows the picture: louder when more extras are on screen and near the lens, panned to where
  they are (Gemini crowd library, scripts/crowd_audio.py);
- the crowd's reactions you can hear, at each `ambient.reactions` moment, sized to how many react;
- foley from the action: footsteps of walkers near the camera, slug landings, a soft cloth sound on pick-ups.
Original synthesis plus CC0 foley and our generated crowd voices; deterministic for a scene.
"""
import json
import zlib
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "roblox-native" / "tools"))
import crowd_audio  # noqa: E402
from music_nature import crickets, drip, shimmer  # noqa: E402
from sfx import RATE, noise  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FOLEY = ROOT / "assets" / "sfx" / "library" / "foley"
REACT_SOUND = {"cheer": "cheer", "gasp": "gasp", "flinch": "gasp", "laugh": "laugh", "turn": "ooh", "point": "ooh",
               "scatter": "scatter"}


def load_spec(scene_id):
    import scene
    path = next((ROOT / "roblox-native" / "scenes").rglob(f"{scene_id}.json"))
    spec = json.loads(path.read_text(encoding="utf-8"))
    errs = scene.validate(spec)
    if errs:
        raise SystemExit("scene doesn't validate: " + "; ".join(errs[:3]))
    return spec


def place_kind(spec):
    st = spec["set"]
    if st.get("kind") == "location":
        return {"bedroom": "interior", "classroom": "interior", "market": "market", "wild_cavern": "wild"}.get(st.get("location"), "interior")
    x = st.get("origin", [0, 0, 0])[0]
    return "arena" if x > 3000 else "grove" if 90 < x < 230 else "plaza"


def wav(path):
    return crowd_audio.take(path)


def ambience(kind, seconds, rng):
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    L, R = np.zeros(n), np.zeros(n)

    def add(x, pan=0.5, gain=1.0):
        L[: len(x)] += x * gain * math.cos(pan * math.pi / 2)
        R[: len(x)] += x * gain * math.sin(pan * math.pi / 2)

    def events(make, gain, every):
        at = rng.uniform(0.5, every)
        while at < seconds - 1:
            s = make() * gain * rng.uniform(0.6, 1.0)
            i = int(at * RATE)
            pan = rng.uniform(0.15, 0.85)
            seg = s[: n - i]
            L[i:i + len(seg)] += seg * math.cos(pan * math.pi / 2)
            R[i:i + len(seg)] += seg * math.sin(pan * math.pi / 2)
            at += rng.uniform(0.6, 1.4) * every

    if kind in ("plaza", "grove", "wild", "market"):
        air = noise(t, 80, 700) * (0.6 + 0.4 * np.sin(2 * math.pi * t / 13) ** 2) * 0.012
        add(air, 0.4)
        add(noise(t, 90, 700)[::-1] * 0.010, 0.6)
    if kind == "plaza":
        add(noise(t, 400, 3500) * 0.004, 0.75)                       # the plaza's waterfalls, far off
        add(noise(t, 30, 140) * 0.010, 0.3)                          # the volcano's low rumble
        events(shimmer, 0.008, 5)
        events(drip, 0.02, 4)
    if kind in ("grove", "wild"):
        add(noise(t, 300, 4500) * (0.012 if kind == "grove" else 0.005), 0.7)   # waterfall / stream
        events(drip, 0.03, 2.5)
        events(crickets, 0.006, 3)
        events(shimmer, 0.01, 4)
    if kind == "arena":
        add(noise(t, 60, 400) * (0.7 + 0.3 * np.sin(2 * math.pi * t / 7)) * 0.016, 0.5)
    if kind == "interior":
        add(noise(t, 50, 260) * 0.004, 0.5)                          # room tone
        add(noise(t, 80, 500) * 0.003, 0.2)                          # the cavern outside, through the walls
        tick = np.exp(-np.arange(int(0.03 * RATE)) / (0.004 * RATE)) * np.sin(2 * math.pi * 2600 * np.arange(int(0.03 * RATE)) / RATE)
        for k in range(int(seconds)):
            i = int((k + 0.5) * RATE)
            L[i:i + len(tick)] += tick[: n - i] * 0.004
            R[i:i + len(tick)] += tick[: n - i] * 0.003
    if kind == "market":
        add(noise(t, 110, 130) * 0.003, 0.5)                         # lantern hum
        clink = lambda: np.sin(2 * math.pi * rng.uniform(2200, 3800) * np.arange(int(0.25 * RATE)) / RATE) \
            * np.exp(-np.arange(int(0.25 * RATE)) / (0.04 * RATE))   # noqa: E731
        events(clink, 0.01, 2.5)
    # the layers above are written at subtle relative levels; this brings the bed to about -38 dBFS outdoors and
    # -40 indoors (present on a phone, well under dialogue and music)
    return np.stack([L, R], axis=1) * (5.0 if kind == "interior" else 2.5)


class Camera:
    def __init__(self, samples):
        self.s = sorted(samples, key=lambda c: c["t"])

    def at(self, t):
        if not self.s:
            return None
        c = min(self.s, key=lambda c: abs(c["t"] - t))
        return np.array(c["pos"]), np.array(c["look"])


def actor_pos(spec, origin, name, t):
    marks, a = spec["marks"], spec["actors"][name]
    m = a.get("mark")
    for b in spec["timeline"]:
        if b.get("actor") == name and b.get("action") == "move_to" and isinstance(b.get("time"), (int, float)) \
                and b["time"] + float(b.get("duration") or 1) <= t:
            m = b["mark"]
    p = marks.get(m, [0, 0, 0])
    return np.array([origin[0] + p[0], origin[1] + p[1], origin[2] + p[2]])


def seen(cam, p):
    """(on-screen weight 0..1, pan -1..1) of a point for a camera sample."""
    pos, look = cam
    d = p - pos
    dist = np.linalg.norm(d) + 1e-6
    ang = math.degrees(math.acos(max(-1, min(1, float(np.dot(d / dist, look / np.linalg.norm(look)))))))
    right = np.cross(look, [0, 1, 0])
    pan = float(np.dot(d / dist, right / (np.linalg.norm(right) + 1e-6)))
    w = (1 if ang < 35 else max(0, 1 - (ang - 35) / 40)) / (1 + dist / 10)
    return w, max(-1, min(1, pan))


def build(scene_id, manifest_path, out):
    spec = load_spec(scene_id)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    seconds = float(manifest.get("duration_out") or manifest["frames"] / 30)
    origin = spec["set"].get("origin", [0, 0, 0])
    rng = np.random.default_rng(zlib.crc32(scene_id.encode()))  # stable across runs (hash() is salted)
    world = ambience(place_kind(spec), seconds, rng)
    cams = Camera(manifest.get("camera", []))
    people = [n for n in spec["actors"] if n.startswith("amb_p")]
    n = len(world)
    # crowd murmur that follows the picture
    if people and cams.s:
        bed = crowd_audio.murmur(seconds, density=min(9, max(2, len(people) // 2)), seed=7, distance=0.4)[:n]
        steps = np.arange(0, seconds, 0.25)
        gain, pan = [], []
        for t in steps:
            cam = cams.at(t)
            ws = [seen(cam, actor_pos(spec, origin, p, t)) for p in people]
            total = sum(w for w, _ in ws)
            gain.append(min(1.0, 0.25 + total / 2.5))
            pan.append(sum(w * pn for w, pn in ws) / total if total > 1e-6 else 0.0)
        g = np.interp(np.arange(n) / RATE, steps, np.convolve(gain, np.ones(5) / 5, mode="same"))
        pn = np.interp(np.arange(n) / RATE, steps, np.convolve(pan, np.ones(5) / 5, mode="same")) * 0.6
        world[:, 0] += bed[:, 0] * g * np.sqrt((1 - pn) / 2) * 0.55
        world[:, 1] += bed[:, 1] * g * np.sqrt((1 + pn) / 2) * 0.55
    # reactions you can hear
    for r in spec.get("_reactions", []):
        kind = REACT_SOUND.get(r.get("kind"), "ooh")
        at = float(r["at"])
        who = len([p for p in people]) if r.get("who", "all") != "slugs" else 0
        if not who or at >= seconds:
            continue
        cam = cams.at(at)
        onscreen = sum(seen(cam, actor_pos(spec, origin, p, at))[0] for p in people) if cam else 1
        c = crowd_audio.crowd(kind, min(12, max(3, who)), 4.0, seed=int(at * 10), spread=0.3) * min(1.0, 0.45 + onscreen / 2)
        i = int((at + 0.1) * RATE)
        world[i:i + len(c)] += c[: n - i] * (0.8 if kind != "ooh" else 0.5)
    # foley from the action
    steps_wav = sorted(FOLEY.glob("footstep_*.wav"))
    land = ROOT / "assets" / "sfx" / "slug_land.wav"
    cloth = sorted(FOLEY.glob("cloth*.wav"))
    for b in spec["timeline"]:
        t0, name = b.get("time"), b.get("actor")
        if not isinstance(t0, (int, float)) or name not in spec["actors"] or t0 >= seconds:
            continue
        kind = spec["actors"][name].get("kind")
        sounds = []
        if b.get("action") == "move_to" and kind == "human" and b.get("gait", "walk") in ("walk", "run", "sprint") and steps_wav:
            every = 0.5 if b.get("gait", "walk") == "walk" else 0.3
            sounds = [(t0 + k * every, steps_wav[k % len(steps_wav)], 0.5) for k in range(int(float(b.get("duration") or 1) / every))]
        elif b.get("action") == "move_to" and b.get("gait") == "hop" and land.exists():
            air, gap = float(b.get("hop_time", 0.42)), float(b.get("gap", 0.18))
            sounds = [(t0 + air + k * (air + gap), land, 0.35) for k in range(int(b.get("hops", 1)))]
        elif b.get("action") == "hold" and cloth:
            sounds = [(t0 + 0.2, cloth[0], 0.3)]
        for t, path, level in sounds:
            if t >= seconds or not cams.s:
                continue
            w, pn = seen(cams.at(t), actor_pos(spec, origin, name, t))
            if w < 0.05:
                continue
            x = wav(path) * level * min(1.0, w * 2)
            i = int(t * RATE)
            seg = x[: n - i]
            world[i:i + len(seg), 0] += seg * math.sqrt((1 - pn * 0.7) / 2)
            world[i:i + len(seg), 1] += seg * math.sqrt((1 + pn * 0.7) / 2)
    crowd_audio.save(out, world, peak=0.7, normalise=False)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
    else:
        print(build(sys.argv[1], sys.argv[2], sys.argv[3]))
