r"""Render one video with the Remotion template: stage -> render -> loudness -> QC.

  .\ss render SS_20261125_PVP_FloppyUnderdog_BestSlug_V01_MASTER media\raw\clip.mkv --format PVP ^
      --narration media\vo\vo.wav --captions media\vo\vo.srt --hook "He brought Inferno. I brought Floppy."

Writes exports\<job>.mp4 (1080x1920, yuv420p BT.709, AAC, about -14 LUFS) and <job>.qc.json.
Renders under Remotion's Free License (individuals and companies of up to 3 people).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import qc
import remotion_job

ROOT = Path(__file__).resolve().parent.parent
NPX = "npx.cmd" if os.name == "nt" else "npx"


def render_one(job, clip, fmt="PVP", narration=None, captions=None, hook="", production=True, out_dir=None,
               **overrides):
    props = remotion_job.build(job, clip, fmt, narration, captions, hook, **overrides)
    return finish("Vertical", job, props, production, out_dir)


def finish(composition, job, props, production=True, out_dir=None):
    """Render a staged job (public/<job>/props.json), level the audio, QC it, clean up."""
    tmp = ROOT / "out" / f"{job}.mp4"
    tmp.parent.mkdir(exist_ok=True)
    cmd = [NPX, "--no-install", "remotion", "render", "remotion/index.ts", composition, str(tmp),
           # CRF 14, not Remotion's 18: platforms re-encode uploads, so the master keeps fine detail for them
           # (owner, 2026-11-25: slugs looked low-resolution up close).
           f"--props={props}", "--pixel-format=yuv420p", "--color-space=bt709", "--crf=14",
           "--license-key=free-license", "--log=error"]
    if not production:
        cmd.append("--is-production=false")
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"Remotion render failed for {job}:\n{(r.stderr or r.stdout)[-1500:]}")
    out = Path(out_dir or ROOT / "exports") / f"{job}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    # Remotion doesn't normalise loudness; match the FFmpeg path (about -14 LUFS).
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp), "-c:v", "copy",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(out)], check=True)
    tmp.unlink()
    shutil.rmtree(ROOT / "public" / job, ignore_errors=True)
    overall, results, dur = qc.check(out)
    out.with_suffix(".qc.json").write_text(qc.json.dumps({"file": out.name, "overall": overall, "checks": results},
                                                         indent=1), encoding="utf-8")
    return out, overall, results, dur


def main():
    a = vars(remotion_job.parser(__doc__).parse_args())
    out, overall, results, dur = render_one(a.pop("job"), a.pop("clip"), a.pop("format"), a.pop("narration"),
                                            a.pop("captions"), a.pop("hook"), **a)
    print(f"{out} ({dur:.1f}s) QC {overall}")
    for r in results:
        if r["status"] != "PASS":
            print(f"   {r['status']:5} {r['check']}: {r['detail']}")
    sys.exit(2 if overall == "FAIL" else 0)


if __name__ == "__main__":
    main()
