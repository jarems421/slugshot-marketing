"""Read models for the five pages. All arithmetic rules live here:

- Never add across platforms. Totals are per platform (EN + ES accounts of one platform may be added,
  since they are the same owner on the same platform) and per account.
- 'count' metrics are summed over days within one account and platform; 'rate' and 'level' metrics are
  never summed (rates are shown per cohort/day, levels as the latest reading).
- Lifetime (cumulative) counts and period counts are labelled separately and never mixed.
- Nothing divides one funnel stage by another: stages are different populations.
"""
import csv
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .connectors import CONNECTORS, BY_PLATFORM
from .store import ROOT, metric_defs

RESEARCH = ROOT / "data" / "local" / "research"
RCONFIG = ROOT / "config" / "research"
SOCIAL = ["youtube", "tiktok", "instagram"]


def _rows(path):
    try:
        with Path(path).open(newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def window(f):
    end = f.get("end") or date.today().isoformat()
    start = f.get("start") or (date.fromisoformat(end) - timedelta(days=27)).isoformat()
    return start, end


def account_filter(store, f):
    plats = [p for p in (f.get("platform") or "").split(",") if p]
    lang = f.get("language") or ""
    return [a for a in store.accounts() if a["active"] and (not plats or a["platform"] in plats)
            and (not lang or a["language"] in (lang, ""))]


def _in(ids):
    return ",".join("?" * len(ids)) or "''"


def day_sum(store, accounts, metric, start, end):
    ids = [a["account_id"] for a in accounts]
    r = store.q(f"""SELECT SUM(value) v, COUNT(value) n FROM observations WHERE account_id IN ({_in(ids)}) AND metric=? AND
                    period_type='day' AND breakdown_dim='' AND status='value' AND period_start BETWEEN ? AND ?""",
                (*ids, metric, start, end))[0]
    return r["v"] if r["n"] else None


def day_avg(store, accounts, metric, start, end):
    """Average per day of a 'daily' metric (people recur across days, so days are never added)."""
    ids = [a["account_id"] for a in accounts]
    r = store.q(f"""SELECT AVG(v) v, COUNT(*) n FROM (SELECT period_start, SUM(value) v FROM observations WHERE account_id IN ({_in(ids)})
                    AND metric=? AND period_type='day' AND breakdown_dim='' AND status='value' AND period_start BETWEEN ? AND ?
                    GROUP BY period_start)""", (*ids, metric, start, end))[0]
    return r["v"] if r["n"] else None


def latest_level(store, accounts, metric, end, entity_type="account"):
    """Sum over accounts of each account's latest reading at or before `end`."""
    total, seen, at = 0, 0, None
    for a in accounts:
        r = store.q("""SELECT value, observed_at_utc FROM observations WHERE account_id=? AND metric=? AND entity_type=?
                       AND period_type='point' AND status='value' AND period_start<=? ORDER BY observed_at_utc DESC LIMIT 1""",
                    (a["account_id"], metric, entity_type, end))
        if r:
            total += r[0]["value"]
            seen += 1
            at = max(at or "", r[0]["observed_at_utc"])
    return (total if seen else None), at


def lifetime_total(store, accounts, metric):
    """Sum of the latest lifetime snapshot of each upload (one account/platform family)."""
    ids = [a["account_id"] for a in accounts]
    r = store.q(f"""SELECT SUM(value) v, COUNT(*) n, MAX(observed_at_utc) at FROM observations o WHERE account_id IN ({_in(ids)})
                    AND metric=? AND entity_type='upload' AND period_type='lifetime' AND status='value' AND observed_at_utc=(
                      SELECT MAX(observed_at_utc) FROM observations o2 WHERE o2.entity_id=o.entity_id AND o2.metric=o.metric
                      AND o2.source=o.source AND o2.period_type='lifetime')""", (*ids, metric))[0]
    return (r["v"] if r["n"] else None), r["at"]


def series(store, accounts, metric, start, end, breakdown_dim=""):
    ids = [a["account_id"] for a in accounts]
    agg = "SUM" if kind(metric) in ("count", "money", "daily") else "AVG"  # per day, across accounts
    return store.q(f"""SELECT period_start d, {agg}(value) v, COUNT(DISTINCT account_id) accounts FROM observations
                       WHERE account_id IN ({_in(ids)}) AND metric=? AND period_type='day' AND breakdown_dim=? AND status='value'
                       AND period_start BETWEEN ? AND ? GROUP BY period_start ORDER BY period_start""",
                   (*ids, metric, breakdown_dim, start, end))


_DEFS = None


def defs():
    global _DEFS
    if _DEFS is None:
        _DEFS = {m["id"]: m for m in metric_defs()["metrics"]}
    return _DEFS


def kind(metric):
    return defs().get(metric, {}).get("kind", "count")


# ------------------------------------------------------------------ overview
def overview(store, f):
    start, end = window(f)
    accts = account_filter(store, f)
    by_plat = {}
    for a in accts:
        by_plat.setdefault(a["platform"], []).append(a)
    platforms = []
    for p in SOCIAL:
        if p not in by_plat:
            continue
        acc = by_plat[p]
        views_period = day_sum(store, acc, "views", start, end)
        views_life, life_at = lifetime_total(store, acc, "views")
        followers, f_at = latest_level(store, acc, "followers", end)
        platforms.append({
            "platform": p, "accounts": [a["account_id"] for a in acc],
            "views": views_period if views_period is not None else views_life,
            "views_basis": "period" if views_period is not None else ("lifetime" if views_life is not None else None),
            "followers": followers, "followers_at": f_at,
            "followers_gained": day_sum(store, acc, "followers_gained", start, end),
            "watch_time_minutes": day_sum(store, acc, "watch_time_minutes", start, end),
            "views_series": series(store, acc, "views", start, end)})
    game = None
    if "roblox" in by_plat:
        acc = by_plat["roblox"]
        d1 = store.q(f"""SELECT period_start d, value v FROM observations WHERE account_id IN ({_in([a['account_id'] for a in acc])})
                         AND metric='d1_retention' AND period_type='day' AND breakdown_dim='' AND status='value'
                         AND period_start BETWEEN ? AND ? ORDER BY period_start DESC LIMIT 1""",
                     (*[a["account_id"] for a in acc], start, end))
        game = {"new_users": day_sum(store, acc, "new_users", start, end),
                "revenue_robux": day_sum(store, acc, "revenue_robux", start, end),
                "d1_latest": d1[0] if d1 else None,
                "dau_series": series(store, acc, "dau", start, end),
                "new_users_series": series(store, acc, "new_users", start, end)}
    accounts = []
    for a in accts:
        fl, fat = latest_level(store, [a], "followers", end)
        accounts.append({**a, "followers": fl, "followers_at": fat,
                         "views": day_sum(store, [a], "views", start, end),
                         "uploads": store.q("SELECT COUNT(*) n FROM uploads WHERE account_id=?", (a["account_id"],))[0]["n"]})
    return {"start": start, "end": end, "platforms": platforms, "game": game, "accounts": accounts,
            "recent": content(store, {**f, "limit": 6, "sort": "published"})["uploads"],
            "has_data": bool(store.q("SELECT 1 FROM observations LIMIT 1"))}


# ------------------------------------------------------------------ content
def latest_upload_metrics(store, upload_id):
    rows = store.q("""SELECT metric, value, status, observed_at_utc, source, note FROM observations o WHERE entity_type='upload'
                      AND entity_id=? AND period_type='lifetime' AND observed_at_utc=(SELECT MAX(observed_at_utc) FROM observations o2
                      WHERE o2.entity_id=o.entity_id AND o2.metric=o.metric AND o2.source=o.source AND o2.period_type='lifetime')""",
                   (upload_id,))
    return {r["metric"]: r for r in rows}


def content(store, f):
    accts = {a["account_id"]: a for a in account_filter(store, f)}
    ups = store.q("""SELECT u.*, a.concept_id, a.language asset_language, a.version, a.edit_file, a.production_minutes,
                     c.title concept_title, c.format, c.hook_type, c.slug FROM uploads u LEFT JOIN assets a ON a.asset_id=u.asset_id
                     LEFT JOIN concepts c ON c.concept_id=a.concept_id""")
    out = []
    for u in ups:
        acc = accts.get(u["account_id"])
        if not acc:
            continue
        lang = u["asset_language"] or acc["language"]
        if f.get("language") and lang != f["language"]:
            continue
        if f.get("format") and u["format"] != f["format"]:
            continue
        m = latest_upload_metrics(store, u["upload_id"])
        out.append({**u, "language": lang, "account_label": acc["label"],
                    "metrics": {k: v["value"] for k, v in m.items() if v["status"] == "value"},
                    "observed_at": max((v["observed_at_utc"] for v in m.values()), default=None)})
    platforms = {u["platform"] for u in out}
    sort = f.get("sort") or "published"
    if sort == "views" and len(platforms) <= 1:  # views are only ranked within one platform
        out.sort(key=lambda u: -(u["metrics"].get("views") or -1))
    else:
        out.sort(key=lambda u: u["published_at_utc"] or "", reverse=True)
    if f.get("limit"):
        out = out[: int(f["limit"])]
    concepts = store.q("SELECT * FROM concepts ORDER BY created_at_utc DESC")
    for c in concepts:
        c["assets"] = store.q("SELECT * FROM assets WHERE concept_id=? ORDER BY language, version", (c["concept_id"],))
    return {"uploads": out, "concepts": concepts, "sort_applied": sort if (sort != "views" or len(platforms) <= 1) else "published",
            "formats": sorted({c["format"] for c in concepts if c["format"]})}


def upload_detail(store, upload_id):
    u = store.q("SELECT * FROM uploads WHERE upload_id=?", (upload_id,))
    if not u:
        return None
    u = u[0]
    hist = store.q("""SELECT metric, value, status, observed_at_utc, source, note FROM observations WHERE entity_type='upload'
                      AND entity_id=? ORDER BY observed_at_utc""", (upload_id,))
    caps = {}
    for name in BY_PLATFORM.get(u["platform"], []):
        caps.update(CONNECTORS[name].capabilities)
    asset = store.q("SELECT * FROM assets WHERE asset_id=?", (u["asset_id"],)) if u["asset_id"] else []
    concept = store.q("SELECT * FROM concepts WHERE concept_id=?", (asset[0]["concept_id"],)) if asset else []
    siblings = store.q("SELECT upload_id, platform, account_id, url FROM uploads WHERE asset_id=? AND upload_id!=?",
                       (u["asset_id"], upload_id)) if u["asset_id"] else []
    exps = [e for e in store.experiments() if u["asset_id"] and any(u["asset_id"] in v["asset_ids"] for v in e["variants"])]
    return {"upload": u, "history": hist, "latest": latest_upload_metrics(store, upload_id), "capabilities": caps,
            "asset": asset[0] if asset else None, "concept": concept[0] if concept else None, "siblings": siblings,
            "experiments": [{"experiment_id": e["experiment_id"], "title": e["title"], "status": e["status"]} for e in exps]}


NAME = re.compile(r"SS_(\d{8})_([A-Z]+)_([A-Za-z0-9]+)(?:_([A-Za-z0-9]+))?_(V\d+)_([A-Z]+)\.mp4$")


def local_renders():
    """Edited videos in exports/ named by the toolkit convention. Paths stay local (never exported)."""
    out = []
    for p in sorted((ROOT / "exports").glob("SS_*.mp4"), reverse=True):
        m = NAME.match(p.name)
        if not m:
            continue
        qc = {}
        qp = p.with_suffix(".qc.json")
        if qp.exists():
            try:
                qc = json.loads(qp.read_text(encoding="utf-8"))
            except ValueError:
                pass
        length = next((c["detail"] for c in qc.get("checks", []) if c.get("check") == "length"), "")
        dur = re.match(r"([\d.]+)s", length)
        out.append({"file": p.name, "date": m.group(1), "format": m.group(2), "concept": m.group(3), "hook": m.group(4) or "",
                    "version": m.group(5), "duration_s": float(dur.group(1)) if dur else None,
                    "qc": qc.get("overall", ""), "test": m.group(2) == "TEST"})
    return out


# ------------------------------------------------------------------ research
LEVELS = {"O": "Observation", "D": "Derived statistic", "P": "Pattern", "I": "Interpretation", "C": "Causal claim",
          "R": "Recommendation"}


def research(store):
    runs = _rows(RESEARCH / "runs.csv")
    last = {}
    for r in runs:
        if r.get("dry_run") == "true":
            continue
        k = r["provider"]
        if k not in last or r["started_at_utc"] > last[k]["started_at_utc"]:
            last[k] = r
    collection = [{"provider": k, "command": v["command"], "at": v["finished_at_utc"] or v["started_at_utc"],
                   "status": v["status"], "rows": v["rows_written"]} for k, v in sorted(last.items())]
    recent_runs = sorted([r for r in runs if r.get("dry_run") != "true"], key=lambda r: r["started_at_utc"], reverse=True)[:8]
    ledgers = []
    for p in sorted((RESEARCH / "evidence").glob("*.json")):
        if p.name.endswith(".evidenceguard.json"):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        claims = [{"id": c.get("claim_id"), "level": c.get("level"), "level_label": LEVELS.get(c.get("level"), "?"),
                   "text": c.get("claim_text", ""), "support": c.get("support_status", ""), "strength": c.get("strength", ""),
                   "reviewed": bool((c.get("review") or {}).get("ai_reviewed"))} for c in d.get("claims", [])]
        memo = d.get("decision_memo") or {}
        ledgers.append({"ledger_id": d.get("ledger_id", p.stem), "updated_at": d.get("updated_at") or d.get("created_at"),
                        "decision": d.get("decision") if isinstance(d.get("decision"), str) else (d.get("decision") or {}).get("question", ""),
                        "summary": d.get("summary") if isinstance(d.get("summary"), str) else "",
                        "example": p.stem.startswith("EXAMPLE"), "claims": claims,
                        "memo": memo if isinstance(memo, (dict, str)) else {},
                        "limitations": d.get("limitations", [])})
    watch = {
        "youtube_creators": [{"label": r.get("label") or r.get("channel_id"), "language": r.get("language_stream", "")}
                             for r in _rows(RCONFIG / "youtube_creators.csv")],
        "twitch_broadcasters": [{"label": r.get("label") or r.get("login"), "language": r.get("language_stream", "")}
                                for r in _rows(RCONFIG / "twitch_broadcasters.csv")],
        "wiki_entities": sorted({r.get("entity_id", "") for r in _rows(RCONFIG / "wiki_entities.csv")} - {""}),
        "roblox_experiences": [r.get("label") or r.get("universe_id") for r in _rows(RCONFIG / "roblox_experiences.csv")]}
    trend_rows = _rows(RESEARCH / "google_trends" / "trending_now.csv")
    latest = max((r["observed_at_utc"] for r in trend_rows), default="")
    day = latest[:10]
    trends = {}
    for r in trend_rows:
        if r["observed_at_utc"][:10] == day:
            trends.setdefault(r["geo"], [])
            if len(trends[r["geo"]]) < 5 and r["term"] not in [t["term"] for t in trends[r["geo"]]]:
                trends[r["geo"]].append({"term": r["term"], "traffic": r.get("approx_traffic", "")})
    obs = _rows(RESEARCH / "observations" / "public_observations.csv")
    seen, observations = set(), []
    for r in sorted(obs, key=lambda r: r.get("observed_at_utc", ""), reverse=True):
        k = (r.get("platform"), r.get("title_or_name") or r.get("content_id"))
        if k in seen:
            continue
        seen.add(k)
        observations.append({"platform": r.get("platform"), "name": r.get("title_or_name") or r.get("content_id"),
                             "metric": r.get("metric"), "value": r.get("value_display"), "source": r.get("source"),
                             "provenance": r.get("provenance"), "region": r.get("region"), "period": r.get("period"),
                             "observed_at": r.get("observed_at_utc")})
        if len(observations) >= 12:
            break
    kb = []
    for base in (ROOT / "research" / "knowledge", RESEARCH / "knowledge"):
        for p in sorted(base.glob("*.md")) if base.exists() else []:
            head = p.read_text(encoding="utf-8").splitlines()[:1]
            kb.append({"file": str(p.relative_to(ROOT)).replace("\\", "/"), "title": (head[0].lstrip("# ") if head else p.stem)})
    return {"collection": collection, "recent_runs": recent_runs, "ledgers": ledgers, "watchlists": watch,
            "trends": {"observed_day": day, "by_geo": trends}, "observations": observations, "knowledge": kb,
            "knowledge_dirs": ["research/knowledge/", "data/local/research/knowledge/"], "kb": knowledge_summary()}


# ------------------------------------------------------------------ game
def game(store, f):
    start, end = window(f)
    accts = account_filter(store, {**f, "platform": ""})
    rbx = [a for a in accts if a["platform"] == "roblox"]
    social = [a for a in accts if a["platform"] in SOCIAL and (not f.get("platform") or a["platform"] in f["platform"].split(","))]
    stages = []
    allcaps = {}
    for name, con in CONNECTORS.items():
        for m, how in con.capabilities.items():
            for p in getattr(con, "platforms", None) or [con.platform]:
                allcaps.setdefault(m, {})[p] = how
    for s in metric_defs()["stages"]:
        ms = []
        for m in [m for m in metric_defs()["metrics"] if m["stage"] == s["id"]]:
            per = []
            for p in m["platforms"]:
                acc = [a for a in (rbx if p == "roblox" else social) if a["platform"] == p]
                if not acc:
                    continue
                if m["kind"] == "daily":
                    v, basis = day_avg(store, acc, m["id"], start, end), "avg/day"
                elif m["kind"] in ("count", "money"):
                    v, basis = day_sum(store, acc, m["id"], start, end), "period"
                    if v is None and m["id"] in ("views", "likes", "comments", "shares", "saves"):
                        v, _ = lifetime_total(store, acc, m["id"])
                        basis = "lifetime" if v is not None else None
                elif m["kind"] == "level":
                    v, _ = latest_level(store, acc, m["id"], end, "experience" if p == "roblox" else "account")
                    basis = "latest"
                else:
                    r = store.q(f"""SELECT value v, period_start d FROM observations WHERE account_id IN ({_in([a['account_id'] for a in acc])})
                                    AND metric=? AND period_type='day' AND breakdown_dim='' AND status='value' AND period_start BETWEEN ? AND ?
                                    ORDER BY period_start DESC LIMIT 1""", (*[a["account_id"] for a in acc], m["id"], start, end))
                    cohort = m["id"] in ("d1_retention", "d7_retention", "d30_retention")
                    v, basis = (r[0]["v"], ("cohort " if cohort else "day ") + r[0]["d"]) if r else (None, None)
                per.append({"platform": p, "value": v, "basis": basis, "how": allcaps.get(m["id"], {}).get(p, "manual")})
            if per:
                ms.append({"metric": m["id"], "label": m["label"], "unit": m["unit"], "kind": m["kind"],
                           "definition": m["definition"], "primary": bool(m.get("primary")), "values": per})
        stages.append({**s, "metrics": ms})
    ids = [a["account_id"] for a in rbx]
    acq = store.q(f"""SELECT breakdown_value source, AVG(value) v FROM observations WHERE account_id IN ({_in(ids)})
                      AND metric='unique_play_users' AND breakdown_dim='AcquisitionSource' AND status='value'
                      AND period_start BETWEEN ? AND ? GROUP BY breakdown_value ORDER BY v DESC""", (*ids, start, end))
    links = store.q(f"""SELECT breakdown_value link, metric, SUM(value) v FROM observations WHERE account_id IN ({_in(ids)})
                        AND breakdown_dim='ShareLink' AND status='value' AND period_start BETWEEN ? AND ?
                        GROUP BY breakdown_value, metric ORDER BY breakdown_value""", (*ids, start, end))
    cohorts = store.q(f"""SELECT period_start d, MAX(CASE WHEN metric='new_users' THEN value END) new_users,
                          MAX(CASE WHEN metric='d1_retention' THEN value END) d1, MAX(CASE WHEN metric='d7_retention' THEN value END) d7,
                          MAX(CASE WHEN metric='d30_retention' THEN value END) d30 FROM observations
                          WHERE account_id IN ({_in(ids)}) AND breakdown_dim='' AND period_type='day' AND status='value'
                          AND metric IN ('new_users','d1_retention','d7_retention','d30_retention') AND period_start BETWEEN ? AND ?
                          GROUP BY period_start ORDER BY period_start DESC LIMIT 21""", (*ids, start, end))
    ser = {m: series(store, rbx, m, start, end) for m in ("dau", "new_users", "revenue_robux", "d1_retention", "avg_session_min")}
    return {"start": start, "end": end, "stages": stages, "acquisition": acq, "share_links": links, "cohorts": cohorts,
            "series": ser, "roblox_accounts": rbx, "acquisition_basis": "average daily unique players with sessions", "activation_note": "Needs in-game onboarding events (docs/dashboard/activation-events-proposal.md)."}


# ------------------------------------------------------------------ experiments
def experiments(store):
    exps = store.experiments()
    links = hypotheses_for_experiments()
    for e in exps:
        e["hypothesis_families"] = links.get(e["experiment_id"], [])
        for v in e["variants"]:
            v["uploads"] = []
            for aid in v["asset_ids"]:
                for u in store.q("SELECT * FROM uploads WHERE asset_id=?", (aid,)):
                    v["uploads"].append({**u, "at_window": at_window(store, u, e)})
    return exps


def at_window(store, u, e):
    """Each metric's lifetime snapshot nearest the experiment's read time (published + window). Per upload,
    per platform; nothing is added across platforms or compared across them."""
    if not (u["published_at_utc"] and e.get("window_hours")):
        return {}
    pub = datetime.fromisoformat(u["published_at_utc"].replace("Z", "+00:00"))
    target = pub + timedelta(hours=e["window_hours"])
    out = {}
    for m in [e["primary_metric"], *e["secondary_metrics"]]:
        r = store.q("""SELECT value, observed_at_utc FROM observations WHERE entity_type='upload' AND entity_id=? AND metric=?
                       AND period_type='lifetime' AND status='value' ORDER BY observed_at_utc""", (u["upload_id"], m))
        if not r:
            continue
        best = min(r, key=lambda x: abs((datetime.fromisoformat(x["observed_at_utc"]) - target).total_seconds()))
        off = (datetime.fromisoformat(best["observed_at_utc"]) - target).total_seconds() / 3600
        out[m] = {"value": best["value"], "observed_at": best["observed_at_utc"], "hours_from_window": round(off, 1)}
    return out


# ------------------------------------------------------------------ knowledge banks (scripts/kb.py)
_KB = None
KB_FIXTURE_DIR = ROOT / "tests" / "fixtures" / "knowledge"


def _kb():
    """scripts/kb.py loaded by path (the toolkit's scripts are not a package). Fixture dashboards read the fixture
    knowledge folder so fixture and real research never mix."""
    global _KB
    if _KB is None:
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location("slugshot_kb", ROOT / "scripts" / "kb.py")
        _KB = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_KB)
    import os
    from .store import is_fixture_db
    if is_fixture_db():
        os.environ["SLUGSHOT_KB_DIR"] = str(KB_FIXTURE_DIR)
    elif os.environ.get("SLUGSHOT_KB_DIR") == str(KB_FIXTURE_DIR):
        os.environ.pop("SLUGSHOT_KB_DIR")       # only undo our own fixture override
    return _KB


def _kb_row(kb, e):
    t = e.get("tags") or {}
    return {"id": e["id"], "bank": e.get("bank"), "kind": e.get("kind"), "title": e.get("title", ""),
            "statement": e.get("statement", ""), "evidence_label": e.get("evidence_label"), "review_status": e.get("review_status"),
            "support_status": e.get("support_status", ""), "strength": e.get("strength", ""), "freshness": kb.status_of(e),
            "review_by": e.get("review_by", ""), "formats": t.get("format", []), "languages": t.get("language", []),
            "characters": t.get("character", []), "stages": t.get("funnel_stage", []), "journey": t.get("journey", []),
            "objectives": t.get("objective", []), "aliases": e.get("report_aliases", [])[:8]}


def knowledge(params=None):
    p = params or {}
    kb = _kb()
    entries = kb.load()
    rows = kb.find(entries, q=p.get("q") or None, bank=p.get("bank") or None, objective=p.get("objective") or None,
                   fmt=p.get("format") or None, lang=p.get("lang") or None, character=p.get("character") or None,
                   stage=p.get("stage") or None, evidence=p.get("evidence") or None, status=p.get("status") or None,
                   due=p.get("due") == "1", include_inventory=p.get("inventory") == "1")
    order = {b: i for i, b in enumerate(["mechanisms", "hooks", "narrative", "humour", "characters", "audiovisual", "funnel",
                                          "opportunities", "culture", "sentiment", "hypotheses", "decisions", "amendments",
                                          "claims", "sources", "inventory"])}
    rows.sort(key=lambda e: (order.get(e.get("bank"), 99), e["id"]))
    limit = int(p.get("limit") or 80)
    banks = {}
    for e in entries:
        if e.get("_error"):
            continue
        b = banks.setdefault(e["bank"], {"bank": e["bank"], "n": 0, "reviewed": 0, "due": 0})
        b["n"] += 1
        b["reviewed"] += e.get("review_status") in ("reviewed", "approved")
        b["due"] += kb.status_of(e) in ("due", "stale") and e.get("review_status") != "retired"
    return {"dir": str(kb.kb_dir()), "total": len(rows), "rows": [_kb_row(kb, e) for e in rows[:limit]],
            "banks": sorted(banks.values(), key=lambda b: order.get(b["bank"], 99)),
            "facets": {"evidence": sorted(kb.EVIDENCE_LABELS), "status": kb.REVIEW, "format": sorted(kb.FORMATS),
                       "lang": ["en", "es"], "stage": sorted(kb.STAGES), "objective": sorted(kb.OBJECTIVES)}}


def knowledge_entry(eid):
    kb = _kb()
    entries = kb.load()
    e = next((x for x in entries if x.get("id") == eid), None)
    return kb.resolve(entries, e) if e else None


def knowledge_summary():
    """Small block for the Research page: counts, due items, opportunities, latest sentiment samples."""
    kb = _kb()
    entries = [e for e in kb.load() if not e.get("_error")]
    if not entries:
        return {"available": False, "dir": str(kb.kb_dir())}
    errs, warns = kb.validate(entries)
    opp = [_kb_row(kb, e) | {"dimensions": e.get("dimensions", {}), "risks": e.get("risks", []), "target": e.get("target", "")}
           for e in entries if e.get("bank") == "opportunities" and e.get("review_status") != "retired"]
    sent = [{"id": e["id"], "title": e.get("title", ""), "denominators": e.get("denominators", {}), "freshness": kb.status_of(e),
             "source": (e.get("policy") or {}).get("source", "")} for e in entries if e.get("bank") == "sentiment"]
    due = [_kb_row(kb, e) for e in entries if kb.status_of(e) in ("due", "stale") and e.get("review_status") != "retired"
           and e.get("bank") != "inventory"]
    return {"available": True, "dir": str(kb.kb_dir()), "n": len(entries), "errors": len(errs), "warnings": len(warns),
            "opportunities": opp, "sentiment": sent[-6:], "due": sorted(due, key=lambda r: r["review_by"])[:12]}


def hypotheses_for_experiments():
    kb = _kb()
    out = {}
    for e in kb.load():
        if e.get("bank") == "hypotheses":
            for x in e.get("experiment_refs", []):
                out.setdefault(x, []).append({"id": e["id"], "title": e.get("title"), "gate": e.get("gate", "")})
    return out


def hypothesis_families():
    kb = _kb()
    fams = [e for e in kb.load() if e.get("bank") == "hypotheses"]
    return [{"id": e["id"], "title": e.get("title"), "question": e.get("statement"), "gate": e.get("gate", ""),
             "order": e.get("priority_order"), "aliases": e.get("report_aliases", []), "experiments": e.get("experiment_refs", []),
             "comparator": e.get("comparator", "")} for e in sorted(fams, key=lambda e: (e.get("priority_order") or 99, e["id"]))]


# ------------------------------------------------------------------ publish
def publish_page(store):
    from . import publish as P
    exps = [{"experiment_id": e["experiment_id"], "title": e["title"], "status": e["status"],
             "variants": [{"variant_id": v["variant_id"], "label": v["label"], "role": v["role"]} for v in e["variants"]]}
            for e in store.experiments() if e["status"] not in ("closed", "abandoned")]
    assets = store.q("""SELECT a.asset_id, a.concept_id, a.language, a.version, a.edit_file, a.fiction_label, c.title
                        FROM assets a JOIN concepts c USING(concept_id) ORDER BY a.created_at_utc DESC""")
    videos = [{"path": "exports/" + r["file"], "file": r["file"], "concept": r["concept"], "qc": r["qc"], "duration_s": r["duration_s"]}
              for r in local_renders()]
    for a in assets:
        ef = a["edit_file"]
        if ef and ef.lower().endswith((".mp4", ".mov", ".webm")) and not any(v["path"].endswith(ef.split("/")[-1]) for v in videos):
            videos.append({"path": ef if "/" in ef or "\\" in ef else "exports/" + ef, "file": ef.split("/")[-1], "concept": a["title"], "qc": "", "duration_s": None})
    jobs = P.jobs(store)
    for j in jobs:
        j.pop("approval", None)
        j["log"] = j["log"][-1:] if j["log"] else []
    return {"accounts": P.accounts_view(store), "jobs": jobs, "assets": assets, "videos": videos, "experiments": exps,
            "reveal_lock": P.cfg()["reveal_lock"], "public_posting": P.cfg()["public_posting"], "tiktok_declaration": {"music": P.TIKTOK_MUSIC, "branded": P.TIKTOK_BRANDED}}


def publish_job(store, job_id):
    from . import publish as P
    j = P.job(store, job_id)
    if not j:
        return None
    acct = store.account(j["account_id"])
    creator, creator_error = None, ""
    if j["platform"] == "tiktok" and j["route"] == "direct":
        try:
            creator = P.tiktok_creator_info(store, acct)
        except Exception as e:  # shown to the owner; posting stays blocked without it
            creator_error = str(e)[:200]
    res = P.check(store, j, creator)
    appr = j.get("approval") or {}
    j["approval"] = {k: appr[k] for k in ("by", "at", "typed_handle") if k in appr} if appr else None
    asset = store.q("SELECT a.*, c.title, c.hook_text FROM assets a JOIN concepts c USING(concept_id) WHERE asset_id=?", (j["asset_id"],))
    return {"job": j, "account": acct, "check": res, "creator": creator, "creator_error": creator_error,
            "asset": asset[0] if asset else None, "routes": list(P.ROUTES[j["platform"]]),
            "tiktok_declaration": P.TIKTOK_BRANDED if j["fields"].get("branded_content") else P.TIKTOK_MUSIC}


# ------------------------------------------------------------------ service usage (Settings)
def service_usage(store):
    """Every external service with a free allowance. Each figure says how it's known: 'live' (the provider reports
    it), 'local estimate' (counted from our own logs) or 'documented' (the published limit; no usage API we can read).
    Credential expiry comes from stored token metadata, never the token itself."""
    import time as _time
    from . import hosting, vault
    from .store import now_iso
    sys_path = str(ROOT / "scripts")
    import sys as _sys
    if sys_path not in _sys.path:
        _sys.path.insert(0, sys_path)
    import research_common as rc
    now = datetime.now(timezone.utc)
    out = []

    def svc(name, rows, note="", link="", status=""):
        out.append({"service": name, "rows": rows, "note": note, "link": link, "status": status})

    def row(label, used=None, limit=None, unit="", how="documented", period="", detail=""):
        pct = round(100 * used / limit, 1) if used is not None and limit else None
        return {"label": label, "used": used, "limit": limit, "remaining": (limit - used) if used is not None and limit else None,
                "pct": pct, "unit": unit, "how": how, "period": period, "detail": detail}

    u = store.pref("cloudinary_usage") or {}
    cr = u.get("credits") or {}
    svc("Cloudinary", [row("Credits", cr.get("usage"), cr.get("limit") or 25, "credits", "live" if cr else "documented",
                           "rolling 30 days", f"checked {u.get('fetched_at', 'never')[:16].replace('T', ' ')}" if u else "not checked yet"),
                       row("Video size", None, round((u.get("video_max_bytes") or 104857600) / 1048576), "MB per file", "live" if u else "documented"),
                       row("Hosted now", len(hosting.hosted(store)), hosting.cfg()["max_hosted_files"], "files", "local estimate", "", "our limit")],
        "1 credit = 1 GB stored, 1 GB of video delivered or 1,000 transformations. Uploads stop at "
        f"{hosting.cfg()['max_credit_pct']}% of credits. The free plan is disabled at its limit, never billed.",
        "https://console.cloudinary.com/", "error" if store.pref("cloudinary_error") else "")
    q = store.pref("buffer_quota") or {}
    reset = datetime.fromtimestamp(q["reset_unix"], timezone.utc).strftime("%d %b %Y") if q.get("reset_unix") else ""
    svc("Buffer", [row("API requests", (q["limit"] - q["remaining"]) if q else None, q.get("limit") or 3000, "requests",
                       "live" if q else "documented", "30-day window", f"resets {reset}" if reset else ""),
                   row("Scheduled posts", None, 10, "posts", "documented", "at any time"),
                   row("API key", None, None, "", "documented", "", "expiry set when the key was made; check Buffer → Settings → API")],
        "Analytics pause below 150 requests left so posting always has room. Insights cover the last 31 days on the free plan.",
        "https://publish.buffer.com/settings/api")
    day = rc.pacific_day(rc.now())
    research = sum(int(r.get("units") or 0) for r in _rows(RESEARCH / "youtube" / "quota_log.csv")
                   if r.get("quota_day_pt") == day and r.get("bucket") == "default")
    dash = store.q("""SELECT COALESCE(SUM(requests_ok + requests_failed), 0) n FROM sync_runs WHERE connector='youtube_analytics'
                      AND fixture=0 AND started_at_utc >= ?""", ((now - timedelta(hours=24)).isoformat(),))[0]["n"]
    uploads = store.q("""SELECT COUNT(*) n FROM publish_jobs WHERE platform='youtube' AND route='api' AND state IN ('done','processing')
                         AND updated_at_utc >= ?""", ((now - timedelta(hours=24)).isoformat(),))[0]["n"]
    svc("YouTube Data API", [row("Research collector", research, 10000, "units", "local estimate", "per day (resets midnight US Pacific)",
                                 "logged per request; our own budget is 3,000"),
                             row("Dashboard refresh", None, None, "", "local estimate", "last 24 h",
                                 f"about {dash} requests (channels, uploads list and Analytics reports)"),
                             row("Uploads", uploads, 100, "videos", "local estimate", "per day")],
        "Google doesn't expose current consumption through the API. Exact figures: Google Cloud console → APIs → Quotas.",
        "https://console.cloud.google.com/apis/dashboard")
    tt_rows = []
    for a in store.accounts():
        if a["platform"] == "tiktok" and a["active"]:
            t = vault.get(f"oauth_tiktok_{a['account_id']}") or {}
            if t.get("refresh_expires_at"):
                days = int((t["refresh_expires_at"] - _time.time()) // 86400)
                tt_rows.append(row(f"{a['label']} sign-in", None, None, "", "live", "", f"renews automatically; re-sign-in needed in {days} days"))
            elif t:
                tt_rows.append(row(f"{a['label']} sign-in", None, None, "", "documented", "", "renews automatically; sign-in lasts up to a year"))
    inbox = store.q("""SELECT COUNT(*) n FROM publish_jobs WHERE platform='tiktok' AND route='inbox' AND state IN ('sent_to_inbox','done')
                       AND updated_at_utc >= ?""", ((now - timedelta(hours=24)).isoformat(),))[0]["n"]
    svc("TikTok API", [row("Inbox uploads", inbox, 5, "pending drafts", "local estimate", "per 24 h"), *tt_rows],
        "Sandbox app: posts through our own app stay private until TikTok audits it; public TikTok posts go via Buffer.",
        "https://developers.tiktok.com/apps")
    g_rows = [row(f"{a['label']} sign-in", None, None, "", "documented", "",
                  "lasts until revoked if the Google consent screen is In production; 7 days in Testing")
              for a in store.accounts() if a["platform"] == "youtube" and a["active"] and vault.has(f"oauth_youtube_{a['account_id']}")]
    if g_rows:
        svc("Google sign-in", g_rows, "", "https://console.cloud.google.com/auth/audience")
    twitch_ready = bool(rc.env_value("TWITCH_CLIENT_ID"))
    svc("Twitch API", [row("Rate limit", None, 800, "points per minute", "documented")],
        "No monthly allowance; research data is kept 24 hours." + ("" if twitch_ready else " Not set up."),
        "https://dev.twitch.tv/console")
    svc("Composio", [row("Tool calls", None, 100000, "calls", "documented", "per month", "Hobby plan; pauses at the cap, can't bill")],
        "Read-only add-on. Usage is shown only in the Composio dashboard.", "https://platform.composio.dev/")
    return {"services": out, "generated_at": now_iso()}
