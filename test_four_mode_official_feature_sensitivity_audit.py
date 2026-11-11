"""Result-blind source-use negative controls on a real saved V2 original."""
import copy
import json
import unittest
from pathlib import Path

from four_mode_official_feature_sensitivity_audit import (
    SENTINEL, examine, negative_control, read_pinned,
)
from four_mode_nov09_main_original_input_readiness import sha1_blob

CODE = "202611080101"
DAY = "20261108"
COMMIT = "a"*40
PATH = "four_mode_forecasts/" + CODE + ".json"
RAW = (Path(__file__).resolve().parent/"four_mode_forecasts"/(CODE+".json")).read_bytes()


def entry(raw=RAW):
    return PATH, sha1_blob(raw), raw


class OfficialFeatureSensitivityAuditTests(unittest.TestCase):
    def test_existing_candidate_ignores_synthetic_official_fields(self):
        obj = json.loads(RAW)
        before = copy.deepcopy(obj)
        result = negative_control(obj)
        self.assertTrue(result["original_baseline_unchanged"])
        self.assertTrue(result[
            "candidate_tickets_unchanged_under_synthetic_official_controls"])
        self.assertEqual(before, obj)
        self.assertNotIn("official_beforeinfo", obj)
        self.assertNotIn("official_odds_120", obj)

    def test_real_saved_original_is_immutable_and_nonformal(self):
        a = examine([entry()], DAY, COMMIT)
        self.assertEqual(a["real_saved_origins_verified"], 1)
        self.assertEqual(a["mode_candidate_insensitive_to_synthetic_official_fields"], 1)
        self.assertEqual(a["only_race_cards_and_title_source_digests"], 1)
        self.assertFalse(a["official_three_source_model_consumption_verified"])
        self.assertFalse(a["candidate_first_remote_receipt_verified"])
        self.assertFalse(a["real_official_source_data_read"])
        self.assertFalse(a["confirmed_results_read"])
        self.assertFalse(a["candidate_files_generated_or_written"])
        self.assertFalse(a["formal"])
        self.assertEqual(a["admitted_prospective_pairs"], 0)

    def test_untrusted_result_and_candidate_must_be_rejected(self):
        for flag, value in (
            ("result", "1-2-3"), ("finish_order", [1,2,3]),
            ("candidate_tickets", ["1-2-3"])):
            with self.subTest(flag=flag):
                v=json.loads(RAW)
                v[flag]=value
                with self.assertRaisesRegex(ValueError, "not_official_feature"):
                    negative_control(v)

    def test_actual_official_bytes_cannot_be_injected_to_fake_a_positive(self):
        for flag in ("official_beforeinfo", "official_exhibition",
                     "official_odds_120"):
            v=json.loads(RAW)
            v[flag]={"not_original_source": "fake"}
            with self.subTest(flag=flag), self.assertRaisesRegex(
                    ValueError, "not_official_feature"):
                negative_control(v)

    def test_wrong_or_missing_source_digest_is_rejected(self):
        for altered in ("string", "different_keys"):
            v=json.loads(RAW)
            if altered == "string":
                v["source_sha256"] = "f"*64
            else:
                v["source_sha256"]["official_odds"] = SENTINEL
            with self.subTest(altered=altered), self.assertRaisesRegex(
                    ValueError, "not_official_feature"):
                negative_control(v)

    def test_incorrect_beforeinfo_status_rejected(self):
        v=json.loads(RAW)
        v["beforeinfo"] = "claimed_official_six_boat"
        with self.assertRaisesRegex(ValueError, "not_official_feature"):
            negative_control(v)

    def test_git_blob_tampering_and_duplicate_inputs_rejected(self):
        with self.assertRaisesRegex(ValueError, "original_git_blob_or_model"):
            examine([(PATH, "b"*40, RAW)], DAY, COMMIT)
        with self.assertRaisesRegex(ValueError, "original_git_blob_or_model"):
            examine([entry(), entry()], DAY, COMMIT)

    def test_rank_probability_tampering_rejected(self):
        v=json.loads(RAW)
        v["modes"]["hit"]["tickets"][0]["p"]+=0.01
        changed=json.dumps(v).encode()
        with self.assertRaisesRegex(ValueError, "original_git_blob_or_model"):
            examine([entry(changed)], DAY, COMMIT)

    def test_result_leak_makes_cohort_unusable(self):
        v=json.loads(RAW)
        v["winning_ticket"]="1-2-3"
        changed=json.dumps(v).encode()
        with self.assertRaisesRegex(ValueError, "original_git_blob_or_model"):
            examine([entry(changed)], DAY, COMMIT)

    def test_read_pinned_git_tree_not_mutable_working_copy(self):
        tree=("100644 blob "+sha1_blob(RAW)+"\t"+PATH+"\0").encode()
        calls=[]
        def fake_git(args):
            calls.append(args)
            if args[0]=="rev-parse":
                return (COMMIT+"\n").encode()
            if args[0]=="ls-tree":
                self.assertEqual(args[3], COMMIT)
                return tree
            if args[0]=="show":
                self.assertEqual(args[1], COMMIT+":"+PATH)
                return RAW
            raise AssertionError(args)
        result=read_pinned(DAY, git=fake_git)
        self.assertEqual(result["pinned_main_commit"], COMMIT)
        self.assertEqual(result["real_saved_origins_verified"], 1)
        self.assertEqual([c[0] for c in calls],["rev-parse","ls-tree","show"])

    def test_invalid_pinning_and_zero_evidence_stay_nonformal(self):
        for invalid_day, ref in (("2026-11-09","refs/remotes/origin/main"),
                                 ("20261109","HEAD")):
            with self.subTest(invalid_day=invalid_day, ref=ref):
                with self.assertRaisesRegex(ValueError, "unsafe_day_or_git_ref"):
                    read_pinned(invalid_day, ref=ref)
        result=examine([], "20261109", COMMIT)
        self.assertEqual(result["real_saved_origins_verified"],0)
        self.assertEqual(result["mode_candidate_insensitive_to_synthetic_official_fields"],0)
        self.assertFalse(result["formal"])


if __name__ == "__main__":
    unittest.main()
