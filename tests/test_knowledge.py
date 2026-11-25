"""Knowledge banks (scripts/kb.py), sentiment pipeline (scripts/sentiment.py) and their dashboard hooks.

Run: .venv\\Scripts\\python -m unittest tests.test_knowledge
Uses only tests/fixtures/knowledge and temporary folders; never the real banks.
"""
import copy
import csv
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import kb  # noqa: E402
import sentiment  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "knowledge"
GT = kb.game_truth_rows()


def fixture_entries():
    return kb.load(FIX)


def errors_for(entries):
    return kb.validate(entries, ledger_claims={}, gt=GT, ref_day=date(2026, 11, 25))[0]


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture_entries()
        self.by = {e["id"]: e for e in self.base}

    def mutate(self, eid, **changes):
        es = copy.deepcopy(self.base)
        for e in es:
            if e["id"] == eid:
                for k, v in changes.items():
                    if v is None:
                        e.pop(k, None)
                    else:
                        e[k] = v
        return es

    def test_fixture_is_valid(self):
        self.assertEqual(errors_for(self.base), [])

    def test_duplicate_ids(self):
        es = self.base + [copy.deepcopy(self.by["MECH-FX01"])]
        self.assertTrue(any("duplicate id" in e for e in errors_for(es)))

    def test_prefix_must_match_bank(self):
        es = self.mutate("MECH-FX01", bank="hooks")
        self.assertTrue(any("prefix" in e for e in errors_for(es)))

    def test_expiring_entry_needs_dates(self):
        es = self.mutate("OPP-FX01", review_by=None)
        self.assertTrue(any("needs review_by" in e for e in errors_for(es)))

    def test_evidence_backed_needs_refs_and_support(self):
        es = self.mutate("MECH-FX01", evidence_refs=None, support_status=None)
        errs = errors_for(es)
        self.assertTrue(any("needs claim_refs" in e for e in errs))
        self.assertTrue(any("needs support_status" in e for e in errs))

    def test_invalid_game_truth_row_and_label(self):
        bad_row = self.mutate("CHAR-FX01", game_truth=[{"row": "Floppy shoots lasers", "label": "OK"}])
        self.assertTrue(any("not in docs/game-truth.md" in e for e in errors_for(bad_row)))
        bad_label = self.mutate("CHAR-FX01", game_truth=[{"row": "Floppy transforms or uses an ability", "label": "OK"}])
        self.assertTrue(any("!= sheet label" in e for e in errors_for(bad_label)))
        missing = self.mutate("CHAR-FX01", game_truth=[])
        self.assertTrue(any("needs game_truth" in e for e in errors_for(missing)))

    def test_game_truth_sheet_records_floppy_damage(self):
        self.assertEqual(GT.get("Floppy does nothing / deals zero damage"), "NO")
        self.assertTrue(any(k.startswith("Floppy deals light damage") and v == "CAPTURE" for k, v in GT.items()))

    def test_hypothesis_needs_design(self):
        es = self.mutate("HYP-FX01", design=None)
        self.assertTrue(any("hypothesis needs design" in e for e in errors_for(es)))

    def test_links_must_resolve(self):
        es = self.mutate("MECH-FX01", links=[{"type": "tested_by", "to": "HYP-NOPE"}])
        self.assertTrue(any("link target HYP-NOPE" in e for e in errors_for(es)))
        es = self.mutate("MECH-FX01", links=[{"type": "likes", "to": "HYP-FX01"}])
        self.assertTrue(any("link type likes" in e for e in errors_for(es)))

    def test_experimental_strength_reserved(self):
        es = self.mutate("MECH-FX01", strength="experimental")
        self.assertTrue(any("reserved" in e for e in errors_for(es)))

    def test_approved_needs_owner(self):
        es = self.mutate("CHAR-FX01", review_status="approved")
        self.assertTrue(any("approved needs an owner" in e for e in errors_for(es)))

    def test_freshness(self):
        d = date(2026, 11, 25)
        self.assertEqual(kb.status_of(self.by["CULT-FX01"], d), "stale")
        self.assertEqual(kb.status_of(self.by["MECH-FX01"], d), "evergreen")
        self.assertEqual(kb.status_of({"review_by": "2026-12-01"}, d), "due")

    def test_sentiment_policy_checks(self):
        es = self.mutate("SENT-FX01", policy={**self.by["SENT-FX01"]["policy"], "source": "scraper"})
        self.assertTrue(any("policy.source" in e for e in errors_for(es)))
        es = self.mutate("SENT-FX01", policy={**self.by["SENT-FX01"]["policy"], "contains_comment_text": True, "text_expires_at": "2026-11-01"})
        self.assertTrue(any("past its expiry" in e for e in errors_for(es)))
        es = self.mutate("SENT-FX01", policy={**self.by["SENT-FX01"]["policy"], "cross_channel_aggregate": True, "derived_metrics_accepted": False})
        self.assertTrue(any("amendment" in e for e in errors_for(es)))
        es = self.mutate("SENT-FX01", items=[{"key": "x", "username": "someone"}])
        self.assertTrue(any("username" in e for e in errors_for(es)))


class QueryExportTests(unittest.TestCase):
    def test_find_filters_and_hides_inventory(self):
        es = fixture_entries()
        self.assertNotIn("INV-FX01", [e["id"] for e in kb.find(es)])
        self.assertIn("INV-FX01", [e["id"] for e in kb.find(es, bank="inventory")])
        self.assertEqual([e["id"] for e in kb.find(es, character="floppy")], ["CHAR-FX01"])
        self.assertEqual([e["id"] for e in kb.find(es, q="readable premise")], ["MECH-FX01"])

    def test_export_gate(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            out, n = kb.export(fixture_entries(), tmp / "snap")
            lines = [json.loads(l) for l in (out / "knowledge.jsonl").read_text(encoding="utf-8").splitlines()]
            ids = {l["id"] for l in lines}
            self.assertNotIn("INV-FX01", ids)
            sent = next(l for l in lines if l["id"] == "SENT-FX01")
            self.assertNotIn("items", sent)
            self.assertTrue(all(not k.startswith("_") for l in lines for k in l))
            self.assertTrue((out / "SNAPSHOT.md").exists())
        finally:
            shutil.rmtree(tmp)

    def test_render(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            idx = kb.render(fixture_entries(), tmp)
            self.assertIn("mechanisms", idx.read_text(encoding="utf-8"))
            self.assertTrue((tmp / "views" / "characters.md").exists())
        finally:
            shutil.rmtree(tmp)


class SentimentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["SLUGSHOT_KB_DIR"] = str(self.tmp / "knowledge")
        self._policy, self._yt = sentiment.policy, sentiment.YT_COMMENTS
        self.pol = {"manual_sources_enabled": True, "youtube_api_derived_metrics_accepted": False, "comment_text_retention_days": 30,
                    "manual_text_retention_days": 30, "manual_summary_retention_days": 365, "derived_retention_months": 36,
                    "raw_comment_export_to_ai": False}
        sentiment.policy = lambda: self.pol
        sentiment.YT_COMMENTS = self.tmp / "youtube_comments.csv"
        with open(sentiment.YT_COMMENTS, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["video_id", "comment_id", "text", "observed_at_utc", "order_param"])
            w.writeheader()
            w.writerow({"video_id": "vidA", "comment_id": "c1", "text": "not another one of these @someone", "observed_at_utc": "2026-11-25T10:00:00+00:00", "order_param": "relevance"})
            w.writerow({"video_id": "vidA", "comment_id": "c2", "text": "what game is this?", "observed_at_utc": "2026-11-25T10:00:00+00:00", "order_param": "relevance"})

    def tearDown(self):
        sentiment.policy, sentiment.YT_COMMENTS = self._policy, self._yt
        os.environ.pop("SLUGSHOT_KB_DIR", None)
        shutil.rmtree(self.tmp)

    def run_cli(self, *args):
        return sentiment.main(list(args))

    def test_youtube_gate(self):
        self.assertEqual(self.run_cli("packet", "--youtube", "--ids", "vidA", "--target", "t", "--selection", "s", "--name", "g"), 2)
        self.pol["youtube_api_derived_metrics_accepted"] = True
        self.assertEqual(self.run_cli("packet", "--youtube", "--ids", "vidA", "--target", "t", "--selection", "s", "--name", "g"), 0)

    def test_manual_scrub_join_and_prune(self):
        paste = self.tmp / "paste.txt"
        paste.write_text("Coolguy99: ya otro más @juan\nme muero jajaja\n", encoding="utf-8")
        self.assertEqual(self.run_cli("packet", "--paste", str(paste), "--platform", "tiktok", "--target", "fmt",
                                      "--selection", "first 2 visible", "--name", "m1"), 0)
        pk = sentiment.work_dir() / "packets" / "m1.jsonl"
        meta, items = sentiment.read_packet(pk)
        texts = " ".join(i["text"] for i in items)
        self.assertNotIn("Coolguy99", texts)
        self.assertNotIn("@juan", texts)
        cb = sentiment.codebook()
        codes = {c["code"]: "absent" for c in cb["codes"]}
        ann = []
        for i in items:
            a = {"key": i["key"], "codebook_version": cb["version"], "codes": dict(codes), "stance": "unclear", "target": ["format"],
                 "irony": "unclear", "language": "es", "coder": "claude"}
            ann.append(a)
        ann[0]["codes"]["FATIGUE"] = "present"
        af = pk.with_name("m1.annotations.jsonl")
        # missing fatigue_intensity -> invalid
        af.write_text("\n".join(json.dumps(a) for a in ann), encoding="utf-8")
        self.assertEqual(self.run_cli("join", str(pk), str(af)), 1)
        ann[0]["fatigue_intensity"] = "mild"
        bad = copy.deepcopy(ann)
        bad[1]["text"] = "copied"
        af.write_text("\n".join(json.dumps(a) for a in bad), encoding="utf-8")
        self.assertEqual(self.run_cli("join", str(pk), str(af)), 1)
        af.write_text("\n".join(json.dumps(a) for a in ann), encoding="utf-8")
        self.assertEqual(self.run_cli("join", str(pk), str(af)), 0)
        samples = kb.kb_dir() / "sentiment" / "samples.jsonl"
        entry = json.loads(samples.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(entry["denominators"], {"items": 2, "coded": 2, "uncoded": 0})
        self.assertNotIn("ya otro", json.dumps(entry))
        self.assertFalse(entry["policy"]["contains_comment_text"])
        errs = kb.validate(kb.load(), ledger_claims={}, gt=GT)[0]
        self.assertEqual(errs, [])
        # prune after text expiry removes the packet text but keeps the summary
        sentiment.cmd_prune(type("A", (), {"dry_run": False})(), today=date(2027, 1, 30))
        self.assertFalse(pk.exists())
        self.assertTrue(samples.read_text(encoding="utf-8").strip())


class DashboardHookTests(unittest.TestCase):
    def test_fixture_isolation_and_views(self):
        prev_fixture = os.environ.get("SLUGSHOT_DASH_FIXTURE")
        os.environ["SLUGSHOT_DASH_FIXTURE"] = "1"
        old = os.environ.pop("SLUGSHOT_KB_DIR", None)
        try:
            from dashboard import views
            d = views.knowledge({})
            self.assertTrue(d["dir"].endswith(os.path.join("fixtures", "knowledge")))
            self.assertTrue(all(r["id"].endswith(("FX01",)) for r in d["rows"]))
            self.assertIsNotNone(views.knowledge_entry("CHAR-FX01"))
            fam = views.hypotheses_for_experiments()
            self.assertIn("EXP-20261124-OPENER", fam)
            s = views.knowledge_summary()
            self.assertEqual(len(s["opportunities"]), 1)
            self.assertTrue(any(r["id"] == "CULT-FX01" for r in s["due"]))
        finally:
            if prev_fixture is None:
                os.environ.pop("SLUGSHOT_DASH_FIXTURE", None)
            else:
                os.environ["SLUGSHOT_DASH_FIXTURE"] = prev_fixture
            os.environ.pop("SLUGSHOT_KB_DIR", None)
            if old:
                os.environ["SLUGSHOT_KB_DIR"] = old


class PolicyConfigTests(unittest.TestCase):
    def test_settings_gate_defaults(self):
        s = json.loads((ROOT / "config" / "research" / "settings.json").read_text(encoding="utf-8"))["sentiment"]
        self.assertFalse(s["raw_comment_export_to_ai"])
        self.assertEqual(s["comment_text_retention_days"], 30)

    def test_codebook_shape(self):
        cb = sentiment.codebook()
        self.assertEqual(len(cb["codes"]), 11)
        self.assertIn("information_request", cb["item_fields"]["play_intent_subtype"]["values"])
        self.assertIn("mixed", cb["item_fields"]["stance"]["values"])


if __name__ == "__main__":
    unittest.main()
