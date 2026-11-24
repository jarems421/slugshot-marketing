r"""Stage files for the Remotion `Vertical` template and write its props JSON.

  python scripts/remotion_job.py JOB CLIP [--format PVP] [--narration VO] [--captions X.srt] [--hook TEXT] ...

Copies the clip, narration and captions into public/<job>/ (git-ignored) and writes
public/<job>/props.json; `ss render` then calls `remotion render --props=...`.
--format loads a preset from config/formats.json; any flag you pass overrides it.
Captions: a preset with "captions": "words" uses the .words.json next to your .srt when it
exists (word-by-word highlight), otherwise the .srt. Both are written by `ss caption`.
Length: narration + 0.4 s if given, else the clip (a shorter clip loops).
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMATS = json.loads((ROOT / "config" / "formats.json").read_text(encoding="utf-8"))


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def build(job, clip, fmt="PVP", narration=None, captions=None, hook="", **overrides):
    """Stage one job and return the props.json path. Used by batch.py too."""
    preset = {k: v for k, v in FORMATS[fmt.upper()].items() if k != "description"}
    preset.update({k: v for k, v in overrides.items() if v is not None})
    dest = ROOT / "public" / job
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    def stage(src, name):
        if not src:
            return None
        target = dest / name
        shutil.copyfile(src, target)
        return f"{job}/{name}"

    mode = preset.pop("captions", "phrases")
    if captions and mode == "words" and captions.endswith(".srt"):
        words = Path(captions).with_suffix("").with_suffix(".words.json")
        captions_path = stage(str(words), "captions.words.json") if words.exists() else stage(captions, "captions.srt")
    elif captions:
        name = "captions.words.json" if captions.endswith(".words.json") else "captions" + Path(captions).suffix.lower()
        captions_path = stage(captions, name)
    else:
        captions_path = None

    clip_len = duration(clip)
    props = {
        "clip": stage(clip, "clip" + Path(clip).suffix.lower()),
        "clipLengthSeconds": clip_len,
        "narration": stage(narration, "narration" + Path(narration).suffix.lower()) if narration else None,
        "captions": captions_path,
        "hook": hook,
        "hookSeconds": preset.pop("hookSeconds", 2.5),
        "clipSeconds": round(duration(narration) + 0.4 if narration else clip_len, 3),
        "endCardSeconds": preset.pop("endCardSeconds", 2),
        **preset,
    }
    (dest / "props.json").write_text(json.dumps(props, indent=1), encoding="utf-8")
    return dest / "props.json"


def parser(doc=__doc__):
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", help="short name; becomes the output file name under exports/")
    ap.add_argument("clip")
    ap.add_argument("--format", default="PVP", choices=[k for k in FORMATS if not k.startswith("_")])
    ap.add_argument("--narration")
    ap.add_argument("--captions", help=".srt (checked) or .words.json from `ss caption`")
    ap.add_argument("--hook", default="")
    ap.add_argument("--fit", choices=["blur", "crop"])
    ap.add_argument("--clip-volume", type=float, dest="clipVolume")
    ap.add_argument("--accent")
    ap.add_argument("--label", help="persistent corner tag; '' to remove")
    ap.add_argument("--no-end-card", action="store_const", const=False, dest="endCard")
    ap.add_argument("--end-title", dest="endCardTitle")
    ap.add_argument("--end-subtitle", dest="endCardSubtitle")
    return ap


def main():
    a = vars(parser().parse_args())
    print(build(a.pop("job"), a.pop("clip"), a.pop("format"), a.pop("narration"), a.pop("captions"), a.pop("hook"), **a))


if __name__ == "__main__":
    main()
