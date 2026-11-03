import json
import unittest
from datetime import datetime,timezone,timedelta
from entry_course_scheduled_write_probe import schedule_canary,from_environment

JST=timezone(timedelta(hours=9))
NOW=datetime(2026,11,4,10,25,tzinfo=JST)

class ScheduledProbeTests(unittest.TestCase):
    def test_schedule_runner_can_create_and_read_only_once_per_day(self):
        store={}
        created=[]
        def create(path,payload):
            created.append(path)
            if path in store:
                self.fail("not allowed to overwrite")
            store[path]=payload
        result=schedule_canary("t12",read=store.get,create=create,
            now=NOW,event_name="schedule",run_id="41640012345")
        self.assertEqual(result["status"],"new_scheduled_runner_write_proof")
        self.assertTrue(result["write_permission_tested_this_run"])
        self.assertEqual(result["path"],
                         "operations/scheduled-write-proof/20261104/t12.json")
        item=json.loads(store[result["path"]])
        self.assertIs(item["forecast_record"],False)
        self.assertIs(item["formal"],False)
        self.assertFalse(item["independent_github_server_first_seen_verified"])
        later=schedule_canary("t12",read=store.get,create=create,
            now=NOW,event_name="schedule",run_id="41640012346")
        self.assertEqual(later["status"],"previous_schedule_proof_readback")
        self.assertFalse(later["write_permission_tested_this_run"])
        self.assertEqual(later["first_witness_run_id"],"41640012345")
        self.assertEqual(len(created),1)
    def test_twelve_and_two_have_separate_canaries(self):
        store={}
        for kind in ("t12","t2"):
            outcome=schedule_canary(kind,read=store.get,
                create=lambda k,v:store.setdefault(k,v),
                now=NOW,event_name="schedule",run_id="12345")
            self.assertEqual(outcome["status"],"new_scheduled_runner_write_proof")
        self.assertEqual(len(store),2)
    def test_pr_and_manual_dispatch_never_create_proof(self):
        for event in ("pull_request","workflow_dispatch",None):
            output=schedule_canary("t2",read=lambda key:self.fail("should not read"),
                create=lambda key,data:self.fail("should not create"),
                now=NOW,event_name=event,run_id="12345")
            self.assertEqual(output["status"],"skipped_non_schedule")
            self.assertFalse(output["write_permission_tested_this_run"])
    def test_malformed_or_mismatched_existing_file_fails_closed(self):
        path="operations/scheduled-write-proof/20261104/t2.json"
        with self.assertRaisesRegex(ValueError,"existing_invalid_json"):
            schedule_canary("t2",read=lambda p:b"invalid",
                            create=lambda p,b:self.fail("must not rewrite"),
                            now=NOW,event_name="schedule",run_id="1")
        bad={"schema":"ENTRY_SCHEDULED_ACTIONS_WRITE_PROOF_V1",
             "date_jst":"20261103","workflow_kind":"t2",
             "event_name":"schedule","run_id":"1","formal":False,
             "forecast_record":False}
        with self.assertRaisesRegex(ValueError,"existing_invalid"):
            schedule_canary("t2",read=lambda p:json.dumps(bad).encode(),
                            create=lambda p,b:self.fail("must not overwrite"),
                            now=NOW,event_name="schedule",run_id="1")
    def test_remote_readback_failure_is_not_success(self):
        with self.assertRaisesRegex(ValueError,"remote_readback_failed"):
            schedule_canary("t12",read=lambda path:None,
                create=lambda path,data:None,
                now=NOW,event_name="schedule",run_id="123")
    def test_missing_run_id_rejected_only_for_schedule(self):
        with self.assertRaisesRegex(ValueError,"missing_run_id"):
            schedule_canary("t12",read=lambda path:None,
                create=lambda path,data:self.fail("must not write"),
                now=NOW,event_name="schedule",run_id=None)
    def test_local_time_partition_when_utc_date_differs(self):
        store={}
        current=datetime(2026,11,3,16,1,tzinfo=timezone.utc)
        output=from_environment("t2",store.get,lambda p,b:store.setdefault(p,b),
            environ={"GITHUB_EVENT_NAME":"schedule","GITHUB_RUN_ID":"42"},
            now=current)
        self.assertIn("/20261104/",output["path"])
if __name__=="__main__":unittest.main()
