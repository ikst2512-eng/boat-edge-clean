import json
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from entry_course_collector import attempt
from test_entry_waku10_pilot import fixture
from test_entry_waku10_source import encode

JST=timezone(timedelta(hours=9))
NOW=datetime(2026,11,3,18,30,tzinfo=JST)

def setup(tmp):
    base,card,evidence=fixture()
    folder=Path(tmp)/"research_snapshots"
    folder.mkdir()
    (folder/(base["race_code"]+".json")).write_text(json.dumps(base))
    return Path(tmp),card,evidence

class CollectorWaku10Tests(unittest.TestCase):
    def test_true_source_backed_waku10_pilot_archives_without_62_old_downloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,evidence=setup(tmp)
            storage={}
            out=attempt(root,now=lambda:NOW,
                card_reader=lambda *x:card,
                prefetch=lambda day:self.fail("62 historical requests unnecessary"),
                waku_fetch=lambda url:encode(evidence["row"]),
                ledger_ops=(storage.get,lambda path,data:storage.setdefault(path,data)))
            self.assertTrue(out["stored"])
            self.assertEqual(out["status"],"new_append_only_waku10_pilot")
            self.assertEqual(out["sample_counts"],{str(i):n for i,n in enumerate([10,10,9,10,9,9],1)})
            self.assertEqual(len(storage),1)
            content=json.loads(next(iter(storage.values())))
            self.assertTrue(content["frame_st_is_not_course_st"])
            self.assertEqual(len(content["waku10_course"]),120)
            self.assertEqual(len(content["waku10_course_plus_frame_st_proxy"]),120)
            self.assertFalse(content["formal"])
    def test_swapped_course_does_not_fake_10_qualified_starts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,evidence=setup(tmp)
            card["beforeinfo"]["start_exhibition"][0]["course"]=2
            card["beforeinfo"]["start_exhibition"][1]["course"]=1
            result=attempt(root,now=lambda:NOW,
                card_reader=lambda *x:card,prefetch=lambda day:({},{}),
                waku_fetch=lambda url:encode(evidence["row"]))
            self.assertFalse(result["stored"])
            self.assertEqual(result["status"],"no_verified_historical_pairs")
            self.assertEqual(result["waku10_pilot_reason"],
                             "waku10_pilot_insufficient_course_specific_frame_runs")
    def test_failed_branch_write_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,evidence=setup(tmp)
            with self.assertRaisesRegex(ValueError,"denied"):
                attempt(root,now=lambda:NOW,
                    card_reader=lambda *x:card,
                    prefetch=lambda day:self.fail("unexpected fallback"),
                    waku_fetch=lambda url:encode(evidence["row"]),
                    ledger_ops=(lambda p:None,
                        lambda p,raw:(_ for _ in ()).throw(ValueError("denied"))))
if __name__=="__main__":unittest.main()
