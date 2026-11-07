"""Same-race outcome-last review: no formal score or artifact substitution."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from test_four_mode_all_mode_same_job_shadow import fixture, JST, CODE
from four_mode_all_mode_same_job_shadow import capture
from four_mode_all_shadow_reference_review import (
    compare, validate_capture_before_any_results,
)


class AllModeReferenceReviewTests(unittest.TestCase):
    def fresh(self,root):
        p,o,git=fixture(root)
        freeze=capture(
            root,p,o,now=datetime(2026,11,7,8,10,0,tzinfo=JST),
            git=git,clock=lambda:datetime(2026,11,7,8,10,1,tzinfo=JST)
        )
        self.assertEqual(freeze["frozen_count"],1)
        return freeze

    @staticmethod
    def write_result(root,finish):
        p=root/"confirmed_results"/(CODE+".json")
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps({
            "race_code":CODE,"status":"confirmed",
            "finish_order":finish,"confirmed_at_jst":"2026-11-07T08:45:00+09:00",
            "collected_at_jst":"2026-11-07T08:46:00+09:00",
            "source_sha256":"f"*64,
            "source_url":"https://boatracecsv.github.io/data/results/realtime/2026/11/07.csv",
        }),encoding="utf-8")
        return p

    def test_valid_reference_same_race_counts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); capture_doc=self.fresh(root)
            old=capture_doc["records"][0]["baseline"]["narrow"][0]
            self.write_result(root,[int(x) for x in old.split("-")])
            report=compare([capture_doc],root)
            self.assertEqual(report["selected_first_600_frozen"],1)
            self.assertEqual(report["confirmed_result_matches"],{"pilot":1})
            self.assertEqual(report["topn_by_phase"]["pilot"]["narrow"]["top1"]["original"],1)
            self.assertFalse(report["formal"])
            self.assertFalse(report["candidate_first_remote_receipt_verified"])
            self.assertFalse(report["model_improvement_proven"])
            self.assertFalse(report["model_promotion_allowed"])

    def test_top1_pair_reports_gained_lost_and_preserves_top3_5_10(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cap=self.fresh(root)
            old=cap["records"][0]["baseline"]["hit"][0]
            pair=cap["records"][0]["top1_pair_candidate"]["hit"][0]
            self.assertNotEqual(old,pair)
            self.write_result(root,[int(x) for x in old.split("-")])
            report=compare([cap],root)
            p=report["top1_pair_by_phase"]["pilot"]["hit"]
            self.assertEqual((p["original"],p["candidate"],p["gained"],p["lost"],p["denominator"]),
                             (1,0,0,1,1))
            self.assertTrue(report["top1_pair_top3_5_10_memberships_preserved"])
            self.assertFalse(report["formal"])
            self.write_result(root,[int(x) for x in pair.split("-")])
            report=compare([cap],root)
            p=report["top1_pair_by_phase"]["pilot"]["hit"]
            self.assertEqual((p["original"],p["candidate"],p["gained"],p["lost"],p["denominator"]),
                             (0,1,1,0,1))

    def test_top1_independent_protocol_blob_pin_prevents_selector_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cap=self.fresh(root)
            from unittest.mock import patch
            # A candidate can remain internally self-consistent while its
            # method hash changes. The independent pre-registered Git blob
            # pin must reject such a revision before reading any result.
            from four_mode_all_shadow_reference_review import TOP1_PROTOCOL
            protocol=json.loads(TOP1_PROTOCOL.read_text())
            self.assertEqual(protocol["registered_jst_date"],"2026-11-08")
            self.assertEqual(protocol["formal_count"],0)
            self.assertFalse(protocol["promotion_allowed"])
            with tempfile.TemporaryDirectory() as o:
                forged=Path(o)/"top1_protocol.json"
                protocol["pinned_selector_git_blob_sha1"]="0"*40
                forged.write_text(json.dumps(protocol))
                with patch("four_mode_all_shadow_reference_review.TOP1_PROTOCOL",forged):
                    with self.assertRaisesRegex(ValueError,
                                                "top1_selector_not_independently_preregistered"):
                        compare([cap],root)

    def test_top1_pair_tamper_rejected_before_reading_results(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cap=self.fresh(root)
            cap["records"][0]["top1_pair_candidate"]["hit"][0]="6-5-4"
            with self.assertRaisesRegex(ValueError,"saved_candidate_not_reproducible"):
                compare([cap],root)

    def test_missing_result_remains_pending_without_hit_rate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            report=compare([self.fresh(root)],root)
            self.assertEqual(report["confirmed_result_matches"],{})
            self.assertEqual(report["missing_result_codes"],[CODE])
            row=report["topn_by_phase"]["pilot"]["narrow"]["top5"]
            self.assertEqual(row["denominator"],0)
            self.assertIsNone(row["original_pct"])
            self.assertIsNone(row["candidate_pct"])
            self.assertEqual(report["top1_pair_by_phase"]["pilot"]["hit"]["denominator"],0)

    def test_result_timestamp_before_deadline_does_not_score(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cap=self.fresh(root)
            path=self.write_result(root,[1,2,3])
            result=json.loads(path.read_text())
            result["confirmed_at_jst"]="2026-11-07T08:10:00+09:00"
            path.write_text(json.dumps(result))
            report=compare([cap],root)
            self.assertEqual(report["confirmed_result_matches"],{})
            self.assertEqual(report["invalid_result_counts"],{"invalid_result_content_or_time":1})

    def test_wrong_source_or_invalid_collection_clock_does_not_score(self):
        # A well-formed winning combination does not authenticate the saved source.
        for field, replacement in (
            ("source_url","https://example.invalid/other.csv"),
            ("collected_at_jst","2026-11-07T08:00:00+09:00"),
            # One-minute backwards collection is within the collector's
            # coverage tolerance but is not valid research chronology.
            ("collected_at_jst","2026-11-07T08:44:00+09:00"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as d:
                root=Path(d);cap=self.fresh(root)
                path=self.write_result(root,[1,2,3])
                stored=json.loads(path.read_text(encoding="utf-8"))
                stored[field]=replacement
                path.write_text(json.dumps(stored),encoding="utf-8")
                report=compare([cap],root)
                self.assertEqual(report["confirmed_result_matches"],{})
                self.assertEqual(report["invalid_result_counts"],
                                 {"invalid_result_content_or_time":1})
                self.assertEqual(
                    report["topn_by_phase"]["pilot"]["hit"]["top10"]["denominator"],0)

    def test_missing_collection_timestamp_does_not_score(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cap=self.fresh(root)
            path=self.write_result(root,[1,2,3])
            stored=json.loads(path.read_text(encoding="utf-8"))
            del stored["collected_at_jst"]
            path.write_text(json.dumps(stored),encoding="utf-8")
            report=compare([cap],root)
            self.assertEqual(report["confirmed_result_matches"],{})
            self.assertEqual(report["invalid_result_counts"],
                             {"invalid_result_content_or_time":1})

    def test_tampered_frozen_candidate_rejected_before_result(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cap=self.fresh(root)
            cap["records"][0]["candidate"]["hit"][0]="6-5-4"
            with self.assertRaisesRegex(ValueError,"saved_candidate_not_reproducible"):
                compare([cap],root)

    def test_tampered_original_blob_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cap=self.fresh(root)
            path=root/"four_mode_forecasts"/(CODE+".json")
            path.write_bytes(path.read_bytes()+b"\n")
            with self.assertRaisesRegex(ValueError,"original_first_add_digest_mismatch"):
                compare([cap],root)

    def test_replay_rejects_original_observation_before_generation(self):
        # A locally frozen candidate is not a valid pre-result source
        # if the claimed original remote observation predates its generation.
        for observed in ("2026-11-06T23:06:00+00:00",
                         "2026-11-06T23:07:00.500000+00:00"):
            with self.subTest(observed=observed), tempfile.TemporaryDirectory() as d:
                root=Path(d)
                frozen=self.fresh(root)
                frozen["records"][0]["original_observed_at_utc"]=observed
                with self.assertRaisesRegex(ValueError,
                        "candidate_cutoff_or_chronology_unproven"):
                    compare([frozen],root)

    def test_selector_drift_hard_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cap=self.fresh(root)
            cap["candidate_method_sha256"]="f"*64
            with self.assertRaisesRegex(ValueError,"candidate_method_changed_or_missing"):
                compare([cap],root)

    def test_incomplete_capture_and_forged_formal_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cap=self.fresh(root)
            cap["validation_error_count"]=1
            with self.assertRaisesRegex(ValueError,"incomplete_or_failed_capture_cohort"):
                compare([cap],root)
            cap=self.fresh(root)
            cap["candidate_first_remote_receipt_verified"]=True
            with self.assertRaisesRegex(ValueError,"forged_formal_or_candidate_receipt"):
                compare([cap],root)

    def test_mixed_frozen_and_ineligible_race_cannot_be_backfilled(self):
        # Both rows were in the original publication; only one froze. Even
        # with a real result for that one, later rows must not replace the
        # ineligible cohort slot to make the reference performance look good.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self.fresh(root)
            omitted = {
                "race_code": "202611070102",
                "status": "ineligible",
                "reason": "original_remote_observation_not_verified",
                "formal": False,
            }
            original["records"].append(omitted)
            original["published_count"] = 2
            original["ineligible_count"] = 1
            self.write_result(root, [1, 2, 3])
            for order in (original["records"], list(reversed(original["records"]))):
                with self.subTest(order=[item["race_code"] for item in order]):
                    mixed = copy.deepcopy(original)
                    mixed["records"] = order
                    with self.assertRaisesRegex(
                        ValueError, "incomplete_candidate_roster_no_replacement"
                    ):
                        compare([mixed], root)

    def test_all_ineligible_records_do_not_fabricate_score(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            report = self.fresh(root)
            report["records"] = [{
                "race_code": CODE,
                "status": "ineligible",
                "reason": "not_frozen_strictly_before_T_minus_12",
                "formal": False,
            }]
            report["frozen_count"] = 0
            report["ineligible_count"] = 1
            output = compare([report], root)
            self.assertEqual(output["selected_first_600_frozen"], 0)
            self.assertEqual(output["confirmed_result_matches"], {})
            self.assertEqual(
                output["excluded_originally_captured"],
                {"not_frozen_strictly_before_T_minus_12": 1},
            )

    def test_no_captures_never_fabricates_paired_outcomes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            report=compare([],root)
            self.assertEqual(report["selected_first_600_frozen"],0)
            self.assertEqual(report["confirmed_result_matches"],{})
            self.assertFalse(report["formal"])


if __name__=="__main__":
    unittest.main()
