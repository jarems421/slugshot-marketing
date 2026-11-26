"""Build the isolated marketing place from a snapshot of the game's integrated place.

  python roblox-native/tools/make_marketing_place.py [--source PATH]

1. Copies ../slugshot/build/SlugshotLobbyTraining.rbxlx (read only) to studio/SlugshotMarketing.source.rbxlx
   unless --source is given, and records its SHA-256.
2. Writes studio/SlugshotMarketing.rbxlx with marketing-only patches:
   - SettingsStore.connect() always returns nil, "MarketingIsolated" (no DataStore access, ever);
   - ServerStorage.SlugshotMarketingMarker (StringValue) holding the token in studio/marker.json,
     plus ServerStorage.SlugshotMarketingProvenance (source hash and game commit).
Every patch must match an exact number of times or the build stops. Text-level edits only, so the
rest of the place (scripts, meshes, binary properties) is byte-for-byte the snapshot.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
STUDIO = HERE / "studio"
GAME = HERE.parent.parent / "slugshot"
DEFAULT_SOURCE = GAME / "build" / "SlugshotLobbyTraining.rbxlx"
MARKER_FILE = STUDIO / "marker.json"
OVERRIDES = STUDIO / "asset-overrides.json"
CONNECT = "function Store.connect(): (any, string?)\n"
ISOLATE = CONNECT + '\tdo return nil, "MarketingIsolated" end -- slugshot-marketing copy: DataStores disabled\n'
SERVER_STORAGE = '<Item class="ServerStorage" referent="'
# The hub's look-only motion (HubMotion: drifting islands and debris, lamp pulses, lava) runs on its own clock. Takes
# set workspace.FilmClock so it follows scene time instead: every pass and patch of a take then shows the islands, and
# the shadows they cast, in the same place (owner, 2026-11-25: shadows "jittering, cut" between frames). Storm flashes
# are random, so they pause while filming.
HUB_CLOCK = [
    ("\tlocal t = os.clock() - started\n\tif t >= nextMove then\n\t\tnextMove = t + (if low then MOVE_RATE else 0)\n"
     "\t\tmoveParts(t)\n\t\tflash(t)\n\t\tpulseStep(t)\n",
     "\tlocal film = workspace:GetAttribute(\"FilmClock\") :: number? -- slugshot-marketing: takes drive the hub's clock\n"
     "\tlocal t = film or (os.clock() - started)\n\tif film or t >= nextMove then\n"
     "\t\tnextMove = t + (if low then MOVE_RATE else 0)\n\t\tmoveParts(t)\n\t\tif not film then\n\t\t\tflash(t)\n\t\tend\n"
     "\t\tif film then\n\t\t\tnextPulse = 0\n\t\tend\n\t\tpulseStep(t)\n"),
    ("\tlocal t = os.clock() - gloopStarted\n",
     "\tlocal t = (workspace:GetAttribute(\"FilmClock\") :: number?) or (os.clock() - gloopStarted) -- slugshot-marketing\n"),
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def marker_token():
    if MARKER_FILE.exists():
        return json.loads(MARKER_FILE.read_text(encoding="utf-8"))["token"]
    token = f"slugshot-marketing:{uuid.uuid4()}"
    MARKER_FILE.write_text(json.dumps({
        "token": token, "place_file": "SlugshotMarketing.rbxlx",
        "instance": "ServerStorage.SlugshotMarketingMarker",
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }, indent=1), encoding="utf-8")
    return token


class Refs:
    n = 0

    @classmethod
    def next(cls):
        cls.n += 1
        return f"mkt-{cls.n}"


def cdata(source):
    return "<![CDATA[" + source.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def module(name, source, children=""):
    return (f'<Item class="ModuleScript" referent="{Refs.next()}"><Properties>'
            f'<string name="Name">{name}</string><ProtectedString name="Source">{cdata(source)}</ProtectedString>'
            f'</Properties>{children}</Item>\n')


def script(name, source):
    return (f'<Item class="Script" referent="{Refs.next()}"><Properties>'
            f'<string name="Name">{name}</string><ProtectedString name="Source">{cdata(source)}</ProtectedString>'
            f'</Properties></Item>\n')


def folder(name, children):
    return (f'<Item class="Folder" referent="{Refs.next()}"><Properties><string name="Name">{name}</string>'
            f'</Properties>{children}</Item>\n')


def package(directory, name):
    """A directory with init.luau becomes a ModuleScript whose children are the other .luau files."""
    init = (directory / "init.luau").read_text(encoding="utf-8")
    kids = "".join(module(p.stem, p.read_text(encoding="utf-8"))
                   for p in sorted(directory.glob("*.luau")) if p.name != "init.luau")
    return module(name, init, kids)


def runtime_xml():
    """ReplicatedStorage.SlugshotMarketing: Reel, Scene, Library and the validated scene specs."""
    sys.path.insert(0, str(Path(__file__).parent))
    import scene  # validates every spec or stops the build
    specs = scene.load_valid()
    runtime = HERE / "runtime"
    library = (HERE / "library" / "library.json").read_text(encoding="utf-8")
    scenes = "".join(module(s["id"], f"return [==[{json.dumps(s)}]==]") for s in specs)
    # Cast: the RemoteFunction human actors use to ask the server (runtime/CastServer.server.luau) for rigs
    cast = f'<Item class="RemoteFunction" referent="{Refs.next()}"><Properties><string name="Name">Cast</string></Properties></Item>\n'
    body = (package(runtime / "vendor" / "Reel", "Reel") + package(runtime / "Scene", "Scene")
            + module("Library", f"return [==[{library}]==]") + folder("Scenes", scenes) + cast)
    return folder("SlugshotMarketing", body), [s["id"] for s in specs]


def string_value(ref, name, value):
    return (f'    <Item class="StringValue" referent="{ref}">\n      <Properties>\n'
            f'        <string name="Name">{name}</string>\n        <string name="Value">{value}</string>\n'
            f'      </Properties>\n    </Item>\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", help="use an existing snapshot instead of copying from the game build")
    a = ap.parse_args()
    snap = STUDIO / "SlugshotMarketing.source.rbxlx"
    if not a.source:
        shutil.copyfile(DEFAULT_SOURCE, snap)  # read from the game, write only here
    elif Path(a.source).resolve() != snap.resolve():
        shutil.copyfile(a.source, snap)
    text = snap.read_text(encoding="utf-8")

    n = text.count(CONNECT)
    if n != 2:
        raise SystemExit(f"expected 2 SettingsStore.connect functions, found {n}; review before patching")
    text = text.replace(CONNECT, ISOLATE)
    for old, new in HUB_CLOCK:
        if text.count(old) != 1:
            raise SystemExit(f"expected HubMotion's clock line once, found {text.count(old)}: {old.splitlines()[0].strip()}")
        text = text.replace(old, new)
    # Repaired slug textures (the game's tools/slugs/repair_textures.py): {old image id: new id}, kept in an ignored
    # file, as the IDs are private. Applies until the game's own build carries the new IDs.
    swapped = 0
    if OVERRIDES.exists():
        for old, new in json.loads(OVERRIDES.read_text(encoding="utf-8")).items():
            # whole-number matches: content links (rbxassetid://ID) and IDs in script source (Floppy's model is
            # loaded at runtime from `model = ID`)
            text, n = re.subn(rf"(?<!\d){old}(?!\d)", new, text)
            swapped += n

    i = text.find(SERVER_STORAGE)
    if i < 0 or text.count(SERVER_STORAGE) != 1:
        raise SystemExit("expected exactly one ServerStorage")
    j = text.find("</Properties>\n", i) + len("</Properties>\n")
    commit = subprocess.run(["git", "-C", str(GAME), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    provenance = f"source=SlugshotLobbyTraining.rbxlx sha256={sha256(snap)} game_commit={commit}"
    if "SlugshotMarketingMarker" in text:
        raise SystemExit("snapshot already contains a marker; start from a clean game snapshot")
    text = text[:j] + string_value("mkt-marker", "SlugshotMarketingMarker", marker_token()) + \
        string_value("mkt-provenance", "SlugshotMarketingProvenance", provenance) + text[j:]

    rs = '<Item class="ReplicatedStorage" referent="'
    if text.count(rs) != 1 or "SlugshotMarketing</string>" in text.split(rs)[1][:2000]:
        raise SystemExit("expected exactly one ReplicatedStorage without an existing SlugshotMarketing folder")
    k = text.find(rs)
    k = text.find("</Properties>\n", k) + len("</Properties>\n")
    xml, scene_ids = runtime_xml()
    text = text[:k] + xml + text[k:]

    sss = '<Item class="ServerScriptService" referent="'
    if text.count(sss) != 1:
        raise SystemExit("expected exactly one ServerScriptService")
    k = text.find("</Properties>\n", text.find(sss)) + len("</Properties>\n")
    text = text[:k] + script("SlugshotMarketingCast", (HERE / "runtime" / "CastServer.server.luau").read_text(encoding="utf-8")) + text[k:]

    out = STUDIO / "SlugshotMarketing.rbxlx"
    out.write_text(text, encoding="utf-8", newline="\n")
    (STUDIO / "provenance.json").write_text(json.dumps({
        "built_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": str(DEFAULT_SOURCE if not a.source else a.source), "source_sha256": sha256(snap),
        "game_commit": commit, "output_sha256": sha256(out),
        "patches": ["SettingsStore.connect -> MarketingIsolated (x2)", "HubMotion follows workspace.FilmClock during takes",
                    f"repaired slug textures: {swapped} reference(s) swapped (studio/asset-overrides.json)",
                    "ServerStorage marker + provenance",
                    "ReplicatedStorage.SlugshotMarketing runtime (Reel 4b810e9, Scene, Library, Scenes, Cast)",
                    "ServerScriptService.SlugshotMarketingCast (human actor rigs and emotes)"],
        "scenes": scene_ids,
    }, indent=1), encoding="utf-8")
    print(f"{out} built from {snap.name} (game {commit[:7]}); marker {marker_token()}; scenes {scene_ids}")


if __name__ == "__main__":
    main()
