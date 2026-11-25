"""`ss dash <command>` (or `.venv\\Scripts\\python -m dashboard <command>`).

  open [--demo]        start the server if needed (no console window) and open the app window   [default]
  serve [--port N]     run the server in this terminal
  sync [names...]      refresh connectors now (all ready ones, or e.g. youtube_analytics, yt-en, roblox)
  status               sources, credentials present (yes/no only), freshness
  import <file.csv> [--skip-bad] [--check]    manual metrics (platform_metrics or long template)
  export [--detail overview|detailed] [--local]  campaign snapshot (safe to share by default)
  install              Desktop and Start-menu shortcuts that open the app window
  demo                 fixture data in a separate database (out/dashboard_demo/), port 47616, labelled FIXTURE
  stop [--demo]        stop the background server
  publish accounts|list|show|new|check|package|mark-posted   drafts and manual packages (`ss publish`);
                       approving and uploading happen only in the dashboard, by the owner
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_DB = ROOT / "out" / "dashboard_demo" / "demo.db"


def use_demo():
    os.environ["SLUGSHOT_DASH_DB"] = str(DEMO_DB)
    os.environ["SLUGSHOT_DASH_FIXTURE"] = "1"
    os.environ["SLUGSHOT_DASH_VAULT"] = str(DEMO_DB.parent / "vault")
    os.environ["SLUGSHOT_DASH_PORT"] = "47616"


def port():
    from .store import settings
    return int(os.environ.get("SLUGSHOT_DASH_PORT") or settings()["port"])


def alive(p):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{p}/api/health", timeout=1.5) as r:
            return json.loads(r.read()).get("app") == "slugshot-dashboard"
    except Exception:
        return False


def edge():
    for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", ""), os.environ.get("LOCALAPPDATA", "")):
        exe = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        if base and exe.exists():
            return exe
    return None


def start_background(demo):
    pyw = Path(sys.executable).with_name("pythonw.exe")
    args = [str(pyw if pyw.exists() else sys.executable), "-m", "dashboard", "serve"] + (["--demo"] if demo else [])
    log = ROOT / "data" / "local" / "dashboard" / ("server_demo.log" if demo else "server.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    flags = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED_PROCESS | NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    with open(log, "ab") as out:
        subprocess.Popen(args, cwd=ROOT, stdout=out, stderr=out, stdin=subprocess.DEVNULL, creationflags=flags, close_fds=True)


def cmd_open(a):
    p = port()
    if not alive(p):
        start_background(a.demo)
        for _ in range(40):
            time.sleep(0.25)
            if alive(p):
                break
        else:
            sys.exit("The dashboard server didn't start; see data\\local\\dashboard\\server.log")
    url = f"http://127.0.0.1:{p}/"
    e = edge()
    if e:
        subprocess.Popen([str(e), f"--app={url}", "--window-size=1440,920"])
    else:
        import webbrowser
        webbrowser.open(url)
    print(f"Opened {url}")


def cmd_status(_a):
    from . import sync, vault
    from .server import CRED_NAMES
    from .store import Store
    s = Store()
    for h in sync.health(s):
        print(f"{h['label'][:34]:34} {h['account_label'][:18]:18} {h['credential'][:20]:20} {h['freshness']:14} {h['last_success_utc'] or ''}")
    print("credentials present: " + ", ".join(f"{n}={'yes' if vault.secret(n) else 'no'}" for n in sorted(CRED_NAMES)))


def cmd_sync(a):
    from . import sync
    for r in sync.run(only=a.names or None):
        print(f"{r.get('connector', '')[:20]:20} {r.get('account_id', ''):14} {r['status']:10} rows {r.get('rows', 0):5} {r.get('message', '')}")


def cmd_import(a):
    from . import imports
    from .store import Store
    p = Path(a.file)
    res = imports.run(Store(), p.read_text(encoding="utf-8-sig"), p.name, a.skip_bad, a.check)
    for e in res.get("errors", []):
        print("ERROR", e)
    if res.get("ok"):
        print(f"{res['kind']}: {res['rows_ok']} rows ok, {res['rows_rejected']} rejected{' (check only, nothing stored)' if a.check else ''}")
    else:
        sys.exit(1)


def cmd_export(a):
    from . import reports
    from .store import Store
    r = reports.build(Store(), a.detail, not a.local, {"start": a.start, "end": a.end, "platform": a.platform, "language": a.language})
    print(f"{len(r['files'])} files -> {r['folder']}")
    for x in r["excluded"]:
        print("excluded:", x)


def cmd_install(_a):
    pyw = ROOT / ".venv" / "Scripts" / "pythonw.exe"
    icon = ROOT / "dashboard" / "static" / "icons" / "app.ico"
    ps = f"""
$s = New-Object -ComObject WScript.Shell
foreach ($dir in @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('Programs')) '')) ) {{
  $l = $s.CreateShortcut((Join-Path $dir 'Slugshot Dashboard.lnk'))
  $l.TargetPath = '{pyw}'
  $l.Arguments = '-m dashboard open'
  $l.WorkingDirectory = '{ROOT}'
  $l.IconLocation = '{icon}'
  $l.Description = 'Slugshot marketing dashboard (local)'
  $l.Save()
  Write-Output ('shortcut: ' + (Join-Path $dir 'Slugshot Dashboard.lnk'))
}}"""
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    print("Pin it: right-click the Start-menu entry > Pin to taskbar. In the app window you can also use ... > Apps > Install.")


def cmd_demo(a):
    use_demo()
    from . import imports, sync
    from .store import Store
    if DEMO_DB.exists():
        try:  # a running demo server holds the database open: stop it first (the live server is never touched)
            cmd_stop(argparse.Namespace(demo=True))
            time.sleep(1.5)
        except (SystemExit, OSError):
            pass
        for f in DEMO_DB.parent.glob("demo.db*"):
            f.unlink()
    s = Store()
    s.x("UPDATE accounts SET external_id='9990001' WHERE account_id='rbx-slugshot'")
    for r in sync.run(s, fixture=True, sleep=lambda _s: None):
        print(f"fixture {r['connector']:18} {r['account_id']:14} {r['status']} rows {r['rows']}")
    fx = ROOT / "tests" / "fixtures" / "dashboard"
    for name in ("manual_platform_metrics.csv", "manual_long.csv"):
        from .connectors import fixture_text
        res = imports.run(s, fixture_text((fx / name).read_text(encoding="utf-8")), name)
        print(f"fixture import {name}: {res.get('rows_ok')} ok {res.get('errors', '')}")
    import importlib.util
    spec = importlib.util.spec_from_file_location("fixture_history", fx / "history.py")
    hist = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hist)
    print(f"fixture history: {hist.backfill(s)} back-filled snapshots")
    if not a.no_open:
        a.demo = True
        cmd_open(a)


def cmd_stop(a):
    if a.demo:
        use_demo()
    from .store import DATA
    info = DATA / ("server_fixture.json" if a.demo else "server.json")
    if not info.exists():
        sys.exit("not running")
    d = json.loads(info.read_text(encoding="utf-8"))
    req = urllib.request.Request(f"http://127.0.0.1:{d['port']}/api/shutdown", data=b"{}", method="POST",
                                 headers={"X-Dash-Token": d["token"], "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=5)
    print("stopped")


def cmd_hosting(a):
    from . import hosting, publish
    from .store import Store
    s, tx = Store(), publish._transport()
    if a.action == "status":
        print(json.dumps(hosting.status(s, tx, refresh=True), indent=1, default=str))
    elif a.action == "test":
        for line in hosting.selftest(s, tx):
            print(line)
    else:
        print("deleted:", hosting.cleanup(s, tx))


def cmd_publish(a):
    from . import publish as P
    from .store import Store
    s = Store()
    if a.action == "accounts":
        for x in P.accounts_view(s):
            print(f"{x['account_id']:8} {x['platform']:10} @{(x['handle'] or '-').lstrip('@'):14} {'active' if x['active'] else 'inactive':9} "
                  f"{x['credential']:24} routes: {', '.join(x['routes'])}")
    elif a.action == "list":
        for j in P.jobs(s, a.state or None):
            print(f"{j['job_id']:34} {j['account_id']:7} {j['route']:7} {j['state']:15} {j['asset_id']}")
    elif a.action == "new":
        if not (a.asset and a.video and a.accounts):
            sys.exit("new needs --asset, --video and --accounts")
        routes = dict(r.split("=", 1) for r in a.route)
        fields = json.loads(a.fields) if a.fields else None
        for acct in a.accounts.split(","):
            print("draft", P.create(s, a.asset, acct.strip(), a.video, routes.get(acct.strip()), fields, a.experiment, a.variant))
        print("Drafts wait in the dashboard (Publish) for the owner's approval.")
    else:
        if not a.job:
            sys.exit(f"{a.action} needs a job ID")
        j = P.job(s, a.job)
        if not j:
            sys.exit("unknown job")
        if a.action == "show":
            j.pop("approval", None)
            print(json.dumps(j, indent=1, ensure_ascii=False))
        elif a.action == "check":
            r = P.check(s, j)
            for e in r["errors"]:
                print("ERROR", e)
            for w in r["warnings"]:
                print("note ", w)
            print("ready for the owner's approval" if not r["errors"] else f"{len(r['errors'])} error(s)")
        elif a.action == "package":
            r = P.package(s, a.job)
            print(f"manual package -> {r['folder']} ({', '.join(r['files'])})")
        elif a.action == "mark-posted":
            if not a.url:
                sys.exit("mark-posted needs --url")
            j = P.mark_posted(s, a.job, a.url)
            print(f"recorded {j['upload_id']} (linked to {j['asset_id']}{', ' + j['experiment_id'] if j['experiment_id'] else ''})")


def main():
    ap = argparse.ArgumentParser(prog="ss dash", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    o = sub.add_parser("open"); o.add_argument("--demo", action="store_true")
    sv = sub.add_parser("serve"); sv.add_argument("--port", type=int); sv.add_argument("--demo", action="store_true")
    sy = sub.add_parser("sync"); sy.add_argument("names", nargs="*")
    sub.add_parser("status")
    im = sub.add_parser("import"); im.add_argument("file"); im.add_argument("--skip-bad", action="store_true"); im.add_argument("--check", action="store_true")
    ex = sub.add_parser("export"); ex.add_argument("--detail", default="overview", choices=["overview", "detailed"])
    ex.add_argument("--local", action="store_true")
    for k in ("start", "end", "platform", "language"):
        ex.add_argument(f"--{k}", default="")
    sub.add_parser("install")
    ho = sub.add_parser("hosting", help="Cloudinary hosting for Buffer: status | test | cleanup")
    ho.add_argument("action", choices=["status", "test", "cleanup"])
    de = sub.add_parser("demo"); de.add_argument("--no-open", action="store_true")
    st = sub.add_parser("stop"); st.add_argument("--demo", action="store_true")
    pb = sub.add_parser("publish", help="drafts, checks and manual packages (no approval here)")
    pb.add_argument("action", choices=["accounts", "list", "show", "new", "check", "package", "mark-posted"])
    pb.add_argument("job", nargs="?")
    pb.add_argument("--asset"); pb.add_argument("--video"); pb.add_argument("--accounts", help="e.g. yt-en,tt-en")
    pb.add_argument("--route", action="append", default=[], help="account=route, e.g. tt-en=manual")
    pb.add_argument("--fields", help="JSON with platform text, e.g. '{\"caption\": \"...\"}'")
    pb.add_argument("--experiment", default=""); pb.add_argument("--variant", default="")
    pb.add_argument("--state", default=""); pb.add_argument("--url", default="")
    a = ap.parse_args()
    if getattr(a, "demo", False) and a.cmd in ("open", "serve"):
        use_demo()
    if a.cmd == "serve":
        from .server import serve
        return serve(a.port)
    {"open": cmd_open, "status": cmd_status, "sync": cmd_sync, "import": cmd_import, "export": cmd_export,
     "install": cmd_install, "demo": cmd_demo, "stop": cmd_stop, "publish": cmd_publish, "hosting": cmd_hosting, None: lambda a_: (setattr(a_, "demo", False), cmd_open(a_))}[a.cmd](a)


if __name__ == "__main__":
    main()
