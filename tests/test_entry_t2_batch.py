import csv
import io
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from entry_course_collector import attempt_batch
from test_entry_waku10_pilot import fixture
from test_entry_waku10_source import waku

JST=timezone(timedelta(hours=9))
NOW=datetime(2026,11,3,18,29,tzinfo=JST)

def write_csv(rows):
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")

def setup(root,count):
    cards={}
    rows=[]
    for index in range(count):
        baseline,card,evidence=fixture()
        code=f"2026110307{8+index:02d}"
        baseline["race_code"]=code
        card["race_key"]=f"20261103-07-{8+index:02d}"
        row=waku()
        row["レースコード"]=code
        rows.append(row)
        cards[code]=card
        folder=Path(root)/"research_snapshots"
        folder.mkdir(exist_ok=True)
        (folder/(code+".json")).write_text(json.dumps(baseline))
    return cards,write_csv(rows)

class BatchTests(unittest.TestCase):
    def test_three_same_window_races_all_archived_without_history_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,3)
            archive={}
            out=attempt_batch(tmp,now=lambda:NOW,
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:bytes_,
                prefetch=lambda day:self.fail("no 62-file fallback"),
                ledger_ops=(archive.get,lambda path,data:archive.setdefault(path,data)))
            self.assertEqual(out["status"],"t2_batch_completed")
            self.assertEqual(out["attempted_count"],3)
            self.assertEqual(out["stored_count"],3)
            self.assertEqual(out["deferred_count"],0)
            self.assertEqual(len(archive),3)
            self.assertEqual(set(archive),{
                f"waku10/20261103/2026110307{i:02d}.json" for i in (8,9,10)})
            self.assertTrue(all(r["stored"] for r in out["results"]))
    def test_one_race_unavailable_does_not_block_other_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,3)
            archive={}
            def card_reader(d,v,r):
                if r=="09":
                    bad=json.loads(json.dumps(cards[d+v+r]))
                    bad["beforeinfo"]=None
                    return bad
                return cards[d+v+r]
            out=attempt_batch(tmp,now=lambda:NOW,
                card_reader=card_reader,waku_fetch=lambda url:bytes_,
                prefetch=lambda day:self.fail("no 62-file fallback"),
                sleep=lambda sec:self.fail("batch must not sleep"),
                ledger_ops=(archive.get,lambda path,data:archive.setdefault(path,data)))
            self.assertEqual(out["attempted_count"],3)
            self.assertEqual(out["stored_count"],2)
            self.assertEqual(out["results"][1]["status"],"preview_not_ready")
            self.assertEqual(len(archive),2)
    def test_remote_failure_is_marked_and_remaining_races_still_attempted(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,2)
            archive={}
            def create(path,data):
                if path.endswith("0708.json"):
                    raise ValueError("write_denied")
                archive[path]=data
            out=attempt_batch(tmp,now=lambda:NOW,
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:bytes_,
                prefetch=lambda day:self.fail("no historical fetch"),
                ledger_ops=(archive.get,create))
            self.assertEqual(out["status"],"t2_batch_error")
            self.assertEqual(out["errors"],1)
            self.assertEqual(out["stored_count"],1)
            self.assertEqual(out["results"][0]["status"],"collector_error")
            self.assertEqual(out["results"][1]["status"],"new_append_only_waku10_pilot")
    def test_missing_all_baselines_still_reports_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=attempt_batch(tmp,now=lambda:NOW,
                prefetch=lambda day:self.fail("unneeded historical fetch"))
            self.assertEqual(out["status"],"no_frozen_baseline_in_late_window")
            self.assertEqual(out["baseline_audit"]["status"],
                             "missing_current_day_research_snapshots")
    def test_batch_size_guard(self):
        with self.assertRaisesRegex(ValueError,"batch_size"):
            attempt_batch(".",now=lambda:NOW,max_per_run=100)
if __name__=="__main__":
    unittest.main()
