r"""Lay a subtle, scattered cavern-nature layer under a music bed (owner request 2026-11-26: M2a plus nature,
"subtle, not in your face, not every second, scattered throughout"). Original synthesis (sfx.py helpers), no samples.

  python scripts/music_nature.py [assets\music\M2a-cavern-sneak-chill.mp3]

Writes <bed>-nature-{faint,subtle,noticeable}.wav (layer about 25, 20 and 16 dB under the bed) next to the bed and logs them in assets\LICENSES.csv.
Layers: a soft breeze, a far stream that swells and fades, and sparse events (water drips, a far bird, cave crickets,
a faint crystal shimmer) at random 3-9 s gaps, panned and given a cave reverb.
"""
import csv
import math
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfx import RATE, ROOT, clock, decay, modes, noise, place

RNG = np.random.default_rng(20261126)


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(RATE), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<f4").reshape(-1, 2).astype(np.float64)


def lowpass(x, hz):
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    return np.fft.irfft(np.fft.rfft(x) / np.sqrt(1 + (f / hz) ** 4), n=len(x))


def drip():
    t = clock(0.6)
    f0 = RNG.uniform(900, 1700)
    plip = np.sin(2 * math.pi * (f0 * t + f0 * 1.6 * 0.012 * (1 - np.exp(-t / 0.012)))) * decay(t, 0.0005, 0.035)
    return plip + 0.4 * modes(t, f0 * 1.9, 0.08, (1, 2.4)) * 0.3


def bird():
    out = np.zeros(round(1.2 * RATE))
    at, base = 0.0, RNG.uniform(2600, 3600)
    for _ in range(RNG.integers(2, 5)):
        t = clock(RNG.uniform(0.06, 0.11))
        f = base * (1 + 0.35 * np.sin(math.pi * t / t[-1])) + 180 * np.sin(2 * math.pi * 38 * t)
        note = np.sin(2 * math.pi * np.cumsum(f) / RATE) * np.sin(math.pi * t / t[-1]) ** 2
        place(out, at, note)
        at += len(t) / RATE + RNG.uniform(0.04, 0.12)
    return lowpass(out, 5000)


def crickets():
    t = clock(RNG.uniform(0.8, 1.6))
    gate = (np.sin(2 * math.pi * 28 * t) > 0.2) * (np.sin(2 * math.pi * 2.2 * t) > -0.3)
    return np.sin(2 * math.pi * RNG.uniform(4200, 4800) * t) * gate * np.sin(math.pi * t / t[-1])


def shimmer():
    t = clock(1.4)
    return sum(modes(t - i * 0.09 if i else t, 2300 * 1.26 ** i, 0.5, (1, 2.01)) * (t >= i * 0.09) for i in range(3)) / 3


def reverb(x, seconds=1.6, wet=0.35):
    t = clock(seconds)
    ir = RNG.normal(size=len(t)) * np.exp(-t / (seconds / 5))
    n = 1 << int(np.ceil(np.log2(len(x) + len(ir))))
    tail = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir / np.sqrt(np.sum(ir ** 2)), n), n)[:len(x)]
    return x + wet * tail


def layer(seconds, density):
    n = round(seconds * RATE)
    t = np.arange(n) / RATE
    left, right = np.zeros(n), np.zeros(n)
    breeze = noise(t, 120, 900) * (0.55 + 0.45 * np.sin(2 * math.pi * t / 11 + 1) ** 2) * 0.010
    stream = noise(t, 900, 3500) * np.clip(np.sin(2 * math.pi * t / 23 + 2), 0, 1) ** 2 * 0.006
    left += breeze + stream * 0.7
    right += breeze[::-1] + stream * 1.0
    kinds = [(drip, 0.035, 5), (bird, 0.012, 1.5), (crickets, 0.006, 1.2), (shimmer, 0.010, 1)]
    weights = np.array([k[2] for k in kinds]) / sum(k[2] for k in kinds)
    at = RNG.uniform(1.5, 3.5)
    while at < seconds - 2:
        make, gain, _ = kinds[RNG.choice(len(kinds), p=weights)]
        s = make() * gain * RNG.uniform(0.6, 1.0)
        pan = RNG.uniform(0.15, 0.85)
        place(left, at, s * math.cos(pan * math.pi / 2))
        place(right, at, s * math.sin(pan * math.pi / 2))
        at += RNG.uniform(3, 9) / density
    return np.stack([reverb(left), reverb(right)], axis=1)


def save(path, x):
    pcm = np.rint(np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "2", "-i", "-", str(path)],
                   input=pcm, check=True)


def main():
    bed_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "assets" / "music" / "M2a-cavern-sneak-chill.mp3"
    bed = load(bed_path)
    log = ROOT / "assets" / "LICENSES.csv"
    rows = list(csv.DictReader(log.open(encoding="utf-8")))
    levels = (("faint", 0.8, 1.0), ("subtle", 1.0, 1.8), ("noticeable", 1.0, 2.8))
    for label, density, level in [l for l in levels if len(sys.argv) < 3 or l[0] == sys.argv[2]]:
        mix = bed + layer(len(bed) / RATE, density) * level
        mix *= min(1.0, 0.89 / np.max(np.abs(mix)))
        out = bed_path.with_name(f"{bed_path.stem}-nature-{label}.wav")
        save(out, mix)
        rel = out.relative_to(ROOT).as_posix()
        if rel not in {r["file"] for r in rows}:
            rows.append({"file": rel, "kind": "music", "source_url": f"{bed_path.name} + scripts/music_nature.py (original synthesis)",
                         "licence": "as the source bed (Lyria; Google Gemini API terms) plus original nature layer",
                         "attribution_required": "no", "allowed_platforms": "check Google terms before publishing",
                         "commercial_ok": "check", "added": date.today().isoformat(), "notes": f"nature layer {label}; owner request"})
        print(out)
    with log.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
