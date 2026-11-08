"""Pure synthetic tests for noncertifying paired exact-McNemar statistics."""
from copy import deepcopy
import math
import unittest

from position_sensitive_paired_inference import (
    exact_one_sided_gain_p, holm_adjust, inference_reference_only,
)
from test_position_sensitive_paired_guard import synthetic_reference, set_paired
from four_mode_position_sensitive_forward import MODES


class PairedInferenceTests(unittest.TestCase):
    def test_exact_one_sided_discordance_tail(self):
        self.assertEqual(exact_one_sided_gain_p(0, 0), 1.0)
        self.assertEqual(exact_one_sided_gain_p(10, 0), 1 / 1024)
        self.assertEqual(exact_one_sided_gain_p(0, 10), 1.0)
        self.assertAlmostEqual(exact_one_sided_gain_p(5, 5), 638 / 1024)
        self.assertAlmostEqual(exact_one_sided_gain_p(2, 1), 0.5)
        for gained, lost in ((-1, 0), (0, -1), (301, 0), (1.0, 0),
                             (True, 0)):
            with self.assertRaises(ValueError):
                exact_one_sided_gain_p(gained, lost)

    def test_holm_adjustment_is_monotone_and_familywise(self):
        adj = holm_adjust({"a": .01, "b": .03, "c": .04})
        self.assertAlmostEqual(adj["a"], .03)
        self.assertAlmostEqual(adj["b"], .06)
        self.assertAlmostEqual(adj["c"], .06)
        with self.assertRaises(ValueError):
            holm_adjust({})
        for p in (-0.1, 1.01, float("nan"), True):
            with self.assertRaises(ValueError):
                holm_adjust({"bad": p})

    def test_zero_or_partial_confirmation_has_no_p_values(self):
        for full in (False, True):
            s = synthetic_reference(full=full)
            if full:
                s["confirmed_result_counts"]["confirmation"] = 299
                s["pending_race_codes"] = ["202611091201"]
                for m in MODES:
                    for k in ("1", "3", "5", "10"):
                        s["by_phase_mode_topn"]["confirmation"][m][k][
                            "reference_denominator"] = 299
            out = inference_reference_only(s)
            self.assertEqual(out["primary"], {})
            self.assertEqual(out["secondary_safety"], {})
            self.assertEqual(out["primary_reference_screen"], "not_evaluated")
            self.assertFalse(out["model_improvement_proven"])

    def test_top1_gain_does_not_mask_top5_top10_losses(self):
        s = synthetic_reference(full=True)
        for phase in ("pilot", "confirmation"):
            for top, counts in {
                1: (40, 50, 20, 10),
                3: (60, 65, 15, 10),
                5: (90, 85, 5, 10),
                10: (120, 115, 5, 10),
            }.items():
                set_paired(s, phase, "hit", top, *counts)
        out = inference_reference_only(s)
        self.assertTrue(out["reference_confirmation_complete"])
        self.assertEqual(out["primary"]["hit"]["net_hit_difference"], 10)
        self.assertEqual(out["secondary_reference_screen"], "observed_top5_top10_net_loss")
        self.assertTrue(out["secondary_safety"]["hit_top5"]["observed_net_loss"])
        self.assertTrue(out["secondary_safety"]["hit_top10"]["observed_net_loss"])
        self.assertFalse(out["promotion_allowed"])

    def test_even_extreme_synthetic_signal_cannot_be_called_formal(self):
        s = synthetic_reference(full=True)
        for phase in ("pilot", "confirmation"):
            for mode, budget in MODES.items():
                for top, base in ((1, 40), (3, 60), (5, 80), (10, 100)):
                    if top > budget:
                        base = 80  # five-ticket narrow Top10 duplicates Top5
                    set_paired(s, phase, mode, top, base, base + 40, 40, 0)
        out = inference_reference_only(s)
        self.assertTrue(out["reference_confirmation_complete"])
        self.assertEqual(out["primary_reference_screen"],
                         "exploratory_superiority_signal_only")
        self.assertEqual(out["secondary_reference_screen"],
                         "exploratory_superiority_signal_only")
        self.assertFalse(out["secondary_safety"]["narrow_top10"]["applicable"])
        self.assertEqual(len([v for v in out["secondary_safety"].values()
                              if v.get("applicable")]), 7)
        self.assertTrue(all(v["holm_adjusted_p"] < .05
                            for v in out["primary"].values()))
        self.assertFalse(out["formal"])
        self.assertFalse(out["promotion_allowed"])
        self.assertFalse(out["model_improvement_proven"])
        self.assertFalse(out["source_independence_verified"])

    def test_reference_tamper_does_not_become_significance(self):
        s = synthetic_reference(full=True)
        corrupted = deepcopy(s)
        set_paired(corrupted, "confirmation", "balance", 5, 5, 9, 2, 0)
        with self.assertRaises(ValueError):
            inference_reference_only(corrupted)
        corrupted = deepcopy(s)
        corrupted["candidate_first_remote_receipt_verified"] = True
        with self.assertRaises(ValueError):
            inference_reference_only(corrupted)


if __name__ == "__main__":
    unittest.main()
