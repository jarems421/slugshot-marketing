r"""Voiceover clean-up and mixing with FFmpeg.

  tidy IN OUT   high-pass, optional denoise, shorten long pauses (keeps a short breath), optional
                speed-up, gentle compression, level to about -16 LUFS
  mix  OUT --narration VO [--music BED] [--sfx file@seconds ...]
                music loops under the voice and ducks while it speaks; SFX land at set times;
                the result (about -14 LUFS) goes to `ss vertical --narration` or `ss render --narration`

  .\ss audio tidy media\vo\raw.wav media\vo\clean.wav --denoise --speed 1.08
  .\ss audio mix media\vo\mixed.wav --narration media\vo\clean.wav --music assets\music\bed.mp3 --sfx assets\sfx\whoosh.wav@2.4

Only use music and SFX you have rights to (see assets\LICENSES.csv). For trending sounds,
add them in each platform's app instead of baking them in.
"""
import argparse
import subprocess
from pathlib import Path


def run(cmd):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *cmd], check=True)


def tidy(a):
    chain = ["highpass=f=80"]
    if a.denoise:
        chain.append("afftdn=nf=-25")
    # Pauses longer than --max-pause are cut down to --keep-pause; shorter ones are left alone.
    chain.append(f"silenceremove=start_periods=1:start_threshold={a.threshold}dB:start_silence=0.05:"
                 f"stop_periods=-1:stop_duration={a.max_pause}:stop_threshold={a.threshold}dB:stop_silence={a.keep_pause}")
    if a.speed != 1:
        chain.append(f"atempo={a.speed}")
    chain += ["acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2",
              "loudnorm=I=-16:TP=-1.5:LRA=9", "aresample=48000"]
    run(["-i", a.input, "-af", ",".join(chain), "-ac", "1", a.output])
    print(a.output)


def mix(a):
    inputs = ["-i", a.narration]
    count = 1
    graph = ["[0:a]aresample=48000,asplit=2[voice][key]"]
    layers = ["[voice]"]
    if a.music:
        inputs += ["-stream_loop", "-1", "-i", a.music]
        count += 1
        graph.append(f"[1:a]aresample=48000,volume={a.music_db}dB[bed]")
        graph.append("[bed][key]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[ducked]")
        layers.append("[ducked]")
    else:
        graph.append("[key]anullsink")
    for i, spec in enumerate(a.sfx or []):
        path, _, at = spec.rpartition("@")
        inputs += ["-i", path]
        ms = int(float(at) * 1000)
        graph.append(f"[{count}:a]aresample=48000,volume={a.sfx_db}dB,adelay={ms}|{ms}[sfx{i}]")
        layers.append(f"[sfx{i}]")
        count += 1
    graph.append(f"{''.join(layers)}amix=inputs={len(layers)}:duration=first:normalize=0,"
                 "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[out]")
    run([*inputs, "-filter_complex", ";".join(graph), "-map", "[out]", a.output])
    print(a.output)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tidy")
    t.add_argument("input")
    t.add_argument("output")
    t.add_argument("--denoise", action="store_true", help="for mic recordings with hiss or room noise")
    t.add_argument("--speed", type=float, default=1.0, help="1.05-1.15 is plenty; check it on a phone")
    t.add_argument("--max-pause", type=float, default=0.35)
    t.add_argument("--keep-pause", type=float, default=0.15)
    t.add_argument("--threshold", type=float, default=-45)
    m = sub.add_parser("mix")
    m.add_argument("output")
    m.add_argument("--narration", required=True)
    m.add_argument("--music")
    m.add_argument("--music-db", type=float, default=-18)
    m.add_argument("--sfx", nargs="*", help="file@seconds")
    m.add_argument("--sfx-db", type=float, default=-6)
    a = ap.parse_args()
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    {"tidy": tidy, "mix": mix}[a.cmd](a)


if __name__ == "__main__":
    main()
