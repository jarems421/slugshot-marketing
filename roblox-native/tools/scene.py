"""Validate Roblox-native scene specs before they are built into the marketing place.

  python roblox-native/tools/scene.py validate [scene.json ...]   (default: every roblox-native/scenes/**/*.json)
  python roblox-native/tools/scene.py list

Checks structure, references (marks, actors, presets, actions, library entries), timing, and the
same canon rules as runtime/Scene/Canon.luau. make_marketing_place.py refuses to build invalid specs.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENES = ROOT / "scenes"
LIBRARY = json.loads((ROOT / "library" / "library.json").read_text(encoding="utf-8"))

MODES = {"authentic_gameplay", "staged_gameplay", "staged_fiction", "hybrid_bridge"}
MECHANICS = {"real", "none", "fictional"}
OUTCOMES = {"organic", "scripted", "n/a"}
PRESETS = {"static_wide", "two_shot", "orbit_reveal", "dolly_in", "slug_low_angle", "reaction_closeup",
           "follow", "snap_zoom", "whip_pan", "close_up", "push_in", "over_shoulder"}
ACTIONS = {"move_to", "face", "hop", "animate", "express", "look", "blink"}
ACTOR_KINDS = {"standin_humanoid", "standin_slug", "clone", "slug"}
SPECIES = {"Floppy", "Inferno", "Aquabeek", "Rammstone", "Tormato", "BoonDoc", "Phosphoro"}
CHANNELS = {"smile", "angry", "react", "look_up", "squint", "open", "lean"}
REPO = ROOT.parent
SET_KINDS = {"cyc", "place"}
CUE_TYPES = {"vfx", "sound"}
TRANSFORM_ACTIONS = {"transform", "ability", "ability_q", "ability_e"}
NEVER_TRANSFORMS = {"floppy"}


ANCHOR = re.compile(r"^L(\d+)(?:\.(start|end))?\s*([+-]\s*[0-9.]+)?$")


def resolve_anchors(spec, dialogue):
    """Times tied to the dialogue: "L3" / "L3.start+0.2" / "L3.end-0.1" in timeline `time` and in a shot's
    `until` (the shot then lasts until that moment). Returns error strings; resolves in place."""
    errs = []
    lines = {ln["n"]: ln for ln in dialogue["lines"]} if dialogue else {}

    def when(v, where):
        if isinstance(v, (int, float)):
            return float(v)
        m = ANCHOR.match(str(v).strip())
        if not m or int(m.group(1)) not in lines:
            errs.append(f"{where}: can't resolve time {v!r} (dialogue lines: {sorted(lines)})")
            return 0.0
        ln = lines[int(m.group(1))]
        return round(ln[m.group(2) or "start"] + float((m.group(3) or "0").replace(" ", "")), 3)

    for b in spec.get("timeline", []):
        if "time" in b:
            b["time"] = when(b["time"], f"beat {b['time']}")
    start = 0.0
    for i, sh in enumerate(spec.get("shots", []), 1):
        if "until" in sh:
            sh["duration"] = round(when(sh.pop("until"), f"shot {i}") - start, 3)
        start += float(sh.get("duration") or 0)
    return errs


def validate(spec):
    e = []
    for key in ("id", "truth", "set", "marks", "shots"):
        if key not in spec:
            e.append(f"missing '{key}'")
    if e:
        return e
    t = spec["truth"]
    if t.get("mode") not in MODES:
        e.append(f"truth.mode must be one of {sorted(MODES)}")
    if t.get("mode") == "authentic_gameplay":
        e.append("authentic_gameplay is captured from real play; the scene runner only stages scenes")
    if t.get("gameplay_mechanics") not in MECHANICS:
        e.append(f"truth.gameplay_mechanics must be one of {sorted(MECHANICS)}")
    if t.get("match_outcome") not in OUTCOMES:
        e.append(f"truth.match_outcome must be one of {sorted(OUTCOMES)}")
    if t.get("mode") in ("staged_fiction", "hybrid_bridge") and not t.get("label"):
        e.append("fiction needs truth.label (the on-screen disclosure, e.g. 'Fictional story')")
    if t.get("mode") == "staged_gameplay" and t.get("match_outcome") == "organic":
        e.append("staged gameplay has a scripted outcome by definition")
    if spec["set"].get("kind") not in SET_KINDS:
        e.append(f"set.kind must be one of {sorted(SET_KINDS)}")
    marks = spec["marks"]
    actors = spec.get("actors", {})
    for name, a in actors.items():
        if a.get("kind") not in ACTOR_KINDS:
            e.append(f"actor {name}: kind must be one of {sorted(ACTOR_KINDS)}")
        if a.get("kind") == "slug" and a.get("species") not in SPECIES:
            e.append(f"actor {name}: slug needs species, one of {sorted(SPECIES)}")
        if a.get("kind") == "clone" and not a.get("asset"):
            e.append(f"actor {name}: clone needs 'asset' (dotted path to a Model in the place)")
        if a.get("mark") not in marks:
            e.append(f"actor {name}: unknown mark {a.get('mark')}")
        if a.get("face") and a["face"] not in actors and a["face"] not in marks:
            e.append(f"actor {name}: face target {a['face']} is not an actor or mark")
    named = set(actors) | set(marks)
    dialogue = None
    if not spec.get("dialogue"):
        e += resolve_anchors(spec, None)
    if spec.get("dialogue"):
        path = REPO / spec["dialogue"]
        if not path.exists():
            e.append(f"dialogue {spec['dialogue']} not found (run `ss dialogue` first)")
        else:
            dialogue = json.loads(path.read_text(encoding="utf-8"))
            e += resolve_anchors(spec, dialogue)
            for ln in dialogue["lines"]:
                if ln.get("actor") and ln["actor"] not in actors:
                    e.append(f"dialogue line {ln['n']}: speaker's actor '{ln['actor']}' is not in this scene")
    total = 0.0
    for i, s in enumerate(spec["shots"], 1):
        total += float(s.get("duration", 0))
        if s.get("preset") not in PRESETS:
            e.append(f"shot {i}: unknown preset {s.get('preset')}")
        if not s.get("duration") or s["duration"] <= 0:
            e.append(f"shot {i}: needs a positive duration")
        for key in ("target", "from", "to"):
            if key in s and s[key] not in named:
                e.append(f"shot {i}: {key} {s[key]} is not an actor or mark")
        for name in s.get("targets", []):
            if name not in named:
                e.append(f"shot {i}: target {name} is not an actor or mark")
    if dialogue and dialogue["duration"] > total + 0.05:
        e.append(f"shots last {total:.2f}s but the dialogue lasts {dialogue['duration']:.2f}s")
    for b in spec.get("timeline", []):
        where = f"beat at {b.get('time')}s"
        if not isinstance(b.get("time"), (int, float)) or b["time"] < 0:
            e.append(f"{where}: time must be >= 0")
        elif b["time"] > total:
            e.append(f"{where}: after the last shot ends ({total:.2f}s)")
        if "cue" in b:
            c = b["cue"]
            if c.get("type") not in CUE_TYPES:
                e.append(f"{where}: cue type must be one of {sorted(CUE_TYPES)}")
            if c.get("type") == "sound" and c.get("sound") not in LIBRARY["sounds"]:
                e.append(f"{where}: sound {c.get('sound')} is not in library.json")
            if c.get("actor") and c["actor"] not in actors:
                e.append(f"{where}: cue actor {c['actor']} unknown")
            continue
        if "marker" in b:
            continue
        actor = b.get("actor")
        if actor not in actors:
            e.append(f"{where}: unknown actor {actor}")
            continue
        identity = actors[actor].get("identity") or str(actors[actor].get("species", "")).lower() or None
        action = b.get("action")
        if identity in NEVER_TRANSFORMS and (action in TRANSFORM_ACTIONS or any(
                w in str(b.get("animation", "")).lower() for w in ("transform", "ability"))):
            e.append(f"{where}: {identity} never transforms or uses abilities (docs/game-truth.md)")
            continue
        if action not in ACTIONS:
            e.append(f"{where}: unknown action {action}")
        if action == "move_to" and b.get("mark") not in marks:
            e.append(f"{where}: unknown mark {b.get('mark')}")
        if action == "face" and b.get("target") not in named:
            e.append(f"{where}: face target {b.get('target')} unknown")
        if action == "express":
            bad = set(b.get("set", {})) - CHANNELS
            if not b.get("set") or bad:
                e.append(f"{where}: express needs 'set' with channels from {sorted(CHANNELS)}")
        if action == "look" and b.get("target") not in named | {"none", "auto"}:
            e.append(f"{where}: look target {b.get('target')} unknown")
        if action == "animate" and b.get("animation") not in LIBRARY["animations"]:
            e.append(f"{where}: animation {b.get('animation')} is not in library.json")
    return e


def all_specs():
    return sorted(SCENES.rglob("*.json"))


def load_valid():
    """Every spec, validated; raises SystemExit listing problems."""
    specs, problems = [], []
    for path in all_specs():
        spec = json.loads(path.read_text(encoding="utf-8"))
        if spec.get("dialogue") and not (REPO / spec["dialogue"]).exists():
            # dialogue manifests are generated (out/ is not in git): skip the scene rather than block every build
            print(f"skipped {path.relative_to(ROOT)}: {spec['dialogue']} not generated yet (run `ss dialogue`)")
            continue
        errs = validate(spec)
        if spec.get("id") != path.stem:
            errs.append(f"id {spec.get('id')} must match the file name {path.stem}")
        problems += [f"{path.relative_to(ROOT)}: {x}" for x in errs]
        if spec.get("dialogue") and not errs:
            # the runtime reads one timing source: the dialogue manifest, inlined (words dropped; not needed there)
            d = json.loads((REPO / spec["dialogue"]).read_text(encoding="utf-8"))
            spec["_dialogue"] = {"id": d["id"], "duration": d["duration"], "lines": [
                {k: ln[k] for k in ("n", "speaker", "actor", "start", "end", "mouth")} for ln in d["lines"]]}
        specs.append(spec)
    ids = [s.get("id") for s in specs]
    problems += [f"duplicate scene id {i}" for i in set(ids) if ids.count(i) > 1]
    if problems:
        raise SystemExit("invalid scene specs:\n  " + "\n  ".join(problems))
    return specs


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if cmd == "list":
        for p in all_specs():
            s = json.loads(p.read_text(encoding="utf-8"))
            print(f"{s.get('id'):32} {s.get('truth', {}).get('mode', '?'):18} {s.get('note', '')}")
        return
    paths = [Path(p) for p in sys.argv[2:]] or all_specs()
    bad = 0
    for p in paths:
        errs = validate(json.loads(Path(p).read_text(encoding="utf-8")))
        print(("OK   " if not errs else "FAIL ") + str(p))
        for x in errs:
            print("     " + x)
        bad += bool(errs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
