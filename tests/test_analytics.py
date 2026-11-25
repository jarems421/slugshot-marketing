"""Offline tests for the owner-facing analytics (dashboard/analytics.py): totals, drill-downs, measurement windows,
creative tags, comparisons and the learning loop. Fixtures only, no network.
Run: .venv\\Scripts\\python -m unittest tests.test_analytics"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="ssanalytics_"))
os.environ["SLUGSHOT_DASH_VAULT"] = str(TMP / "vault")
os.environ["SLUGSHOT_DASH_FIXTURE"] = "1"
sys.path.insert(0, str(ROOT))

from dashboard import analytics as A  # noqa: E402
from dashboard import sync, views  # noqa: E402
from dashboard.store import Store  # noqa: E402

FX = ROOT / "tests" / "fixtures" / "dashboard"
spec = importlib.util.spec_from_file_location("fixture_history", FX / "history.py")
HIST = importlib.util.module_from_spec(spec)
spec.loader.exec_module(HIST)


def fresh(name, history=True):
    p = TMP / f"{name}.db"
    for f in TMP.glob(f"{name}.db*"):
        f.unlink()
    os.environ["SLUGSHOT_DASH_DB"] = str(p)
    s = Store(p)
    sync.run(s, fixture=True, sleep=lambda _s: None)
    if history:
        HIST.backfill(s)
    return s


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


class Gains(unittest.TestCase):
    def test_first_snapshot_near_publish_counts(self):
        g, part = A.gains([("2026-11-10", 100), ("2026-11-11", 160)], "2026-11-10", "2026-11-01", "2026-11-30", False)
        self.assertEqual((g, part), ({"2026-11-10": 100, "2026-11-11": 60}, False))

    def test_tracking_that_began_late_is_partial_not_counted(self):
        g, part = A.gains([("2026-11-20", 5000), ("2026-11-21", 5100)], "2026-10-01", "2026-11-01", "2026-11-30", False)
        self.assertEqual((g, part), ({"2026-11-21": 100}, True))   # the 5,000 earlier views are not "views this month"
        g, _ = A.gains([("2026-11-20", 5000), ("2026-11-21", 5100)], "2026-10-01", A.EARLIEST, "2026-11-30", True)
        self.assertEqual(sum(g.values()), 5100)                       # but they count in all time

    def test_window_before_tracking_is_unknown(self):
        _, part = A.gains([("2026-11-20", 5000)], "2026-10-01", "2026-10-01", "2026-10-31", False)
        self.assertTrue(part)
        g, part = A.gains([("2026-11-20", 5000)], "2026-11-15", "2026-10-01", "2026-10-31", False)
        self.assertEqual((g, part), ({}, False))                     # published after the window: a real zero


class Totals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = fresh("totals")
        cls.d = A.analytics(cls.s, {"range": "30"})

    def test_views_are_the_sum_of_accounts_and_labelled(self):
        t = self.d["totals"]["views"]
        self.assertEqual(t["value"], sum(r["stats"]["views"] for r in self.d["accounts"] if r["stats"]["views"] is not None))
        self.assertIn("tt-en", t["estimated"])                       # TikTok period views come from snapshots
        self.assertIn("yt-es", t["missing"])                         # no data stays missing, never 0

    def test_one_source_per_video_no_double_counting(self):
        snaps = A.snapshots(self.s, A.uploads_of(self.s, ["tt-en"]))
        both = snaps["UPL-tiktok-7400000000000000001"]
        self.assertEqual(both["views"]["source"], "tiktok")          # native first, though Buffer also reports the video
        self.assertEqual(both["reach"]["source"], "buffer")          # Buffer adds what TikTok's API lacks

    def test_followers_combined_and_change(self):
        f = self.d["totals"]["followers"]
        self.assertEqual(f["value"], sum(r["stats"]["followers"] for r in self.d["accounts"] if r["stats"]["followers"] is not None))
        self.assertIsNotNone(f["change"])
        tt = next(r for r in self.d["accounts"] if r["account_id"] == "tt-en")["stats"]
        self.assertEqual(tt["followers_change_basis"], "since first reading")  # TikTok reports no gains/losses

    def test_avg_view_is_weighted_by_views_of_videos_that_report_it(self):
        snaps = A.snapshots(self.s, A.uploads_of(self.s, ["yt-en"]))
        num = sum(A.latest(v["avg_view_duration_s"]["points"]) * A.latest(v["views"]["points"]) for v in snaps.values() if "avg_view_duration_s" in v)
        den = sum(A.latest(v["views"]["points"]) for v in snaps.values() if "avg_view_duration_s" in v)
        yt = next(r for r in self.d["accounts"] if r["account_id"] == "yt-en")["stats"]
        self.assertAlmostEqual(yt["avg_view_s"], round(num / den, 1))

    def test_filters_narrow(self):
        tt = A.analytics(self.s, {"range": "30", "platform": "tiktok"})
        self.assertEqual({r["platform"] for r in tt["accounts"]}, {"tiktok"})
        es = A.analytics(self.s, {"range": "30", "language": "es"})
        self.assertEqual({r["language"] for r in es["accounts"]}, {"es"})
        one = A.analytics(self.s, {"range": "all", "account": "ig-en"})
        self.assertEqual([r["account_id"] for r in one["accounts"]], ["ig-en"])
        self.assertTrue(one["all_time"])


class WindowsTagsLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = s = fresh("loop", history=False)
        s.save_concept({"concept_id": "CON-FX-RULE", "title": "Rule world", "format": "WORLD",
                        "tags": A.clean_tags({"format": ["WORLD"], "hook": ["RULE_WORLD"], "codes": ["RULE_WORLD"], "character": ["Floppy"]})})
        s.save_concept({"concept_id": "CON-FX-DUEL", "title": "Duel", "format": "PVP",
                        "tags": A.clean_tags({"format": ["PVP"], "codes": ["GAMEPLAY_PROOF"]})})
        s.save_asset({"concept_id": "CON-FX-RULE", "language": "en", "version": "V01"})
        s.save_asset({"concept_id": "CON-FX-DUEL", "language": "en", "version": "V01"})
        pub = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
        rows = []
        # Four TikTok videos: three read at ~48 h, one only at 70 h (outside the 48 h window).
        for i, (concept, n_views, at) in enumerate([("RULE", 900, 46), ("RULE", 1100, 50), ("RULE", 700, 47), ("DUEL", 400, 70)]):
            vid = f"81000000000000000{i}"
            s.save_upload({"platform": "tiktok", "platform_video_id": vid, "account_id": "tt-en", "asset_id": f"CON-FX-{concept}-EN-V01",
                           "published_at_utc": pub.isoformat(), "title": f"{concept} {i}", "source": "test"})
            obs_at = (pub + timedelta(hours=at)).isoformat()
            rows.append({"platform": "tiktok", "account_id": "tt-en", "entity_type": "upload", "entity_id": f"UPL-tiktok-{vid}",
                         "metric": "views", "value": n_views, "period_type": "lifetime", "period_start": "", "period_end": obs_at[:10],
                         "observed_at_utc": obs_at, "source": "tiktok"})
        s.put_obs(rows)
        cls.kb_dir = TMP / "kb"
        shutil.copytree(ROOT / "tests" / "fixtures" / "knowledge", cls.kb_dir)
        views.KB_FIXTURE_DIR = cls.kb_dir                             # never write into the fixture folder itself

    def test_checkpoints_flag_readings_outside_the_window(self):
        late = {"upload_id": "UPL-tiktok-810000000000000003", "platform": "tiktok", "published_at_utc": "2026-11-01T12:00:00+00:00"}
        cp = A.checkpoints(self.s, late, ("views",))
        self.assertFalse(cp["48h"]["views"]["within"])                # read at 70 h: shown, but not comparable at 48 h
        self.assertTrue(cp["7d"]["views"]["value"] == 400 and not cp["7d"]["views"]["within"])

    def test_compare_groups_comparable_videos_only(self):
        r = A.compare(self.s, {"platform": "tiktok", "checkpoint": "48h", "by": "format"})
        self.assertGreaterEqual(r["excluded"]["outside_window"], 1)       # incl. the 70 h reading and older fixture videos
        world = next(g for g in r["groups"] if g["key"] == "WORLD")
        self.assertEqual((world["n"], world["median"], world["enough"]), (3, 900, True))
        self.assertFalse(any(g["key"] == "PVP" for g in r["groups"]))   # its only video was read too late
        with self.assertRaises(ValueError):
            A.compare(self.s, {"checkpoint": "48h"})                    # never across platforms

    def test_tags_reuse_existing_vocabularies(self):
        v = A.vocab()
        self.assertIn("RULE_WORLD", [x["id"] for x in v["codes"]])
        self.assertIn("Floppy", [x["id"] for x in v["character"]])
        with self.assertRaises(ValueError):
            A.clean_tags({"codes": ["MADE_UP_CODE"]})

    def test_finding_reaches_the_bank_and_the_next_brief(self):
        r = A.compare(self.s, {"platform": "tiktok", "checkpoint": "48h", "by": "format"})
        e = A.finding_draft(r, "WORLD")
        self.assertEqual((e["evidence_label"], e["review_status"], e["concept_refs"]), ("owned_result", "draft", ["CON-FX-RULE"]))
        A.save_finding(e)
        kb = views._kb()
        entries = kb.load()
        self.assertIn(e["id"], [x["id"] for x in entries])
        errs, _ = kb.validate(entries)
        self.assertFalse([x for x in errs if e["id"] in x])
        groups = kb.brief(entries, "rule world tiktok", fmt="WORLD")
        self.assertIn(e["id"], [x["id"] for x in groups.get("claims", [])])


class Cadence(unittest.TestCase):
    def test_young_videos_refresh_more_often(self):
        s = fresh("cadence", history=False)
        cfg = {"refresh_hours": 24, "young_refresh_hours": 4, "young_days": 8}
        self.assertEqual(sync.refresh_hours(s, {"account_id": "yt-es"}, cfg), 24)
        s.save_upload({"platform": "youtube", "platform_video_id": "FXyoung00001", "account_id": "yt-es",
                       "published_at_utc": datetime.now(timezone.utc).isoformat(), "source": "test"})
        self.assertEqual(sync.refresh_hours(s, {"account_id": "yt-es"}, cfg), 4)


class Library(unittest.TestCase):
    def test_local_videos_group_by_concept_and_skip_test_renders(self):
        s = fresh("library", history=False)
        media = ROOT / "media" / "_test_library"
        media.mkdir(parents=True, exist_ok=True)
        try:
            for name in ("a_en.mp4", "a_es.mp4"):
                (media / name).write_bytes(b"\x00" * 64)
            s.save_concept({"concept_id": "CON-FX-LIB", "title": "Library test"})
            s.save_asset({"concept_id": "CON-FX-LIB", "language": "en", "version": "V01", "edit_file": "media/_test_library/a_en.mp4"})
            s.save_asset({"concept_id": "CON-FX-LIB", "language": "es", "version": "V01", "edit_file": "media/_test_library/a_es.mp4"})
            g = next(x for x in A.library(s) if x["key"] == "CON-FX-LIB")
            self.assertEqual((g["languages"], len(g["versions"]), g["status"]), (["en", "es"], 2, "ready"))
            self.assertFalse(any("TEST" in v["path"] for x in A.library(s, True) for v in x["versions"]))
        finally:
            shutil.rmtree(media, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
