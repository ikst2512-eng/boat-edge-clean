"""Fail-closed tests for four-mode forward research gating; no live data changes."""
import copy
import json
import unittest
from itertools import permutations
from four_mode_forward_paired_score import COUNTS, PROTOCOL, protocol_check, score


class FourModeForwardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    def row(self):
        tickets = ["-".join(map(str, p)) for p in permutations(range(1, 7), 3)]
        return {
            "race_code": "202611070101",
            "deadline_jst": "2026-11-07T08:35:00+09:00",
            "model_version": self.policy["model_version"],
            "official_source_received_jst": "2026-11-07T08:09:00+09:00",
            "baseline_generated_jst": "2026-11-07T08:10:00+09:00",
            "baseline_github_observed_jst": "2026-11-07T08:10:02+09:00",
            "candidate_generated_jst": "2026-11-07T08:10:05+09:00",
            "candidate_github_observed_jst": "2026-11-07T08:10:07+09:00",
            "official_beforeinfo_complete_6": True,
            "official_exhibition_complete_6": True,
            "official_odds_complete_120": True,
            "result_based_features_used": False,
            "source_sha256": "a"*64,
            "original_forecast_sha256": "b"*64,
            "candidate_method_sha256": "c"*64,
            "mode_candidate_selector_sha256": {m:"d"*64 for m in COUNTS},
            "baseline": {m:tickets[:n] for m,n in COUNTS.items()},
            "candidate": {m:tickets[:n] for m,n in COUNTS.items()},
            "formal": False,
            "model_improvement_proven": False
        }

    def result(self):
        return {"race_code":"202611070101", "status":"confirmed", "finish_order":[1,2,3],
                "confirmed_at_jst":"2026-11-07T08:50:00+09:00",
                "collected_at_jst":"2026-11-07T08:51:00+09:00",
                "source_url":"https://boatracecsv.github.io/data/results/realtime/2026/11/07.csv",
                "source_sha256":"e"*64}

    def test_protocol_is_locked_and_nov05_cannot_enter(self):
        self.assertEqual(protocol_check(self.policy)["pilot_races"],300)
        changed=copy.deepcopy(self.policy); changed["early_stopping_allowed"]=True
        with self.assertRaisesRegex(ValueError,"changed_forward_protocol"):
            protocol_check(changed)
        row=self.row()
        row["race_code"]="202611050101"
        row["deadline_jst"]="2026-11-05T08:35:00+09:00"
        report=score([row],{},self.policy)
        self.assertEqual(report["eligible_roster_count"],0)
        self.assertIn("date_or_model_version_mismatch",report["excluded_before_result_read"])

    def test_real_reference_result_is_never_formal(self):
        row=self.row()
        report=score([row],{row["race_code"]:self.result()},self.policy)
        self.assertEqual(report["matched_by_phase"],{"pilot":1})
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["baseline"],1)
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["candidate"],1)
        self.assertFalse(report["formal"])
        self.assertFalse(report["model_improvement_proven"])
        self.assertFalse(report["independent_first_remote_receipt_verified"])
        self.assertFalse(report["model_promotion_allowed"])

    def test_missing_result_never_becomes_miss(self):
        row=self.row()
        report=score([row],{},self.policy)
        self.assertEqual(report["pending_result_codes"],[row["race_code"]])
        self.assertEqual(report["matched_by_phase"],{})
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["denominator_reference_only"],0)

    def test_outcome_in_input_and_same_second_are_refused(self):
        row=self.row();row["finish_order"]=[1,2,3]
        self.assertIn("outcome_leak_in_pre_result_roster",
                      score([row],{},self.policy)["excluded_before_result_read"])
        row=self.row();row["candidate_github_observed_jst"]=row["candidate_generated_jst"]
        self.assertIn("late_or_same_second_T12",
                      score([row],{},self.policy)["excluded_before_result_read"])
        row=self.row();row["official_odds_complete_120"]=False
        self.assertIn("incomplete_or_postrace_feature",
                      score([row],{},self.policy)["excluded_before_result_read"])
        for exhibition in (False, None):
            row=self.row()
            if exhibition is None:
                row.pop("official_exhibition_complete_6")
            else:
                row["official_exhibition_complete_6"]=exhibition
            self.assertIn("incomplete_or_postrace_feature",
                          score([row],{},self.policy)["excluded_before_result_read"])

    def test_mixed_invalid_future_roster_refused_without_backfill(self):
        valid = self.row()
        rejected = copy.deepcopy(valid)
        rejected["race_code"] = "202611070102"
        rejected["deadline_jst"] = "2026-11-07T08:40:00+09:00"
        rejected["candidate_github_observed_jst"] = rejected["candidate_generated_jst"]
        # The second row must not be silently omitted and replaced by a
        # later valid candidate in the first fixed 600 forecast slots.
        with self.assertRaisesRegex(ValueError, "incomplete_candidate_roster_no_replacement"):
            score([valid, rejected], {valid["race_code"]: self.result()}, self.policy)
        with self.assertRaisesRegex(ValueError, "incomplete_candidate_roster_no_replacement"):
            score([rejected, valid], {valid["race_code"]: self.result()}, self.policy)

    def test_original_remote_observation_must_precede_candidate(self):
        # A candidate that predates the original GitHub observation is not
        # the reproducible, result-blind post-publication shadow we registered.
        for field, value in (
            ("baseline_github_observed_jst", "2026-11-07T08:10:00.500000+09:00"),
            ("candidate_generated_jst", "2026-11-07T08:10:01+09:00"),
            ("candidate_generated_jst", "2026-11-07T08:10:02.500000+09:00"),
            ("candidate_github_observed_jst", "2026-11-07T08:10:05.500000+09:00"),
        ):
            with self.subTest(field=field, value=value):
                row = self.row()
                row[field] = value
                verdict = score([row], {}, self.policy)
                self.assertEqual(verdict["eligible_roster_count"], 0)
                self.assertIn("late_or_same_second_T12",
                              verdict["excluded_before_result_read"])

    def test_candidate_rank_losses_cannot_be_hidden(self):
        row=self.row()
        original=row["candidate"]["hit"]
        row["candidate"]["hit"]=original[1:]+["6-5-4"]
        report=score([row],{row["race_code"]:self.result()},self.policy)
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["lost"],1)
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["candidate"],0)

    def test_candidate_selector_drift_and_duplicate_are_rejected(self):
        a=self.row();b=copy.deepcopy(a)
        b["race_code"]="202611070102"
        b["mode_candidate_selector_sha256"]["hit"]="f"*64
        with self.assertRaisesRegex(ValueError,"selector_changed_across_future_races"):
            score([a,b],{},self.policy)
        with self.assertRaisesRegex(ValueError,"duplicate_candidate"):
            score([a,a],{},self.policy)

    def test_forged_source_or_collection_clock_is_excluded(self):
        row=self.row()
        for field,replacement in (
            ("source_url","https://example.org/confirmed.csv"),
            ("collected_at_jst","2026-11-07T08:00:00+09:00"),
            # Collector's bounded 3-minute skew tolerance must not
            # establish research-grade confirmed-result chronology.
            ("collected_at_jst","2026-11-07T08:49:00+09:00"),
        ):
            with self.subTest(field=field):
                result=self.result()
                result[field]=replacement
                report=score([row],{row["race_code"]:result},self.policy)
                self.assertEqual(report["matched_by_phase"],{})
                self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]
                                 ["denominator_reference_only"],0)
                self.assertIn("untrusted_result_or_time",
                              report["invalid_result_counts"])

    def test_untrusted_result_is_not_scored(self):
        row=self.row();result=self.result()
        result["confirmed_at_jst"]="2026-11-07T08:10:00+09:00"
        report=score([row],{row["race_code"]:result},self.policy)
        self.assertEqual(report["matched_by_phase"],{})
        self.assertIn("untrusted_result_or_time",report["invalid_result_counts"])


if __name__ == "__main__":
    unittest.main()
