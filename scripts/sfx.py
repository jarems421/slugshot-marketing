r"""Original procedural sound effects for marketing edits, in the game's "tactile cavern fantasy" direction
(../slugshot/docs/audio/sound-plan.md). Deterministic (fixed seed): no recordings, downloaded samples, model
services or asset IDs, so every file is ours to use on any platform. Helpers adapted from the game repo's
tools/audio/build_style_test.py (same owner).

  .\ss sfx            writes assets\sfx\*.wav and logs each in assets\LICENSES.csv

  cavern_bed     12 s loopable room tone: low cave air, a far water trickle, sparse drips, a faint glow hum
  slug_land      a heavy, damp creature landing on stone (Rammstone-sized; use lower gain for small slugs)
  floppy_burble  Floppy's sleepy, airy little burble (a smile, a shrug)
  whoosh         a soft air pass for motivated camera moves and whip transitions
  crystal_tick   the small magical accent: a punchline beat or a reveal, never on every cut
  finger_snap    a dry, bright finger snap (human actors; R6 hands have no fingers, so the sound sells it)
  blaster_shot   the slug blaster firing: a soft pneumatic thump with a short rising zip, not a gunshot
  footstep       one light step on stone (place per footfall, low in the mix)
  boing / slide_up / slide_down / cartoon_pop   cartoon comedy accents (a bounce, a rise, a fall, a pop)
  sub_boom       a deep generic boom for a reveal or punchline (original; not a meme recording)
  riser / tension_sting   build-up into a turn; a short horror-style sting
  record_scratch the "wait, what?" stop
  sparkle_reveal an ascending crystal cascade for a reveal (the cavern magic, bigger than crystal_tick)

CC0 Kenney library (impacts, crystal, foley, UI pops, cartoon zips, sci-fi/goo): scripts/sfx_library.py -> assets\sfx\library\
"""
import csv
import math
import wave
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "sfx"
RATE = 48000
SEED = 20261125
RNG = np.random.default_rng(SEED)


def clock(seconds):
    return np.arange(round(seconds * RATE)) / RATE


def noise(t, low, high):
    n = RNG.normal(size=len(t))
    f = np.fft.rfftfreq(len(t), 1 / RATE)
    shape = 1 / np.sqrt(1 + (f / high) ** 8)
    if low:
        shape *= 1 - 1 / np.sqrt(1 + (f / low) ** 8)
    n = np.fft.irfft(np.fft.rfft(n) * shape, n=len(t))
    return n / max(np.std(n), 1e-9)


def decay(t, attack, tail):
    return (1 - np.exp(-t / attack)) * np.exp(-t / tail)


def sweep(t, start, end, rate):
    phase = end * t + (start - end) * rate * (1 - np.exp(-t / rate))
    return np.sin(2 * math.pi * phase)


def modes(t, fundamental, tail, ratios=(1, 2.13, 3.71, 5.43)):
    out = np.zeros_like(t)
    for i, r in enumerate(ratios):
        out += np.sin(2 * math.pi * fundamental * r * t) * decay(t, 0.0008, tail / (1 + i * 0.7)) / (1 + i) ** 1.4
    return out


def place(target, at, sound, gain=1.0):
    s = round(at * RATE)
    n = min(len(sound), len(target) - s)
    target[s:s + n] += sound[:n] * gain


def cavern_bed():
    t = clock(12)
    air = 0.5 * noise(t, 30, 260) * (0.85 + 0.15 * np.sin(2 * math.pi * t / 6))
    trickle = 0.07 * noise(t, 1400, 4200) * (0.6 + 0.4 * np.sin(2 * math.pi * t / 3) ** 2)
    hum = 0.05 * np.sin(2 * math.pi * 55 * t) + 0.025 * np.sin(2 * math.pi * 110.7 * t)
    bed = air + trickle + hum
    for at in (1.3, 3.9, 5.2, 8.1, 10.4):
        td = clock(0.5)
        place(bed, at, modes(td, RNG.uniform(1700, 2600), 0.06, (1, 1.9, 3.1)), 0.18)
    fade = round(0.5 * RATE)  # crossfade the ends so the bed loops without a seam
    bed[:fade] = bed[:fade] * np.linspace(0, 1, fade) + bed[-fade:] * np.linspace(1, 0, fade)
    return bed[:-fade]


def slug_land():
    t = clock(0.55)
    body = 0.55 * sweep(t, 120, 46, 0.03) * decay(t, 0.002, 0.07)
    body += 0.3 * noise(t, 80, 900) * decay(t, 0.002, 0.06)
    place(body, 0.008, noise(t, 700, 4200) * decay(t, 0.002, 0.03), 0.09)
    for at in (0.03, 0.05, 0.08):
        place(body, at, modes(t, RNG.uniform(900, 1500), 0.01), 0.03)
    return body


def floppy_burble():
    t = clock(0.6)
    out = np.zeros_like(t)
    for i, (at, f) in enumerate(((0.0, 260), (0.11, 310), (0.2, 235))):
        tb = clock(0.25)
        bubble = sweep(tb, f * 0.8, f * 1.25, 0.04) * decay(tb, 0.006, 0.05)
        place(out, at, bubble, 0.35 - i * 0.05)
    out += 0.06 * noise(t, 300, 2400) * decay(t, 0.02, 0.15)
    return out


def whoosh():
    t = clock(0.7)
    env = np.sin(np.pi * np.clip(t / 0.7, 0, 1)) ** 2
    centre = 600 + 1600 * np.sin(np.pi * t / 0.7)
    out = np.zeros_like(t)
    for low, high, g in ((200, 900, 0.5), (700, 2600, 0.35), (2000, 6000, 0.15)):
        out += g * noise(t, low, high)
    return out * env * (0.6 + 0.4 * (centre / 2200))


def crystal_tick():
    t = clock(0.7)
    out = 0.3 * modes(t, 1320, 0.22, (1, 2.76, 5.4))
    out += 0.08 * noise(t, 2500, 8000) * decay(t, 0.0005, 0.01)
    return out


def finger_snap():
    t = clock(0.25)
    out = 0.9 * noise(t, 1800, 9000) * decay(t, 0.0003, 0.012)
    out += 0.4 * modes(t, 2100, 0.02, (1, 1.6, 2.7))
    return out


def blaster_shot():
    t = clock(0.6)
    thump = 0.6 * sweep(t, 180, 60, 0.04) * decay(t, 0.002, 0.08)
    puff = 0.35 * noise(t, 300, 2500) * decay(t, 0.003, 0.09)
    zip_ = 0.18 * sweep(t, 600, 1800, 0.08) * decay(t, 0.01, 0.12)
    return thump + puff + zip_


def footstep():
    t = clock(0.3)
    return 0.6 * noise(t, 90, 1200) * decay(t, 0.003, 0.035) + 0.2 * sweep(t, 140, 80, 0.02) * decay(t, 0.002, 0.04)


def boing():
    t = clock(0.7)
    f = 260 * (1 + 0.45 * np.exp(-t / 0.25) * np.sin(2 * math.pi * 11 * t))
    phase = np.cumsum(f) / RATE
    return 0.6 * np.sin(2 * math.pi * phase) * decay(t, 0.003, 0.22)


def slide(up):
    t = clock(0.65)
    a, b = (420, 1350) if up else (1350, 420)
    f = a + (b - a) * (t / t[-1]) ** 0.8
    f = f * (1 + 0.012 * np.sin(2 * math.pi * 6 * t))  # whistle vibrato
    tone = np.sin(2 * math.pi * np.cumsum(f) / RATE)
    env = np.minimum(1, t / 0.04) * np.minimum(1, (t[-1] - t) / 0.06)
    return (0.5 * tone + 0.04 * noise(t, 900, 5000)) * env


def sub_boom():
    t = clock(1.4)
    body = 0.8 * sweep(t, 78, 34, 0.25) * decay(t, 0.004, 0.45)
    body += 0.25 * noise(t, 40, 400) * decay(t, 0.003, 0.12)
    place(body, 0.0, noise(clock(0.05), 1500, 6000) * decay(clock(0.05), 0.0005, 0.008), 0.15)
    return body


def riser():
    t = clock(2.0)
    env = (t / t[-1]) ** 2
    hiss = noise(t, 400, 9000) * env
    tone = np.sin(2 * math.pi * np.cumsum(200 + 1400 * (t / t[-1]) ** 2) / RATE) * env
    return 0.35 * hiss + 0.25 * tone


def record_scratch():
    t = clock(0.55)
    rate = 1 + 0.9 * np.sin(2 * math.pi * 5.5 * t)  # the hand moving back and forth
    grit = noise(t, 300, 5000)
    idx = np.clip((np.cumsum(np.abs(rate)) * 1.0).astype(int), 0, len(t) - 1)
    return 0.7 * grit[idx] * (0.4 + 0.6 * np.abs(np.sin(2 * math.pi * 5.5 * t))) * np.minimum(1, (t[-1] - t) / 0.05)


def sparkle_reveal():
    t = clock(1.0)
    out = np.zeros_like(t)
    for i, f in enumerate((1320, 1568, 1760, 2093, 2637)):
        place(out, 0.07 * i, modes(clock(0.6), f, 0.18, (1, 2.76, 5.4)), 0.22)
    return out + 0.04 * noise(t, 4000, 12000) * decay(t, 0.01, 0.4)


def cartoon_pop():
    t = clock(0.18)
    return 0.7 * sweep(t, 900, 180, 0.02) * decay(t, 0.0008, 0.04) + 0.2 * noise(t, 2000, 8000) * decay(t, 0.0003, 0.006)


def tension_sting():
    t = clock(1.8)
    low = sum(np.sin(2 * math.pi * f * t) for f in (55, 58.3, 82.4)) * decay(t, 0.01, 0.7) * 0.25
    high = sum(np.sin(2 * math.pi * f * t) for f in (1244, 1318)) * decay(t, 0.002, 0.35) * 0.12
    return low + high + 0.15 * noise(t, 60, 600) * decay(t, 0.003, 0.2)


def master(signal, peak):
    signal = signal - signal.mean()
    signal = np.tanh(signal * 1.2)
    signal *= peak / max(np.max(np.abs(signal)), 1e-9)
    f = round(0.006 * RATE)
    signal[:f] *= np.linspace(0, 1, f)
    signal[-f:] *= np.linspace(1, 0, f)
    return signal


def write(path, signal):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(np.rint(signal * 32767).astype("<i2").tobytes())


SOUNDS = {"cavern_bed": (cavern_bed, 0.5), "slug_land": (slug_land, 0.9), "floppy_burble": (floppy_burble, 0.7),
          "whoosh": (whoosh, 0.6), "crystal_tick": (crystal_tick, 0.6),
          # added 2026-11-26 for human actors; appended so the seeded sounds above stay identical
          "finger_snap": (finger_snap, 0.7), "blaster_shot": (blaster_shot, 0.8), "footstep": (footstep, 0.5),
          # added 2026-11-26: comedy and story accents for short-form edits (gaps the CC0 library doesn't cover)
          "boing": (boing, 0.6), "slide_up": (lambda: slide(True), 0.55), "slide_down": (lambda: slide(False), 0.55),
          "sub_boom": (sub_boom, 0.9), "riser": (riser, 0.6), "record_scratch": (record_scratch, 0.6),
          "sparkle_reveal": (sparkle_reveal, 0.55), "cartoon_pop": (cartoon_pop, 0.6), "tension_sting": (tension_sting, 0.7)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = ROOT / "assets" / "LICENSES.csv"
    rows = list(csv.DictReader(log.open(encoding="utf-8")))
    known = {r["file"] for r in rows}
    for name, (make, peak) in SOUNDS.items():
        path = OUT / f"{name}.wav"
        write(path, master(make(), peak))
        rel = f"assets/sfx/{name}.wav"
        if rel not in known:
            rows.append({"file": rel, "kind": "sfx", "source_url": "scripts/sfx.py (original synthesis, seed 20261125)",
                         "licence": "original (owner)", "attribution_required": "no", "allowed_platforms": "all",
                         "commercial_ok": "yes", "added": date.today().isoformat(),
                         "notes": "procedural; no samples, recordings or services"})
        print(path)
    with log.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0].keys()) if rows else
                           ["file", "kind", "source_url", "licence", "attribution_required", "allowed_platforms",
                            "commercial_ok", "added", "notes"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
