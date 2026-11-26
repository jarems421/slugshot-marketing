"""Builds roblox-native/scenes/imw/most_feared_slug.json (pilot 01): python roblox-native/scenes/imw/build_most_feared_slug.py
Times anchor to out/dialogue/most-feared-slug."""
import json
from pathlib import Path

ROOT = Path(r"C:\Users\runni\slugshot marketing")
T, S = [], []


def b(time, actor, action, **kw):
    T.append({"time": time, "actor": actor, "action": action, **kw})


def shot(preset, until, **kw):
    S.append({"preset": preset, "until": until, **kw})


def cu(target, until, size=1.5, side=20, fov=34, headroom=0.1, **kw):
    shot("close_up", until, target=target, size=size, side=side, fov=fov, headroom=headroom, **kw)


def tp(time, actor, mark):  # off-camera reposition; must finish before the cut (scene.py checks it)
    if isinstance(time, str) and "+" in time:
        base, off = time.rsplit("+", 1)
        time = f"{base}{float(off) - 0.08:+.3f}"
    b(time, actor, "move_to", mark=mark, duration=0.02)


marks = {
    # duel lane along -Z on the open plaza (the floor shot_test fired across)
    "kai": [-2, 0, -4, 180], "raf": [2, 0, -19, 0],
    "kai_chest": [-2, 1.7, -4, 0], "raf_chest": [2, 1.7, -19, 0], "raf_shin": [2, 0.4, -18.2, 0],
    "floppy": [-0.9, 0, -5.6, 0], "floppy_off": [-14, 0, 18, 0], "lens_floppy": [-0.9, 0.9, -1.6, 0],
    "rammstone": [4.4, 0, -18.2, 200],
    "inferno_off": [-16, 0, 20, 0],
    # moving-target drill: Raf runs west to east across the lane, Kai leads him
    "run_a": [-8, 0, -17, 90], "run_b": [9, 0, -17, 90], "lead": [3.2, 1.4, -17, 0],
    "train": [6, 0.6, -23, 0],
    # the challengers' huddle (beside Raf) and their line-up facing Kai
    "mira_off": [24, 0, -30, 0], "juno_off": [26, 0, -28, 0],
    "mira": [5.6, 0, -17.2, 200], "juno": [5.0, 0, -21.5, 200],
    "miss_far": [-9, 1.2, -26, 0], "run_c": [7, 0, -17, 270], "run_d": [-7, 0, -17, 270], "huddle": [2, 0, -17.6, 0],
}
actors = {
    "kai": {"kind": "human", "human": "kai", "mark": "kai", "blaster": True, "loaded": "Floppy", "face": "raf"},
    "raf": {"kind": "human", "human": "raf", "mark": "raf", "blaster": True, "loaded": "Rammstone", "face": "kai", "phase": 1.7},
    "mira": {"kind": "human", "human": "mira", "mark": "mira_off", "phase": 2.1, "auto_look": False},
    "juno": {"kind": "human", "human": "juno", "mark": "juno_off", "phase": 4.4, "auto_look": False},
    "floppy": {"kind": "slug", "species": "Floppy", "mark": "floppy", "face": "kai", "scale": 0.8, "auto_look": False},
    "rammstone": {"kind": "slug", "species": "Rammstone", "mark": "rammstone", "face": "kai", "scale": 0.8, "phase": 2.3, "auto_look": False},
    "inferno": {"kind": "slug", "species": "Inferno", "mark": "inferno_off", "scale": 0.8, "phase": 0.7, "auto_look": False},
}

# --- Hook: the rule (L1) -------------------------------------------------------------------------------------------
shot("over_shoulder", "L1.start+2.15", **{"from": "kai"}, target="raf", shoulder=1, back=2.6, offset=1.6, eye=0.35, fov=30)
b(0.0, "kai", "aim", target="raf_chest", duration=2.4)
b(0.0, "raf", "aim", target="kai_chest", duration=2.3)
b(0.2, "raf", "express", set={"smirk": 1, "squint": 0.3}, ease=0.3)
cu("raf", "L1.end+0.2", size=1.45, side=-24)
b("L1.start+2.2", "raf", "point", target="floppy", duration=1.7)
b("L1.start+2.4", "raf", "express", set={"smile": 0.8, "smirk": 0}, ease=0.3)
# --- L2-L3: challenged every day; the same slug every time ------------------------------------------------------------
shot("push_in", "L2.end+0.1", target="kai", from_size=1.6, size=1.1, side=18, eye=0.0, headroom=0.12, fov=34)
b("L2.start", "kai", "express", set={"smile": -0.5, "squint": 0.3}, ease=0.4)
b("L2.start+0.9", "kai", "gesture", move="shrug", mask="upper", duration=1.6)
cu("kai", "L3.end+0.2", size=1.9, side=12, eye=-0.1, headroom=0.2, fov=38)
b("L3.start+0.2", "kai", "look", target="floppy")
b("L3.start+0.5", "floppy", "hop", height=0.5, duration=0.42)
b("L3.start+0.5", "kai", "hold", item="floppy", hand="right", facing="out", duration=6.9, ease=0.4)
# --- L4-L5: "Floppy." The push lands on his name; "Mm. Hello." ---------------------------------------------------------
shot("push_in", "L4.end+0.1", target="floppy", from_size=2.4, size=1.25, side=6, fov=36)
b("L4.start", "floppy", "look", target="lens_floppy")
b("L4.start", "floppy", "express", set={"squint": 0.6}, ease=0.3)
cu("floppy", "L5.end+0.15", size=1.05, side=10, fov=32)
b("L5.start+1.5", "floppy", "express", set={"smile": 0.7}, ease=0.4)
b("L5.start+1.1", "kai", "express", set={"smile": 0.3}, ease=0.4)
tp("L5.end+0.16", "floppy", "floppy_off")
# --- L6-L8: weakest, slowest; Raf wins before it lands; the plop at Raf's feet --------------------------------------
cu("kai", "L6.start+2.4", size=1.4, side=28, fov=34)
b("L5.end+0.2", "kai", "aim", target="raf_chest", duration=4.6)
b("L6.start+0.3", "kai", "express", set={"smile": 0.4, "squint": 0.5}, ease=0.3)
shot("slug_cam", "L7.start+0.05", target="kai", mode="ride", angle=50, near=2.4, height=1.0, fov=45, lead=1.0)
b("L6.start+3.85", "kai", "shoot", slug="Floppy", target="raf_shin", speed=4)
shot("slug_cam", "L7.start+1.05", target="raf", mode="ride", angle=-45, near=2.6, height=1.4, fov=46, lead=1.4, land=3.0)
cu("kai", "L7.start+1.5", size=1.5, side=24, fov=36)
b("L7.start+0.2", "raf", "shoot", slug="Rammstone", target="kai_chest", speed=16)
b("L7.start+1.18", "kai", "gesture", move="flinch", weight=1.0)
b("L7.start+1.2", "kai", "express", set={"react": 1, "smile": -0.6}, ease=0.1)
cu("raf", "L8.end+0.35", size=1.7, side=-30, eye=-0.15, headroom=0.18, fov=38)
b("L7.start+1.6", "raf", "look", target="raf_shin")
b("L7.start+1.7", "raf", "express", set={"smirk": 1, "squint": 0.4}, ease=0.3)
b("L8.start", "raf", "gesture", move="cheer", duration=1.4)
b("L8.start", "raf", "express", set={"smile": 1, "smirk": 0, "react": 0.6}, ease=0.15)
# --- L9: eyes closed ----------------------------------------------------------------------------------------------------
cu("raf", "L9.end+0.12", size=1.35, side=22, fov=34)
b("L9.start", "raf", "look", target="none")
b("L9.start+0.8", "raf", "express", set={"squint": 2.0, "smile": 0.5, "react": 0}, ease=0.25)
b("L9.start+0.7", "raf", "aim", target="kai_chest", duration=1.5)
b("L9.start+1.55", "raf", "shoot", slug="Rammstone", target="kai_chest", speed=20)
# --- L10: two hundred losses ---------------------------------------------------------------------------------------------
tp("L9.end+0.05", "floppy", "floppy")
cu("kai", "L10.end+0.3", size=2.2, side=-20, eye=-0.25, headroom=0.25, fov=40)
b("L10.start", "kai", "gesture", move="flinch", weight=0.8)
b("L10.start+0.1", "kai", "express", set={"react": 0.6, "smile": -0.7, "squint": 0.2}, ease=0.2)
b("L10.start+0.7", "kai", "gesture", move="sad", mask="upper", duration=2.4)
b("L10.start+0.8", "kai", "look", target="floppy")
b("L10.start+1.0", "floppy", "look", target="kai")
# --- L11-L12: the turn ----------------------------------------------------------------------------------------------------
shot("push_in", "L11.end+0.2", target="kai", from_size=2.0, size=1.25, side=14, eye=0.0, headroom=0.12, fov=34)
b("L11.start+0.4", "floppy", "hop", height=0.5, duration=0.42)
b("L11.start+0.4", "kai", "hold", item="floppy", hand="right", facing="holder", duration=5.75, ease=0.3)
b("L11.start+0.6", "kai", "express", set={"smile": 0, "react": 0, "squint": 0.3}, ease=0.6)
b("L11.start+2.0", "kai", "look", target="floppy")
cu("kai", "L12.end+0.3", size=1.35, side=45, fov=34)
b("L12.start", "floppy", "look", target="kai")
b("L12.start+0.3", "floppy", "express", set={"squint": 0.4, "react": 0.5}, ease=0.4)
# --- L13: the drill: how slow he flies; aim where you'll be ------------------------------------------------------------
tp("L12.end+0.31", "floppy", "floppy_off")
shot("slug_cam", "L13.start+2.85", target="kai", shot=2, mode="ride", angle=50, near=2.4, height=1.0, fov=45, lead=1.0)
b("L12.end+0.3", "kai", "aim", target="train", duration=1.2)
b("L13.start+0.2", "kai", "shoot", slug="Floppy", target="train", speed=7)
tp("L13.start+2.8", "raf", "run_a")
shot("over_shoulder", "L13.end+0.2", **{"from": "kai"}, target="raf", shoulder=1, back=2.6, offset=1.6, eye=0.35, fov=48)
b("L13.start+2.86", "raf", "move_to", mark="run_b", gait="run", duration=3.4)
b("L13.start+2.9", "kai", "aim", target="lead", duration=1.6)
b("L13.start+3.3", "kai", "shoot", slug="Floppy", target="lead", speed=7)
b("L13.start+4.75", "raf", "gesture", move="flinch", weight=1.0)
# --- L14: "Watch this." ------------------------------------------------------------------------------------------------
tp("L13.end+0.21", "raf", "raf")
cu("kai", "L14.end+0.25", size=1.2, side=24, fov=32)
b("L14.start", "kai", "express", set={"smirk": 1, "smile": 0.4, "squint": 0.3}, ease=0.25)
b("L14.start+0.3", "kai", "aim", target="raf_chest", duration=5.6)
# --- L15: seven, a hundred, fifteen: hits land on the words --------------------------------------------------------
cu("raf", "L15.start+1.15", size=1.5, side=-20, fov=34)
b("L15.start+0.1", "raf", "gesture", move="flinch", weight=0.9)
b("L15.start+0.1", "raf", "express", set={"react": 0.8, "smile": -0.3}, ease=0.1)
cu("raf", "L15.start+2.0", size=1.25, side=26, fov=34)
b("L15.start+1.3", "raf", "gesture", move="flinch", weight=1.0)
shot("over_shoulder", "L15.end+0.25", **{"from": "kai"}, target="raf", shoulder=-1, back=2.6, offset=1.6, eye=0.35, fov=36)
b("L15.start+2.15", "raf", "gesture", move="flinch", weight=1.0)
b("L15.start+2.6", "raf", "express", set={"react": 1, "smile": -0.7, "angry": 0.4}, ease=0.2)
# --- L16: "He stopped missing." the ride, slowed at the hit ---------------------------------------------------------
shot("slug_cam", "L16.end+0.38", target="kai", shot=4, mode="ride", angle=65, near=3.2, height=1.2, fov=44, lead=1.2, land=4.5)
b("L15.end+0.3", "kai", "shoot", slug="Floppy", target="raf_chest", speed=9)
b("L16.end-0.02", "raf", "gesture", move="flinch", weight=1.0)
# --- L17-L18: "again, laughing" / "Good luck, bro." -----------------------------------------------------------------
tp("L16.end+0.39", "floppy", "floppy")
cu("raf", "L17.end+0.2", size=1.6, side=-26, fov=36)
b("L17.start", "raf", "express", set={"smile": 1, "react": 0.5, "angry": 0}, ease=0.25)
b("L17.start+0.1", "raf", "gesture", move="laugh", duration=1.8)
b("L17.start+1.0", "raf", "point", target="floppy", duration=1.3)
cu("raf", "L18.end+0.25", size=1.2, side=18, fov=32)
b("L18.start", "raf", "express", set={"smirk": 1, "smile": 0.5, "squint": 0.3}, ease=0.2)
b("L18.start+0.2", "raf", "gesture", move="wave", mask="upper", duration=1.4)
# --- L19-L20: not laughing / "Run it back." ------------------------------------------------------------------------
cu("raf", "L19.end+0.3", size=1.15, side=-14, fov=32)
b("L19.start", "raf", "express", set={"smile": -0.8, "smirk": 0, "react": 0.9, "squint": 0}, ease=0.3)
b("L19.start+0.3", "raf", "gesture", move="disbelief", duration=2.6)
b("L19.start+0.2", "rammstone", "express", set={"lean": -0.6}, ease=0.4)
cu("raf", "L20.end+0.3", size=1.3, side=20, fov=34)
b("L20.start-0.2", "raf", "express", set={"angry": 0.6, "react": 0.3}, ease=0.2)
b("L20.start", "raf", "point", target="kai", duration=1.3)
# --- L21: ran it back, lost again; so did everyone ----------------------------------------------------------------
tp("L20.end+0.25", "mira", "mira")
tp("L20.end+0.25", "juno", "juno")
cu("raf", "L21.start+1.0", size=1.5, side=-24, fov=34)
b("L21.start+0.35", "raf", "gesture", move="flinch", weight=1.0)
cu("raf", "L21.start+2.15", size=1.4, side=16, fov=34)
b("L21.start+1.1", "raf", "gesture", move="facepalm", duration=1.6)
shot("two_shot", "L21.end+0.25", targets=["mira", "juno"], distance=11, height=2.0, fov=40)
b("L21.start+2.25", "mira", "gesture", move="flinch", weight=1.0)
b("L21.start+2.45", "juno", "gesture", move="flinch", weight=1.0)
b("L21.start+2.8", "mira", "express", set={"react": 1, "smile": -0.6}, ease=0.2)
b("L21.start+2.9", "juno", "express", set={"react": 1, "smile": -0.5}, ease=0.2)
# --- L22: a month undefeated; the challengers confer ------------------------------------------------------------------
shot("close_up", "L22.start+2.3", target="kai", size=1.6, side=-15, eye=0.0, headroom=0.12, fov=36)
b("L21.end+0.26", "kai", "hold", item="floppy", hand="shoulder", duration=6.5, ease=0.05)
b("L22.start", "kai", "gesture", move="arms_crossed", duration=4.6)
b("L22.start", "kai", "express", set={"smile": 0.7, "smirk": 0.6, "react": 0}, ease=0.3)
b("L22.start+0.3", "floppy", "express", set={"squint": 0.5, "smile": 0.5}, ease=0.4)
for who in ("raf", "mira", "juno"):
    b("L22.start+2.2", who, "face", target="huddle", duration=0.4)
shot("two_shot", "L22.end+0.4", targets=["raf", "mira"], distance=8, height=1.8, fov=40)
b("L22.start+2.5", "raf", "gesture", move="think", duration=2.6)
b("L22.start+2.7", "mira", "gesture", move="arms_crossed", duration=2.4)
b("L22.start+2.9", "juno", "gesture", move="think", duration=2.3)
# --- L23-L24: a different slug; "FINALLY! Someone good!" -----------------------------------------------------------
b("L22.end+0.34", "raf", "hold", item="inferno", hand="right", facing="out", duration=2.8, ease=0.03)
b("L22.end+0.33", "raf", "face", target="kai", duration=0.03)
shot("push_in", "L23.end+0.2", target="inferno", from_size=2.6, size=1.4, side=-12, fov=36)
b("L23.start+0.4", "raf", "express", set={"smile": 0.4, "smirk": 0.8, "angry": 0, "react": 0}, ease=0.3)
b("L23.end+0.15", "kai", "hold", item="inferno", hand="right", facing="out", duration=5.47, ease=0.03)
b("L28.end+0.05", "kai", "hold", item="inferno", hand="right", facing="out", duration=12.0, ease=0.03)
cu("inferno", "L24.end+0.25", size=1.2, side=14, fov=34)
b("L24.start", "inferno", "express", set={"react": 1}, ease=0.15)
b("L24.start+0.05", "inferno", "hop", height=0.45, duration=0.4)
b("L24.start+0.9", "inferno", "hop", height=0.3, duration=0.35)
b("L24.start+0.2", "kai", "express", set={"smile": 1, "smirk": 0.5}, ease=0.3)
# --- L25: "A dragon. Fast, straight, and on fire." the showcase shot --------------------------------------------------
cu("inferno", "L25.end+0.25", size=1.7, side=-24, fov=36)
b("L25.start", "inferno", "express", set={"react": 0.8, "lean": 0.4}, ease=0.3)
b("L25.start+1.0", "inferno", "hop", height=0.3, duration=0.35)
# --- L26-L27: aimed like a Floppy; Inferno isn't slow --------------------------------------------------------------
tp("L25.end+0.26", "raf", "run_c")
shot("over_shoulder", "L26.end+0.05", **{"from": "kai"}, target="raf", shoulder=1, back=2.6, offset=1.6, eye=0.35, fov=48)
b("L25.end+0.27", "raf", "move_to", mark="run_d", gait="run", duration=4.2)
b("L26.start+0.4", "kai", "aim", target="miss_far", duration=1.6)
b("L26.start+0.5", "kai", "express", set={"smirk": 1, "squint": 0.4}, ease=0.2)
shot("slug_cam", "L27.start+0.3", target="kai", shot=5, mode="ride", angle=-45, near=2.6, height=1.4, fov=46, lead=1.4, land=3.0)
cu("kai", "L27.start+4.7", size=1.3, side=22, fov=34)
b("L27.start+1.2", "kai", "look", target="miss_far")
b("L27.start+1.4", "kai", "express", set={"smirk": 0, "smile": -0.4, "react": 0.8, "squint": 0}, ease=0.3)
b("L27.start+3.0", "kai", "look", target="raf")
b("L26.end+0.08", "kai", "shoot", slug="Inferno", target="miss_far", speed=22)
cu("raf", "L27.end+0.15", size=1.4, side=-20, fov=34)
b("L27.start+4.0", "raf", "look", target="kai")
b("L27.start+4.1", "raf", "express", set={"smile": 0.2, "react": 0.4, "squint": 0.3}, ease=0.3)
# --- L28: "LET'S GOOO!" -----------------------------------------------------------------------------------------------
cu("raf", "L28.end+0.25", size=1.6, side=24, fov=36)
b("L28.start", "raf", "gesture", move="hands_up", duration=1.3)
tp("L28.end+0.24", "raf", "raf")
b("L28.start", "raf", "express", set={"smile": 1, "react": 1, "squint": 0}, ease=0.12)
# --- L29-L30: everyone challenges Kai; they all hand him the dragon ------------------------------------------------
shot("over_shoulder", "L29.end+0.1", **{"from": "kai"}, target="raf", shoulder=-1, back=2.6, offset=1.6, eye=0.35, fov=46)
b("L29.start+0.5", "raf", "point", target="kai", duration=2.2)
b("L29.start+0.8", "mira", "point", target="kai", duration=1.9)
b("L29.start+1.1", "juno", "point", target="kai", duration=1.6)
for who in ("mira", "juno"):
    b("L28.end+0.2", who, "face", target="kai", duration=0.05)
    b("L29.start+0.5", who, "express", set={"smile": 0.8, "smirk": 1, "react": 0}, ease=0.3)
shot("push_in", "L30.end+0.35", target="kai", from_size=1.7, size=1.15, side=-16, fov=34)
b("L30.start", "kai", "express", set={"smile": -0.6, "smirk": 0, "react": 0.3, "squint": 0.2}, ease=0.4)
b("L30.start+0.3", "kai", "look", target="inferno")
# --- L31-L32: "Am I the weak one now?" / "Mm. Welcome." -------------------------------------------------------------
cu("inferno", "L31.end+0.45", size=1.15, side=12, fov=32)
b("L31.start+0.1", "inferno", "express", set={"react": 0, "lean": -0.6}, ease=0.4)
b("L31.start+0.2", "inferno", "look", target="kai")
cu("floppy", "L32.end+1.1", size=0.95, side=-8, fov=32)
b("L31.end+0.2", "floppy", "look", target="inferno")
b("L32.start+0.6", "floppy", "express", set={"squint": 0.5, "smile": 0}, ease=0.3)
b("L32.end+0.25", "floppy", "look", target="lens_floppy")
b("L32.end+0.5", "floppy", "express", set={"smile": 1}, ease=0.5)

spec = {
    "id": "most_feared_slug",
    "note": "pilot 01 'The most feared slug': narrator-led In My World; Kai is always handed Floppy, learns him, then gets handed the dragon",
    "format": "vertical",
    "truth": {"mode": "staged_fiction", "source": "staged_runtime", "gameplay_mechanics": "fictional", "match_outcome": "n/a",
              "label": "Fictional story"},
    "dialogue": "out/dialogue/most-feared-slug/dialogue.json",
    "set": {"kind": "place", "origin": [19, 0, 20], "yaw": 0},
    "marks": marks, "actors": actors,
    "slowmo": [{"from": "L16.end+0.02", "until": "L16.end+0.36", "rate": 0.22, "ramp": 0.05},
               {"from": "L26.end+0.12", "until": "L26.end+0.38", "rate": 0.2, "ramp": 0.05}],
    "shots": S, "timeline": T,
    "capture": {"ui": "hidden", "sample": 0.5},
}
out = ROOT / "roblox-native" / "scenes" / "imw" / "most_feared_slug.json"
out.write_text(json.dumps(spec, indent=1), encoding="utf-8")
print(out, len(S), "shots", len(T), "beats")
