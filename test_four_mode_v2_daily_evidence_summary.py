"""Test report refuses misleading success metrics from incomplete evidence."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from four_mode_v2_daily_evidence_summary import summarize

A = "202611040101"


class EvidenceSummaryTests(unittest.TestCase):
    def setUp(self):
        self.capture = {
            "schema":"V2_THIRD_RATE_FROZEN_NIGHTLY_ARTIFACT_AUDIT_V1",
            "status":"frozen_artifacts_scored_limited_cohort",
            "cohort_completeness_verified":True,
            "frozen":1,"paired":1,"pending_results":0,
            "pending_or_unknown_runs":0,"unsuccessful_runs":0,
            "missing_or_failed_artifacts":[],"bad_validation_runs":[],
            "race_codes_paired":[A],
            "paired_race_scores":[{"race_code":A,"topn":{
                "top1":{"baseline":0,"candidate":0,"gained":0,"lost":0},
                "top3":{"baseline":0,"candidate":1,"gained":1,"lost":0},
                "top5":{"baseline":1,"candidate":1,"gained":0,"lost":0},
                "top10":{"baseline":1,"candidate":1,"gained":0,"lost":0},
            }}],
            "by_race_day_jst":{
                "20261104":{"paired":1,"race_codes":[A],"topn":{
                    "top1":{"baseline":0,"candidate":0,"gained":0,"lost":0},
                    "top3":{"baseline":0,"candidate":1,"gained":1,"lost":0},
                    "top5":{"baseline":1,"candidate":1,"gained":0,"lost":0},
                    "top10":{"baseline":1,"candidate":1,"gained":0,"lost":0},
                }}
            },
        }
        self.capture["topn"] = {
            key: dict(vals) for key, vals in
            self.capture["by_race_day_jst"]["20261104"]["topn"].items()}
        self.ledger = {
            "schema":"V2_THIRD_RATE_DURABLE_LEDGER_SCORE_V1",
            "status":"durable_frozen_evidence_scored",
            "frozen":1,"invalid_files":[],
        }
        self.reconciliation = {
            "schema":"V2_THIRD_RATE_CAPTURE_LEDGER_RECONCILIATION_V1",
            "status":"bounded_frozen_roster_matched",
        }

    def test_verified_paired_day_shows_numerical_topn_delta(self):
        md = summarize(self.capture,self.ledger,self.reconciliation)
        self.assertIn("Evidence ready for bounded research comparison: yes",md)
        self.assertIn("| TOP1 | 0 | 0 | +0 |",md)
        self.assertIn("| TOP3 | 0 | 1 | +1 |",md)
        self.assertIn("| TOP5 | 1 | 1 | +0 |",md)
        self.assertIn("Not certified:",md)
        self.assertNotIn("accuracy withheld",md)

    def test_broken_ledger_or_capture_withholds_hit_claims(self):
        for report,field,value in (
            ("reconciliation","status","incomplete_capture_inventory"),
            ("ledger","status","ledger_branch_unavailable"),
            ("capture","cohort_completeness_verified",False),
            ("capture","status","incomplete_capture_run_outcomes"),
        ):
            with self.subTest(report=report,field=field):
                obj=getattr(self,report)
                original=obj[field]
                obj[field]=value
                md=summarize(self.capture,self.ledger,self.reconciliation)
                self.assertIn("TopN accuracy withheld",md)
                self.assertNotIn("| TOP3 |",md)
                obj[field]=original

    def test_missing_top1_withholds_results_instead_of_counting_miss(self):
        del self.capture["paired_race_scores"][0]["topn"]["top1"]
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("TopN accuracy withheld", md)
        self.assertNotIn("| TOP1 |", md)
        self.assertNotIn("| TOP3 |", md)

    def test_top1_aggregate_mismatch_withholds_all_scores(self):
        self.capture["topn"]["top1"]["candidate"] = 1
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("TopN accuracy withheld", md)
        self.assertNotIn("| TOP1 |", md)

    def test_impossible_top1_hit_progression_withholds_entire_table(self):
        # Keep the aggregate consistent with the forged individual score.
        for topn in (self.capture["paired_race_scores"][0]["topn"],
                     self.capture["by_race_day_jst"]["20261104"]["topn"],
                     self.capture["topn"]):
            topn["top1"] = {"baseline":0, "candidate":1,
                             "gained":1, "lost":0}
            topn["top3"] = {"baseline":0, "candidate":0,
                             "gained":0, "lost":0}
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("TopN accuracy withheld", md)
        self.assertNotIn("| TOP1 |", md)
        self.assertNotIn("| TOP3 |", md)

    def test_no_paired_results_never_claims_comparison_ready(self):
        self.capture.update({"paired": 0, "by_race_day_jst": {}})
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("Evidence ready for bounded research comparison: no", md)
        self.assertIn("TopN accuracy withheld", md)

    def test_daily_paired_count_must_match_total(self):
        self.capture["paired"] = 2
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("Evidence ready for bounded research comparison: no", md)
        self.assertNotIn("| TOP3 |", md)

    def test_invalid_second_day_cannot_be_silently_skipped(self):
        self.capture["paired"] = 2
        self.capture["by_race_day_jst"]["20261105"] = {
            "paired": 1, "topn": {"top3": {"baseline": 1}}}
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("TopN accuracy withheld", md)
        self.assertNotIn("| TOP3 |", md)

    def test_per_day_topn_must_match_global_topn_if_supplied(self):
        self.capture["topn"] = {
            k: dict(v) for k,v in
            self.capture["by_race_day_jst"]["20261104"]["topn"].items()}
        self.capture["topn"]["top3"]["candidate"] = 0
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("Evidence ready for bounded research comparison: no", md)
        self.assertNotIn("| TOP3 |", md)

    def test_same_count_wrong_daily_race_id_must_withhold_accuracy(self):
        self.capture["by_race_day_jst"]["20261104"]["race_codes"] = [
            "202611040102"]
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("Evidence ready for bounded research comparison: no", md)
        self.assertNotIn("| TOP3 |", md)

    def test_same_count_wrong_global_scored_identity_must_withhold(self):
        self.capture["paired_race_scores"] = [{"race_code":"202611040102"}]
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("TopN accuracy withheld", md)
        self.assertNotIn("| TOP3 |", md)

    def test_missing_global_totals_cannot_claim_matched_comparison(self):
        self.capture.pop("topn")
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("TopN accuracy withheld", md)

    def test_duplicate_daily_roster_cannot_show_comparison(self):
        self.capture["paired"] = 2
        group = self.capture["by_race_day_jst"]["20261104"]
        group["paired"] = 2
        group["race_codes"] = [A, A]
        self.capture["race_codes_paired"] = [A, "202611040102"]
        self.capture["paired_race_scores"] = [
            {"race_code":A}, {"race_code":"202611040102"}]
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertNotIn("| TOP3 |", md)

    def test_forged_aggregate_top3_gain_is_withheld(self):
        # Both the day and global table claim a gain, but the frozen
        # individual race result records a miss for candidate Top3.
        self.capture["paired_race_scores"][0]["topn"]["top3"] = {
            "baseline":0,"candidate":0,"gained":0,"lost":0}
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("Evidence ready for bounded research comparison: no", md)
        self.assertNotIn("| TOP3 |", md)

    def test_invalid_per_race_hit_boolean_cannot_show_gain(self):
        self.capture["paired_race_scores"][0]["topn"]["top3"]["candidate"] = True
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertIn("TopN accuracy withheld", md)
        self.assertNotIn("| TOP3 |", md)

    def test_per_race_gain_loss_arithmetic_must_be_consistent(self):
        self.capture["paired_race_scores"][0]["topn"]["top3"]["lost"] = 1
        md = summarize(self.capture, self.ledger, self.reconciliation)
        self.assertNotIn("| TOP3 |", md)

    def test_missing_reports_are_diagnostic_not_zero_hits(self):
        md=summarize(None,None,None)
        self.assertIn("Capture audit: unavailable",md)
        self.assertIn("TopN accuracy withheld",md)
        self.assertNotIn("| TOP3 |",md)

    def test_missing_per_day_score_fields_never_show_partial_hit_table(self):
        del self.capture["by_race_day_jst"]["20261104"]["topn"]["top3"]["lost"]
        md=summarize(self.capture,self.ledger,self.reconciliation)
        self.assertNotIn("| TOP3 |",md)

    def test_cli_preserves_summary_if_all_inputs_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"daily.md"
            proc=subprocess.run([
                sys.executable,
                str(Path(__file__).with_name("four_mode_v2_daily_evidence_summary.py")),
                "--capture",str(Path(tmp)/"capture.json"),
                "--ledger",str(Path(tmp)/"ledger.json"),
                "--reconciliation",str(Path(tmp)/"reconciliation.json"),
                "--output",str(output),
            ],capture_output=True,text=True,timeout=20)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertIn("TopN accuracy withheld",output.read_text())

if __name__ == "__main__":
    unittest.main()
