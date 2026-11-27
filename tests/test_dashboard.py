"""Offline tests for the dashboard (fixtures only, no network). Run: .venv\\Scripts\\python -m unittest tests.test_dashboard"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="ssdash_"))
os.environ["SLUGSHOT_DASH_VAULT"] = str(TMP / "vault")
os.environ["SLUGSHOT_DASH_FIXTURE"] = "1"
sys.path.insert(0, str(ROOT))

from dashboard import connectors as C  # noqa: E402
from dashboard import imports, reports, sync, vault, views  # noqa: E402
from dashboard.store import Store  # noqa: E402

FX = ROOT / "tests" / "fixtures" / "dashboard"
NOSLEEP = lambda _s: None  # noqa: E731


def fresh(name):
    p = TMP / f"{name}.db"
    for f in TMP.glob(f"{name}.db*"):
        f.unlink()
    os.environ["SLUGSHOT_DASH_DB"] = str(p)
    s = Store(p)
    s.x("UPDATE accounts SET external_id='9990001' WHERE account_id='rbx-slugshot'")
    return s


def obs(**kw):
    base = {"platform": "youtube", "account_id": "yt-en", "entity_type": "account", "entity_id": "yt-en", "metric": "views",
            "value": 1.0, "period_type": "day", "period_start": "2026-11-20", "period_end": "2026-11-20",
            "observed_at_utc": "2026-11-21T00:00:00+00:00", "source": "test"}
    base.update(kw)
    return base


class StoreSemantics(unittest.TestCase):
    def test_day_rows_deduplicate_lifetime_rows_keep_history(self):
        s = fresh("store1")
        s.put_obs([obs(value=10)])
        s.put_obs([obs(value=12, observed_at_utc="2026-11-22T00:00:00+00:00")])  # late correction replaces
        self.assertEqual([r["value"] for r in s.q("SELECT value FROM observations WHERE period_type='day'")], [12])
        for t, v in (("2026-11-21T00:00:00+00:00", 100), ("2026-11-22T00:00:00+00:00", 150)):
            s.put_obs([obs(entity_type="upload", entity_id="UPL-youtube-x", period_type="lifetime", period_start="", value=v, observed_at_utc=t)])
        self.assertEqual(len(s.q("SELECT 1 FROM observations WHERE period_type='lifetime'")), 2)

    def test_missing_unavailable_and_zero_are_distinct(self):
        s = fresh("store2")
        s.put_obs([obs(metric="likes", value=0), obs(metric="shares", value=None, status="unavailable")])
        rows = {r["metric"]: r for r in s.q("SELECT metric, value, status FROM observations")}
        self.assertEqual((rows["likes"]["value"], rows["likes"]["status"]), (0, "value"))
        self.assertEqual((rows["shares"]["value"], rows["shares"]["status"]), (None, "unavailable"))
        self.assertNotIn("comments", rows)  # missing = no row
        self.assertEqual(views.day_sum(s, [s.account("yt-en")], "comments", "2026-11-01", "2026-11-30"), None)
        self.assertEqual(views.day_sum(s, [s.account("yt-en")], "likes", "2026-11-01", "2026-11-30"), 0)

    def test_seeded_experiment_has_no_results(self):
        s = fresh("store3")
        e = s.experiments()
        self.assertEqual(e[0]["experiment_id"], "EXP-20261124-OPENER")
        self.assertEqual((e[0]["results"], e[0]["decision"], e[0]["status"]), ("", "", "proposed"))
        self.assertEqual([v["role"] for v in e[0]["variants"]], ["control", "treatment"])

    def test_identifiers_validated(self):
        s = fresh("store4")
        with self.assertRaises(ValueError):
            s.save_account({"account_id": "Bad ID", "platform": "youtube"})
        with self.assertRaises(ValueError):
            s.save_experiment({"experiment_id": "nope", "title": "x"})
        cid = s.save_concept({"title": "Floppy underdog"})
        self.assertEqual(cid, "CON-FLOPPY-UNDERDOG")
        self.assertEqual(s.save_asset({"concept_id": cid, "language": "es"}), "CON-FLOPPY-UNDERDOG-ES-V01")


class Connectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = fresh("sync")
        cls.results = {(r["connector"], r["account_id"]): r for r in sync.run(cls.s, fixture=True, sleep=NOSLEEP)}

    def test_failures_are_isolated(self):
        r = self.results
        self.assertEqual(r[("youtube_analytics", "yt-es")]["status"], "failed")  # no ES fixture
        self.assertEqual(r[("youtube_analytics", "yt-en")]["status"], "ok")
        self.assertEqual(r[("tiktok", "tt-es")]["status"], "ok")
        self.assertEqual(r[("roblox_analytics", "rbx-slugshot")]["status"], "partial")  # D30 query refused, rest stored
        self.assertGreater(r[("roblox_analytics", "rbx-slugshot")]["rows"], 100)

    def test_tiktok_asks_only_for_fields_its_scopes_unlock(self):
        # Live 2026-11-25: asking for `username` without user.info.profile failed the whole user/info call (401).
        tt = C.CONNECTORS["tiktok"]
        granted = {"user.info.basic", "user.info.stats", "video.list", "video.upload", "video.publish"}
        fields = ",".join(f for sc, f in tt.FIELDS.items() if sc in granted).split(",")
        self.assertNotIn("username", fields)
        self.assertIn("follower_count", fields)
        a = self.s.account("tt-es")
        self.assertEqual((a["handle"], a["external_id"]), ("es.roni_jt", "FIXTURE-open-id-es"))  # handle from creator_info

    def test_buffer_adds_only_what_native_apis_lack(self):
        s = self.s
        self.assertEqual(self.results[("buffer", "tt-en")]["status"], "ok")
        self.assertEqual(self.results[("buffer", "ig-en")]["status"], "ok")
        up = s.q("SELECT upload_id FROM uploads WHERE platform='tiktok' AND platform_video_id='7400000000000000001'")
        self.assertEqual(len(up), 1)                                   # Buffer joins the native upload, no duplicate
        by_src = {}
        for r in s.q("SELECT metric, source, value FROM observations WHERE entity_id=?", (up[0]["upload_id"],)):
            by_src.setdefault(r["source"], set()).add(r["metric"])
        self.assertEqual(by_src["buffer"], {"reach", "watch_time_minutes", "avg_view_duration_s"})  # views/shares stay native
        self.assertFalse(s.q("SELECT 1 FROM uploads WHERE platform_video_id='7400000000000000009'"))  # metrics not computed yet
        ig = {r["metric"]: r["value"] for r in s.q("""SELECT o.metric, o.value FROM observations o JOIN uploads u ON u.upload_id=o.entity_id
                                                      WHERE u.platform_video_id='FXreel001' AND o.source='buffer'""")}
        self.assertEqual(ig, {"views": 320, "reach": 0, "saves": 7, "likes": 21})  # a computed 0 stays 0; engagementRate not stored
        self.assertEqual(s.pref("buffer_channel_tt-es")["id"], "ch-tt-es")  # matched by platform and handle

    def test_buffer_refuses_a_channel_with_another_handle(self):
        s = fresh("bufid")
        s.x("UPDATE accounts SET handle='someone_else' WHERE account_id='tt-en'")
        r = {(x["connector"], x["account_id"]): x for x in sync.run(s, only=["buffer"], fixture=True, sleep=NOSLEEP)}
        self.assertEqual(r[("buffer", "tt-en")]["status"], "needs_auth")
        self.assertFalse(s.q("SELECT 1 FROM observations WHERE source='buffer' AND account_id='tt-en'"))

    def test_roblox_async_operation_polled(self):
        n = self.s.q("SELECT COUNT(*) n FROM observations WHERE metric='dau' AND breakdown_dim=''")[0]["n"]
        self.assertGreater(n, 20)

    def test_new_users_from_isnewuser_breakdown(self):
        new = self.s.q("SELECT COUNT(*) n FROM observations WHERE metric='new_users' AND source='roblox_analytics'")[0]["n"]
        self.assertGreater(new, 20)

    def test_instagram_rejected_metric_marked_unavailable(self):
        rows = self.s.q("SELECT metric, status FROM observations WHERE entity_id='UPL-instagram-IGFX3'")
        st = {r["metric"]: r["status"] for r in rows}
        self.assertEqual(st["views"], "value")
        self.assertEqual(st["shares"], "unavailable")
        self.assertFalse(self.s.q("SELECT 1 FROM uploads WHERE platform_video_id='IGFX4'"))  # photos ignored

    def test_retry_on_429_then_success(self):
        calls = []

        def fake(url, params=None, headers=None, data=None, timeout=30, user_agent=None):
            calls.append(1)
            if len(calls) < 3:
                raise C.rc.HttpError(429, "slow down")
            return b'{"ok": true}', {}
        orig = C.rc.http
        C.rc.http = fake
        try:
            ctx = C.Ctx(sleep=NOSLEEP)
            self.assertEqual(ctx.call("k", "https://example.invalid"), {"ok": True})
            self.assertEqual((ctx.ok, ctx.failed), (1, 2))
            calls.clear()
            C.rc.http = lambda *a, **k: (_ for _ in ()).throw(C.rc.HttpError(401, "revoked"))
            with self.assertRaises(C.rc.HttpError):
                C.Ctx(sleep=NOSLEEP).call("k", "https://example.invalid")  # auth errors are not retried
        finally:
            C.rc.http = orig

    def test_incremental_window_rereads_three_days(self):
        acct = self.s.account("rbx-slugshot")
        start = C.backfill_start(self.s, "roblox_analytics", acct, 90)
        last = self.s.q("SELECT MAX(period_start) d FROM observations WHERE source='roblox_analytics'")[0]["d"]
        self.assertEqual(start, date.fromisoformat(last) - timedelta(days=3))


class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = fresh("rules")
        sync.run(cls.s, fixture=True, sleep=NOSLEEP)

    def test_platforms_never_summed(self):
        o = views.overview(self.s, {})
        self.assertEqual({p["platform"] for p in o["platforms"]}, {"youtube", "tiktok", "instagram"})
        for p in o["platforms"]:
            self.assertIn("views", p)
        self.assertNotIn("views_total", o)
        tt = next(p for p in o["platforms"] if p["platform"] == "tiktok")
        self.assertEqual(tt["views_basis"], "lifetime")  # TikTok has no daily views; labelled, not mixed

    def test_daily_players_averaged_not_summed(self):
        g = views.game(self.s, {})
        dau = next(m for st in g["stages"] for m in st["metrics"] if m["metric"] == "dau")["values"][0]
        self.assertEqual(dau["basis"], "avg/day")
        daily = [r["v"] for r in views.series(self.s, [self.s.account("rbx-slugshot")], "dau", *views.window({}))]
        self.assertAlmostEqual(dau["value"], sum(daily) / len(daily))

    def test_views_sort_only_within_one_platform(self):
        mixed = views.content(self.s, {"sort": "views"})
        self.assertEqual(mixed["sort_applied"], "published")
        one = views.content(self.s, {"sort": "views", "platform": "youtube"})
        self.assertEqual(one["sort_applied"], "views")
        v = [u["metrics"]["views"] for u in one["uploads"]]
        self.assertEqual(v, sorted(v, reverse=True))

    def test_language_filter(self):
        es = views.content(self.s, {"language": "es"})["uploads"]
        self.assertTrue(es)
        self.assertTrue(all(u["language"] == "es" for u in es))

    def test_no_conversion_between_stages(self):
        g = views.game(self.s, {})
        ids = {m["metric"] for st in g["stages"] for m in st["metrics"]}
        self.assertFalse(any("conversion" in i or i.endswith("_cvr") and i != "payer_cvr" for i in ids))


class Imports(unittest.TestCase):
    def test_platform_metrics_import_creates_registry(self):
        s = fresh("imp1")
        text = C.fixture_text((FX / "manual_platform_metrics.csv").read_text(encoding="utf-8"))
        r = imports.run(s, text, "m.csv")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["rows_ok"], 2)
        u = s.q("SELECT * FROM uploads WHERE platform='youtube'")[0]
        self.assertEqual(u["account_id"], "yt-es")
        self.assertEqual(u["asset_id"], "CON-ONESLUGFORLIFE-ES-V01")
        rounded = s.q("SELECT value, note FROM observations WHERE metric='views' AND platform='tiktok'")[0]
        self.assertEqual((rounded["value"], rounded["note"]), (22400, "rounded as displayed"))
        self.assertEqual(s.q("SELECT value FROM observations WHERE metric='avg_view_pct'")[0]["value"], 74.2)
        self.assertFalse(imports.run(s, text, "m.csv")["ok"])  # same file twice refused

    def test_bad_rows_refused_with_row_numbers(self):
        s = fresh("imp2")
        bad = ("date_start,date_end,platform,account_id,entity_type,entity_id,metric,value,breakdown_dim,breakdown_value,note\n"
               "2026-11-20,2026-11-20,myspace,,account,,views,5,,,\n"
               "2026-11-20,2026-11-20,tiktok,tt-en,account,,vibes,5,,,\n"
               "20/11/2026,,tiktok,tt-en,account,,views,5,,,\n"
               "2026-11-20,2026-11-20,tiktok,tt-en,account,,views,lots,,,\n"
               "2026-11-20,2026-11-20,tiktok,tt-en,account,,views,12,,,\n")
        r = imports.run(s, bad, "bad.csv")
        self.assertFalse(r["ok"])
        joined = "\n".join(r["errors"])
        for frag in ("row 2", "row 3", "row 4", "row 5", "myspace", "vibes", "YYYY-MM-DD", "not a number"):
            self.assertIn(frag, joined)
        self.assertFalse(s.q("SELECT 1 FROM observations"))
        r = imports.run(s, bad, "bad.csv", skip_bad=True)
        self.assertEqual((r["rows_ok"], r["rows_rejected"]), (1, 4))

    def test_future_observation_refused(self):
        s = fresh("imp3")
        hdr = (FX / "manual_platform_metrics.csv").read_text(encoding="utf-8").splitlines()[0]
        row = "X,,PVP,,,youtube,https://youtu.be/AAAAAAAAAAA,,2099-01-01T00:00:00Z,5,,,,,,,,,,,en,yt-en"
        r = imports.run(s, hdr + "\n" + row + "\n", "f.csv")
        self.assertFalse(r["ok"])
        self.assertIn("future", r["errors"][0])


class Exports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = fresh("exp")
        sync.run(cls.s, fixture=True, sleep=NOSLEEP)
        imports.run(cls.s, C.fixture_text((FX / "manual_platform_metrics.csv").read_text(encoding="utf-8")), "m.csv")
        reports.SHARE_DIR = TMP / "share"
        reports.LOCAL_DIR = TMP / "local"

    def test_snapshot_files_readable_and_safe(self):
        r = reports.build(self.s, "detailed", True)
        folder = reports.ROOT / r["folder"] if not Path(r["folder"]).is_absolute() else Path(r["folder"])
        names = set(r["files"])
        for must in ("README.md", "metric_definitions.csv", "sources.csv", "experiments.json", "content_youtube.csv",
                     "content_tiktok.csv", "observations_roblox.csv", "research_findings.csv"):
            self.assertIn(must, names)
        self.assertFalse(any(n.endswith(".zip") for n in names))
        readme = (folder / "README.md").read_text(encoding="utf-8")
        self.assertIn("FIXTURE DATA", readme)
        self.assertIn("never added together", readme)
        content = (folder / "content_tiktok.csv").read_text(encoding="utf-8")
        self.assertNotIn(".mp4", content)  # local media paths stripped in safe mode
        self.assertFalse(any("youtube" in n and "tiktok" in n for n in names))  # providers in separate files

    def test_export_aborts_on_credential_leak(self):
        vault.put("ROBLOX_ANALYTICS_API_KEY", "LEAKTEST-1234567890abcdef")
        self.s.x("UPDATE experiments SET next_action='LEAKTEST-1234567890abcdef'")
        try:
            with self.assertRaises(RuntimeError):
                reports.build(self.s, "overview", True)
        finally:
            vault.delete("ROBLOX_ANALYTICS_API_KEY")
            self.s.x("UPDATE experiments SET next_action=''")

    def test_sharing_rule_excludes_provider(self):
        orig = reports.settings

        def no_tiktok():
            st = orig()
            st["sharing"]["tiktok"] = False
            st["sharing"]["manual"] = False
            return st
        reports.settings = no_tiktok
        try:
            r = reports.build(self.s, "detailed", True)
        finally:
            reports.settings = orig
        self.assertNotIn("observations_tiktok.csv", r["files"])
        self.assertTrue(any("tiktok" in x for x in r["excluded"]))


class Vault(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "credential encryption uses Windows DPAPI")
    def test_dpapi_round_trip_and_ciphertext(self):
        vault.put("UNITTEST_SECRET", {"access_token": "plaintext-token-value"})
        raw = (Path(os.environ["SLUGSHOT_DASH_VAULT"]) / "UNITTEST_SECRET.dpapi").read_bytes()
        self.assertNotIn(b"plaintext-token-value", raw)
        self.assertEqual(vault.get("UNITTEST_SECRET")["access_token"], "plaintext-token-value")
        vault.delete("UNITTEST_SECRET")
        self.assertIsNone(vault.get("UNITTEST_SECRET"))
        with self.assertRaises(ValueError):
            vault.put("../escape", "x")


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer  # noqa: F401
        from dashboard import server
        fresh("srv")
        cls.port = 47699
        cls.app = server.App(cls.port)
        cls.httpd = server.ExclusiveServer(("127.0.0.1", cls.port), server.make_handler(cls.app))
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def req(self, path, method="GET", body=None, headers=None):
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=json.dumps(body).encode() if body is not None else None,
                                   method=method, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_bad_host_refused(self):
        self.assertEqual(self.req("/api/health", headers={"Host": "attacker.example"})[0], 403)

    def test_write_needs_token_and_same_origin(self):
        self.assertEqual(self.req("/api/sync", "POST", {})[0], 403)
        self.assertEqual(self.req("/api/prefs", "POST", {"theme": "x"}, {"X-Dash-Token": self.app.token, "Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.req("/api/prefs", "POST", {"theme": "light"}, {"X-Dash-Token": self.app.token})[0], 200)

    @unittest.skipUnless(os.name == "nt", "the credential write endpoint uses Windows DPAPI")
    def test_credentials_write_only(self):
        st, _ = self.req("/api/credentials", "POST", {"name": "TIKTOK_CLIENT_KEY", "value": "SECRETVALUE-abcdef123456"}, {"X-Dash-Token": self.app.token})
        self.assertEqual(st, 200)
        try:
            for path in ("/api/status", "/api/meta", "/api/overview"):
                self.assertNotIn(b"SECRETVALUE", self.req(path)[1])
            self.assertIn(b'"TIKTOK_CLIENT_KEY": true', self.req("/api/status")[1])
            self.assertEqual(self.req("/api/credentials", "POST", {"name": "PATH", "value": "x"}, {"X-Dash-Token": self.app.token})[0], 400)
        finally:
            vault.delete("TIKTOK_CLIENT_KEY")

    def test_token_embedded_in_page(self):
        st, body = self.req("/")
        self.assertEqual(st, 200)
        self.assertIn(self.app.token.encode(), body)

    def test_static_path_traversal_blocked(self):
        self.assertEqual(self.req("/static/../store.py")[0], 404)
        self.assertEqual(self.req("/static/%2e%2e/store.py")[0], 404)

    def test_port_cannot_be_shared(self):
        from dashboard import server
        with self.assertRaises(OSError):
            server.ExclusiveServer(("127.0.0.1", self.port), server.make_handler(self.app))


class RepoBoundaries(unittest.TestCase):
    def test_private_paths_ignored(self):
        for p in ("data/local/dashboard/slugshot.db", "data/local/dashboard/vault/x.dpapi", "exports/share/dashboard/x/README.md",
                  "out/dashboard_demo/demo.db", ".env"):
            r = subprocess.run(["git", "check-ignore", "-q", p], cwd=ROOT)
            self.assertEqual(r.returncode, 0, f"{p} is not git-ignored")

    def test_no_secret_values_in_tracked_dashboard_files(self):
        files = subprocess.run(["git", "ls-files", "--others", "--cached", "--exclude-standard", "dashboard", "config/dashboard",
                                "tests/fixtures/dashboard"], cwd=ROOT, capture_output=True, text=True).stdout.split()
        vals = [v for v in vault.all_secret_values() if len(v) > 12]
        for f in files:
            p = ROOT / f
            if p.suffix in (".png", ".ico", ".woff2"):
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            for v in vals:
                self.assertNotIn(v, text, f"credential value found in {f}")


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
