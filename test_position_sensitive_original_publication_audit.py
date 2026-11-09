"""No-network synthetic regression tests for actual source first-add log audit."""
import json
import subprocess
import unittest

from position_sensitive_original_publication_audit import (
    audit_log, SCHEMA,
)

COMMIT = "b"*40
BASE = "c"*40
TIP = "a"*40
DAY = "20261109"


def line(timestamp, text):
    return (timestamp+" "+text+"\n").encode()


def full_log(n=2):
    staging = {"excluded":{}, "new_untracked_json":n, "staged_valid":n}
    states = {
        "source_capture":"success", "receipt_staging":"success",
        "publication":"pushed_to_main"
    }
    verdict = {
        "schema":"FOUR_MODE_FINAL_EVIDENCE_VERDICT_V1",
        "status":"passed",
        "detail":{
            "status":"published_with_durable_early_observation",
            "evidence_required":True, "published":n,
        },
    }
    return b"".join([
        line("2026-11-09T01:38:08.100Z",
             "Four-mode staging diagnostic: "+json.dumps(staging,sort_keys=True)),
        line("2026-11-09T01:38:16.100Z",
             "Published four-mode commit: "+COMMIT+f" new archives: {n}"),
        line("2026-11-09T01:38:55.100Z",
             "Four-mode execution stages: "+json.dumps(states,sort_keys=True)),
        line("2026-11-09T01:38:56.100Z",
             "FOUR_MODE_EVIDENCE_VERDICT="+json.dumps(verdict,sort_keys=True)),
    ])


def empty_log():
    staging = {"excluded":{},"new_untracked_json":0,"staged_valid":0}
    states = {
        "source_capture":"success","receipt_staging":"success",
        "publication":"no_eligible_candidates",
    }
    verdict = {
        "schema":"FOUR_MODE_FINAL_EVIDENCE_VERDICT_V1",
        "status":"passed",
        "detail":{"status":"no_new_forecasts","evidence_required":False},
    }
    return b"".join([
        line("2026-11-09T02:36:37.020Z",
             "Four-mode staging diagnostic: "+json.dumps(staging,sort_keys=True)),
        line("2026-11-09T02:36:37.265Z",
             "No new cutoff-safe four-mode candidates"),
        line("2026-11-09T02:36:38.270Z",
             "Four-mode execution stages: "+json.dumps(states,sort_keys=True)),
        line("2026-11-09T02:36:38.391Z",
             "FOUR_MODE_EVIDENCE_VERDICT="+json.dumps(verdict,sort_keys=True)),
    ])


class Git:
    def __init__(self):
        self.commands = []
        self.changes = [
            "A\tfour_mode_forecasts/202611090101.json",
            "A\tfour_mode_forecasts/202611090102.json",
        ]
        self.ancestor = True

    def __call__(self,*argv):
        self.commands.append(argv)
        if argv[0]=="rev-parse":
            self.assert_path(argv, "refs/remotes/origin/main^{commit}")
            return (TIP+"\n").encode()
        if argv[0]=="rev-list":
            return (COMMIT+" "+BASE+"\n").encode()
        if argv[0]=="merge-base":
            if not self.ancestor:
                raise subprocess.CalledProcessError(1, argv)
            return b""
        if argv[0]=="diff-tree":
            return ("\n".join(self.changes)+"\n").encode()
        raise AssertionError("unsafe_git_command"+repr(argv))

    @staticmethod
    def assert_path(argv, expected):
        if argv[-1]!=expected:
            raise AssertionError("incorrect_git_ref")


class SourcePublicationLogTests(unittest.TestCase):
    def test_real_source_commit_first_add_but_not_remote_first_receipt(self):
        git = Git()
        out=audit_log(DAY,42546585986,full_log(),git)
        self.assertEqual(out["schema"],SCHEMA)
        self.assertEqual(out["first_added_originals_in_current_main_history"],2)
        self.assertEqual(out["reported_publication_commit_sha"],COMMIT)
        self.assertEqual(out["reported_publication_parent_sha"],BASE)
        self.assertEqual(out["main_snapshot_sha"],TIP)
        self.assertFalse(out["current_main_git_first_add_is_first_remote_receipt"])
        self.assertFalse(out["capture_success_proves_research_candidate_publication"])
        self.assertFalse(out["formal"])
        self.assertFalse(out["promotion_allowed"])
        self.assertFalse(any("confirmed_results" in str(c) for c in git.commands))

    def test_green_but_no_new_files_does_not_read_git_or_claim_publication(self):
        git=Git()
        result=audit_log(DAY,42551875149,empty_log(),git)
        self.assertEqual(result["first_added_originals_in_current_main_history"],0)
        self.assertIsNone(result["reported_publication_commit_sha"])
        self.assertEqual(result["status"],
                         "capture_job_succeeded_with_zero_new_original_forecasts")
        self.assertEqual(git.commands,[])
        self.assertEqual(result["candidate_first_remote_receipts_verified"],0)

    def test_log_echoed_source_code_cannot_be_treated_as_stdout(self):
        git=Git()
        prefix=line("2026-11-09T01:38:08.050Z",
                    '\x1b[36;1mprint("Published four-mode commit:",sha)\x1b[0m')
        out=audit_log(DAY,42,prefix+full_log(),git)
        self.assertEqual(out["logged_staged_new_originals"],2)
        self.assertFalse(out["formal"])

    def test_published_count_disagrees_with_first_add_diff(self):
        git=Git()
        git.changes.pop()
        with self.assertRaisesRegex(ValueError, "actual_main_commit_first_add_count_mismatch"):
            audit_log(DAY,42,full_log(),git)

    def test_candidate_or_results_path_in_source_commit_rejected(self):
        for different in (
            "A\tposition_sensitive_research/202611090101.json",
            "M\tfour_mode_forecasts/202611090101.json",
            "A\tconfirmed_results/202611090101.json",
            "A\tfour_mode_forecasts/202611080101.json",
        ):
            git=Git()
            git.changes[0]=different
            with self.subTest(change=different), self.assertRaises(ValueError):
                audit_log(DAY,42,full_log(),git)

    def test_current_main_missing_published_commit_fails(self):
        git=Git()
        git.ancestor=False
        with self.assertRaisesRegex(ValueError,"capture_publication_not_in_main_history"):
            audit_log(DAY,42,full_log(),git)

    def test_mutated_green_job_no_eligible_status_rejected(self):
        log=empty_log().replace(b'"staged_valid": 0',b'"staged_valid": 1')
        with self.assertRaises(ValueError):
            audit_log(DAY,42,log,Git())
        log=empty_log()+line("2026-11-09T02:36:38.500Z",
                             "Published four-mode commit: "+COMMIT+" new archives: 1")
        with self.assertRaisesRegex(ValueError,"ambiguous_capture_publication_status"):
            audit_log(DAY,42,log,Git())

    def test_missing_duplicate_and_reversed_stdout_fails_closed(self):
        log=full_log()
        with self.assertRaisesRegex(ValueError,"capture_stdout_evidence_missing"):
            audit_log(DAY,42,log.split(b"FOUR_MODE_EVIDENCE_VERDICT=")[0],Git())
        with self.assertRaisesRegex(ValueError,"duplicated_capture_stdout_marker"):
            audit_log(DAY,42,log+log,Git())
        modified=log.replace(b"2026-11-09T01:38:55.100Z",
                             b"2026-11-09T01:38:15.000Z")
        with self.assertRaisesRegex(ValueError,"capture_event_time_regression"):
            audit_log(DAY,42,modified,Git())

    def test_invalid_day_large_log_unknown_run_rejected(self):
        for day in ("20261108","20270101","2026-11-09","../../../"):
            git=Git()
            with self.subTest(day=day), self.assertRaises(ValueError):
                audit_log(day,42,full_log(),git)
            self.assertEqual(git.commands,[])
        with self.assertRaises(ValueError):
            audit_log(DAY,0,full_log(),Git())
        with self.assertRaisesRegex(ValueError,"oversized"):
            audit_log(DAY,42,b"x"*2000001,Git())

    def test_wrong_verdict_against_success_staging_refused(self):
        log=full_log().replace(b'"evidence_required": true',
                               b'"evidence_required": false')
        with self.assertRaisesRegex(ValueError,"published_commit_and_staging_disagree"):
            audit_log(DAY,42,log,Git())
        log=full_log().replace(b"new archives: 2",b"new archives: 3")
        with self.assertRaisesRegex(ValueError,"published_commit_and_staging_disagree"):
            audit_log(DAY,42,log,Git())


if __name__=="__main__":
    unittest.main()
