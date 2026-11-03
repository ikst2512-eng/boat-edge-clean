import json
import unittest
from datetime import datetime,timezone,timedelta
from entry_waku10_durable_ledger import validate_waku10_archive,publish_waku10
from test_entry_waku10_pilot import fixture
from entry_waku10_pilot import prepare_waku10_pilot

JST=timezone(timedelta(hours=9))
NOW=datetime(2026,11,3,18,30,tzinfo=JST)
def sample():
    base,card,e=fixture()
    pilot=prepare_waku10_pilot(base,card,e,frozen_at="2026-11-03T18:29:00+09:00")
    pilot["write_received_at"]="2026-11-03T18:30:00+09:00"
    pilot["local_snapshot_only"]=True
    pilot["independently_archived"]=False
    return pilot
def raw(p):
    return (json.dumps(p,ensure_ascii=False,sort_keys=True)+"\n").encode("utf-8")

class Waku10LedgerTests(unittest.TestCase):
    def test_separate_branch_path_and_append_only_readback(self):
        storage={}
        first=publish_waku10(raw(sample()),storage.get,
                             lambda k,v:storage.setdefault(k,v),clock=lambda:NOW)
        self.assertEqual(first["status"],"new_append_only_waku10_pilot")
        self.assertEqual(first["path"],"waku10/20261103/202611030708.json")
        self.assertFalse(first["formal"])
        second=publish_waku10(raw(sample()),storage.get,
                             lambda k,v:self.fail("overwrite"),clock=lambda:NOW)
        self.assertEqual(second["status"],"already_identical_waku10_pilot")
        self.assertFalse(second["independent_remote_first_seen_verified"])
    def test_new_pilot_not_published_after_cutoff(self):
        with self.assertRaisesRegex(ValueError,"not_pre_cutoff"):
            validate_waku10_archive(raw(sample()),
                  now=datetime(2026,11,3,18,32,tzinfo=JST))
    def test_source_after_freeze_rejected_even_before_cutoff(self):
        p=sample()
        p["source_receipts"][0]["received_at"]="2026-11-03T18:29:30+09:00"
        with self.assertRaisesRegex(ValueError,"late_or_invalid_receipt"):
            validate_waku10_archive(raw(p),now=NOW)
    def test_missing_waku10_source_receipt_rejected(self):
        p=sample()
        p["source_receipts"]=[r for r in p["source_receipts"] if r["source"]!="third_party_waku10"]
        with self.assertRaisesRegex(ValueError,"missing_receipts"):
            validate_waku10_archive(raw(p),now=NOW)
    def test_formal_and_mislabelled_course_st_rejected(self):
        p=sample();p["frame_st_is_not_course_st"]=False
        with self.assertRaisesRegex(ValueError,"header_invalid"):
            validate_waku10_archive(raw(p),now=NOW)
        p=sample();p["formal"]=True
        with self.assertRaisesRegex(ValueError,"header_invalid"):
            validate_waku10_archive(raw(p),now=NOW)
    def test_missing_source_history_starts_rejected(self):
        p=sample();p["sample_counts"]["3"]=7
        with self.assertRaisesRegex(ValueError,"samples_insufficient"):
            validate_waku10_archive(raw(p),now=NOW)
    def test_collision_and_missing_remote_readback_fail(self):
        with self.assertRaisesRegex(ValueError,"immutable_archive_collision"):
            publish_waku10(raw(sample()),lambda p:b"different",
                            lambda p,b:self.fail("overwrite"),clock=lambda:NOW)
        with self.assertRaisesRegex(ValueError,"readback_mismatch"):
            publish_waku10(raw(sample()),lambda p:None,lambda p,b:None,clock=lambda:NOW)
if __name__=="__main__":unittest.main()
