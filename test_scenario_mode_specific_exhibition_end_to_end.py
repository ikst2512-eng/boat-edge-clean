"""End-to-end #1710 <-> pinned #1698 experiment (synthetic evidence only).

CI fetches *reviewed* #1698 by Git SHA. Never impersonates official
beforeinfo, provenance, live forecast, hit rate or source receipt.
"""
import copy
import hashlib
import importlib
import json
import os
import unittest

from scenario_official_exhibition_projection import project_exhibition_research
from scenario_exhibition_all_mode_runner import run_exhibition_scenario_lab
from scenario_mode_specific_exhibition_end_to_end import (
    evaluate_exhibition_mode_lenses, MODES, BUDGETS,
)
from test_scenario_official_exhibition_projection import fixture, replay_stub

STUDY = "EXPLORATORY_ONLY_MODE_EXHIBITION_INTEGRATION"
RATES = [5.2, 5.9, 6.4, 4.7, 5.5, 5.1]


def hypotheses():
    return {
        "escape_wall": {
            "head_log_shifts": [3.5, 0, 0, 0, 0, 0],
            "position_coefficients": {
                "exhibition_st_s": {"second": .3, "third": .15},
                "exhibition_time_s": {"second": .15, "third": .08},
            },
        },
        "two_sashi": {
            "head_log_shifts": [0, 3.5, 0, 0, 0, 0],
            "position_coefficients": {
                "exhibition_st_s": {"second": .3, "third": .15},
                "exhibition_time_s": {"second": .15, "third": .08},
            },
        },
        "third_attack": {
            "head_log_shifts": [0, 0, 3.5, 0, 0, 0],
            "position_coefficients": {
                "exhibition_st_s": {"second": .3, "third": .15},
                "exhibition_time_s": {"second": .15, "third": .08},
            },
        },
        "outer_benefit": {
            "head_log_shifts": [0, 0, 0, 0, 3.5, 0],
            "position_coefficients": {
                "exhibition_st_s": {"second": .3, "third": .15},
                "exhibition_time_s": {"second": .15, "third": .08},
            },
        },
    }


def weights():
    return {
        "narrow": {"escape_wall": 1.0, "two_sashi": 0.0,
                   "third_attack": 0.0, "outer_benefit": 0.0},
        "hit": {"escape_wall": 0.0, "two_sashi": 1.0,
                "third_attack": 0.0, "outer_benefit": 0.0},
        "balance": {"escape_wall": .5, "two_sashi": 0.0,
                    "third_attack": .5, "outer_benefit": 0.0},
        "hole": {"escape_wall": 0.0, "two_sashi": 0.0,
                 "third_attack": .5, "outer_benefit": .5},
    }


class PinnedModeExhibitionIntegrationTests(unittest.TestCase):
    def setUp(self):
        if os.getenv("RESEARCH_1698_PIN_REQUIRED") != "1":
            self.skipTest("exact #1698 git blob needed; never use default installation")
        try:
            module = importlib.import_module("position_sensitive_conditioned_lab")
        except ImportError as exc:
            self.fail("missing pinned #1698 conditional lab: " + str(exc))
        self.callback = module.experimental_conditional_board
        s, c = fixture()  # SYNTHETIC source bytes / dates / odds
        self.projection = project_exhibition_research(s, c, replay_stub)

    def run_experiment(self, projection=None, rates=None, scenarios=None, mode_weights=None,
                       callback=None):
        return evaluate_exhibition_mode_lenses(
            copy.deepcopy(self.projection if projection is None else projection),
            copy.deepcopy(RATES if rates is None else rates),
            copy.deepcopy(hypotheses() if scenarios is None else scenarios),
            copy.deepcopy(weights() if mode_weights is None else mode_weights),
            self.callback if callback is None else callback,
            study_id=STUDY)

    def test_four_mode_end_to_end_from_six_exhibition_boats(self):
        inputs = copy.deepcopy(self.projection)
        r = self.run_experiment()
        self.assertEqual(r["race_code"], "202611091710")
        self.assertEqual(set(r["four_mode_research_tickets"]), set(MODES))
        self.assertEqual(
            {name: len(row["tickets"]) for name, row in r["four_mode_research_tickets"].items()},
            BUDGETS)
        self.assertEqual(len(r["scenario_board_sha256"]), 4)
        self.assertTrue(r["scenario_boards_identical_across_modes"])
        # A source-driven hypothesis may yield shared Top1 even when weights
        # differ; the test MUST NOT require four artificially unique picks.
        self.assertGreaterEqual(r["distinct_top1_mode_tickets"], 3)
        self.assertLessEqual(r["distinct_top1_mode_tickets"], 4)
        self.assertNotEqual(
            r["four_mode_research_tickets"]["narrow"]["top1"],
            r["four_mode_research_tickets"]["hit"]["top1"])
        self.assertEqual(inputs, self.projection)
        for flag in ("formal", "forecast_usable", "promotion_allowed",
                     "production_changed", "first_candidate_remote_receipt_verified",
                     "official_exhibition_http_receipts_independently_verified",
                     "official_same_race_racelist_exhibition_odds120_verified",
                     "coefficient_calibration_or_hit_rate_proven"):
            if flag in r:
                self.assertFalse(r[flag], flag)
        self.assertFalse(r["weights_from_race_features_independently_calibrated"])
        self.assertFalse(r["outcomes_read_by_adapter"])
        self.assertEqual(r["new_formal_pilot_races"], 0)
        self.assertEqual(r["new_formal_confirmation_races"], 0)

    def test_remove_duplicate_conditional_work_without_changing_any_mode_ticket(self):
        calls = []
        def count_calls(*args):
            calls.append(args[3])
            return self.callback(*args)
        optimized = self.run_experiment(callback=count_calls)
        self.assertEqual(len(calls), len(hypotheses()))
        self.assertEqual(optimized["scenario_conditional_computations"], 4)
        self.assertEqual(optimized["redundant_conditional_recomputations_removed"], 12)
        self.assertEqual(len(set(calls)), 4)

        # Reference output exactly reproduces the prior four-call implementation
        # using the unmodified runner on the SAME pinned #1698 callback.
        for mode in MODES:
            plans = {
                key: {**copy.deepcopy(value), "weight": weights()[mode][key]}
                for key, value in hypotheses().items()
            }
            legacy = run_exhibition_scenario_lab(
                copy.deepcopy(self.projection), copy.deepcopy(RATES),
                plans, self.callback, study_id=STUDY)
            expected = legacy["mode_result"]
            self.assertEqual(
                optimized["four_mode_research_tickets"][mode]["tickets"],
                expected["existing_four_mode_selector_on_mixture"][mode]["tickets"])
            self.assertEqual(
                optimized["four_mode_research_tickets"][mode]["distinct_120_mixture_digest"],
                expected["mixed_120_board_sha256"])
            self.assertEqual(
                optimized["scenario_board_sha256"],
                expected["scenario_board_sha256"])

    def test_identical_weights_keeps_overlap_legitimately(self):
        common = weights()["narrow"]
        w = {mode: copy.deepcopy(common) for mode in MODES}
        out = self.run_experiment(mode_weights=w)
        self.assertEqual(out["four_mode_research_tickets"]["narrow"]["top1"],
                         out["four_mode_research_tickets"]["hit"]["top1"])
        self.assertEqual(out["pairwise_same_race_overlap"]["narrow__hit"]["shared_ticket_count"], 5)
        self.assertEqual(out["pairwise_same_race_overlap"]["narrow__hit"]["smaller_mode_overlap_fraction"], 1)
        self.assertEqual(len({r["distinct_120_mixture_digest"] for r in
                              out["four_mode_research_tickets"].values()}), 1)

    def test_st_measurement_changes_probability_not_fake_receipt(self):
        original = self.run_experiment()
        p = copy.deepcopy(self.projection)
        p["exhibition_features_by_boat"][1]["exhibition_st_s"] = .02
        # Deliberately synthetic SHA; cannot certify original official bytes.
        p["exhibition_features_sha256"] = hashlib.sha256(json.dumps(
            p["exhibition_features_by_boat"], sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        later = self.run_experiment(projection=p)
        self.assertNotEqual(
            original["four_mode_research_tickets"]["narrow"]["distinct_120_mixture_digest"],
            later["four_mode_research_tickets"]["narrow"]["distinct_120_mixture_digest"])
        self.assertFalse(later["official_exhibition_http_receipts_independently_verified"])

    def test_tampered_projection_digest_rejects(self):
        p = copy.deepcopy(self.projection)
        p["exhibition_features_by_boat"][0]["exhibition_time_s"] += .05
        with self.assertRaises(ValueError):
            self.run_experiment(projection=p)

    def test_exhibition_cannot_be_mislabeled_as_final_entry(self):
        p = copy.deepcopy(self.projection)
        p["exhibition_is_actual_final_entry"] = True
        with self.assertRaises(ValueError):
            self.run_experiment(projection=p)

    def test_invalid_mode_weights_fail(self):
        w = weights()
        del w["balance"]
        with self.assertRaisesRegex(ValueError, "incomplete_mode_hypotheses"):
            self.run_experiment(mode_weights=w)
        w = weights()
        w["hit"]["two_sashi"] = .2
        with self.assertRaisesRegex(ValueError, "scenario_weights_must_sum_one"):
            self.run_experiment(mode_weights=w)

    def test_mode_specific_scenario_fraud_cannot_be_injected(self):
        h = hypotheses()
        h["escape_wall"]["payout"] = 100
        with self.assertRaisesRegex(ValueError, "scenario_hypothesis_wrong_contract"):
            self.run_experiment(scenarios=h)

    def test_fake_formal_callback_is_rejected(self):
        def fake_formal(*args):
            out = self.callback(*args)
            out["formal"] = True
            return out
        with self.assertRaisesRegex(ValueError, "conditional_lab_contract"):
            self.run_experiment(callback=fake_formal)

    def test_fake_head_probability_callback_is_rejected(self):
        def fake_head(*args):
            out = self.callback(*args)
            pairs = out["ranked_board"]
            out["ranked_board"] = [(t, v * (2 if t[0] == 1 else 1))
                                   for t, v in pairs]
            return out
        with self.assertRaises(ValueError):
            self.run_experiment(callback=fake_head)


if __name__ == "__main__":
    unittest.main()
