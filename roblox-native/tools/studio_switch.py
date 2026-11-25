"""Switch Roblox Studio over to the marketing place (owner-sanctioned handoff helper).

  python roblox-native/tools/studio_switch.py [--rebuild]

--rebuild also saves and closes the marketing place itself, rebuilds studio/SlugshotMarketing.rbxlx
from the snapshot (make_marketing_place.py: runtime + validated scenes), and reopens it.

For every open Studio window that is NOT SlugshotMarketing.rbxlx it: stops a running playtest,
saves the place (save_place = Ctrl+S to its own file or Roblox version; never publishes), and closes
that Studio window. Then it opens studio/SlugshotMarketing.rbxlx and waits until Studio reports it.

This is the only sanctioned way Claude touches a non-marketing place, and it is limited to
start_stop_play(false) and save_place: no Luau, no edits. It stops (leaving the window open) if a
save needs a dialog or fails, so unsaved work is never discarded. Actions are logged to
capture/logs/studio-guard.log. Run only when the owner asks for the switch.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from studio_guard import MARKER, Mcp, log

ROOT = Path(__file__).resolve().parent.parent
PLACE = ROOT / "studio" / MARKER["place_file"]


def studios(mcp):
    return json.loads(mcp.tool("list_roblox_studios", {})).get("studios", [])


def studio_pids():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-Process RobloxStudioBeta -ErrorAction SilentlyContinue | "
                          "ForEach-Object { \"$($_.Id)|$($_.MainWindowTitle)\" }"],
                         capture_output=True, text=True).stdout
    return [l.split("|", 1) for l in out.splitlines() if "|" in l]


def close_window(place_name):
    for pid, title in studio_pids():
        if place_name.rsplit(".", 1)[0].lower() in title.lower():
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"(Get-Process -Id {pid}).CloseMainWindow() | Out-Null"])
            for _ in range(30):
                time.sleep(1)
                if not any(p == pid for p, _ in studio_pids()):
                    return True, f"closed Studio pid {pid} ({title})"
            return False, f"Studio pid {pid} did not close (a dialog may be open): {title}"
    return False, f"no Studio window titled like {place_name}"


def maximise():
    """Studio can reopen in a small window (seen 2026-11-25: 1088x624), which would make film-mode footage low
    resolution; maximise the marketing window (Scene.film also refuses small viewports)."""
    script = ('Add-Type -Namespace W -Name U -MemberDefinition \'[DllImport("user32.dll")] public static extern bool '
              'ShowWindow(System.IntPtr h, int c);\'; Get-Process RobloxStudioBeta -ErrorAction SilentlyContinue | '
              'Where-Object { $_.MainWindowTitle -like "*SlugshotMarketing*" } | '
              'ForEach-Object { [W.U]::ShowWindow($_.MainWindowHandle, 3) | Out-Null }')
    subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)


def main():
    rebuild = "--rebuild" in sys.argv
    mcp = Mcp()
    mcp.deadline = time.monotonic() + 240
    try:
        for s in studios(mcp):
            name = s.get("file") or s.get("name")
            if name == MARKER["place_file"] and not rebuild:
                continue
            if s.get("mode") == "Play":
                mcp.tool("start_stop_play", {"studio_id": s["id"], "is_start": False})
                log(f"SWITCH stopped playtest in {name}")
                for _ in range(20):
                    time.sleep(1)
                    cur = next((x for x in studios(mcp) if x["id"] == s["id"]), {})
                    if cur.get("mode") != "Play":
                        break
            result = mcp.tool("save_place", {"studio_id": s["id"]})
            log(f"SWITCH save_place {name}: {result[:200]}")
            print(f"save {name}: {result}")
            # The tool returns "Saved: <message>{json}"; read the status from the JSON part.
            brace = result.find("{")
            try:
                status = json.loads(result[brace:]).get("status") if brace >= 0 else result.split(":")[0]
            except json.JSONDecodeError:
                status = result.split(":")[0].strip()
            if status not in ("Saved", "NotNeeded"):
                raise SystemExit(f"Stopped: saving {name} returned {status}. Save it in Studio, then rerun.")
            ok, msg = close_window(name)
            log(f"SWITCH {msg}")
            print(msg)
            if not ok:
                raise SystemExit("Stopped before opening the marketing place.")
    finally:
        mcp.close()

    if rebuild:  # marketing window is closed; rebuild the file from the snapshot (validates scenes)
        r = subprocess.run([sys.executable, str(Path(__file__).parent / "make_marketing_place.py"),
                            "--source", str(ROOT / "studio" / "SlugshotMarketing.source.rbxlx")],
                           capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        log(f"SWITCH rebuild exit={r.returncode}")
        if r.returncode:
            raise SystemExit("Rebuild failed; marketing place left closed. Fix the error and rerun.")

    if not any(MARKER["place_file"].rsplit(".", 1)[0].lower() in t.lower() for _, t in studio_pids()):
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Start-Process -FilePath '{PLACE}'"])
        log(f"SWITCH opened {PLACE.name}")
        print(f"opening {PLACE}")
    for _ in range(90):
        time.sleep(2)
        try:
            m = Mcp()
            try:
                names = [x.get("file") or x.get("name") for x in studios(m)]
            finally:
                m.close()
        except Exception:
            continue
        if names == [MARKER["place_file"]]:
            maximise()
            print("Studio reports only SlugshotMarketing.rbxlx open")
            return
    raise SystemExit("Marketing place did not appear in Studio within 3 minutes; check the Studio window.")


if __name__ == "__main__":
    main()
