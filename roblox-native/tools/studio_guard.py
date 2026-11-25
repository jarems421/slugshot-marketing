"""PreToolUse hook: Roblox Studio MCP calls may only target the isolated marketing place.

Wired in .claude/settings.json for every mcp__Roblox_Studio__* tool. It does not trust anything
Claude says: it opens its own short connection to Roblox Studio's MCP server (%LOCALAPPDATA%\\Roblox\\mcp.bat)
and requires ALL of:
  1. exactly one Studio window is open,
  2. its file is SlugshotMarketing.rbxlx,
  3. the tool call's studio_id is that window,
  4. ServerStorage.SlugshotMarketingMarker.Value equals the token in roblox-native/studio/marker.json
     (read in the Edit datamodel, or Server during play; the read is a single property lookup).
Anything else, including errors and timeouts, denies the call (fail closed).
Exempt (no place access): list_roblox_studios, list_roblox_skills, get_roblox_skill, http_get (Roblox docs only).

Manual test:  python studio_guard.py --probe      (prints the decision for "the open Studio")
"""
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = json.loads((ROOT / "studio" / "marker.json").read_text(encoding="utf-8"))
LOG = ROOT / "capture" / "logs" / "studio-guard.log"
PREFIX = "mcp__Roblox_Studio__"
EXEMPT = {"list_roblox_studios", "list_roblox_skills", "get_roblox_skill", "http_get"}
TIMEOUT = 25.0


def studio_mcp_exe():
    """The StudioMCP.exe that Roblox's own mcp.bat launches (path changes with each Studio update)."""
    bat = Path(os.environ.get("LOCALAPPDATA", "")) / "Roblox" / "mcp.bat"
    text = bat.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'"([^"]*StudioMCP\.exe)"', text)
    if m and Path(m.group(1)).exists():
        return m.group(1)
    found = sorted((bat.parent / "Versions").glob("*/StudioMCP.exe"), key=lambda p: p.stat().st_mtime)
    if not found:
        raise FileNotFoundError("StudioMCP.exe not found; is Roblox Studio installed?")
    return str(found[-1])


class Mcp:
    """Minimal stdio MCP client for Roblox Studio's own server."""

    def __init__(self):
        # Talk to StudioMCP.exe directly in binary mode: through cmd.exe and text-mode pipes
        # (CRLF line endings) the server never answered.
        self.p = subprocess.Popen([studio_mcp_exe()], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL)
        self.q = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()
        self.n = 0
        self.deadline = time.monotonic() + TIMEOUT
        self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "slugshot-studio-guard", "version": "1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _read(self):
        for line in iter(self.p.stdout.readline, b""):
            self.q.put(line.decode("utf-8", "replace"))

    def _send(self, msg):
        self.p.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
        self.p.stdin.flush()

    def request(self, method, params):
        self.n += 1
        rid = self.n
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        while True:
            left = self.deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError(f"Studio MCP did not answer {method}")
            try:
                msg = json.loads(self.q.get(timeout=left))
            except queue.Empty:
                raise TimeoutError(f"Studio MCP did not answer {method}")
            except json.JSONDecodeError:
                continue
            if msg.get("id") == rid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg["result"]

    def tool(self, name, args):
        res = self.request("tools/call", {"name": name, "arguments": args})
        text = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
        if res.get("isError"):
            raise RuntimeError(f"{name}: {text[:300]}")
        return text

    def close(self):
        try:
            self.p.kill()
        except Exception:
            pass


def verify(studio_id):
    """Return (ok, reason)."""
    mcp = Mcp()
    try:
        studios = json.loads(mcp.tool("list_roblox_studios", {})).get("studios", [])
        if len(studios) != 1:
            names = ", ".join(s.get("file") or s.get("name", "?") for s in studios) or "none"
            return False, f"{len(studios)} Studio windows open ({names}); only SlugshotMarketing.rbxlx may be open"
        s = studios[0]
        if (s.get("file") or s.get("name")) != MARKER["place_file"]:
            return False, f"open place is {s.get('file') or s.get('name')!r}, not {MARKER['place_file']}"
        if studio_id is not None and s.get("id") != studio_id:
            return False, "tool call targets a different Studio id than the open marketing place"
        datamodel = "Server" if s.get("mode") == "Play" or "Mode: Play" in s.get("state", "") else "Edit"
        code = ('local m = game:GetService("ServerStorage"):FindFirstChild("SlugshotMarketingMarker") '
                'return m and m:IsA("StringValue") and m.Value or "<missing>"')
        try:
            value = mcp.tool("execute_luau", {"studio_id": s["id"], "datamodel_type": datamodel, "code": code})
        except RuntimeError as e:
            # Studio's reported mode can lag a play start or stop by a moment (seen 2026-11-25: "Edit datamodel is
            # not available in Play mode"). Read the same marker in the other datamodel; the token must still match.
            if "not available" not in str(e):
                raise
            datamodel = "Edit" if datamodel == "Server" else "Server"
            value = mcp.tool("execute_luau", {"studio_id": s["id"], "datamodel_type": datamodel, "code": code})
        if MARKER["token"] not in value:
            return False, f"marker check failed in {datamodel} datamodel"
        return True, f"verified marketing place ({datamodel})"
    finally:
        mcp.close()


def log(line):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).replace(microsecond=0).isoformat()} {line}\n")
    except Exception:
        pass


def main():
    if "--probe" in sys.argv:
        try:
            print(verify(None))
        except Exception as e:
            print((False, f"error: {e}"))
        return
    try:
        event = json.load(sys.stdin)
    except Exception:
        event = {}
    tool = str(event.get("tool_name", ""))
    short = tool[len(PREFIX):] if tool.startswith(PREFIX) else tool
    if short in EXEMPT:
        sys.exit(0)
    studio_id = (event.get("tool_input") or {}).get("studio_id")
    try:
        if not studio_id:
            ok, reason = False, "no studio_id in the tool call"
        else:
            ok, reason = verify(studio_id)
    except Exception as e:  # fail closed
        ok, reason = False, f"could not verify the target ({type(e).__name__}: {e})"
    log(f"{'ALLOW' if ok else 'DENY '} {short} {reason}")
    if ok:
        sys.exit(0)  # normal permission rules still apply
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": f"Slugshot studio guard: {reason}. Marketing MCP work needs only "
                                    f"SlugshotMarketing.rbxlx open in Studio (see roblox-native/README.md)."}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
