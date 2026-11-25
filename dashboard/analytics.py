"""Owner-facing analytics: Overview totals, the views and followers drill-downs, account pages, video galleries.

Owner decision 2026-11-25: show combined totals, labelled for what they are.
- Views: gross platform-reported views, added across platforms. Not unique viewers; each platform counts a view its
  own way (the page says so once, briefly).
- Followers: combined account follower/subscriber counts. Not unique people.
- Watch time: added only where an account reports it; the accounts covered are listed.
The AI exports (reports.py) keep platforms separate; this module is only for the owner's screens.

How a period is measured:
- YouTube has daily channel analytics: period views, watch time, likes... are day sums.
- TikTok and Instagram only give lifetime totals per video. Period gains come from successive daily snapshots of
  each video: the gain between two snapshots lands on the later day. A video first seen long after it was published
  has its earlier views counted only in "all time", never as views in a window (they happened before tracking).
- Each video's metric comes from one source: the native API first, then Buffer, then manual imports. Buffer only
  writes what the native API lacks, so nothing is counted twice.
- Missing stays missing (None), never 0. A comparison with the previous period is given only when both periods
  could be measured the same way.
"""
from datetime import date, datetime, timedelta, timezone

from .store import now_iso

SOCIAL = ("youtube", "tiktok", "instagram")
SOURCES = {"youtube": ["youtube_analytics"], "tiktok": ["tiktok", "buffer"], "instagram": ["instagram", "buffer"]}
ENGAGEMENT = ("likes", "comments", "shares", "saves")
UPLOAD_METRICS = ("views", "watch_time_minutes", "avg_view_duration_s", "avg_view_pct", "completion_rate", "reach",
                  "followers_gained", *ENGAGEMENT)
EARLIEST = "2020-01-01"


def _d(x):
    return date.fromisoformat(str(x)[:10])


def _days(start, end):
    d, out = _d(start), []
    while d <= _d(end):
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _rank(platform, source):
    order = SOURCES.get(platform, [])
    if source in order:
        return order.index(source)
    return len(order) + (0 if source.startswith("manual") else 1)


def _in(ids):
    return ",".join("?" * len(ids)) or "''"


def window(f):
    """(start, end, all_time). Presets: 7, 30, 90 days, all; or explicit start/end."""
    end = f.get("end") or date.today().isoformat()
    rng = f.get("range") or ""
    if rng == "all":
        return EARLIEST, end, True
    if f.get("start") and not rng:
        return f["start"], end, False
    days = int(rng) if rng.isdigit() else 30
    return (_d(end) - timedelta(days=days - 1)).isoformat(), end, False


def accounts_for(store, f):
    plats = [p for p in (f.get("platform") or "").split(",") if p]
    ids = [a for a in (f.get("account") or "").split(",") if a]
    lang = f.get("language") or ""
    return [a for a in store.accounts() if a["active"] and a["platform"] in SOCIAL and (not plats or a["platform"] in plats)
            and (not ids or a["account_id"] in ids) and (not lang or a["language"] == lang)]


# ------------------------------------------------------------------ raw reads
def _day_series(store, acct, metric, start, end):
    rows = store.q("""SELECT period_start d, SUM(value) v FROM observations WHERE account_id=? AND metric=? AND period_type='day'
                      AND breakdown_dim='' AND status='value' AND period_start BETWEEN ? AND ? GROUP BY period_start""",
                   (acct, metric, start, end))
    return {r["d"]: r["v"] for r in rows}


def _has_days(store, acct, metric):
    return bool(store.q("""SELECT 1 FROM observations WHERE account_id=? AND metric=? AND period_type='day' AND status='value'
                           AND breakdown_dim='' LIMIT 1""", (acct, metric)))


def uploads_of(store, account_ids):
    if not account_ids:
        return []
    return store.q(f"""SELECT u.*, a.concept_id, a.language asset_language, a.edit_file, a.version, c.title concept_title
                       FROM uploads u LEFT JOIN assets a ON a.asset_id=u.asset_id LEFT JOIN concepts c ON c.concept_id=a.concept_id
                       WHERE u.account_id IN ({_in(account_ids)})""", tuple(account_ids))


def snapshots(store, uploads, metrics=UPLOAD_METRICS):
    """{upload_id: {metric: {"source": s, "points": [(day, value), ...]}}}: one source per video and metric, last value per day."""
    if not uploads:
        return {}
    plat = {u["upload_id"]: u["platform"] for u in uploads}
    rows = store.q(f"""SELECT entity_id, metric, source, value, observed_at_utc FROM observations WHERE entity_type='upload'
                       AND period_type='lifetime' AND status='value' AND entity_id IN ({_in(list(plat))})
                       AND metric IN ({_in(list(metrics))}) ORDER BY observed_at_utc""", (*plat, *metrics))
    by = {}
    for r in rows:
        by.setdefault(r["entity_id"], {}).setdefault(r["metric"], {}).setdefault(r["source"], {})[r["observed_at_utc"][:10]] = r["value"]
    out = {}
    for uid, ms in by.items():
        for m, srcs in ms.items():
            src = min(srcs, key=lambda s: (_rank(plat[uid], s), -len(srcs[s])))
            out.setdefault(uid, {})[m] = {"source": src, "points": sorted(srcs[src].items())}
    return out


def gains(points, published, start, end, all_time):
    """Daily gains of one video's lifetime counter inside [start, end]. Returns ({day: gain}, partial)."""
    out, partial = {}, False
    if not points:
        return out, partial
    first_day, first_v = points[0]
    near_publish = bool(published) and (_d(first_day) - _d(published)).days <= 1
    if all_time or near_publish:
        if start <= first_day <= end:
            out[first_day] = first_v
    elif start < first_day <= end:
        partial = True  # tracking began inside the window: views before the first snapshot are unknown
    elif first_day > end and published and published <= end:
        partial = True  # published before the window ended but not tracked until after it: the window is unknown
    for (d0, v0), (d1, v1) in zip(points, points[1:]):
        if start <= d1 <= end:
            out[d1] = out.get(d1, 0) + (v1 - v0)
    return out, partial


def latest(points, upto=None):
    pts = [p for p in points if upto is None or p[0] <= upto]
    return pts[-1][1] if pts else None


# ------------------------------------------------------------------ per account
def account_stats(store, a, start, end, all_time, ups, snaps):
    """Every number one account contributes for the window, with how it was measured."""
    aid, p = a["account_id"], a["platform"]
    mine = [u for u in ups if u["account_id"] == aid]
    days = _days(start, end) if not all_time else None
    out = {"series": {}, "basis": {}, "partial": {}}

    def from_days(metric):
        s = _day_series(store, aid, metric, start, end)
        return (s, "daily report") if s else (None, None)

    def from_snaps(metric):
        tot, any_pts, partial = {}, False, False
        for u in mine:
            sn = snaps.get(u["upload_id"], {}).get(metric)
            if not sn:
                continue
            any_pts = True
            g, part = gains(sn["points"], (u["published_at_utc"] or "")[:10], start, end, all_time)
            partial |= part
            for d_, v in g.items():
                tot[d_] = tot.get(d_, 0) + v
        return (tot, "daily snapshots") if any_pts else (None, None), partial

    for metric in ("views", "watch_time_minutes", *ENGAGEMENT):
        if p == "youtube" or _has_days(store, aid, metric):
            ser, basis = from_days(metric)
            part = False
        else:
            (ser, basis), part = from_snaps(metric)
        out[metric] = round(sum(ser.values()), 2) if ser is not None else None
        if ser is not None:
            out["series"][metric] = [{"d": d_, "v": ser.get(d_, 0)} for d_ in (days or sorted(ser))]
        out["basis"][metric], out["partial"][metric] = basis, part
    pav = period_avg_view(store, [a], start, end)
    out["avg_view_s"], out["avg_view_basis"] = (pav[0], "period") if pav[0] is not None else (weighted_avg_view(mine, snaps), "lifetime")
    out["days_with_data"] = {m: len(_day_series(store, aid, m, start, end)) for m in ("views", "watch_time_minutes")} if out["basis"].get("views") == "daily report" else {}

    # Followers: latest level, change over the window, gained/lost where the platform reports them.
    pts = store.q("""SELECT period_start d, value v, observed_at_utc o FROM observations WHERE account_id=? AND metric='followers'
                     AND entity_type='account' AND period_type='point' AND status='value' ORDER BY period_start, observed_at_utc""", (aid,))
    level = {}
    for r in pts:
        level[r["d"]] = r["v"]
    lv = sorted(level.items())
    at_end = latest(lv, end)
    before = [x for x in lv if x[0] < start]
    at_start = before[-1][1] if before else None
    gained = sum(_day_series(store, aid, "followers_gained", start, end).values()) if _has_days(store, aid, "followers_gained") else None
    lost = sum(_day_series(store, aid, "followers_lost", start, end).values()) if _has_days(store, aid, "followers_lost") else None
    if all_time and at_end is not None:
        change, cbasis = at_end, "since the account began"
    elif at_end is not None and at_start is not None:
        change, cbasis = at_end - at_start, "follower count"
    elif gained is not None:
        change, cbasis = gained - (lost or 0), "gained minus lost"
    elif at_end is not None and [x for x in lv if start <= x[0] <= end][:1] and [x for x in lv if start <= x[0] <= end][0][0] < end:
        first_in = [x for x in lv if start <= x[0] <= end][0]
        change, cbasis = at_end - first_in[1], "since first reading"
    else:
        change, cbasis = None, None
    out.update(followers=at_end, followers_start=at_start, followers_change=change, followers_change_basis=cbasis,
               followers_gained=gained, followers_lost=lost,
               followers_growth=round(100 * change / at_start, 1) if change is not None and at_start else None)
    if lv:
        carry, ser = None, []
        for d_ in (days or [x[0] for x in lv]):
            carry = level.get(d_, carry)
            if carry is not None:
                ser.append({"d": d_, "v": carry})
        out["series"]["followers"] = ser
    return out


def period_avg_view(store, accounts, start, end):
    """Average view duration inside the window, where a platform reports it per day (YouTube): each day's average
    weighted by that day's views. Returns (value, accounts covered); (None, []) when no account reports it per day."""
    num = den = 0.0
    covered = []
    for a in accounts:
        avg = _day_series(store, a["account_id"], "avg_view_duration_s", start, end)
        views = _day_series(store, a["account_id"], "views", start, end)
        both = [(avg[d_], views[d_]) for d_ in avg if d_ in views and views[d_]]
        if both:
            covered.append(a["account_id"])
            num += sum(x * v for x, v in both)
            den += sum(v for _, v in both)
    return (round(num / den, 1), covered) if den else (None, [])


def comparable(store, account_id, metric, cur, prev, pstart):
    """True only if the previous period was measured the same way and about as completely as the current one:
    same basis, neither period partly measured, and for daily reports, data that began before the previous period and
    at least 80% as many days with data. Anything else suppresses the comparison rather than risk a false change."""
    if prev is None or cur[metric] is None or prev[metric] is None:
        return False
    if cur["basis"].get(metric) != prev["basis"].get(metric) or cur["partial"].get(metric) or prev["partial"].get(metric):
        return False
    if cur["basis"].get(metric) == "daily report":
        first = store.q("""SELECT MIN(period_start) d FROM observations WHERE account_id=? AND metric=? AND period_type='day'
                           AND breakdown_dim='' AND status='value'""", (account_id, metric))[0]["d"]
        if not first or first > pstart:
            return False
        c, q = cur["days_with_data"].get(metric, 0), prev["days_with_data"].get(metric, 0)
        if q < 0.8 * c:
            return False
    return True


def avg_view_total(store, accounts, uploads, snaps, start, end):
    """Period average where any account reports one per day (only those accounts); otherwise the lifetime per-video
    average, labelled as such. The two are never blended."""
    value, covered = period_avg_view(store, accounts, start, end)
    if value is not None:
        return {"value": value, "basis": "period", "covered": covered}
    value = weighted_avg_view(uploads, snaps)
    return {"value": value, "basis": "lifetime" if value is not None else None,
            "covered": sorted({u["account_id"] for u in uploads}) if value is not None else []}


def weighted_avg_view(uploads, snaps):
    """Average view duration: each video's own reported average, weighted by its views, over the videos that report
    both. Dividing total watch time by total views would mix videos with and without watch-time data."""
    num = den = 0.0
    for u in uploads:
        sn = snaps.get(u["upload_id"], {})
        a, v = latest(sn["avg_view_duration_s"]["points"]) if "avg_view_duration_s" in sn else None, latest(sn["views"]["points"]) if "views" in sn else None
        if a is not None and v:
            num, den = num + a * v, den + v
    return round(num / den, 1) if den else None


def _sum(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals), 2) if vals else None


def analytics(store, f):
    start, end, all_time = window(f)
    accts = accounts_for(store, f)
    ups = uploads_of(store, [a["account_id"] for a in accts])
    snaps = snapshots(store, ups)
    span = (_d(end) - _d(start)).days + 1
    pstart, pend = (_d(start) - timedelta(days=span)).isoformat(), (_d(start) - timedelta(days=1)).isoformat()
    rows = []
    for a in accts:
        st = account_stats(store, a, start, end, all_time, ups, snaps)
        prev = None if all_time else account_stats(store, a, pstart, pend, False, ups, snaps)
        st["views_prev"] = prev["views"] if comparable(store, a["account_id"], "views", st, prev, pstart) else None
        st["watch_prev"] = prev["watch_time_minutes"] if comparable(store, a["account_id"], "watch_time_minutes", st, prev, pstart) else None
        rows.append({**{k: a[k] for k in ("account_id", "platform", "language", "label", "handle")}, "stats": st,
                     "videos": sum(1 for u in ups if u["account_id"] == a["account_id"])})

    def total(key, prev_key=None):
        have = [r for r in rows if r["stats"][key] is not None]
        val = _sum(r["stats"][key] for r in have)
        prev = None
        if prev_key and have and all(r["stats"][prev_key] is not None for r in have):
            prev = _sum(r["stats"][prev_key] for r in have)
        return {"value": val, "prev": prev, "covered": [r["account_id"] for r in have],
                "missing": [r["account_id"] for r in rows if r["stats"][key] is None]}

    views = total("views", "views_prev")
    views["estimated"] = [r["account_id"] for r in rows if r["stats"]["basis"]["views"] == "daily snapshots"]
    views["partial"] = [r["account_id"] for r in rows if r["stats"]["partial"]["views"]]
    fol = total("followers")
    fol["change"] = _sum(r["stats"]["followers_change"] for r in rows) if rows and all(
        r["stats"]["followers_change"] is not None for r in rows if r["stats"]["followers"] is not None) else None
    starts = [r["stats"]["followers_start"] for r in rows if r["stats"]["followers"] is not None]
    fol["growth"] = round(100 * fol["change"] / sum(starts), 1) if fol["change"] is not None and starts and None not in starts and sum(starts) else None
    watch = total("watch_time_minutes", "watch_prev")
    eng = {m: total(m) for m in ENGAGEMENT}

    platforms = []
    for p in SOCIAL:
        pr = [r for r in rows if r["platform"] == p]
        if not pr:
            continue
        agg = {k: _sum(r["stats"][k] for r in pr) for k in ("views", "watch_time_minutes", "followers", "followers_change", *ENGAGEMENT)}
        agg["views_prev"] = _sum(r["stats"]["views_prev"] for r in pr) if all(r["stats"]["views_prev"] is not None for r in pr if r["stats"]["views"] is not None) else None
        av = avg_view_total(store, [a for a in accts if a["platform"] == p], [u for u in ups if u["platform"] == p], snaps, start, end)
        agg["avg_view_s"], agg["avg_view_basis"] = av["value"], av["basis"]
        agg["series"] = {m: _merge([r["stats"]["series"].get(m) for r in pr]) for m in ("views", "followers", "watch_time_minutes")}
        platforms.append({"platform": p, "accounts": [r["account_id"] for r in pr], "stats": agg})

    videos = []
    for u in ups:
        sn = snaps.get(u["upload_id"], {})
        lat = {m: latest(v["points"]) for m, v in sn.items()}
        g, part = gains(sn["views"]["points"], (u["published_at_utc"] or "")[:10], start, end, all_time) if "views" in sn else ({}, False)
        acct = next(a for a in accts if a["account_id"] == u["account_id"])
        videos.append({"upload_id": u["upload_id"], "platform": u["platform"], "account_id": u["account_id"],
                       "account_label": acct["label"], "language": u["asset_language"] or acct["language"],
                       "title": u["title"] or u["concept_title"] or u["platform_video_id"], "url": u["url"],
                       "published_at_utc": u["published_at_utc"], "asset_id": u["asset_id"], "concept_id": u["concept_id"],
                       "local_path": _local(u["edit_file"]) if u["edit_file"] else None, "metrics": lat,
                       "views_in_period": round(sum(g.values()), 2) if "views" in sn and not part else None,
                       "views_source": (sn.get("views") or {}).get("source")})
    return {"start": start, "end": end, "all_time": all_time, "prev": None if all_time else {"start": pstart, "end": pend},
            "filters": {k: f.get(k, "") for k in ("range", "platform", "account", "language")},
            "accounts": rows, "platforms": platforms,
            "totals": {"views": views, "followers": fol, "watch_time_minutes": watch, "engagement": eng,
                       "avg_view": avg_view_total(store, accts, ups, snaps, start, end)},
            "videos": videos, "has_data": bool(store.q("SELECT 1 FROM observations WHERE platform IN ('youtube','tiktok','instagram') LIMIT 1")),
            "generated_at": now_iso()}


def _merge(series_list):
    acc = {}
    for s in series_list:
        for p in s or []:
            acc[p["d"]] = acc.get(p["d"], 0) + p["v"]
    return [{"d": d_, "v": v} for d_, v in sorted(acc.items())] if acc else []


def video_detail(store, upload_id):
    """One publication: its history per metric (one source each) and the other publications of the same video."""
    u = store.q("SELECT * FROM uploads WHERE upload_id=?", (upload_id,))
    if not u:
        return None
    u = u[0]
    acct = store.account(u["account_id"]) or {}
    sn = snapshots(store, [u]).get(upload_id, {})
    hist = {m: [{"d": d_, "v": v} for d_, v in x["points"]] for m, x in sn.items()}
    sibs = store.q("SELECT * FROM uploads WHERE asset_id=? AND upload_id!=?", (u["asset_id"], upload_id)) if u["asset_id"] else []
    sib_snaps = snapshots(store, sibs)
    siblings = [{"upload_id": s["upload_id"], "platform": s["platform"], "account_id": s["account_id"],
                 "account_label": (store.account(s["account_id"]) or {}).get("label", s["account_id"]), "url": s["url"],
                 "published_at_utc": s["published_at_utc"],
                 "metrics": {m: latest(x["points"]) for m, x in sib_snaps.get(s["upload_id"], {}).items()}} for s in sibs]
    asset = store.q("""SELECT a.*, c.title concept_title FROM assets a JOIN concepts c USING(concept_id) WHERE asset_id=?""",
                    (u["asset_id"],)) if u["asset_id"] else []
    peers = [x for x in uploads_of(store, [u["account_id"]]) if x["upload_id"] != upload_id]
    peer_views = [latest(v["views"]["points"]) for v in snapshots(store, peers, ("views",)).values() if "views" in v]
    peer_views = sorted(x for x in peer_views if x is not None)
    exps = [{"experiment_id": e["experiment_id"], "title": e["title"], "status": e["status"]} for e in store.experiments()
            if e["status"] in ("running", "analysing", "decided") and u["asset_id"] and any(u["asset_id"] in v["asset_ids"] for v in e["variants"])]
    return {"upload": u, "local_path": _local(asset[0]["edit_file"]) if asset and asset[0]["edit_file"] else None,
            "account": {k: acct.get(k) for k in ("account_id", "platform", "language", "label", "handle")},
            "latest": {m: latest(x["points"]) for m, x in sn.items()}, "sources": {m: x["source"] for m, x in sn.items()},
            "history": hist, "siblings": siblings, "asset": asset[0] if asset else None,
            "account_median_views": peer_views[len(peer_views) // 2] if peer_views else None, "account_videos": len(peers) + 1,
            "experiments": exps, "checkpoints": checkpoints(store, u),
            "concept_id": asset[0]["concept_id"] if asset else None,
            "tags": concept_tags(store, asset[0]["concept_id"]) if asset else {}}


# ------------------------------------------------------------------ video library (Content page)
_probe_cache = {}


def _local(path):
    """Workspace-relative path of a playable local video (exports/ or media/ only), or None."""
    from .publish import resolve_video, rel
    if not path:
        return None
    cands = [path] if ("/" in path or "\\" in path) else [f"exports/{path}", path]
    for c in cands:
        try:
            return rel(resolve_video(c))
        except ValueError:
            continue
    return None


DELETABLE_JOB_STATES = ("draft", "failed")  # nothing approved, on its way, or posted


def delete_video(store, path, recycle=None):
    """Owner's Delete on the Content page: one local video (exports/ or media/ only) goes to the Recycle Bin with
    its sidecars, and its unsent drafts are removed. Refused while it is posted, approved or uploading."""
    from . import publish
    f = publish.resolve_video(path)
    relp = publish.rel(f)
    jobs = [j for j in store.q("SELECT job_id, state, video_path, asset_id FROM publish_jobs") if _local(j["video_path"]) == relp]
    busy = [j for j in jobs if j["state"] not in DELETABLE_JOB_STATES]
    if busy:
        raise ValueError(f"it is {busy[0]['state'].replace('_', ' ')} in Publish; finish or remove that first")
    assets = {a["asset_id"] for a in store.q("SELECT asset_id, edit_file FROM assets") if _local(a["edit_file"]) == relp}
    assets |= {j["asset_id"] for j in jobs}
    if assets and store.q(f"SELECT 1 FROM uploads WHERE asset_id IN ({','.join('?' * len(assets))}) LIMIT 1", tuple(assets)):
        raise ValueError("it has been posted; posted videos stay for their history")
    for j in jobs:
        publish.delete(store, j["job_id"])
    files = [f] + [x for x in (f.with_suffix(".qc.json"), f.with_suffix(".meta.json"), f.with_suffix(".sheet.jpg")) if x.exists()]
    for x in files:
        (recycle or _recycle)(x)
    return {"deleted": relp, "drafts_removed": len(jobs), "files": len(files)}


def _recycle(f):
    """Windows Recycle Bin, so a Delete can be undone from there."""
    import os
    import subprocess
    env = dict(os.environ, SS_RECYCLE=str(f))
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                    "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("
                    "$env:SS_RECYCLE, 'OnlyErrorDialogs', 'SendToRecycleBin')"], env=env, check=True, capture_output=True,
                   timeout=60)


def _probe(relpath):
    from .publish import ROOT, probe
    p = ROOT / relpath
    key = (relpath, p.stat().st_mtime)
    if key not in _probe_cache:
        _probe_cache[key] = probe(p) or {}
    return _probe_cache[key]


def library(store, show_posted=False):
    """Concepts = produced videos on this PC awaiting publication, grouped per concept with their language versions.
    Render-registry details (file names, QC, versions) stay available in each video's detail view."""
    from .views import local_renders
    assets = store.q("""SELECT a.*, c.title concept_title FROM assets a JOIN concepts c USING(concept_id) ORDER BY a.created_at_utc DESC""")
    jobs = store.q("SELECT job_id, asset_id, account_id, platform, state, video_path FROM publish_jobs")
    posted = {}
    for u in store.q("SELECT asset_id, platform, account_id, url FROM uploads WHERE asset_id IS NOT NULL"):
        posted.setdefault(u["asset_id"], []).append(u)
    items, seen = [], set()
    for a in assets:
        path = _local(a["edit_file"])
        if not path:
            continue
        seen.add(path.split("/")[-1])
        items.append({"key": a["concept_id"], "title": a["concept_title"], "asset_id": a["asset_id"], "path": path,
                      "language": a["language"], "version": a["version"], "fiction_label": a["fiction_label"]})
    by_asset = {a["asset_id"]: a for a in assets}
    for j in jobs:  # a draft may use another file of the same version (e.g. a re-export)
        a = by_asset.get(j["asset_id"])
        path = _local(j["video_path"])
        if a and path and path.split("/")[-1] not in seen:
            seen.add(path.split("/")[-1])
            items.append({"key": a["concept_id"], "title": a["concept_title"], "asset_id": a["asset_id"], "path": path,
                          "language": a["language"], "version": a["version"], "fiction_label": a["fiction_label"]})
    for r in local_renders():
        if r["test"] or r["file"] in seen:
            continue  # smoke-test renders aren't content
        items.append({"key": "render:" + r["concept"], "title": r["concept"], "asset_id": None, "path": f"exports/{r['file']}",
                      "language": r.get("language", ""), "version": r["version"], "fiction_label": "", "qc": r["qc"],
                      "variant": r.get("hook", "")})
    accounts = {a["account_id"]: a for a in store.accounts()}
    groups = {}
    for it in items:
        it["made_at"] = _made_at(it["path"])
        info = _probe(it["path"])
        it.update(duration_s=info.get("duration_s"), width=info.get("width"), height=info.get("height"),
                  qc=it.get("qc") or _qc(it["path"]))
        it["posted_on"] = [{"platform": u["platform"], "account_id": u["account_id"], "url": u["url"]} for u in posted.get(it["asset_id"], [])]
        it["jobs"] = [{"job_id": j["job_id"], "account_id": j["account_id"], "state": j["state"]} for j in jobs
                      if (it["asset_id"] and j["asset_id"] == it["asset_id"] and j["video_path"] == it["path"]) or j["video_path"] == it["path"]]
        it["status"] = "posted" if it["posted_on"] else "publishing" if any(j["state"] not in ("done",) for j in it["jobs"]) else "ready"
        it["audience"] = _audience(it, accounts)
        groups.setdefault(it["key"], {"key": it["key"], "title": it["title"], "versions": []})["versions"].append(it)
    out = []
    for g in groups.values():
        # newest first within each language: the card and the drawer open on versions[0] (owner, 2026-11-25:
        # the card kept playing V01 after V02 was made)
        g["versions"].sort(key=lambda v: (v["version"], v["made_at"] or ""), reverse=True)
        g["versions"].sort(key=lambda v: v["language"])
        g["languages"] = sorted({v["language"] for v in g["versions"] if v["language"]})
        g["made_at"] = max((v["made_at"] for v in g["versions"] if v["made_at"]), default="")
        auds = list(dict.fromkeys(v["audience"] for v in g["versions"]))
        if len(auds) == 1:
            g["audience"] = auds[0]
        else:  # versions differ: name every destination rather than summarise by one language
            parts = []
            for a in auds:
                for p in a.removeprefix("For: ").split(", "):
                    if p not in parts:
                        parts.append(p)
            g["audience"] = "For: " + ", ".join(parts)
        st = {v["status"] for v in g["versions"]}
        g["status"] = "ready" if "ready" in st else "publishing" if "publishing" in st else "posted"
        if show_posted or g["status"] != "posted":
            out.append(g)
    order = {"ready": 0, "publishing": 1, "posted": 2}
    return sorted(out, key=lambda g: (order[g["status"]], g["title"].lower()))


LANG_NAMES = {"en": "English", "es": "Spanish"}


def _made_at(relpath):
    """When the video file was made (its modification time), ISO UTC; blank when the file is missing."""
    from datetime import datetime, timezone
    from .publish import ROOT
    p = ROOT / relpath
    return datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds") if p.exists() else ""


def _audience(it, accounts):
    """Who a video is for, in plain words: the accounts it has drafts or posts on, else every active account in its
    language, else that the language isn't set yet."""
    named = [accounts[x["account_id"]] for x in it["jobs"] + it["posted_on"] if x["account_id"] in accounts]
    if named:
        seen = []
        for a in named:
            h = a["handle"] or a["account_id"]
            if h not in seen:
                seen.append(h)
        return "For: " + ", ".join(seen)
    lang = it.get("language") or ""
    if not lang:
        return "For: language not set"
    n = sum(1 for a in accounts.values() if a["language"] == lang and a["active"] and a["platform"] != "roblox")
    return f"For: all {LANG_NAMES.get(lang, lang.upper())} accounts ({n})"


def _qc(relpath):
    import json as _json
    from .publish import ROOT
    q = (ROOT / relpath).with_suffix(".qc.json")
    try:
        return _json.loads(q.read_text(encoding="utf-8")).get("overall", "") if q.exists() else ""
    except ValueError:
        return ""


def thumbnail(relpath):
    """A cached JPEG frame of a local video (FFmpeg, on this PC), or None."""
    import hashlib
    import subprocess
    from .publish import ROOT, _tool, resolve_video
    from .store import DATA
    p = resolve_video(relpath)
    out = DATA / "thumbs" / (hashlib.sha1(f"{p}:{p.stat().st_mtime}".encode()).hexdigest()[:20] + ".jpg")
    if out.exists():
        return out
    exe = _tool("ffmpeg")
    if not exe:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = (_probe(relpath) or {}).get("duration_s") or 2
    try:
        subprocess.run([exe, "-v", "error", "-y", "-ss", f"{min(1.0, dur / 3):.2f}", "-i", str(p), "-frames:v", "1",
                        "-vf", "scale=360:-2", "-q:v", "4", str(out)], capture_output=True, timeout=30, check=True)
    except (subprocess.SubprocessError, OSError):
        return None
    return out if out.exists() else None


# ------------------------------------------------------------------ creative tags (reusing the codebook and knowledge banks)
TAG_KEYS = ("format", "objective", "hook", "codes", "character", "humour", "mechanism")


def vocab():
    """Allowed tag values, all from existing systems: the creative codebook (hook and narrative codes), the knowledge
    banks (objectives, formats, characters, humour and mechanism entries) and the format presets."""
    import json as _json
    from .store import ROOT
    from .views import _kb
    cb = _json.loads((ROOT / "config" / "research" / "codebooks" / "slugshot-creative.json").read_text(encoding="utf-8"))
    kb = _kb()
    try:
        entries = kb.load()
    except Exception:  # knowledge banks unavailable: tags still work with codebook values
        entries = []

    def bank(name):
        return [{"id": e["id"], "label": e.get("title", e["id"])} for e in entries
                if e.get("bank") == name and e.get("review_status") != "retired" and e.get("kind") != "inventory_item"]
    codes = [{"id": c["code"], "label": c["code"].replace("_", " ").title(), "hint": c.get("criterion", "")} for c in cb["codes"]]
    return {"format": [{"id": f, "label": f.title()} for f in sorted(kb.FORMATS - {"TEST"})],
            "objective": [{"id": o, "label": o.replace("_", " ")} for o in sorted(kb.OBJECTIVES)],
            "hook": codes, "codes": codes, "character": roster(), "humour": bank("humour"),
            "mechanism": bank("mechanisms"), "codebook_version": cb.get("version")}


def roster():
    """Characters a video shows: the game's names from the caption glossary (kept current from the game's status page),
    not the characters bank, whose entries are guidance about characters."""
    import json as _json
    from .store import ROOT
    g = _json.loads((ROOT / "config" / "glossary.json").read_text(encoding="utf-8"))
    skip = {"Slugshot", "Roblox"}
    return [{"id": t["term"], "label": t["term"]} for t in g.get("terms", []) if t["term"] not in skip and t["term"][:1].isupper()]


def clean_tags(tags):
    v = vocab()
    out = {}
    for k in TAG_KEYS:
        vals = tags.get(k) or []
        vals = [vals] if isinstance(vals, str) else list(vals)
        allowed = {x["id"] for x in v[k]}
        bad = [x for x in vals if x not in allowed]
        if bad:
            raise ValueError(f"unknown {k} tag(s): {', '.join(bad)}")
        out[k] = vals[:1] if k == "hook" else vals
    return out


def concept_tags(store, concept_id):
    import json as _json
    r = store.q("SELECT tags, format FROM concepts WHERE concept_id=?", (concept_id,))
    if not r:
        return {}
    t = _json.loads(r[0]["tags"] or "{}")
    if not t.get("format") and r[0]["format"]:
        t["format"] = [r[0]["format"]]
    return t


# ------------------------------------------------------------------ measurement windows
# Videos are compared at the same age after publication. Tolerances follow the refresh rhythm: videos under 8 days
# old are refreshed every few hours (settings young_refresh_hours), older ones daily.
CHECKPOINTS = {"24h": (24, 6), "48h": (48, 8), "7d": (168, 24)}
CP_METRICS = ("views", "likes", "comments", "shares", "saves", "watch_time_minutes", "followers_gained")


def _age(iso, t0):
    t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (t - t0).total_seconds() / 3600


def checkpoints(store, upload, metrics=CP_METRICS):
    """{checkpoint: {metric: {value, age_h, within}}}: the reading nearest each age. `within` False means it lies
    outside the tolerance, so it is shown flagged and never compared with other videos at that checkpoint."""
    pub = upload.get("published_at_utc")
    if not pub:
        return {}
    t0 = datetime.fromisoformat(pub.replace("Z", "+00:00"))
    if t0.tzinfo is None:
        t0 = t0.replace(tzinfo=timezone.utc)
    rows = store.q(f"""SELECT metric, source, value, observed_at_utc FROM observations WHERE entity_type='upload' AND entity_id=?
                       AND period_type='lifetime' AND status='value' AND metric IN ({_in(list(metrics))})""",
                   (upload["upload_id"], *metrics))
    by = {}
    for r in rows:
        by.setdefault(r["metric"], {}).setdefault(r["source"], []).append(r)
    out = {}
    for cp, (target, tol) in CHECKPOINTS.items():
        for m, srcs in by.items():
            src = min(srcs, key=lambda s: (_rank(upload["platform"], s), -len(srcs[s])))
            best = min(srcs[src], key=lambda r: abs(_age(r["observed_at_utc"], t0) - target))
            age = _age(best["observed_at_utc"], t0)
            if age < 0:
                continue
            out.setdefault(cp, {})[m] = {"value": best["value"], "age_h": round(age, 1), "within": abs(age - target) <= tol}
    return out


# ------------------------------------------------------------------ comparable performance
def compare(store, f):
    """Groups of comparable videos: one platform, optionally one language, all read at the same checkpoint (within
    tolerance), grouped by a creative tag. Medians and ranges per group. Videos read outside the window, without a
    reading or without the tag are counted and left out, never silently mixed in."""
    platform = f.get("platform")
    if platform not in SOCIAL:
        raise ValueError("choose one platform: videos are only compared within a platform")
    cp = f.get("checkpoint") or "48h"
    if cp not in CHECKPOINTS:
        raise ValueError("checkpoint must be 24h, 48h or 7d")
    metric, by = f.get("metric") or "views", f.get("by") or "format"
    if by not in TAG_KEYS:
        raise ValueError(f"group by one of {', '.join(TAG_KEYS)}")
    accts = accounts_for(store, {"platform": platform, "language": f.get("language", "")})
    ups = uploads_of(store, [a["account_id"] for a in accts])
    groups, excluded, base = {}, {"outside_window": 0, "no_reading": 0, "untagged": 0}, []
    for u in ups:
        r = checkpoints(store, u, (metric,)).get(cp, {}).get(metric)
        if not r:
            excluded["no_reading"] += 1
            continue
        if not r["within"]:
            excluded["outside_window"] += 1
            continue
        tags = concept_tags(store, u["concept_id"]) if u["concept_id"] else {}
        vals = tags.get(by) or []
        item = {"upload_id": u["upload_id"], "title": u["title"] or u["concept_title"] or u["platform_video_id"],
                "concept_id": u["concept_id"], "value": r["value"], "age_h": r["age_h"]}
        base.append(item)
        if not vals:
            excluded["untagged"] += 1
        for v in vals:
            groups.setdefault(v, []).append(item)

    def summary(items):
        xs = sorted(i["value"] for i in items)
        n = len(xs)
        med = (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2) if n else None
        return {"n": n, "median": med, "low": xs[0] if xs else None, "high": xs[-1] if xs else None,
                "enough": n >= 3, "videos": sorted(items, key=lambda i: -i["value"])}
    out = [{"key": k, **summary(v)} for k, v in groups.items()]
    out.sort(key=lambda g: (-g["n"], -(g["median"] or 0)))
    return {"platform": platform, "language": f.get("language", ""), "checkpoint": cp, "tolerance_h": CHECKPOINTS[cp][1],
            "metric": metric, "by": by, "all": summary(base), "groups": out, "excluded": excluded,
            "multi_label": by in ("codes", "character", "humour", "mechanism", "objective"),
            "note": "Patterns across groups, not single videos. Groups under 3 videos are shown but are too small to compare."}


# ------------------------------------------------------------------ learning loop
def finding_draft(result, group, statement="", link_to="", link_type="supports"):
    """A draft knowledge-bank entry (bank claims, kind observation, evidence owned_result) from a comparison. It stays a
    draft until the owner reviews it; `ss kb validate` checks it; `ss kb brief` then surfaces it for the next brief."""
    import hashlib
    g = next((x for x in result["groups"] if x["key"] == group), None)
    if not g:
        raise ValueError(f"no group {group} in this comparison")
    concepts = sorted({v["concept_id"] for v in g["videos"] if v["concept_id"]})
    if not concepts:
        raise ValueError("the videos in this group aren't linked to concepts yet")
    day = date.today().isoformat()
    tags = {"objective": [], "funnel_stage": ["Discovery"], "journey": [], "mechanism": [], "format": [], "codes": [],
            "character": [], "language": [result["language"]] if result["language"] else [], "market": []}
    key = {"format": "format", "codes": "codes", "hook": "codes", "mechanism": "mechanism", "objective": "objective",
           "character": "character"}.get(result["by"])
    if key:
        tags[key] = [group]
    lang = f" {result['language'].upper()}" if result["language"] else ""
    text = statement or (f"On {result['platform']}{lang}, videos tagged {group} had a median of {g['median']:g} {result['metric']} at "
                         f"{result['checkpoint']} (n={g['n']}, range {g['low']:g} to {g['high']:g}), against {result['all']['median']:g} "
                         f"for all {result['all']['n']} comparable videos. Observational, not a controlled test.")
    hid = hashlib.sha1(f"{result['platform']}{result['checkpoint']}{result['by']}{group}{day}".encode()).hexdigest()[:4].upper()
    return {"schema_version": "kb-1.0", "id": f"CLM-OWN-{day.replace('-', '')}-{hid}", "bank": "claims", "kind": "observation",
            "title": f"{result['platform']}{lang} at {result['checkpoint']}: {result['by']} {group}", "statement": text,
            "evidence_label": "owned_result", "support_status": "supported" if g["enough"] else "indeterminate",
            "strength": "suggestive" if g["n"] >= 5 else "exploratory", "review_status": "draft", "shelf_life": "platform_90d",
            "observed_at": day, "review_by": (date.today() + timedelta(days=90)).isoformat(),
            "evidence_refs": concepts, "concept_refs": concepts, "claim_refs": [], "report_aliases": [],
            "boundaries": f"{result['platform']} only; read at {result['checkpoint']} +/-{result['tolerance_h']} h; "
                          f"{result['excluded']['outside_window']} video(s) outside the window left out.",
            "rivals": ["topic and posting time differ between videos", "small samples"], "transfer_assumption": "",
            "tags": tags, "game_truth": [], "links": [{"type": link_type, "to": link_to}] if link_to else [],
            "history": [{"at": now_iso(), "by": "dashboard compare", "change": "drafted"}]}


def save_finding(entry):
    """Append a draft finding to the curated knowledge bank, refusing anything the bank's validator rejects for it."""
    import json as _json
    from .views import _kb
    kb = _kb()
    errs, _ = kb.validate(kb.load() + [entry])
    mine = [e for e in errs if entry["id"] in e]
    if mine:
        raise ValueError("; ".join(mine)[:400])
    path = kb.kb_dir() / "curated" / "owned_findings.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(_json.dumps(entry, ensure_ascii=False) + "\n")
    return {"id": entry["id"], "file": str(path)}
