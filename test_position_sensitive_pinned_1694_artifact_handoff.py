"""Synthetic contract tests; the real #1694 artifact is fetched only by CI."""
import copy
import json
import tempfile
from pathlib import Path
import unittest

from position_sensitive_pinned_1694_artifact_handoff import (
    pinned_handoff, SOURCE_RUN_ID, SOURCE_HEAD_SHA, SOURCE_WORKFLOW,
    SOURCE_ARTIFACT_ID, SOURCE_ARTIFACT_NAME, SOURCE_ARTIFACT_DIGEST, REPO,
    SOURCE_REPORT_SHA256, read_exact_pinned_report,
)
from test_position_sensitive_cross_pr_t12_bridge import report


def run_meta():
    return {
        "id": SOURCE_RUN_ID, "head_sha": SOURCE_HEAD_SHA,
        "path": SOURCE_WORKFLOW, "event": "pull_request",
        "status": "completed", "conclusion": "success",
        "repository": {"full_name": REPO},
        "head_repository": {"full_name": REPO},
    }


def artifact_meta():
    return {
        "id": SOURCE_ARTIFACT_ID, "name": SOURCE_ARTIFACT_NAME,
        "digest": SOURCE_ARTIFACT_DIGEST, "expired": False,
        "workflow_run": {"id": SOURCE_RUN_ID, "head_sha": SOURCE_HEAD_SHA},
    }


def roster():
    codes = ["202611090708", "202611091110", "202611091908"]
    return {
        "schema": "POSITION_SENSITIVE_ALL_CANDIDATE_LIVE_HTTP_ROSTER_V1",
        "status": "whole_remote_ledger_snapshot_observed_nonformal",
        "fetched_research_branch_tip": "a" * 40,
        "candidate_files": len(codes),
        "candidate_original_exact_replays": len(codes),
        "candidate_first_remote_receipts_independently_verified": 0,
        "all_candidate_observations_externally_first_arrival_attested": False,
        "complete_capture_and_rescue_run_inventory_verified": False,
        "official_T12_beforeinfo_six_and_120_odds_verified": False,
        "formal": False, "promotion_allowed": False,
        "model_improvement_proven": False, "production_changed": False,
        "rows": [{
            "race_code": code, "candidate_sha256": "a" * 64,
            "original_sha256": "b" * 64,
            "original_and_candidate_ticket_replay": True,
            "independent_first_remote_receipt_verified": False,
            "formal": False, "promotion_allowed": False,
            "status": "deadline_cutoff_elapsed_no_new_observation_attempt",
        } for code in codes],
    }


class PinnedSourceConsumerTests(unittest.TestCase):
    def assess(self, a=None, r=None, s=None, c=None):
        return pinned_handoff(
            run_meta() if a is None else a,
            artifact_meta() if r is None else r,
            report() if s is None else s,
            roster() if c is None else c)

    def test_mixed_real_source_code_hypothesis_never_promotes(self):
        out = self.assess()
        self.assertEqual(out["candidate_rows"], 3)
        self.assertEqual(out["source_races_in_pinned_report"], 3)
        self.assertEqual(out["matched_same_race_rows"], 1)
        self.assertEqual(out["unmatched_candidate_rows"], 2)
        self.assertEqual(len(out["candidate_blockers"]), 3)
        self.assertIn("official_racelist_original", out["candidate_blockers"][1]["blockers"])
        for flag in ("formal", "model_improvement_proven",
                     "promotion_allowed", "production_changed", "outcomes_read",
                     "source_report_individual_http_originals_replayed_by_this_consumer",
                     "github_artifact_zip_digest_independently_computed_by_this_consumer",
                     "candidate_capture_roster_truly_complete"):
            self.assertFalse(out[flag], flag)

    def test_wrong_run_sha_or_wrong_workflow_rejected(self):
        for key, fake in (("head_sha", "f" * 40),
                          ("path", ".github/workflows/other.yml"),
                          ("conclusion", "failure"), ("event", "workflow_dispatch"),
                          ("id", SOURCE_RUN_ID+1)):
            m = run_meta()
            m[key] = fake
            with self.assertRaisesRegex(ValueError, "source_ci_run_not_pinned"):
                self.assess(a=m)

    def test_fake_run_repository_rejected(self):
        for key in ("repository", "head_repository"):
            m = run_meta()
            m[key] = {"full_name": "attacker/fork"}
            with self.assertRaisesRegex(ValueError, "source_ci_run_not_pinned"):
                self.assess(a=m)

    def test_wrong_artifact_digest_or_identity_rejected(self):
        for key, fake in (("digest", "sha256:" + "f"*64),
                          ("id", SOURCE_ARTIFACT_ID+1),
                          ("name", "other"),
                          ("expired", True)):
            m = artifact_meta()
            m[key] = fake
            with self.assertRaisesRegex(ValueError, "source_artifact_metadata_not_pinned"):
                self.assess(r=m)

    def test_mismatch_artifact_origin_run_rejected(self):
        a = artifact_meta()
        a["workflow_run"]["id"] += 1
        with self.assertRaisesRegex(ValueError, "source_artifact_metadata_not_pinned"):
            self.assess(r=a)

    def test_roster_count_drift_rejected(self):
        c = roster()
        c["candidate_files"] += 1
        with self.assertRaisesRegex(ValueError, "untrusted_or_partial_candidate_roster"):
            self.assess(c=c)

    def test_missing_candidate_replay_fails(self):
        c = roster()
        c["rows"][0]["original_and_candidate_ticket_replay"] = False
        with self.assertRaisesRegex(ValueError, "invalid_original_candidate_row"):
            self.assess(c=c)

    def test_candidate_first_receipt_forgery_fails(self):
        c = roster()
        c["rows"][0]["independent_first_remote_receipt_verified"] = True
        with self.assertRaisesRegex(ValueError, "invalid_original_candidate_row"):
            self.assess(c=c)

    def test_unauthenticated_roster_first_arrival_overclaim_fails(self):
        c = roster()
        c["all_candidate_observations_externally_first_arrival_attested"] = True
        with self.assertRaisesRegex(ValueError, "untrusted_or_partial_candidate_roster"):
            self.assess(c=c)

    def test_candidate_sha_forgery_fails(self):
        c = roster()
        c["rows"][0]["candidate_sha256"] = "nothex"
        with self.assertRaisesRegex(ValueError, "invalid_original_candidate_row"):
            self.assess(c=c)

    def test_duplicate_candidate_race_id_fails(self):
        c = roster()
        c["rows"][2]["race_code"] = c["rows"][0]["race_code"]
        with self.assertRaisesRegex(ValueError, "candidate_roster_duplicate"):
            self.assess(c=c)

    def test_pinned_original_report_raw_checksum_not_just_schema(self):
        self.assertEqual(len(SOURCE_REPORT_SHA256), 64)
        with tempfile.TemporaryDirectory() as temp:
            fake = Path(temp) / "fake-official-report.json"
            fake.write_text(json.dumps(report()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,
                                        "pinned_source_report_raw_sha256_mismatch"):
                read_exact_pinned_report(fake)

    def test_pinned_report_source_path_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "actual-report.json"
            target.write_text(json.dumps(report()), encoding="utf-8")
            linked = Path(temp) / "linked-report.json"
            linked.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "unsafe_pinned_report_path"):
                read_exact_pinned_report(linked)

    def test_no_future_roster_does_not_create_samples(self):
        c = roster()
        c["candidate_files"] = c["candidate_original_exact_replays"] = 0
        c["rows"] = []
        out = self.assess(c=c)
        self.assertEqual(out["formal_pilot"], 0)
        self.assertEqual(out["formal_confirmation"], 0)
        self.assertEqual(out["matched_same_race_rows"], 0)


if __name__ == "__main__":
    unittest.main()
