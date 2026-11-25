"""Offline tests for publishing (fixture transport, no network, nothing posted).
Run: .venv\\Scripts\\python -m unittest tests.test_publish"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="sspub_"))
os.environ.setdefault("SLUGSHOT_DASH_VAULT", str(TMP / "vault"))  # keep another suite's vault when run together
os.environ["SLUGSHOT_DASH_FIXTURE"] = "1"
sys.path.insert(0, str(ROOT))

from dashboard import publish as P  # noqa: E402
from dashboard.store import Store  # noqa: E402

MEDIA = ROOT / "media" / "_test_publish"


def fresh(name):
    p = TMP / f"{name}.db"
    for f in TMP.glob(f"{name}.db*"):
        f.unlink()
    os.environ["SLUGSHOT_DASH_DB"] = str(p)
    s = Store(p)
    s.save_concept({"concept_id": "CON-FX-PUBLISH", "title": "Fixture publish", "hook_text": "Floppy hits for 7. Still trying."})
    s.save_asset({"concept_id": "CON-FX-PUBLISH", "language": "en", "version": "V01"})
    s.save_experiment({"experiment_id": "EXP-FX-PUB", "title": "Fixture experiment", "status": "running",
                       "variants": [{"variant_id": "A", "role": "control", "label": "A"}, {"variant_id": "B", "role": "treatment", "label": "B"}]})
    return s


def video(name, size):
    MEDIA.mkdir(parents=True, exist_ok=True)
    p = MEDIA / name
    with open(p, "wb") as f:
        f.write(os.urandom(min(size, 4096)))
        f.truncate(size)
    return p


def wait(s, jid, t=20):
    end = time.time() + t
    while time.time() < end:
        j = P.job(s, jid)
        if j["state"] not in ("approved", "uploading") and jid not in P._running:
            return j
        time.sleep(0.05)
    raise AssertionError("upload did not finish")


AID = "CON-FX-PUBLISH-EN-V01"


@contextmanager
def publishing(**over):
    """Run with publishing settings overridden (public_posting, reveal_lock, tiktok_app_audited, ...)."""
    orig = P.settings

    def patched():
        st = orig()
        st["publishing"] = {**st.get("publishing", {}), **over}
        return st
    P.settings = patched
    try:
        yield
    finally:
        P.settings = orig


def tearDownModule():
    shutil.rmtree(MEDIA, ignore_errors=True)
    shutil.rmtree(TMP, ignore_errors=True)


class Rules(unittest.TestCase):
    def test_tiktok_chunk_rules(self):
        self.assertEqual(P.tiktok_chunks(3_000_000), (3_000_000, 1))       # under 5 MB: whole file
        self.assertEqual(P.tiktok_chunks(7_000_000), (7_000_000, 1))
        self.assertEqual(P.tiktok_chunks(25_000_000), (10_000_000, 2))     # last chunk carries 15 MB
        self.assertEqual(P.tiktok_chunks(50_000_123), (10_000_000, 5))     # TikTok's worked example

    def test_paths_outside_exports_and_media_are_refused(self):
        with self.assertRaises(ValueError):
            P.resolve_video(ROOT / "config" / "dashboard" / "settings.json")
        with self.assertRaises(ValueError):
            P.resolve_video(ROOT / ".." / "slugshot" / "x.mp4")

    def test_defaults_follow_platform_rules(self):
        s = fresh("defaults")
        v = video("d.mp4", 1000)
        yt = P.job(s, P.create(s, AID, "yt-en", v))
        tt = P.job(s, P.create(s, AID, "tt-en", v, "direct"))
        self.assertEqual(yt["fields"]["privacy"], "private")
        self.assertIsNone(yt["fields"]["made_for_kids"])               # an explicit owner choice
        self.assertEqual(tt["fields"]["privacy"], "")                   # TikTok: no default privacy
        self.assertFalse(any(tt["fields"][k] for k in ("allow_comment", "allow_duet", "allow_stitch", "commercial")))
        self.assertIn("choose whether this video is made for kids (YouTube requires the declaration)", P.check(s, yt)["errors"])

    def test_visibility_and_reveal_lock_are_separate(self):
        s = fresh("lock")
        v = video("l.mp4", 1000)
        yt = P.update(s, P.create(s, AID, "yt-en", v), {"privacy": "public", "made_for_kids": False})
        with publishing(public_posting=False, reveal_lock=True):
            self.assertTrue(any("public posting is off" in e for e in P.check(s, yt)["errors"]))
        with publishing(public_posting=True, reveal_lock=True):
            r = P.check(s, yt)
            self.assertEqual((r["errors"], r["visibility"], r["needs_reveal_ok"]), ([], "visible", True))
            with self.assertRaises(ValueError):                          # public + lock: owner must confirm the video
                P.approve(s, yt["job_id"], "Ronin_JT", reveal_ok=False)
            named = P.update(s, yt["job_id"], {"title": "Playing Slug Shot for 1 hour"})
            self.assertTrue(any("names the game" in e for e in P.check(s, named)["errors"]))
            private = P.update(s, yt["job_id"], {"privacy": "private"})
            r = P.check(s, private)
            self.assertEqual((r["errors"], r["needs_reveal_ok"]), ([], False))  # private: naming it is only a warning
            self.assertTrue(any("names the game" in w for w in r["warnings"]))
        with publishing(public_posting=True, reveal_lock=False):
            r = P.check(s, P.update(s, yt["job_id"], {"privacy": "public"}))
            self.assertEqual((r["errors"], r["needs_reveal_ok"]), ([], False))
        bad = P.update(s, P.create(s, AID, "tt-en", v, "inbox"), {"caption": "Floppy does nothing lol"})
        self.assertTrue(any("game truth" in e for e in P.check(s, bad)["errors"]))

    def test_tiktok_unaudited_app_limits_direct_post(self):
        s = fresh("ttaudit")
        v = video("ta.mp4", 1000)
        creator = P.tiktok_creator_info(s, s.account("tt-en"), P.FixtureTransport())   # a public account
        with publishing(public_posting=True, tiktok_app_audited=False):
            pub = P.update(s, P.create(s, AID, "tt-en", v, "direct"), {"privacy": "PUBLIC_TO_EVERYONE"})
            errs = P.check(s, pub, creator)["errors"]
            self.assertTrue(any("audited" in e and "'Only me'" in e for e in errs))
            self.assertTrue(any("account is public" in e for e in errs))
            inbox = P.check(s, P.job(s, P.create(s, AID, "tt-en", v, "inbox")))
            self.assertEqual((inbox["errors"], inbox["visibility"], inbox["needs_reveal_ok"]), ([], "in_app", True))
        with publishing(public_posting=True, tiktok_app_audited=True):
            self.assertFalse(any("audited" in e for e in P.check(s, pub, creator)["errors"]))

    def test_instagram_follows_the_same_rules(self):
        s = fresh("ig")
        ig = P.job(s, P.create(s, AID, "ig-en", video("ig.mp4", 1000), "api"))
        with publishing(public_posting=True, reveal_lock=True):
            r = P.check(s, ig)
            self.assertTrue(any("public https URL" in e for e in r["errors"]))
            self.assertTrue(r["needs_reveal_ok"])
        with publishing(public_posting=False):
            self.assertTrue(any("public posting is off" in e for e in P.check(s, ig)["errors"]))

    def test_inactive_account_refused(self):
        s = fresh("inactive")
        s.x("UPDATE accounts SET active=0 WHERE account_id='ig-es'")
        with self.assertRaises(ValueError):
            P.create(s, AID, "ig-es", video("i.mp4", 1000))


class Approval(unittest.TestCase):
    def test_approval_needs_exact_handle_and_tiktok_consent(self):
        s = fresh("appr")
        jid = P.create(s, AID, "yt-en", video("a.mp4", 1000))
        P.update(s, jid, {"made_for_kids": False})
        with self.assertRaises(ValueError):
            P.approve(s, jid, "@someone_else")
        tj = P.create(s, AID, "tt-en", video("a2.mp4", 1000), "inbox")
        with self.assertRaises(ValueError):
            P.approve(s, tj, "@.roni_jt", consent=False)
        self.assertEqual(P.job(s, jid)["state"], "draft")

    def test_errors_block_approval(self):
        s = fresh("block")
        jid = P.create(s, AID, "yt-en", video("b.mp4", 1000))            # made_for_kids not chosen
        with self.assertRaises(ValueError):
            P.approve(s, jid, "Ronin_JT")

    def test_change_after_approval_voids_it(self):
        s = fresh("void")
        v = video("v.mp4", 1000)
        jid = P.create(s, AID, "yt-en", v)
        P.update(s, jid, {"made_for_kids": False})
        j = P.job(s, jid)
        fh = P.sha256(v)
        P._set(s, jid, state="approved", approval={"file_sha256": fh, "fingerprint": P.fingerprint(j, fh), "reveal_lock": True})
        with open(v, "ab") as f:
            f.write(b"x")                                               # file changed after approval
        with self.assertRaises(RuntimeError):
            P.run(s, jid, P.FixtureTransport())
        self.assertEqual(P.job(s, jid)["state"], "draft")
        self.assertFalse(P.job(s, jid)["approval"])

    def test_upload_refused_when_token_belongs_to_another_account(self):
        s = fresh("ident")
        for acct, route, other in (("yt-en", "api", {"youtube": "@roni_jtes", "tiktok": ".roni_jt"}),
                                   ("tt-en", "inbox", {"youtube": "@ronin_jt", "tiktok": "es.roni_jt"})):
            v = video(f"id-{acct}.mp4", 1000)
            jid = P.create(s, AID, acct, v, route)
            if acct == "yt-en":
                P.update(s, jid, {"made_for_kids": False})
            j = P.job(s, jid)
            P._set(s, jid, state="approved", approval={"file_sha256": P.sha256(v), "fingerprint": P.fingerprint(j, P.sha256(v)),
                                                        "reveal_lock": P.cfg()["reveal_lock"]})
            tx = P.FixtureTransport(identity=other)
            with self.assertRaises(RuntimeError) as e:
                P.run(s, jid, tx)
            self.assertIn("reconnect", str(e.exception))
            self.assertFalse([c for c in tx.calls if c[0] == "PUT" or "init" in c[1] or "upload/youtube" in c[1]])  # nothing sent

    def test_public_posting_turned_off_after_approval_blocks_run(self):
        s = fresh("ppoff")
        v = video("pp.mp4", 1000)
        jid = P.create(s, AID, "yt-en", v)
        P.update(s, jid, {"made_for_kids": False, "privacy": "public"})
        j = P.job(s, jid)
        P._set(s, jid, state="approved", approval={"file_sha256": P.sha256(v), "fingerprint": P.fingerprint(j, P.sha256(v)),
                                                    "reveal_lock": True})
        with publishing(public_posting=False, reveal_lock=True):
            with self.assertRaises(RuntimeError):
                P.run(s, jid, P.FixtureTransport())

    def test_edit_clears_approval(self):
        s = fresh("edit")
        jid = P.create(s, AID, "yt-en", video("e.mp4", 1000))
        P._set(s, jid, state="failed", approval={"at": "x"})
        P.update(s, jid, {"title": "New"})
        self.assertFalse(P.job(s, jid)["approval"])


class Uploads(unittest.TestCase):
    def test_youtube_resumable_upload_links_version_and_experiment(self):
        s = fresh("yt")
        v = video("yt.mp4", 20 * 1024 * 1024 + 5)
        jid = P.create(s, AID, "yt-en", v, experiment_id="EXP-FX-PUB", variant_id="B")
        P.update(s, jid, {"made_for_kids": False, "title": "Fixture upload"})
        tx = P.FixtureTransport()
        orig = P._transport
        P._transport = lambda: tx  # the background run records into this fixture
        try:
            P.approve(s, jid, "@ronin_jt")                             # handle match ignores case and @
            j = wait(s, jid)
        finally:
            P._transport = orig
        self.assertEqual(j["state"], "done", j["log"])
        self.assertEqual(j["result"]["platform_video_id"], "FXyt0000001")
        up = s.q("SELECT * FROM uploads WHERE upload_id=?", (j["upload_id"],))[0]
        self.assertEqual((up["asset_id"], up["account_id"], up["source"]), (AID, "yt-en", "publish:api"))
        variant = s.q("SELECT asset_ids FROM variants WHERE experiment_id='EXP-FX-PUB' AND variant_id='B'")[0]
        self.assertIn(AID, json.loads(variant["asset_ids"]))
        puts = [c for c in tx.calls if c[0] == "PUT" and c[3]]
        ranges = [c[2]["Content-Range"] for c in puts]
        self.assertEqual(len(puts), 3)
        self.assertTrue(ranges[0].startswith("bytes 0-8388607/"))      # 8 MiB chunks, multiples of 256 KiB
        self.assertTrue(ranges[-1].endswith(f"-{v.stat().st_size - 1}/{v.stat().st_size}"))
        init = next(c for c in tx.calls if c[0] == "POST")
        self.assertEqual(init[2]["status"]["privacyStatus"], "private")
        self.assertFalse(any("Bearer" in str(x) for x in j["log"]))

    def test_tiktok_inbox_then_owner_marks_posted(self):
        s = fresh("tt")
        v = video("tt.mp4", 25_000_000)
        jid = P.create(s, AID, "tt-en", v, "inbox")
        tx = P.FixtureTransport()
        P._set(s, jid, state="approved", approval={"file_sha256": P.sha256(v), "fingerprint": P.fingerprint(P.job(s, jid), P.sha256(v)), "reveal_lock": True})
        j = P.run(s, jid, tx)
        self.assertEqual(j["state"], "sent_to_inbox")
        init = next(c for c in tx.calls if c[1].endswith("/inbox/video/init/"))
        self.assertEqual(init[2]["source_info"], {"source": "FILE_UPLOAD", "video_size": 25_000_000, "chunk_size": 10_000_000, "total_chunk_count": 2})
        ranges = [c[2]["Content-Range"] for c in tx.calls if c[0] == "PUT"]
        self.assertEqual(ranges, ["bytes 0-9999999/25000000", "bytes 10000000-24999999/25000000"])
        self.assertFalse(s.q("SELECT 1 FROM uploads"))                  # nothing posted yet
        j = P.mark_posted(s, jid, "https://www.tiktok.com/@.roni_jt/video/7300000000000000001")
        self.assertEqual(j["state"], "done")
        self.assertEqual(s.q("SELECT platform_video_id, asset_id FROM uploads")[0], {"platform_video_id": "7300000000000000001", "asset_id": AID})

    def test_tiktok_direct_post_sends_owner_choices(self):
        s = fresh("ttd")
        v = video("ttd.mp4", 3_000_000)
        jid = P.create(s, AID, "tt-en", v, "direct")
        P.update(s, jid, {"privacy": "SELF_ONLY", "allow_comment": True, "is_aigc": True})
        tx = P.FixtureTransport(inbox_status="PUBLISH_COMPLETE")
        P._set(s, jid, state="approved", approval={"file_sha256": P.sha256(v), "fingerprint": P.fingerprint(P.job(s, jid), P.sha256(v)), "reveal_lock": True})
        j = P.run(s, jid, tx)
        body = next(c for c in tx.calls if c[1].endswith("/publish/video/init/"))[2]
        self.assertEqual(body["post_info"]["privacy_level"], "SELF_ONLY")
        self.assertEqual((body["post_info"]["disable_comment"], body["post_info"]["disable_duet"], body["post_info"]["is_aigc"]), (False, True, True))
        self.assertEqual(j["state"], "done")

    def test_buffer_route_posts_with_owner_approval(self):
        s = fresh("buf")
        v = video("buf.mp4", 1000)
        jid = P.create(s, AID, "tt-en", v)                              # Buffer is TikTok's first route
        self.assertEqual(P.job(s, jid)["route"], "buffer")
        self.assertTrue(any("Cloudinary" in w for w in P.check(s, P.job(s, jid))["warnings"]))  # hosted at approval
        P.update(s, jid, {"video_url": "https://example.invalid/clip.mp4", "is_aigc": True})          # or the owner's own link
        with publishing(public_posting=True, reveal_lock=True):
            r = P.check(s, P.job(s, jid))
            self.assertEqual((r["errors"], r["visibility"], r["needs_reveal_ok"]), ([], "visible", True))
            j = P.job(s, jid)
            P._set(s, jid, state="approved", approval={"file_sha256": P.sha256(v), "fingerprint": P.fingerprint(j, P.sha256(v)), "reveal_lock": True})
            tx = P.FixtureTransport()
            j = P.run(s, jid, tx)
        self.assertEqual((j["state"], j["result"]["platform_video_id"]), ("done", "7400000000000000001"))
        inp = next(c for c in tx.calls if "createPost" in str(c[2]))[2]["variables"]["i"]
        self.assertEqual((inp["channelId"], inp["mode"], inp["metadata"]), ("ch-tt-en", "shareNow", {"tiktok": {"isAiGenerated": True}}))
        self.assertEqual(inp["assets"], [{"video": {"url": "https://example.invalid/clip.mp4", "metadata": {"thumbnailOffset": 1000}}}])
        self.assertFalse(any("Bearer" in str(x) for x in j["log"]))

    def test_buffer_draft_and_wrong_channel(self):
        s = fresh("bufd")
        v = video("bufd.mp4", 1000)
        jid = P.create(s, AID, "ig-en", v, fields={"video_url": "https://example.invalid/r.mp4", "buffer_draft": True})
        with publishing(public_posting=True, reveal_lock=True):
            self.assertEqual(P.check(s, P.job(s, jid))["visibility"], "in_app")
            j = P.job(s, jid)
            P._set(s, jid, state="approved", approval={"file_sha256": P.sha256(v), "fingerprint": P.fingerprint(j, P.sha256(v)), "reveal_lock": True})
            tx = P.FixtureTransport()
            self.assertEqual(P.run(s, jid, tx)["state"], "in_buffer_drafts")
            inp = next(c for c in tx.calls if "createPost" in str(c[2]))[2]["variables"]["i"]
            self.assertEqual((inp["saveToDraft"], inp["metadata"]["instagram"]["type"]), (True, "reel"))
            tj = P.create(s, AID, "tt-en", v, fields={"video_url": "https://example.invalid/c.mp4"})
            j = P.job(s, tj)
            P._set(s, tj, state="approved", approval={"file_sha256": P.sha256(v), "fingerprint": P.fingerprint(j, P.sha256(v)), "reveal_lock": True})
            tx = P.FixtureTransport(identity={"youtube": "@ronin_jt", "tiktok": "es.roni_jt"})  # Buffer only has the ES channel
            with self.assertRaises(RuntimeError):
                P.run(s, tj, tx)
            self.assertFalse([c for c in tx.calls if "createPost" in str(c[2])])

    def approved(self, s, jid, v):
        j = P.job(s, jid)
        P._set(s, jid, state="approved", approval={"file_sha256": P.sha256(v), "fingerprint": P.fingerprint(j, P.sha256(v)),
                                                    "reveal_lock": P.cfg()["reveal_lock"]})

    def test_hosted_once_shared_then_deleted_after_last_post(self):
        s = fresh("host")
        v = video("host.mp4", 3000)
        a = P.create(s, AID, "tt-en", v)
        b = P.create(s, AID, "ig-en", v)
        self.approved(s, a, v)
        self.approved(s, b, v)
        tx = P.FixtureTransport()
        ja = P.run(s, a, tx)
        self.assertEqual(ja["state"], "done")
        url = next(c for c in tx.calls if "createPost" in str(c[2]))[2]["variables"]["i"]["assets"][0]["video"]["url"]
        self.assertTrue(url.startswith("https://res.cloudinary.com/fixture/video/authenticated/s--"))
        self.assertEqual(s.q("SELECT state FROM hosted_assets")[0]["state"], "hosted")  # Instagram still needs it
        P.run(s, b, tx)
        self.assertEqual(tx.hosted_uploads, 1)                              # one upload for both accounts
        self.assertEqual(s.q("SELECT state FROM hosted_assets")[0]["state"], "deleted")
        self.assertEqual(len(tx.destroyed), 1)
        for jid in (a, b):                                                  # the signed link is never logged or stored
            j = P.job(s, jid)
            self.assertNotIn("s--", json.dumps(j["log"]) + json.dumps(j["result"]))

    def test_no_duplicate_post_and_retry_follows_existing_buffer_post(self):
        s = fresh("dup")
        v = video("dup.mp4", 2000)
        a = P.create(s, AID, "tt-en", v)
        self.approved(s, a, v)
        b = P.create(s, AID, "tt-en", v, "inbox")
        with self.assertRaises(ValueError) as e:                             # same file, same account
            P.approve(s, b, "@.roni_jt", consent=True, reveal_ok=True)
        self.assertIn(a, str(e.exception))
        P._set(s, a, state="failed", result={"buffer_post_id": "bufpost-1"})   # crashed after Buffer accepted the post
        tx = P.FixtureTransport()
        self.assertEqual(P.run(s, a, tx)["state"], "done")
        self.assertFalse([c for c in tx.calls if "createPost" in str(c[2])])
        self.assertEqual(getattr(tx, "hosted_uploads", 0), 0)

    def test_instagram_shows_ready_through_buffer(self):
        s = fresh("acctview")
        orig = P.credential
        P.credential = lambda st, acct, route=None: ("ready", "") if route == "buffer" else ("not connected", "no token")
        try:
            ig = next(a for a in P.accounts_view(s) if a["account_id"] == "ig-en")
        finally:
            P.credential = orig
        self.assertEqual((ig["credential"], ig["credential_note"], ig["buffer"]), ("ready", "via Buffer", True))

    def test_free_tier_guard_and_abandoned_cleanup(self):
        from dashboard import hosting as H
        s = fresh("guard")
        v = video("g.mp4", 2000)
        a = P.create(s, AID, "tt-en", v)
        self.approved(s, a, v)
        orig = P._transport
        P._transport = lambda: P.FixtureTransport(credit_pct=75)           # over our 60% credit limit
        try:
            P.start(s, a, background=False)
        finally:
            P._transport = orig
        self.assertEqual(P.job(s, a)["state"], "failed")
        self.assertIn("credits at 75%", P.job(s, a)["log"][-1]["msg"])
        self.assertFalse(s.q("SELECT 1 FROM hosted_assets"))
        s.set_pref("cloudinary_usage", None)
        tx = P.FixtureTransport()
        H.host(s, P.sha256(v), v, tx)                                       # hosted, then the job is deleted
        P.delete(s, a)
        self.assertEqual(s.q("SELECT state FROM hosted_assets")[0]["state"], "deleted")
        b = P.create(s, AID, "ig-en", v)
        self.approved(s, b, v)
        H.host(s, P.sha256(v), v, tx)
        P._set(s, b, state="failed")
        self.assertEqual(H.cleanup(s, tx), [])                              # a recent failure may be retried
        from datetime import datetime, timedelta, timezone
        self.assertEqual(len(H.cleanup(s, tx, now=datetime.now(timezone.utc) + timedelta(days=4))), 1)  # abandoned

    def test_manual_package_and_youtube_link(self):
        s = fresh("man")
        jid = P.create(s, AID, "yt-es", video("m.mp4", 1000), "manual")
        self.assertEqual(P.job(s, jid)["state"], "manual_pending")
        r = P.package(s, jid)
        folder = ROOT / r["folder"]
        self.assertTrue((folder / "CHECKLIST.md").exists() and (folder / "title.txt").exists())
        shutil.rmtree(folder)
        j = P.mark_posted(s, jid, "https://youtu.be/abcdefghijk")
        self.assertEqual(j["result"]["platform_video_id"], "abcdefghijk")
        with self.assertRaises(ValueError):
            P.mark_posted(s, P.create(s, AID, "yt-es", video("m2.mp4", 1000), "manual"), "not a link")


class ServerRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dashboard import server
        cls.s = fresh("srvpub")
        cls.port = 47698
        cls.app = server.App(cls.port)
        cls.app.store = cls.s
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
                return resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers

    def test_page_media_range_and_token(self):
        v = video("srv.mp4", 5000)
        st, body, _ = self.req("/api/publish/jobs", "POST", {"asset_id": AID, "video": str(v), "account_ids": ["yt-en"]})
        self.assertEqual(st, 403)                                       # writes need the page token
        st, body, _ = self.req("/api/publish/jobs", "POST", {"asset_id": AID, "video": str(v), "account_ids": ["yt-en"]}, {"X-Dash-Token": self.app.token})
        jid = json.loads(body)["job_ids"][0]
        st, body, _ = self.req("/api/publish")
        self.assertTrue(any(j["job_id"] == jid for j in json.loads(body)["jobs"]))
        st, body, hd = self.req("/api/publish/media/" + jid, headers={"Range": "bytes=100-199"})
        self.assertEqual((st, len(body), hd["Content-Range"]), (206, 100, "bytes 100-199/5000"))
        st, body, _ = self.req("/api/publish/job/" + jid)
        self.assertIn("choose whether this video is made for kids (YouTube requires the declaration)", json.loads(body)["check"]["errors"])
        st, body, _ = self.req("/api/publish/approve", "POST", {"job_id": jid, "confirm": "wrong"}, {"X-Dash-Token": self.app.token})
        self.assertEqual(st, 400)


class DeleteVideo(unittest.TestCase):
    """Content page Delete (owner, 2026-11-25): Recycle Bin, unsent drafts removed, posted or busy videos refused."""

    def test_deletes_file_sidecars_and_drafts(self):
        from dashboard import analytics as A
        s = fresh("delete")
        v = video("del_a.mp4", 2048)
        v.with_suffix(".qc.json").write_text("{}")
        jid = P.create(s, AID, "yt-en", v)
        binned = []
        r = A.delete_video(s, P.rel(v), recycle=lambda f: (binned.append(f.name), f.unlink()))
        self.assertEqual(r["drafts_removed"], 1)
        self.assertEqual(sorted(binned), ["del_a.mp4", "del_a.qc.json"])
        self.assertIsNone(P.job(s, jid))

    def test_refuses_approved_or_posted(self):
        from dashboard import analytics as A
        s = fresh("delete2")
        v = video("del_b.mp4", 2048)
        jid = P.create(s, AID, "yt-en", v)
        s.x("UPDATE publish_jobs SET state='approved' WHERE job_id=?", (jid,))
        with self.assertRaises(ValueError):
            A.delete_video(s, P.rel(v), recycle=lambda f: self.fail("must not delete"))
        s.x("UPDATE publish_jobs SET state='draft' WHERE job_id=?", (jid,))
        s.save_upload({"asset_id": AID, "platform": "youtube", "account_id": "yt-en", "platform_video_id": "x1", "url": "https://youtu.be/x1"})
        with self.assertRaises(ValueError):
            A.delete_video(s, P.rel(v), recycle=lambda f: self.fail("must not delete"))
        self.assertTrue(v.exists())

    def test_refuses_outside_exports_and_media(self):
        from dashboard import analytics as A
        with self.assertRaises(ValueError):
            A.delete_video(fresh("delete3"), "config/dashboard/settings.json", recycle=lambda f: self.fail("no"))


if __name__ == "__main__":
    unittest.main()
