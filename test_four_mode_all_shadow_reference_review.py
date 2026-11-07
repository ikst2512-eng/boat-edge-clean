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

    def test_no_captures_never_fabricates_paired_outcomes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            report=compare([],root)
            self.assertEqual(report["selected_first_600_frozen"],0)
            self.assertEqual(report["confirmed_result_matches"],{})
            self.assertFalse(report["formal"])


if __name__=="__main__":
    unittest.main()
