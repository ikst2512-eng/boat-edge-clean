"""Git fixture tests: separate candidate ledger is create-only, read-only.

Synthetic temporary Git repositories only. No remote GitHub/branch writes.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from position_sensitive_ledger_history_audit import audit_ledger
from test_four_mode_position_sensitive_forward import frozen


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.DEVNULL,
                                   timeout=20).decode().strip()


def commit(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    git(root, "add", "--", name)
    git(root, "commit", "-qm", "add "+name)


class GitLedgerHistoryTests(unittest.TestCase):
    def setUp(self):
        self.context = tempfile.TemporaryDirectory()
        self.addCleanup(self.context.cleanup)
        self.root = Path(self.context.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "unit-test")
        git(self.root, "commit", "-qm", "initial", "--allow-empty")
        self.base = git(self.root, "rev-parse", "HEAD")
        git(self.root, "checkout", "-qb", "position-sensitive-forward-evidence-ledger")
        commit(self.root, "position_sensitive_research/README.md", "research only\n")

    def candidate(self):
        s, original = frozen()
        content = json.dumps(s, ensure_ascii=False, sort_keys=True)
        path = "position_sensitive_research/"+s["race_code"]+".json"
        commit(self.root, path, content)
        return s, original, path

    def audit(self, original_read=None):
        return audit_ledger(self.root, "HEAD", base=self.base,
                            original_read=original_read)

    def test_initial_readme_only_is_empty_unverified(self):
        x = self.audit()
        self.assertEqual(x["candidate_files"], 0)
        self.assertEqual(x["recorded_first_add_commits_after_bootstrap"], 1)
        self.assertFalse(x["branch_tip_is_independently_pinned"])
        self.assertFalse(x["remote_history_rewrite_excluded"])
        self.assertFalse(x["formal"])
        self.assertFalse(x["promotion_allowed"])

    def test_one_frozen_future_candidate_replayed_but_not_remote_attested(self):
        s, original, path = self.candidate()
        x = self.audit(original_read=lambda code: original)
        self.assertEqual(x["candidate_files"], 1)
        self.assertEqual(x["candidate_original_exact_replays"], 1)
        self.assertEqual(x["candidate_first_remote_receipts_independently_verified"], 0)
        self.assertFalse(x["model_improvement_proven"])

    def test_candidate_without_authoritative_original_does_not_claim_replay(self):
        self.candidate()
        x = self.audit()
        self.assertEqual(x["candidate_files"], 1)
        self.assertEqual(x["candidate_original_exact_replays"], 0)
        self.assertFalse(x["formal"])

    def test_original_bytes_mismatch_rejected(self):
        self.candidate()
        with self.assertRaisesRegex(ValueError, "candidate_original_replay_failed"):
            self.audit(original_read=lambda _: b"{}")

    def test_updating_existing_candidate_is_a_hard_failure(self):
        _, _, path = self.candidate()
        (self.root / path).write_text("TAMPERED", encoding="utf-8")
        git(self.root, "add", "--", path)
        git(self.root, "commit", "-qm", "modify candidate")
        with self.assertRaisesRegex(ValueError, "first_add_blob_mutated_or_invalid"):
            self.audit()

    def test_readme_overwrite_is_forbidden(self):
        path = self.root / "position_sensitive_research/README.md"
        path.write_text("changed policy\n")
        git(self.root, "add", "--", "position_sensitive_research/README.md")
        git(self.root, "commit", "-qm", "rewrite")
        with self.assertRaisesRegex(ValueError, "first_add_blob_mutated_or_invalid"):
            self.audit()

    def test_deleted_candidate_is_forbidden(self):
        _, _, path = self.candidate()
        git(self.root, "rm", "--", path)
        git(self.root, "commit", "-qm", "delete candidate")
        with self.assertRaisesRegex(ValueError, "first_add_blob_mutated_or_invalid"):
            self.audit()

    def test_unapproved_paths_cannot_appear_on_ledger(self):
        commit(self.root, "confirmed_results/202611090101.json", "{}")
        with self.assertRaisesRegex(ValueError, "unapproved_ledger_change_path"):
            self.audit()

    def test_result_bearing_forecast_is_rejected(self):
        s, _, _ = self.candidate()
        wrong = {**s, "finish_order": [1, 2, 3]}
        # New race path but internal code mismatch, also forbidden.
        path = "position_sensitive_research/202611090102.json"
        commit(self.root, path, json.dumps(wrong))
        with self.assertRaises(ValueError):
            self.audit()

    def test_missing_bootstrap_or_wrong_branch_tip_fails(self):
        with self.assertRaisesRegex(ValueError, "invalid_ledger_tip_or_base"):
            audit_ledger(self.root, self.base, base=self.base)
        with self.assertRaisesRegex(ValueError, "missing_git_branch_or_base"):
            audit_ledger(self.root, "nonexistent-research", base=self.base)

    def test_invalid_history_external_file_does_not_leak_results(self):
        (self.root/"confirmed_results").mkdir()
        poison = self.root/"confirmed_results/202611090101.json"
        poison.write_text("BROKEN_RESULT_NEVER_READ")
        x = self.audit()
        self.assertEqual(x["candidate_files"], 0)
        self.assertEqual(poison.read_text(), "BROKEN_RESULT_NEVER_READ")


if __name__ == "__main__":
    unittest.main()
