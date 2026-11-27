"""Builds roblox-native/scenes/imw/most_feared_slug_v02.json (pilot 01, V02 after the owner's review).
  python roblox-native/scenes/imw/build_most_feared_slug_v02.py
Times anchor to out/dialogue/most-feared-slug-v02. Act 1 hub plaza, act 2 training arena, act 3 hub (sets.md).
Owner rules (directing.md section 8): wider by default, establish before cutting in, split-screen duel, show every loss,
speaker on screen, Floppy's lines into the lens, no extras without a job."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
T, S = [], []


def b(time, actor, action, **kw):
    T.append({"time": time, "actor": actor, "action": action, **kw})


def shot(preset, until, **kw):
    S.append({"preset": preset, "until": until, **kw})


def cu(target, until, size, side=20, fov=36, headroom=0.1, **kw):
    shot("close_up", until, target=target, size=size, side=side, fov=fov, headroom=headroom, **kw)


def early(time, by=0.05):  # shift a time or line anchor earlier
    if isinstance(time, (int, float)):
        return round(time - by, 3)
    m = re.match(r"^(L\d+(?:\.(?:start|end))?)([+-][0-9.]+)?$", time)
    return f"{m.group(1)}{float(m.group(2) or 0) - by:+.3f}"


def tp(time, actor, mark):  # off-camera reposition; must FINISH before the cut it hides behind (shots frame their first frame)
    b(early(time), actor, "move_to", mark=mark, duration=0.02)


def knock(time, actor, mark):  # an over-the-top knockback: thrown back, flinching, landing
    b(time, actor, "gesture", move="flinch", weight=1.0)
    b(time, actor, "move_to", mark=mark, gait="back", duration=0.32)
    b(time + 0.3, actor, "gesture", move="land", weight=1.0)
    b(time, actor, "express", set={"react": 1, "smile": -0.7, "squint": 0, "smirk": 0}, ease=0.08)


def A(x, z, yaw=0, y=0):  # training arena local -> spec coords (spec origin is the hub plaza)
    return [5981 + x, y, -20 + z, yaw]


marks = {
    # hub plaza (act 1 and 3)
    "kai_h": [-2, 0, -4, 180], "raf_h": [2, 0, -17, 0], "raf_h2": [1.4, 0, -7.6, 0], "raf_h3": [2, 0, -12, 0],
    "mira_h1": [-6.5, 0, -12, 140], "juno_h1": [5.2, 0, -11, 220], "mira_h3": [-1.6, 0, -13.5, 0], "juno_h3": [5.0, 0, -13.5, 0],
    "floppy_h": [-0.9, 0, -5.6, 0], "inferno_off": [-16, 0, 20, 0], "ram_off": [-18, 0, 22, 0],
    # training arena (act 2)
    "kai_a": A(-2, 10, 180), "kai_kb": A(-2.6, 15, 180), "raf_a": A(2, -8, 0), "raf_kb": A(2.4, -12.5, 0),
    "kai_chest": A(-2, 10, 0, 1.7), "raf_chest": A(2, -8, 0, 1.7), "floppy_miss": A(5.0, -6.0, 0, 0.4),
    "floppy_a": A(-0.8, 8.4), "ram_land": A(-3.4, 13.0, 30), "ram_under": A(-3.4, 13.0, 30, -2.8),
    "dummy": A(-1, -14, 0, 1.2), "run_a": A(-9, -6, 90), "run_b": A(9, -6, 90), "lead": A(3.5, -6, 0, 1.4),
    "run_c": A(-9, -6, 90), "run_d": A(9, -6, 90), "miss_far": A(18, -12, 0, 1.5),
    "mira_a": A(-7, -7, 20), "juno_a": A(7, -7, -20), "mira_chest": A(-7, -7, 0, 1.7), "juno_chest": A(7, -7, 0, 1.7),
    "mira_kb": A(-7.6, -11, 20), "juno_kb": A(7.6, -11, -20),
    "raf_hud": A(2, -13.4, 180), "mira_hud": A(0.2, -11.6, 140), "juno_hud": A(3.8, -11.6, 220), "huddle": A(2, -12, 0),
    "raf_near": A(0.8, 7.0, 0),
}
actors = {
    "kai": {"kind": "human", "human": "kai", "mark": "kai_h", "blaster": True, "loaded": "Floppy", "face": "raf_h"},
    "raf": {"kind": "human", "human": "raf", "mark": "raf_h", "blaster": True, "loaded": "Rammstone", "face": "kai_h", "phase": 1.7},
    "mira": {"kind": "human", "human": "mira", "mark": "mira_h1", "blaster": True, "loaded": "Aquabeek", "face": "kai_h", "phase": 2.1, "auto_look": False},
    "juno": {"kind": "human", "human": "juno", "mark": "juno_h1", "blaster": True, "loaded": "Inferno", "face": "kai_h", "phase": 4.4, "auto_look": False},
    "floppy": {"kind": "slug", "species": "Floppy", "mark": "floppy_h", "face": "kai_h", "scale": 0.8, "auto_look": False},
    "rammstone": {"kind": "slug", "species": "Rammstone", "mark": "ram_off", "scale": 0.9, "phase": 2.3, "auto_look": False, "ground": False},
    "inferno": {"kind": "slug", "species": "Inferno", "mark": "inferno_off", "scale": 0.8, "phase": 0.7, "auto_look": False},
}

# ===================================== ACT 1: hub plaza, the rule =====================================================
# L1 "In my world, you don't pick your slug for a duel." Establish: the two of them facing off, full bodies.
shot("over_shoulder", "L1.start+2.85", **{"from": "kai"}, target="raf", shoulder=1, back=2.8, offset=1.8, eye=0.35, fov=40)  # two_shot framed rock or void
b(0.0, "kai", "aim", target="raf_chest", duration=2.9)
b(0.0, "raf", "aim", target="kai_chest", duration=2.9)
b(0.2, "raf", "express", set={"smirk": 1, "squint": 0.3}, ease=0.3)
# "Whoever challenges you picks it for you." Raf points at Floppy.
cu("raf", "L1.end+0.25", size=2.4, side=-24)
b("L1.start+2.95", "raf", "point", target="floppy", duration=1.8)
b("L1.start+3.1", "raf", "express", set={"smile": 0.8, "smirk": 0}, ease=0.3)
# L2 "Which is why Kai gets challenged every single day." Three challengers, then Kai.
cu("mira", "L2.start+0.9", size=2.4, side=20)
b("L1.end+0.2", "mira", "point", target="kai", duration=1.1)
b("L1.end+0.2", "mira", "express", set={"smirk": 1, "smile": 0.4}, ease=0.2)
cu("juno", "L2.start+1.6", size=2.4, side=-20)
b("L2.start+0.8", "juno", "point", target="kai", duration=1.0)
b("L2.start+0.8", "juno", "express", set={"smirk": 1, "squint": 0.4}, ease=0.2)
cu("kai", "L2.end+0.2", size=2.6, side=18)
b("L2.start+1.5", "kai", "gesture", move="shrug", mask="upper", duration=1.4)
b("L2.start+1.5", "kai", "express", set={"smile": -0.4, "squint": 0.3}, ease=0.3)
# L3 "Because every challenger hands him the same slug." Raf walks Floppy over and hands him across.
tp("L2.end+0.19", "raf", "raf_h2")
b("L2.end+0.19", "raf", "face", target="kai_h", duration=0.02)
cu("kai", "L3.end+0.35", size=2.4, side=20, fov=40, headroom=0.12)
b("L2.end+0.18", "raf", "hold", item="floppy", hand="right", facing="out", duration=2.2, ease=0.03)
b("L3.start+1.85", "kai", "hold", item="floppy", hand="right", facing="out", duration=6.78, ease=0.35)  # until the cut to the arena
b("L3.start+0.3", "raf", "express", set={"smirk": 1, "smile": 0.6}, ease=0.3)
b("L3.start+1.0", "kai", "express", set={"smile": -0.3, "react": 0.3}, ease=0.3)
# L4 "Floppy." The push lands on his name; he looks straight into the lens.
shot("push_in", "L4.end+0.1", target="floppy", from_size=2.6, size=1.6, side=0, eye=0.05, headroom=0.12, fov=36)
b("L4.start-0.3", "floppy", "look", target="camera")
b("L4.start", "floppy", "express", set={"squint": 0.55}, ease=0.3)
# L5 "Mm. Hello." Into the lens, whole face in frame, smile on "Hello".
cu("floppy", "L5.end+0.2", size=1.55, side=0, fov=34, headroom=0.12)
b("L5.start+1.5", "floppy", "express", set={"smile": 0.8}, ease=0.4)

# ===================================== ACT 2: training arena, the duels ===============================================
CUT2 = "L5.end+0.18"  # before the cut at L5.end+0.2: a shot is framed at its first frame
for who, m in (("kai", "kai_a"), ("raf", "raf_a"), ("floppy", "floppy_a")):
    tp(CUT2, who, m)
b(CUT2, "kai", "face", target="raf_a", duration=0.02)
b(CUT2, "raf", "face", target="kai_a", duration=0.02)
b(CUT2, "floppy", "look", target="none")
# L6 "Floppy is the weakest slug in the cavern." Establish the arena: both shooters, full bodies, dummies behind.
cu("raf", "L6.start+2.5", size=4.0, side=30, fov=44, headroom=0.12)  # over-the-shoulder behind Kai framed a cover block
b("L6.start+0.3", "kai", "aim", target="raf_chest", duration=2.6)
b("L6.start+0.3", "raf", "aim", target="kai_chest", duration=2.6)
# "Seven damage a shot..." Split screen: both fire at once. Top: Floppy flopping. Bottom: Rammstone's cool form.
shot("split", "L6.start+4.15", views=[
    {"preset": "slug_cam", "target": "kai", "shot": 1, "mode": "ride", "angle": 15, "near": 4.0, "height": 1.0, "fov": 46, "lead": 1.0},  # far side from Rammstone's path
    {"preset": "slug_cam", "target": "raf", "shot": 1, "mode": "ride", "angle": -45, "near": 5.0, "distance": 7.0, "height": 1.3, "fov": 46, "lead": 1.4}])
b("L6.start+2.6", "kai", "shoot", slug="Floppy", target="floppy_miss", speed=3.4)
b("L6.start+2.6", "raf", "shoot", slug="Rammstone", target="kai_chest", speed=14)
# Impact: screens rejoin on a wide of Kai thrown back; Floppy still flopping along towards Raf.
knock(17.18 + 2.6 + 1.31, "kai", "kai_kb")  # Rammstone: 18.4 studs at 14/s after the L6.start+2.6 launch
cu("kai", "L7.start", size=2.4, side=20, fov=42, headroom=0.15)
# L7 "Raf beat him before his first shot even landed." Rammstone surfaces by Kai, looks up cocky, digs back down.
tp("L6.end+0.24", "rammstone", "ram_land")
cu("rammstone", "L7.start+1.4", size=2.0, side=10, fov=36)
b("L7.start+0.05", "rammstone", "look", target="camera")
b("L7.start+0.1", "rammstone", "express", set={"react": 1}, ease=0.25)
b("L7.start+0.85", "rammstone", "move_to", mark="ram_under", duration=0.55)
# "...even landed." Floppy finally plops at Raf's feet; Raf looks down at him.
cu("raf", "L8.start", size=3.6, side=-35, fov=40, headroom=0.12)
b("L7.start+1.4", "raf", "look", target="floppy_miss")
b("L7.start+1.6", "raf", "express", set={"smirk": 1, "squint": 0.4, "react": 0}, ease=0.3)
# L8 "Too EASY!"
cu("raf", "L8.end+0.25", size=2.4, side=22, fov=36)
b("L8.start", "raf", "gesture", move="cheer", duration=1.3)
b("L8.start", "raf", "express", set={"smile": 1, "smirk": 0, "react": 0.6}, ease=0.15)
tp("L8.end+0.24", "kai", "kai_a")
b("L8.end+0.24", "kai", "express", set={"react": 0, "smile": -0.2}, ease=0.05)
# L9 "The next day, Raf beat him with his eyes closed."
cu("raf", "L9.end+0.05", size=2.6, side=-22, fov=36)
b("L9.start+0.6", "raf", "express", set={"squint": 2.0, "smile": 0.5, "smirk": 0.6, "react": 0}, ease=0.25)
b("L9.start+0.5", "raf", "aim", target="kai_chest", duration=1.6)
b("L9.start+1.8", "raf", "shoot", slug="Rammstone", target="kai_chest", speed=18)
# L10 "Two hundred duels. Two hundred losses." Kai thrown back again, then sinks; Floppy looks up at him.
knock(30.15, "kai", "kai_kb")
cu("kai", "L10.end+0.4", size=3.2, side=-30, fov=40, headroom=0.14)
b("L10.start+0.8", "kai", "gesture", move="sad", mask="upper", duration=2.4)
b("L10.start+0.9", "kai", "look", target="floppy")
b("L10.start+1.0", "floppy", "look", target="kai")
# L11 "But when you lose with the same slug two hundred times, something strange happens." Face to face.
shot("push_in", "L11.end+0.2", target="kai", from_size=3.0, size=2.0, side=70, eye=0.0, headroom=0.12, fov=36)
b("L11.start+0.4", "floppy", "hop", height=0.5, duration=0.42)
b("L11.start+0.4", "kai", "hold", item="floppy", hand="right", facing="holder", duration=6.2, ease=0.35)
b("L11.start+0.6", "kai", "express", set={"smile": 0, "react": 0, "squint": 0.3}, ease=0.6)
b("L11.start+1.6", "kai", "look", target="floppy")
b("L11.start+1.8", "floppy", "look", target="kai")
# L12 "You learn him." Profile two-shot: both faces.
cu("kai", "L12.end+0.25", size=2.2, side=40, fov=36)
b("L12.start+0.2", "floppy", "express", set={"squint": 0.4, "react": 0.5}, ease=0.4)
b("L12.start+0.3", "kai", "express", set={"smile": 0.5}, ease=0.4)
# L13 "Kai learned exactly how slow a Floppy flies." Practice on the dummy, wide from the side.
tp("L12.end+0.24", "kai", "kai_a")
tp("L12.end+0.24", "floppy", "floppy_a")
shot("slug_cam", "L13.start+2.3", target="kai", shot=2, mode="ride", angle=50, near=2.4, height=1.0, fov=45, lead=1.0)  # how slow he flies
b("L12.end+0.3", "kai", "aim", target="dummy", duration=1.6)
b("L13.start+0.25", "kai", "shoot", slug="Floppy", target="dummy", speed=6)
# "He learned to aim where you're going to be, not where you are." Raf runs; Kai leads him; it lands on him.
tp("L13.start+2.29", "raf", "run_a")
shot("two_shot", "L13.end+0.2", targets=["kai", "lead"], distance=24, height=3.5, fov=44)
b("L13.start+2.32", "raf", "move_to", mark="run_b", gait="run", duration=3.6)
b("L13.start+2.4", "kai", "aim", target="lead", duration=1.8)
b("L13.start+2.93", "kai", "shoot", slug="Floppy", target="lead", speed=9)  # 17 studs at 9/s meets Raf there
b("L13.start+4.83", "raf", "gesture", move="flinch", weight=1.0)
# L14 "Watch this."
tp("L13.end+0.19", "raf", "raf_a")
b("L13.end+0.19", "raf", "face", target="kai_a", duration=0.02)
cu("kai", "L14.end+0.25", size=2.2, side=24, fov=34)
b("L14.start", "kai", "express", set={"smirk": 1, "smile": 0.4, "squint": 0.3}, ease=0.25)
b("L14.start", "kai", "aim", target="raf_chest", duration=4.3)
# L15 "Seven damage. A hundred health. That's fifteen hits." Three hits land on the three numbers, in a wide.
for k, at in enumerate((0.3, 1.2, 2.3)):
    b(f"L15.start{at - 1.53:+.2f}", "kai", "shoot", slug="Floppy", target="raf_chest", speed=12)  # 1.53 s flight lands it on the word
    b(f"L15.start+{at:.2f}", "raf", "gesture", move="flinch", weight=0.9)
cu("raf", "L15.end+0.25", size=5.0, side=85, fov=42, headroom=0.12)
b("L15.start+2.5", "raf", "express", set={"react": 1, "smile": -0.7, "angry": 0.4}, ease=0.2)
# L16 "He stopped missing." The ride, slowed at the hit; Raf thrown back.
shot("slug_cam", "L16.end+0.02", target="kai", shot=7, mode="ride", angle=70, near=4.5, height=1.2, fov=44, lead=1.2, land=4.5)  # cut on the hit
cu("raf", "L16.end+0.38", size=4.0, side=85, fov=40, headroom=0.12)  # the slow-motion knockback, full body
b("L15.end+0.3", "kai", "shoot", slug="Floppy", target="raf_chest", speed=12)
knock_t = "L16.end+0.04"
b(knock_t, "raf", "gesture", move="flinch", weight=1.0)
b(knock_t, "raf", "move_to", mark="raf_kb", gait="back", duration=0.32)
# L17 "Raf handed him Floppy again, laughing."
tp("L16.end+0.36", "raf", "raf_a")
cu("raf", "L17.end+0.25", size=2.6, side=-26, fov=36)
b("L17.start", "raf", "express", set={"smile": 1, "react": 0.5, "angry": 0}, ease=0.25)
b("L17.start+0.1", "raf", "gesture", move="laugh", duration=1.8)
# L18 "Good luck, bro."
cu("raf", "L18.end+0.25", size=2.2, side=18, fov=34)
b("L18.start", "raf", "express", set={"smirk": 1, "smile": 0.5, "squint": 0.3}, ease=0.2)
b("L18.start+0.2", "raf", "gesture", move="wave", mask="upper", duration=1.3)
# L19 "Twenty-two seconds later," the hit and the knockback in a wide; "Raf was not laughing." his face.
cu("raf", "L19.start+1.45", size=5.0, side=85, fov=42, headroom=0.12)  # the two-shot framed empty arena
b("L18.end+0.05", "kai", "aim", target="raf_chest", duration=1.4)
b("L19.start+0.7", "kai", "shoot", slug="Floppy", target="raf_chest", speed=12)  # 8th shot
knock(56.07 + 0.7 + 1.5, "raf", "raf_kb")
cu("raf", "L19.end+0.3", size=2.2, side=-14, fov=34)
b("L19.start+1.6", "raf", "express", set={"smile": -0.8, "smirk": 0, "react": 0.9, "squint": 0}, ease=0.3)
b("L19.start+1.8", "raf", "gesture", move="disbelief", duration=2.0)
# L20 "Run it back."
cu("raf", "L20.end+0.25", size=2.4, side=20, fov=34)
b("L20.start-0.2", "raf", "express", set={"angry": 0.6, "react": 0.3}, ease=0.2)
b("L20.start", "raf", "point", target="kai", duration=1.1)
# L21 "He ran it back. He lost again." / "So did everyone else." Each of them loses on screen.
tp("L20.end+0.24", "raf", "raf_a")
tp("L20.end+0.24", "mira", "mira_a")
tp("L20.end+0.24", "juno", "juno_a")
cu("raf", "L21.start+1.55", size=5.0, side=85, fov=42, headroom=0.12)
b("L20.end+0.25", "kai", "aim", target="raf_chest", duration=1.3)
b("L21.start-0.6", "kai", "shoot", slug="Floppy", target="raf_chest", speed=12)  # 9th
knock(60.87 + 0.9, "raf", "raf_kb")
cu("mira", "L21.start+2.25", size=3.2, side=-35, fov=40)
b("L21.start+0.3", "kai", "shoot", slug="Floppy", target="mira_chest", speed=12)  # 10th
b("L21.start+1.0", "mira", "aim", target="kai_chest", duration=1.0)
knock(60.87 + 1.8, "mira", "mira_kb")
cu("juno", "L21.end+0.25", size=3.2, side=-25, fov=40)
b("L21.start+1.0", "kai", "shoot", slug="Floppy", target="juno_chest", speed=12)  # 11th
b("L21.start+1.6", "juno", "aim", target="kai_chest", duration=1.0)
knock(60.87 + 2.6, "juno", "juno_kb")
# L22 "A whole month without a single loss." Kai, low and proud; Floppy on his shoulder, looking at us.
tp("L21.end+0.24", "kai", "kai_a")
b("L21.end+0.25", "kai", "hold", item="floppy", hand="shoulder", duration=9.9, ease=0.03)
shot("close_up", "L22.start+2.4", target="kai", size=2.8, side=-20, eye=-0.35, headroom=0.12, fov=38)
b("L22.start", "kai", "gesture", move="arms_crossed", duration=2.6)
b("L22.start", "kai", "express", set={"smile": 0.7, "smirk": 0.6, "react": 0, "squint": 0}, ease=0.3)
b("L21.end+0.3", "floppy", "look", target="camera")
b("L22.start+0.3", "floppy", "express", set={"squint": 0.5, "smile": 0.6}, ease=0.4)
# "So the challengers did something nobody had ever done." The three of them confer.
for who, m in (("raf", "raf_hud"), ("mira", "mira_hud"), ("juno", "juno_hud")):
    tp("L22.start+2.39", who, m)
    b("L22.start+2.39", who, "face", target="huddle", duration=0.02)
    b("L22.start+2.39", who, "express", set={"react": 0, "smile": 0, "smirk": 0}, ease=0.05)
cu("raf", "L22.end+0.45", size=3.5, side=60, fov=40, headroom=0.12)  # the huddle
b("L22.start+2.6", "raf", "gesture", move="think", duration=2.6)
b("L22.start+2.8", "mira", "gesture", move="arms_crossed", duration=2.4)
b("L22.start+3.0", "juno", "gesture", move="think", duration=2.3)
for who in ("raf", "mira", "juno"):
    b("L22.start+5.0", who, "look", target="kai")
# L23 "They gave Kai a different slug." Raf holds Inferno out to Kai; Kai takes it on "slug".
tp("L22.end+0.44", "raf", "raf_near")
b("L22.end+0.44", "raf", "face", target="kai_a", duration=0.02)
b("L22.end+0.42", "raf", "hold", item="inferno", hand="right", facing="out", duration=3.4, ease=0.03)
cu("raf", "L23.end+0.25", size=2.4, side=30, fov=40, headroom=0.12)
b("L23.start+0.4", "raf", "express", set={"smirk": 1, "smile": 0.5, "angry": 0}, ease=0.3)
b("L23.start+2.4", "kai", "hold", item="inferno", hand="right", facing="out", duration=10.78, ease=0.35)  # until just before the cut to the miss
b("L23.start+1.5", "kai", "express", set={"react": 0.8, "smile": 0}, ease=0.2)
# L24 KAI "But... I like Floppy." Kai with Inferno in hand, looking down at Floppy at his feet.
tp("L23.end+0.24", "floppy", "floppy_a")
cu("kai", "L24.end+0.25", size=3.0, side=25, fov=38, headroom=0.12)
b("L24.start+0.2", "kai", "look", target="floppy")
b("L24.start+0.6", "kai", "express", set={"smile": 0.3, "squint": 0.3, "react": 0}, ease=0.4)
b("L24.start+0.5", "floppy", "look", target="kai")
# L25 INFERNO "Relax. I'm the good one."
cu("inferno", "L25.end+0.25", size=1.6, side=14, fov=34)
b("L25.start", "inferno", "look", target="camera")
b("L25.start", "inferno", "express", set={"react": 0.8, "lean": 0.4}, ease=0.3)
# L26 "A dragon. Fast, straight, and on fire."
cu("inferno", "L26.end+0.25", size=2.0, side=-18, fov=36)
b("L26.start+0.9", "inferno", "hop", height=0.3, duration=0.35)
# L27 "And Kai aimed it exactly like a Floppy." Wide: Raf runs one way, Kai aims way ahead of him.
tp("L26.end+0.24", "raf", "run_c")
shot("over_shoulder", "L27.end+0.05", **{"from": "kai"}, target="raf", shoulder=1, back=3.0, offset=1.8, eye=0.35, fov=46)
b("L26.end+0.26", "raf", "move_to", mark="run_d", gait="run", duration=4.6)
b("L27.start+0.4", "kai", "aim", target="miss_far", duration=4.2)
b("L27.start+0.5", "kai", "express", set={"smirk": 1, "squint": 0.4}, ease=0.2)
# The miss: the dragon in slow motion, way ahead of Raf.
shot("slug_cam", "L28.start+0.3", target="kai", shot=12, mode="ride", angle=-45, near=5.0, distance=9.0, height=1.4, fov=46, lead=1.4, land=3.0)
b("L27.end+0.08", "kai", "shoot", slug="Inferno", target="miss_far", speed=22)
# L28 "He'd spent months aiming way ahead for the slowest slug there is." Kai's face.
cu("kai", "L28.start+4.2", size=2.0, side=22, fov=34)
b("L28.start+0.4", "kai", "look", target="miss_far")
b("L28.start+0.5", "kai", "express", set={"smirk": 0, "smile": -0.4, "react": 0.8, "squint": 0}, ease=0.3)
b("L28.start+2.4", "kai", "look", target="raf")
# "Inferno isn't slow." Raf, untouched, looks back at the crash, then at Kai.
cu("raf", "L28.end+0.15", size=2.6, side=-20, fov=36)
b("L28.start+4.3", "raf", "look", target="miss_far")
b("L28.start+5.2", "raf", "look", target="kai")
b("L28.start+5.3", "raf", "express", set={"smile": 0.4, "smirk": 1, "react": 0.2}, ease=0.3)
# L29 "LET'S GOOO!"
cu("raf", "L29.end+0.25", size=2.6, side=-24, fov=36)
b("L29.start", "raf", "gesture", move="hands_up", duration=1.2)
b("L29.start", "raf", "express", set={"smile": 1, "react": 1, "squint": 0, "smirk": 0}, ease=0.12)

# ===================================== ACT 3: hub, the dragon is the new Floppy =========================================
CUT3 = "L29.end+0.24"
for who, m in (("kai", "kai_h"), ("raf", "raf_h3"), ("mira", "mira_h3"), ("juno", "juno_h3"), ("floppy", "floppy_h")):
    tp(CUT3, who, m)
for who in ("raf", "mira", "juno"):
    b(CUT3, who, "face", target="kai_h", duration=0.02)
    b(CUT3, who, "express", set={"smile": 0.7, "smirk": 1, "react": 0, "angry": 0, "squint": 0.2}, ease=0.05)
b(CUT3, "kai", "face", target="raf_h3", duration=0.02)
b(CUT3, "kai", "express", set={"smile": -0.3, "react": 0.4, "smirk": 0, "squint": 0}, ease=0.05)
b(CUT3, "kai", "hold", item="inferno", hand="right", facing="out", duration=12.0, ease=0.03)
# L30 "So now, everyone challenges Kai again." Over Kai's shoulder: all three, pointing.
cu("raf", "L30.end+0.2", size=3.0, side=0, fov=42, headroom=0.12)  # all three, pointing at Kai (and us)
b("L30.start+0.4", "raf", "point", target="kai", duration=1.8)
b("L30.start+0.6", "mira", "point", target="kai", duration=1.6)
b("L30.start+0.8", "juno", "point", target="kai", duration=1.4)
# L31 "And they all hand him the dragon." Kai, resigned, Inferno in hand.
shot("push_in", "L31.end+0.4", target="kai", from_size=3.0, size=2.0, side=-16, fov=36)
b("L31.start+0.3", "kai", "look", target="inferno")
b("L31.start", "kai", "express", set={"smile": -0.6, "react": 0.3, "squint": 0.2}, ease=0.4)
# L32 INFERNO "Wait. Am I the weak one now?"
cu("inferno", "L32.end+0.45", size=1.6, side=12, fov=34)
b("L32.start+0.1", "inferno", "express", set={"react": 0, "lean": -0.6}, ease=0.4)
b("L32.start+0.2", "inferno", "look", target="kai")
# L33 FLOPPY "Mm. Welcome." Into the lens; the smile after the line.
cu("floppy", "L33.end+1.2", size=1.55, side=0, fov=34, headroom=0.12)
b("L32.end+0.3", "floppy", "look", target="camera")
b("L33.start+0.4", "floppy", "express", set={"squint": 0.5, "smile": 0}, ease=0.3)
b("L33.end+0.35", "floppy", "express", set={"smile": 1}, ease=0.5)

spec = {
    "id": "most_feared_slug_v02",
    "note": "pilot 01 V02 after the owner's review: hub -> training arena duels (split screen, knockbacks, every loss shown) -> hub",
    "format": "vertical",
    "truth": {"mode": "staged_fiction", "source": "staged_runtime", "gameplay_mechanics": "fictional", "match_outcome": "n/a",
              "label": "Fictional story"},
    "dialogue": "out/dialogue/most-feared-slug-v02/dialogue.json",
    "set": {"kind": "place", "origin": [19, 0, 20], "yaw": 0},
    "marks": marks, "actors": actors,
    "slowmo": [{"from": "L16.end+0.03", "until": "L16.end+0.36", "rate": 0.22, "ramp": 0.05},
               {"from": "L27.end+0.12", "until": "L27.end+0.38", "rate": 0.2, "ramp": 0.05}],
    "shots": S, "timeline": T,
    "capture": {"ui": "hidden", "sample": 0.5},
}
out = ROOT / "roblox-native" / "scenes" / "imw" / "most_feared_slug_v02.json"
out.write_text(json.dumps(spec, indent=1), encoding="utf-8")
print(out, len(S), "shots", len(T), "beats")
