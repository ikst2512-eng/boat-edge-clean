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
    def test_repeated_t2_job_reuses_original_without_downloading_or_predicting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,evidence=setup(tmp)
            storage={}
            ops=(storage.get,lambda path,data:storage.setdefault(path,data))
            first=attempt(root,now=lambda:NOW,card_reader=lambda *x:card,
                waku_fetch=lambda url:encode(evidence["row"]),
                prefetch=lambda day:self.fail("no history"),ledger_ops=ops)
            self.assertTrue(first["stored"])
            previous=storage[first["path"]]
            second=attempt(root,now=lambda:NOW,
                card_reader=lambda *x:self.fail("must reuse immutable capture"),
                waku_fetch=lambda url:self.fail("no Waku10 refetch"),
                prefetch=lambda day:self.fail("no historical fetch"),
                ledger_ops=(storage.get,lambda path,data:self.fail("no overwrite")))
            self.assertEqual(second["status"],"already_identical_waku10_pilot")
            self.assertEqual(second["sha256"],first["sha256"])
            self.assertEqual(storage[first["path"]],previous)
    def test_corrupt_preexisting_waku10_does_not_recompute_or_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,evidence=setup(tmp)
            key="waku10/20261103/"+evidence["race_code"]+".json"
            existing={key:b"not valid json"}
            with self.assertRaisesRegex(ValueError,"waku10_archive_json_invalid"):
                attempt(root,now=lambda:NOW,
                    card_reader=lambda *x:self.fail("do not reconstruct corrupt evidence"),
                    waku_fetch=lambda url:self.fail("do not overwrite"),
                    ledger_ops=(existing.get,lambda *a:self.fail("no overwrite")))
    def test_original_capture_bound_to_different_t12_baseline_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,evidence=setup(tmp)
            storage={}
            first=attempt(root,now=lambda:NOW,card_reader=lambda *x:card,
                waku_fetch=lambda url:encode(evidence["row"]),
                ledger_ops=(storage.get,lambda key,data:storage.setdefault(key,data)))
            original=json.loads(storage[first["path"]])
            original["reference_t12_top10"]=["1-2-3"]
            storage[first["path"]]=json.dumps(original).encode()+bytes([10])
            with self.assertRaisesRegex(ValueError,"existing_waku10_archive_reference_mismatch"):
                attempt(root,now=lambda:NOW,
                    card_reader=lambda *x:self.fail("do not refetch mismatched archive"),
                    ledger_ops=(storage.get,lambda *a:self.fail("no overwrite")))
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
    def test_insufficient_real_course_runs_report_six_counts_without_saving(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,card,evidence=setup(tmp)
            # A real entry swap breaks the historical frame/course identity;
            # the full 10-frame history must not be passed off as 10 starts
            # in the newly assigned courses.
            card["beforeinfo"]["start_exhibition"][0]["course"]=2
            card["beforeinfo"]["start_exhibition"][1]["course"]=1
            rows=[]
            def reader(day,venue,race):
                rows.append((day,venue,race))
                return card
            out=attempt(root,now=lambda:NOW,
                card_reader=reader,
                skip_historical_fallback=True,
                prefetch=lambda day:self.fail("no unrelated history requests"),
                waku_fetch=lambda url:encode(evidence["row"]),
                ledger_ops=(lambda path:None,
                    lambda path,payload:self.fail("never save insufficient rows")))
            self.assertFalse(out["stored"])
            self.assertEqual(out["status"],"ineligible_waku10_pilot")
            self.assertEqual(out["reason"],
                             "waku10_pilot_insufficient_course_specific_frame_runs")
            self.assertEqual(out["course_sample_counts"],
                             {"1":0,"2":0,"3":9,"4":10,"5":9,"6":9})
            self.assertEqual(out["insufficient_course_boats"],[2,1])
            self.assertEqual(out["minimum_course_starts_required"],8)
            self.assertEqual(out["sample_source"],
                             "third_party_waku10_frame_history")
            self.assertEqual(out["historical_requests"],0)
            self.assertEqual(rows,[("20261103","07","8")])

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
