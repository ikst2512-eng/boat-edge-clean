"""Fake-only tests: live roster never certifies first remote candidate arrival."""
from datetime import datetime
import hashlib
import json
import unittest

from test_four_mode_position_sensitive_forward import archive, frozen
from position_sensitive_live_roster_audit import (
    inspect_roster, PREFIX, README, REMOTE_REF, ORIGINAL_REF,
)

TIP = "a"*40
UTC_BEFORE = datetime.fromisoformat("2026-11-09T16:48:00+09:00")
UTC_AFTER = datetime.fromisoformat("2026-11-09T20:27:00+09:00")


def make_fixture():
    s, original = frozen(archive("202611091912",
                                deadline="2026-11-09T20:38:00+09:00"),
                         "2026-11-09T14:25:00+09:00")
    candidate = json.dumps(s, ensure_ascii=False, sort_keys=True).encode()
    path = PREFIX+s["race_code"]+".json"
    return s, original, candidate, path


def fake_git(s, original, candidate, path, names=None):
    def git(*args):
        if args == ("rev-parse", "--verify", REMOTE_REF+"^{commit}"):
            return (TIP+"\n").encode()
        if args == ("ls-tree", "-r", "--name-only", TIP, "--", PREFIX):
            return ("\n".join(names if names is not None else [README,path])+"\n").encode()
        if args == ("show", TIP+":"+path):
            return candidate
        if args == ("show", ORIGINAL_REF+":four_mode_forecasts/"+s["race_code"]+".json"):
            return original
        raise AssertionError("unexpected_git_op:"+str(args))
    return git


def fake_observer(s, original, candidate, *, actual_tip=TIP, actual_digest=None):
    return {
        "status": "github_candidate_existing_preT12_observation_not_first_receipt",
        "observed_branch_commit_sha": actual_tip,
        "candidate_sha256": actual_digest or hashlib.sha256(candidate).hexdigest(),
        "original_forecast_sha256": hashlib.sha256(original).hexdigest(),
        "server_observed_utc": "2026-11-09T07:48:00+00:00",
        "independent_candidate_first_remote_receipt_verified": False,
        "formal": False,
        "promotion_allowed": False,
    }


class AllCandidateLiveRosterTests(unittest.TestCase):
    def test_realistic_live_mocked_observation_stays_nonformal(self):
        s, original, candidate, path = make_fixture()
        report = inspect_roster(
            fake_git(s, original, candidate, path),
            lambda code, orig: fake_observer(s, original, candidate),
            UTC_BEFORE, allow_live=True)
        self.assertEqual(report["candidate_files"], 1)
        self.assertEqual(report["candidate_original_exact_replays"], 1)
        self.assertEqual(report["status_counts"][
            "remote_existence_observed_preT12_not_first_receipt"], 1)
        self.assertEqual(report["candidate_first_remote_receipts_independently_verified"], 0)
        self.assertFalse(report["formal"])
        self.assertFalse(report["promotion_allowed"])
        self.assertFalse(report["complete_capture_and_rescue_run_inventory_verified"])
        self.assertFalse(report["official_T12_beforeinfo_six_and_120_odds_verified"])

    def test_t12_elapsed_never_recontacts_github(self):
        s, original, candidate, path = make_fixture()
        def forbidden_observer(*args):
            raise AssertionError("no_post_T12_observation_allowed")
        report = inspect_roster(fake_git(s, original, candidate, path),
                                forbidden_observer, UTC_AFTER, allow_live=True)
        self.assertEqual(report["rows"][0]["status"],
                         "deadline_cutoff_elapsed_no_new_observation_attempt")
        self.assertNotIn("observed_at_utc", report["rows"][0])

    def test_live_disabled_does_no_remote_io(self):
        s, original, candidate, path = make_fixture()
        def forbidden(*args):
            raise AssertionError("should_not_do_HTTP")
        report = inspect_roster(fake_git(s, original, candidate, path), forbidden,
                                UTC_BEFORE, allow_live=False)
        self.assertEqual(report["rows"][0]["status"],
                         "predeadline_read_only_live_observation_not_enabled")

    def test_changed_remote_branch_sha_cannot_pass(self):
        s, original, candidate, path = make_fixture()
        with self.assertRaisesRegex(ValueError, "remote_observation_or_tip_mismatch"):
            inspect_roster(
                fake_git(s, original, candidate, path),
                lambda *_: fake_observer(s, original, candidate, actual_tip="b"*40),
                UTC_BEFORE, allow_live=True)

    def test_different_remote_candidate_blob_cannot_pass(self):
        s, original, candidate, path = make_fixture()
        with self.assertRaisesRegex(ValueError, "remote_observation_or_tip_mismatch"):
            inspect_roster(
                fake_git(s, original, candidate, path),
                lambda *_: fake_observer(s, original, candidate, actual_digest="b"*64),
                UTC_BEFORE, allow_live=True)

    def test_altered_saved_candidate_fails_before_http(self):
        s, original, candidate, path = make_fixture()
        modified = json.loads(candidate)
        modified["candidate"]["hit"][0] = "6-5-4"
        mutated = json.dumps(modified).encode()
        def forbidden(*args):
            raise AssertionError("unverified_candidate_should_never_be_observed")
        with self.assertRaisesRegex(ValueError, "candidate_original_exact_replay_failed"):
            inspect_roster(fake_git(s, original, mutated, path), forbidden,
                           UTC_BEFORE, allow_live=True)

    def test_unapproved_ledger_path_fails_before_http(self):
        s, original, candidate, path = make_fixture()
        paths = [README, path, "position_sensitive_research/confirmed_results.json"]
        with self.assertRaisesRegex(ValueError, "unapproved_candidate_path"):
            inspect_roster(fake_git(s, original, candidate, path, names=paths),
                           lambda *_: None, UTC_BEFORE, allow_live=True)

    def test_duplicate_roster_entries_fail(self):
        s, original, candidate, path = make_fixture()
        with self.assertRaisesRegex(ValueError, "duplicate_paths"):
            inspect_roster(fake_git(s, original, candidate, path,
                                    names=[README,path,path]),
                           lambda *_: None, UTC_BEFORE)

    def test_missing_bootstrap_and_empty_candidate_files_fail_safe(self):
        s, original, candidate, path = make_fixture()
        with self.assertRaisesRegex(ValueError, "missing_bootstrap"):
            inspect_roster(fake_git(s, original, candidate, path, names=[path]),
                           lambda *_: None, UTC_BEFORE)
        report = inspect_roster(fake_git(s, original, candidate, path,
                                          names=[README]),
                                lambda *_: None, UTC_BEFORE, allow_live=True)
        self.assertEqual(report["candidate_files"], 0)
        self.assertEqual(report["rows"], [])
        self.assertFalse(report["formal"])


if __name__ == "__main__":
    unittest.main()
