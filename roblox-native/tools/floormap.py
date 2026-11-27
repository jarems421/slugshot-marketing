"""Floor maps: where an extra can stand and walk without sinking into a crack (owner, 2026-11-27: people "sunken into
the ground", "spawning inside the cracks" on the spawn plaza, in most videos).

A map is a 0.5-stud height grid of a set's solid floor (CanCollide surfaces only, so glow, crystals and ink don't
count), read in a playtest with raycasts and saved in library/floors/<name>.json. Each cell is one character:
chr(48 + round((y + 4) * 8)) (heights -4..4.75 at 1/8 stud), "!" where there is no floor. Rows run +z, columns +x, from
`origin` (world x, z).

A spot is standable when the floor around it (radius 1.25 studs) has no step bigger than STEP between neighbouring
cells: gentle slopes pass, crack walls, pits, ledges and holes fail. A path is walkable when every half stud of it is
standable.

  python roblox-native/tools/floormap.py show hub_plaza      a text picture of the standable cells
"""
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLOORS = ROOT / "library" / "floors"
STEP = 0.3        # studs between neighbouring cells (0.5 apart) that still counts as walkable floor
RADIUS = 1.25     # studs of clear floor needed around a standing spot


def decode_rle(text):
    """'P{18}RT' -> 'P' * 18 + 'RT'; rows separated by '|' (how the playtest hands the scan over)."""
    rows = []
    for line in text.split("|"):
        out, i = [], 0
        while i < len(line):
            c = line[i]
            if i + 1 < len(line) and line[i + 1] == "{":
                j = line.index("}", i)
                out.append(c * int(line[i + 2:j]))
                i = j + 1
            else:
                out.append(c)
                i += 1
        rows.append("".join(out))
    return rows


class Floor:
    def __init__(self, data):
        self.name = data["name"]
        self.x0, self.z0 = data["origin"]
        self.step = data["step"]
        self.rows = data["rows"]
        self.w = max(len(r) for r in self.rows)
        self.h = len(self.rows)

    def covers(self, x, z):
        return self.x0 <= x <= self.x0 + (self.w - 1) * self.step and self.z0 <= z <= self.z0 + (self.h - 1) * self.step

    def height(self, i, j):
        if not (0 <= j < self.h and 0 <= i < len(self.rows[j])):
            return None
        c = self.rows[j][i]
        return None if c == "!" else (ord(c) - 48) / 8 - 4

    @lru_cache(maxsize=200000)
    def standable_cell(self, i, j):
        r = int(math.ceil(RADIUS / self.step))
        for dj in range(-r, r + 1):
            for di in range(-r, r + 1):
                if di * di + dj * dj > r * r:
                    continue
                h = self.height(i + di, j + dj)
                if h is None:
                    return False
                for ni, nj in ((i + di + 1, j + dj), (i + di, j + dj + 1)):
                    if (ni - i) ** 2 + (nj - j) ** 2 > r * r:
                        continue
                    n = self.height(ni, nj)
                    if n is None or abs(n - h) > STEP:
                        return False
        return True

    def standable(self, x, z):
        return self.standable_cell(round((x - self.x0) / self.step), round((z - self.z0) / self.step))

    def walkable(self, a, b):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / self.step))
        return all(self.standable(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n + 1))


@lru_cache(maxsize=None)
def all_floors():
    return [Floor(json.loads(p.read_text(encoding="utf-8"))) for p in sorted(FLOORS.glob("*.json"))]


def floor_at(x, z):
    """The saved floor map covering world (x, z), or None (no map: nothing is checked there)."""
    return next((f for f in all_floors() if f.covers(x, z)), None)


def standable(x, z):
    f = floor_at(x, z)
    return True if f is None else f.standable(x, z)


def walkable(a, b):
    f = floor_at(*a) or floor_at(*b)
    return True if f is None else f.walkable(a, b)


def show(name):
    f = next(f for f in all_floors() if f.name == name)
    for j in range(f.h - 1, -1, -2):
        print("".join("." if f.standable_cell(i, j) else ("~" if f.height(i, j) is None else "#") for i in range(0, f.w, 2)))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "show":
        show(sys.argv[2])
    else:
        print(__doc__)
