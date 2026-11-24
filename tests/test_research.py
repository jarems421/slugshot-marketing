"""Offline tests for the research collectors (fixtures only, no network). Run: .venv\\Scripts\\python -m unittest tests.test_research"""
import csv
import json
import shutil
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import observe  # noqa: E402
import research_common as rc  # noqa: E402
import trends_collect  # noqa: E402

OUT = ROOT / "out" / "unittest_research"
FX = ROOT / "tests" / "fixtures" / "research"
PY = sys.executable


def run(script, *args, check=True):
    r = subprocess.run([PY, str(ROOT / "scripts" / script), "--dry-run", "--data-dir", str(OUT / script), *args],
                       capture_output=True, text=True, cwd=ROOT)
    if check and r.returncode:
        raise AssertionError(f"{script} {args} failed:\n{r.stdout}\n{r.stderr}")
    return r


def rows(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Common(unittest.TestCase):
    def test_counts_keep_rounding_and_blanks(self):
        self.assertEqual(rc.parse_count("24.5K"), (24500, True))
        self.assertEqual(rc.parse_count("3,400"), (3400, False))
        self.assertEqual(rc.parse_count("1.2M"), (1200000, True))
        self.assertEqual(rc.parse_count("0"), (0, False))
        for blank in ("", "-", "—", "n/a", "unknown"):
            self.assertEqual(rc.parse_count(blank), (None, False))
        self.assertEqual(rc.parse_count("lots"), (None, False))

    def test_pacific_quota_day(self):
        # 07:30 UTC on 24 Nov is still 23 Nov in California (PST, UTC-8); 08:30 is 24 Nov.
        self.assertEqual(rc.pacific_day(datetime(2026, 11, 24, 7, 30, tzinfo=timezone.utc)), "2026-11-23")
        self.assertEqual(rc.pacific_day(datetime(2026, 11, 24, 8, 30, tzinfo=timezone.utc)), "2026-11-24")
        self.assertEqual(rc.pacific_day(datetime(2026, 7, 1, 6, 30, tzinfo=timezone.utc)), "2026-06-30")  # PDT

    def test_prune_expired_rows(self):
        p = OUT / "prune.csv"
        old = rc.iso(rc.now() - timedelta(hours=1))
        new = rc.iso(rc.now() + timedelta(hours=1))
        rc.write_rows(p, ["id", "expires_at_utc"], [{"id": "a", "expires_at_utc": old}, {"id": "b", "expires_at_utc": new},
                                                     {"id": "c", "expires_at_utc": ""}])
        self.assertEqual(rc.prune_file(p, ["id", "expires_at_utc"]), 1)
        self.assertEqual([r["id"] for r in rows(p)], ["b", "c"])

    def test_export_expiry_is_enforced(self):
        d = OUT / "exports"
        shutil.rmtree(d, ignore_errors=True)
        rc.export("test", "t", [{"a": "1"}], [("a", "x", "y")], notes=[], provenance="P1", retention_rule="test",
                  expires_at=rc.now() - timedelta(seconds=1), share=True, dry_run=True, out_dir=d)
        self.assertEqual(len(list(d.glob("*.csv"))), 2)  # export + MANIFEST
        self.assertEqual(len(rc.prune_exports(d)), 1)
        self.assertEqual([p.name for p in d.glob("*.csv")], ["MANIFEST.csv"])

    def test_old_header_is_migrated(self):
        p = OUT / "migrate.csv"
        rc.write_rows(p, ["a"], [{"a": "1"}])
        rc.append_rows(p, ["a", "b"], [{"a": "2", "b": "x"}])
        self.assertEqual(rows(p), [{"a": "1", "b": ""}, {"a": "2", "b": "x"}])


class YouTube(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(OUT / "yt_collect.py", ignore_errors=True)
        for args in (["discover", "roblox pvp", "--lang", "es", "--region", "MX"], ["chart", "--region", "MX"],
                     ["creators", "--channels", "UCDRYRUNCHANNELA"], ["comments", "--ids", "DRYRUN00001"],
                     ["stats", "--check-shorts"], ["report", "--history", "--comments"]):
            run("yt_collect.py", *args)
        cls.d = OUT / "yt_collect.py"

    def test_parameters_are_logged(self):
        snap = rows(self.d / "youtube_snapshots.csv")
        disc = [r for r in snap if r["collection"] == "discover"]
        self.assertTrue(disc and all(r["region_param"] == "MX" and r["relevance_language_param"] == "es" for r in disc))
        runs = rows(self.d / "runs.csv")
        self.assertIn('"region": "MX"', runs[0]["params_json"])

    def test_missing_stays_blank(self):
        r = [x for x in rows(self.d / "youtube_snapshots.csv") if x["video_id"] == "DRYRUN00002"][0]
        self.assertEqual(r["likes"], "")

    def test_shorts_status(self):
        rep = rows(next((self.d / "reports").glob("dryrun_youtube_report_*.csv")))
        st = {r["video_id"]: r["shorts_status"] for r in rep}
        self.assertEqual(st["DRYRUN00001"], "confirmed_short")
        self.assertEqual(st["DRYRUN00004"], "not_short_duration")
        self.assertIn(st["DRYRUNCHART1"], ("candidate", "confirmed_short"))

    def test_creator_window_stops_at_old_uploads(self):
        self.assertNotIn("DRYRUNOLD01", {r["video_id"] for r in rows(self.d / "youtube_snapshots.csv")})

    def test_comments_have_no_authors(self):
        text = (self.d / "youtube_comments.csv").read_text(encoding="utf-8")
        self.assertNotIn("SHOULD NOT BE STORED", text)
        self.assertNotIn("UCSHOULDNOTBESTORED", text)

    def test_every_request_counted(self):
        q = rows(self.d / "quota_log.csv")
        self.assertTrue(any(r["bucket"] == "search" for r in q))
        self.assertTrue(all(r["quota_day_pt"] for r in q))

    def test_exports_have_expiry_json_and_no_scores(self):
        man = rows(self.d / "reports" / "MANIFEST.csv")
        self.assertTrue(all(r["expires_at_utc"] for r in man))
        j = json.loads(next((self.d / "reports").glob("dryrun_youtube_report_*.json")).read_text(encoding="utf-8"))
        cols = {c["name"] for c in j["columns"]}
        self.assertFalse({"rank", "score", "median", "outlier"} & cols)

    def test_budget_stops_before_requests(self):
        cfg_path = rc.CONFIG / "settings.json"
        original = cfg_path.read_text(encoding="utf-8")
        cfg = json.loads(original)
        cfg["youtube"]["daily_search_budget"] = 0
        try:
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            r = run("yt_collect.py", "discover", "x", check=False)
        finally:
            cfg_path.write_text(original, encoding="utf-8")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Stopped before any request", r.stderr)


class Wikimedia(unittest.TestCase):
    def test_redirect_and_gaps(self):
        shutil.rmtree(OUT / "wiki_collect.py", ignore_errors=True)
        run("wiki_collect.py", "pull")
        res = rows(OUT / "wiki_collect.py" / "wiki_resolved.csv")
        baj = [r for r in res if r["requested_title"] == "Bajoterra"][0]
        self.assertEqual((baj["is_redirect"], baj["canonical_title"]), ("true", "Slugterra"))
        pv = rows(OUT / "wiki_collect.py" / "wiki_pageviews.csv")
        red = [r for r in pv if r["title_role"] == "redirect"]
        self.assertEqual(len(red), 2)  # fixture has 2 days; the missing days must not appear as zeros
        self.assertTrue(all(r["language_edition"] == "es" for r in red))
        run("wiki_collect.py", "pull")  # second pull must not duplicate points
        self.assertEqual(len(rows(OUT / "wiki_collect.py" / "wiki_pageviews.csv")), len(pv))


class Trends(unittest.TestCase):
    def test_rss_and_imports(self):
        d = OUT / "trends_collect.py"
        shutil.rmtree(d, ignore_errors=True)
        run("trends_collect.py", "rss", "--geo", "GB,MX")
        rss = rows(d / "trending_now.csv")
        self.assertEqual({r["geo"] for r in rss}, {"GB", "MX"})
        self.assertTrue(all(r["trend_started_at_utc"].endswith("+00:00") for r in rss))
        run("trends_collect.py", "import", str(FX / "trends_multiTimeline.csv"), str(FX / "trends_geoMap.csv"),
            str(FX / "trends_relatedQueries.csv"), "--geo", "MX", "--search-type", "web", "--downloaded-at", "2026-11-24T10:00:00Z")
        vals = rows(d / "explore_values.csv")
        kinds = {(r["term"], r["value_raw"]): r["value_kind"] for r in vals}
        self.assertEqual(kinds[("Bajoterra", "<1")], "less_than_one")
        self.assertEqual(kinds[("Roblox", "Breakout")], "breakout")
        self.assertEqual(kinds[("Roblox", "+250%")], "percent_increase")
        self.assertIn("missing", kinds.values())
        self.assertEqual(len({r["import_id"] for r in vals}), 3)  # each download keeps its own scale
        again = run("trends_collect.py", "import", str(FX / "trends_geoMap.csv"))
        self.assertIn("already imported", again.stdout)
        bad = run("trends_collect.py", "import", str(FX / "trends_bad.csv"), check=False)
        self.assertNotEqual(bad.returncode, 0)

    def test_value_kind(self):
        self.assertEqual(trends_collect.value_kind("100"), ("100", "index_0_100"))
        self.assertEqual(trends_collect.value_kind(""), ("", "missing"))


class Observations(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(OUT / "observe.py", ignore_errors=True)

    def test_examples_import_and_dedupe(self):
        ex = ROOT / "data" / "templates" / "examples"
        run("observe.py", "import", str(ex / "observations_creative_center.csv"), "--source", "creative_center",
            "--platform", "tiktok", "--entity-type", "hashtag")
        md = run("observe.py", "import", str(ex / "observations_chatgpt_table.md"), "--source", "creative_center",
                 "--platform", "tiktok", "--entity-type", "hashtag", "--region", "US", "--period", "7 days", "--observed-at", "2026-11-24")
        self.assertIn("4 duplicates skipped", md.stdout)
        run("observe.py", "import", str(ex / "observations_vidiq.csv"))
        st = rows(OUT / "observe.py" / "public_observations.csv")
        huss = [r for r in st if r["content_key"] == "tiktok:hashtag:huss" and r["metric"] == "views"][0]
        self.assertEqual((huss["value_display"], huss["value_numeric"], huss["value_rounded"], huss["provenance"]),
                         ("71.6M", "71600000", "true", "P1"))
        vid = {r["metric"]: r["provenance"] for r in st if r["content_key"] == "tiktok:post:7708074478366100754"}
        self.assertEqual(vid, {"views": "P3", "breakout_multiple": "P3", "format_description": "P4"})
        self.assertFalse([r for r in st if r["metric"] == "rank"])  # blank rank is not invented

    def test_bad_rows_refuse_file(self):
        r = run("observe.py", "import", str(FX / "observations_bad.csv"), check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ambiguous", r.stdout)
        self.assertIn("relative", r.stdout)
        self.assertIn("in the future", r.stdout)
        self.assertFalse((OUT / "observe.py" / "public_observations.csv").exists())

    def test_repeat_observation_kept(self):
        f1, f2 = OUT / "o1.csv", OUT / "o2.csv"
        OUT.mkdir(parents=True, exist_ok=True)
        f1.write_text("url,observed_at_utc,views,source\nhttps://www.tiktok.com/@a/video/1234567890,2026-11-23T10:00:00Z,1.0K,platform_page\n")
        f2.write_text("url,observed_at_utc,views,source\nhttps://www.tiktok.com/@a/video/1234567890,2026-11-24T10:00:00Z,2.5K,platform_page\n")
        run("observe.py", "import", str(f1))
        out = run("observe.py", "import", str(f2))
        self.assertIn("1 items are repeat observations", out.stdout)

    def test_markdown_links_and_bold(self):
        self.assertEqual(observe.strip_md("[GH'S](https://youtube.com/shorts/0w10o6CLxps)"), "https://youtube.com/shorts/0w10o6CLxps")
        self.assertEqual(observe.strip_md("**#huss**"), "#huss")


class Corrections(unittest.TestCase):
    """Stage 4.4 review fixes (ChatGPT review, 2026-11-24)."""

    def test_wiki_aliases_failures_zero(self):
        d = OUT / "wiki_edge"
        shutil.rmtree(d, ignore_errors=True)
        r = subprocess.run([PY, str(ROOT / "scripts" / "wiki_collect.py"), "--dry-run", "--data-dir", str(d), "--entities",
                            str(FX / "wiki_entities_edgecases.csv"), "pull", "--all-redirects"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("counted once", r.stdout)
        pv = rows(d / "wiki_pageviews.csv")
        keys = [(x["project"], x["article_title"], x["period_start"]) for x in pv]
        self.assertEqual(len(keys), len(set(keys)))  # no title counted twice
        self.assertEqual({x["entity_id"] for x in pv}, {"slugterra"})
        zero = [x for x in pv if x["article_title"] == "Slugterra (serie)"]
        self.assertEqual(zero[0]["views"], "0")  # a returned 0 stays 0
        cov = {x["article_title"]: x["status"] for x in rows(d / "wiki_coverage.csv")}
        self.assertEqual(cov["Brokenpage"], "failed")
        self.assertEqual(cov["Quietpage"], "no_data")
        self.assertEqual(cov["Bajoterra"], "ok")
        self.assertEqual(cov["Lookupfails"], "resolve_failed")  # never silently dropped
        res = {x["requested_title"]: x["note"] for x in rows(d / "wiki_resolved.csv")}
        self.assertTrue(res["Lookupfails"].startswith("resolve failed"))

    def test_youtube_contexts_moments_and_category(self):
        d = OUT / "yt_moments"
        shutil.rmtree(d, ignore_errors=True)
        ytrun = lambda *x: subprocess.run([PY, str(ROOT / "scripts" / "yt_collect.py"), "--dry-run", "--data-dir", str(d), *x],
                                          capture_output=True, text=True, cwd=ROOT, check=True)
        ytrun("chart", "--region", "MX")
        ytrun("chart", "--region", "ES")
        ytrun("report", "--history")
        rep = {r["video_id"]: r for r in rows(next((d / "reports").glob("dryrun_youtube_report_*.csv")))}
        c1 = rep["DRYRUNCHART1"]
        self.assertEqual((c1["stored_rows"], c1["observations"], c1["discovery_contexts"]), ("2", "1", "2"))
        self.assertEqual(c1["hours_since_prev"], "")  # same moment never produces growth
        self.assertEqual(rep["DRYRUNCHART2"]["category_mismatch"], "true")  # category 10 in a category-20 chart, kept
        self.assertEqual(c1["category_mismatch"], "false")
        hist = rows(next((d / "reports").glob("dryrun_youtube_history_*.csv")))
        self.assertTrue(all(h["duplicate_context"] == "true" for h in hist if h["video_id"] == "DRYRUNCHART1"))
        # Add an older moment: 30 min earlier is under min_growth_hours (no growth); 3 h earlier gives growth.
        snap = d / "youtube_snapshots.csv"
        base = rows(snap)
        fields = list(base[0].keys())
        t0 = rc.parse_time(base[0]["observed_at_utc"])
        for hours, views in ((0.5, "249000"), (3, "200000")):
            for r in shutil.rmtree(d / "reports", ignore_errors=True) or []:
                pass
            old = dict(base[0], observed_at_utc=rc.iso(t0 - timedelta(hours=hours)), views=views)
            rc.write_rows(snap, fields, [old] + base)
            ytrun("report")
            r = {x["video_id"]: x for x in rows(next((d / "reports").glob("dryrun_youtube_report_*.csv")))}[base[0]["video_id"]]
            if hours < 1:
                self.assertEqual(r["views_per_hour_since_prev"], "")
            else:
                self.assertEqual(r["view_increase_since_prev"], str(int(base[0]["views"]) - 200000))
                self.assertEqual(r["observations"], "2")

    def test_observation_scope_in_key(self):
        d = OUT / "obs_scope"
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        f = d / "scope.csv"
        f.write_text("title_or_name,views,region,period,category\n#huss,71.6M,US,7 days,\n#huss,20.1M,GB,7 days,\n"
                     "#huss,180M,US,30 days,\n#huss,1.1M,US,7 days,Games\n", encoding="utf-8")
        r = subprocess.run([PY, str(ROOT / "scripts" / "observe.py"), "--dry-run", "--data-dir", str(d), "import", str(f),
                            "--source", "creative_center", "--platform", "tiktok", "--entity-type", "hashtag",
                            "--observed-at", "2026-11-24", "--source-url", "https://ads.tiktok.com/creative/creativeCenter/trends/hashtag"],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout)
        st = rows(d / "public_observations.csv")
        self.assertEqual(len(st), 4)  # four scopes, no false duplicates
        self.assertEqual({x["value_display"] for x in st}, {"71.6M", "20.1M", "180M", "1.1M"})
        self.assertTrue(all(x["source_url"] and x["observed_at_utc"].startswith("2026-11-24") for x in st))
        again = subprocess.run([PY, str(ROOT / "scripts" / "observe.py"), "--dry-run", "--data-dir", str(d), "import", str(f),
                                "--source", "creative_center", "--platform", "tiktok", "--entity-type", "hashtag",
                                "--observed-at", "2026-11-24"], capture_output=True, text=True, cwd=ROOT)
        self.assertIn("4 duplicates skipped", again.stdout)

    def test_cc_paste_parser(self):
        en = observe.parse_cc_text((FX / "cc_paste_en.txt").read_text(encoding="utf-8"))
        self.assertEqual([(r["rank"], r["title_or_name"], r["posts"], r["views"]) for r in en],
                         [("1", "#dryrunhashone", "24.5K", "60.1M"), ("2", "#dryrunhashtwo", "940", "1.2M"),
                          ("3", "#dryrunhashthree", "", "")])
        es = observe.parse_cc_text((FX / "cc_paste_es.txt").read_text(encoding="utf-8"))
        self.assertEqual([(r["rank"], r["posts"], r["views"]) for r in es], [("1", "12,3K", "4,5M"), ("2", "800", "")])
        self.assertEqual(rc.parse_count("12,3K"), (12300, True))

    def test_trends_rss_export_has_expiry(self):
        d = OUT / "trends_exp"
        shutil.rmtree(d, ignore_errors=True)
        for args in (["rss", "--geo", "GB"], ["report"]):
            subprocess.run([PY, str(ROOT / "scripts" / "trends_collect.py"), "--dry-run", "--data-dir", str(d), *args],
                           capture_output=True, text=True, cwd=ROOT, check=True)
        man = rows(d / "reports" / "MANIFEST.csv")
        self.assertTrue(man and man[0]["expires_at_utc"])


class Twitch(unittest.TestCase):
    def test_dry_run_and_language_filter(self):
        d = OUT / "twitch_collect.py"
        shutil.rmtree(d, ignore_errors=True)
        run("twitch_collect.py", "clips", "--game", "Roblox", "--lang", "en,es")
        clips = rows(d / "twitch_clips.csv")
        self.assertEqual({c["language"] for c in clips}, {"en", "es"})
        self.assertNotIn("SHOULD-NOT-BE-STORED", (d / "twitch_clips.csv").read_text(encoding="utf-8"))
        self.assertTrue(all(c["expires_at_utc"] for c in clips))
        run("twitch_collect.py", "report")
        self.assertFalse(list(rc.SHARE.glob("dryrun_twitch_*")))  # never shared while terms are unreviewed


class Roblox(unittest.TestCase):
    def test_games(self):
        d = OUT / "rbx_collect.py"
        shutil.rmtree(d, ignore_errors=True)
        run("rbx_collect.py", "games")
        r = rows(d / "roblox_experiences.csv")[0]
        self.assertEqual((r["playing"], r["up_votes"], r["source_stability"]), ("12345", "900", "legacy_unstable"))


if __name__ == "__main__":
    unittest.main()
