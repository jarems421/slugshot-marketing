"""Draw the human actors' face kit: classic Roblox-style painted faces in our ink, as separate layers.

  python roblox-native/tools/faces.py            writes roblox-native/library/faces/<style>/<layer>_<name>.png + preview.png

Owner, 2026-11-26: humans need "actual facial features", the painted Roblox face look of top videos, not dots and
lines. A face is three decals on the head's front, swapped per frame by the scene runner (Humans.luau): eyes, brows
and mouth. A few images make many expressions, and talking swaps only the mouth. Styles: "boy" and "girl" (lashes,
softer brows). Original art (no catalog faces); uploaded as private Decals only with the owner's approval.
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "library" / "faces"
S = 512          # texture size
K = 4            # supersampling
INK = (24, 22, 28, 255)
WHITE = (255, 255, 255, 255)
TONGUE = (196, 74, 86, 255)
MOUTH_IN = (70, 22, 34, 255)
BLUSH = (255, 120, 140, 70)

EYE_Y, EYE_X, MOUTH_Y, BROW_Y = 0.46, 0.175, 0.68, 0.30
G = 1.3  # feature scale (owner: features need to read like top Roblox faces)


def canvas():
    return Image.new("RGBA", (S * K, S * K), (0, 0, 0, 0))


def P(x, y):
    return x * S * K, y * S * K


def ellipse(d, cx, cy, rx, ry, fill):
    (x0, y0), (x1, y1) = P(cx - rx, cy - ry), P(cx + rx, cy + ry)
    d.ellipse([x0, y0, x1, y1], fill=fill)


def stroke(d, pts, width, fill=INK):
    pts = [P(x, y) for x, y in pts]
    w = int(width * S * K)
    d.line(pts, fill=fill, width=w, joint="curve")
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=fill)


def curve(cx, cy, half, bend, n=24, tilt=0.0):
    """Points of a gentle arc: bend > 0 sags down in the middle (a smile), < 0 bows up."""
    return [(cx + half * u, cy + bend * (1 - u * u) + tilt * u) for u in (i / n * 2 - 1 for i in range(n + 1))]


def done(img):
    return img.resize((S, S), Image.LANCZOS)


# Eyes -----------------------------------------------------------------------------------------------------------

def eye_open(d, cx, cy, side, style, rx=0.047 * G, ry=0.072 * G, shift=0.0):
    cx += shift
    ellipse(d, cx, cy, rx, ry, INK)
    ellipse(d, cx - rx * 0.32, cy - ry * 0.42, rx * 0.42, rx * 0.42, WHITE)
    ellipse(d, cx + rx * 0.38, cy + ry * 0.38, rx * 0.17, rx * 0.17, WHITE)
    if style == "girl":
        # lashes: short flicks out of the upper outer lid, along its normal
        for a in (35, 58, 80):
            r = math.radians(a)
            x, y = cx + side * rx * math.sin(r), cy - ry * math.cos(r)
            nx, ny = side * math.sin(r) / rx, -math.cos(r) / ry
            n = math.hypot(nx, ny)
            stroke(d, [(x, y), (x + nx / n * 0.03 + side * 0.008, y + ny / n * 0.03 - 0.006)], 0.011)


def eyes(name, style):
    img = canvas()
    d = ImageDraw.Draw(img)
    for side in (-1, 1):
        cx, cy = 0.5 + side * EYE_X, EYE_Y
        if name in ("open", "left", "right"):
            eye_open(d, cx, cy, side, style, shift={"open": 0, "left": -0.022, "right": 0.022}[name])
        elif name == "wide":
            eye_open(d, cx, cy, side, style, rx=0.058 * G, ry=0.088 * G)
        elif name == "half":  # deadpan: the upper lid cuts straight across
            eye_open(d, cx, cy, side, style)
            lid = Image.new("L", img.size, 0)
            ImageDraw.Draw(lid).rectangle([0, 0, S * K, P(0, cy - 0.012)[1]], fill=255)
            img.paste((0, 0, 0, 0), mask=lid)
            d = ImageDraw.Draw(img)
            stroke(d, [(cx - 0.08, cy - 0.016 - side * 0.004), (cx + 0.08, cy - 0.016 + side * 0.004)], 0.022)
        elif name == "closed":  # a blink: soft downward arcs
            stroke(d, curve(cx, cy + 0.01, 0.065, 0.028), 0.022)
            if style == "girl":
                stroke(d, [(cx + side * 0.048, cy + 0.012), (cx + side * 0.07, cy - 0.004)], 0.011)
        elif name == "happy":  # ^ ^
            stroke(d, curve(cx, cy + 0.012, 0.065, -0.05), 0.024)
    return done(img)


# Brows ----------------------------------------------------------------------------------------------------------

def brows(name, style):
    img = canvas()
    d = ImageDraw.Draw(img)
    w = 0.026 if style == "boy" else 0.019
    for side in (-1, 1):
        cx = 0.5 + side * (EYE_X + 0.01)
        if name == "neutral":
            stroke(d, curve(cx, BROW_Y, 0.066, -0.015, tilt=side * 0.004), w)
        elif name == "raised":
            stroke(d, curve(cx, BROW_Y - 0.035, 0.064, -0.028, tilt=side * 0.006), w)
        elif name == "angry":  # inner ends down
            stroke(d, [(cx - side * 0.066, BROW_Y + 0.04), (cx + side * 0.064, BROW_Y - 0.01)], w * 1.15)
        elif name == "sad":  # inner ends up
            stroke(d, [(cx - side * 0.064, BROW_Y - 0.026), (cx + side * 0.064, BROW_Y + 0.016)], w)
        elif name == "skeptic":  # one up, one flat and low: the deadpan "really?"
            if side < 0:
                stroke(d, curve(cx, BROW_Y - 0.04, 0.064, -0.03), w)
            else:
                stroke(d, [(cx - 0.064, BROW_Y + 0.022), (cx + 0.064, BROW_Y + 0.01)], w)
    return done(img)


# Mouths ---------------------------------------------------------------------------------------------------------

def open_mouth(d, cx, cy, rx, ry, smile=0.0, teeth=False, tongue=True):
    """A filled open mouth; smile > 0 flattens the top into a D."""
    pts = []
    for i in range(64):
        a = i / 64 * 2 * math.pi
        x, y = math.cos(a), math.sin(a)
        if y < 0:
            y *= 1 - 0.75 * smile
        pts.append(P(cx + rx * x, cy + ry * y))
    d.polygon(pts, fill=INK)
    inner = [((px - P(cx, 0)[0]) * 0.8 + P(cx, 0)[0], (py - P(0, cy)[1]) * 0.78 + P(0, cy)[1]) for px, py in pts]
    d.polygon(inner, fill=MOUTH_IN)
    if tongue:
        ellipse(d, cx, cy + ry * 0.45, rx * 0.5, ry * 0.32, TONGUE)
    if teeth:
        top = cy - ry * (1 - 0.75 * smile) * 0.78
        d.rectangle([*P(cx - rx * 0.66, top), *P(cx + rx * 0.66, top + ry * 0.32)], fill=WHITE)


def mouths(name):
    img = canvas()
    d = ImageDraw.Draw(img)
    cx, cy = 0.5, MOUTH_Y
    if name == "neutral":
        stroke(d, curve(cx, cy, 0.068, 0.016), 0.022)
    elif name == "flat":
        stroke(d, [(cx - 0.068, cy + 0.005), (cx + 0.068, cy)], 0.022)
    elif name == "smile":
        stroke(d, curve(cx, cy - 0.015, 0.115, 0.055), 0.024)
    elif name == "grin":
        open_mouth(d, cx, cy + 0.01, 0.115, 0.07, smile=1.0, teeth=True, tongue=False)
    elif name == "smirk":
        stroke(d, [(cx - 0.075, cy + 0.01), (cx + 0.025, cy + 0.013), (cx + 0.08, cy - 0.022)], 0.022)
    elif name == "frown":
        stroke(d, curve(cx, cy + 0.025, 0.08, -0.034), 0.022)
    elif name == "o":
        open_mouth(d, cx, cy + 0.012, 0.046, 0.064, tongue=False)
    elif name == "talk_small":
        open_mouth(d, cx, cy + 0.008, 0.055, 0.032, smile=0.3, tongue=False)
    elif name == "talk_wide":
        open_mouth(d, cx, cy + 0.02, 0.075, 0.066, smile=0.25)
    elif name == "talk_smile":
        open_mouth(d, cx, cy + 0.01, 0.095, 0.055, smile=0.9, teeth=True)
    elif name == "blush":
        for side in (-1, 1):
            ellipse(d, 0.5 + side * 0.2, 0.575, 0.05, 0.022, BLUSH)
        img = img.filter(ImageFilter.GaussianBlur(10))
    return done(img)


EYES = ["open", "left", "right", "wide", "half", "closed", "happy"]
BROWS = ["neutral", "raised", "angry", "sad", "skeptic"]
MOUTHS = ["neutral", "flat", "smile", "grin", "smirk", "frown", "o", "talk_small", "talk_wide", "talk_smile", "blush"]
STYLES = {"boy": {"eyes": "boy", "brows": "boy"}, "girl": {"eyes": "girl", "brows": "girl"}}


def preview(layers):
    """Composite expressions on R6-head-like swatches in a few skin tones, for the owner to review."""
    combos = [("neutral", "open", "neutral", "neutral"), ("talking", "open", "neutral", "talk_wide"),
              ("happy talk", "open", "raised", "talk_smile"), ("smile", "open", "neutral", "smile"),
              ("big grin", "happy", "raised", "grin"), ("smirk", "half", "neutral", "smirk"),
              ("shocked", "wide", "raised", "o"), ("disbelief", "half", "skeptic", "flat"),
              ("angry", "open", "angry", "frown"), ("sad", "open", "sad", "frown"),
              ("blink", "closed", "neutral", "neutral"), ("glance", "left", "neutral", "smile")]
    skins = [(234, 184, 146), (196, 140, 104), (141, 96, 70), (246, 205, 170)]
    cell = 220
    sheet = Image.new("RGB", (cell * len(combos), cell * 2 * 2 + 40), (30, 28, 40))
    d = ImageDraw.Draw(sheet)
    for row, style in enumerate(("boy", "girl")):
        for col, (label, e, b, m) in enumerate(combos):
            skin = skins[(col + row) % len(skins)]
            head = Image.new("RGBA", (S, S), (0, 0, 0, 0))
            ImageDraw.Draw(head).rounded_rectangle([20, 60, S - 20, S - 40], radius=110, fill=skin + (255,))
            for layer in (layers[style]["eyes"][e], layers[style]["brows"][b], layers[style]["mouths"][m]):
                head.alpha_composite(layer)
            if label in ("happy talk", "big grin") and style == "girl":
                head.alpha_composite(layers[style]["mouths"]["blush"])
            y = 20 + row * (cell * 2 + 10)
            sheet.paste(head.resize((cell - 10, cell - 10)).convert("RGB"), (col * cell + 5, y),
                        head.resize((cell - 10, cell - 10)))
            d.text((col * cell + 8, y + cell - 4), f"{style}: {label}", fill=(230, 230, 230))
    return sheet


def main():
    layers, manifest = {}, {}
    for style, spec in STYLES.items():
        folder = OUT / style
        folder.mkdir(parents=True, exist_ok=True)
        layers[style] = {"eyes": {}, "brows": {}, "mouths": {}}
        for kind, names, make in (("eyes", EYES, lambda n: eyes(n, spec["eyes"])),
                                  ("brows", BROWS, lambda n: brows(n, spec["brows"])),
                                  ("mouths", MOUTHS, mouths)):
            for n in names:
                img = make(n)
                img.save(folder / f"{kind}_{n}.png")
                layers[style][kind][n] = img
                manifest.setdefault(style, {}).setdefault(kind, []).append(n)
    preview(layers).save(OUT / "preview.png")
    (OUT / "kit.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(OUT / "preview.png")


if __name__ == "__main__":
    main()
