"""Synthetic only: compare rank turnover, not real gains or losses."""
import copy
import math
import unittest

from position_sensitive_feature_ablation import audit_feature_ablation, TOPS, MODES
from test_position_sensitive_conditioned_lab import evidence

RATES = [6.25, 7.05, 4.83, 6.5, 5.7, 5.15]
STUDY = "EXPLORATORY_ONLY_ABLATION_20261109"


def run(e=None, p=None, r=None):
    if p is None:
        p = {
            "motor_2ren_pct": {"second": 0.8, "third": 0.4},
            "exhibition_st_s": {"second": 0.16, "third": 0.08},
        }
    return audit_feature_ablation(
        RATES if r is None else r,
        evidence() if e is None else e, p, STUDY)


class FeatureAblationTests(unittest.TestCase):
    def test_same_race_three_way_all_modes_and_budgets(self):
        d = run()
        self.assertEqual(set(d["ticket_budgets"]), set(MODES))
        for label in ("original_v2_vs_frozen_six_rate",
                      "frozen_six_rate_vs_exploratory_features",
                      "original_v2_vs_exploratory_features"):
            self.assertEqual(set(d[label]), set(MODES))
            for mode, budget in MODES.items():
                self.assertEqual(set(d[label][mode]["topk"]), set(str(k) for k in TOPS))
                self.assertEqual(len(d[label][mode]["original_top1"].split("-")), 3)
                self.assertFalse(d[label][mode]["topk"]["10"]["applicable"]
                                 if budget < 10 else False)
                for k in TOPS:
                    part = d[label][mode]["topk"][str(k)]
                    if k <= budget:
                        self.assertTrue(part["applicable"])
                        self.assertEqual(part["retained_tickets"] + part["replaced_tickets"], k)
                        self.assertTrue(part["no_accuracy_inference"])
        self.assertEqual(d["same_race_original_and_candidate"], True)

    def test_true_unregistered_research_no_performance_certification(self):
        d = run()
        for label in ("official_source_authenticated",
                      "official_six_and_odds120_before_t12_verified",
                      "candidate_first_remote_receipt_verified",
                      "confirmed_outcomes_read", "topk_hit_rate_measured",
                      "roi_measured", "calibration_measured", "formal",
                      "model_improvement_proven", "promotion_allowed",
                      "production_changed"):
            self.assertFalse(d[label], label)
        self.assertEqual(d["used_features_with_nonzero_coefficients"],
                         ["exhibition_st_s", "motor_2ren_pct"])

    def test_leave_one_out_labels_are_not_causal_estimates(self):
        d = run()
        self.assertEqual(set(d["leave_one_feature_out"]),
                         {"motor_2ren_pct", "exhibition_st_s"})
        for value in d["leave_one_feature_out"].values():
            self.assertIn("not_causal", value["interpretation"])
            self.assertEqual(set(value["without_feature_vs_with_all"]), set(MODES))

    def test_zero_weight_does_not_mark_feature_consumed(self):
        blank = {"boats": [{"boat": n} for n in range(1, 7)], "context": {}}
        d = run(e=blank, p={"motor_2ren_pct": {"second": 0, "third": 0}})
        self.assertEqual(d["used_features_with_nonzero_coefficients"], [])
        self.assertEqual(d["leave_one_feature_out"], {})
        self.assertIn("motor_2ren_pct", d["missing_or_invalid_features"])
        for mode in MODES:
            for k in TOPS:
                p = d["frozen_six_rate_vs_exploratory_features"][mode]["topk"][str(k)]
                if p["applicable"]:
                    self.assertFalse(p["membership_changed"])

    def test_missing_active_exhibition_refuses_hypothetical_score(self):
        e = evidence()
        del e["boats"][1]["exhibition_st_s"]
        with self.assertRaisesRegex(ValueError, "invalid_exhibition_st_s"):
            run(e=e)

    def test_result_payout_leakage_rejected(self):
        for field in ("result", "payout", "confirmed_finish"):
            e = evidence()
            e[field] = "1-2-3"
            with self.assertRaisesRegex(ValueError, "outcome_contaminated"):
                run(e=e)

    def test_modified_input_digest_and_output_determinism(self):
        a = run()
        b = run()
        self.assertEqual(a, b)
        different = evidence()
        different["boats"][1]["motor_2ren_pct"] = 22
        c = run(e=different)
        self.assertNotEqual(a["input_fingerprint_sha256_self_supplied"],
                            c["input_fingerprint_sha256_self_supplied"])
        self.assertEqual(len(a["input_fingerprint_sha256_self_supplied"]), 64)

    def test_invalid_rate_and_invalid_coefficients(self):
        with self.assertRaisesRegex(ValueError, "invalid six national win rates"):
            run(r=[6.0] * 5 + [math.nan])
        with self.assertRaisesRegex(ValueError, "invalid_coefficient"):
            run(p={"motor_2ren_pct": {"second": math.inf, "third": 0}})
        with self.assertRaisesRegex(ValueError, "unregistered_feature_name"):
            run(p={"future_result": {"second": 1, "third": 1}})


if __name__ == "__main__":
    unittest.main()
