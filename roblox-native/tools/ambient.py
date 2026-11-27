"""Background life for scene specs (owner, 2026-11-27: "the environment should be part of the performance").

A spec may carry an `ambient` block. Before validation, scene.py calls expand(), which turns it into ordinary marks,
actors and timeline beats. Seeded, so every film pass and patch shows the same crowd, and nothing new is needed in the
runtime. The extras are named amb_*.

  "ambient": {
    "seed": 7,
    "clear": ["kai_h", "raf_h"],            marks the extras keep away from (the main characters' spots)
    "clear_radius": 5,
    "avoid": [[x, z], ...],                 extra spots nobody should stand on (2.5 studs)
    "residents": {"near": [0, 0, 0], "radius": 60, "max": 8},   the game's grove slugs, recreated (library/grove.json)
    "groups": [
      {"zone": [x1, z1, x2, z2], "people": 4, "slugs": 3, "activities": ["stroll", "chat", "watch"],
       "focus": "mark", "until": "L5.end+0.2"},
      {"activities": ["ring"], "focus": "duel_c", "people": 10, "slugs": 3, "radius": 9, "open": [150, 210]}
    ],
    "reactions": [
      {"at": "L7.start+0.1", "kind": "cheer", "focus": "raf"},
      {"at": 12.4, "kind": "scatter", "focus": "duel_c", "who": "people"}
    ]
  }

Which crowd fits is the scene's call (owner, 2026-11-27): two people talking get a busy hangout all around them
(stroll, chat, watch); a duel gets either nobody, a ring of watchers (`ring`, facing the focus, with an `open` arc in
degrees where the camera looks in), or people who scatter when it starts (a `scatter` reaction).

People: generic players in the extras wardrobe (library.json extras_wardrobe: shirt, trousers and hair on everyone,
never a named cast outfit). A stroller walks between points and pauses, chatters pair up facing each other (talking
hands, laughs, nods), watchers face the focus and cheer, point or applaud now and then, ring watchers stand around the
focus. Slugs roam in short, even hops (one per 1.6 studs, so they never race), rest, look around and perk up.

Reactions (cheer, gasp, flinch, point, laugh, turn, scatter) reach everyone in `who` (all, people, slugs) as one crowd:
nearest first but close together (shock within about 0.3 s), faces to match, turned to the focus. Each holds until
`until` (a line anchor: the end of the beat that caused it), else for `hold` seconds, else until the next reaction;
scatter is for good. Anchor `at` and `until` to the script line so the crowd reacts to what's on screen.

Floors: every spot and every walk is checked against the saved floor map of that place (tools/floormap.py), so nobody
stands in a crack or walks through a pit (owner, 2026-11-27: people "sunken into the ground", "stuck in the cracks").
"""
import json
import math
import random
from pathlib import Path

import floormap

ROOT = Path(__file__).resolve().parent.parent
SPECIES = ["Floppy", "Inferno", "Aquabeek", "Rammstone", "Tormato", "BoonDoc", "Phosphoro"]
SKINS = [[234, 184, 146], [224, 172, 132], [196, 140, 104], [141, 96, 70], [246, 205, 170], [120, 82, 60]]
HOP_STRIDE, HOP_AIR, HOP_GAP = 1.6, 0.42, 0.18      # a background slug's hop: studs per hop, seconds up, seconds down
WALK_SPEED, RUN_SPEED = 4.2, 9.0                     # studs per second
# Room around everyone (owner, 2026-11-27: crowds "too cramped ... squished and mushed together", even busy ones).
# Centre-to-centre studs between standing spots; a zone that can't fit everyone at this spacing gets fewer extras.
PERSON_GAP, SLUG_GAP = 4.0, 2.5
REACT_MOVES = {"cheer": ["cheer", "applaud"], "gasp": ["disbelief", "hands_up"], "flinch": ["flinch", "cower"],
               "point": ["point_emote"], "laugh": ["laugh"], "turn": ["think", "tilt"], "scatter": []}
SLUG_REACT = {"cheer": {"smile": 1}, "gasp": {"react": 1}, "flinch": {"react": 1}, "point": {"react": 1},
              "laugh": {"smile": 1}, "turn": {"react": 0.6}, "scatter": {"react": 1}}
# The whole crowd reads as one reaction (owner, 2026-11-27: never "parts of the crowd looking shocked ... whilst the
# rest just look normal"). Faces match the move; shock lands almost together, a cheer ripples a little.
PERSON_FACE = {"cheer": {"smile": 1, "open": 0.4}, "gasp": {"open": 0.8, "smile": 0}, "flinch": {"open": 0.6, "smile": 0},
               "point": {"open": 0.3}, "laugh": {"smile": 1, "open": 0.5}, "turn": {"smile": 0}, "scatter": {"open": 0.8, "smile": 0}}
SPREAD = {"gasp": 0.12, "flinch": 0.1, "scatter": 0.15, "turn": 0.2, "point": 0.25, "cheer": 0.3, "laugh": 0.3}


def _library():
    return json.loads((ROOT / "library" / "library.json").read_text(encoding="utf-8"))


def _grove():
    path = ROOT / "library" / "grove.json"
    return json.loads(path.read_text(encoding="utf-8"))["slugs"] if path.exists() else []


def _look(rng, wardrobe):
    skin = rng.choice(SKINS)
    return {"skin": skin, "colors": {"Torso": skin, "LeftArm": skin, "RightArm": skin, "LeftLeg": skin, "RightLeg": skin},
            "shirt": rng.choice(wardrobe["shirts"]), "pants": rng.choice(wardrobe["pants"]),
            "hair": [rng.choice(wardrobe["hair"])], "face_style": rng.choice(["boy", "girl"])}


class World:
    """Spec <-> world coordinates (marks are relative to set.origin, turned by set.yaw) and the floor checks."""

    def __init__(self, spec, clears, r, avoid):
        st = spec.get("set", {})
        self.o = st.get("origin", [0, 0, 0])
        self.yaw = math.radians(st.get("yaw", 0))
        self.place = st.get("kind") == "place"
        self.clears, self.r, self.avoid = clears, r, avoid
        self.taken = []   # (x, z, gap): where someone stands, so nobody else stops on top of them

    def to_world(self, p):
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return self.o[0] + c * p[0] + s * p[2], self.o[2] - s * p[0] + c * p[2]

    def to_spec(self, world):
        dx, dy, dz = world[0] - self.o[0], world[1] - self.o[1], world[2] - self.o[2]
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return [round(c * dx - s * dz, 2), round(dy, 2), round(s * dx + c * dz, 2)]

    def ok(self, p, gap=0.0):
        if not all(math.hypot(p[0] - t[0], p[2] - t[1]) >= max(gap, t[2]) for t in self.taken):
            return False
        if not all(math.hypot(p[0] - c[0], p[2] - c[2]) >= self.r for c in self.clears):
            return False
        if not all(math.hypot(p[0] - a[0], p[2] - a[1]) >= 2.5 for a in self.avoid):
            return False
        return not self.place or floormap.standable(*self.to_world(p))

    def walk_ok(self, a, b):
        return not self.place or floormap.walkable(self.to_world(a), self.to_world(b))

    def take(self, p, gap):
        self.taken.append((p[0], p[2], gap))

    def point(self, rng, zone, y=0.0, near=None, reach=None, tries=60, gap=0.0):
        """A free, standable spot in the zone (and within `reach` of `near`, reachable on foot from it)."""
        x1, z1, x2, z2 = zone
        for _ in range(tries):
            if near is not None and reach:
                ang, d = rng.uniform(0, math.tau), rng.uniform(reach * 0.4, reach)
                p = [round(near[0] + d * math.cos(ang), 2), y, round(near[2] + d * math.sin(ang), 2)]
                if not (min(x1, x2) <= p[0] <= max(x1, x2) and min(z1, z2) <= p[2] <= max(z1, z2)):
                    continue
            else:
                p = [round(rng.uniform(min(x1, x2), max(x1, x2)), 2), y, round(rng.uniform(min(z1, z2), max(z1, z2)), 2)]
            if self.ok(p, gap) and (near is None or self.walk_ok(near, p)):
                return p
        return None


def expand(spec, duration):
    amb = spec.pop("ambient", None)
    if not amb:
        return spec
    rng = random.Random(amb.get("seed", 1))
    marks, actors, timeline = spec.setdefault("marks", {}), spec.setdefault("actors", {}), spec.setdefault("timeline", [])
    wardrobe = _library()["extras_wardrobe"]
    clears = [marks[m] for m in amb.get("clear", []) if m in marks]
    world = World(spec, clears, float(amb.get("clear_radius", 5)), [tuple(a) for a in amb.get("avoid", [])])
    n = {"p": 0, "s": 0, "m": 0}
    beats = {}        # actor -> its beats, filtered for reactions at the end
    roles = {}        # actor -> "person" | "slug"
    homes = {}        # actor -> where it stands (spec coords), for reaction order and scatter
    faces = {}        # actor -> what it faced before a reaction (to turn back)

    def mark(p, yaw=0):
        n["m"] += 1
        name = f"amb_m{n['m']}"
        marks[name] = [p[0], p[1], p[2], round(yaw, 1)]
        return name

    def beat(t, actor, action, **kw):
        if t < duration - 0.3:
            beats.setdefault(actor, []).append({"time": round(t, 3), "actor": actor, "action": action, **kw})

    def person(p, yaw):
        n["p"] += 1
        name = f"amb_p{n['p']}"
        actors[name] = {"kind": "human", "look": _look(rng, wardrobe), "mark": mark(p, yaw),
                        "auto_look": False, "phase": round(rng.uniform(0, 5), 2)}  # no blaster key: "false" = holstered
        roles[name], homes[name] = "person", p
        return name

    def slug(p, yaw, species=None, scale=None):
        n["s"] += 1
        name = f"amb_s{n['s']}"
        actors[name] = {"kind": "slug", "species": species or rng.choice(SPECIES), "mark": mark(p, yaw),
                        "scale": scale or round(rng.uniform(0.6, 0.85), 2), "auto_look": False,
                        "phase": round(rng.uniform(0, 5), 2)}
        roles[name], homes[name] = "slug", p
        return name

    def focus_pos(name):
        if name in marks:
            return marks[name]
        if name in actors:
            return marks[actors[name]["mark"]]
        return None

    for g in amb.get("groups", []):
        stop = float(g["until"]) if isinstance(g.get("until"), (int, float)) else duration
        focus = g.get("focus")
        acts = g.get("activities", ["stroll"])
        if acts == ["ring"]:
            _ring(rng, g, world, focus, focus_pos(focus), stop, person, slug, beat, faces)
            continue
        zone = g["zone"]
        roles_wanted = [acts[i % len(acts)] for i in range(int(g.get("people", 0)))]
        if roles_wanted.count("chat") % 2:
            roles_wanted[len(roles_wanted) - 1 - roles_wanted[::-1].index("chat")] = "stroll" if "stroll" in acts else "watch"
        for _ in range(roles_wanted.count("chat") // 2):
            _chat(rng, zone, world, stop, person, actors, homes, faces, mark, beat)
        for role in (r for r in roles_wanted if r != "chat"):
            p = world.point(rng, zone, gap=PERSON_GAP)
            if not p:
                continue
            name = person(p, rng.uniform(0, 360))
            world.take(p, PERSON_GAP)
            if role == "watch":
                if focus:
                    actors[name]["face"] = faces[name] = focus
                t = rng.uniform(1, 4)
                while t < stop:
                    beat(t, name, "gesture", move=rng.choice(["cheer", "applaud", "point_emote", "nod", "think"]), mask="upper")
                    t += rng.uniform(3, 7)
            else:
                _stroll(rng, name, p, zone, world, stop, mark, beat)
        for _ in range(int(g.get("slugs", 0))):
            p = world.point(rng, zone, gap=SLUG_GAP)
            if p:
                world.take(p, SLUG_GAP)
                _slug_life(rng, slug(p, rng.uniform(0, 360)), p, zone, world, stop, mark, beat)

    res = amb.get("residents")
    if res:
        near, radius = res.get("near", [0, 0, 0]), float(res.get("radius", 60))
        spots = [(s, world.to_spec(s["at"]), s.get("yaw", 0) - spec.get("set", {}).get("yaw", 0)) for s in _grove()]
        spots = [x for x in spots if math.hypot(x[1][0] - near[0], x[1][2] - near[2]) <= radius]
        rng.shuffle(spots)
        for s, here, yaw in spots[: int(res.get("max", 8))]:
            if not all(math.hypot(here[0] - c[0], here[2] - c[2]) >= world.r for c in clears):
                continue
            name = slug(here, yaw, s["species"], s.get("scale", 0.8))
            zone = [here[0] - 3, here[2] - 3, here[0] + 3, here[2] + 3]
            _slug_life(rng, name, here, zone, world, duration, mark, beat, home_only=True)

    _react(rng, amb.get("reactions", []), roles, homes, faces, beats, focus_pos, world, duration, mark)
    for name in sorted(beats):
        timeline.extend(sorted(beats[name], key=lambda b: b["time"]))
    return spec


def _chat(rng, zone, world, stop, person, actors, homes, faces, mark, beat):
    """Two people facing each other, about 3.8 studs apart, with room around the pair."""
    for _ in range(40):
        mid = world.point(rng, zone, gap=PERSON_GAP + 1.9)
        if not mid:
            return
        ang = rng.uniform(0, math.tau)
        pa = [round(mid[0] + 1.9 * math.cos(ang), 2), 0, round(mid[2] + 1.9 * math.sin(ang), 2)]
        pb = [round(mid[0] - 1.9 * math.cos(ang), 2), 0, round(mid[2] - 1.9 * math.sin(ang), 2)]
        if world.ok(pa, PERSON_GAP) and world.ok(pb, PERSON_GAP):
            break
    else:
        return
    centre = mark(mid)
    a, b = person(pa, 0), person(pb, 0)
    for who, p in ((a, pa), (b, pb)):
        world.take(p, PERSON_GAP)
        actors[who]["face"] = faces[who] = centre
    t, speaker = rng.uniform(0, 1.5), rng.choice([a, b])
    while t < stop:
        other = b if speaker == a else a
        d = rng.uniform(1.6, 3.2)
        beat(t, speaker, "gesture", move=rng.choice(["explain", "explain", "point_emote", "shrug"]), mask="upper", duration=round(d, 2))
        beat(t, speaker, "express", set={"smile": round(rng.uniform(0.2, 0.9), 2)}, ease=0.3)
        if rng.random() < 0.45:
            beat(t + d * 0.6, other, "gesture", move=rng.choice(["laugh", "nod", "agree"]), mask="upper")
            beat(t + d * 0.6, other, "express", set={"smile": 1}, ease=0.25)
        t += d + rng.uniform(0.2, 0.8)
        speaker = other


def _stroll(rng, name, here, zone, world, stop, mark, beat):
    t = rng.uniform(0, 2)
    while t < stop - 1:
        nxt = world.point(rng, zone, near=here, reach=12, gap=PERSON_GAP)
        if not nxt:
            break
        dur = max(1.2, math.hypot(nxt[0] - here[0], nxt[2] - here[2]) / WALK_SPEED)
        if t + dur > stop:
            break
        beat(t, name, "move_to", mark=mark(nxt), gait="walk", duration=round(dur, 2))
        here = nxt
        t += dur
        if rng.random() < 0.5:
            beat(t + 0.3, name, "gesture", move=rng.choice(["wave", "think", "shrug", "nod"]), mask="upper")
        t += rng.uniform(1.5, 4.5)


def _ring(rng, g, world, focus, centre, stop, person, slug, beat, faces):
    """Watchers around a fight: evenly round the focus (skipping the `open` arc and any unstandable spot), facing in."""
    if centre is None:
        return
    radius, count = float(g.get("radius", 9)), int(g.get("people", 8))
    lo, hi = g.get("open", [0, 0])

    def opened(a):  # the arc left free for the camera, in degrees (0 = +z from the focus); it may wrap past 360
        a %= 360
        return lo <= a <= hi if lo <= hi else (a >= lo or a <= hi)

    angles = [a for a in (360 * k / max(count * 2, 1) + rng.uniform(-6, 6) for k in range(count * 2)) if not opened(a)]
    rng.shuffle(angles)
    placed = 0
    for a in sorted(angles[: count * 2]):
        if placed >= count:
            break
        r = radius + rng.uniform(-0.8, 0.8)
        p = [round(centre[0] + r * math.sin(math.radians(a)), 2), 0, round(centre[2] + r * math.cos(math.radians(a)), 2)]
        if not world.ok(p, PERSON_GAP - 0.8):   # shoulder to shoulder round a fight, but not overlapping
            continue
        name = person(p, a + 180)
        world.take(p, PERSON_GAP - 0.8)
        faces[name] = focus
        placed += 1
        beat(0, name, "face", target=focus, duration=0.05)
        t = rng.uniform(0.5, 3)
        while t < stop:
            beat(t, name, "gesture", move=rng.choice(["cheer", "applaud", "point_emote", "nod", "arms_crossed"]), mask="upper")
            t += rng.uniform(2.5, 6)
    for _ in range(int(g.get("slugs", 0))):
        a = rng.uniform(0, 360)
        if opened(a):
            continue
        r = radius - 1.5
        p = [round(centre[0] + r * math.sin(math.radians(a)), 2), 0, round(centre[2] + r * math.cos(math.radians(a)), 2)]
        if world.ok(p, SLUG_GAP):
            world.take(p, SLUG_GAP)
            name = slug(p, a + 180)
            faces[name] = focus
            beat(0.2, name, "look", target=focus)


def _slug_life(rng, name, here, zone, world, stop, mark, beat, home_only=False):
    """A background slug: rests, looks about, hops a little way in even hops, perks up now and then."""
    t = rng.uniform(0, 2)
    home = here
    while t < stop - 1:
        roll = rng.random()
        if roll < 0.35:
            nxt = world.point(rng, zone, y=here[1], near=here, reach=4, gap=SLUG_GAP) if not home_only else \
                [round(home[0] + rng.uniform(-2, 2), 2), home[1], round(home[2] + rng.uniform(-2, 2), 2)]
            if nxt:
                hops = max(1, round(math.hypot(nxt[0] - here[0], nxt[2] - here[2]) / HOP_STRIDE))
                beat(t, name, "move_to", mark=mark(nxt), gait="hop", hops=hops, height=0.3, hop_time=HOP_AIR, gap=HOP_GAP)
                here = nxt
                t += hops * (HOP_AIR + HOP_GAP)
        elif roll < 0.6:
            beat(t, name, "look", target=mark([here[0] + rng.uniform(-6, 6), here[1] + 1, here[2] + rng.uniform(-6, 6)]))
            t += rng.uniform(1.5, 3)
        elif roll < 0.75:
            beat(t, name, "hop", height=round(rng.uniform(0.2, 0.4), 2), duration=HOP_AIR)
            t += 1.4
        elif roll < 0.88:
            beat(t, name, "express", set={"react": 1}, ease=0.3)
            beat(t + 1.6, name, "express", set={"react": 0}, ease=0.5)
            t += 2.4
        else:
            beat(t, name, "look", target="none")
            t += rng.uniform(2, 4)
        t += rng.uniform(0.3, 1.2)


def _react(rng, reactions, roles, homes, faces, beats, focus_pos, world, duration, mark):
    """Crowd reactions on story beats: staggered nearest-first, interrupting each extra's own activity."""
    busy = {}   # actor -> [(from, to)] when its own activity is suspended
    for r in sorted(reactions, key=lambda r: float(r["at"])):
        at, kind, focus = float(r["at"]), r.get("kind", "turn"), r.get("focus")
        assert kind in REACT_MOVES, f"ambient reaction kind {kind} is not one of {sorted(REACT_MOVES)}"
        fp = focus_pos(focus)
        who = r.get("who", "all")
        later = [float(x["at"]) for x in reactions if float(x["at"]) > at]
        if isinstance(r.get("until"), (int, float)):
            settle = float(r["until"])
        elif "hold" in r:
            settle = at + float(r["hold"])
        else:
            settle = min(later) if later else at + 4.0
        for name in sorted(roles):
            if who not in ("all", roles[name] + "s"):
                continue
            here = homes[name]
            dist = math.hypot(here[0] - fp[0], here[2] - fp[2]) if fp else 0
            t = at + min(0.3, dist * 0.02) + rng.uniform(0, float(r.get("spread", SPREAD[kind])))
            if t >= duration - 0.3:
                continue
            end = duration if kind == "scatter" else max(settle, t + 1.2)
            window = (t - 0.05, end)
            busy.setdefault(name, []).append(window)
            react = []
            if roles[name] == "person":
                react.append({"time": t, "action": "face", "target": focus, "duration": 0.3})
                react.append({"time": t, "action": "express", "set": PERSON_FACE[kind], "ease": 0.15})
                if kind == "scatter":
                    react += _flee(rng, here, fp, t, world, mark)
                else:
                    # one move for the whole crowd (a second for variety only where both read the same)
                    move = REACT_MOVES[kind][0] if rng.random() < 0.7 else rng.choice(REACT_MOVES[kind])
                    react.append({"time": t + 0.1, "action": "gesture", "move": move, "mask": "upper",
                                  "duration": round(max(1.0, end - t - 0.2), 2)})
                    if end < duration - 0.5:
                        react.append({"time": end, "action": "express", "set": {"open": 0, "smile": 0.2}, "ease": 0.5})
                        if faces.get(name):
                            react.append({"time": end, "action": "face", "target": faces[name], "duration": 0.5})
            else:
                react.append({"time": t, "action": "look", "target": focus})
                react.append({"time": t, "action": "express", "set": SLUG_REACT[kind], "ease": 0.2})
                react.append({"time": t + 0.05, "action": "hop", "height": 0.35, "duration": HOP_AIR})
                if kind == "scatter" and fp:
                    react += _flee(rng, here, fp, t + 0.5, world, mark, hop=True)
                elif end < duration - 0.5:
                    react.append({"time": end, "action": "express", "set": {k: 0 for k in SLUG_REACT[kind]}, "ease": 0.6})
            react = [{"time": round(b.pop("time"), 3), "actor": name, **b, "_reaction": True}
                     for b in react if b["time"] < duration - 0.3]
            own = beats.setdefault(name, [])
            beats[name] = [b for b in own if not window[0] <= b["time"] < window[1]] + react
    for name, own in beats.items():
        keep = []
        for b in own:
            if b.pop("_reaction", False):
                keep.append(b)
                continue
            # a move of its own still under way when a reaction starts would carry the extra back into its routine
            if b.get("action") == "move_to" and any(b["time"] < lo < b["time"] + float(b.get("duration") or 2)
                                                    for lo, hi in busy.get(name, [])):
                continue
            keep.append(b)
        beats[name] = keep


def _flee(rng, here, fp, t, world, mark, hop=False):
    """Run (or hop) away from the focus to a standable spot 8-14 studs further out."""
    away = math.atan2(here[2] - fp[2], here[0] - fp[0]) if fp else rng.uniform(0, math.tau)
    for _ in range(40):
        ang = away + rng.uniform(-0.6, 0.6)
        d = rng.uniform(8, 14)
        p = [round(here[0] + d * math.cos(ang), 2), here[1], round(here[2] + d * math.sin(ang), 2)]
        if world.ok(p) and world.walk_ok(here, p):
            if hop:
                return [{"time": t, "action": "move_to", "mark": mark(p), "gait": "hop", "hops": max(1, round(d / HOP_STRIDE)),
                         "height": 0.3, "hop_time": HOP_AIR, "gap": HOP_GAP}]
            return [{"time": t + 0.2, "action": "move_to", "mark": mark(p), "gait": "run",
                     "duration": round(max(1.0, d / RUN_SPEED), 2)}]
    return []
