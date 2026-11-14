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
            out=attempt(tmp,waku_enabled=False,now=lambda:NOW,prefetch=lambda *a,**k:self.fail("unnecessary fetch"))
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
            out=attempt(root,waku_enabled=False,now=lambda:NOW,prefetch=prefetch,card_reader=lambda *a:card,
                        ledger_ops=(get,put),output_dir=root/"research_captures",min_starts=1)
            self.assertEqual(out["status"],"new_append_only_late_capture")
            self.assertEqual(out["race_code"],"202611030708")
            self.assertEqual(len(storage),1)
            content=json.loads(next(iter(storage.values())))
            self.assertTrue(content["not_equivalent_to_t12"])
            self.assertEqual(len(content["course_plus_st"]),120)
    def test_no_history_is_not_promoted_to_fake_research(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,_=setup(tmp)
            out=attempt(root,waku_enabled=False,now=lambda:NOW,prefetch=lambda day:({},{}),
                        card_reader=lambda *args:card,
                        ledger_ops=(lambda p:None,lambda p,b:self.fail("no publish")))
            self.assertEqual(out["status"],"no_verified_historical_pairs")
            self.assertFalse(out["stored"])
    def test_insufficient_history_reports_each_boat_course_starts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,urls=setup(tmp)
            out=attempt(root,waku_enabled=False,now=lambda:NOW,prefetch=lambda day:(urls,{}),
                card_reader=lambda *args:card,min_starts=10)
            self.assertEqual(out["status"],"ineligible_late_study")
            self.assertEqual(out["reason"],"late_study_insufficient_course_samples")
            self.assertEqual(len(out["course_start_counts"]),6)
            self.assertEqual(out["insufficient_boats"],[1,2,3,4,5,6])
            self.assertFalse(out["stored"])
    def test_missing_preview_must_not_fetch_any_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,_=setup(tmp)
            card["source_audit"]["beforeinfo"]["status"]="not_published_or_unavailable"
            out=attempt(root,waku_enabled=False,now=lambda:NOW,
                prefetch=lambda day:self.fail("should not download 62 files"),
                card_reader=lambda *args:card,sleep=lambda seconds:None)
            self.assertEqual(out["status"],"preview_not_ready")
            self.assertEqual(out["historical_requests"],0)
            self.assertFalse(out["stored"])
    def test_live_racecard_receives_unpadded_race_number(self):
        # An actual 12-digit ledger key such as ...0708 contains '08',
        # while clean_racecard.racecard accepts '8'. The original race_key
        # and signed research baseline must stay unmodified.
        with tempfile.TemporaryDirectory() as tmp:
            root,card,_=setup(tmp)
            card["source_audit"]["beforeinfo"]["status"]="not_published_or_unavailable"
            observed=[]
            def reader(day,venue,race):
                observed.append((day,venue,race))
                if race!="8":
                    raise ValueError("invalid_race_key")
                return card
            out=attempt(root,waku_enabled=False,now=lambda:NOW,
                prefetch=lambda day:self.fail("do not fetch history without preview"),
                card_reader=reader,preview_poll_limit=1)
            self.assertEqual(observed,[("20261103","07","8")])
            self.assertEqual(out["race_code"],"202611030708")
            self.assertEqual(out["status"],"preview_not_ready")
            self.assertNotEqual(out["reason"],"invalid_race_key")
            self.assertEqual(out["historical_requests"],0)

    def test_wrong_race_preview_must_not_fetch_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,_=setup(tmp)
            card["race_key"]="20261103-07-09"
            out=attempt(root,waku_enabled=False,now=lambda:NOW,
                prefetch=lambda day:self.fail("wrong race should not download"),
                card_reader=lambda *args:card,sleep=lambda seconds:None)
            self.assertEqual(out["status"],"preview_not_ready")
            self.assertIn("not_verified_same_race_preresult",out["reason"])
    def test_source_not_used_if_prefetch_crosses_cutoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,urls=setup(tmp)
            iter_time=iter((NOW,NOW,NOW,NOW,NOW,datetime(2026,11,3,18,32,tzinfo=JST)))
            out=attempt(root,waku_enabled=False,now=lambda:next(iter_time),prefetch=lambda day:(urls,{}),card_reader=lambda *args:card)
            self.assertEqual(out["status"],"history_fetch_crossed_late_cutoff")
if __name__=="__main__":unittest.main()
