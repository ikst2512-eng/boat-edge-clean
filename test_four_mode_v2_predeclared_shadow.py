"""The V2 shadow must not use the result to generate or reorder candidates."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from four_mode_v2_predeclared_shadow import candidate_order, evaluate, VERSION


def tickets():
    combos = ["1-2-3", "1-2-4", "1-3-2", "2-1-3", "3-1-2",
              "1-4-2", "2-3-1", "3-2-1", "4-1-2", "5-1-2"]
    return [{"combo": c, "p": 10-i} for i, c in enumerate(combos)]


class V2ShadowTests(unittest.TestCase):
    def test_close_gap_preserves_exact_membership(self):
        old = tickets()
        new, enabled = candidate_order(old, [6.0, 5.8, 5.1, 4.0, 3.0, 2.0])
        self.assertTrue(enabled)
        self.assertEqual(set(new), {x["combo"] for x in old})
        self.assertEqual(len(new), 10)

    def test_wide_gap_keeps_original(self):
        old = tickets()
        new, enabled = candidate_order(old, [7.0, 5.0, 4.0, 3.0, 2.0, 1.0])
        self.assertFalse(enabled)
        self.assertEqual(new, [x["combo"] for x in old])

    def test_rejects_duplicate_and_nonfinite_scores(self):
        with self.assertRaises(ValueError):
            candidate_order(tickets()[:-1] + [tickets()[0]], [5.0]*6)
        bad = tickets()
        bad[0]["p"] = float("nan")
        with self.assertRaises(ValueError):
            candidate_order(bad, [5.0]*6)

    def test_filters_v1_and_never_claims_formal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f = root / "four_mode_forecasts"
            f.mkdir()
            for code, version in (
                ("202610280101", "CLEAN_FOUR_MODES_V1_UNCALIBRATED"),
                ("202611030101", VERSION)):
                (f / (code+".json")).write_text(json.dumps({
                    "race_code": code, "model_version": version,
                    "input_national_win_rates": [5.0]*6}))
            def archived(code, root):
                return 200, {"model_version": VERSION,
                    "modes": {"hit": {"tickets": tickets()},
                              "narrow": {"tickets": [{}]*5},
                              "balance": {"tickets": [{}]*16},
                              "hole": {"tickets": [{}]*22}}}
            with patch("four_mode_v2_predeclared_shadow.archived_four_modes", side_effect=archived), \
                 patch("four_mode_v2_predeclared_shadow.compare_race",
                       return_value={"status": "historical_comparison_only",
                                     "winning_ticket": "2-1-3",
                                     "modes": {m: dict({f"top{n}": False for n in (3, 5, 10)}, coverage_diagnostic="winner_head_absent")
                                               for m in ("narrow", "hit", "balance", "hole")}}):
                report = evaluate(root)
            self.assertEqual(report["v2_forecasts_seen"], 1)
            self.assertEqual(report["v2_comparable"], 1)
            self.assertEqual(report["groups"]["20261103"]["modes"]["hit"]["top10"], 0)
            self.assertEqual(report["groups"]["20261103"]["miss_reasons"]["hit"]["winner_head_absent"], 1)
            self.assertFalse(report["formal"])
            self.assertFalse(report["independent_remote_first_seen_verified"])


    def test_missing_result_not_confused_with_invalid_result(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "four_mode_forecasts"
            folder.mkdir()
            for code in ("202611030101", "202611030102"):
                (folder / (code+".json")).write_text(json.dumps({
                    "race_code": code, "model_version": VERSION,
                    "input_national_win_rates": [5.0]*6}))
            def archived(code, root):
                return 200, {"model_version": VERSION,
                    "modes": {"hit": {"tickets": tickets()},
                              "narrow": {"tickets": [{}]*5},
                              "balance": {"tickets": [{}]*16},
                              "hole": {"tickets": [{}]*22}}}
            def compared(code, root):
                return {"status": "result_unavailable" if code.endswith("01") else "invalid_result_or_timing"}
            with (patch("four_mode_v2_predeclared_shadow.archived_four_modes", side_effect=archived),
                  patch("four_mode_v2_predeclared_shadow.compare_race", side_effect=compared)):
                report = evaluate(root)
            self.assertEqual(report["v2_forecasts_seen"], 2)
            self.assertEqual(report["v2_comparable"], 0)
            self.assertEqual(report["groups"]["20261103"]["pending_results"], 1)
            self.assertEqual(report["excluded"]["invalid_or_untrusted_result"], 1)

    def test_no_v2_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "four_mode_forecasts").mkdir()
            report = evaluate(td)
            self.assertEqual(report["status"], "no_comparable_v2_yet")
            self.assertEqual(report["v2_comparable"], 0)


if __name__ == "__main__":
    unittest.main()
