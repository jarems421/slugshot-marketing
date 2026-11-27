"""Offline regression coverage for the TikTok genre workflow."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "research" / "tiktok-genre")
)

import apify
import build
import process
import run
import savetop
import speed
import ss_subtitles
from genre_common import preferred_track, read_csv, write_json
from measure import measure
from whisper_run import usable_segments


class CollectionTests(unittest.TestCase):
    def test_paginated_receipt_and_charge_cap(self):
        page = [{"id": str(i)} for i in range(500)]
        started = {"id": "run-1", "status": "RUNNING"}
        finished = {
            "id": "run-1",
            "status": "SUCCEEDED",
            "defaultDatasetId": "data-1",
            "usageTotalUsd": 0.24,
        }
        payload = {"searchQueries": ["in my world Roblox"]}
        transport = Mock(
            side_effect=[{"data": started}, {"data": finished}, page, [{"id": "last"}]]
        )

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(run, "req", transport),
            patch.object(run.time, "sleep"),
            patch.dict(run.os.environ, {"APIFY_ACTOR": "clockworks~tiktok-scraper"}),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            output, items = run.run("test-run", payload, 0.5, data_dir=Path(directory))
            receipt = json.loads((output / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(
                json.loads((output / "items.json").read_text(encoding="utf-8")), items
            )
        self.assertEqual(
            (receipt["items"], receipt["charge_cap_usd"], receipt["input"]),
            (501, 0.5, payload),
        )
        self.assertEqual(
            transport.call_args_list,
            [
                call(
                    "acts/clockworks~tiktok-scraper/runs",
                    params={
                        "maxTotalChargeUsd": 0.5,
                        "timeout": 900,
                        "waitForFinish": 30,
                    },
                    payload=payload,
                ),
                call("actor-runs/run-1", params={"waitForFinish": 30}),
                call("datasets/data-1/items", params={"offset": 0, "limit": 500}),
                call("datasets/data-1/items", params={"offset": 500, "limit": 500}),
            ],
        )

    def test_bearer_for_apify_api_only(self):
        api = "https://api.apify.com/v2/key-value-stores/store/records/test.vtt"
        cdn = "https://media.example.invalid/test.vtt"
        with (
            patch.object(apify.rc, "env_value", return_value="fake_fixture_token"),
            patch.object(apify.rc, "http", return_value=(b"test", {})) as transport,
        ):
            self.assertEqual(apify.download(api), b"test")
            self.assertEqual(apify.download(cdn, timeout=8), b"test")
            with self.assertRaises(ValueError):
                apify.download("http://api.apify.com/media")
        self.assertEqual(
            transport.call_args_list,
            [
                call(
                    api,
                    timeout=30,
                    unredirected_headers={"Authorization": "Bearer fake_fixture_token"},
                ),
                call(cdn, timeout=8, unredirected_headers={}),
            ],
        )

    def test_existing_actor_media_can_be_saved(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(savetop, "download", return_value=b"fixture") as download,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            root = Path(directory)
            dataset = root / "items.json"
            out = root / "output"
            url = "https://media.example.invalid/test.mp4"
            write_json(dataset, [{"id": "1", "mediaUrls": [url]}, {"id": "2"}])
            savetop.main([str(dataset), "--output-dir", str(out)])
            self.assertEqual(
                [(p.name, p.read_bytes()) for p in out.iterdir()],
                [("1.mp4", b"fixture")],
            )
            download.assert_called_once_with(url, timeout=120)


class CaptionTests(unittest.TestCase):
    def test_track_choice_and_webvtt(self):
        tracks = [{"language": "spa"}, {"language": "eng-US"}]
        self.assertIs(preferred_track(tracks), tracks[1])
        self.assertIs(preferred_track(tracks[:1]), tracks[0])
        self.assertIsNone(preferred_track([]))
        self.assertEqual(
            process.vtt_lines(
                "WEBVTT\r\n\r\n1\r\n00:00:03.400 --> 00:00:04.200\r\n<i>First cue</i>\r\n\r\n"
                "00:05.000 --> 00:06.000\r\nFirst cue\r\n\r\n00:08.500 --> 00:10.000\r\nNew cue\r\n"
            ),
            [(3, "First cue"), (8, "New cue")],
        )

    def test_actor_subtitle_cache_and_counts(self):
        url = "https://media.example.invalid/cue.vtt"
        items = [
            {"dataType": "profile"},
            {"dataType": "video", "id": "cached"},
            {"dataType": "video", "id": "missing"},
            {
                "dataType": "video",
                "id": "success",
                "subtitles": [{"language": "eng", "url": url}],
            },
            {
                "dataType": "video",
                "id": "failure",
                "subtitles": [{"language": "eng", "url": url}],
            },
        ]
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(ss_subtitles.time, "sleep"),
            patch.object(
                ss_subtitles.rc,
                "http",
                side_effect=[(b"WEBVTT", {}), ss_subtitles.rc.HttpError(404, "gone")],
            ),
        ):
            root = Path(directory)
            (root / "cached.vtt").write_bytes(b"old")
            self.assertEqual(ss_subtitles.fetch_tracks(items, root), (2, 1, 1))
            self.assertEqual((root / "success.vtt").read_bytes(), b"WEBVTT")
            self.assertFalse((root / "failure.vtt").exists())

    def test_pool_prefers_new_snapshot_and_keeps_missing_counts_blank(self):
        old = {
            "id": "42",
            "text": "In my world Roblox",
            "playCount": 50,
            "searchQuery": "old",
        }
        latest = {
            **old,
            "playCount": 0,
            "searchQuery": "fresh",
            "createTimeISO": "2026-11-10",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, date, posts in (
                ("a", "2026-11-20", [old]),
                (
                    "b",
                    "2026-11-25",
                    [
                        latest,
                        {"error": "missing"},
                        {**latest, "id": "ad", "isAd": True},
                    ],
                ),
            ):
                folder = root / f"apify-{name}"
                folder.mkdir()
                write_json(folder / "run.json", {"id": name, "finishedAt": date})
                write_json(folder / "items.json", posts)
            subtitles = root / "subtitles"
            subtitles.mkdir()
            write_json(
                subtitles / "42.whisper.json",
                {"language": "en", "segments": [[0, "First words"]]},
            )
            with patch.object(
                process, "download", side_effect=AssertionError("no network")
            ):
                rows = list(process.pool_rows(process.load_runs(root), subtitles))
            self.assertEqual(len(rows), 1)
            self.assertEqual(
                (rows[0]["views"], rows[0]["likes"], rows[0]["age_days"]), (0, None, 15)
            )
            self.assertEqual(
                (rows[0]["apify_run_id"], rows[0]["discovery_route"]),
                ("b", "old | fresh"),
            )
            self.assertEqual(
                (rows[0]["transcript_source"], rows[0]["transcript_words"]),
                ("eng Whisper-small (local)", 2),
            )

    def test_whisper_segment_filter(self):
        outcome = {
            "segments": [
                {"text": "  Spot on  ", "start": 1.8, "no_speech_prob": 0.2},
                {"text": "  ", "start": 3},
                {"text": "Maybe", "start": 4, "no_speech_prob": 0.8},
            ]
        }
        self.assertEqual(usable_segments(outcome), [[1, "Spot on"]])


class ReportTests(unittest.TestCase):
    def test_tiers_exclude_recent_posts_and_cap_a_creator(self):
        def row(index, creator, **updates):
            base = {
                "id": str(index),
                "creator": creator,
                "age_days": 10,
                "views": index,
                "transcript_words": 20,
                "roblox": "True",
                "transcript_source": "eng TikTok",
            }
            return {**base, **updates}

        rows = [
            row(index, "high" if index >= 145 else str(index)) for index in range(150)
        ]
        rows.append(row(200, "too-recent", age_days=4))
        tiers, median = build.select_tiers(rows)
        chosen = [r["id"] for tier in tiers.values() for r in tier]
        self.assertEqual(median, 75)
        self.assertEqual(len(chosen), len(set(chosen)))
        self.assertNotIn("200", chosen)
        self.assertEqual(sum(r["creator"] == "high" for r in tiers["TOP"]), 4)
        self.assertEqual(
            (tiers["TOP"][0]["views"], tiers["FLOP"][0]["views"]), (149, 0)
        )

    def test_build_report_handles_missing_metrics_and_reads_excel_csv(self):
        saved = dict.fromkeys(process.FIELDS, None)
        saved.update(
            id="abc", age_days=3, views=0, caption="In my world", transcript="[]"
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            root = Path(directory)
            pool = root / "pool.csv"
            process.rc.write_rows(pool, process.FIELDS, [saved])
            build.main(
                ["--pool", str(pool), "--out", str(root / "report"), "--no-downloads"]
            )
            row = read_csv(root / "report" / "ALL-POSTS.csv")[0]
            self.assertEqual(row["tier"], "")
            self.assertTrue(row["untiered_reason"].startswith("A. "))
            self.assertEqual(
                (row["views"], row["likes"], row["like_rate_pct"]), ("0", "", "")
            )

    def test_narration_rate_and_pauses(self):
        posts = [{"id": "a", "tier": "TOP", "views": "2500000"}]
        transcripts = {
            "a": {
                "transcript": json.dumps(
                    [
                        [0, "Four words in cue"],
                        [4, "A cue"],
                        [9, "Three more words"],
                        [12, "ignored ending"],
                    ]
                )
            }
        }
        self.assertEqual(speed.rates(posts, transcripts, "TOP"), ([45.0], [45.0]))
        words = [
            {"start": 0, "end": 0.3},
            {"start": 0.75, "end": 1},
            {"start": 1.12, "end": 2},
        ]
        self.assertEqual(
            measure({"segments": [{"words": words}], "text": " Good test. "}),
            {"wpm": 90, "longest_gap": 0.45, "gaps_over_0.3s": 1, "text": "Good test."},
        )


if __name__ == "__main__":
    unittest.main()
