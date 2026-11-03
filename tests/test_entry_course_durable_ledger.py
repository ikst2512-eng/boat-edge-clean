import json
import unittest
from datetime import datetime, timezone, timedelta
from entry_course_durable_ledger import prepare,publish,verify_write_access,WRITE_PROBE_PATH,WRITE_PROBE_BYTES
from test_entry_course_late_preview import inputs,FROZEN,T2
from entry_course_late_preview import prepare_late_preview_study

JST=timezone(timedelta(hours=9))

def frozen():
    base,card,batch=inputs()
    obj=prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=1)
    return dict(obj,write_received_at="2026-11-03T18:30:00+09:00",
                 local_snapshot_only=True,independently_archived=False)
def raw(obj):
    return (json.dumps(obj,ensure_ascii=False,sort_keys=True)+"\n").encode()
class LedgerTests(unittest.TestCase):
    def test_first_run_write_probe_uses_exact_nonforecast_bytes(self):
        storage={}
        def get(path):return storage.get(path)
        def put(path,raw):storage[path]=raw
        verdict=verify_write_access(get,put)
        self.assertEqual(verdict["status"],"new_write_probe")
        self.assertFalse(verdict["forecast_record"])
        self.assertFalse(verdict["formal"])
        self.assertEqual(storage[WRITE_PROBE_PATH],WRITE_PROBE_BYTES)
        self.assertFalse(json.loads(WRITE_PROBE_BYTES)["forecast_record"])
    def test_write_probe_is_idempotent_without_overwrite(self):
        storage={WRITE_PROBE_PATH:WRITE_PROBE_BYTES}
        verdict=verify_write_access(storage.get,lambda p,b:self.fail("unexpected write"))
        self.assertEqual(verdict["status"],"existing_write_probe_readback")
        self.assertFalse(verdict["write_permission_tested_this_run"])
    def test_write_probe_rejects_conflicting_or_unreadable_content(self):
        with self.assertRaisesRegex(ValueError,"write_probe_collision"):
            verify_write_access(lambda p:b"changed",lambda p,b:self.fail("write"))
        with self.assertRaisesRegex(ValueError,"write_probe_readback_mismatch"):
            verify_write_access(lambda p:None,lambda p,b:None)
    def test_write_probe_denied_write_propagates(self):
        with self.assertRaisesRegex(ValueError,"unauthorized"):
            verify_write_access(lambda p:None,lambda p,b:(_ for _ in ()).throw(ValueError("unauthorized")))
    def test_prospectively_eligible_capture_has_stable_path(self):
        path=prepare(raw(frozen()),now=datetime(2026,11,3,18,30,20,tzinfo=JST))
        self.assertEqual(path,"entry_course/20261103/202611030708.json")
    def test_remote_write_is_append_only_with_readback(self):
        storage={}
        def read(path):return storage.get(path)
        def create(path,payload):
            self.assertNotIn(path,storage)
            storage[path]=payload
        clock=lambda:datetime(2026,11,3,18,30,20,tzinfo=JST)
        obj=raw(frozen())
        first=publish(obj,read,create,clock=clock)
        self.assertTrue(first["stored"])
        self.assertEqual(first["status"],"new_append_only_late_capture")
        second=publish(obj,read,lambda p,b:self.fail("overwrite"),clock=clock)
        self.assertEqual(second["status"],"already_identical_late_capture")
        self.assertFalse(second["independent_remote_first_seen_verified"])
    def test_conflict_is_never_overwritten(self):
        with self.assertRaisesRegex(ValueError,"immutable_late_capture_conflict"):
            publish(raw(frozen()),lambda path:b"conflict",lambda path,b:self.fail("write"),
                    clock=lambda:datetime(2026,11,3,18,30,20,tzinfo=JST))
    def test_missing_remote_readback_fails(self):
        with self.assertRaisesRegex(ValueError,"late_capture_remote_readback_mismatch"):
            publish(raw(frozen()),lambda path:None,lambda path,b:None,
                    clock=lambda:datetime(2026,11,3,18,30,20,tzinfo=JST))
    def test_publication_crossing_cutoff_is_not_certified(self):
        times=iter([datetime(2026,11,3,18,30,20,tzinfo=JST),
                    datetime(2026,11,3,18,32,tzinfo=JST)])
        store={}
        with self.assertRaisesRegex(ValueError,"remote_published_after_late_cutoff"):
            publish(raw(frozen()),store.get,lambda k,v:store.setdefault(k,v),clock=lambda:next(times))
    def test_t12_reconstruction_cannot_be_published_as_late(self):
        obj=frozen();obj["cutoff_at"]=obj["reference_baseline_cutoff_at"]
        with self.assertRaisesRegex(ValueError,"late_capture_not_before_cutoff"):
            prepare(raw(obj),now=datetime(2026,11,3,18,30,20,tzinfo=JST))
    def test_wrong_label_and_future_receipts_blocked(self):
        obj=frozen();obj["entry_source"]="official_beforeinfo"
        with self.assertRaisesRegex(ValueError,"invalid_late_capture_provenance"):
            prepare(raw(obj),now=datetime(2026,11,3,18,30,20,tzinfo=JST))
        obj=frozen();obj["source_receipts"][0]["received_at"]="2026-11-03T18:32:00+09:00"
        with self.assertRaisesRegex(ValueError,"invalid_late_receipt"):
            prepare(raw(obj),now=datetime(2026,11,3,18,30,20,tzinfo=JST))
if __name__=="__main__":unittest.main()
