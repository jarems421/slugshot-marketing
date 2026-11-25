"""SQLite store for the dashboard (data/local/dashboard/slugshot.db, git-ignored).

Identifiers (stable, human-readable):
- account_id   one of our own accounts, e.g. yt-en, tt-es, rbx-slugshot (config/dashboard/settings.json)
- concept_id   a creative idea, e.g. CON-FLOPPY-UNDERDOG; language-neutral
- asset_id     one edited video of a concept in one language, e.g. CON-FLOPPY-UNDERDOG-EN-V01
- upload_id    one platform upload of an asset, e.g. UPL-youtube-<video id>
- job_id       one publishing job (draft -> owner approval -> upload), e.g. PUB-20261125-101500-yt-en
Experiments compare assets or concepts. Uploading the same asset to three platforms is one unit with
three measurements, never three experiments.

Metric observations are long format. Missing = no row. A provider that doesn't offer a metric writes
status 'unavailable' (value NULL). A real zero is value 0. Staleness is read from observed_at_utc.
"""
import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "local" / "dashboard"
CONFIG = ROOT / "config" / "dashboard"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
  account_id TEXT PRIMARY KEY, platform TEXT NOT NULL, language TEXT NOT NULL DEFAULT '',
  label TEXT NOT NULL DEFAULT '', handle TEXT NOT NULL DEFAULT '', external_id TEXT NOT NULL DEFAULT '',
  active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS concepts (
  concept_id TEXT PRIMARY KEY, title TEXT NOT NULL, format TEXT NOT NULL DEFAULT '', hook_type TEXT NOT NULL DEFAULT '',
  hook_text TEXT NOT NULL DEFAULT '', slug TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
  created_at_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY, concept_id TEXT NOT NULL REFERENCES concepts(concept_id), language TEXT NOT NULL DEFAULT '',
  version TEXT NOT NULL DEFAULT 'V01', edit_file TEXT NOT NULL DEFAULT '', production_minutes REAL,
  fiction_label TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', created_at_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS uploads (
  upload_id TEXT PRIMARY KEY, asset_id TEXT REFERENCES assets(asset_id), account_id TEXT, platform TEXT NOT NULL,
  platform_video_id TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '', title TEXT NOT NULL DEFAULT '',
  published_at_utc TEXT NOT NULL DEFAULT '', duration_s REAL, source TEXT NOT NULL DEFAULT '',
  UNIQUE(platform, platform_video_id));
CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY, platform TEXT NOT NULL, account_id TEXT NOT NULL DEFAULT '',
  entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, metric TEXT NOT NULL,
  value REAL, status TEXT NOT NULL DEFAULT 'value',
  period_type TEXT NOT NULL, period_start TEXT NOT NULL DEFAULT '', period_end TEXT NOT NULL DEFAULT '',
  breakdown_dim TEXT NOT NULL DEFAULT '', breakdown_value TEXT NOT NULL DEFAULT '',
  observed_at_utc TEXT NOT NULL, snapshot_key TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL, provenance TEXT NOT NULL DEFAULT 'P1', run_id TEXT NOT NULL DEFAULT '',
  expires_at_utc TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '',
  UNIQUE(platform, entity_type, entity_id, metric, period_type, period_start, period_end,
         breakdown_dim, breakdown_value, source, snapshot_key));
CREATE INDEX IF NOT EXISTS obs_lookup ON observations(platform, entity_type, metric, period_start);
CREATE INDEX IF NOT EXISTS obs_entity ON observations(entity_id);
CREATE TABLE IF NOT EXISTS experiments (
  experiment_id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'proposed',
  hypothesis TEXT NOT NULL DEFAULT '', one_change TEXT NOT NULL DEFAULT '', design TEXT NOT NULL DEFAULT '',
  primary_metric TEXT NOT NULL DEFAULT '', secondary_metrics TEXT NOT NULL DEFAULT '[]',
  window_hours REAL, stop_rule TEXT NOT NULL DEFAULT '', threshold TEXT NOT NULL DEFAULT '',
  platforms TEXT NOT NULL DEFAULT '[]', language TEXT NOT NULL DEFAULT '', campaign TEXT NOT NULL DEFAULT '',
  results TEXT NOT NULL DEFAULT '', limitations TEXT NOT NULL DEFAULT '', decision TEXT NOT NULL DEFAULT '',
  next_action TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '',
  created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS variants (
  experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE, variant_id TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'treatment', label TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
  asset_ids TEXT NOT NULL DEFAULT '[]', PRIMARY KEY (experiment_id, variant_id));
CREATE TABLE IF NOT EXISTS sync_runs (
  run_id TEXT PRIMARY KEY, connector TEXT NOT NULL, account_id TEXT NOT NULL DEFAULT '',
  started_at_utc TEXT NOT NULL, finished_at_utc TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'running',
  rows_written INTEGER NOT NULL DEFAULT 0, requests_ok INTEGER NOT NULL DEFAULT 0, requests_failed INTEGER NOT NULL DEFAULT 0,
  message TEXT NOT NULL DEFAULT '', fixture INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS imports (
  import_id TEXT PRIMARY KEY, kind TEXT NOT NULL, file_name TEXT NOT NULL, sha256 TEXT NOT NULL,
  imported_at_utc TEXT NOT NULL, rows_ok INTEGER NOT NULL, rows_rejected INTEGER NOT NULL, UNIQUE(sha256, kind));
CREATE TABLE IF NOT EXISTS publish_jobs (
  job_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id), account_id TEXT NOT NULL,
  platform TEXT NOT NULL, route TEXT NOT NULL, video_path TEXT NOT NULL, fields TEXT NOT NULL DEFAULT '{}',
  experiment_id TEXT NOT NULL DEFAULT '', variant_id TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT 'draft',
  approval TEXT NOT NULL DEFAULT '', result TEXT NOT NULL DEFAULT '{}', log TEXT NOT NULL DEFAULT '[]',
  upload_id TEXT NOT NULL DEFAULT '', created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS prefs (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hosted_assets (
  sha256 TEXT PRIMARY KEY, provider TEXT NOT NULL, public_id TEXT NOT NULL, state TEXT NOT NULL,
  version TEXT NOT NULL DEFAULT '', format TEXT NOT NULL DEFAULT '', bytes INTEGER, last_error TEXT NOT NULL DEFAULT '',
  created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL, deleted_at_utc TEXT NOT NULL DEFAULT '');
"""

_lock = threading.RLock()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def db_path():
    import os
    return Path(os.environ.get("SLUGSHOT_DASH_DB") or DATA / "slugshot.db")


def is_fixture_db():
    import os
    return bool(os.environ.get("SLUGSHOT_DASH_FIXTURE"))


def settings():
    return json.loads((CONFIG / "settings.json").read_text(encoding="utf-8"))


def metric_defs():
    return json.loads((CONFIG / "metrics.json").read_text(encoding="utf-8"))


class Store:
    def __init__(self, path=None):
        self.path = Path(path or db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        with _lock:
            self.conn.executescript(SCHEMA)
            self._seed()

    # ---- basics
    def q(self, sql, args=()):
        with _lock:
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def x(self, sql, args=()):
        with _lock, self.conn:
            return self.conn.execute(sql, args)

    def many(self, sql, rows):
        with _lock, self.conn:
            self.conn.executemany(sql, rows)

    def pref(self, key, default=None):
        r = self.q("SELECT value FROM prefs WHERE key=?", (key,))
        return json.loads(r[0]["value"]) if r else default

    def set_pref(self, key, value):
        self.x("INSERT OR REPLACE INTO prefs(key, value) VALUES (?, ?)", (key, json.dumps(value)))

    def _seed(self):
        """Accounts from settings.json (new ones only) and seed experiments, once per database."""
        for a in settings().get("accounts", []):
            self.conn.execute(
                "INSERT OR IGNORE INTO accounts(account_id, platform, language, label, handle, external_id, active) VALUES (?,?,?,?,?,?,?)",
                (a["account_id"], a["platform"], a.get("language", ""), a.get("label", ""), a.get("handle", ""),
                 a.get("external_id", ""), 1 if a.get("active", True) else 0))
            if a.get("handle"):  # fill a blank handle from settings; never overwrite one set in the dashboard
                self.conn.execute("UPDATE accounts SET handle=? WHERE account_id=? AND handle=''", (a["handle"], a["account_id"]))
        if not self.q("SELECT 1 FROM prefs WHERE key='seeded_experiments'"):
            seed = json.loads((CONFIG / "experiments_seed.json").read_text(encoding="utf-8"))
            for e in seed["experiments"]:
                self.save_experiment(e, commit=False)
            self.conn.execute("INSERT INTO prefs(key, value) VALUES ('seeded_experiments', 'true')")
        self.conn.commit()

    # ---- accounts
    def accounts(self):
        return self.q("SELECT * FROM accounts ORDER BY platform, language")

    def account(self, account_id):
        r = self.q("SELECT * FROM accounts WHERE account_id=?", (account_id,))
        return r[0] if r else None

    def save_account(self, a):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", a.get("account_id", "")):
            raise ValueError("account_id: lowercase letters, digits and dashes")
        if a.get("platform") not in {"youtube", "tiktok", "instagram", "roblox"}:
            raise ValueError("platform must be youtube, tiktok, instagram or roblox")
        if a.get("language", "") not in {"", "en", "es"}:
            raise ValueError("language must be en, es or blank")
        self.x("""INSERT INTO accounts(account_id, platform, language, label, handle, external_id, active)
                  VALUES (?,?,?,?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET platform=excluded.platform,
                  language=excluded.language, label=excluded.label, handle=excluded.handle,
                  external_id=excluded.external_id, active=excluded.active""",
               (a["account_id"], a["platform"], a.get("language", ""), a.get("label", "") or a["account_id"],
                a.get("handle", ""), a.get("external_id", ""), 1 if a.get("active", True) else 0))

    # ---- content registry
    def save_concept(self, c):
        cid = c.get("concept_id") or "CON-" + slugify(c.get("title", ""))
        if not re.fullmatch(r"CON-[A-Z0-9-]{2,60}", cid):
            raise ValueError("concept_id must look like CON-FLOPPY-UNDERDOG")
        self.x("""INSERT INTO concepts(concept_id, title, format, hook_type, hook_text, slug, notes, created_at_utc)
                  VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(concept_id) DO UPDATE SET title=excluded.title,
                  format=excluded.format, hook_type=excluded.hook_type, hook_text=excluded.hook_text,
                  slug=excluded.slug, notes=excluded.notes""",
               (cid, c.get("title") or cid, c.get("format", ""), c.get("hook_type", ""), c.get("hook_text", ""),
                c.get("slug", ""), c.get("notes", ""), now_iso()))
        return cid

    def save_asset(self, a):
        concept = a["concept_id"]
        if not self.q("SELECT 1 FROM concepts WHERE concept_id=?", (concept,)):
            raise ValueError(f"unknown concept {concept}")
        lang = a.get("language", "")
        version = (a.get("version") or "V01").upper()
        aid = a.get("asset_id") or f"{concept}-{lang.upper() or 'XX'}-{version}"
        self.x("""INSERT INTO assets(asset_id, concept_id, language, version, edit_file, production_minutes, fiction_label, notes, created_at_utc)
                  VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(asset_id) DO UPDATE SET language=excluded.language,
                  version=excluded.version, edit_file=excluded.edit_file, production_minutes=excluded.production_minutes,
                  fiction_label=excluded.fiction_label, notes=excluded.notes""",
               (aid, concept, lang, version, a.get("edit_file", ""), num_or_none(a.get("production_minutes")),
                a.get("fiction_label", ""), a.get("notes", ""), now_iso()))
        return aid

    def save_upload(self, u):
        platform, vid = u["platform"], (u.get("platform_video_id") or "").strip()
        if not vid:
            raise ValueError("platform_video_id is required")
        uid = u.get("upload_id") or f"UPL-{platform}-{vid}"
        existing = self.q("SELECT * FROM uploads WHERE platform=? AND platform_video_id=?", (platform, vid))
        if existing:
            old = existing[0]
            uid = old["upload_id"]
            merged = {k: (u.get(k) if u.get(k) not in (None, "") else old[k]) for k in old}
            self.x("""UPDATE uploads SET asset_id=?, account_id=?, url=?, title=?, published_at_utc=?, duration_s=?
                      WHERE upload_id=?""", (merged["asset_id"], merged["account_id"], merged["url"], merged["title"],
                                             merged["published_at_utc"], merged["duration_s"], uid))
        else:
            self.x("""INSERT INTO uploads(upload_id, asset_id, account_id, platform, platform_video_id, url, title, published_at_utc, duration_s, source)
                      VALUES (?,?,?,?,?,?,?,?,?,?)""",
                   (uid, u.get("asset_id") or None, u.get("account_id", ""), platform, vid, u.get("url", ""),
                    u.get("title", ""), u.get("published_at_utc", ""), num_or_none(u.get("duration_s")), u.get("source", "")))
        return uid

    # ---- observations
    def put_obs(self, rows):
        """rows: dicts with platform, account_id, entity_type, entity_id, metric, value, period_type,
        period_start, period_end, observed_at_utc, source; optional status, breakdown_dim/value, provenance,
        run_id, expires_at_utc, note. 'lifetime' and 'point' observations keep every snapshot (velocity);
        'day' and 'window' observations replace the earlier reading of the same period (deduplication)."""
        out = []
        for r in rows:
            snap = r["observed_at_utc"] if r["period_type"] in ("lifetime", "point") else ""
            value = r.get("value")
            status = r.get("status") or ("value" if value is not None else "unavailable")
            out.append((r["platform"], r.get("account_id", ""), r["entity_type"], r["entity_id"], r["metric"],
                        value, status, r["period_type"], r.get("period_start", ""), r.get("period_end", ""),
                        r.get("breakdown_dim", ""), r.get("breakdown_value", ""), r["observed_at_utc"], snap,
                        r["source"], r.get("provenance", "P1"), r.get("run_id", ""), r.get("expires_at_utc", ""),
                        r.get("note", "")))
        self.many("""INSERT INTO observations(platform, account_id, entity_type, entity_id, metric, value, status, period_type,
                     period_start, period_end, breakdown_dim, breakdown_value, observed_at_utc, snapshot_key, source,
                     provenance, run_id, expires_at_utc, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                     ON CONFLICT(platform, entity_type, entity_id, metric, period_type, period_start, period_end,
                     breakdown_dim, breakdown_value, source, snapshot_key) DO UPDATE SET value=excluded.value,
                     status=excluded.status, observed_at_utc=excluded.observed_at_utc, run_id=excluded.run_id,
                     account_id=excluded.account_id, expires_at_utc=excluded.expires_at_utc, note=excluded.note""", out)
        return len(out)

    def forget_source(self, source_prefix, account_id=None):
        """Delete data from one source (used when an owner disconnects an account)."""
        sql, args = "DELETE FROM observations WHERE source LIKE ?", [source_prefix + "%"]
        if account_id:
            sql += " AND account_id=?"
            args.append(account_id)
        return self.x(sql, args).rowcount

    def prune_expired(self):
        return self.x("DELETE FROM observations WHERE expires_at_utc != '' AND expires_at_utc < ?", (now_iso(),)).rowcount

    # ---- experiments
    def save_experiment(self, e, commit=True):
        eid = e.get("experiment_id") or f"EXP-{datetime.now(timezone.utc):%Y%m%d}-{slugify(e.get('title', ''))[:24]}"
        if not re.fullmatch(r"EXP-[A-Z0-9-]{3,60}", eid):
            raise ValueError("experiment_id must look like EXP-20261124-OPENER")
        if e.get("status", "proposed") not in STATUSES:
            raise ValueError("status must be one of " + ", ".join(STATUSES))
        ts = now_iso()
        vals = (eid, e.get("title") or eid, e.get("status", "proposed"), e.get("hypothesis", ""), e.get("one_change", ""),
                e.get("design", ""), e.get("primary_metric", ""), json.dumps(e.get("secondary_metrics", [])),
                num_or_none(e.get("window_hours")), e.get("stop_rule", ""), e.get("threshold", ""),
                json.dumps(e.get("platforms", [])), e.get("language", ""), e.get("campaign", ""), e.get("results", ""),
                e.get("limitations", ""), e.get("decision", ""), e.get("next_action", ""), e.get("source", ""), ts, ts)
        conn = self.conn
        with _lock:
            conn.execute("""INSERT INTO experiments(experiment_id, title, status, hypothesis, one_change, design, primary_metric,
                secondary_metrics, window_hours, stop_rule, threshold, platforms, language, campaign, results, limitations,
                decision, next_action, source, created_at_utc, updated_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(experiment_id) DO UPDATE SET title=excluded.title, status=excluded.status,
                hypothesis=excluded.hypothesis, one_change=excluded.one_change, design=excluded.design,
                primary_metric=excluded.primary_metric, secondary_metrics=excluded.secondary_metrics,
                window_hours=excluded.window_hours, stop_rule=excluded.stop_rule, threshold=excluded.threshold,
                platforms=excluded.platforms, language=excluded.language, campaign=excluded.campaign,
                results=excluded.results, limitations=excluded.limitations, decision=excluded.decision,
                next_action=excluded.next_action, source=excluded.source, updated_at_utc=excluded.updated_at_utc""", vals)
            if "variants" in e:
                conn.execute("DELETE FROM variants WHERE experiment_id=?", (eid,))
                for v in e["variants"]:
                    conn.execute("INSERT INTO variants(experiment_id, variant_id, role, label, description, asset_ids) VALUES (?,?,?,?,?,?)",
                                 (eid, v.get("variant_id") or "A", v.get("role", "treatment"), v.get("label", ""),
                                  v.get("description", ""), json.dumps(v.get("asset_ids", []))))
            if commit:
                conn.commit()
        return eid

    def experiments(self):
        exps = self.q("SELECT * FROM experiments ORDER BY created_at_utc DESC")
        for e in exps:
            e["secondary_metrics"] = json.loads(e["secondary_metrics"])
            e["platforms"] = json.loads(e["platforms"])
            e["variants"] = self.q("SELECT * FROM variants WHERE experiment_id=? ORDER BY variant_id", (e["experiment_id"],))
            for v in e["variants"]:
                v["asset_ids"] = json.loads(v["asset_ids"])
        return exps

    # ---- sync runs
    def start_run(self, run_id, connector, account_id=""):
        self.x("INSERT INTO sync_runs(run_id, connector, account_id, started_at_utc, fixture) VALUES (?,?,?,?,?)",
               (run_id, connector, account_id, now_iso(), 1 if is_fixture_db() else 0))

    def finish_run(self, run_id, status, rows=0, ok=0, failed=0, message=""):
        self.x("""UPDATE sync_runs SET finished_at_utc=?, status=?, rows_written=?, requests_ok=?, requests_failed=?, message=?
                  WHERE run_id=?""", (now_iso(), status, rows, ok, failed, message[:500], run_id))

    def last_runs(self):
        return self.q("""SELECT s.* FROM sync_runs s JOIN (SELECT connector, account_id, MAX(started_at_utc) m FROM sync_runs
                         GROUP BY connector, account_id) t ON s.connector=t.connector AND s.account_id=t.account_id
                         AND s.started_at_utc=t.m ORDER BY s.connector, s.account_id""")

    def last_success(self, connector, account_id=""):
        r = self.q("""SELECT MAX(finished_at_utc) t FROM sync_runs WHERE connector=? AND account_id=? AND status IN ('ok','partial')""",
                   (connector, account_id))
        return r[0]["t"] if r and r[0]["t"] else None


STATUSES = ["proposed", "planned", "running", "analysing", "decided", "abandoned"]


def slugify(s):
    return re.sub(r"[^A-Z0-9]+", "-", (s or "").upper()).strip("-")[:48] or "UNTITLED"


def num_or_none(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise ValueError(f"'{v}' is not a number")
