"""Write the temporary locations (library/locations/*.json) from one readable description each.

  python roblox-native/tools/make_locations.py

Owner, 2026-11-27: locations must feel handcrafted, not assembled. So every location here gets:
- furniture a little off the grid (seeded small turns and nudges; rows staggered), never perfectly centred;
- clutter and story props (books, a slug plush, backpacks, plants, shelves, lanterns, barrels, a sign);
- a Slugshot signature: glowing crystals growing in a corner, cavern light through the windows, the game's own
  blaster on a wall where it fits;
- shaped architecture: ceiling beams, wainscot panels, door frames indoors; caves walled with varied, turned stones
  in several shades instead of flat boxes;
- motivated light (lamps, windows, lanterns) with warm interiors against teal cavern light;
- `seat_*` marks (sit pose: the mark on the seat, facing out; a mark's yaw 0 faces actors toward -z, 180 toward +z) and
  `look_*` marks (things to look at).
Generated props come from library/props.json. Run `scene.py validate` and look at stills after changing a location.
"""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "library" / "locations"
PROPS = json.loads((ROOT / "library" / "props.json").read_text(encoding="utf-8"))["props"]
ROCK = [[48, 38, 72], [56, 44, 82], [40, 32, 60], [62, 50, 88]]
INK_WOOD, DARK_WOOD, WINDOW = [42, 32, 52], [60, 42, 30], [38, 120, 118]


def prop(name, at, scale, rng=None, jitter=0.0, **kw):
    at = list(at) + [0] * (4 - len(at))
    if rng and jitter:
        at = [round(at[0] + rng.uniform(-jitter, jitter), 2), at[1], round(at[2] + rng.uniform(-jitter, jitter), 2),
              round(at[3] + rng.uniform(-7, 7), 1)]
    return {"name": name, "mesh": PROPS[name]["mesh"], "tex": PROPS[name]["tex"], "at": at, "scale": scale, **kw}


def box(name, size, at, color, material="SmoothPlastic", group="props", **kw):
    return {"name": name, "box": size, "at": at, "color": color, "material": material, "group": group, **kw}


def glow(name, size, at, face, color=WINDOW, brightness=0.7):
    return {"name": name, "box": size, "at": at, "color": color, "glow": {"face": face, "range": 18, "brightness": brightness},
            "group": "props", "shadow": False}


def room(w, d, h, floor, wall, ceil, door_wall="front"):
    hw, hd = w / 2, d / 2
    out = [
        box("floor", [w, 1, d], [0, -0.5, 0], floor[0], floor[1], "floor"),
        box("wall_back", [w + 2, h, 1], [0, h / 2, -hd - 0.5], wall, "Plaster", "walls"),
        box("wall_front", [w + 2, h, 1], [0, h / 2, hd + 0.5], wall, "Plaster", "walls"),
        box("wall_left", [1, h, d], [-hw - 0.5, h / 2, 0], wall, "Plaster", "walls"),
        box("wall_right", [1, h, d], [hw + 0.5, h / 2, 0], wall, "Plaster", "walls"),
        box("ceiling", [w + 2, 1, d + 2], [0, h + 0.5, 0], ceil, "Plaster", "walls"),
    ]
    panel = [max(0, c - 18) for c in wall]
    for name, size, at in (("back", [w, 3, 0.15], [0, 1.5, -hd + 0.08]), ("front", [w, 3, 0.15], [0, 1.5, hd - 0.08]),
                           ("left", [0.15, 3, d], [-hw + 0.08, 1.5, 0]), ("right", [0.15, 3, d], [hw - 0.08, 1.5, 0])):
        out.append(box(f"wainscot_{name}", size, at, panel, "WoodPlanks", "trim"))
        rail = [size[0], 0.25, size[2] + 0.1] if size[0] > 1 else [size[0] + 0.1, 0.25, size[2]]
        out.append(box(f"rail_{name}", rail, [at[0], 3.1, at[2]], INK_WOOD, "Wood", "trim"))
    for k, z in enumerate([-d / 4, d / 4] if d < 24 else [-d / 3, 0, d / 3]):
        out.append(box(f"beam_{k}", [w, 0.7, 0.9], [0, h - 0.35, round(z, 2)], DARK_WOOD, "Wood", "trim"))
    dz = hd - 0.1
    out += [box("door", [4, 7.5, 0.25], [0, 3.75, dz], [92, 62, 44], "WoodPlanks", "props"),
            box("door_frame_l", [0.4, 8, 0.5], [-2.2, 4, dz], DARK_WOOD, "Wood", "trim"),
            box("door_frame_r", [0.4, 8, 0.5], [2.2, 4, dz], DARK_WOOD, "Wood", "trim"),
            box("door_frame_top", [4.8, 0.5, 0.5], [0, 8, dz], DARK_WOOD, "Wood", "trim")]
    return out


def cave_walls(w, d, h, rng):
    """Walls of turned, overlapping stones in several shades: reads as rock, not as a box."""
    out = [box("roof", [w + 12, 4, d + 12], [0, h + 2, 0], [30, 24, 46], "Rock", "walls")]
    hw, hd = w / 2, d / 2
    sides = [((-hw, hw), -hd - 2, "z"), ((-hw, hw), hd + 2, "z"), ((-hd, hd), -hw - 2, "x"), ((-hd, hd), hw + 2, "x")]
    k = 0
    for (a, b), fixed, axis in sides:
        t = a
        while t < b:
            span = rng.uniform(9, 15)
            hgt = rng.uniform(h * 0.7, h * 1.05)
            size = [span, hgt, rng.uniform(5, 8)] if axis == "z" else [rng.uniform(5, 8), hgt, span]
            at = [round(t + span / 2, 2), round(hgt / 2 - 1, 2), round(fixed + rng.uniform(-1.5, 1.5), 2)] if axis == "z" \
                else [round(fixed + rng.uniform(-1.5, 1.5), 2), round(hgt / 2 - 1, 2), round(t + span / 2, 2)]
            at.append(round(rng.uniform(-12, 12), 1))
            out.append(box(f"stone_{k}", size, at, rng.choice(ROCK), "Rock", "walls"))
            k += 1
            t += span * 0.8
    for j in range(6):   # boulders at the foot of the walls
        ang = rng.uniform(0, math.tau)
        r = min(hw, hd) - 3
        s = rng.uniform(2.5, 5)
        out.append(box(f"boulder_{j}", [s, s * 0.7, s * 1.1], [round(r * math.cos(ang), 2), round(s * 0.3, 2), round(r * math.sin(ang), 2),
                                                              round(rng.uniform(0, 360), 1)], rng.choice(ROCK), "Rock", "walls"))
    return out


def crystals(at, scale=0.4, index=1):
    return {"kit": "crystals-1", "index": index, "at": at, "scale": scale}


def bedroom():
    rng = random.Random("bedroom")
    pieces = room(26, 20, 13, ([150, 105, 72], "WoodPlanks"), [74, 60, 102], [56, 46, 80]) + [
        box("window_frame", [7.4, 5.4, 0.4], [5, 7, -9.8], DARK_WOOD, "Wood"),
        box("window_bar_v", [0.3, 4.6, 0.3], [5, 7, -9.55], DARK_WOOD, "Wood"),
        box("window_bar_h", [6.6, 0.3, 0.3], [5, 7, -9.55], DARK_WOOD, "Wood"),
        glow("window_glow", [6.4, 4.4, 0.2], [5, 7, -9.65], "Back"),
        box("rug", [9, 0.08, 6], [-0.6, 0.04, 1.2, 4], [36, 118, 120], "Fabric"),
        box("rug_border", [9.6, 0.06, 6.6], [-0.6, 0.02, 1.2, 4], INK_WOOD, "Fabric"),
        box("poster_a_frame", [2.9, 3.7, 0.08], [-3, 7.5, -9.97, 3], INK_WOOD),
        box("poster_a", [2.6, 3.4, 0.1], [-3, 7.5, -9.93, 3], [190, 80, 150]),
        box("poster_b_frame", [0.08, 3.3, 2.7], [-12.97, 8, -3, 0], INK_WOOD),
        box("poster_b", [0.1, 3.0, 2.4], [-12.93, 8, -3, 0], [240, 180, 70]),
        prop("bed", [-8.3, 0, -6.2, 0], 1.45, rng, 0.2),
        prop("slug_plush", [-9.2, 2.2, -7.4, 25], 1.3),
        prop("wardrobe", [-11.6, 0, 4, 90], 1.35, rng, 0.15),
        prop("desk", [8.5, 0, -8.6, 0], 1.0, rng, 0.15),
        prop("books", [6.6, 0, -6.8, 30], 1.4),
        prop("terrarium", [11.6, 0, -3.5, -90], 0.9, rng, 0.15),
        prop("bookshelf", [12.1, 0, 4.5, -90], 1.3, rng, 0.1),
        prop("wall_shelf", [12.85, 6.2, -1.2, -90], 1.3),
        prop("beanbag", [-1.8, 0, 5.2, 25], 1.1, rng, 0.3),
        prop("backpack", [-5.3, 0, -3.2, 40], 1.2),
        prop("plant_pot", [11.8, 0, 8.6, 0], 1.3),
        prop("plant_pot", [-12, 0, -9, 60], 1.0),
        {"name": "blaster_rack", "clone": "StarterPack.Blaster", "at": [-12.7, 6.2, 3.5, 90], "scale": 1.0},
        box("rack_peg_a", [0.4, 0.2, 0.2], [-12.8, 5.8, 2.6], INK_WOOD, "Wood"),
        box("rack_peg_b", [0.4, 0.2, 0.2], [-12.8, 5.8, 4.4], INK_WOOD, "Wood"),
        crystals([-12.2, 0, 9.0, 30], 0.45),
        crystals([12.3, 0, -9.2, 200], 0.35, 2),
        {"light": "point", "at": [-3, 11.4, -2], "range": 32, "brightness": 2.2, "color": [255, 214, 160], "shadows": True},
        {"light": "point", "at": [5, 10.5, 5], "range": 26, "brightness": 1.3, "color": [255, 222, 180]},
        {"light": "point", "at": [8.5, 4.6, -8.2], "range": 12, "brightness": 1.2, "color": [255, 200, 120]},
        {"light": "point", "at": [5, 7, -8.2], "range": 14, "brightness": 0.9, "color": [110, 230, 220]},
        {"light": "point", "at": [-12, 1.5, 9], "range": 8, "brightness": 0.8, "color": [110, 230, 220]},
    ]
    return {"name": "bedroom", "origin": [0, 0, 9000],
            "about": "A player's bedroom: bed with a slug plush, desk + lamp, wardrobe, bookshelf, wall shelf, beanbag, slug terrarium, a blaster on the wall, crystals in the corners, a window glowing with cavern light. Room 26 x 20 x 13 studs.",
            "pieces": pieces,
            "marks": {"center": [0, 0, 2, 0], "by_bed": [-4.5, 0, -3.5, 0], "at_desk": [8.5, 0, -5.5, 0], "by_window": [4.5, 0, -6.5, 0],
                      "door": [0, 0, 8, 0], "seat_bed": [-8.0, 0, -2.6, 180], "seat_beanbag": [-1.8, 0, 5.2, 180],
                      "look_terrarium": [11.2, 2.4, -3.5, 0], "look_window": [5, 7, -9.6, 0], "look_poster": [-3, 7.5, -9.9, 0],
                      "look_blaster": [-12.7, 6.2, 3.5, 0]}}


def classroom():
    rng = random.Random("classroom")
    desks, seats, bags = [], {}, []
    for r, z in enumerate((-1.5, 4, 9.5)):
        for c, x in enumerate((-8, 0, 8)):
            xx = x + (0.6 if r % 2 else -0.4)
            desks.append(prop("student_desk", [xx, 0, z, 180], 1.0, rng, 0.3))
            seats[f"seat_r{r + 1}c{c + 1}"] = [round(xx, 2), 0, round(z + 0.9, 2), 180]
            if rng.random() < 0.4:
                bags.append(prop("backpack", [round(xx + 1.6, 2), 0, round(z + 0.6, 2), rng.uniform(0, 360)], 1.1))
    pieces = room(34, 26, 14, ([130, 100, 78], "WoodPlanks"), [66, 88, 100], [52, 64, 76]) + [
        box("board_frame", [13, 7, 0.4], [0, 6.5, -12.75], [96, 64, 40], "Wood"),
        box("board", [12, 6, 0.2], [0, 6.5, -12.5], [34, 70, 52], "Slate"),
        box("chalk_ledge", [12, 0.25, 0.6], [0, 3.4, -12.3], [96, 64, 40], "Wood"),
        box("chalk_lines_a", [5, 0.15, 0.05], [-2.5, 8, -12.38], [225, 225, 215], shadow=False),
        box("chalk_lines_b", [3.5, 0.15, 0.05], [-3.2, 7.2, -12.38], [225, 225, 215], shadow=False),
        box("chalk_slug", [1.6, 1.0, 0.05], [3.5, 7.4, -12.38], [225, 225, 215], shadow=False),
        prop("teacher_desk", [-6, 0, -8.2, 180], 1.05, rng, 0.2),
        prop("books", [-4.4, 0, -10.2, 15], 1.3),
        prop("bookshelf", [16.1, 0, -6, -90], 1.3, rng, 0.1),
        prop("bookshelf", [16.1, 0, 2, -90], 1.3, rng, 0.1),
        prop("plant_pot", [15.8, 0, 11.6, 0], 1.4),
        prop("plant_pot", [-16, 0, -12, 40], 1.2),
        prop("wall_shelf", [16.85, 7, 7.5, -90], 1.3),
        glow("window_glow_a", [0.2, 4.4, 5.4], [-16.85, 7.5, -4], "Right"),
        glow("window_glow_b", [0.2, 4.4, 5.4], [-16.85, 7.5, 6], "Right"),
        box("window_frame_a", [0.4, 5.0, 6.0], [-16.95, 7.5, -4], DARK_WOOD, "Wood"),
        box("window_frame_b", [0.4, 5.0, 6.0], [-16.95, 7.5, 6], DARK_WOOD, "Wood"),
        box("clock", [1.6, 1.6, 0.2], [9, 10, -12.9], [230, 220, 200]),
        box("clock_rim", [1.9, 1.9, 0.15], [9, 10, -12.95], INK_WOOD),
        crystals([-16.2, 0, 12.0, 120], 0.4),
        {"light": "point", "at": [-6, 12.5, 0], "range": 30, "brightness": 1.3, "color": [255, 226, 180], "shadows": True},
        {"light": "point", "at": [6, 12.5, 0], "range": 30, "brightness": 1.3, "color": [255, 226, 180]},
    ] + desks + bags
    marks = {"teacher": [-1.5, 0, -9.5, 0], "front": [0, 0, -5.5, 0], "aisle": [4, 0, 4, 0], "back_row": [-4, 0, 11.5, 0],
             "door": [14, 0, 11, 0], "seat_l1": [-8, 0, -0.5, 0], "seat_c1": [0, 0, -0.5, 0], "seat_r1": [8, 0, -0.5, 0],
             "look_board": [0, 6.5, -12.4, 0], "look_window": [-16.8, 7.5, 1, 0], **seats}
    return {"name": "classroom", "origin": [400, 0, 9000],
            "about": "A classroom: chalkboard with a slug doodle, teacher's desk + globe, nine student desks in staggered rows with backpacks, bookshelves, plants, cavern-light windows. Room 34 x 26 x 14 studs.",
            "pieces": pieces, "marks": marks}


def wild_cavern():
    rng = random.Random("wild")
    pieces = [box("ground", [80, 2, 80], [0, -1, 0], [38, 64, 58], "Ground", "floor"),
              box("moss_a", [22, 0.2, 16], [-12, 0.05, 4, 8], [52, 104, 76], "LeafyGrass", "floor"),
              box("moss_b", [18, 0.2, 14], [14, 0.05, -10, -12], [52, 104, 76], "LeafyGrass", "floor"),
              box("path", [5, 0.12, 30], [1, 0.03, 14, 6], [70, 62, 80], "Pebble", "floor")] + cave_walls(70, 70, 44, rng) + [
        {"kit": "mushroom-12", "at": [-20, 0, -18, 30], "scale": 0.55},
        {"kit": "mushroom-3", "at": [18, 0, -20, 120], "scale": 0.5},
        {"kit": "mushroom-5", "at": [-26, 0, 10, 200], "scale": 0.6},
        {"kit": "mushroom-13", "at": [24, 0, 14, 60], "scale": 0.45},
        {"kit": "crystals-5", "at": [10, 0, -8, 0], "scale": 1.0},
        {"kit": "crystals-10", "at": [-12, 0, -24, 40], "scale": 1.2},
        {"kit": "crystals-1", "at": [-6, 0, 16, 90], "scale": 1.0},
        {"kit": "crystals-10", "index": 2, "at": [26, 0, -26, 200], "scale": 0.9},
        {"kit": "hub-flora-bell", "at": [-8, 0, -6, 0]},
        {"kit": "hub-flora-bell", "index": 2, "at": [-10, 0, -14, 45]},
        {"kit": "hub-flora-star", "at": [-15, 0, 2, 0]},
        {"kit": "hub-flora-star", "index": 2, "at": [20, 0, -2, 70]},
        {"kit": "hub-flora-lantern", "at": [-3, 0, -14, 0]},
        {"kit": "hub-flora-lantern", "index": 2, "at": [20, 0, -4, 0]},
        {"kit": "hub-lantern-post", "at": [-5, 0, 22, 0]},
        {"kit": "hub-lantern-post", "index": 2, "at": [5, 0, 22, 0]},
        prop("boulder", [17, 0, 6, 30], 1.0, solid=True),
        prop("plant_pot", [3.5, 0, 24, 10], 1.2),
        {"light": "point", "at": [0, 14, 0], "range": 40, "brightness": 1.1, "color": [120, 220, 210]},
        {"light": "point", "at": [-18, 10, -12], "range": 26, "brightness": 1.0, "color": [170, 120, 255]},
        {"light": "point", "at": [16, 10, -14], "range": 26, "brightness": 1.0, "color": [110, 240, 170]},
    ]
    return {"name": "wild_cavern", "origin": [800, 0, 9000],
            "about": "A wild cavern outside town: mossy ground and a pebble path, giant glowing mushrooms, flowers, crystal clusters, a crystal boulder, lantern posts, walls of turned stones. About 70 x 70 studs.",
            "pieces": pieces,
            "marks": {"clearing": [0, 0, 0, 0], "boulder_side": [12, 0, 9, 0], "path": [0, 0, 18, 0], "tree_shade": [-14, 0, -8, 0],
                      "crystals": [6, 0, -4, 0], "look_crystals": [10, 3, -8, 0], "look_boulder": [17, 3, 6, 0]}}


def market():
    rng = random.Random("market")
    pieces = [box("ground", [64, 1, 54], [0, -0.5, 0], [86, 78, 96], "Cobblestone", "floor"),
              box("stall_rug", [8, 0.06, 3], [2, 0.03, 0.2, 2], [150, 70, 60], "Fabric", "floor")] + cave_walls(62, 52, 40, rng) + [
        {"kit": "hub-gun-shop", "at": [-14, 0, -16, 20], "scale": 0.35},
        prop("stall", [2, 0, -4, 0], 1.0),
        prop("shop_shelf", [-6, 0, -6, 4], 1.1, rng, 0.2),
        prop("crates", [8.5, 0, -2.5, 15], 1.0),
        prop("crates", [10.5, 0, -5, -20], 0.9),
        prop("barrel", [-9.2, 0, -3.8, 0], 1.1, rng, 0.2),
        prop("barrel", [12.4, 0, -1.2, 40], 1.0, rng, 0.2),
        prop("stool", [2.4, 0, -6.8, 10], 1.1),
        prop("sign_board", [5.6, 0, 1.2, -25], 1.8),
        prop("paper_lantern", [-1.5, 6.2, -3.0, 0], 1.0),
        prop("paper_lantern", [5.5, 6.2, -3.0, 20], 1.0),
        prop("plant_pot", [-12.5, 0, 2.5, 0], 1.3),
        {"kit": "hub-lantern-post", "at": [-9, 0, 6, 0]},
        {"kit": "hub-lantern-post", "index": 2, "at": [12, 0, 6, 0]},
        {"kit": "hub-flora-lantern", "at": [16, 0, -12, 0]},
        {"kit": "hub-flora-star", "at": [-20, 0, 4, 0]},
        {"kit": "crystals-5", "at": [22, 0, -16, 0], "scale": 1.1},
        {"kit": "crystals-1", "at": [-24, 0, 14, 80], "scale": 0.8},
        {"light": "point", "at": [2, 7, -2], "range": 18, "brightness": 1.4, "color": [255, 200, 130], "shadows": True},
        {"light": "point", "at": [0, 18, 6], "range": 44, "brightness": 1.0, "color": [170, 150, 255]},
        {"light": "point", "at": [-1.5, 5.8, -3], "range": 8, "brightness": 0.9, "color": [255, 170, 90]},
        {"light": "point", "at": [5.5, 5.8, -3], "range": 8, "brightness": 0.9, "color": [255, 170, 90]},
    ]
    return {"name": "market", "origin": [1200, 0, 9000],
            "about": "A small cavern market: a stall with an awning and paper lanterns, a shelf of creature jars, crates and barrels, a painted slug sign, the town's mushroom shop behind, lanterns, crystals. About 60 x 50 studs.",
            "pieces": pieces,
            "marks": {"shopkeeper": [2, 0, -6.5, 0], "customer": [2, 0, 1.5, 0], "browse": [-6, 0, -2.5, 0], "street": [0, 0, 10, 0],
                      "seat_stool": [2.4, 0, -6.8, 0], "look_jars": [-6, 3, -6, 0], "look_sign": [5.6, 1.6, 1.2, 0]}}


def main():
    for loc in (bedroom(), classroom(), wild_cavern(), market()):
        loc["source"] = ("boxes + hub kit pieces (cloned at play time from workspace.HubArt) + generated props (library/props.json); "
                         "written by tools/make_locations.py")
        (OUT / f"{loc['name']}.json").write_text(json.dumps(loc, indent=1), encoding="utf-8")
        print(loc["name"], len(loc["pieces"]), "pieces")


if __name__ == "__main__":
    main()
