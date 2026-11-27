r"""Crowd voices for the world sound (owner, 2026-11-27: crowd audio from Gemini TTS, inside the monthly cap).

  python scripts/crowd_audio.py library          generate the missing takes (cached; costs a few cents once)
  python scripts/crowd_audio.py demo OUT.wav     a 20 s check: murmur, then a cheer, a gasp and a laugh

The library lives in assets\sfx\crowd\<kind>\<voice>_<n>.wav (24 kHz mono from Gemini, logged in assets\LICENSES.csv).
Kinds: murmur (casual small talk, unhurried), cheer, gasp, laugh, ooh, scatter (startled, kid-safe). Voices are
Gemini prebuilt voices the cast doesn't use, so the crowd never sounds like a main character.

crowd(kind, n, seconds, seed) layers takes into a crowd of n voices: staggered starts, small pitch and level
differences, spread across the stereo field, a little room reverb. murmur(seconds, density, seed) is a continuous
bed of overlapping chatter. Deterministic for a seed, so every render of an edit matches.
"""
import csv
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "assets" / "sfx" / "crowd"
RATE = 48000
VOICES = ["Charon", "Leda", "Zephyr", "Callirrhoe", "Iapetus", "Despina", "Schedar", "Gacrux", "Laomedeia", "Sulafat",
          "Alnilam", "Erinome"]
LINES = {
    "murmur": ["So what did you end up doing yesterday?", "No way, he actually said that?", "I need to get some food after this.",
               "Have you tried the new arena yet?", "Honestly it was kind of funny.", "Wait, where did everyone go?",
               "My slug keeps falling asleep, I swear.", "Yeah, yeah, I know, I'll do it later.", "That's what I told her!",
               "Did you see the waterfall earlier?", "I mean, it could've gone worse.", "Okay but hear me out."],
    "cheer": ["Yeah! Let's go!", "Woo! Nice one!", "Yesss!", "Let's gooo!", "Come on! Yeah!", "Woohoo!", "That was sick!",
              "Go go go!", "Yeah! Again!", "Woo!"],
    "gasp": ["<gasp> Whoa!", "<gasp> No way!", "<gasp> Ohh!", "<gasp> What?!", "<gasp>", "<gasp> Oh my gosh!",
             "<gasp> Wait, what?", "<gasp> Huh?!", "<gasp> Oh no!", "<gasp> Whoa whoa!"],
    "laugh": ["<laugh>", "<laugh> Ha ha ha!", "<laugh> Oh my days.", "<laugh> No way!", "<laugh> That's so funny.",
              "<laugh> Ha!", "<laugh> Stop it!", "<laugh> Hahaha.", "<laugh> I can't.", "<laugh> Okay, okay."],
    "ooh": ["Ooooh!", "Oooh, nice.", "Ohhh!", "Ooh!", "Woah, ooh!", "Oooooh.", "Ooh, look at that!", "Ohhh, okay!"],
    "scatter": ["Whoa! Run!", "Move, move!", "Watch out!", "Ahh! Go go go!", "Get out of the way!", "Whoa whoa whoa!",
                "Run for it!", "Eek! Move!"],
}
STYLE = {
    "murmur": "Casual background small talk between friends, relaxed and unhurried, conversational, a little distant.",
    "cheer": "An excited spectator cheering at an exciting moment, loud and happy.",
    "gasp": "A shocked onlooker reacting to something surprising, sharp intake of breath, genuinely startled.",
    "laugh": "A spectator genuinely laughing at something funny, warm and natural.",
    "ooh": "An impressed crowd member going ooh at something cool.",
    "scatter": "A startled bystander hurrying out of the way, a bit panicked but playful, family-friendly.",
}


def ffmpeg():
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    return str(next((Path.home() / "AppData/Local/Microsoft/WinGet/Packages").glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe")))


def library():
    import gemini_tts
    log = ROOT / "assets" / "LICENSES.csv"
    rows = []
    for kind, lines in LINES.items():
        out = LIB / kind
        out.mkdir(parents=True, exist_ok=True)
        for i, line in enumerate(lines):
            voice = VOICES[(i * 5 + len(kind)) % len(VOICES)]
            path = out / f"{voice}_{i:02d}.wav"
            if path.exists():
                continue
            secs = gemini_tts.speak(line, voice, STYLE[kind], path)
            print(f"{kind}/{path.name}: {secs:.1f}s", flush=True)
            rows.append([f"assets/sfx/crowd/{kind}/{path.name}", "Gemini TTS (generated, owner-approved commercial use)",
                         f"crowd {kind}: {line}", "generated", date.today().isoformat()])
    if rows:
        with log.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
    print(f"spent this month about ${gemini_tts.month_spend():.3f}")


_cache = {}


def take(path, cents=0.0):
    key = (str(path), round(cents, 1))
    if key not in _cache:
        af = ["loudnorm=I=-20:TP=-3"]
        if cents:
            af.insert(0, f"rubberband=pitch={2 ** (cents / 1200):.5f}:formant=preserved")
        raw = subprocess.run([ffmpeg(), "-v", "error", "-i", str(path), "-af", ",".join(af), "-f", "f32le", "-ac", "1",
                              "-ar", str(RATE), "-"], capture_output=True, check=True).stdout
        _cache[key] = np.frombuffer(raw, "<f4").astype(np.float64)
    return _cache[key]


def takes(kind):
    return sorted((LIB / kind).glob("*.wav"))


def reverb(x, seconds=1.1, wet=0.25, seed=7):
    rng = np.random.default_rng(seed)
    n = int(seconds * RATE)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 6, n))
    ir[0] = 0
    out = np.stack([np.convolve(x[:, c], ir, mode="full")[:len(x)] for c in range(2)], axis=1)
    out *= np.abs(x).max() / max(np.abs(out).max(), 1e-9)
    return x * (1 - wet) + out * wet


def lowpass(x, hz):
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    gain = 1 / np.sqrt(1 + (f / hz) ** 4)
    return np.stack([np.fft.irfft(np.fft.rfft(x[:, c]) * gain, n=len(x)) for c in range(x.shape[1])], axis=1)


def crowd(kind, n, seconds, seed=1, spread=0.35, distance=0.0):
    """n voices of one kind, starting within `spread` seconds of each other. distance 0 (close) .. 1 (far)."""
    rng = np.random.default_rng(seed)
    pool = takes(kind)
    if not pool:
        raise SystemExit(f"no crowd takes for {kind}: run `python scripts/crowd_audio.py library`")
    out = np.zeros((int(seconds * RATE), 2))
    for i in range(n):
        x = take(pool[rng.integers(len(pool))], cents=float(rng.uniform(-150, 150)))
        start = int(rng.uniform(0, spread) * RATE)
        x = x[: max(0, len(out) - start)] * rng.uniform(0.5, 1.0)
        pan = rng.uniform(-0.8, 0.8)
        out[start:start + len(x), 0] += x * np.sqrt((1 - pan) / 2)
        out[start:start + len(x), 1] += x * np.sqrt((1 + pan) / 2)
    out /= max(1.0, np.sqrt(n) * 0.7)
    if distance > 0:
        out = lowpass(out, 6000 - 4500 * distance)
    return reverb(out, wet=0.2 + 0.25 * distance, seed=seed)


def murmur(seconds, density=6, seed=1, distance=0.5):
    """A continuous bed of overlapping chatter: about `density` voices talking at any moment."""
    rng = np.random.default_rng(seed)
    pool = takes("murmur")
    out = np.zeros((int(seconds * RATE), 2))
    for lane in range(density):
        t, pan = rng.uniform(0, 2.5), rng.uniform(-0.9, 0.9)
        while t < seconds:
            x = take(pool[rng.integers(len(pool))], cents=float(rng.uniform(-200, 200))) * rng.uniform(0.4, 0.9)
            s = int(t * RATE)
            x = x[: max(0, len(out) - s)]
            out[s:s + len(x), 0] += x * np.sqrt((1 - pan) / 2)
            out[s:s + len(x), 1] += x * np.sqrt((1 + pan) / 2)
            t += len(x) / RATE + rng.uniform(0.3, 1.8)
    out /= max(1.0, np.sqrt(density) * 0.8)
    return reverb(lowpass(out, 5500 - 4000 * distance), wet=0.3, seed=seed)


def save(path, x, peak=0.9, normalise=True):
    """normalise: scale to `peak`; otherwise keep the levels (a quiet room stays quiet), only pulled down to `peak`
    if it would clip."""
    top = max(np.abs(x).max(), 1e-9)
    if normalise or top > peak:
        x = x * (peak / top)
    pcm = np.rint(np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "2", "-i", "-", str(path)],
                   input=pcm, check=True)


def demo(out):
    total = 20
    x = murmur(total, density=7, seed=3) * 0.6
    for kind, at, n in (("cheer", 5, 8), ("gasp", 10, 8), ("laugh", 14, 7)):
        c = crowd(kind, n, 4, seed=at)
        s = int(at * RATE)
        x[s:s + len(c)] += c[: len(x) - s]
    save(out, x)
    print(out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["library"]:
        library()
    elif sys.argv[1:2] == ["demo"]:
        demo(Path(sys.argv[2]))
    else:
        print(__doc__)
