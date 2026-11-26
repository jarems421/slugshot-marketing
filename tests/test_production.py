"""Production pass (2026-11-25): dialogue parsing/alignment/captions, scene anchors and canon, decoder ranges.

  .venv\\Scripts\\python -m unittest tests.test_production
"""
import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "roblox-native" / "tools"))

import assemble  # noqa: E402
import dialogue  # noqa: E402
import scene  # noqa: E402
import take  # noqa: E402


def words(*pairs):
    return [{"word": f" {w}", "start": s, "end": e} for w, s, e in pairs]


DIALOGUE = {"lines": [{"n": 1, "start": 0.0, "end": 1.2, "actor": "a"}, {"n": 2, "start": 1.7, "end": 2.5, "actor": "b"}],
            "duration": 2.8}

SPEC = {
    "id": "t", "truth": {"mode": "staged_fiction", "source": "staged_runtime", "gameplay_mechanics": "none",
                         "match_outcome": "n/a", "label": "Fictional skit"},
    "set": {"kind": "place", "origin": [0, 0, 0]},
    "marks": {"m1": [0, 0, 0, 0], "m2": [2, 0, 0, 0]},
    "actors": {"a": {"kind": "slug", "species": "Floppy", "mark": "m1"},
               "b": {"kind": "slug", "species": "Rammstone", "mark": "m2"}},
    "shots": [{"preset": "close_up", "target": "a", "until": "L1.end+0.3"},
              {"preset": "over_shoulder", "from": "a", "target": "b", "until": "L2.end+0.5"}],
    "timeline": [{"time": "L2.start-0.1", "actor": "b", "action": "express", "set": {"angry": 0.6}}],
}


class Dialogue(unittest.TestCase):
    def test_parse_gaps_and_overlaps(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("# c\nFLOPPY (flat): Yep.\n[beat 1.1]\nRAMMSTONE: Hm.\n[overlap 0.2]\nFLOPPY: What.\n")
        lines = dialogue.parse(f.name)
        self.assertEqual([ln["speaker"] for ln in lines], ["FLOPPY", "RAMMSTONE", "FLOPPY"])
        self.assertEqual(lines[0]["direction"], "flat")
        self.assertEqual(lines[0]["gap_after"], 1.1)
        self.assertEqual(lines[1]["gap_after"], -0.2)

    def test_unknown_speaker_rejected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("NOBODY: hi\n")
        with self.assertRaises(SystemExit):
            dialogue.parse(f.name)

    def test_align_uses_script_words_and_flags_deviations(self):
        out, dev = dialogue.align("I heard you do seven damage.", words(
            ("I", 0, .1), ("heard", .1, .3), ("you", .3, .4), ("do", .4, .5), ("7", .5, .7), ("damage.", .7, 1.0)), 2.0)
        self.assertEqual([w["text"] for w in out], "I heard you do seven damage.".split())
        self.assertEqual(dev, [])  # "7" == "seven"
        self.assertAlmostEqual(out[4]["start"], 2.5)
        out, dev = dialogue.align("Per shot.", words(("Harshad", 0, .5)), 0)
        self.assertEqual([w["text"] for w in out], ["Per", "shot."])  # captions keep the script
        self.assertTrue(dev)
        _, dev = dialogue.align("That's not a lot.", words(("Heh,", 0, .2), ("That's", .3, .5), ("not", .5, .6),
                                                          ("a", .6, .7), ("lot.", .7, .9)), 0)
        self.assertIn("extra: 'Heh,'", dev)

    def test_captions_keep_short_lines_whole(self):
        w = [{"text": t, "start": i, "end": i + .5} for i, t in enumerate("I never said it was.".split())]
        self.assertEqual(len(list(dialogue.caption_groups(w))), 1)
        long = [{"text": t, "start": i, "end": i + .5} for i, t in enumerate("one two three, four five six seven eight nine".split())]
        groups = list(dialogue.caption_groups(long))
        self.assertGreater(len(groups), 1)
        self.assertTrue(all(len(g) >= 2 for g in groups))

    def test_gemini_groups_keep_directions_and_overlaps(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("NARRATOR (calm): One.\nNARRATOR: Two.\nNARRATOR: Three.\nNARRATOR (amused): Four.\n"
                    "FLOPPY: Five.\n[overlap 0.2]\nFLOPPY: Six.\nNARRATOR: Seven.\n")
        groups = dialogue.gemini_groups(dialogue.parse(f.name))
        # directions never merge or spread; an [overlap] (interruption) stays its own request
        self.assertEqual(groups, [[0], [1, 2], [3], [4], [5], [6]])

    def test_split_points_cut_in_the_pause(self):
        w = [{"text": t, "start": s, "end": e} for t, s, e in
             (("Some", 0, .2), ("pick", .2, .4), ("fire.", .4, .7), ("Some", 1.1, 1.3), ("pick", 1.3, 1.5), ("water.", 1.5, 1.9))]
        self.assertEqual(dialogue.split_points(w, [3, 3]), [0.9])
        w[3]["start"] = 0.72  # no audible pause at the boundary: refuse to cut (caller performs line by line)
        self.assertIsNone(dialogue.split_points(w, [3, 3]))

    def test_mouth_envelope(self):
        rate = dialogue.RATE
        t = np.arange(rate) / rate
        pcm = (np.sin(2 * np.pi * 200 * t) * (t > 0.5)).astype(np.float32)
        env = dialogue.mouth_envelope(pcm)
        self.assertEqual(len(env), 30)
        self.assertTrue(all(0 <= v <= 1 for v in env))
        self.assertLess(max(env[:12]), 0.05)
        self.assertGreater(max(env[18:]), 0.8)


class Scenes(unittest.TestCase):
    def test_anchors_resolve(self):
        spec = copy.deepcopy(SPEC)
        self.assertEqual(scene.resolve_anchors(spec, DIALOGUE), [])
        self.assertEqual(spec["shots"][0]["duration"], 1.5)
        self.assertEqual(spec["shots"][1]["duration"], 1.5)
        self.assertEqual(spec["timeline"][0]["time"], 1.6)

    def test_bad_anchor(self):
        spec = copy.deepcopy(SPEC)
        spec["timeline"][0]["time"] = "L9"
        self.assertTrue(scene.resolve_anchors(spec, DIALOGUE))

    def test_slug_species_sets_canon_identity(self):
        spec = copy.deepcopy(SPEC)
        scene.resolve_anchors(spec, DIALOGUE)
        self.assertEqual(scene.validate(spec), [])
        spec["timeline"].append({"time": 0.5, "actor": "a", "action": "transform"})
        self.assertTrue(any("never transforms" in e for e in scene.validate(spec)))

    def test_slug_needs_known_species_and_channels(self):
        spec = copy.deepcopy(SPEC)
        scene.resolve_anchors(spec, DIALOGUE)
        spec["actors"]["b"]["species"] = "Slinger"
        spec["timeline"].append({"time": 0.5, "actor": "a", "action": "express", "set": {"wink": 1}})
        errs = scene.validate(spec)
        self.assertTrue(any("species" in e for e in errs))
        self.assertTrue(any("express" in e for e in errs))

    def test_assemble_anchor(self):
        d = {"lines": [{"n": 6, "start": 8.0, "end": 9.5}]}
        self.assertEqual(assemble.when("L6.end+0.55", d), 10.05)
        self.assertEqual(assemble.when(1.5, None), 1.5)
        with self.assertRaises(SystemExit):
            assemble.when("L6", None)


class Audience(unittest.TestCase):
    """Dashboard Content cards say who a video is for (owner request, 2026-11-25)."""

    ACCOUNTS = {a["account_id"]: a for a in [
        {"account_id": "yt-en", "platform": "youtube", "language": "en", "handle": "@ronin_jt", "active": 1},
        {"account_id": "tt-en", "platform": "tiktok", "language": "en", "handle": ".roni_jt", "active": 1},
        {"account_id": "ig-es", "platform": "instagram", "language": "es", "handle": "", "active": 0},
        {"account_id": "tt-es", "platform": "tiktok", "language": "es", "handle": "es.roni_jt", "active": 1},
        {"account_id": "rbx", "platform": "roblox", "language": "en", "handle": "", "active": 1}]}

    def test_language_counts_active_social_accounts(self):
        from dashboard.analytics import _audience
        it = {"jobs": [], "posted_on": [], "language": "en"}
        self.assertEqual(_audience(it, self.ACCOUNTS), "For: all English accounts (2)")
        self.assertEqual(_audience({**it, "language": "es"}, self.ACCOUNTS), "For: all Spanish accounts (1)")
        self.assertEqual(_audience({**it, "language": ""}, self.ACCOUNTS), "For: language not set")

    def test_named_accounts_win(self):
        from dashboard.analytics import _audience
        it = {"jobs": [{"account_id": "tt-es"}], "posted_on": [{"account_id": "yt-en"}], "language": "en"}
        self.assertEqual(_audience(it, self.ACCOUNTS), "For: es.roni_jt, @ronin_jt")


class Decoder(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual(take.ranges([1, 2, 3, 7, 9, 10]), "1-3, 7, 9-10")
        self.assertEqual(take.ranges([]), "")


if __name__ == "__main__":
    unittest.main()


class GeminiTTS(unittest.TestCase):
    """Spending guard and response parsing for scripts/gemini_tts.py (offline)."""

    def test_finds_audio_in_rest_and_sdk_shapes(self):
        import gemini_tts
        self.assertEqual(gemini_tts._find_audio({"steps": [{"content": [{"type": "text"}, {"type": "audio", "data": "QQ=="}]}]}), "QQ==")
        self.assertEqual(gemini_tts._find_audio({"output_audio": {"data": "Qg=="}}), "Qg==")
        self.assertIsNone(gemini_tts._find_audio({"steps": []}))

    def test_cap_refuses_before_calling(self):
        import gemini_tts
        b = {"model": "m", "project_billing": True, "monthly_cap_usd": 0.0, "usd_per_m_input": 0.5, "usd_per_m_audio": 9.0}
        orig_budget, orig_key = gemini_tts.budget, gemini_tts.env_value
        gemini_tts.budget, gemini_tts.env_value = (lambda: b), (lambda name: "test-key")
        try:
            with self.assertRaises(SystemExit) as e:
                gemini_tts.speak("Hello there.", "Puck", "", Path(tempfile.gettempdir()) / "x.wav")
            self.assertIn("cap", str(e.exception))
        finally:
            gemini_tts.budget, gemini_tts.env_value = orig_budget, orig_key

    def test_estimate_scale(self):
        import gemini_tts
        b = {"usd_per_m_input": 0.5, "usd_per_m_audio": 9.0}
        self.assertLess(gemini_tts.estimate("x" * 400, 30, b), 0.01)  # a 30 s take costs under a cent

    def test_style_adds_shared_delivery(self):
        import gemini_tts
        s = gemini_tts.style_for({"style": "cool"}, "dry")
        self.assertTrue(s.startswith("dry. cool. "))
        self.assertIn("storytime", s)

    def test_cast_voices_are_not_rejected(self):
        import json
        cast = json.loads((ROOT / "config" / "cast.json").read_text(encoding="utf-8"))["characters"]
        for name, c in cast.items():
            g = c.get("gemini") or {}
            self.assertNotIn(g.get("voice"), g.get("rejected", {}), name)


class Review2(unittest.TestCase):
    """Owner review 2026-11-25 (evening): BOM scripts, window-recording calibration."""

    def test_script_with_bom_parses(self):
        p = Path(tempfile.gettempdir()) / "ss_bom_script.txt"
        p.write_text("# note\nFLOPPY (slow): Five more minutes.\n", encoding="utf-8-sig")
        lines = dialogue.parse(p)
        self.assertEqual(lines[0]["speaker"], "FLOPPY")

    def test_calibrate_finds_viewport_card(self):
        import shutil
        import subprocess
        if os.environ.get("SLUGSHOT_TEST_SKIP_MEDIA"):
            self.skipTest("offline runner skips FFmpeg calibration, which generates a test video")
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not on PATH")
        v = Path(tempfile.gettempdir()) / "ss_cal.mkv"
        # a 320x200 grey window with a magenta 200x120 viewport at (60, 40) from frame 3, VFR like gfxcapture
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=gray:s=320x200:r=30:d=0.4",
                        "-vf", "drawbox=x=60:y=40:w=200:h=120:color=0xFF00FF:t=fill:enable='gte(n,3)'",
                        "-c:v", "libx264", "-crf", "0", "-pix_fmt", "yuv444p", str(v)], check=True)
        x, y, w, h = take.calibrate(v)
        self.assertLessEqual(abs(x - 60) + abs(y - 40), 2)
        self.assertLessEqual(abs(w - 200) + abs(h - 120), 4)


class ContentOrder(unittest.TestCase):
    def test_newest_version_first(self):
        vs = [{"language": "en", "version": "V01", "made_at": "a"}, {"language": "en", "version": "V02", "made_at": "b"}]
        vs.sort(key=lambda v: (v["version"], v["made_at"] or ""), reverse=True)
        vs.sort(key=lambda v: v["language"])
        self.assertEqual(vs[0]["version"], "V02")
