"""Make a 1080x1920 captioned MP4 with FFmpeg: clip + optional narration + SRT captions + hook text.

  --fit blur  whole landscape frame centred over a blurred fill (safe for HUD/UI)
  --fit crop  centre crop to fill the frame (bigger action; check nothing important is cut)

Audio is the narration (if given) mixed over the clip's own audio at --clip-volume,
loudness-normalised to about -14 LUFS. If the narration is longer than the clip, the clip loops.
"""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

W, H, FPS = 1080, 1920, 30

# ASS colours are &HAABBGGRR. Yellow #ffd23f, ink #16161a.
ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial Black,104,&H00FFFFFF,&H00FFFFFF,&H001A1616,&H80000000,0,0,0,0,100,100,0,0,1,6,3,2,70,70,500,1
Style: Hook,Arial Black,84,&H001A1616,&H001A1616,&H003FD2FF,&H003FD2FF,0,0,0,0,100,100,0,0,3,20,0,8,80,80,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    return float(info["format"]["duration"]), any(s["codec_type"] == "audio" for s in info["streams"])


def ass_time(t):
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def ass_text(text):
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def srt_events(srt_path):
    blocks = re.split(r"\n\s*\n", Path(srt_path).read_text(encoding="utf-8-sig").strip())
    for b in blocks:
        lines = b.strip().splitlines()
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", lines[1] if len(lines) > 1 else "")
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        yield start, end, "\n".join(lines[2:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip")
    ap.add_argument("out")
    ap.add_argument("--narration")
    ap.add_argument("--srt", help="captions to burn in (from caption.py, checked by hand)")
    ap.add_argument("--hook", default="", help="text box at the top for the first --hook-seconds")
    ap.add_argument("--hook-seconds", type=float, default=2.5)
    ap.add_argument("--fit", choices=["blur", "crop"], default="blur")
    ap.add_argument("--start", type=float, default=0, help="start time in the clip (s)")
    ap.add_argument("--duration", type=float, help="output length (s); default: narration + 0.4 s, else clip")
    ap.add_argument("--clip-volume", type=float, default=0.25)
    args = ap.parse_args()

    clip_len, clip_has_audio = probe(args.clip)
    if args.duration:
        duration = args.duration
    elif args.narration:
        duration = probe(args.narration)[0] + 0.4
    else:
        duration = clip_len - args.start

    events = []
    if args.hook:
        events.append(f"Dialogue: 1,{ass_time(0)},{ass_time(args.hook_seconds)},Hook,,0,0,0,,{ass_text(args.hook)}")
    if args.srt:
        events += [f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Caption,,0,0,0,,{ass_text(t)}" for s, e, t in srt_events(args.srt)]

    if args.fit == "blur":
        video = (f"[0:v]fps={FPS},split[a][b];"
                 f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:2,eq=brightness=-0.15[bg];"
                 f"[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    else:
        video = f"[0:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    video += ",setsar=1,ass=sub.ass,format=yuv420p[v]"

    audio_in = []
    if clip_has_audio:
        audio_in.append(f"[0:a]volume={args.clip_volume}[ca]")
    if args.narration:
        audio_in.append("[1:a]anull[na]")
    labels = ("[ca]" if clip_has_audio else "") + ("[na]" if args.narration else "")
    if labels:
        mix = "amix=inputs=2:normalize=0," if len(audio_in) == 2 else ""
        audio = ";".join(audio_in) + f";{labels}{mix}loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
    else:
        audio = None

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    loop = duration > clip_len - args.start
    cmd += (["-stream_loop", "-1"] if loop else []) + ["-ss", str(args.start), "-i", str(Path(args.clip).resolve())]
    if args.narration:
        cmd += ["-i", str(Path(args.narration).resolve())]
    cmd += ["-filter_complex", video + (";" + audio if audio else ""), "-map", "[v]"]
    cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"] if audio else ["-an"]
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd += ["-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-r", str(FPS), "-movflags", "+faststart", str(out)]

    # The ass filter is given a bare filename so Windows drive colons never need escaping.
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "sub.ass").write_text(ASS_HEADER + "\n".join(events) + "\n", encoding="utf-8")
        subprocess.run(cmd, cwd=tmp, check=True)
    print(f"{out} ({duration:.1f}s, {W}x{H}{', clip looped' if loop else ''})")


if __name__ == "__main__":
    main()
