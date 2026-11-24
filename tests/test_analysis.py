"""Adversarial and positive tests for the evidence ledger (scripts/evidence.py) and analysis (scripts/research_analysis.py).
Fixtures only, no network. Run: .venv\\Scripts\\python -m unittest tests.test_analysis"""
import csv
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import evidence  # noqa: E402
import research_analysis as ra  # noqa: E402

OUT = ROOT / "out" / "unittest_analysis"
PY = sys.executable


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return path


def ledger(evidence_items, claims):
    L = evidence.template("TEST-01", "test")
    L["evidence"], L["claims"] = evidence_items, claims
    return L


def ev(eid, family="tiktok", role="platform_metric", prov="P1", **kw):
    return {"evidence_id": eid, "source_family": family, "actual_role": role, "provenance": prov,
            "locator": kw.pop("locator", {"note": "fixture"}), **kw}


def claim(cid, text, level="O", status="supported", strength="exploratory", refs=("E1",), **kw):
    return {"claim_id": cid, "claim_text": text, "level": level, "support_status": status, "strength": strength,
            "evidence_refs": list(refs), "review": {"ai_reviewed": True}, **kw}


def check(L, bundle=None):
    return evidence.validate(L, OUT / "ledger.json", bundle)


def has(items, fragment):
    return any(fragment in i for i in items)


class Traps(unittest.TestCase):
    def test_01_huge_hashtag_count_is_not_accelerating(self):
        L = ledger([ev("E1", item="tiktok:hashtag:huss", observed_at="2026-11-24", scope={"region": "US", "period": "7 days"},
                       locator={"value": "71.6M"}, metric_definition="unknown")],
                   [claim("C1", "Huss is an accelerating meme with 71.6M weekly views", level="P", strength="suggestive")])
        self.assertTrue(has(check(L).errors, "needs at least two comparable observations"))

    def test_02_same_upstream_is_not_independent(self):
        L = ledger([ev("E1", family="youtube", item="v1", locator={"value": "7.36M"}),
                    ev("E2", family="youtube", role="third_party_estimate", prov="P3", item="v1", locator={"value": "7.36M"}),
                    ev("E3", family="youtube", role="third_party_estimate", prov="P3", item="v1", locator={"value": "7.4M"})],
                   [claim("C1", "The video reached about 7.36M views", level="O", strength="convergent", refs=("E1", "E2", "E3"))])
        self.assertTrue(has(check(L).errors, "convergent needs at least two independent source families"))

    def test_03_blank_is_not_zero(self):
        f = write_csv(OUT / "b" / "obs.csv", [{"key": "a", "likes": ""}])
        L = ledger([ev("E1", locator={"file": "obs.csv", "where": {"key": "a"}, "column": "likes", "value": "0"})],
                   [claim("C1", "The post had no likes")])
        self.assertTrue(has(check(L, f.parent).errors, "missing is not zero"))

    def test_04_spanish_retrieval_is_not_audience(self):
        L = ledger([ev("E1", family="youtube", item="v1", scope={"region_param": "MX", "relevance_language_param": "es"})],
                   [claim("C1", "Mexican viewers like underdog videos", level="I", strength="exploratory",
                          rival_hypotheses=["retrieval bias"])])
        self.assertTrue(has(check(L).errors, "not audience geography"))

    def test_05_one_declining_video_is_not_a_declining_meme(self):
        L = ledger([ev("E1", family="youtube", item="v1", metric="views", observed_at="2026-11-20T00:00:00+00:00", scope={"q": "huss"}),
                    ev("E2", family="youtube", item="v1", metric="views", observed_at="2026-11-24T00:00:00+00:00", scope={"q": "huss"})],
                   [claim("C1", "The Huss meme is declining", level="P", strength="suggestive", refs=("E1", "E2"),
                          rival_hypotheses=["normal age decay"])])
        self.assertTrue(has(check(L).errors, "one item's trajectory"))

    def test_06_pageviews_are_not_fandom_size(self):
        L = ledger([ev("E1", family="wikimedia", scope={"language_edition": "es"})],
                   [claim("C1", "The Spanish Slugterra fandom is large", level="I", strength="exploratory",
                          rival_hypotheses=["news spike"])])
        self.assertTrue(has(check(L).errors, "fandom"))

    def test_07_correlation_is_not_causation(self):
        L = ledger([ev("E1")], [claim("C1", "Using the trending sound drives higher engagement", level="P", strength="suggestive",
                                      rival_hypotheses=["creator size"])])
        self.assertTrue(has(check(L).errors, "causal wording"))
        L2 = ledger([ev("E1")], [claim("C1", "The sound causes more views", level="C", strength="suggestive")])
        self.assertTrue(has(check(L2).errors, "without an experiment"))

    def test_08_featured_sample_not_generalised(self):
        L = ledger([ev("E1", sample_role="featured"), ev("E2", sample_role="featured")],
                   [claim("C1", "Most Roblox clips open with a rule statement", level="P", strength="exploratory", refs=("E1", "E2"),
                          rival_hypotheses=["selection"])])
        self.assertTrue(has(check(L).errors, "generalises from featured examples"))

    def test_09_specification_fragility_detected(self):
        rows = [{"creator_handle": "a", "fmt": "X", "value_numeric": "1000"}, {"creator_handle": "a", "fmt": "X", "value_numeric": "900"},
                {"creator_handle": "b", "fmt": "Y", "value_numeric": "300"}, {"creator_handle": "c", "fmt": "Y", "value_numeric": "350"},
                {"creator_handle": "c", "fmt": "X", "value_numeric": "100"}]
        f = write_csv(OUT / "sens" / "public_observations_x.csv", rows)
        r = subprocess.run([PY, str(ROOT / "scripts" / "research_analysis.py"), "sensitivity", str(f), "value_numeric", "--by", "fmt"],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(json.loads(r.stdout)["verdict"], "fragile")  # dropping creator 'a' flips the top format

    def test_10_counterexample_flags_review(self):
        L = ledger([ev("E1", observed_at="t1"), ev("E2", observed_at="t2"), ev("E3")],
                   [claim("C1", "Rule-statement hooks appear in recent Roblox story clips", level="P", strength="supported_descriptive",
                          refs=("E1", "E2"), counterevidence_refs=["E3"], rival_hypotheses=["search surface"])])
        R = check(L)
        self.assertTrue(has(R.review, "counterevidence is recorded"))

    def test_11_uncertain_but_useful_recommendation_is_valid(self):
        L = ledger([ev("E1", item="tiktok:hashtag:huss", observed_at="2026-11-24", locator={"value": "24.4K"})],
                   [claim("C1", "Creative Center displayed 24.4K posts for #huss (US, 7 days)", level="O"),
                    claim("C2", "Prototype one 15-second rule-world Slugshot skit as a cheap test", level="R", status="supported",
                          strength="exploratory", refs=("C1",),
                          next_discriminating_test="Post variant vs plain duel; compare 48 h engaged views on our own channel")])
        R = check(L)
        self.assertEqual(R.errors, [], R.errors)

    def test_12_unsupported_needs_contradiction_or_search(self):
        L = ledger([ev("E1")], [claim("C1", "Huss is popular in Chile", level="O", status="unsupported", refs=())])
        self.assertTrue(has(check(L).errors, "unsupported needs the evidence"))

    def test_13_numbers_and_rows_must_match(self):
        f = write_csv(OUT / "n" / "obs.csv", [{"key": "a", "views": "71600000"}])
        L = ledger([ev("E1", locator={"file": "obs.csv", "where": {"key": "a"}, "column": "views", "value": "81.6M"})],
                   [claim("C1", "Creative Center displayed 81.6M views")])
        self.assertTrue(has(check(L, f.parent).errors, "doesn't match"))
        L["evidence"][0]["locator"]["value"] = "71.6M"
        L["claims"][0]["claim_text"] = "Creative Center displayed 71.6M views"
        self.assertEqual(check(L, f.parent).errors, [])

    def test_14_exact_quote(self):
        src = OUT / "q" / "paper.txt"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("Triangulation is strongest when methods have different sources of bias.", encoding="utf-8")
        L = ledger([ev("E1", family="literature", role="literature_finding",
                       locator={"source_path": "paper.txt", "quote": "methods have unrelated sources of bias"})],
                   [claim("C1", "Triangulation works best with differently biased methods", level="O")])
        self.assertTrue(has(check(L, src.parent).errors, "not an exact passage"))

    def test_16_honest_uncertainty_is_not_flagged_as_overclaim(self):
        L = ledger([ev("E1", item="tiktok:hashtag:huss", observed_at="2026-11-24")],
                   [claim("C1", "Whether Huss is rising or declining is unknown from one snapshot", level="P",
                          status="supported", strength="exploratory", rival_hypotheses=["n/a"])])
        R = check(L)
        self.assertEqual(R.errors, [])
        self.assertTrue(has(R.review, "negated/uncertain wording"))

    def test_17_a_long_series_counts_as_repeated_observation(self):
        L = ledger([ev("E1", family="wikimedia", role="observed_result", item="es:Slugterra", series_points=3980)],
                   [claim("C1", "Spanish Wikipedia attention to the article is declining", level="P", strength="suggestive",
                          rival_hypotheses=["news cycle"])])
        self.assertFalse(has(check(L).errors, "two comparable observations"))

    def test_18_overclaim_recorded_as_unsupported_is_a_valid_audit(self):
        L = ledger([ev("E1", item="tiktok:hashtag:huss", observed_at="2026-11-24", locator={"value": "71.6M"})],
                   [claim("C1", "Huss is accelerating", level="P", status="unsupported", strength="exploratory",
                          rival_hypotheses=["one snapshot"])])
        R = check(L)
        self.assertEqual(R.errors, [])
        self.assertTrue(has(R.review, "record of an overclaim"))

    def test_15_evidenceguard_export_is_schema_shaped(self):
        L = ledger([ev("E1")], [claim("C1", "Creative Center showed the hashtag")])
        p = OUT / "eg.json"
        p.write_text(json.dumps(L), encoding="utf-8")
        subprocess.run([PY, str(ROOT / "scripts" / "evidence.py"), "export-evidenceguard", str(p)], check=True,
                       capture_output=True, cwd=ROOT)
        out = json.loads((OUT / "eg.evidenceguard.json").read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "research" / "upstream" / "evidenceguard" / "claim_evidence.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(out), set(schema["required"]))
        self.assertEqual(out["summary"]["total_claims"], 1)


class Analysis(unittest.TestCase):
    def test_youtube_cross_channel_guard(self):
        rows = [{"video_id": "a", "channel_id": "UC1", "views": "10"}, {"video_id": "b", "channel_id": "UC2", "views": "20"}]
        self.assertIsNotNone(ra.youtube_guard("youtube_report_x.csv", rows))
        self.assertIsNone(ra.youtube_guard("youtube_report_x.csv", rows[:1]))
        self.assertIsNone(ra.youtube_guard("public_observations_x.csv", rows))
        # derived files (samples, joins) carry YouTube columns without the youtube_ filename
        self.assertIsNotNone(ra.youtube_guard("sample_BRIEF-X.sample.csv", rows))
        self.assertEqual(ra.provider_of("sample_BRIEF-X.sample.csv", rows[0].keys()), "youtube")

    def test_repeat_collapses_duplicate_contexts(self):
        rows = [{"video_id": "v", "observation_moment": "2026-11-24T10:00:00+00:00", "views": "100"},
                {"video_id": "v", "observation_moment": "2026-11-24T10:00:00+00:00", "views": "100"},
                {"video_id": "v", "observation_moment": "2026-11-24T14:00:00+00:00", "views": "180"}]
        f = write_csv(OUT / "rep" / "youtube_history_x.csv", rows)
        r = subprocess.run([PY, str(ROOT / "scripts" / "research_analysis.py"), "repeat", str(f)], capture_output=True, text=True, cwd=ROOT)
        item = json.loads(r.stdout)["items"][0]
        self.assertEqual(item["observations"], 2)
        self.assertEqual(item["changes"][0]["per_hour"], 20.0)

    def test_blind_packet_has_no_outcomes(self):
        rows = [{"content_key": "tiktok:post:1", "title_or_name": "noob vs pro", "views": "9M", "rank": "1", "value_display": "9M",
                 "creator_handle": "famous"}]
        f = write_csv(OUT / "blind" / "public_observations_x.csv", rows)
        dest = OUT / "blind" / "packet.jsonl"
        subprocess.run([PY, str(ROOT / "scripts" / "research_analysis.py"), "blind-packet", str(f), "--out", str(dest)], check=True,
                       capture_output=True, cwd=ROOT)
        item = json.loads(dest.read_text(encoding="utf-8").splitlines()[0])
        self.assertFalse(set(item) & ra.OUTCOME_COLS)
        self.assertNotIn("creator", item)

    def test_multilabel_annotations(self):
        ver = json.loads((ROOT / "config/research/codebooks/slugshot-creative.json").read_text(encoding="utf-8"))["version"]
        rows = [{"content_key": "tiktok:post:1", "title_or_name": "everyone gets one creature in this town", "value_numeric": "500",
                 "sample_role": "featured"},
                {"content_key": "tiktok:post:2", "title_or_name": "my starter slug run", "value_numeric": "40", "sample_role": "ordinary"}]
        f = write_csv(OUT / "ann" / "public_observations_x.csv", rows)
        good = OUT / "ann" / "good.jsonl"
        good.write_text("\n".join(json.dumps(x) for x in [
            {"key": "tiktok:post:1", "codebook_version": ver, "access": "full_playback", "blinded": True,
             "codes": {"RULE_WORLD": "present", "STATUS_REVERSAL": "absent"}, "evidence": [{"quote": "everyone gets one creature"}]},
            {"key": "tiktok:post:2", "codebook_version": ver, "access": "caption_only", "blinded": True,
             "codes": {"RULE_WORLD": "uncertain"}}]), encoding="utf-8")
        run = lambda p: subprocess.run([PY, str(ROOT / "scripts" / "research_analysis.py"), "--data-dir", str(OUT / "annroot"),
                                        "join-annotations", str(f), str(p)], capture_output=True, text=True, cwd=ROOT)
        r = run(good)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        table = {row["code"]: row for row in json.loads(r.stdout)["association_table"]}
        self.assertEqual(table["RULE_WORLD"]["featured"]["present"], 1)
        self.assertEqual(table["RULE_WORLD"]["ordinary"]["uncertain"], 1)
        bad = OUT / "ann" / "bad.jsonl"
        bad.write_text(json.dumps({"key": "tiktok:post:2", "codebook_version": ver, "access": "caption_only",
                                   "blinded": True, "codes": {"RULE_WORLD": "absent", "CHOICE": "present"},
                                   "evidence": [{"quote": "which slug would you bring"}]}), encoding="utf-8")
        r = run(bad)
        self.assertIn("needs full_playback or excerpt", r.stdout)
        self.assertIn("not an exact substring", r.stdout)

    def test_trend_single_snapshot_is_unknown(self):
        d = OUT / "trendroot"
        shutil.rmtree(d, ignore_errors=True)
        write_csv(d / "observations" / "public_observations.csv", [
            {"content_key": "tiktok:hashtag:huss", "title_or_name": "#huss", "metric": "views", "source": "creative_center",
             "region": "US", "period": "7 days", "category": "", "value_display": "71.6M", "value_numeric": "71600000",
             "value_rounded": "true", "observed_at_utc": "2026-11-24T00:00:00+00:00", "provenance": "P1",
             "metric_definition": "unknown", "entity_type": "hashtag", "creator_handle": "", "creator_name": ""}])
        r = subprocess.run([PY, str(ROOT / "scripts" / "research_analysis.py"), "--data-dir", str(d), "trend", "huss"],
                           capture_output=True, text=True, cwd=ROOT)
        self.assertIn("lifecycle    unknown", r.stdout)

    def test_changepoints_find_a_step(self):
        d = OUT / "cproot"
        shutil.rmtree(d, ignore_errors=True)
        rows = [{"entity_id": "x", "project": "en.wikipedia", "article_title": "X", "granularity": "daily",
                 "period_start": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", "views": str(100 if i < 56 else 400)} for i in range(112)]
        write_csv(d / "wikimedia" / "wiki_pageviews.csv", rows)
        r = subprocess.run([PY, str(ROOT / "scripts" / "research_analysis.py"), "--data-dir", str(d), "changepoints"],
                           capture_output=True, text=True, cwd=ROOT)
        cps = json.loads(r.stdout)["series"][0]["change_points"]
        self.assertTrue(cps and cps[0] in ("2026-02-27", "2026-02-28", "2026-03-01", "2026-03-02", "2026-03-03"), cps)


if __name__ == "__main__":
    unittest.main()
