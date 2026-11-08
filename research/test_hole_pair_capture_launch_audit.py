"""No-network, no-forecast, no-result tests of dispatch-readiness boundaries."""
import unittest
from unittest.mock import patch

from research import hole_pair_capture_launch_audit as m

SHA = "a" * 40


class CaptureLaunchAuditTests(unittest.TestCase):
    def test_only_default_tree_controls_dispatch_prerequisite(self):
        r = m.audit([], SHA)
        self.assertFalse(r["default_branch_workflow_present"])
        self.assertFalse(r["default_branch_dispatch_prerequisite_satisfied"])
        self.assertIn("workflow_dispatch_not_registered_on_default_branch",
                      r["blockers"])
        self.assertFalse(r["formal"])
        self.assertFalse(r["eligible_formal_cohort_started_proven"])

    def test_registered_workflow_does_not_prove_live_capture_or_receipt(self):
        r = m.audit([m.WORKFLOW], SHA)
        self.assertTrue(r["default_branch_dispatch_prerequisite_satisfied"])
        self.assertFalse(r["capture_run_executed_by_this_audit"])
        self.assertFalse(r["candidate_artifact_created_by_this_audit"])
        self.assertFalse(r["independent_first_candidate_receipt_verified"])
        self.assertFalse(r["official_t12_complete_verified"])
        self.assertFalse(r["formal"])
        self.assertFalse(r["production_promotion_allowed"])

    def test_unrelated_default_workflow_does_not_unlock(self):
        r = m.audit([".github/workflows/hole-pair-blockers.yml"], SHA)
        self.assertFalse(r["default_branch_dispatch_prerequisite_satisfied"])

    def test_invalid_tree_and_main_sha_rejected(self):
        for paths in (None, [None], [m.WORKFLOW, 3], "foo"):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                m.audit(paths, SHA)
        for sha in ("abc", "x" * 40, ""):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                m.audit([], sha)

    def test_git_audit_checks_main_ref_not_current_pr_tree(self):
        with patch.object(m, "_git", side_effect=[SHA, ""] ) as git:
            r = m.audit_git_default("origin/main")
        self.assertFalse(r["default_branch_workflow_present"])
        self.assertEqual(git.call_args_list[0].args,
                         ("rev-parse", "--verify", "origin/main^{commit}"))
        self.assertEqual(git.call_args_list[1].args,
                         ("ls-tree", "--name-only", "-r", "origin/main",
                          "--", m.WORKFLOW))

    def test_git_default_registered_is_still_nonformal(self):
        with patch.object(m, "_git", side_effect=[SHA, m.WORKFLOW]):
            r = m.audit_git_default("origin/main")
        self.assertTrue(r["default_branch_workflow_present"])
        self.assertFalse(r["formal"])

    def test_invalid_ref_rejected_before_any_git_command(self):
        with patch.object(m, "_git") as git:
            for ref in ("", "-main", "origin/../main", "main;echo bad", None):
                with self.subTest(ref=ref), self.assertRaises(ValueError):
                    m.audit_git_default(ref)
            git.assert_not_called()

    def test_unexpected_git_path_fails_closed(self):
        with patch.object(m, "_git", side_effect=[SHA, "unrelated/path"]):
            with self.assertRaisesRegex(ValueError, "unexpected_default_tree_result"):
                m.audit_git_default("origin/main")


if __name__ == "__main__":
    unittest.main()
