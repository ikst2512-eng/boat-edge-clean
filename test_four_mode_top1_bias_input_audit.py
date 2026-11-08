"""Guardrails for outcome-blind archived Top1 concentration audit."""
import json
import tempfile
import unittest
from pathlib import Path

from clean_four_modes import rank_modes
from research_model import probabilities, COUNTS, TICKETS
from four_mode_top1_bias_input_audit import audit, verified_pre_result_snapshot


RATES_A = [4.62, 5.35, 3.92, 5.86, 4.48, 3.18]
RATES_B = [4.76, 2.64, 5.35, 5.52, 3.92, 5.49]


def write_forecast(root, code, rates):
    day=code[:8]
    iso_day = f"{day[:4]}-{day[4:6]}-{day[6:8]}"
    p=root/"four_mode_forecasts"/(code+".json")
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code": code,
        "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
        "status": "provisional",
        "target_rates_not_proven": True,
        "generated_at_jst": iso_day+"T08:00:00+09:00",
        "deadline_jst": iso_day+"T08:30:00+09:00",
        "input_national_win_rates": rates,
        "beforeinfo": "optional_not_in_snapshot",
        "modes": rank_modes(probabilities(rates)),
    }),encoding="utf-8")
    return p


class Top1BiasInputAuditTests(unittest.TestCase):
    def test_fixed_prior_within_same_first_boat_cannot_use_rate_differences(self):
        self.assertEqual(sum(COUNTS),1000)
        self.assertEqual(len(COUNTS),120)
        a,b=(1,2,4),(1,2,3)
        assert COUNTS[TICKETS.index(a)] == 60
        assert COUNTS[TICKETS.index(b)] == 59
        expected=(60.5/59.5)
        ratios=[]
        for rates in (RATES_A,RATES_B):
            p=dict(probabilities(rates))
            ratio=p[a]/p[b]
            self.assertAlmostEqual(ratio,expected,places=12)
            ratios.append(ratio)
            # 1-2-4 ranks over 1-2-3 for EVERY valid rate vector
            # because both combinations have head=1, and the head
            # weight cancels from the ratio.
            self.assertGreater(p[a],p[b])
        self.assertAlmostEqual(ratios[0],ratios[1],places=12)

    def test_two_different_races_share_three_mode_top1(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            write_forecast(root,"202611080101",RATES_A)
            write_forecast(root,"202611080102",RATES_B)
            r=audit(root,"20261108")
            self.assertEqual(r["file_count"],2)
            self.assertEqual(r["valid_v2_saved"],2)
            self.assertEqual(r["distinct_national_win_rate_vectors"],2)
            self.assertEqual(r["same_top1_narrow_hit_balance"],2)
            self.assertEqual(r["top1_combos_by_mode"]["narrow"],{"1-2-4":2})
            self.assertEqual(r["top1_combos_by_mode"]["hit"],{"1-2-4":2})
            self.assertEqual(r["top1_combos_by_mode"]["balance"],{"1-2-4":2})
            self.assertEqual(r["beforeinfo_flags"],{"optional_not_in_snapshot":2})
            self.assertEqual(r["hit_top2_different_head_count"],0)
            self.assertEqual(r["distinct_first_5_ticket_sets_by_mode"]["narrow"],1)
            self.assertFalse(r["confirmed_results_read"])
            self.assertFalse(r["formal"])
            self.assertFalse(r["model_promotion_allowed"])

    def test_invalid_archive_does_not_inflate_denominator(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            write_forecast(root,"202611080101",RATES_A)
            file=write_forecast(root,"202611080102",RATES_B)
            raw=json.loads(file.read_text())
            raw["modes"]["hit"]["tickets"][0]["combo"]="1-1-4"
            file.write_text(json.dumps(raw))
            r=audit(root,"20261108")
            self.assertEqual(r["file_count"],2)
            self.assertEqual(r["valid_v2_saved"],1)
            self.assertEqual(len(r["invalid_archives"]),1)
            self.assertEqual(r["same_top1_narrow_hit_balance_pct"],100.0)

    def test_syntactically_valid_ticket_reordering_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            file=write_forecast(root,"202611080101",RATES_A)
            raw=json.loads(file.read_text())
            a=raw["modes"]["hit"]["tickets"]
            a[0],a[1]=a[1],a[0]
            file.write_text(json.dumps(raw),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,
                                        "stored_ticket_not_reproduced_from_inputs"):
                verified_pre_result_snapshot(raw,"202611080101")
            report=audit(root,"20261108")
            self.assertEqual(report["file_count"],1)
            self.assertEqual(report["valid_v2_saved"],0)
            self.assertEqual(len(report["invalid_archives"]),1)
            self.assertFalse(report["formal"])

    def test_plausible_but_forged_probability_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            file=write_forecast(root,"202611080101",RATES_A)
            raw=json.loads(file.read_text())
            raw["modes"]["balance"]["tickets"][0]["p"] += 0.01
            file.write_text(json.dumps(raw),encoding="utf-8")
            report=audit(root,"20261108")
            self.assertEqual(report["valid_v2_saved"],0)
            self.assertEqual(report["invalid_archives"][0]["reason"],
                             "stored_ticket_not_reproduced_from_inputs")

    def test_result_presence_is_not_read_or_scored(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            write_forecast(root,"202611080101",RATES_A)
            file=root/"confirmed_results"/"202611080101.json"
            file.parent.mkdir()
            file.write_bytes(b"not-even-json")
            r=audit(root,"20261108")
            self.assertEqual(r["valid_v2_saved"],1)
            self.assertFalse(r["confirmed_results_read"])
            self.assertEqual(r["status"],"reference_only_not_accuracy")

    def test_empty_day_is_unknown_not_zero_concentration(self):
        with tempfile.TemporaryDirectory() as d:
            r=audit(Path(d),"20261109")
            self.assertEqual(r["file_count"],0)
            self.assertIsNone(r["same_top1_narrow_hit_balance_pct"])
            self.assertIsNone(r["hit_top2_different_head_pct"])
            self.assertFalse(r["coverage_of_unsaved_races_verified"])

    def test_invalid_day_and_bad_rank_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid_audit_day"):
            audit(Path("."),"2026-11-08")
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            f=write_forecast(root,"202611080101",RATES_A)
            raw=json.loads(f.read_text())
            raw["modes"]["hit"]["tickets"]=raw["modes"]["hit"]["tickets"][:3]
            with self.assertRaisesRegex(ValueError,"invalid_mode_ticket_count"):
                verified_pre_result_snapshot(raw,"202611080101")


if __name__ == "__main__":
    unittest.main()
