import base64
import hashlib
import json
import unittest
from entry_course_schedule_write_audit import inspect_write_witness

REPO="ikst2512-eng/boat-edge-clean"
DAY="20261103"
RUN=41612345678
AT="2026-11-03T12:31:00+00:00"


def example(*,run_id=str(RUN),kind="t12",date=DAY,observed=AT,
            forecast=False):
    return {"schema":"ENTRY_SCHEDULED_ACTIONS_WRITE_PROOF_V1",
            "date_jst":date,"workflow_kind":kind,"event_name":"schedule",
            "run_id":run_id,"received_at_local":observed,
            "forecast_record":forecast,"formal":False,
            "independent_github_server_first_seen_verified":False}


def evidence(item):
    raw=(json.dumps(item,sort_keys=True)+"\n").encode()
    sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    return raw,sha


def call(kind="t12",*,data=None,run_ids=(RUN,),blob_override=None,tree_override=None):
    item=data if data is not None else example(kind=kind)
    raw,sha=evidence(item)
    path=f"operations/scheduled-write-proof/{DAY}/{kind}.json"
    if tree_override is None:
        tree=[{"path":path,"type":"blob","sha":sha if blob_override is None else blob_override}]
    else:
        tree=tree_override
    starts=[{"id":i,"created_at":"2026-11-03T12:25:00+00:00",
             "status":"completed","conclusion":"success"} for i in run_ids]
    def get(route):
        return {"sha":sha,"encoding":"base64","content":base64.b64encode(raw).decode()}
    return inspect_write_witness(DAY,kind,tree,starts,get,repository=REPO)


class WitnessTests(unittest.TestCase):
    def test_exact_runner_scheduled_event_and_sha_are_linked(self):
        x=call()
        self.assertEqual(x["status"],"scheduled_write_proof_run_linked")
        self.assertTrue(x["write_proven"])
        self.assertTrue(x["git_blob_sha_verified"])
        self.assertFalse(x["forecast_record"])
        self.assertFalse(x["independent_server_first_seen_verified"])
    def test_separate_t2_runner_witness(self):
        x=call("t2",data=example(kind="t2"))
        self.assertTrue(x["write_proven"])
    def test_missing_witness_does_not_turn_successful_run_into_write_proof(self):
        x=call(tree_override=[])
        self.assertEqual(x["status"],"scheduled_write_proof_missing")
        self.assertFalse(x["write_proven"])
    def test_manual_or_pr_runner_not_in_schedule_history(self):
        x=call(run_ids=())
        self.assertEqual(x["status"],"scheduled_write_proof_run_not_in_schedule_history")
        self.assertFalse(x["write_proven"])
    def test_nonforecast_flag_is_required(self):
        x=call(data=example(forecast=True))
        self.assertEqual(x["status"],"scheduled_write_proof_invalid_or_unreadable")
        self.assertFalse(x["write_proven"])
    def test_wrong_day_cannot_be_reused(self):
        x=call(data=example(date="20261102"))
        self.assertFalse(x["write_proven"])
    def test_cross_kind_witness_invalid(self):
        x=call(data=example(kind="t2"))
        self.assertFalse(x["write_proven"])
    def test_witness_local_clock_must_follow_schedule_created_time(self):
        x=call(data=example(observed="2026-11-03T12:20:00+00:00"))
        self.assertEqual(x["status"],"scheduled_write_proof_invalid_or_unreadable")
    def test_tampered_git_blob_is_not_certified(self):
        x=call(blob_override="f"*40)
        self.assertEqual(x["status"],"scheduled_write_proof_invalid_or_unreadable")
    def test_malformed_run_id_not_certified(self):
        x=call(data=example(run_id="manual"))
        self.assertFalse(x["write_proven"])


if __name__=="__main__":unittest.main()
