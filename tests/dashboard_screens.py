"""Screenshots of every dashboard page with headless Edge, for visual review and the handoff report.

Usage: .venv\\Scripts\\python tests\\dashboard_screens.py [port] [out_dir] [--themes dark,light] [--width 1440]
The server must be running (e.g. the fixture demo on 47616).
"""
import subprocess
import sys
from pathlib import Path

EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PAGES = ["overview", "content", "research", "game", "experiments", "publish", "settings"]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    port = args[0] if args else "47616"
    out = Path(args[1] if len(args) > 1 else "out/dashboard_screens")
    themes = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--themes=")), "dark,light").split(",")
    width = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--width=")), "1440")
    height = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--height=")), "1400")
    pages = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--pages=")), ",".join(PAGES)).split(",")
    out.mkdir(parents=True, exist_ok=True)
    for theme in themes:
        for p in pages:
            f = out / f"{p}-{theme}-{width}.png"
            subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{height}",
                            "--virtual-time-budget=6000", f"--screenshot={f.resolve()}",
                            f"http://127.0.0.1:{port}/?theme={theme}#/{p}"], capture_output=True, timeout=60)
            print(f, f.exists())


if __name__ == "__main__":
    main()
