import csv
import io
import json
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from entry_course_collector import attempt,candidates,BASE
from test_entry_course_late_preview import inputs

JST=timezone(timedelta(hours=9))
NOW=datetime(2026,11,3,18,30,tzinfo=JST)

def encode_csv(row):
    f=io.StringIO();w=csv.DictWriter(f,fieldnames=list(row))
    w.writeheader();w.writerow(row);return f.getvalue().encode("utf-8-sig")

def setup(tmp):
    base,card,batch=inputs()
    root=Path(tmp);folder=root/"research_snapshots";folder.mkdir()
    (folder/(base["race_code"]+".json")).write_text(json.dumps(base))
    history=batch["history"][0]
    urls={BASE+"programs/race_cards/2026/11/02.csv":encode_csv(history["race_card"]),
          BASE+"results/realtime/2026/11/02.csv":encode_csv(history["result"])}
    return root,card,urls

class CollectorTests(unittest.TestCase):
    def test_empty_snapshots_skip_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=attempt(tmp,now=lambda:NOW,prefetch=lambda *a,**k:self.fail("unnecessary fetch"))
            self.assertEqual(out["status"],"no_frozen_baseline_in_late_window")
    def test_only_same_day_pre_cutoff_snapshots_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,urls=setup(tmp)
            self.assertEqual(len(candidates(root,now=NOW)),1)
            self.assertEqual(len(candidates(root,now=datetime(2026,11,3,18,32,tzinfo=JST))),0)
    def test_existing_snapshot_with_complete_research_sources_archives_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,urls=setup(tmp)
            storage={}
            prefetch=lambda day:(urls,{})
            get=lambda p:storage.get(p)
            put=lambda p,raw:storage.setdefault(p,raw)
            out=attempt(root,now=lambda:NOW,prefetch=prefetch,card_reader=lambda *a:card,
                        ledger_ops=(get,put),output_dir=root/"research_captures",min_starts=1)
            self.assertEqual(out["status"],"new_append_only_late_capture")
            self.assertEqual(out["race_code"],"202611030708")
            self.assertEqual(len(storage),1)
            content=json.loads(next(iter(storage.values())))
            self.assertTrue(content["not_equivalent_to_t12"])
            self.assertEqual(len(content["course_plus_st"]),120)
    def test_no_history_is_not_promoted_to_fake_research(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,_,_=setup(tmp)
            out=attempt(root,now=lambda:NOW,prefetch=lambda day:({},{}),
                        card_reader=lambda *args:self.fail("no history, no card"),
                        ledger_ops=(lambda p:None,lambda p,b:self.fail("no publish")))
            self.assertEqual(out["status"],"no_verified_historical_pairs")
            self.assertFalse(out["stored"])
    def test_source_not_used_if_prefetch_crosses_cutoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,_,urls=setup(tmp)
            iter_time=iter((NOW,datetime(2026,11,3,18,32,tzinfo=JST)))
            out=attempt(root,now=lambda:next(iter_time),prefetch=lambda day:(urls,{}))
            self.assertEqual(out["status"],"history_fetch_crossed_late_cutoff")
if __name__=="__main__":unittest.main()
