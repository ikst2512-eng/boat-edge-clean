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


def report(race_codes,age,window_start,window_end,hit=True):
    rows={code:flags(hit) for code in race_codes}
    hits={m:{f"top{k}":sum(int(r[m][f"top{k}"]) for r in rows.values())
             for k in (3,5,10)} for m in MODES}
    delta={}
    for m in MODES[1:]:
        delta[m]={}
        for k in (3,5,10):
            key=f"top{k}"
            gain=sum(int(r[m][key] and not r["baseline"][key]) for r in rows.values())
            loss=sum(int(r["baseline"][key] and not r[m][key]) for r in rows.values())
            delta[m][key]={"gained":gain,"lost":loss,"net":gain-loss}
    return {"schema":"HOLE_FUTURE_ARTIFACT_BATCH_V1",
            "window_start_jst":window_start,
            "window_end_exclusive_jst":window_end,
            "recheck_lag_days":age,
            "capture_window_complete":False,
            "formal":False,"independent_first_receipt_verified":False,
            "comparable":len(rows),"race_codes":sorted(rows),
            "per_race_flags":rows,"hits":hits,"delta":delta}


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
                other=report([CODE],21,"2026-11-04","2026-11-05",hit=False)
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

    def test_run_history_filtered_before_limit_not_buried_by_pr_checks(self):
        events=[]
        def invoke(args,**kwargs):
            if args[1:3]==["run","list"]:
                self.assertIn("--event",args)
                event=args[args.index("--event")+1]
                events.append(event)
                self.assertEqual(args[args.index("--limit")+1],"2")
                # Simulate large PR activity: it must not appear in either
                # event-filtered query, even if most recent overall.
                listed=([{"databaseId":123,"event":"schedule","conclusion":"success"}]
                        if event=="schedule" else
                        [{"databaseId":124,"event":"workflow_dispatch","conclusion":"success"}])
                return SimpleNamespace(returncode=0,stdout=json.dumps(listed))
            run_id=int(args[3])
            self.assertIn(run_id,(123,124))
            target=Path(args[args.index("--dir")+1])
            target.mkdir(parents=True,exist_ok=True)
            (target/"hole_future_batch.json").write_text(json.dumps(
                report([CODE],0,"2026-11-04","2026-11-06")))
            return SimpleNamespace(returncode=0,stdout="")
        with patch("hole_future_cumulative_rollup.subprocess.run",side_effect=invoke):
            result=fetch_previous("owner/repo",limit=2)
        self.assertEqual(events,["schedule","workflow_dispatch"])
        self.assertEqual(result["runs_listed"],2)
        self.assertEqual(result["event_runs_returned"],
                         {"schedule":1,"workflow_dispatch":1})
        self.assertEqual(result["comparable"],1)
        self.assertEqual(result["hits"]["third_national_rate"]["top10"],1)
    def test_mismatched_age_invalidates_entire_run(self):
        with patch("hole_future_cumulative_rollup.subprocess.run",
                   side_effect=self.fake_gh("tampered")):
            result=fetch_previous("owner/repo",limit=2)
        self.assertEqual(result["daily_artifacts_read"],0)
        self.assertEqual(result["unavailable_daily_run_ids"],[123])

if __name__=="__main__":
    unittest.main()
