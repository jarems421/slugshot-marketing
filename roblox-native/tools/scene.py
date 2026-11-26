"""Validate Roblox-native scene specs before they are built into the marketing place.

  python roblox-native/tools/scene.py validate [scene.json ...]   (default: every roblox-native/scenes/**/*.json)
  python roblox-native/tools/scene.py list
  python roblox-native/tools/scene.py json ID                    one validated spec as the runtime reads it (rehearsals)

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
           "follow", "snap_zoom", "whip_pan", "close_up", "push_in", "over_shoulder", "slug_shot", "slug_cam", "split"}
FX = {"flash", "shake"}
CLOCKS = {"scene", "output"}
ACTIONS = {"move_to", "face", "hop", "animate", "express", "look", "blink",
           "gesture", "aim", "point", "shoot", "hold", "equip", "holster"}
ACTOR_KINDS = {"standin_humanoid", "standin_slug", "clone", "slug", "human"}
# Human actors (runtime/Scene/Humans.luau): what only they do, how they travel, and how they hold a slug.
HUMAN_ACTIONS = {"gesture", "aim", "point", "shoot", "hold", "equip", "holster"}
GAITS = {"walk", "run", "sprint", "back"}
HANDS = {"right", "left", "shoulder", "shoulder_left"}  # one hand or a shoulder (owner, 2026-11-26)
SPECIES = {"Floppy", "Inferno", "Aquabeek", "Rammstone", "Tormato", "BoonDoc", "Phosphoro"}
CHANNELS = {"smile", "angry", "react", "look_up", "squint", "open", "lean", "smirk"}  # smirk: humans' painted faces
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
    for i, w in enumerate(spec.get("slowmo", []), 1):
        for key in ("from", "until"):
            if key in w:
                w[key] = when(w[key], f"slowmo {i}")
    for f in spec.get("fx", []):
        if "at" in f:
            f["at"] = when(f["at"], f"fx {f.get('type')}")
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
        if a.get("kind") == "human" and a.get("human") not in LIBRARY.get("humans", {}) and not isinstance(a.get("look"), dict):
            e.append(f"actor {name}: human needs 'human' (one of {sorted(LIBRARY.get('humans', {}))}) or a 'look'")
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
    for i, s in enumerate(spec["shots"], 1):
        if s.get("clock", "scene") not in CLOCKS:
            e.append(f"shot {i}: clock is 'scene' or 'output'")
        if s.get("preset") == "split":
            views = s.get("views")
            if not isinstance(views, list) or len(views) != 2:
                e.append(f"shot {i}: split needs two views (top, bottom)")
                continue
            for k, v in enumerate(views, 1):
                if v.get("preset") not in PRESETS - {"split"}:
                    e.append(f"shot {i} view {k}: unknown preset {v.get('preset')}")
                if "until" in v or "duration" in v:
                    e.append(f"shot {i} view {k}: views last as long as their split shot")
                for key in ("target", "from", "to"):
                    if key in v and v[key] not in named:
                        e.append(f"shot {i} view {k}: {key} {v[key]} is not an actor or mark")
        if s.get("preset") in ("slug_cam", "slug_shot") and s.get("target") not in actors:
            e.append(f"shot {i}: {s.get('preset')} target is the shooter (a human actor)")
    words = []
    if spec.get("dialogue"):
        wp = (REPO / spec["dialogue"]).with_name("dialogue.words.json")
        if wp.exists():
            words = json.loads(wp.read_text(encoding="utf-8"))
    for i, w in enumerate(spec.get("slowmo", []), 1):
        a, b, rate = w.get("from"), w.get("until"), w.get("rate")
        if not all(isinstance(x, (int, float)) for x in (a, b, rate)) or not (0 < a < b) or not (0.02 <= rate < 1):
            e.append(f"slowmo {i}: needs from < until (seconds or line anchors) and 0.02 <= rate < 1")
            continue
        # The edit lengthens the video by inserting silence; a spoken word inside the segment would be cut.
        spoken = [x["text"].strip() for x in words if x["startMs"] / 1000 < b and x["endMs"] / 1000 > a]
        if spoken:
            e.append(f"slowmo {i}: {a}-{b}s overlaps spoken words {spoken}; slow motion goes in a dialogue gap")
    for f in spec.get("fx", []):
        if f.get("type") not in FX or not isinstance(f.get("at"), (int, float)):
            e.append(f"fx: type one of {sorted(FX)} with an 'at' time")
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
        if "duration" in b and (not isinstance(b["duration"], (int, float)) or b["duration"] <= 0):
            e.append(f"{where}: duration must be a positive number of seconds (anchors work for `time` only)")
        human = actors[actor].get("kind") == "human"
        if action in HUMAN_ACTIONS and not human:
            e.append(f"{where}: {action} is for human actors")
        slug = actors[actor].get("kind") == "slug"
        if action == "move_to" and "gait" in b and not (human and b["gait"] in GAITS or slug and b["gait"] == "hop"):
            e.append(f"{where}: gait is {sorted(GAITS)} for humans or hop for slugs")
        if action == "move_to" and b.get("gait") == "hop" and "duration" in b:
            e.append(f"{where}: a hopping move's length comes from hops, hop_time and gap, not duration")
        if action == "gesture":
            move = LIBRARY.get("human_moves", {}).get(b.get("move"))
            if not move:
                e.append(f"{where}: gesture move {b.get('move')} is not in library.json human_moves")
            elif move.get("loop") and not b.get("duration"):
                e.append(f"{where}: {b['move']} loops, so the gesture needs a duration")
        if action in ("aim", "point") and b.get("target") not in named:
            e.append(f"{where}: {action} target {b.get('target')} unknown")
        if action in ("shoot", "equip", "holster", "aim") and human and actors[actor].get("blaster") is None:
            e.append(f"{where}: {action} needs the actor to carry a blaster (\"blaster\": true or false = holstered)")
        if action == "shoot" and b.get("slug"):
            if b["slug"] not in SPECIES:
                e.append(f"{where}: shoot slug must be one of {sorted(SPECIES)}")
            if b.get("target") not in named:
                e.append(f"{where}: a slug shot needs a target (actor or mark)")
        if action == "hold":
            item = actors.get(b.get("item"), {})
            if not item or item.get("kind") == "human":
                e.append(f"{where}: hold needs 'item', a slug or prop actor in this scene")
            if not b.get("duration") or b["duration"] <= 0:
                e.append(f"{where}: hold needs a positive duration")
            if b.get("hand", "right") not in HANDS or b.get("facing", "holder") not in ("holder", "out"):
                e.append(f"{where}: hold hand is one of {sorted(HANDS)}, facing 'holder' or 'out'")
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
    if cmd == "json":
        # one validated spec as the runtime reads it, for a rehearsal without a rebuild (Scene.load)
        spec = next((s for s in load_valid() if s["id"] == sys.argv[2]), None)
        if not spec:
            raise SystemExit(f"no valid scene {sys.argv[2]}")
        print(json.dumps(spec))
        return
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
