"""Temporary video hosting for Buffer (which only accepts a public link): Cloudinary, free plan.

Flow: the owner approves a Buffer job -> the approved file (same SHA-256 the approval bound) is uploaded once
-> Buffer gets a signed link -> once every Buffer job using that file has finished, the file is deleted.

Safety:
- Only approved files are uploaded (publish.run calls host() after re-checking the approval's file hash).
- Delivery type `authenticated`: the file is reachable only through a signed link, and nobody can request
  on-the-fly transformations (which would spend credits). We never request transformations or add-ons.
- One upload per file: public_id is derived from the file hash, so retries overwrite instead of duplicating,
  and TikTok EN/ES and Instagram share one hosted copy.
- Free-tier guard (settings publishing.hosting): file size, number of hosted files, and credit/storage/bandwidth
  percentages are checked before every upload; the plan is never changed and no payment method is touched.
- Signed links and credentials are never logged, stored in job results or exported.

Live facts (Cloudinary docs, 2026-11-25): Free = 25 credits per rolling 30 days (1 credit = 1 GB storage, or
1 GB video bandwidth, or 1,000 transformations); an upload counts as 1 transformation; max video 100 MB;
Admin API 500 requests/hour; exceeding the free plan disables the account rather than billing it.
"""
import base64
import hashlib
import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

from . import vault
from .store import now_iso, settings

API = "https://api.cloudinary.com/v1_1"
DEFAULTS = {"provider": "cloudinary", "folder": "slugshot-publish", "max_file_mb": 95, "max_hosted_files": 5,
            "max_credit_pct": 60, "max_storage_pct": 60, "max_bandwidth_pct": 60, "abandon_hours": 72,
            "usage_cache_minutes": 60}
_locks = {}
_guard = threading.Lock()


class HostingError(Exception):
    pass


def cfg():
    return {**DEFAULTS, **settings().get("publishing", {}).get("hosting", {})}


def creds():
    return tuple(vault.secret(n) for n in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"))


def ready():
    if os.environ.get("SLUGSHOT_DASH_FIXTURE"):
        return True
    return all(creds())


def _sign(params, secret):
    s = "&".join(f"{k}={params[k]}" for k in sorted(params)) + secret
    return hashlib.sha1(s.encode()).hexdigest()


def _basic():
    _, key, secret = creds()
    return {"Authorization": "Basic " + base64.b64encode(f"{key}:{secret}".encode()).decode()}


def _err(st, body):
    msg = (body.get("error") or {}).get("message", "") if isinstance(body, dict) else ""
    return HostingError(f"Cloudinary refused (HTTP {st}): {msg[:200]}")


def public_id(sha):
    return f"{cfg()['folder']}/{sha[:32]}"


def signed_url(row):
    """Signed delivery link to the original file (no transformation). Never log or store it."""
    cloud, _, secret = creds()
    if os.environ.get("SLUGSHOT_DASH_FIXTURE"):
        cloud, secret = "fixture", "fixture"
    tail = f"v{row['version']}/{row['public_id']}.{row['format']}"
    sig = base64.urlsafe_b64encode(hashlib.sha1((tail + secret).encode()).digest()).decode()[:8]
    return f"https://res.cloudinary.com/{cloud}/video/authenticated/s--{sig}--/{tail}"


# ------------------------------------------------------------------ usage and limits
def usage(store, tx, force=False):
    """Cloudinary plan usage (cached; the Admin API allows 500 requests an hour on Free)."""
    c = store.pref("cloudinary_usage")
    if c and not force and time.time() - c["fetched"] < cfg()["usage_cache_minutes"] * 60:
        return c
    cloud = creds()[0] or "fixture"
    st, _, r = tx.json("GET", f"{API}/{cloud}/usage", headers=_basic())
    if st != 200:
        raise _err(st, r)

    def part(k):
        v = r.get(k) or {}
        return {"usage": v.get("usage"), "limit": v.get("limit"), "used_percent": v.get("used_percent")} if isinstance(v, dict) else {"usage": v}
    out = {"fetched": time.time(), "fetched_at": now_iso(), "plan": r.get("plan", ""), "last_updated": r.get("last_updated", ""),
           "credits": part("credits"), "storage": part("storage"), "bandwidth": part("bandwidth"),
           "transformations": part("transformations"), "objects": part("objects"),
           "video_max_bytes": (r.get("media_limits") or {}).get("video_max_size_bytes")}
    store.set_pref("cloudinary_usage", out)
    return out


def hosted(store, live_only=True):
    sql = "SELECT * FROM hosted_assets" + (" WHERE state IN ('uploading','hosted','failed')" if live_only else "") + " ORDER BY created_at_utc DESC"
    return store.q(sql)


def guard(store, size, tx):
    """Refuse an upload that could push the free plan towards its limits. Returns the usage it checked."""
    c = cfg()
    u = usage(store, tx)
    cap = min(c["max_file_mb"] * 1024 ** 2, u.get("video_max_bytes") or 100 * 1024 ** 2)
    if size > cap:
        raise HostingError(f"the file is {size / 1e6:.0f} MB; the hosting limit is {cap / 1e6:.0f} MB (compress it locally)")
    for k, lim in (("credits", c["max_credit_pct"]), ("storage", c["max_storage_pct"]), ("bandwidth", c["max_bandwidth_pct"])):
        pct = (u.get(k) or {}).get("used_percent")
        if pct is not None and pct >= lim:
            raise HostingError(f"Cloudinary {k} at {pct:.0f}% of the free plan (our limit {lim}%); wait for the 30-day window or clean up")
    if len(hosted(store)) >= c["max_hosted_files"]:
        raise HostingError(f"{c['max_hosted_files']} files are already hosted; finish or clean up those jobs first")
    return u


# ------------------------------------------------------------------ upload, check, delete
def _multipart(fields, file_name, data):
    b = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{file_name}"\r\nContent-Type: video/mp4\r\n\r\n'.encode())
    return b"".join(parts) + data + f"\r\n--{b}--\r\n".encode(), f"multipart/form-data; boundary={b}"


def host(store, sha, path, tx, log=lambda m: None):
    """Upload the approved file once (or reuse it) and return the row. Retries overwrite the same public_id."""
    with _guard:
        lock = _locks.setdefault(sha, threading.Lock())
    with lock:
        row = (store.q("SELECT * FROM hosted_assets WHERE sha256=?", (sha,)) or [None])[0]
        if row and row["state"] == "hosted":
            log("reusing the hosted copy of this file")
            return row
        size = path.stat().st_size
        guard(store, size, tx)
        cloud, key, secret = creds()
        pid = public_id(sha)
        t = now_iso()
        store.x("""INSERT INTO hosted_assets(sha256, provider, public_id, state, bytes, created_at_utc, updated_at_utc)
                   VALUES (?,?,?,?,?,?,?) ON CONFLICT(sha256) DO UPDATE SET state='uploading', updated_at_utc=excluded.updated_at_utc,
                   last_error=''""", (sha, "cloudinary", pid, "uploading", size, t, t))
        params = {"public_id": pid, "overwrite": "true", "type": "authenticated", "timestamp": str(int(time.time()))}
        fields = {**params, "api_key": key or "fixture", "signature": _sign(params, secret or "fixture")}
        body, ctype = _multipart(fields, path.name, path.read_bytes())
        log(f"hosting {size / 1e6:.1f} MB on Cloudinary (private signed link)")
        st, raw = 0, b""
        for attempt in range(3):
            st, _, raw = tx.request("POST", f"{API}/{cloud or 'fixture'}/video/upload", {"Content-Type": ctype}, body, timeout=600)
            if st in (0, 429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(0 if os.environ.get("SLUGSHOT_DASH_FIXTURE") else 5 * (attempt + 1))
                continue
            break
        try:
            r = json.loads(raw or b"{}")
        except ValueError:
            r = {}
        if st != 200 or not r.get("public_id"):
            store.x("UPDATE hosted_assets SET state='failed', last_error=?, updated_at_utc=? WHERE sha256=?",
                    (str(_err(st, r))[:300], now_iso(), sha))
            raise _err(st, r)
        if r.get("type") != "authenticated" or int(r.get("bytes") or 0) != size:
            destroy(store, sha, tx, pid)
            raise HostingError("Cloudinary stored something other than the approved file; it was deleted again")
        store.x("""UPDATE hosted_assets SET state='hosted', public_id=?, version=?, format=?, bytes=?, updated_at_utc=?
                   WHERE sha256=?""", (r["public_id"], str(r.get("version", "")), r.get("format") or "mp4", r["bytes"], now_iso(), sha))
        row = store.q("SELECT * FROM hosted_assets WHERE sha256=?", (sha,))[0]
        if not reachable(row, tx):
            raise HostingError("the hosted link didn't answer; retry")
        return row


def reachable(row, tx):
    """Fetch the first byte through the signed link, as Buffer would."""
    st, _, _ = tx.request("GET", signed_url(row), {"Range": "bytes=0-0"}, timeout=60)
    return st in (200, 206)


def destroy(store, sha, tx, pid=None):
    cloud, key, secret = creds()
    row = (store.q("SELECT * FROM hosted_assets WHERE sha256=?", (sha,)) or [None])[0]
    pid = pid or (row or {}).get("public_id") or public_id(sha)
    params = {"public_id": pid, "type": "authenticated", "invalidate": "true", "timestamp": str(int(time.time()))}
    st, _, r = tx.json("POST", f"{API}/{cloud or 'fixture'}/video/destroy",
                       form={**params, "api_key": key or "fixture", "signature": _sign(params, secret or "fixture")})
    if st != 200 or r.get("result") not in ("ok", "not found"):
        store.x("UPDATE hosted_assets SET last_error=?, updated_at_utc=? WHERE sha256=?", (str(_err(st, r))[:300], now_iso(), sha))
        raise _err(st, r)
    store.x("UPDATE hosted_assets SET state='deleted', deleted_at_utc=?, updated_at_utc=? WHERE sha256=?", (now_iso(), now_iso(), sha))
    return r.get("result")


# ------------------------------------------------------------------ lifecycle
PENDING = ("draft", "approved", "uploading", "processing", "in_buffer_drafts", "failed")


def _jobs_for(store, sha):
    out = []
    for r in store.q("SELECT job_id, state, approval, fields, updated_at_utc FROM publish_jobs WHERE route='buffer'"):
        try:
            a = json.loads(r["approval"] or "{}")
            f = json.loads(r["fields"] or "{}")
        except ValueError:
            continue
        if a.get("file_sha256") == sha and not f.get("video_url"):
            out.append(r)
    return out


def release(store, sha, tx):
    """Delete the hosted copy once every Buffer job that uses it has finished. Returns True if deleted."""
    row = (store.q("SELECT * FROM hosted_assets WHERE sha256=? AND state IN ('hosted','failed','uploading')", (sha,)) or [None])[0]
    if not row:
        return False
    if any(j["state"] in PENDING for j in _jobs_for(store, sha)):
        return False
    destroy(store, sha, tx)
    return True


def cleanup(store, tx, now=None):
    """Delete hosted copies nobody needs: no unfinished job, or only failed/abandoned ones older than abandon_hours."""
    now = now or datetime.now(timezone.utc)
    cut = now - timedelta(hours=cfg()["abandon_hours"])
    done = []
    for row in hosted(store):
        jobs = _jobs_for(store, row["sha256"])
        live = [j for j in jobs if j["state"] in PENDING and not (
            j["state"] in ("failed", "draft") and datetime.fromisoformat(j["updated_at_utc"]) < cut)]
        stale_upload = row["state"] in ("uploading", "failed") and datetime.fromisoformat(row["updated_at_utc"]) < cut
        if not live or stale_upload:
            try:
                destroy(store, row["sha256"], tx)
                done.append(row["public_id"])
            except HostingError:
                pass
    return done


def status(store, tx=None, refresh=False):
    """For the Settings page: usage, limits, hosted files (no links, no credentials) and Buffer's API quota."""
    out = {"configured": ready(), "limits": cfg(), "usage": store.pref("cloudinary_usage"), "error": store.pref("cloudinary_error", ""),
           "hosted": [{k: r[k] for k in ("public_id", "state", "bytes", "created_at_utc", "updated_at_utc", "last_error")}
                      for r in hosted(store, live_only=False)[:20]],
           "buffer_quota": store.pref("buffer_quota")}
    if refresh and out["configured"] and tx is not None:
        try:
            out["usage"], out["error"] = usage(store, tx, force=True), ""
        except Exception as e:  # shown on the page; never includes credentials
            out["error"] = str(e)[:200]
        store.set_pref("cloudinary_error", out["error"])
    return out


TEST_CARD = "media/_integration_test/upload_test_1080x1920.mp4"


def selftest(store, tx):
    """Live check with the neutral test card only: upload, fetch through the signed link, delete, confirm gone."""
    from .publish import sha256, resolve_video
    p = resolve_video(TEST_CARD)
    sha = sha256(p)
    steps = []
    u = usage(store, tx, force=True)
    steps.append(f"auth + usage OK: plan {u.get('plan')}, credits {(u.get('credits') or {}).get('used_percent')}%")
    row = host(store, sha, p, tx)
    steps.append(f"upload OK: {row['bytes']} bytes, type authenticated, signed link answers")
    st, _, _ = tx.request("GET", signed_url(row).replace("/s--", "/s--x"), {"Range": "bytes=0-0"}, timeout=60)
    steps.append(f"tampered link refused: HTTP {st}")
    steps.append(f"delete: {destroy(store, sha, tx)}")
    for waited in range(0, 181, 15):  # the CDN can serve a cached copy for a little while after the delete
        st, _, _ = tx.request("GET", signed_url(row), {"Range": "bytes=0-0"}, timeout=60)
        if st not in (200, 206) or os.environ.get("SLUGSHOT_DASH_FIXTURE"):
            break
        time.sleep(15)
    steps.append(f"link after delete: HTTP {st} after ~{waited} s")
    return steps
