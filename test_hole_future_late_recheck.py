"""A newly settled late result is recovered only from archived frozen snapshots."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hole_future_cumulative_rollup import fetch_previous

MODES=("baseline","donor_order","max_ticket_score","third_national_rate")
CODE="202611040101"


def flags(hit):
    return {m:{"top3":False,"top5":False,"top10":hit and m=="third_national_rate"}
            for m in MODES}


def report(race_codes,age,window_start,window_end):
    rows={code:flags(True) for code in race_codes}
    return {"schema":"HOLE_FUTURE_ARTIFACT_BATCH_V1",
            "window_start_jst":window_start,
            "window_end_exclusive_jst":window_end,
            "recheck_lag_days":age,
            "capture_window_complete":False,
            "formal":False,"independent_first_receipt_verified":False,
            "comparable":len(rows),"race_codes":sorted(rows),
            "per_race_flags":rows}


class LateResultTests(unittest.TestCase):
    def fake_gh(self,mode="recovered"):
        def invoke(args,**kwargs):
            if args[1]=="run" and args[2]=="list":
                return SimpleNamespace(returncode=0,
                    stdout=json.dumps([{"databaseId":123,
                         "event":"schedule","conclusion":"success"}]))
            self.assertEqual(args[1:3],["run","download"])
            target=Path(args[args.index("--dir")+1])
            target.mkdir(parents=True,exist_ok=True)
            primary=report([],0,"2026-11-04","2026-11-06")
            (target/"hole_future_batch.json").write_text(json.dumps(primary))
            if mode=="recovered":
                late=report([CODE],7,"2026-11-04","2026-11-05")
                (target/"hole_future_late_7d.json").write_text(json.dumps(late))
            elif mode=="conflicting":
                late=report([CODE],7,"2026-11-04","2026-11-05")
                (target/"hole_future_late_7d.json").write_text(json.dumps(late))
                other=report([CODE],21,"2026-11-04","2026-11-05")
                other["per_race_flags"][CODE]["third_national_rate"]["top10"]=False
                (target/"hole_future_late_21d.json").write_text(json.dumps(other))
            elif mode=="tampered":
                late=report([CODE],21,"2026-11-04","2026-11-05")
                (target/"hole_future_late_7d.json").write_text(json.dumps(late))
            return SimpleNamespace(returncode=0,stdout="")
        return invoke

    def test_late_confirmed_result_recovered_without_regenerating_ticket(self):
        with patch("hole_future_cumulative_rollup.subprocess.run",
                   side_effect=self.fake_gh()):
            result=fetch_previous("owner/repo",limit=2)
        self.assertEqual(result["daily_artifacts_read"],2)
        self.assertEqual(result["late_recheck_reports_read"],1)
        self.assertEqual(result["comparable"],1)
        self.assertEqual(result["hits"]["third_national_rate"]["top10"],1)
        self.assertFalse(result["independent_first_receipt_verified"])

    def test_disagreeing_late_rechecks_are_quarantined(self):
        with patch("hole_future_cumulative_rollup.subprocess.run",
                   side_effect=self.fake_gh("conflicting")):
            result=fetch_previous("owner/repo",limit=2)
        self.assertEqual(result["comparable"],0)
        self.assertEqual(result["conflicted_codes_quarantined"],[CODE])

    def test_mismatched_age_invalidates_entire_run(self):
        with patch("hole_future_cumulative_rollup.subprocess.run",
                   side_effect=self.fake_gh("tampered")):
            result=fetch_previous("owner/repo",limit=2)
        self.assertEqual(result["daily_artifacts_read"],0)
        self.assertEqual(result["unavailable_daily_run_ids"],[123])

if __name__=="__main__":
    unittest.main()
