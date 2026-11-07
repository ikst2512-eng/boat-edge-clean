"""Outcome-last tests for saved four-mode hole shadow and GitHub observation.

Synthetic proof fields exercise rejection logic; they do NOT certify real races.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from forward_hole_saved_evidence_gate import inspect_race
from hole_upper_rank_pair_protection import propose

CODE = "202611050101"
SHA = "a" * 40
BASE = ["1-2-3", "1-2-4", "1-3-2", "2-3-1", "2-3-4",
        "3-4-1", "3-4-2", "1-2-5", "2-3-5", "3-4-5"]
DONOR = ["1-4-2", "1-2-3", "1-2-4", "1-3-2", "2-3-1",
         "2-3-4", "3-4-1", "3-4-2", "1-2-5", "2-3-5"]


class SavedShadowGateTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        p = self.root / "four_mode_forecasts" / (CODE + ".json")
        p.parent.mkdir()
        modes = {
            name: {"tickets": [{"combo": combo, "p": 1.0} for combo in
                               (BASE if name != "hit" else DONOR)]}
            for name in ("narrow", "hit", "balance", "hole")
        }
        record = {
            "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
            "race_code": CODE, "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
            "validated": False, "deadline_jst": "2026-11-05T12:00:00+09:00",
            "generated_at_jst": "2026-11-05T10:00:00+09:00",
            "source_title_received_jst": "2026-11-05T09:59:00+09:00",
            "source_cards_received_jst": "2026-11-05T09:59:30+09:00",
            "modes": modes,
        }
        self.raw = (json.dumps(record, sort_keys=True) + "\n").encode()
        p.write_bytes(self.raw)
        digest = hashlib.sha256(self.raw).hexdigest()
        self.publication = {"outcome": "pushed_to_main", "commit_sha": SHA,
                            "added_forecasts": 1}
        self.shadow = {
            "schema": "HOLE_SHADOW_PUBLISHED_SAME_JOB_V1",
            "status": "research_only_after_confirmed_push",
            "formal": False, "independent_first_receipt_verified": False,
            "publication_commit_sha": SHA, "published_new_count": 1,
            "records": [{
                "race_code": CODE, "status": "shadow_frozen_unverified",
                "local_freeze_at_jst": "2026-11-05T10:02:00+09:00",
                "t_minus_12_jst": "2026-11-05T11:48:00+09:00",
                "deadline_jst": "2026-11-05T12:00:00+09:00",
                "source_sha256": digest,
                "baseline": BASE, "shadow": propose(BASE, DONOR, 3),
                "candidate_algorithm": "hole_upper_rank_pair_protection.propose:hit_rank3:v1",
            }]
        }
        self.remote = {
            "schema": "FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1",
            "status": "remote_observation_audited_nonformal",
            "formal": False, "independent_first_remote_receipt_verified": False,
            "github_server_observation_not_first_receipt": True,
            "publication_commit_sha": SHA, "publication_count": 1,
            "records": [{
                "race_code": CODE, "status": "github_server_observed_before_t_minus_12",
                "first_add_commit": SHA, "first_add_blob_matches_remote": True,
                "independent_first_remote_receipt_verified": False,
                "original_sha256": digest,
                "github_api_server_date_utc": "2026-11-05T01:02:00+00:00",
                "deadline_minus_12_jst": "2026-11-05T11:48:00+09:00",
            }]
        }
        self.calls = []

    def git(self, args):
        self.calls.append("git-" + args[0])
        if args[0] == "diff-tree":
            return ("four_mode_forecasts/" + CODE + ".json\n").encode()
        if args[0] == "merge-base":
            return b""
        if args[0] == "show":
            return self.raw
        raise AssertionError(args)

    def result(self, code, root):
        self.calls.append("result")
        return {"race_code": CODE, "status": "historical_comparison_only",
                "formal": False, "remote_first_seen_verified": False,
                "winning_ticket": "1-4-2"}

    def inspect(self, **changes):
        args = dict(
            code=CODE, root=self.root, publication=self.publication,
            hole_shadow=self.shadow, observation=self.remote,
            git=self.git, result_reader=self.result,
        )
        args.update(changes)
        return inspect_race(**args)

    def test_result_read_last_and_saved_rank3_gain(self):
        out = self.inspect()
        self.assertEqual(out["status"], "matched_saved_shadow_and_remote_observation_research_only")
        self.assertEqual(self.calls, ["git-diff-tree", "git-merge-base", "git-show", "result"])
        self.assertTrue(out["topn"]["top3"]["gained"])
        self.assertTrue(out["topn"]["top10"]["gained"])
        self.assertFalse(out["topn"]["top1"]["gained"])
        self.assertFalse(out["formal"])
        self.assertFalse(out["complete_capture_run_inventory_verified"])

    def test_enrollment_never_reads_result(self):
        out = self.inspect(score_outcome=False)
        self.assertEqual(out["status"], "pre_result_evidence_consistent_research_only")
        self.assertEqual(out["deadline_jst"], "2026-11-05T12:00:00+09:00")
        self.assertEqual(len(out["baseline_top10"]), 10)
        self.assertEqual(len(out["candidate_top10"]), 10)
        self.assertEqual(self.calls, ["git-diff-tree", "git-merge-base", "git-show"])
        self.assertFalse(out["result_accessed"])
        self.assertFalse(out["capture_run_inventory_verified"])
        self.assertNotIn("winning_ticket", out)
        self.assertNotIn("topn", out)

    def test_invalid_score_mode_blocked(self):
        with self.assertRaisesRegex(ValueError, "invalid_scoring_gate"):
            self.inspect(score_outcome=1)
        self.assertEqual(self.calls, [])

    def test_missing_result_never_counts_as_loss(self):
        out = self.inspect(result_reader=lambda *_: {"status": "result_unavailable"})
        self.assertEqual(out["status"], "pending_independent_result")
        self.assertNotIn("topn", out)
        self.assertFalse(out["scorable"])

    def test_missing_shadow_refuses_result_read(self):
        self.shadow["records"][0]["status"] = "calculation_crossed_t_minus_12"
        out = self.inspect()
        self.assertEqual(out["reason"], "shadow_not_frozen")
        self.assertNotIn("result", self.calls)

    def test_server_observed_after_cutoff_refuses_result_read(self):
        self.remote["records"][0]["status"] = "github_server_observed_after_t_minus_12"
        out = self.inspect()
        self.assertEqual(out["reason"], "no_predeadline_github_server_observation")
        self.assertNotIn("result", self.calls)

    def test_remote_clock_forgery_refused(self):
        self.remote["records"][0]["github_api_server_date_utc"] = "2026-11-05T03:00:00+00:00"
        out = self.inspect()
        self.assertEqual(out["status"], "excluded_unverified_evidence")
        self.assertNotIn("result", self.calls)

    def test_non_main_commit_rejected_before_result(self):
        import subprocess
        def invalid_git(args):
            if args[0] == "merge-base":
                raise subprocess.CalledProcessError(1, args)
            return self.git(args)
        out = self.inspect(git=invalid_git)
        self.assertEqual(out["status"], "excluded_unverified_evidence")
        self.assertNotIn("result", self.calls)

    def test_original_changed_after_archive_refused(self):
        (self.root / "four_mode_forecasts" / (CODE + ".json")).write_bytes(b"tampered")
        out = self.inspect()
        self.assertEqual(out["status"], "excluded_unverified_evidence")
        self.assertNotIn("result", self.calls)

    def test_saved_shadow_tampered_refused(self):
        self.shadow["records"][0]["shadow"][2] = "6-1-2"
        out = self.inspect()
        self.assertEqual(out["status"], "excluded_unverified_evidence")
        self.assertNotIn("result", self.calls)

    def test_race_identity_conflict_rejected_before_result(self):
        self.remote["records"][0]["race_code"] = "202611050102"
        out = self.inspect()
        self.assertEqual(out["reason"], "publication_evidence_race_roster_mismatch")
        self.assertNotIn("result", self.calls)

    def test_fake_first_receipt_claim_rejected(self):
        self.remote["independent_first_remote_receipt_verified"] = True
        out = self.inspect()
        self.assertEqual(out["reason"], "untrusted_observation_roster")

    def test_old_period_never_enters_predeclared_study(self):
        out = self.inspect(code="202611040101")
        self.assertEqual(out["reason"], "outside_predeclared_study_window")
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
