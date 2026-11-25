"""Local HTTP server for the dashboard: loopback only, no login, no hosting.

Protections: binds 127.0.0.1; rejects any Host header other than 127.0.0.1/localhost:<port> (DNS
rebinding); rejects cross-origin requests; every write needs the per-start token embedded in the page.
Credentials can be written to the vault but are never sent back.
"""
import json
import mimetypes
import os
import secrets
import threading
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import analytics, imports, oauth, publish, reports, sync, vault, views
from .connectors import CONNECTORS
from .store import DATA, ROOT, Store, is_fixture_db, metric_defs, settings

STATIC = Path(__file__).resolve().parent / "static"
CRED_NAMES = {"YOUTUBE_OAUTH_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_SECRET", "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET",
              "ROBLOX_ANALYTICS_API_KEY", "BUFFER_API_KEY", "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"}
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")


class App:
    def __init__(self, port):
        self.port = port
        self.token = secrets.token_urlsafe(24)
        self.store = Store()
        self.stop = threading.Event()


def make_handler(app):
    hosts = {f"127.0.0.1:{app.port}", f"localhost:{app.port}"}
    origins = {f"http://{h}" for h in hosts}

    class H(BaseHTTPRequestHandler):
        server_version = "SlugshotDashboard"

        def log_message(self, fmt, *args):  # quiet; never log query strings (OAuth codes)
            pass

        def _send(self, code, body, ctype="application/json", extra=None):
            data = body if isinstance(body, bytes) else (json.dumps(body, default=str).encode() if ctype == "application/json" else body.encode())
            self.send_response(code)
            self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith(("text", "application/json")) else ""))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store" if ctype == "application/json" else "no-cache")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _guard(self, write):
            if self.headers.get("Host") not in hosts:
                self._send(403, {"error": "bad host"})
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in origins:
                self._send(403, {"error": "cross-origin request refused"})
                return False
            if write and not secrets.compare_digest(self.headers.get("X-Dash-Token", ""), app.token):
                self._send(403, {"error": "missing token"})
                return False
            return True

        def _params(self):
            q = urllib.parse.urlparse(self.path).query
            return {k: v[-1] for k, v in urllib.parse.parse_qs(q).items()}

        def do_GET(self):
            if not self._guard(False):
                return
            path = urllib.parse.urlparse(self.path).path
            p, s = self._params(), app.store
            try:
                if path in ("/", "/index.html"):
                    html = (STATIC / "index.html").read_text(encoding="utf-8")
                    html = html.replace("__TOKEN__", app.token).replace("__FIXTURE__", "true" if is_fixture_db() else "false")
                    return self._send(200, html, "text/html", {"Content-Security-Policy":
                        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"})
                if path in ("/sw.js", "/manifest.webmanifest"):
                    return self._static(path.lstrip("/"))
                if path.startswith("/static/"):
                    return self._static(path[len("/static/"):])
                if path == "/oauth/callback":
                    ok, msg = oauth.finish(p)
                    if ok:
                        sync.run_in_background()
                    return self._send(200, f"<!doctype html><meta charset=utf-8><title>Slugshot</title><body style='font:16px system-ui;padding:40px;background:#040827;color:#fff8ff'><p>{msg}</p>", "text/html")
                api = {
                    "/api/health": lambda: {"ok": True, "app": "slugshot-dashboard", "fixture": is_fixture_db()},
                    "/api/status": lambda: {"sources": sync.health(s), "sync": sync.state(), "fixture": is_fixture_db(),
                                            "auto_refresh": s.pref("auto_refresh", settings().get("auto_refresh", True)),
                                            "credentials": {n: bool(vault.secret(n)) for n in sorted(CRED_NAMES)},
                                            "imports": s.q("SELECT * FROM imports ORDER BY imported_at_utc DESC LIMIT 8"),
                                            "redirect_uri": oauth.redirect_uri()},
                    "/api/meta": lambda: {"metrics": metric_defs(), "accounts": s.accounts(),
                                          "capabilities": {k: c.capabilities for k, c in CONNECTORS.items()}},
                    "/api/overview": lambda: views.overview(s, p),
                    "/api/content": lambda: views.content(s, p),
                    "/api/renders": lambda: views.local_renders(),
                    "/api/research": lambda: views.research(s),
                    "/api/game": lambda: views.game(s, p),
                    "/api/experiments": lambda: views.experiments(s),
                    "/api/knowledge": lambda: views.knowledge(p),
                    "/api/hypotheses": lambda: views.hypothesis_families(),
                    "/api/analytics": lambda: analytics.analytics(s, p),
                    "/api/library": lambda: analytics.library(s, p.get("posted") == "1"),
                    "/api/services": lambda: views.service_usage(s),
                    "/api/vocab": lambda: analytics.vocab(),
                    "/api/compare": lambda: analytics.compare(s, p),
                }
                if path in api:
                    return self._send(200, api[path]())
                if path.startswith("/api/knowledge/"):
                    d = views.knowledge_entry(urllib.parse.unquote(path.rsplit("/", 1)[1]))
                    return self._send(200 if d else 404, d or {"error": "not found"})
                if path == "/api/hosting":
                    from . import hosting
                    return self._send(200, hosting.status(s, publish._transport(), refresh=p.get("refresh") == "1"))
                if path == "/api/publish":
                    return self._send(200, views.publish_page(s))
                if path.startswith("/api/publish/job/"):
                    d = views.publish_job(s, urllib.parse.unquote(path.rsplit("/", 1)[1]))
                    return self._send(200 if d else 404, d or {"error": "not found"})
                if path.startswith("/api/publish/media/"):
                    j = publish.job(s, urllib.parse.unquote(path.rsplit("/", 1)[1]))
                    return self._media(publish.resolve_video(j["video_path"])) if j else self._send(404, {"error": "not found"})
                if path == "/api/media":  # local videos for the Content gallery: exports/ and media/ only
                    return self._media(publish.resolve_video(p.get("path", "")))
                if path == "/api/thumb":
                    t = analytics.thumbnail(p.get("path", ""))
                    return self._send(200, t.read_bytes(), "image/jpeg") if t else self._send(404, {"error": "no thumbnail"})
                if path.startswith("/api/video/"):
                    d = analytics.video_detail(s, urllib.parse.unquote(path.rsplit("/", 1)[1]))
                    return self._send(200 if d else 404, d or {"error": "not found"})
                if path.startswith("/api/upload/"):
                    d = views.upload_detail(s, urllib.parse.unquote(path.rsplit("/", 1)[1]))
                    return self._send(200 if d else 404, d or {"error": "not found"})
                self._send(404, {"error": "not found"})
            except ValueError as e:  # e.g. a media path outside exports/ and media/
                self._send(400, {"error": str(e)[:200]})
            except Exception as e:
                traceback.print_exc()
                self._send(500, {"error": f"{type(e).__name__}: {e}"[:300]})

        def _static(self, rel):
            f = (STATIC / rel).resolve()
            if not str(f).startswith(str(STATIC.resolve())) or not f.is_file():
                return self._send(404, {"error": "not found"})
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            extra = {"Service-Worker-Allowed": "/"} if f.name == "sw.js" else None
            self._send(200, f.read_bytes(), ctype, extra)

        def _media(self, f):
            """Local preview with byte ranges (the video element seeks with them). Files come only from
            publish.resolve_video, which allows exports/ and media/ only."""
            size = f.stat().st_size
            rng = self.headers.get("Range", "")
            start, end = 0, size - 1
            if rng.startswith("bytes="):
                a, _, b = rng[6:].split(",")[0].partition("-")
                start = int(a) if a else max(0, size - int(b))
                end = min(int(b), size - 1) if a and b else end
            length = end - start + 1
            self.send_response(206 if rng else 200)
            self.send_header("Content-Type", mimetypes.guess_type(f.name)[0] or "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(length))
            if rng:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            with open(f, "rb") as fh:
                fh.seek(start)
                left = length
                try:
                    while left > 0:
                        b = fh.read(min(1 << 20, left))
                        if not b:
                            break
                        self.wfile.write(b)
                        left -= len(b)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        def do_POST(self):
            if not self._guard(True):
                return
            path = urllib.parse.urlparse(self.path).path
            n = int(self.headers.get("Content-Length") or 0)
            if n > 20_000_000:
                return self._send(413, {"error": "too large"})
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._send(400, {"error": "bad JSON"})
            s = app.store
            try:
                if path == "/api/sync":
                    if body.get("wait"):
                        return self._send(200, {"results": sync.run(s, only=body.get("only"))})
                    sync.run_in_background(only=body.get("only"))
                    return self._send(202, {"started": True})
                if path == "/api/experiments":
                    return self._send(200, {"experiment_id": s.save_experiment(body)})
                if path == "/api/concepts":
                    if "tags" in body:
                        body["tags"] = analytics.clean_tags(body["tags"])
                    return self._send(200, {"concept_id": s.save_concept(body)})
                if path == "/api/concept-tags":  # tags only, so the rest of the concept is untouched
                    c = s.q("SELECT * FROM concepts WHERE concept_id=?", (body["concept_id"],))
                    if not c:
                        raise ValueError("unknown concept")
                    return self._send(200, {"concept_id": s.save_concept({**c[0], "tags": analytics.clean_tags(body.get("tags") or {})})})
                if path == "/api/finding":  # learning loop: a comparison group -> a draft knowledge-bank entry
                    res = analytics.compare(s, body)
                    e = analytics.finding_draft(res, body["group"], body.get("statement", ""), body.get("link_to", ""), body.get("link_type", "supports"))
                    return self._send(200, analytics.save_finding(e) if body.get("save") else e)
                if path == "/api/assets":
                    return self._send(200, {"asset_id": s.save_asset(body)})
                if path == "/api/media/delete":  # owner's Delete on the Content page (Recycle Bin, drafts only)
                    return self._send(200, analytics.delete_video(s, body.get("path", "")))
                if path == "/api/uploads":
                    return self._send(200, {"upload_id": s.save_upload(body)})
                if path == "/api/accounts":
                    s.save_account(body)
                    return self._send(200, {"ok": True})
                if path == "/api/import":
                    return self._send(200, imports.run(s, body.get("text", ""), body.get("file_name", "upload.csv"),
                                                       bool(body.get("skip_bad")), bool(body.get("dry_run"))))
                if path == "/api/export":
                    return self._send(200, reports.build(s, body.get("detail", "overview"), body.get("share", True), body.get("filters")))
                if path == "/api/open-folder":
                    target = (ROOT / body.get("folder", "")).resolve()
                    allowed = [(ROOT / "exports" / "share" / "dashboard").resolve(), (DATA / "exports").resolve(), publish.PACKAGES.resolve()]
                    if any(str(target).startswith(str(a)) for a in allowed) and target.is_dir():
                        os.startfile(target)
                        return self._send(200, {"ok": True})
                    return self._send(400, {"error": "not an export folder"})
                if path == "/api/credentials":
                    name = body.get("name", "")
                    acct = body.get("account_id", "")
                    if name == "INSTAGRAM_TOKEN":
                        if not s.account(acct):
                            raise ValueError("unknown account")
                        import time
                        vault.put(f"token_instagram_{acct}", {"access_token": body["value"].strip(), "refreshed_at": 0,
                                                             "expires_at": time.time() + 5184000})
                    elif name in CRED_NAMES:
                        vault.put(name, body["value"].strip())
                    else:
                        raise ValueError("unknown credential name")
                    return self._send(200, {"ok": True})
                if path == "/api/oauth/start":
                    return self._send(200, {"url": oauth.start(body["provider"], body["account_id"], body.get("purpose", "analytics"))})
                if path == "/api/publish/jobs":
                    ids = [publish.create(s, body["asset_id"], a, body["video"], body.get("routes", {}).get(a),
                                          None, body.get("experiment_id", ""), body.get("variant_id", ""))
                           for a in body.get("account_ids", [])]
                    if not ids:
                        raise ValueError("choose at least one account")
                    return self._send(200, {"job_ids": ids})
                if path == "/api/publish/update":
                    publish.update(s, body["job_id"], body.get("fields"), body.get("route"))
                    return self._send(200, views.publish_job(s, body["job_id"]))
                if path == "/api/publish/approve":
                    publish.approve(s, body["job_id"], body.get("confirm", ""), bool(body.get("consent")), bool(body.get("reveal_ok")))
                    return self._send(200, {"ok": True})
                if path == "/api/publish/retry":
                    j = publish.job(s, body["job_id"])
                    if not j or j["state"] != "failed" or not j["approval"]:
                        raise ValueError("only a failed, approved job can be retried")
                    publish.start(s, j["job_id"])
                    return self._send(200, {"ok": True})
                if path == "/api/publish/package":
                    return self._send(200, publish.package(s, body["job_id"]))
                if path == "/api/publish/mark-posted":
                    publish.mark_posted(s, body["job_id"], body.get("url", ""))
                    return self._send(200, {"ok": True})
                if path == "/api/publish/delete":
                    publish.delete(s, body["job_id"])
                    return self._send(200, {"ok": True})
                if path == "/api/disconnect":
                    con, acct = body.get("connector"), body.get("account_id")
                    if con not in CONNECTORS:
                        raise ValueError("unknown connector")
                    key = {"youtube_analytics": f"oauth_youtube_{acct}", "tiktok": f"oauth_tiktok_{acct}",
                           "instagram": f"token_instagram_{acct}"}.get(con)
                    if key:
                        vault.delete(key)
                    removed = s.forget_source(con, acct) if body.get("forget_data") else 0
                    return self._send(200, {"ok": True, "rows_removed": removed})
                if path == "/api/hosting/cleanup":
                    from . import hosting
                    return self._send(200, {"deleted": hosting.cleanup(s, publish._transport())})
                if path == "/api/prefs":
                    for k in ("auto_refresh", "theme"):
                        if k in body:
                            s.set_pref(k, body[k])
                    return self._send(200, {"ok": True})
                if path == "/api/shutdown":
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return self._send(200, {"ok": True})
                self._send(404, {"error": "not found"})
            except (ValueError, KeyError) as e:
                self._send(400, {"error": str(e)})
            except Exception as e:
                traceback.print_exc()
                self._send(500, {"error": f"{type(e).__name__}: {e}"[:300]})

    return H


class ExclusiveServer(ThreadingHTTPServer):
    """HTTPServer sets SO_REUSEADDR, which on Windows lets two servers share one port (requests then go to
    either). Exclusive binding makes a taken port an error instead of a silent hijack in either direction."""
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        import socket
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def serve(port=None, open_browser=False):
    port = port or int(os.environ.get("SLUGSHOT_DASH_PORT") or settings()["port"])
    app = App(port)
    try:
        httpd = ExclusiveServer(("127.0.0.1", port), make_handler(app))
    except OSError:
        raise SystemExit(f"Port {port} is already in use by another program. Close it, or change 'port' in "
                         "config/dashboard/settings.json (then update the OAuth redirect URIs).")
    info = DATA / ("server_fixture.json" if is_fixture_db() else "server.json")
    info.parent.mkdir(parents=True, exist_ok=True)
    info.write_text(json.dumps({"port": port, "pid": os.getpid(), "token": app.token}), encoding="utf-8")
    if not is_fixture_db():
        threading.Thread(target=sync.auto_refresh_loop, args=(app.stop,), daemon=True).start()
    print(f"Slugshot dashboard on http://127.0.0.1:{port}/ (loopback only)")
    try:
        httpd.serve_forever()
    finally:
        app.stop.set()
        info.unlink(missing_ok=True)
