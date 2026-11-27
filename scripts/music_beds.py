r"""Cut scene beds together into one music track, with transitions chosen by the change in energy.

  python scripts/music_beds.py plan.json        (or import plan_fades / render)

plan.json: {"out": "media/x_music.wav", "total": 109.6,
            "beds": [{"src": "assets/music/M2a-cavern-sneak-chill-nature-subtle.wav", "at": 0},
                     {"src": "assets/music/S06-showdown.mp3", "at": 17.13}, ...]}

Owner rule (2026-11-27): going UP in energy (calm -> tense) may be sharp, landing on the beat; coming DOWN (tense ->
calm) must never be sharp: the old bed fades out gradually under the new one. The old fixed 0.35 s crossfade made
every change sound abrupt ("all the sound transitions are currently sharp rather than intentional choices").
Every bed is levelled to -16 LUFS first, as `ss audio mix` does.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RATE = 48000
# Energy of each bed (docs/creative/music-brief.md): 1 calm, 2 lively, 3 intense.
ENERGY = {"M1": 2, "M2": 1, "M2a": 1, "M2b": 1, "M3": 1, "M4": 2, "M5": 3, "M6": 1, "M6a": 1, "M7": 1,
          "S01": 2, "S02": 3, "S03": 2, "S04": 1, "S05": 1, "S06": 3, "S07": 3, "S08": 2, "S09": 3, "S10": 1, "S11": 3}
UP_FADE = 0.25        # rising: a quick, decisive switch on the beat
LEVEL_FADE = 1.0      # same energy: a soft crossfade
DOWN_OUT, DOWN_IN = 3.0, 1.5   # falling: the old bed sinks away over 3 s while the new one rises over 1.5 s


def energy(src):
    stem = Path(src).stem
    for key in sorted(ENERGY, key=len, reverse=True):
        if stem.startswith(key + "-") or stem == key:
            return ENERGY[key]
    return 2


def plan_fades(beds):
    """Per bed: (fade_in, fade_out) seconds, from the energy step at each change."""
    out = [[0.0, 0.0] for _ in beds]
    for i in range(1, len(beds)):
        a, b = energy(beds[i - 1]["src"]), energy(beds[i]["src"])
        if b > a:
            out[i - 1][1], out[i][0] = UP_FADE, UP_FADE
        elif b < a:
            out[i - 1][1], out[i][0] = DOWN_OUT, DOWN_IN
        else:
            out[i - 1][1], out[i][0] = LEVEL_FADE, LEVEL_FADE
    if beds:
        out[0][0] = 0.5
        out[-1][1] = 1.5
    return out


def load(src):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ROOT / src), "-af", "loudnorm=I=-16:TP=-2:LRA=11",
                          "-f", "f32le", "-ac", "2", "-ar", str(RATE), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<f4").reshape(-1, 2).astype(np.float64)


def render(plan):
    beds, total = plan["beds"], float(plan["total"])
    fades = plan_fades(beds)
    mix = np.zeros((int(total * RATE) + RATE, 2))
    for i, bed in enumerate(beds):
        start = float(bed["at"])
        end = float(beds[i + 1]["at"]) if i + 1 < len(beds) else total
        fin, fout = fades[i]
        # a falling change lets the old bed run on past the change while it sinks away
        n = int((end - start + fout) * RATE)
        x = load(bed["src"])
        x = np.concatenate([x] * int(np.ceil(n / len(x))))[:n]
        env = np.ones(n)
        ni, no = int(fin * RATE), int(fout * RATE)
        if ni:
            env[:ni] = np.linspace(0, 1, ni) ** 2 if fin > LEVEL_FADE else np.linspace(0, 1, ni)
        if no:
            env[-no:] = np.linspace(1, 0, no) ** (0.5 if fout > LEVEL_FADE else 1)
        s = int(start * RATE)
        seg = mix[s:s + n]
        seg += (x * env[:, None])[:len(seg)]
    mix = mix[: int(total * RATE)]
    mix *= 0.9 / max(np.abs(mix).max(), 1e-9)
    out = ROOT / plan["out"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "2", "-i", "-", "-ar", str(RATE), str(out)],
                   input=np.rint(np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes(), check=True)
    for bed, (fi, fo) in zip(beds, fades):
        print(f"{float(bed['at']):7.2f}s {Path(bed['src']).stem:36} in {fi:.2f}s out {fo:.2f}s")
    return out


if __name__ == "__main__":
    print(render(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))))
