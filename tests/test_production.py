"""Production pass (2026-11-25): dialogue parsing/alignment/captions, scene anchors and canon, decoder ranges.

  .venv\\Scripts\\python -m unittest tests.test_production
"""
import copy
import json
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

    def test_line_filters_trim_and_tempo(self):
        plain = dialogue.line_filters()
        self.assertFalse(any("silenceremove" in f or "tempo" in f for f in plain))
        f = dialogue.line_filters(tempo=1.25, trim=True)
        self.assertTrue(f[0].startswith("silenceremove") and "areverse" in f)
        self.assertIn("rubberband=tempo=1.2500:pitchq=quality:formant=preserved", f)
        self.assertTrue(f[-1].startswith("aresample"))

    def test_gemini_lines_get_the_characters_pitch_lift(self):
        # owner, 2026-11-27: Floppy is Gemini Puck lifted 3.5 semitones (cast.json gemini.pitch); Gemini lines used to
        # ignore the lift
        import gemini_tts
        calls, orig = [], (gemini_tts.speak, dialogue.ffmpeg)
        gemini_tts.speak = lambda text, voice, style, out: (Path(out).write_bytes(b"x"), 1.0)[1]
        dialogue.ffmpeg = lambda *a: calls.append(a)
        try:
            with tempfile.TemporaryDirectory() as d:
                (Path(d) / "lines").mkdir()
                lines = [{"speaker": "FLOPPY", "text": "Mm.", "direction": "", "gap_after": 0},
                         {"speaker": "NARRATOR", "text": "Hi.", "direction": "", "gap_after": 0}]
                dialogue.perform(lines, "gemini", Path(d), only={1, 2})
        finally:
            gemini_tts.speak, dialogue.ffmpeg = orig
        chains = [a[a.index("-af") + 1] for a in calls]
        self.assertIn(f"rubberband=pitch={2 ** (3.5 / 12):.5f}", chains[0])
        self.assertNotIn("rubberband=pitch", chains[1])

    def test_music_fades_follow_energy(self):
        import music_beds
        beds = [{"src": "assets/music/M2a-cavern-sneak-chill-nature-subtle.wav", "at": 0},
                {"src": "assets/music/S06-showdown.mp3", "at": 10},
                {"src": "assets/music/S04-sad-nature-subtle.wav", "at": 20},
                {"src": "assets/music/S10-awkward.mp3", "at": 30}]
        f = music_beds.plan_fades(beds)
        self.assertEqual(f[0][1], music_beds.UP_FADE)       # calm -> showdown: sharp
        self.assertEqual(f[1][1], music_beds.DOWN_OUT)      # showdown -> sad: the old bed sinks away slowly
        self.assertEqual(f[2][0], music_beds.DOWN_IN)
        self.assertEqual(f[2][1], music_beds.LEVEL_FADE)    # sad -> awkward: same energy, soft crossfade

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


class Ambient(unittest.TestCase):
    """Background life (tools/ambient.py): seeded, valid, and out of the main characters' way."""

    def spec(self):
        return {"id": "amb_t", "truth": {"mode": "staged_fiction", "gameplay_mechanics": "none", "match_outcome": "n/a",
                                         "label": "Fictional story"},
                "set": {"kind": "place", "origin": [120, 0, 10], "yaw": 0},
                "marks": {"hero": [0, 0, 0, 0]},
                "actors": {"kai": {"kind": "human", "human": "kai", "mark": "hero"}},
                "shots": [{"preset": "orbit_reveal", "duration": 12, "target": "hero", "from": 0, "to": 40}],
                "ambient": {"seed": 3, "clear": ["hero"], "clear_radius": 6, "avoid": [[4, 4]],
                            "residents": {"near": [0, 0, 0], "radius": 40, "max": 4},
                            "groups": [{"zone": [-12, -12, 12, 12], "people": 5, "slugs": 2,
                                        "activities": ["stroll", "chat", "chat", "watch"], "focus": "hero"}]}}

    def test_same_seed_same_crowd(self):
        a, b = self.spec(), self.spec()
        self.assertEqual(scene.validate(a), [])
        scene.validate(b)
        self.assertEqual(a, b)
        self.assertNotIn("ambient", a)
        self.assertGreaterEqual(sum(n.startswith("amb_p") for n in a["actors"]), 5)

    def test_extras_keep_clear_of_heroes_and_avoid_spots(self):
        import math
        s = self.spec()
        scene.validate(s)
        used = {a["mark"] for n, a in s["actors"].items() if n.startswith("amb_p")}
        used |= {b["mark"] for b in s["timeline"] if b.get("action") == "move_to" and b["actor"].startswith("amb_p")}
        for m in used:
            x, _, z = s["marks"][m][:3]
            self.assertGreaterEqual(math.hypot(x, z), 6 - 2.0, m)  # chat partners stand 1.9 studs off their (clear) centre
            self.assertGreaterEqual(math.hypot(x - 4, z - 4), 2.5 - 2.0, m)

    def test_extras_never_wear_cast_outfits(self):
        s = self.spec()
        scene.validate(s)
        cast = {scene.LIBRARY["humans"][k]["shirt"] for k in ("kai", "raf", "mira", "juno")}
        for n, a in s["actors"].items():
            if n.startswith("amb_p"):
                self.assertNotIn(a["look"].get("shirt"), cast)

    def test_residents_come_from_the_grove_library(self):
        s = self.spec()
        scene.validate(s)
        grove = {g["species"] for g in json.loads((ROOT / "roblox-native/library/grove.json").read_text(encoding="utf-8"))["slugs"]}
        residents = [a for n, a in s["actors"].items() if n.startswith("amb_s") and "scale" in a and a["species"] in grove]
        self.assertTrue(residents)


class Ambient2(unittest.TestCase):
    """Owner review of the first living-environments demo (2026-11-27): cracks, racing slugs, plain bodies, reactions."""

    def spec(self, **amb):
        s = {"id": "amb_t2", "truth": {"mode": "staged_fiction", "gameplay_mechanics": "none", "match_outcome": "n/a",
                                        "label": "Fictional story"},
             "set": {"kind": "place", "origin": [19, 0, 20], "yaw": 0},
             "marks": {"kai_h": [-15, 0, -18.5, 0], "raf_h": [-10, 0, -20.5, 0]},
             "actors": {"kai": {"kind": "human", "human": "kai", "mark": "kai_h"},
                        "raf": {"kind": "human", "human": "raf", "mark": "raf_h"}},
             "shots": [{"preset": "close_up", "duration": 14, "target": "raf"}],
             "ambient": {"seed": 4, "clear": ["kai_h", "raf_h"],
                         "groups": [{"zone": [-40, -46, 6, -24], "people": 10, "slugs": 4,
                                     "activities": ["stroll", "chat", "chat", "watch"], "focus": "kai_h"}], **amb}}
        self.assertEqual(scene.validate(s), [])
        return s

    def test_nobody_stands_or_walks_on_a_crack(self):
        import floormap
        s = self.spec()
        o = s["set"]["origin"]
        for n, a in s["actors"].items():
            if n.startswith("amb_"):
                x, _, z = s["marks"][a["mark"]][:3]
                self.assertTrue(floormap.standable(o[0] + x, o[2] + z), n)
        for b in s["timeline"]:
            if b.get("action") == "move_to":
                x, _, z = s["marks"][b["mark"]][:3]
                self.assertTrue(floormap.standable(o[0] + x, o[2] + z), b)

    def test_floor_map_knows_the_plaza_cracks(self):
        import floormap
        self.assertFalse(floormap.standable(-10.0, 10.0))   # the crack measured at world (-10, 10): 2.45 deep
        self.assertFalse(floormap.standable(14.0, 12.0))    # the pit by the old duel spot
        self.assertTrue(floormap.standable(7.0, 1.0))       # open plaza floor (spec -12, -19)

    def test_slugs_hop_at_one_even_stride(self):
        import math
        s = self.spec()
        pos = {n: s["marks"][a["mark"]] for n, a in s["actors"].items() if a["kind"] == "slug"}
        for b in sorted(s["timeline"], key=lambda b: b["time"]):
            if b.get("gait") == "hop":
                to = s["marks"][b["mark"]]
                d = math.hypot(to[0] - pos[b["actor"]][0], to[2] - pos[b["actor"]][2])
                self.assertLessEqual(d / b["hops"], 2.4, b)
                pos[b["actor"]] = to

    def test_every_extra_is_dressed(self):
        s = self.spec()
        wardrobe = scene.LIBRARY["extras_wardrobe"]
        for n, a in s["actors"].items():
            if n.startswith("amb_p"):
                self.assertIn(a["look"]["shirt"], wardrobe["shirts"])
                self.assertIn(a["look"]["pants"], wardrobe["pants"])
                self.assertTrue(a["look"]["hair"])
                self.assertNotIn("blaster", a)

    def test_reaction_interrupts_and_staggers(self):
        s = self.spec(reactions=[{"at": 6.0, "kind": "cheer", "focus": "raf", "hold": 2.0}])
        people = [n for n in s["actors"] if n.startswith("amb_p")]
        firsts = []
        for n in people:
            mine = [b for b in s["timeline"] if b.get("actor") == n]
            turn = [b for b in mine if b["action"] == "face" and b.get("target") == "raf"]
            self.assertTrue(turn, n)
            t = turn[0]["time"]
            firsts.append(t)
            own = [b for b in mine if t - 0.04 < b["time"] < t + 2.0 and b["action"] == "move_to"]
            self.assertEqual(own, [], n)
        self.assertGreater(max(firsts) - min(firsts), 0.05)   # not all on the same frame

    def test_scatter_runs_everyone_away(self):
        import math
        s = self.spec(reactions=[{"at": 8.0, "kind": "scatter", "focus": "kai_h", "who": "people"}])
        kai = s["marks"]["kai_h"]
        for n in (n for n in s["actors"] if n.startswith("amb_p")):
            runs = [b for b in s["timeline"] if b.get("actor") == n and b.get("gait") == "run"]
            if not runs:
                continue
            start = s["marks"][s["actors"][n]["mark"]]
            end = s["marks"][runs[-1]["mark"]]
            self.assertGreater(math.hypot(end[0] - kai[0], end[2] - kai[2]), math.hypot(start[0] - kai[0], start[2] - kai[2]) - 3)

    def test_ring_leaves_the_camera_side_open(self):
        import math
        s = self.spec()
        ring = {"id": "amb_r", "truth": s["truth"], "set": s["set"], "marks": {"c": [-12, 0, -19, 0]}, "actors": {},
                "shots": [{"preset": "orbit_reveal", "duration": 6, "target": "c", "from": 0, "to": 10}],
                "ambient": {"seed": 2, "groups": [{"activities": ["ring"], "focus": "c", "people": 12, "radius": 8.5,
                                                   "open": [135, 205]}]}}
        self.assertEqual(scene.validate(ring), [])
        c = ring["marks"]["c"]
        for n, a in ring["actors"].items():
            m = ring["marks"][a["mark"]]
            ang = math.degrees(math.atan2(m[0] - c[0], m[2] - c[2])) % 360
            self.assertFalse(135 <= ang <= 205, (n, ang))  # demo uses a wider [120, 220]


class Ambient3(unittest.TestCase):
    """Owner review 2 (2026-11-27): crowds not cramped, framing not too tight, one consistent crowd reaction."""

    def spec(self, **amb):
        s = Ambient2.spec(self, **amb)
        return s

    def test_nobody_stands_on_top_of_anyone(self):
        import math
        import ambient
        s = self.spec()
        spots = [(n, s["marks"][a["mark"]]) for n, a in s["actors"].items() if n.startswith("amb_")]
        for i, (n, p) in enumerate(spots):
            for m, q in spots[i + 1:]:
                d = math.hypot(p[0] - q[0], p[2] - q[2])
                kinds = {s["actors"][n]["kind"], s["actors"][m]["kind"]}
                need = ambient.SLUG_GAP if "slug" in kinds else 3.7   # chat partners stand 3.8 apart
                self.assertGreaterEqual(d, need - 0.01, (n, m, round(d, 2)))

    def test_shock_lands_together_with_matching_faces(self):
        s = self.spec(reactions=[{"at": 6.0, "kind": "gasp", "focus": "raf"}])
        people = [n for n in s["actors"] if n.startswith("amb_p")]
        times, faces = [], []
        for n in people:
            turn = [b for b in s["timeline"] if b.get("actor") == n and b["action"] == "face" and b.get("target") == "raf"]
            face = [b for b in s["timeline"] if b.get("actor") == n and b["action"] == "express" and b["time"] >= 6.0]
            times.append(turn[0]["time"])
            faces.append(face[0]["set"])
        self.assertLess(max(times) - min(times), 0.45)
        self.assertTrue(all(f == faces[0] for f in faces))
        self.assertGreater(faces[0].get("open", 0), 0.5)

    def test_reaction_holds_until_its_beat_ends(self):
        s = self.spec(reactions=[{"at": 5.0, "kind": "gasp", "focus": "raf", "until": 11.0}])
        n = next(n for n in s["actors"] if n.startswith("amb_p"))
        own = [b for b in s["timeline"] if b.get("actor") == n and 5.0 < b["time"] < 10.9
               and b["action"] in ("gesture", "move_to") and b.get("move") not in ("disbelief", "hands_up")]
        self.assertEqual(own, [])

    def test_framing_flags_tight_shots_for_what_happens_in_them(self):
        s = self.spec(reactions=[{"at": 6.0, "kind": "cheer", "focus": "raf"}])
        s["timeline"].append({"time": 3.0, "actor": "raf", "action": "aim", "target": "kai", "duration": 1.0})
        s["actors"]["raf"]["blaster"] = True
        s["shots"] = [{"preset": "close_up", "duration": 14, "target": "raf", "size": 1.1}]
        warns = " | ".join(scene.framing_warnings(s))
        self.assertIn("crowd's cheer", warns)
        self.assertIn("aim", warns)
        s["shots"] = [{"preset": "medium", "duration": 14, "target": "raf", "size": 2.6}]
        self.assertEqual(scene.framing_warnings(s), [])
        s["shots"] = [{"preset": "close_up", "duration": 14, "target": "raf", "size": 1.1, "tight": "the stare-down"}]
        self.assertEqual(scene.framing_warnings(s), [])


class Locations(unittest.TestCase):
    """Temporary locations (2026-11-27): a scene set in one gets its origin, named spots and pieces."""

    def test_location_set_brings_origin_marks_and_pieces(self):
        s = {"id": "loc_t", "truth": {"mode": "staged_fiction", "gameplay_mechanics": "none", "match_outcome": "n/a",
                                       "label": "Fictional story"},
             "set": {"kind": "location", "location": "bedroom"}, "marks": {},
             "actors": {"kai": {"kind": "human", "human": "kai", "mark": "by_bed"}},
             "shots": [{"preset": "medium", "duration": 3, "target": "kai"}], "timeline": []}
        self.assertEqual(scene.validate(s), [])
        self.assertEqual(s["set"]["origin"], [0, 0, 9000])
        self.assertIn("by_bed", s["marks"])
        self.assertTrue(any(p.get("mesh") for p in s["set"]["_location"]["pieces"]))

    def test_unknown_location_is_an_error(self):
        s = {"id": "loc_x", "truth": {}, "set": {"kind": "location", "location": "moon_base"}, "marks": {}, "shots": []}
        self.assertTrue(any("moon_base" in e for e in scene.validate(s)))

    def test_every_location_file_is_well_formed(self):
        for p in sorted((ROOT / "roblox-native/library/locations").glob("*.json")):
            loc = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(loc["name"], p.stem)
            self.assertEqual(len(loc["origin"]), 3)
            for piece in loc["pieces"]:
                self.assertEqual(sum(k in piece for k in ("box", "mesh", "kit", "light", "clone")), 1, piece)


class ActingAndStories(unittest.TestCase):
    """Owner critiques (2026-11-27): mannerisms, listening, interruptions, background vignettes, interactions, sound."""

    def scene(self, timeline=None, **extra):
        return {"id": "act_t", "truth": {"mode": "staged_fiction", "gameplay_mechanics": "none", "match_outcome": "n/a",
                                         "label": "Fictional story"},
                "set": {"kind": "place", "origin": [19, 0, 20], "yaw": 0},
                "marks": {"kai_h": [-15, 0, -18.5, 0], "mira_h": [-10, 0, -20.5, 0]},
                "actors": {"kai": {"kind": "human", "human": "kai", "mark": "kai_h"},
                           "mira": {"kind": "human", "human": "mira", "mark": "mira_h"}},
                "shots": [{"preset": "medium", "duration": 16, "target": "kai"}],
                "timeline": timeline or [], **extra}

    def test_mannerisms_fill_gaps_but_never_cover_authored_beats(self):
        authored = {"time": 5.0, "actor": "kai", "action": "gesture", "move": "wave", "mask": "upper", "duration": 2.0}
        s = self.scene([dict(authored)])
        self.assertEqual(scene.validate(s), [])
        kai = [b for b in s["timeline"] if b.get("actor") == "kai" and b["action"] == "gesture"]
        self.assertGreater(len(kai), 1)
        for b in kai:
            if b is not None and b.get("move") != "wave":
                end = b["time"] + float(b.get("duration") or 1.6)
                self.assertFalse(b["time"] < 7.0 and end > 5.0, b)
        mira = [b for b in s["timeline"] if b.get("actor") == "mira" and b.get("move") == "arms_crossed"]
        self.assertTrue(mira)   # Mira rests with her arms folded

    def test_acting_is_seeded_and_can_be_turned_off(self):
        a, b = self.scene(), self.scene()
        scene.validate(a)
        scene.validate(b)
        self.assertEqual(a["timeline"], b["timeline"])
        c = self.scene(acting=False)
        scene.validate(c)
        self.assertEqual(c["timeline"], [])

    def test_listeners_nod_and_interruptions_cut_off(self):
        import acting
        s = self.scene()
        dialogue = {"lines": [{"n": 1, "actor": "kai", "start": 1.0, "end": 5.0}, {"n": 2, "actor": "mira", "start": 4.6, "end": 7.0}]}
        words = [{"text": " absolutely", "startMs": 2000, "endMs": 2600}, {"text": " no", "startMs": 3000, "endMs": 3200}]
        acting.expand(s, 16, dialogue, words)
        kai = [b for b in s["timeline"] if b.get("actor") == "kai"]
        self.assertTrue(any(b["action"] == "express" and b["set"].get("open") and abs(b["time"] - 4.6) < 0.01 for b in kai))
        self.assertTrue(any(b["action"] == "look" and b.get("target") == "mira" for b in kai))

    def test_vignettes_tell_stories_and_hand_offs_are_in_reach(self):
        import math
        s = self.scene()
        s["ambient"] = {"seed": 5, "clear": ["kai_h", "mira_h"],
                        "groups": [{"zone": [-40, -46, -12, -24], "people": 7, "activities": ["show_off", "trade", "training", "runaway"]}]}
        self.assertEqual(scene.validate(s), [])
        holds = [b for b in s["timeline"] if b.get("action") == "hold"]
        self.assertGreaterEqual(len(holds), 2)
        for h in holds:
            carried = [o for o in holds if o is not h and o["item"] == h["item"] and o["time"] < h["time"] < o["time"] + o["duration"]]
            if carried:
                continue   # a hand-off: the slug is in the giver's hands at the meeting point
            holder = s["marks"][s["actors"][h["actor"]]["mark"]]
            pet = s["marks"][s["actors"][h["item"]]["mark"]]
            moved = [b for b in s["timeline"] if b.get("actor") == h["actor"] and b.get("action") == "move_to" and b["time"] < h["time"]]
            if not moved:
                self.assertLess(math.hypot(holder[0] - pet[0], holder[2] - pet[2]), 3.5, h)

    def test_far_pick_up_is_flagged(self):
        s = self.scene([{"time": 2.0, "actor": "kai", "action": "hold", "item": "pet", "duration": 3}])
        s["marks"]["far"] = [10, 0, 10, 0]
        s["actors"]["pet"] = {"kind": "slug", "species": "Floppy", "mark": "far"}
        scene.validate(s)
        self.assertTrue(any("picks up pet" in w for w in scene.interaction_warnings(s)))

    def test_sound_follows_the_picture(self):
        import numpy as np
        sys.path.insert(0, str(ROOT / "scripts"))
        import soundscape
        cam = (np.array([0.0, 2, 0]), np.array([0.0, 0, -1]))
        front, _ = soundscape.seen(cam, np.array([0.0, 2, -8]))
        behind, _ = soundscape.seen(cam, np.array([0.0, 2, 8]))
        _, pan_right = soundscape.seen(cam, np.array([6.0, 2, -6]))
        self.assertGreater(front, behind)
        self.assertGreater(pan_right, 0.3)
        self.assertEqual(soundscape.place_kind({"set": {"kind": "location", "location": "market"}}), "market")
        self.assertEqual(soundscape.place_kind({"set": {"kind": "place", "origin": [120, 0, 10]}}), "grove")


class ExportsKeepLatest(unittest.TestCase):
    """Owner, 2026-11-27: the Content page keeps only the latest version of each video as videos pile up."""

    def setUp(self):
        import batch
        self.batch, self.saved = batch, batch.ROOT
        self.tmp = tempfile.TemporaryDirectory()
        batch.ROOT = Path(self.tmp.name)
        self.ex = batch.ROOT / "exports"
        self.ex.mkdir()

    def tearDown(self):
        self.batch.ROOT = self.saved
        self.tmp.cleanup()

    def make(self, name, language=None):
        (self.ex / f"{name}.mp4").write_bytes(b"x")
        (self.ex / f"{name}.qc.json").write_text("{}")
        if language:
            (self.ex / f"{name}.meta.json").write_text(json.dumps({"language": language}))

    def test_older_versions_move_to_the_archive_and_numbers_keep_climbing(self):
        self.make("SS_20261126_WORLD_Pilot_Ep1_V01_MASTER", "en")
        self.make("SS_20261127_WORLD_Pilot_Ep1_V01_MASTER", "en")
        self.make("SS_20261127_WORLD_Pilot_Ep1es_V01_MASTER", "es")       # another hook
        self.make("SS_20261127_WORLD_PilotTwo_Ep1_V01_MASTER", "en")      # another concept
        self.make("SS_20261127_WORLD_Pilot_Ep1_V02_MASTER", "en")
        moved = self.batch.archive_older(self.ex / "SS_20261127_WORLD_Pilot_Ep1_V02_MASTER.mp4", "en")
        self.assertEqual(sorted(moved), ["SS_20261126_WORLD_Pilot_Ep1_V01_MASTER.mp4", "SS_20261127_WORLD_Pilot_Ep1_V01_MASTER.mp4"])
        left = sorted(p.name for p in self.ex.glob("*.mp4"))
        self.assertEqual(left, ["SS_20261127_WORLD_PilotTwo_Ep1_V01_MASTER.mp4", "SS_20261127_WORLD_Pilot_Ep1_V02_MASTER.mp4",
                                "SS_20261127_WORLD_Pilot_Ep1es_V01_MASTER.mp4"])
        self.assertTrue((self.ex / "archive" / "SS_20261127_WORLD_Pilot_Ep1_V01_MASTER.qc.json").exists())
        # an archived V01 is never reused
        (self.ex / "SS_20261127_WORLD_Pilot_Ep1_V02_MASTER.mp4").replace(self.ex / "archive" / "SS_20261127_WORLD_Pilot_Ep1_V02_MASTER.mp4")
        self.assertEqual(self.batch.next_name("20261127", "world", "Pilot", "Ep1"), "SS_20261127_WORLD_Pilot_Ep1_V03_MASTER")

    def test_other_languages_and_renders_outside_exports_are_left_alone(self):
        self.make("SS_20261127_WORLD_Pilot_Ep1_V01_MASTER", "es")
        self.make("SS_20261127_WORLD_Pilot_Ep1_V02_MASTER", "en")
        self.assertEqual(self.batch.archive_older(self.ex / "SS_20261127_WORLD_Pilot_Ep1_V02_MASTER.mp4", "en"), [])
        self.assertEqual(self.batch.archive_older(Path(self.tmp.name) / "SS_20261127_WORLD_Pilot_Ep1_V03_MASTER.mp4", "es"), [])
        self.assertEqual(len(list(self.ex.glob("*.mp4"))), 2)
