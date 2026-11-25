"""Synchronisation: runs each ready connector per account, isolates failures, records every run.

- Daily by default (settings.refresh_hours); stale data refreshes when the dashboard opens and on an
  hourly check while it runs. Manual refresh from the UI or `ss dash sync`.
- One connector failing (network, quota, revoked token) is recorded and skipped; the rest carry on.
- Day-level data is re-read over the last 3 days (late corrections) and deduplicated by period.
"""
import os
import threading
import traceback
from datetime import datetime, timedelta, timezone

from . import connectors as C
from .store import Store, now_iso, settings

_running = threading.Lock()
_state = {"running": False, "started_at": None, "last_result": None}


def state():
    return dict(_state)


def targets(store, only=None):
    out = []
    for a in store.accounts():
        if not a["active"]:
            continue
        for name in C.BY_PLATFORM.get(a["platform"], []):
            if only and name not in only and a["account_id"] not in only and a["platform"] not in only:
                continue
            out.append((C.CONNECTORS[name], a))
    return out


def health(store):
    """One row per connector x account: credential state, last run, freshness. Never includes secrets."""
    cfg = settings()
    rows = []
    last = {(r["connector"], r["account_id"]): r for r in store.last_runs()}
    for con, a in targets(store):
        cred = con.credential_state(a)
        if os.environ.get("SLUGSHOT_DASH_FIXTURE"):
            cred = "ready"  # fixture database: replayed responses stand in for credentials (UI is labelled FIXTURE)
        ok_at = store.last_success(con.name, a["account_id"])
        r = last.get((con.name, a["account_id"]))
        if cred != "ready":
            fresh = "not connected"
        elif not ok_at:
            fresh = "never synced"
        else:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(ok_at)).total_seconds() / 3600
            fresh = "fresh" if age < cfg["refresh_hours"] else ("due" if age < cfg["stale_hours"] else "stale")
        rows.append({"connector": con.name, "label": con.label, "route": con.route, "platform": a["platform"],
                     "account_id": a["account_id"], "account_label": a["label"], "language": a["language"],
                     "credential": cred, "last_success_utc": ok_at, "last_status": r["status"] if r else None,
                     "last_message": r["message"] if r else "", "freshness": fresh,
                     "fixture": bool(r and r.get("fixture"))})
    return rows


def refresh_hours(store, account, cfg):
    """Daily, but every few hours while the account has a video under young_days old, so 24 h and 48 h readings
    land close to those ages (analytics.CHECKPOINTS)."""
    young = (datetime.now(timezone.utc) - timedelta(days=cfg.get("young_days", 8))).isoformat()
    if store.q("SELECT 1 FROM uploads WHERE account_id=? AND published_at_utc >= ? LIMIT 1", (account["account_id"], young)):
        return cfg.get("young_refresh_hours", 4)
    return cfg["refresh_hours"]


def run(store=None, only=None, fixture=None, due_only=False, sleep=None):
    """Sync every ready target (or the ones named in `only`). Returns a list of per-target results."""
    if not _running.acquire(blocking=False):
        return [{"status": "busy", "message": "a sync is already running"}]
    store = store or Store()
    fixture = bool(os.environ.get("SLUGSHOT_DASH_FIXTURE")) if fixture is None else fixture
    _state.update(running=True, started_at=now_iso())
    results = []
    try:
        cfg = settings()
        for con, a in targets(store, only):
            if not fixture and con.credential_state(a) != "ready":
                continue
            if due_only:
                ok_at = store.last_success(con.name, a["account_id"])
                if ok_at and datetime.now(timezone.utc) - datetime.fromisoformat(ok_at) < timedelta(hours=refresh_hours(store, a, cfg)):
                    continue
            run_id = f"{con.name}-{a['account_id']}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{os.urandom(2).hex()}"
            store.start_run(run_id, con.name, a["account_id"])
            ctx = C.Ctx(fixture=fixture, **({"sleep": sleep} if sleep else {}))
            ctx.variant = a["language"]
            try:
                out = con.sync(store, a, ctx, run_id)
                n, msg = out if isinstance(out, tuple) else (out, "")
                status = "partial" if msg else "ok"
            except C.NeedsAuth as e:
                n, status, msg = 0, "needs_auth", str(e)
            except C.rc.HttpError as e:
                n, status, msg = 0, "failed", f"HTTP {e.status}: {e.reason}"
            except Exception as e:  # isolate anything unexpected; keep the message short and secret-free
                n, status, msg = 0, "failed", f"{type(e).__name__}: {C.rc.redact(str(e))[:200]}"
                traceback.print_exc()
            store.finish_run(run_id, status, n, ctx.ok, ctx.failed, msg)
            results.append({"connector": con.name, "account_id": a["account_id"], "status": status, "rows": n, "message": msg})
        store.prune_expired()
    finally:
        _state.update(running=False, last_result=results)
        _running.release()
    return results


def run_in_background(**kw):
    t = threading.Thread(target=run, kwargs=kw, daemon=True)
    t.start()
    return t


def auto_refresh_loop(stop):
    """While the server runs: sync anything due, then check hourly. No OS scheduler involved."""
    while not stop.is_set():
        try:
            store = Store()
            if store.pref("auto_refresh", settings().get("auto_refresh", True)):
                run(store, due_only=True)
            from . import hosting, publish
            if hosting.ready() and hosting.hosted(store):
                hosting.cleanup(store, publish._transport())  # abandoned hosted videos; finished ones go at once
        except Exception:
            traceback.print_exc()
        stop.wait(3600)
