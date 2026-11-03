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
            "by_race_day_jst":{
                "20261104":{"paired":1,"topn":{
                    "top3":{"baseline":0,"candidate":1,"gained":1,"lost":0},
                    "top5":{"baseline":1,"candidate":1,"gained":0,"lost":0},
                    "top10":{"baseline":1,"candidate":1,"gained":0,"lost":0},
                }}
            },
        }
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
