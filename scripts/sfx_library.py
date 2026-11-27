r"""Curate public-domain (CC0) Kenney audio into assets\sfx\library\<category>\ for video edits.

  python scripts/sfx_library.py <folder-with-extracted-kenney-packs>

The packs (kenney.nl: impact-sounds, interface-sounds, rpg-audio, digital-audio, casino-audio, sci-fi-sounds,
ui-audio) are CC0 1.0: no attribution, any platform, commercial use. Each pick is converted to 48 kHz WAV and
logged in assets\LICENSES.csv. Original procedural sounds stay in scripts/sfx.py.
"""
import csv
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "sfx" / "library"
# category: [(pack, filename prefix, how many variants)]
PICKS = {
    "impacts": [("impact-sounds", "impactPunch_heavy", 2), ("impact-sounds", "impactPunch_medium", 1), ("impact-sounds", "impactSoft_heavy", 2),
                ("impact-sounds", "impactSoft_medium", 1), ("impact-sounds", "impactWood_heavy", 1), ("impact-sounds", "impactMetal_heavy", 1),
                ("impact-sounds", "impactPlate_heavy", 1), ("impact-sounds", "impactBell_heavy", 1), ("impact-sounds", "impactMining", 1),
                ("sci-fi-sounds", "lowFrequency_explosion", 2), ("sci-fi-sounds", "explosionCrunch", 1)],
    "crystal": [("impact-sounds", "impactGlass_light", 2), ("impact-sounds", "impactGlass_medium", 1), ("interface-sounds", "glass", 2)],
    "foley": [("impact-sounds", "footstep_concrete", 3), ("impact-sounds", "footstep_wood", 1), ("impact-sounds", "footstep_grass", 1),
              ("rpg-audio", "doorOpen", 1), ("rpg-audio", "doorClose", 1), ("rpg-audio", "creak", 2), ("rpg-audio", "cloth", 2),
              ("rpg-audio", "bookFlip", 1), ("rpg-audio", "metalLatch", 1), ("rpg-audio", "handleCoins", 1), ("casino-audio", "chips-stack", 1),
              ("casino-audio", "dice-throw", 1)],
    "ui-pops": [("interface-sounds", "click", 1), ("interface-sounds", "select", 1), ("interface-sounds", "confirmation", 2), ("interface-sounds", "error", 1),
                ("interface-sounds", "drop", 1), ("interface-sounds", "pluck", 2), ("interface-sounds", "bong", 1), ("interface-sounds", "question", 1),
                ("interface-sounds", "toggle", 1), ("interface-sounds", "maximize", 1), ("interface-sounds", "minimize", 1),
                ("interface-sounds", "scratch", 1), ("interface-sounds", "glitch", 1)],
    "cartoon-zips": [("digital-audio", "powerUp", 3), ("digital-audio", "phaserUp", 1), ("digital-audio", "phaserDown", 1), ("digital-audio", "highUp", 1),
                     ("digital-audio", "highDown", 1), ("digital-audio", "lowDown", 1), ("digital-audio", "pepSound", 1), ("digital-audio", "zapThreeToneUp", 1),
                     ("digital-audio", "zapThreeToneDown", 1), ("digital-audio", "threeTone", 1), ("digital-audio", "twoTone", 1), ("digital-audio", "phaseJump", 1)],
    "scifi-goo": [("sci-fi-sounds", "slime", 2), ("sci-fi-sounds", "forceField", 1), ("sci-fi-sounds", "thrusterFire", 1), ("sci-fi-sounds", "laserSmall", 1),
                  ("sci-fi-sounds", "computerNoise", 1)],
}


def ffmpeg():
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    hits = list(Path.home().glob("AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/*/bin/ffmpeg.exe"))
    if not hits:
        raise SystemExit("ffmpeg not found")
    return str(hits[0])


def main():
    src = Path(sys.argv[1])
    ff = ffmpeg()
    log = ROOT / "assets" / "LICENSES.csv"
    rows = list(csv.DictReader(log.open(encoding="utf-8")))
    known = {r["file"] for r in rows}
    n = 0
    for cat, picks in PICKS.items():
        (OUT / cat).mkdir(parents=True, exist_ok=True)
        for pack, prefix, count in picks:
            files = sorted(p for p in (src / pack).iterdir() if p.stem.startswith(prefix) and p.suffix in (".ogg", ".wav"))[:count]
            if not files:
                print(f"missing: {pack}/{prefix}")
            for f in files:
                dest = OUT / cat / f"{f.stem}.wav"
                subprocess.run([ff, "-v", "error", "-y", "-i", str(f), "-ar", "48000", str(dest)], check=True)
                rel = dest.relative_to(ROOT).as_posix()
                if rel not in known:
                    rows.append({"file": rel, "kind": "sfx", "source_url": f"https://kenney.nl/assets/{pack}", "licence": "CC0 1.0 (Kenney)",
                                 "attribution_required": "no", "allowed_platforms": "all", "commercial_ok": "yes",
                                 "added": date.today().isoformat(), "notes": f"Kenney {pack}/{f.name}; converted to 48 kHz WAV"})
                    known.add(rel)
                n += 1
    with log.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"{n} sounds in {OUT}")


if __name__ == "__main__":
    main()
