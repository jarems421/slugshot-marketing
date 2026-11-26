r"""Smoke test: run each part of the toolkit once and write reports\smoke-test.md (PASS/WARN/FAIL/BLOCKED).

Uses media\sample\ (clip.mp4, narration.wav) and writes only to out\smoke\. Takes a few minutes
(Whisper and Kokoro on CPU, one Remotion render). The live YouTube check makes one videos.list
call (1 quota unit) when a key is in .env. Manual checks are listed at the end of the report.
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import qc
import render

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
PY_TTS = ROOT / ".venv-tts" / "Scripts" / "python.exe"
SAMPLE = ROOT / "media" / "sample"
OUT = ROOT / "out" / "smoke"
sys.path.insert(0, str(ROOT / "scripts"))
NPX = "npx.cmd" if os.name == "nt" else "npx"
results = []


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=ROOT, **kw)


def check(name, fn):
    try:
        status, detail = fn()
    except Exception as e:  # a crash in a check is a FAIL, not a crash of the report
        status, detail = "FAIL", f"{type(e).__name__}: {e}"
    detail = detail.replace(str(ROOT) + os.sep, "").replace(str(ROOT) + "/", "")
    results.append((name, status, detail))
    print(f"{status:8} {name}: {detail}", flush=True)


def qc_status(path):
    overall, res, dur = qc.check(path)
    issues = "; ".join(f"{r['check']}: {r['detail']}" for r in res if r["status"] != "PASS")
    return overall, f"{path.relative_to(ROOT)} {dur:.1f}s" + (f" ({issues})" if issues else "")


def tools():
    found = {}
    for name, cmd in {"git": ["git", "--version"], "node": ["node", "--version"],
                      "ffmpeg": ["ffmpeg", "-hide_banner", "-version"]}.items():
        r = run(cmd)
        found[name] = r.stdout.splitlines()[0] if r.returncode == 0 else "MISSING"
    filters = run(["ffmpeg", "-hide_banner", "-filters"]).stdout
    need = ["ass", "loudnorm", "sidechaincompress", "silenceremove", "blackdetect", "freezedetect", "ebur128"]
    missing_f = [f for f in need if f" {f} " not in filters]
    found["ffmpeg filters"] = "all present" if not missing_f else "MISSING " + ",".join(missing_f)
    found["obs"] = "installed" if Path(os.environ["ProgramFiles"], "obs-studio/bin/64bit/obs64.exe").exists() else "MISSING"
    found["kdenlive"] = "installed" if Path(os.environ["LOCALAPPDATA"], "Programs/Kdenlive/bin/kdenlive.exe").exists() else "MISSING"
    found["kokoro venv"] = "installed" if PY_TTS.exists() else "MISSING"
    found["kokoro model"] = "present" if (ROOT / "models/kokoro/kokoro-v1.0.onnx").exists() else "MISSING"
    missing = [k for k, v in found.items() if "MISSING" in v]
    return ("FAIL" if missing else "PASS"), "; ".join(f"{k}: {v}" for k, v in found.items())


def glossary_test():
    r = run([PY, "scripts/glossary.py", "test"])
    n = r.stdout.count("PASS")
    return ("PASS" if r.returncode == 0 else "FAIL"), f"{n} term-correction checks passed" + (
        "" if r.returncode == 0 else " - " + [l for l in r.stdout.splitlines() if l.startswith("FAIL")][0])


def voice():
    out = OUT / "kokoro.wav"
    r = run([PY_TTS, "scripts/voice.py", "He brought Inferno. I brought Floppy. Slugshot, on Roblox.", out])
    if r.returncode:
        return "FAIL", r.stderr.strip()[-300:]
    # Round-trip through Whisper (+ glossary) to check the names come out right.
    r = run([PY, "scripts/caption.py", out, "--out", OUT / "kokoro"])
    text = " ".join(l for l in (OUT / "kokoro.srt").read_text(encoding="utf-8").splitlines()
                    if l and "-->" not in l and not l.isdigit())
    ok = all(w in text for w in ("Inferno", "Floppy", "Slugshot", "Roblox"))
    extra = len(text.split()) > 9  # the line has 9 words; more means invented words got through
    return ("PASS" if ok and not extra else "WARN"), f"Whisper heard: \"{text}\""


def whisper():
    r = run([PY, "scripts/caption.py", SAMPLE / "narration.wav", "--out", OUT / "narration"])
    if r.returncode:
        return "FAIL", r.stderr.strip().splitlines()[-1]
    return "PASS", r.stdout.strip().replace("\n", " | ")


def audio():
    tidy, mixed = OUT / "vo_tidy.wav", OUT / "vo_mixed.wav"
    bed = OUT / "bed_tone.wav"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
         "aevalsrc=0.3*sin(2*PI*220*t):s=48000:d=6", bed])
    for cmd in (["tidy", SAMPLE / "narration.wav", tidy, "--speed", "1.08"],
                ["mix", mixed, "--narration", tidy, "--music", bed]):
        r = run([PY, "scripts/audio.py", *cmd])
        if r.returncode:
            return "FAIL", r.stderr.strip()[-300:]
    dur = lambda p: float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).stdout)
    return "PASS", f"narration {dur(SAMPLE / 'narration.wav'):.1f}s -> tidied {dur(tidy):.1f}s; ducked music mix written"


def ffmpeg_vertical():
    out = OUT / "ffmpeg_vertical.mp4"
    r = run([PY, "scripts/vertical.py", SAMPLE / "clip.mp4", out, "--narration", SAMPLE / "narration.wav",
             "--srt", OUT / "narration.srt", "--hook", "TEST RENDER - not gameplay"])
    return ("FAIL", r.stderr.strip()[-300:]) if r.returncode else qc_status(out)


def remotion():
    out, overall, res, dur = render.render_one("smoke", str(SAMPLE / "clip.mp4"), "TEST", str(SAMPLE / "narration.wav"),
                                               str(OUT / "narration.srt"), "TEST RENDER", production=False,
                                               out_dir=OUT)
    return qc_status(out)


def makemyclip():
    env = {**os.environ, "MAKEMYCLIP_WORKSPACE": str(ROOT / "media"),
           "MAKEMYCLIP_FFMPEG_PATH": shutil.which("ffmpeg") or ""}
    r = run([NPX, "--no-install", "clip", "doctor", "--json"], env=env)
    if r.returncode:
        return "FAIL", "clip doctor exited non-zero"
    return "PASS", "clip doctor OK, workspace = media\\ (whisper.cpp intentionally not installed)"


def yt_dry():
    d = OUT / "yt_dryrun"
    shutil.rmtree(d, ignore_errors=True)
    for args in (["discover", "roblox pvp"], ["stats"], ["report"]):
        r = run([PY, "scripts/yt_collect.py", "--dry-run", "--data-dir", d, *args])
        if r.returncode:
            return "FAIL", r.stderr.strip()[-300:]
    return "PASS", "discover -> stats -> report (+ data dictionary) on fake fixtures, no network"


def assembly():
    """Multi-scene edit from every external asset type: script -> Kokoro WAV, PNG still, OBS-style MKV,
    a 9:16 'Flow' MP4, text cards, music + SFX, script-synced scenes."""
    a = OUT / "assets"
    a.mkdir(parents=True, exist_ok=True)
    ff = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    run([*ff, "-ss", "4", "-i", SAMPLE / "clip.mp4", "-frames:v", "1", "-vf", "crop=480:430:470:0,scale=1080:-1",
         a / "still.png"])
    run([*ff, "-i", SAMPLE / "clip.mp4", "-c", "copy", a / "recording.mkv"])
    run([*ff, "-f", "lavfi", "-i", "gradients=s=1080x1920:d=4:c0=0x2b1d4a:c1=0xc0582a:r=30", "-f", "lavfi", "-i",
         "sine=f=180:d=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", a / "flow.mp4"])
    run([*ff, "-f", "lavfi", "-i", "aevalsrc=0.3*sin(2*PI*220*t):s=48000:d=8", a / "bed.wav"])
    run([*ff, "-f", "lavfi", "-i", "anoisesrc=d=0.5:c=pink:a=0.4,afade=t=out:st=0.2:d=0.3", a / "whoosh.wav"])
    rel = lambda p: str(p.relative_to(ROOT)).replace("\\", "/")
    edit = {
        "concept": "Smoke", "hook_id": "Assembly", "format": "WORLD", "script": "jobs/scripts/sample-story.md",
        "tidy": True, "sync": "script", "music": rel(a / "bed.wav"), "sfx": [{"src": rel(a / "whoosh.wav"), "at": 5.3}],
        "captions": "auto", "emphasis": ["Floppy"], "label": "TEST - not gameplay",
        "scenes": [
            {"kind": "card", "text": "In my world, everyone gets one slug.", "seconds": 2},
            {"kind": "image", "src": rel(a / "still.png"), "seconds": 2, "fit": "crop", "zoom": 1.15},
            {"kind": "video", "src": rel(a / "recording.mkv"), "trim_start": 2, "seconds": 2, "fit": "crop", "punch_at": [0.9]},
            {"kind": "video", "src": rel(a / "flow.mp4"), "seconds": 2, "transition": "fade", "label": "AI-generated scene"},
            {"kind": "card", "text": "Would you pick Floppy?", "seconds": 2}]}
    (OUT / "edit.json").write_text(json.dumps(edit, indent=1), encoding="utf-8")
    r = run([PY, "scripts/assemble.py", OUT / "edit.json", "--test", "--out-dir", OUT])
    if r.returncode == 1 or "QC" not in r.stdout:
        return "FAIL", (r.stderr or r.stdout).strip()[-400:]
    video = next(OUT.glob("SS_*_WORLD_Smoke_Assembly_*.mp4"))
    status, detail = qc_status(video)
    starts = next((l for l in r.stdout.splitlines() if l.startswith("scene starts")), "")
    return status, f"5 scenes (card, PNG, MKV, 9:16 MP4, card) + Kokoro script + music/SFX; {starts}; {detail}"


def candidates():
    r = run([PY, "scripts/candidates.py", SAMPLE / "clip.mp4", ROOT / "tests" / "fixtures" / "gemini_sample.csv"])
    index = ROOT / "media" / "candidates" / "clip" / "index.csv"
    if r.returncode or not index.exists():
        return "FAIL", (r.stderr or r.stdout).strip()[-300:]
    n = len(index.read_text(encoding="utf-8").strip().splitlines()) - 1
    skipped = "skip row 3" in r.stdout
    return ("PASS" if n == 2 and skipped else "WARN"), f"{n} padded clips + index.csv from a Gemini-style CSV; out-of-range row skipped: {skipped}"


def yt_dictionary():
    reports = list((OUT / "yt_dryrun" / "reports").glob("*youtube_report_*.csv"))
    readme = next((OUT / "yt_dryrun" / "reports").glob("*_README.md"), None)
    ok = reports and readme and "| views_per_hour_since_prev |" in readme.read_text(encoding="utf-8")
    return ("PASS" if ok else "FAIL"), "report + data dictionary written (real runs go to exports/share for ChatGPT)"


def yt_live():
    env_file = ROOT / ".env"
    has_key = os.environ.get("YOUTUBE_API_KEY") or (
        env_file.exists() and any(l.startswith("YOUTUBE_API_KEY=") and l.split("=", 1)[1].strip()
                                  for l in env_file.read_text(encoding="utf-8").splitlines()))
    if not has_key:
        return "BLOCKED", "no YOUTUBE_API_KEY in .env (needs your Google Cloud key)"
    d = OUT / "yt_live"
    shutil.rmtree(d, ignore_errors=True)
    r = run([PY, "scripts/yt_collect.py", "--data-dir", d, "stats", "--ids", "jNQXAC9IVRw"])  # 1 unit
    return ("FAIL", (r.stderr or r.stdout).strip()[-300:]) if r.returncode else ("PASS", r.stdout.strip())


def research_unit():
    r = run([PY, "-m", "unittest", "tests.test_research"])
    last = (r.stderr.strip().splitlines() or ["?"])[-1]
    ran = next((l for l in r.stderr.splitlines() if l.startswith("Ran ")), "")
    return ("PASS" if r.returncode == 0 else "FAIL"), f"{ran}: {last} (YouTube, Wikimedia, Trends, observations, Twitch, Roblox on fixtures)"


def analysis_unit():
    r = run([PY, "-m", "unittest", "tests.test_analysis"])
    last = (r.stderr.strip().splitlines() or ["?"])[-1]
    ran = next((l for l in r.stderr.splitlines() if l.startswith("Ran ")), "")
    return ("PASS" if r.returncode == 0 else "FAIL"), f"{ran}: {last} (evidence-ledger traps, intake, repeat, sensitivity, blind coding, trend, change points)"


def evidence_example():
    ledger = ROOT / "data" / "local" / "research" / "evidence" / "EXAMPLE-HUSS-SLUGTERRA.json"
    if not ledger.exists():
        return "WARN", "worked example ledger not present (it lives in data/local, not git)"
    r = run([PY, "scripts/evidence.py", "validate", ledger, "--bundle", ROOT / "exports" / "share" / "research"])
    return ("PASS" if r.returncode == 0 else "FAIL"), r.stdout.strip().splitlines()[0][:250]


def scholarly_skills():
    """Run the pinned upstream offline suites with their Windows skip."""
    summaries = []
    passed = True
    for skill in ("verifying-bibliography", "surveying-literature"):
        result = run([PY, "tests/run_offline.py", "--skill", skill], env={**os.environ, "PYTHONUTF8": "1"})
        lines = result.stderr.strip().splitlines()
        ran = next((line for line in lines if line.startswith("Ran ")), "?")
        summaries.append(f"{skill}: {ran} {lines[-1] if lines else '?'}")
        passed = passed and result.returncode == 0
    return ("PASS" if passed else "FAIL"), "; ".join(summaries)


def live(script, args, ok_text):
    d = OUT / "research_live" / script.split(".")[0]
    shutil.rmtree(d, ignore_errors=True)
    r = run([PY, f"scripts/{script}", "--data-dir", d, *args])
    out = (r.stdout + r.stderr).strip()
    if r.returncode:
        return ("BLOCKED" if "BLOCKED" in out else "FAIL"), out.splitlines()[-1][:300]
    return ("PASS" if ok_text in out else "WARN"), out.splitlines()[-1][:300]


def wiki_live():
    return live("wiki_collect.py", ["pull", "--days", "3"], "stored")


def trends_live():
    return live("trends_collect.py", ["rss", "--geo", "GB,MX"], "rows ->")


def roblox_live():
    return live("rbx_collect.py", ["games"], "snapshots ->")


def oembed_live():
    d = OUT / "research_live"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "oembed.csv"
    f.write_text("url,observed_at_utc,source\nhttps://www.tiktok.com/@sebasgb572/video/7708074478366100754,2026-11-24,platform_page\n")
    status, detail = live("observe.py", ["import", f, "--oembed"], "Imported")
    rows = (d / "observe" / "public_observations.csv")
    checked = rows.exists() and ",true," in rows.read_text(encoding="utf-8")
    return (status if checked else "WARN"), f"oEmbed check {'confirmed the post ID' if checked else 'did not confirm the post'} ({detail})"


def twitch_live():
    return live("twitch_collect.py", ["categories", "Roblox"], "Roblox")


def youtube_live_v2():
    """The upgraded collector live: a 1-unit chart call + 1-unit Shorts-playlist check, only when the key is present."""
    import research_common as rc
    if not rc.env_value("YOUTUBE_API_KEY"):
        return "BLOCKED", "no YOUTUBE_API_KEY in .env"
    return live("yt_collect.py", ["chart", "--region", "MX", "--max", "5", "--check-shorts"], "chart snapshots")


RESEARCH = [("Research collectors offline tests", research_unit),
            ("Research analysis + evidence ledger tests", analysis_unit),
            ("Evidence ledger worked example (real data)", evidence_example),
            ("Installed scholarly skills (upstream offline tests)", scholarly_skills),
            ("Wikimedia pageviews live", wiki_live),
            ("Google Trending Now RSS live", trends_live),
            ("Roblox experience stats live (legacy API)", roblox_live),
            ("TikTok oEmbed live check", oembed_live),
            ("YouTube upgraded collector live (chart + Shorts check)", youtube_live_v2),
            ("Twitch Helix live", twitch_live)]


def dashboard_unit():
    r = run([PY, "-m", "unittest", "tests.test_dashboard"])
    last = (r.stderr.strip().splitlines() or ["?"])[-1]
    ran = next((l for l in r.stderr.splitlines() if l.startswith("Ran ")), "")
    return ("PASS" if r.returncode == 0 else "FAIL"), f"{ran}: {last} (store, metric rules, connectors on fixtures, imports, exports, vault, server security)"


def dashboard_demo():
    """Fixture sync of every connector into out/dashboard_demo/ (separate database), then a safe export check."""
    r = run([PY, "-m", "dashboard", "demo", "--no-open"])
    out = (r.stdout + r.stderr).strip()
    runs = [l for l in out.splitlines() if l.startswith("fixture ") and not l.startswith("fixture import")]
    ok = sum(" ok " in l or " partial " in l for l in runs)
    failed = [l.split()[1] + "/" + l.split()[2] for l in out.splitlines() if l.startswith("fixture ") and " failed " in l]
    # Only Spanish accounts without their own fixtures may fail (isolated by design); inactive accounts are skipped.
    status = "PASS" if r.returncode == 0 and ok >= 6 and failed and all(f.endswith("-es") for f in failed) else "FAIL"
    return status, f"{ok} connector runs ok/partial; {len(failed)} isolated failures as designed ({', '.join(failed)}: no ES fixture)"


def dashboard_live_server():
    """The real server answers on loopback with the dashboard's own health reply (if running)."""
    import json as _j
    import urllib.request
    port = _j.loads((ROOT / "config" / "dashboard" / "settings.json").read_text(encoding="utf-8"))["port"]
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as resp:
            return ("PASS" if _j.loads(resp.read()).get("app") == "slugshot-dashboard" else "FAIL"), f"127.0.0.1:{port} answers"
    except Exception as e:
        return "WARN", f"not running on {port} ({type(e).__name__}); start it with ss dash"


def knowledge_unit():
    r = run([PY, "-m", "unittest", "tests.test_knowledge"])
    last = (r.stderr.strip().splitlines() or ["?"])[-1]
    ran = next((l for l in r.stderr.splitlines() if l.startswith("Ran ")), "")
    return ("PASS" if r.returncode == 0 else "FAIL"), f"{ran}: {last} (schema, links, game truth, expiry, export and policy gates, sentiment pipeline, fixture isolation)"


def publish_unit():
    r = run([PY, "-m", "unittest", "tests.test_publish"])
    last = (r.stderr.strip().splitlines() or ["?"])[-1]
    ran = next((l for l in r.stderr.splitlines() if l.startswith("Ran ")), "")
    return ("PASS" if r.returncode == 0 else "FAIL"), f"{ran}: {last} (fixture uploads only: chunking, approval binding, reveal lock, game truth, manual fallback, linking)"


def analytics_unit():
    r = run([PY, "-m", "unittest", "tests.test_analytics"])
    last = (r.stderr.strip().splitlines() or ["?"])[-1]
    ran = next((l for l in r.stderr.splitlines() if l.startswith("Ran ")), "")
    return ("PASS" if r.returncode == 0 else "FAIL"), f"{ran}: {last} (combined totals, no double counting, measurement windows, tags, comparisons, learning loop)"


def knowledge_live():
    """The real private knowledge banks validate (skipped when they don't exist on this machine)."""
    kbdir = ROOT / "data" / "local" / "research" / "knowledge"
    if not kbdir.exists():
        return "WARN", "no knowledge banks on this machine (data/local/research/knowledge)"
    r = run([PY, "scripts/kb.py", "validate"])
    first = (r.stdout.strip().splitlines() or ["?"])[0]
    return ("PASS" if r.returncode == 0 else "FAIL"), first.split(": ", 1)[-1]


DASHBOARD = [("Dashboard tests", dashboard_unit), ("Knowledge and sentiment tests", knowledge_unit),
             ("Publishing tests (no network)", publish_unit),
             ("Analytics tests (owner screens)", analytics_unit),
             ("Knowledge banks validate", knowledge_live), ("Dashboard fixture sync (all connectors)", dashboard_demo),
             ("Dashboard server on loopback", dashboard_live_server)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).replace(microsecond=0)
    if "--dashboard" in sys.argv:
        for name, fn in DASHBOARD:
            check(name, fn)
        return write_report(started, research_only=True, name="dashboard")
    if "--research" in sys.argv:
        for name, fn in RESEARCH:
            check(name, fn)
        return write_report(started, research_only=True)
    check("Installed tools", tools)
    check("Glossary corrections", glossary_test)
    check("Whisper transcription", whisper)
    check("Kokoro voice + Whisper round trip", voice)
    check("Audio tidy + ducked mix", audio)
    check("FFmpeg vertical render + QC", ffmpeg_vertical)
    check("Remotion template render + QC", remotion)
    check("Multi-scene assembly (all asset types) + QC", assembly)
    check("Gemini timestamps -> review clips", candidates)
    check("MakeMyClip setup", makemyclip)
    check("YouTube collector dry run", yt_dry)
    check("YouTube report + data dictionary", yt_dictionary)
    check("YouTube collector live call", yt_live)
    for name, fn in RESEARCH + DASHBOARD:
        check(name, fn)
    write_report(started)


def write_report(started, research_only=False, name="research"):
    cmd = f".\\ss smoke --{name}" if research_only else ".\\ss smoke"
    lines = ["# Smoke test", "", f"Run {started.isoformat()} by `{cmd}`. Outputs in `out/smoke/`.",
             "WARN in a render check is about the sample footage (a dark 1422x430 preview strip), not the pipeline.",
             "Live research checks make a handful of free calls (Wikimedia, Google Trends RSS, Roblox, TikTok oEmbed; "
             "YouTube about 2 units; Twitch 1 point when enabled). BLOCKED = waiting on credentials or an owner decision.", "",
             "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {n} | **{s}** | {d.replace('|', '/')} |" for n, s, d in results]
    if research_only:
        report = ROOT / "reports" / f"smoke-test-{name}.md"
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(report)
        sys.exit(1 if any(s == "FAIL" for _, s, _ in results) else 0)
    lines += ["", "## Manual checks (a person must do these)", "",
              "- Watch `out/smoke/ffmpeg_vertical.mp4` and `out/smoke/remotion.mp4` on a phone: captions readable, "
              "in time with the voice, clear of the platform buttons; audio clean.",
              "- Listen to `out/smoke/kokoro.wav`: is the voice good enough to use, or should narration be recorded?",
              "- Watch the assembled `out/smoke/SS_*_WORLD_Smoke_Assembly_*.mp4`: do scene changes land on the right words?",
              "- Read `out/smoke/narration.srt` against the narration; add new mishearings to config/glossary.json.",
              "- Record 20 s of real gameplay in OBS and run it through `.\\ss import`, `caption`, `render`."]
    report = ROOT / "reports" / "smoke-test.md"
    report.parent.mkdir(exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report)
    sys.exit(1 if any(s == "FAIL" for _, s, _ in results) else 0)


if __name__ == "__main__":
    main()
