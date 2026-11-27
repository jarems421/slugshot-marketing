"""Acting pass for the named cast (owner, 2026-11-27: "more nuanced body language, interruptions and character-specific
mannerisms"). scene.py runs it after the ambient block, so it fills in what the director didn't write:

  1. a baseline face and posture per character, and slow posture shifts so nobody stands frozen;
  2. idle mannerisms in the gaps (each character's own moves at their own rate; arms-folded characters rest that way);
  3. listening: nods on the speaker's longest words, and an in-character reaction when someone else finishes a line;
  4. interruptions: when a line starts before the previous one ends, the cut-off speaker stops short, mouth open, and
     looks round; the interrupter leans in and points.

Profiles come from each human's `mannerisms` in library.json (from the cast personas in config/cast.json). Authored
beats always win: nothing is added on top of a gesture, aim, point, hold or shoot the spec already has, and a channel
the spec sets itself keeps the spec's values. Seeded per scene, so every pass of a take is identical.
Opt out per scene with "acting": false, or per actor with "acting": false in the actor.
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUSY = {"gesture", "aim", "point", "shoot", "hold", "equip", "holster"}
CLIP = 1.6           # seconds assumed for a gesture without a duration (most authored clips are 0.8-1.8 s)


def _library():
    return json.loads((ROOT / "library" / "library.json").read_text(encoding="utf-8"))


def _pick(rng, weighted):
    total = sum(w for _, w in weighted)
    r = rng.uniform(0, total)
    for move, w in weighted:
        r -= w
        if r <= 0:
            return move
    return weighted[-1][0]


class Busy:
    """When an actor's body is already spoken for (authored beats, then what this pass adds)."""

    def __init__(self, beats):
        self.spans = sorted((b["time"], b["time"] + float(b.get("duration") or CLIP)) for b in beats)

    def free(self, t, d):
        return all(e <= t - 0.15 or s >= t + d + 0.15 for s, e in self.spans)

    def add(self, t, d):
        self.spans.append((t, t + d))

    def gaps(self, start, end, least):
        cur = start
        for s, e in sorted(self.spans) + [(end, end)]:
            if s - cur >= least:
                yield cur, min(s, end)
            cur = max(cur, e)
            if cur >= end:
                break


def expand(spec, duration, dialogue=None, words=None):
    if spec.get("acting") is False:
        return spec
    lib = _library()
    humans = lib.get("humans", {})
    actors = spec.get("actors", {})
    timeline = spec.setdefault("timeline", [])
    rng = random.Random(f"{spec.get('id')}-acting")
    cast = {}
    for name, a in actors.items():
        if name.startswith("amb_") or a.get("acting") is False:
            continue
        if a.get("kind") == "human" and humans.get(a.get("human", ""), {}).get("mannerisms"):
            cast[name] = humans[a["human"]]["mannerisms"]
    if not cast:
        return spec
    lines = (dialogue or {}).get("lines", [])
    added = []
    loops = {k for k, v in lib.get("human_moves", {}).items() if v.get("loop")}

    def beat(t, actor, action, **kw):
        if action == "gesture" and kw.get("move") in loops and "duration" not in kw:
            kw["duration"] = CLIP   # a looping clip runs until told to stop
        if 0 <= t < duration - 0.3:
            added.append({"time": round(t, 3), "actor": actor, "action": action, **kw})

    for name, prof in cast.items():
        mine = [b for b in timeline if b.get("actor") == name]
        busy = Busy([b for b in mine if b.get("action") in BUSY and isinstance(b.get("time"), (int, float))])
        set_channels = {k for b in mine if b.get("action") == "express" for k in b.get("set", {})}
        own = [(ln["start"], ln["end"]) for ln in lines if ln.get("actor") == name]
        # 1. baseline face and posture; slow posture shifts
        base = {k: v for k, v in prof.get("base", {}).items() if k not in set_channels}
        if base:
            beat(0.0, name, "express", set=base, ease=0.4)
        if "lean" not in set_channels and prof.get("sway", 0.1) > 0:
            t, lean0 = rng.uniform(2, 4), prof.get("base", {}).get("lean", 0.0)
            while t < duration - 1:
                beat(t, name, "express", set={"lean": round(lean0 + rng.uniform(-1, 1) * prof.get("sway", 0.1), 3)}, ease=1.2)
                t += rng.uniform(4, 8)
        # 3. listening (before idle, so reactions to the dialogue take their place first)
        for i, ln in enumerate(lines):
            if ln.get("actor") == name or not ln.get("actor"):
                continue
            ws = [w for w in (words or []) if ln["start"] - 0.01 <= w["startMs"] / 1000 < ln["end"]]
            ws.sort(key=lambda w: (len(w["text"].strip(" ,.!?")), -w["startMs"]), reverse=True)
            for w in ws[:max(1, int((ln["end"] - ln["start"]) / 3))]:
                t = w["startMs"] / 1000
                if rng.random() < prof.get("listen_rate", 0.5) and busy.free(t, 0.8):
                    beat(t, name, "gesture", move=_pick(rng, prof.get("listen", [["nod", 1]])), mask="head")
                    busy.add(t, 0.8)
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            t = ln["end"] + 0.12
            if prof.get("after") and rng.random() < prof.get("after_rate", 0.5) and busy.free(t, 1.4) \
                    and not (nxt and nxt.get("actor") == name and nxt["start"] < t + 0.6):
                move = _pick(rng, prof["after"])
                beat(t, name, "gesture", move=move, mask="upper")
                face = prof.get("after_face")
                if face and not set(face) & set_channels:
                    beat(t, name, "express", set=face, ease=0.25)
                    beat(t + 1.6, name, "express", set={k: prof.get("base", {}).get(k, 0) for k in face}, ease=0.6)
                busy.add(t, 1.4)
        # 4. interruptions
        for prev, cur in zip(lines, lines[1:]):
            if cur["start"] >= prev["end"] - 0.05 or not prev.get("actor") or not cur.get("actor"):
                continue
            t = cur["start"]
            if prev["actor"] == name:
                beat(t, name, "express", set={"open": 0.7}, ease=0.1)
                beat(t + 0.9, name, "express", set={"open": 0}, ease=0.4)
                beat(t, name, "look", target=cur["actor"])
            elif cur["actor"] == name and busy.free(t - 0.1, 1.2):
                beat(t - 0.1, name, "express", set={"lean": round(prof.get("base", {}).get("lean", 0) + 0.25, 3)}, ease=0.15)
                beat(t, name, "gesture", move="point_emote", mask="upper")
                busy.add(t - 0.1, 1.2)
        # 2. idle mannerisms in the gaps (talking characters gesture on their own longer lines too)
        for s, e in own:
            if e - s >= 2.2 and busy.free(s + 0.25, CLIP) and rng.random() < prof.get("talk_rate", 0.6):
                beat(s + 0.25, name, "gesture", move=_pick(rng, prof.get("talk", prof.get("idle", [["explain", 1]]))), mask="upper")
                busy.add(s + 0.25, CLIP)
        lo, hi = prof.get("gap", [3.5, 7.0])
        rest = prof.get("rest")
        for s, e in list(busy.gaps(0.3, duration - 0.5, 2.5)):
            if rest:
                beat(s + 0.2, name, "gesture", move=rest, mask="arms", duration=round(e - s - 0.4, 2))
                continue
            t = s + rng.uniform(0.3, lo / 2)
            while t + CLIP < e:
                beat(t, name, "gesture", move=_pick(rng, prof["idle"]), mask=prof.get("idle_mask", "upper"))
                t += CLIP + rng.uniform(lo, hi)
    timeline.extend(sorted(added, key=lambda b: b["time"]))
    return spec
