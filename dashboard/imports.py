"""Manual imports, for metrics no authorised API provides (TikTok Studio, Instagram app, YouTube Studio,
Roblox Creator Dashboard share links and acquisition, onboarding funnels).

Two formats:
- platform_metrics: the existing data/templates/platform_metrics_template.csv (`ss export` uses the same file),
  one row per upload per observation. Optional extra columns: account_id, language, concept_id, asset_id,
  platform_video_id.
- long: data/templates/dashboard_metrics_long_template.csv, one row per value:
  date_start,date_end,platform,account_id,entity_type,entity_id,metric,value,breakdown_dim,breakdown_value,note

Strict like `ss observe`: blank stays blank, "1.2K" is stored as 1200 and flagged rounded, bad dates, unknown
metrics or accounts are errors that name the row. A file with errors is refused unless skip_bad is set.
The same file is never imported twice.
"""
import csv
import hashlib
import io
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import research_common as rc  # noqa: E402

from .store import ROOT, metric_defs, now_iso, slugify  # noqa: E402

TEMPLATES = ROOT / "data" / "templates"
PLATFORMS = {"youtube", "tiktok", "instagram", "roblox"}
WATCH = {"average watch time (s)": "avg_view_duration_s", "average watch time": "avg_view_duration_s",
         "avg view duration (s)": "avg_view_duration_s", "average view percentage": "avg_view_pct",
         "avg % viewed": "avg_view_pct", "average percentage viewed": "avg_view_pct",
         "watched full video (%)": "completion_rate", "watched full video": "completion_rate",
         "watch time (min)": "watch_time_minutes", "watch time (minutes)": "watch_time_minutes",
         "watch time (hours)": ("watch_time_minutes", 60)}
PM_NUMERIC = {"views": "views", "likes": "likes", "comments": "comments", "shares": "shares", "saves": "saves",
              "profile_visits": "profile_visits", "link_new_players": "link_new_players"}
FNAME = re.compile(r"SS_\d{8}_([A-Z]+)_([A-Za-z0-9]+)(?:_[A-Za-z0-9]+)?_(V\d+)_[A-Z]+\.mp4$")


def video_id_from_url(platform, url):
    url = url or ""
    pats = {"youtube": [r"youtu\.be/([\w-]{11})", r"[?&]v=([\w-]{11})", r"/shorts/([\w-]{11})"],
            "tiktok": [r"/video/(\d+)"], "instagram": [r"/(?:reel|reels|p)/([\w-]+)"]}
    for p in pats.get(platform, []):
        m = re.search(p, url)
        if m:
            return m.group(1)
    return ""


def _time(s, row_errors, field):
    try:
        t = rc.parse_time(s)
    except ValueError:
        t = None
        row_errors.append(f"{field} '{s}' must look like 2026-11-25T17:00:00Z or 2026-11-25")
    if t and t > datetime.now(timezone.utc).replace(microsecond=0) and field == "observed_at_utc":
        row_errors.append(f"{field} is in the future")
    return t


def _value(raw, errs, field):
    raw = (raw or "").strip()
    if raw.lower() in rc.MISSING:
        return None, False
    s = raw.replace("%", "").strip()
    if re.fullmatch(r"-?\d+\.\d+", s):  # a plain decimal (45.6), not a 1.234 thousands separator
        if not re.fullmatch(r"\d{1,3}\.\d{3}", s):
            return float(s), False
    v, rounded = rc.parse_count(s)
    if v is None:
        errs.append(f"{field} '{raw}' is not a number")
    return v, rounded


def _account(store, platform, account_id, language, errs):
    if account_id:
        a = store.account(account_id)
        if not a:
            errs.append(f"unknown account_id '{account_id}' (add it in Settings)")
        elif a["platform"] != platform:
            errs.append(f"account {account_id} is {a['platform']}, not {platform}")
        return a
    cands = [a for a in store.accounts() if a["platform"] == platform and (not language or a["language"] == language)]
    if len(cands) == 1:
        return cands[0]
    errs.append(f"say which {platform} account (account_id, or language en/es)")
    return None


def detect(header):
    h = set(header)
    if {"metric", "value", "date_start"} <= h:
        return "long"
    if {"platform", "published_url", "observed_at_utc", "views"} <= h:
        return "platform_metrics"
    return None


def run(store, text, file_name="upload.csv", skip_bad=False, dry_run=False):
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    kind = detect(reader.fieldnames or [])
    if not kind:
        return {"ok": False, "errors": ["Unrecognised columns. Use data/templates/platform_metrics_template.csv or "
                                        "data/templates/dashboard_metrics_long_template.csv."]}
    if store.q("SELECT 1 FROM imports WHERE sha256=? AND kind=?", (digest, kind)):
        return {"ok": False, "errors": ["This exact file was imported before; nothing changed."]}
    rows = [r for r in reader if any((v or "").strip() for v in r.values())]
    plan, errors = (_plan_pm if kind == "platform_metrics" else _plan_long)(store, rows)
    rejected = len({e[0] for e in errors})
    if errors and not skip_bad:
        return {"ok": False, "kind": kind, "errors": [f"row {n}: {msg}" for n, msg in errors]}
    ok_rows = [p for p in plan if p["row"] not in {e[0] for e in errors}]
    if dry_run:
        return {"ok": True, "kind": kind, "rows_ok": len(ok_rows), "rows_rejected": rejected, "dry_run": True,
                "errors": [f"row {n}: {m}" for n, m in errors]}
    import_id = f"imp-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{digest[:6]}"
    obs = []
    for p in ok_rows:
        for fn, arg in p.get("registry", []):
            arg_ = dict(arg)
            if fn == "upload" and arg_.get("asset_id") is None:
                arg_.pop("asset_id")
            {"concept": store.save_concept, "asset": store.save_asset, "upload": store.save_upload}[fn](arg_)
        for o in p["obs"]:
            obs.append({**o, "run_id": import_id, "source": f"manual:{kind}"})
    store.put_obs(obs)
    store.x("INSERT INTO imports(import_id, kind, file_name, sha256, imported_at_utc, rows_ok, rows_rejected) VALUES (?,?,?,?,?,?,?)",
            (import_id, kind, Path(file_name).name, digest, now_iso(), len(ok_rows), rejected))
    return {"ok": True, "kind": kind, "import_id": import_id, "rows_ok": len(ok_rows), "rows_rejected": rejected,
            "observations": len(obs), "errors": [f"row {n}: {m}" for n, m in errors]}


def _plan_pm(store, rows):
    plan, errors = [], []
    for n, r in enumerate(rows, 2):
        errs = []
        if (r.get("experiment_id") or "").startswith("EXAMPLE"):
            continue
        platform = (r.get("platform") or "").strip().lower()
        if platform not in PLATFORMS - {"roblox"}:
            errs.append(f"platform '{r.get('platform')}' must be youtube, tiktok or instagram")
        acc = _account(store, platform, (r.get("account_id") or "").strip(), (r.get("language") or "").strip().lower(), errs) if not errs else None
        observed = _time(r.get("observed_at_utc", ""), errs, "observed_at_utc")
        if not (r.get("observed_at_utc") or "").strip():
            errs.append("observed_at_utc is required")
        posted = _time(r.get("posted_at_utc", ""), errs, "posted_at_utc") if (r.get("posted_at_utc") or "").strip() else None
        vid = (r.get("platform_video_id") or "").strip() or video_id_from_url(platform, r.get("published_url", ""))
        if not vid and not errs:
            errs.append("needs published_url (or platform_video_id) to identify the upload")
        registry, asset_id = [], (r.get("asset_id") or "").strip() or None
        ef = (r.get("edit_file") or "").strip()
        m = FNAME.search(ef)
        concept_id = (r.get("concept_id") or "").strip() or (f"CON-{slugify(m.group(2))}" if m else "")
        lang = (r.get("language") or (acc or {}).get("language") or "").lower()
        if concept_id and not asset_id:
            asset_id = f"{concept_id}-{lang.upper() or 'XX'}-{m.group(3) if m else 'V01'}"
        if concept_id:
            registry.append(("concept", {"concept_id": concept_id, "title": m.group(2) if m else concept_id,
                                         "format": (r.get("format") or (m.group(1) if m else "")).upper(),
                                         "hook_type": r.get("hook_type", ""), "slug": r.get("slug", "")}))
            registry.append(("asset", {"asset_id": asset_id, "concept_id": concept_id, "language": lang, "edit_file": ef,
                                       "version": m.group(3) if m else "V01",
                                       "production_minutes": (r.get("production_minutes") or "").replace(",", "") or None}))
        obs = []
        values = {}
        for col, metric in PM_NUMERIC.items():
            v, rounded = _value(r.get(col), errs, col)
            if v is not None:
                values[metric] = (v, rounded)
        wname = (r.get("watch_metric_name") or "").strip().lower()
        wv, wr = _value(r.get("watch_metric_value"), errs, "watch_metric_value")
        if wv is not None:
            target = WATCH.get(wname)
            if not target:
                errs.append(f"watch_metric_name '{r.get('watch_metric_name')}' not recognised ({', '.join(sorted(WATCH))})")
            else:
                metric, scale = target if isinstance(target, tuple) else (target, 1)
                values[metric] = (wv * scale, wr)
        if errs:
            errors += [(n, e) for e in errs]
            continue
        upload = {"platform": platform, "platform_video_id": vid, "account_id": acc["account_id"], "url": r.get("published_url", ""),
                  "published_at_utc": rc.iso(posted) if posted else "", "asset_id": asset_id, "source": "manual"}
        registry.append(("upload", upload))
        uid = f"UPL-{platform}-{vid}"
        existing = store.q("SELECT upload_id FROM uploads WHERE platform=? AND platform_video_id=?", (platform, vid))
        uid = existing[0]["upload_id"] if existing else uid
        for metric, (v, rounded) in values.items():
            obs.append({"platform": platform, "account_id": acc["account_id"], "entity_type": "upload", "entity_id": uid,
                        "metric": metric, "value": v, "period_type": "lifetime", "period_start": "",
                        "period_end": rc.iso(observed)[:10], "observed_at_utc": rc.iso(observed),
                        "note": "rounded as displayed" if rounded else (r.get("notes") or "")[:200]})
        plan.append({"row": n, "registry": registry, "obs": obs})
    return plan, errors


def _plan_long(store, rows):
    known = {m["id"]: m for m in metric_defs()["metrics"]}
    plan, errors = [], []
    for n, r in enumerate(rows, 2):
        errs = []
        platform = (r.get("platform") or "").strip().lower()
        if platform not in PLATFORMS:
            errs.append(f"platform '{r.get('platform')}' unknown")
        metric = (r.get("metric") or "").strip()
        if metric not in known:
            errs.append(f"metric '{metric}' unknown (see config/dashboard/metrics.json)")
        acc = _account(store, platform, (r.get("account_id") or "").strip(), "", errs) if platform in PLATFORMS else None
        try:
            d0 = date.fromisoformat((r.get("date_start") or "").strip())
            d1 = date.fromisoformat((r.get("date_end") or r.get("date_start") or "").strip())
            if d1 < d0:
                errs.append("date_end is before date_start")
            if d1 > date.today():
                errs.append("date_end is in the future")
        except ValueError:
            errs.append("dates must be YYYY-MM-DD")
            d0 = d1 = None
        et = (r.get("entity_type") or "account").strip()
        if et not in ("account", "upload", "experience"):
            errs.append("entity_type must be account, upload or experience")
        v, rounded = _value(r.get("value"), errs, "value")
        if v is None and not errs:
            errs.append("value is blank (leave the row out instead)")
        if errs:
            errors += [(n, e) for e in errs]
            continue
        eid = (r.get("entity_id") or "").strip() or (acc["external_id"] or acc["account_id"] if et == "experience" else acc["account_id"])
        if et == "upload" and not eid.startswith("UPL-"):
            eid = f"UPL-{platform}-{eid}"
        plan.append({"row": n, "obs": [{
            "platform": platform, "account_id": acc["account_id"], "entity_type": et, "entity_id": eid, "metric": metric,
            "value": v, "period_type": "day" if d0 == d1 else "window", "period_start": d0.isoformat(), "period_end": d1.isoformat(),
            "breakdown_dim": (r.get("breakdown_dim") or "").strip(), "breakdown_value": (r.get("breakdown_value") or "").strip(),
            "observed_at_utc": now_iso(), "note": "rounded as displayed" if rounded else (r.get("note") or "")[:200]}]})
    return plan, errors
