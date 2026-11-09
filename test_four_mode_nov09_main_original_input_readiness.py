"""Result-blind pinned-main archive and original V2 ranking integrity tests."""
import json
import unittest
from pathlib import Path

from four_mode_nov09_main_original_input_readiness import (
    read_pinned_main, review_snapshot, sha1_blob,
)

ROOT = Path(__file__).resolve().parent
CODE = "202611080101"
COMMIT = "1" * 40


def original():
    return (ROOT / "four_mode_forecasts" / (CODE + ".json")).read_bytes()


def entry(raw=None, blob=None):
    raw = original() if raw is None else raw
    return ("four_mode_forecasts/" + CODE + ".json",
            sha1_blob(raw) if blob is None else blob, raw)


class OriginalOnlyFutureInputReadinessTest(unittest.TestCase):
    def check(self, row):
        return review_snapshot([row], "20261108", COMMIT)

    def test_original_exact_git_blob_and_ranked_tickets(self):
        out = self.check(entry())
        self.assertEqual(out["file_count"], 1)
        self.assertEqual(out["valid_v2_original_inputs"], 1)
        self.assertEqual(out["invalid_inputs"], [])
        self.assertEqual(out["source_cards_and_title_before_generated"], 1)
        self.assertEqual(out["generated_before_deadline_minus_12_min"], 1)
        self.assertEqual(sum(out["top1_head_counts_original"]["hit"].values()), 1)
        self.assertFalse(out["results_read"])
        self.assertFalse(out["outcome_metric_computed"])
        self.assertFalse(out["candidate_generated_or_modified"])
        self.assertFalse(out["formal"])
        self.assertEqual(out["formal_count"], 0)
        self.assertFalse(out["model_promotion_allowed"])

    def test_tampered_blob_is_excluded_even_if_saved_rank_syntax_is_valid(self):
        out = self.check(entry(blob="a" * 40))
        self.assertEqual(out["valid_v2_original_inputs"], 0)
        self.assertEqual(out["invalid_inputs"][0]["reason"], "git_blob_content_mismatch")

    def test_changed_original_probability_replay_is_excluded(self):
        obj = json.loads(original())
        obj["modes"]["hit"]["tickets"][0]["p"] += 0.00001
        raw = json.dumps(obj, sort_keys=True).encode()
        out = self.check(entry(raw))
        self.assertEqual(out["valid_v2_original_inputs"], 0)
        self.assertEqual(out["invalid_inputs"][0]["reason"], "stored_ticket_not_reproduced_from_inputs")

    def test_result_or_late_candidate_never_enters_original_input_readiness(self):
        obj = json.loads(original())
        obj["finish_order"] = [1, 2, 3]
        out = self.check(entry(json.dumps(obj).encode()))
        self.assertEqual(out["valid_v2_original_inputs"], 0)
        self.assertEqual(out["invalid_inputs"][0]["reason"], "result_or_candidate_leak_into_saved_original")

    def test_two_independent_source_hashes_are_required(self):
        obj = json.loads(original())
        self.assertEqual(set(obj["source_sha256"]), {"race_cards", "title"})
        obj["source_sha256"]["race_cards"] = "not-a-hash"
        out = self.check(entry(json.dumps(obj).encode()))
        self.assertEqual(out["valid_v2_original_inputs"], 0)
        self.assertEqual(out["invalid_inputs"][0]["reason"], "missing_input_source_digest")
        obj["source_sha256"] = "a" * 64
        out = self.check(entry(json.dumps(obj).encode()))
        self.assertEqual(out["valid_v2_original_inputs"], 0)
        self.assertEqual(out["invalid_inputs"][0]["reason"], "missing_input_source_digest")

    def test_source_timestamp_after_generation_fails(self):
        obj = json.loads(original())
        obj["source_cards_received_jst"] = obj["deadline_jst"]
        out = self.check(entry(json.dumps(obj).encode()))
        self.assertEqual(out["valid_v2_original_inputs"], 0)
        self.assertEqual(out["invalid_inputs"][0]["reason"], "source_timestamp_after_forecast_generation")

    def test_non_jst_deadline_or_generation_fails_closed(self):
        obj = json.loads(original())
        obj["deadline_jst"] = "2026-11-08T10:00:00+00:00"
        out = self.check(entry(json.dumps(obj).encode()))
        self.assertEqual(out["valid_v2_original_inputs"], 0)
        self.assertIn(out["invalid_inputs"][0]["reason"],
                      ("timestamp_not_jst", "invalid_archive_timestamps"))

    def test_duplicate_file_is_a_visible_exclusion_not_a_second_forecast(self):
        out = review_snapshot([entry(), entry()], "20261108", COMMIT)
        self.assertEqual(out["valid_v2_original_inputs"], 1)
        self.assertEqual(len(out["invalid_inputs"]), 1)
        self.assertEqual(out["invalid_inputs"][0]["reason"], "duplicate_race_path")

    def test_git_ref_is_anchored_before_listing_or_reading_originals(self):
        calls = []
        record = entry()
        tree = ("100644 blob " + record[1] + "\t" + record[0] + "\0").encode()
        def fake_git(args):
            calls.append(args)
            if args[0] == "rev-parse":
                return (COMMIT + "\n").encode()
            if args[0] == "ls-tree":
                self.assertEqual(args[3], COMMIT)
                return tree
            if args[0] == "show":
                self.assertEqual(args[1], COMMIT + ":" + record[0])
                return record[2]
            raise AssertionError("unexpected_git_request")
        out = read_pinned_main("20261108", git=fake_git)
        self.assertEqual(out["pinned_main_commit"], COMMIT)
        self.assertEqual(out["valid_v2_original_inputs"], 1)
        self.assertEqual([a[0] for a in calls], ["rev-parse", "ls-tree", "show"])
        with self.assertRaisesRegex(ValueError, "unsafe_git_ref_or_day"):
            read_pinned_main("20261108", ref="-bad", git=fake_git)

    def test_no_originals_does_not_forge_formal_or_outcome_hits(self):
        out = review_snapshot([], "20261109", COMMIT)
        self.assertEqual(out["file_count"], 0)
        self.assertEqual(out["valid_v2_original_inputs"], 0)
        self.assertFalse(out["formal"])
        self.assertFalse(out["outcome_metric_computed"])
        self.assertFalse(out["official_beforeinfo_six_and_odds_120_from_original_verified"])


if __name__ == "__main__":
    unittest.main()
