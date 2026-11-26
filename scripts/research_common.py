"""Shared plumbing for the research collectors (YouTube, Wikimedia, Google Trends, Twitch, Roblox, observations).

Conventions every collector follows (full schema: docs/research-data.md):
- Times are ISO 8601 UTC with an explicit +00:00 offset. `observed_at_utc` = when we read the value.
- Missing values are blank, never 0. Raw provider values are kept as the provider gave them.
- Every run gets a `run_id` and a row in data/local/research/runs.csv with the exact parameters sent.
- Provider files stay separate (no merging across platforms). Each row carries `expires_at_utc` when the
  provider's terms limit storage; `ss research prune` deletes expired rows and expired exports.
- Exports for ChatGPT go to exports/share/research/ with a CSV, a JSON copy, a _README.md data dictionary
  and a line in MANIFEST.csv. Providers whose terms are unclear write to data/local/research/<p>/reports/.
Credentials come from the environment or the git-ignored .env and are never printed or logged.
"""
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "local" / "research"
SHARE = ROOT / "exports" / "share" / "research"
CONFIG = ROOT / "config" / "research"
FIXTURES = ROOT / "tests" / "fixtures" / "research"
PROVENANCE = {
    "P1": "first-party measured: the platform's own count, as displayed or returned (may be rounded)",
    "P2": "first-party sampled or normalised: a platform index, rank or 0-100 scale, not a count",
    "P3": "third-party reported or estimated: a tool's figure (e.g. vidIQ), not confirmed by the platform",
    "P4": "qualitative interpretation: a description, hook or format reading by a person or AI",
}
csv.field_size_limit(10_000_000)


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat() if dt else ""


def parse_time(s):
    """ISO 8601 (Z or offset) or plain YYYY-MM-DD (taken as 00:00 UTC). Returns aware UTC datetime or None."""
    s = (s or "").strip()
    if not s:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def settings():
    return json.loads((CONFIG / "settings.json").read_text(encoding="utf-8"))


def load_json_config(name):
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def env_value(name):
    """Read a credential from the environment or .env. Never print the result."""
    v = os.environ.get(name, "")
    env = ROOT / ".env"
    if not v and env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            if line.strip().startswith(name + "="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
    return v


def new_run_id(provider):
    return f"{provider}-{now():%Y%m%dT%H%M%SZ}-{os.urandom(2).hex()}"


class Run:
    """One collection run: counts requests (failed ones too) and writes a runs.csv row at the end."""
    FIELDS = ["run_id", "provider", "command", "started_at_utc", "finished_at_utc", "params_json",
              "requests_ok", "requests_failed", "cost_units", "rows_written", "status", "note", "dry_run"]

    def __init__(self, provider, command, params, dry_run, data_dir=None):
        self.provider, self.command, self.params, self.dry_run = provider, command, params, dry_run
        self.id = ("dryrun-" if dry_run else "") + new_run_id(provider)
        self.started = now()
        self.ok = self.failed = self.units = self.rows = 0
        self.dir = Path(data_dir) if data_dir else DATA / ("dryrun" if dry_run else "")
        self.dir.mkdir(parents=True, exist_ok=True)

    def finish(self, status="ok", note=""):
        row = {"run_id": self.id, "provider": self.provider, "command": self.command,
               "started_at_utc": iso(self.started), "finished_at_utc": iso(now()),
               "params_json": json.dumps(self.params, ensure_ascii=False, sort_keys=True),
               "requests_ok": self.ok, "requests_failed": self.failed, "cost_units": self.units,
               "rows_written": self.rows, "status": status, "note": note, "dry_run": str(self.dry_run).lower()}
        append_rows(self.dir / "runs.csv", self.FIELDS, [row])


class HttpError(Exception):
    def __init__(self, status, reason):
        super().__init__(f"HTTP {status}: {reason}")
        self.status, self.reason = status, reason


def http(url, params=None, headers=None, data=None, timeout=30, user_agent=None):
    """GET (or POST when data is given). Returns (body_bytes, response_headers). Error messages never
    contain the URL or query string, because some providers put credentials there."""
    full = url + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    h = {"User-Agent": user_agent or ua(), **(headers or {})}
    body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
    req = urllib.request.Request(full, data=body, headers=h, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        try:
            raw = e.read()[:2000].decode("utf-8", "replace")
            j = json.loads(raw)
            err = j.get("error", j)
            reason = err.get("message") if isinstance(err, dict) else str(err)
            reason = reason or j.get("message") or raw[:200]
        except Exception:
            reason = e.reason
        raise HttpError(e.code, redact(str(reason))) from None
    except urllib.error.URLError as e:
        raise HttpError(0, f"network error: {e.reason}") from None


def redact(text):
    for name in ("YOUTUBE_API_KEY", "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "COMPOSIO_API_KEY", "APIFY_TOKEN"):
        v = env_value(name)
        if v and len(v) > 6:
            text = text.replace(v, "[redacted]")
    return text


def ua():
    contact = settings().get("contact", "")
    return f"SlugshotMarketingResearch/1.0 (internal research tool; {contact or 'no contact set'}) python-urllib"


def fixture(name):
    p = FIXTURES / name
    return p.read_bytes()


def read_rows(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_rows(path, fields, rows):
    """Append rows; if the file's header is older than `fields`, rewrite it with the new columns (blank)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            header = next(csv.reader(f), [])
        if header != list(fields):
            old = read_rows(path)
            write_rows(path, fields, old)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


def write_rows(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def prune_file(path, fields, at=None):
    """Delete rows whose expires_at_utc has passed. Returns rows removed."""
    rows = read_rows(path)
    at = at or now()
    keep = [r for r in rows if not r.get("expires_at_utc") or parse_time(r["expires_at_utc"]) > at]
    if len(keep) != len(rows):
        write_rows(path, fields, keep)
    return len(rows) - len(keep)


# ---------- exports ----------

MANIFEST_FIELDS = ["file", "provider", "generated_at_utc", "rows", "provenance", "retention_rule",
                   "expires_at_utc", "share_status", "dry_run"]


def export(provider, stem, rows, columns, *, notes, provenance, retention_rule, expires_at, share, dry_run,
           out_dir=None, extra_meta=None):
    """Write CSV + JSON + _README.md. `columns` is [(name, source, meaning)]. `share` False keeps the files
    local (data/local/research/<provider>/reports). Returns the CSV path."""
    stamp = f"{now():%Y%m%dT%H%MZ}"
    name = ("dryrun_" if dry_run else "") + f"{stem}_{stamp}"
    base = Path(out_dir) if out_dir else (SHARE if share and not dry_run else DATA / ("dryrun" if dry_run else "") / provider / "reports")
    base.mkdir(parents=True, exist_ok=True)
    cols = [c for c, _, _ in columns]
    csv_path = base / f"{name}.csv"
    write_rows(csv_path, cols, rows)
    meta = {"provider": provider, "generated_at_utc": iso(now()), "rows": len(rows), "provenance": provenance,
            "retention_rule": retention_rule, "expires_at_utc": iso(expires_at) if expires_at else "",
            "share_status": "shareable for internal analysis" if share else "LOCAL ONLY: do not share yet",
            "dry_run": dry_run, **(extra_meta or {})}
    (base / f"{name}.json").write_text(json.dumps({"meta": meta, "columns": [
        {"name": c, "source": s, "meaning": m} for c, s, m in columns],
        "rows": [{c: r.get(c, "") for c in cols} for r in rows]}, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# {name}.csv", ""]
    if dry_run:
        lines += ["**FAKE TEST DATA from fixtures. Do not analyse.**", ""]
    lines += [f"- Provider: {provider}", f"- Generated: {meta['generated_at_utc']}", f"- Rows: {len(rows)}",
              f"- Provenance: {provenance}" + (f" ({PROVENANCE[provenance]})" if provenance in PROVENANCE else ""),
              f"- Retention: {retention_rule}" + (f"; delete or refresh by {meta['expires_at_utc']}" if expires_at else ""),
              f"- Sharing: {meta['share_status']}", "", "| column | source | meaning |", "|---|---|---|"]
    lines += [f"| {c} | {s} | {m} |" for c, s, m in columns]
    lines += ["", "How to read it:"] + [f"- {n}" for n in notes + [
        "Blank means unknown or not available. Never treat blank as 0.",
        "Times are UTC. observed_at_utc is when the collector read the value."]]
    (base / f"{name}_README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if base == SHARE or out_dir:
        append_rows(base / "MANIFEST.csv", MANIFEST_FIELDS, [{
            "file": csv_path.name, "provider": provider, "generated_at_utc": meta["generated_at_utc"], "rows": len(rows),
            "provenance": provenance, "retention_rule": retention_rule, "expires_at_utc": meta["expires_at_utc"],
            "share_status": meta["share_status"], "dry_run": str(dry_run).lower()}])
        rebuild_dictionary(base)
    return csv_path


def rebuild_dictionary(base):
    """DATA_DICTIONARY.md: every export listed in MANIFEST.csv, then the column dictionary of the newest export of
    each kind, so one file explains everything in the folder."""
    base = Path(base)
    man = read_rows(base / "MANIFEST.csv")
    lines = ["# Research exports: data dictionary", "",
             f"Rebuilt {iso(now())}. Upload this file with the CSV/JSON exports. Provenance codes: " +
             "; ".join(f"{k} = {v}" for k, v in PROVENANCE.items()) + ".", "",
             "## Files in this folder", "", "| file | provider | rows | provenance | retention | expires | sharing |",
             "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['file']} | {r['provider']} | {r['rows']} | {r['provenance']} | {r['retention_rule']} | "
              f"{r['expires_at_utc'] or 'none'} | {r['share_status']} |" for r in man]
    newest = {}
    for r in man:
        kind = re.sub(r"_\d{8}T\d{4}Z\.csv$", "", r["file"])
        newest[kind] = r["file"]
    for kind, f in sorted(newest.items()):
        readme = base / (f[:-4] + "_README.md")
        if readme.exists():
            body = readme.read_text(encoding="utf-8").splitlines()
            lines += ["", f"## {kind}", ""] + [l for l in body[1:] if not l.startswith("- Generated") and not l.startswith("- Rows")]
    (base / "DATA_DICTIONARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def prune_exports(base=SHARE, at=None):
    """Delete exported files (csv/json/README) whose manifest expiry has passed."""
    manifest = Path(base) / "MANIFEST.csv"
    removed = []
    at = at or now()
    keep = []
    for r in read_rows(manifest):
        if r.get("expires_at_utc") and parse_time(r["expires_at_utc"]) <= at:
            stem = r["file"][:-4]
            for suffix in (".csv", ".json", "_README.md"):
                p = Path(base) / (stem + suffix)
                if p.exists():
                    p.unlink()
            removed.append(r["file"])
        else:
            keep.append(r)
    if removed:
        write_rows(manifest, MANIFEST_FIELDS, keep)
    if manifest.exists():
        rebuild_dictionary(base)
    return removed


# ---------- small parsers shared by importers ----------

SUFFIX = {"k": 1e3, "m": 1e6, "b": 1e9, "mil": 1e3, "mill": 1e6, "mm": 1e6}
MISSING = {"", "-", "—", "–", "n/a", "na", "none", "null", "unknown", "?", "blank", "not shown", "hidden"}


def parse_count(raw):
    """'24.5K' -> (24500, True); '3,400' -> (3400, False); '' -> (None, False). Rounded flag = shown abbreviated."""
    s = str(raw or "").strip()
    if s.lower() in MISSING:
        return None, False
    t = s.lower().replace(" ", "").replace(" ", "")
    m = re.fullmatch(r"([0-9]+(?:[.,][0-9]+)*)(k|m|b|mil|mill|mm)?\+?", t)
    if not m:
        return None, False
    num, suf = m.groups()
    if suf:
        num = num.replace(",", ".") if num.count(",") == 1 and "." not in num else num.replace(",", "")
        return int(round(float(num) * SUFFIX[suf])), True
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", num):  # thousands separators, either style
        return int(re.sub(r"[.,]", "", num)), False
    if re.fullmatch(r"\d+", num):
        return int(num), False
    return None, False


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pacific_day(dt):
    """YouTube quotas reset at midnight US Pacific time (US DST rules). Returns the quota day as YYYY-MM-DD."""
    y = dt.year
    mar = datetime(y, 3, 8, 10, tzinfo=timezone.utc)  # 2nd Sunday of March, 02:00 PST = 10:00 UTC
    mar += timedelta(days=(6 - mar.weekday()) % 7)
    nov = datetime(y, 11, 1, 9, tzinfo=timezone.utc)  # 1st Sunday of November, 02:00 PDT = 09:00 UTC
    nov += timedelta(days=(6 - nov.weekday()) % 7)
    offset = 7 if mar <= dt < nov else 8
    return (dt - timedelta(hours=offset)).date().isoformat()


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)
