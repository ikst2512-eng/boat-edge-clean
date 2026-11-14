"""Nonproduction TopK exposure invariants for position-sensitive frozen candidate."""
import json
from pathlib import Path
import tempfile
import unittest

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_position_sensitive_shadow import shadow_modes
from position_sensitive_topk_exposure_audit import (
    TOPS, BUDGETS, audit_topk_day, compare_rankings
)

RATES = [5.01, 5.89, 6.28, 2.64, 6.09, 6.15]


def ranked(rates=RATES):
    old = rank_modes(probabilities(rates))
    candidate = shadow_modes(rates)["modes"]
    return ({m: [x["combo"] for x in old[m]["tickets"]] for m in BUDGETS},
            {m: [x["combo"] for x in candidate[m]["tickets"]] for m in BUDGETS})


class TopKExposureTests(unittest.TestCase):
    def test_same_race_k_membership_and_invariants(self):
        old, new = ranked()
        out = compare_rankings(old, new)
        self.assertEqual(set(out), set(BUDGETS))
        for mode, row in out.items():
            self.assertEqual(set(row["topn"]), set(map(str, TOPS)))
            self.assertEqual(row["top1_changed"], old[mode][0] != new[mode][0])
            for n in TOPS:
                metric = row["topn"][str(n)]
                if n > BUDGETS[mode]:
                    self.assertFalse(metric["applicable"])
                    self.assertEqual(metric["mode_ticket_budget"], BUDGETS[mode])
                    continue
                self.assertTrue(metric["applicable"])
                self.assertEqual(metric["retained"],
                                 len(set(old[mode][:n]) & set(new[mode][:n])))
                self.assertEqual(metric["retained"] +
                                 metric["displaced_tickets_not_outcomes"], n)
                self.assertEqual(metric["old_top1_dropped"],
                                 old[mode][0] not in new[mode][:n])
                self.assertEqual(metric["candidate_top1_not_in_old_topn"],
                                 new[mode][0] not in old[mode][:n])

    def test_bad_ticket_and_duplicate_are_rejected(self):
        old, new = ranked()
        new["narrow"][0] = new["narrow"][1]
        with self.assertRaises(ValueError):
            compare_rankings(old, new)
        old, new = ranked()
        new["narrow"][0] = "1-1-2"
        with self.assertRaises(ValueError):
            compare_rankings(old, new)
        old, new = ranked()
        del old["hole"]
        with self.assertRaises(ValueError):
            compare_rankings(old, new)

    def test_no_result_leak_no_archive_mutation_and_tamper_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "four_mode_forecasts").mkdir()
            (root / "confirmed_results").mkdir()
            result_file = root / "confirmed_results" / "202611080101.json"
            result_file.write_text("{ intentionally invalid result JSON")
            old, _ = ranked()
            record = {
                "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
                "race_code": "202611080101",
                "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
                "target_rates_not_proven": True,
                "generated_at_jst": "2026-11-08T08:00:00+09:00",
                "deadline_jst": "2026-11-08T12:00:00+09:00",
                "input_national_win_rates": RATES,
                "modes": rank_modes(probabilities(RATES)),
            }
            path = root / "four_mode_forecasts" / "202611080101.json"
            pristine = json.dumps(record, sort_keys=True)
            path.write_text(pristine)
            report = audit_topk_day("20261108", root)
            self.assertEqual(report["compared"], 1)
            self.assertEqual(report["excluded"], 0)
            self.assertFalse(report["formal"])
            self.assertEqual(report["forward_holdout_scored"], 0)
            self.assertFalse(report["by_mode"]["narrow"]["topn"]["10"]["applicable"])
            self.assertTrue(report["by_mode"]["hit"]["topn"]["10"]["applicable"])
            self.assertEqual(report["by_mode"]["hit"]["top1_changed"],
                             int(old["hit"][0] != ranked()[1]["hit"][0]))
            self.assertEqual(path.read_text(), pristine)
            self.assertEqual(result_file.read_text(), "{ intentionally invalid result JSON")
            record["modes"]["hit"]["tickets"][0]["p"] = -1
            altered = json.dumps(record)
            path.write_text(altered)
            report2 = audit_topk_day("20261108", root)
            self.assertEqual(report2["compared"], 0)
            self.assertEqual(report2["excluded"], 1)
            self.assertEqual(report2["exclusions"]["original_ticket_mismatch"], 1)
            self.assertEqual(path.read_text(), altered)

    def test_empty_or_invalid_day_never_fake_accuracy(self):
        with tempfile.TemporaryDirectory() as td:
            report = audit_topk_day("20261108", td)
            self.assertEqual(report["compared"], 0)
            self.assertIsNone(report["by_mode"]["hit"]["topn"]["5"][
                "mean_displaced_ticket_slots_per_race"])
            self.assertFalse(report["model_improvement_proven"])
        with self.assertRaises(ValueError):
            audit_topk_day("../results")


if __name__ == "__main__":
    unittest.main()
