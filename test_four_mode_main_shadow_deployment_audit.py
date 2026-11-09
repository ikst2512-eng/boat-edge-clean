"""Fail-closed main/Draft candidate pipeline deployment inventory tests."""
import unittest
from unittest.mock import patch

from four_mode_main_shadow_deployment_audit import (
    STEP_ORIGINAL, STEP_REMOTE, STEP_FREEZE, STEP_LEDGER,
    WORKFLOW, audit_live, review, stages,
)

MAIN_SHA = "a" * 40
DRAFT_SHA = "b" * 40


def workflow(candidate=False):
    s = (
        "name: Four-mode prospective capture (research only)\n"
        "on:\n  pull_request:\n    paths: []\n"
        "concurrency:\n  group: ${{ github.event_name == 'pull_request' }}\n"
        "jobs:\n"
        "  capture:\n"
        "    if: github.ref == 'refs/heads/main' && "
        "github.event_name != 'pull_request'\n"
        "    steps:\n"
        f"      - name: {STEP_ORIGINAL}\n"
        "        run: python clean_four_mode_capture.py\n"
        f"      - name: {STEP_REMOTE}\n"
        "        run: python four_mode_github_server_observation.py\n"
    )
    if candidate:
        s += (
            f"      - name: {STEP_FREEZE}\n"
            "        run: python four_mode_all_mode_same_job_shadow.py\n"
            f"      - name: {STEP_LEDGER}\n"
            "        run: python four_mode_all_shadow_durable_ledger.py\n"
            "      - uses: actions/upload-artifact@v4\n"
            "        with:\n          path: |\n"
            "            four-mode-evidence/all-mode-shadow.json\n"
            "            four-mode-evidence/all-mode-shadow-ledger.json\n"
        )
    return s.encode()


class DeploymentAuditTests(unittest.TestCase):
    def test_main_without_candidate_draft_with_candidate_is_not_deployed(self):
        report = review(workflow(), workflow(True), MAIN_SHA, DRAFT_SHA)
        self.assertEqual(report["status"], "draft_candidate_stages_not_deployed_on_main")
        self.assertFalse(report["main_candidate_stages_deployed_in_source"])
        self.assertTrue(report["draft_candidate_stages_available_for_manual_review"])
        self.assertFalse(report["live_candidate_step_execution_verified"])
        self.assertFalse(report["independent_first_remote_candidate_receipt_verified"])
        self.assertFalse(report["formal"])
        self.assertEqual(report["admitted_prospective_pairs"], 0)
        self.assertFalse(report["model_promotion_allowed"])

    def test_both_present_does_not_prove_candidate_receipt(self):
        report = review(workflow(True), workflow(True), MAIN_SHA, DRAFT_SHA)
        self.assertTrue(report["main_candidate_stages_deployed_in_source"])
        self.assertEqual(report["status"],
                         "main_candidate_stages_present_execution_and_receipt_unverified")
        self.assertFalse(report["live_candidate_step_execution_verified"])
        self.assertFalse(report["formal"])

    def test_no_candidate_anywhere_is_incomplete_draft_but_nonformal(self):
        report = review(workflow(), workflow(), MAIN_SHA, DRAFT_SHA)
        self.assertFalse(report["draft_candidate_stages_available_for_manual_review"])
        self.assertFalse(report["formal"])

    def test_partial_stage_does_not_pass(self):
        w = workflow(True).decode().replace(
            f"      - name: {STEP_LEDGER}\n"
            "        run: python four_mode_all_shadow_durable_ledger.py\n", "")
        with self.assertRaisesRegex(ValueError, "partial_candidate_pipeline"):
            stages(w.encode())

    def test_code_step_without_output_artifact_rejected(self):
        w = workflow(True).decode().replace(
            "            four-mode-evidence/all-mode-shadow-ledger.json\n", "")
        with self.assertRaisesRegex(ValueError, "candidate_pipeline_wiring_incomplete"):
            stages(w.encode())

    def test_duplicate_step_rejected(self):
        w = workflow(True).decode()
        w += f"      - name: {STEP_FREEZE}\n"
        with self.assertRaisesRegex(ValueError, "duplicated_capture_stage"):
            stages(w.encode())

    def test_unexpected_workflow_identity_and_guard_rejected(self):
        variants = [
            workflow().replace(b"Four-mode prospective capture", b"Unrelated capture"),
            workflow().replace(b"refs/heads/main", b"refs/heads/research"),
            workflow().replace(b"github.event_name == 'pull_request'",
                               b"github.event_name == 'workflow_dispatch'"),
        ]
        for raw in variants:
            with self.subTest(raw=raw[:50]):
                with self.assertRaisesRegex(ValueError, "workflow_identity"):
                    stages(raw)

    def test_invalid_sha_or_malformed_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "unpinned"):
            review(workflow(), workflow(True), "HEAD", DRAFT_SHA)
        with self.assertRaisesRegex(ValueError, "missing_or_oversized"):
            review(b"", workflow(True), MAIN_SHA, DRAFT_SHA)
        with self.assertRaisesRegex(ValueError, "non_utf8"):
            review(b"\xff", workflow(True), MAIN_SHA, DRAFT_SHA)

    def test_live_git_uses_only_pinned_original_commit_blobs(self):
        wf_main, wf_draft = workflow(), workflow(True)
        observed = []
        def fake_git(*args):
            observed.append(args)
            if args[0] == "rev-parse":
                return (MAIN_SHA if "origin/main" in args[-1] else DRAFT_SHA).encode()
            if args[0] == "show":
                return wf_main if args[1].startswith(MAIN_SHA) else wf_draft
            raise AssertionError(args)
        with patch("four_mode_main_shadow_deployment_audit.git", side_effect=fake_git):
            result = audit_live()
        self.assertEqual(result["main_commit_sha"], MAIN_SHA)
        self.assertEqual(result["draft_commit_sha"], DRAFT_SHA)
        self.assertFalse(result["draft_verified_at_exact_pr_head_sha"])
        self.assertEqual(observed[2], ("show", MAIN_SHA + ":" + WORKFLOW))
        self.assertEqual(observed[3], ("show", DRAFT_SHA + ":" + WORKFLOW))
        with patch("four_mode_main_shadow_deployment_audit.git", side_effect=fake_git):
            exact = audit_live(draft_ref=DRAFT_SHA)
        self.assertTrue(exact["draft_verified_at_exact_pr_head_sha"])
        self.assertEqual(exact["draft_commit_sha"], DRAFT_SHA)
        with self.assertRaisesRegex(ValueError, "unsafe_nonpinned"):
            audit_live(main_ref="some_feature_branch")


if __name__ == "__main__":
    unittest.main()
