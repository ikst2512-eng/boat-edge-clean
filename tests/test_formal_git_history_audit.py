"""Synthetic Git history audit regression tests; no results or remote access."""
import unittest
from formal_candidate_validator import InvalidCandidate
from formal_git_history_audit import inspect_git_history


class GitHistoryTests(unittest.TestCase):
    def fixture(self):
        candidate = {"race_key": "20261028-01-01"}
        receipt = {
            "artifact_path": "data/formal_predictions/20261028-01-01.json",
            "artifact_commit_sha": "a" * 40,
            "first_seen_at": "2026-10-28T09:00:00+09:00",
        }
        history = [{
            "sha": "a" * 40, "action": "added",
            "path": receipt["artifact_path"],
            "committed_at": "2026-10-28T09:00:00+09:00",
        }]
        return candidate, receipt, history

    def test_consistent_history_never_approves(self):
        candidate, receipt, history = self.fixture()
        result = inspect_git_history(candidate, receipt, history)
        self.assertTrue(result["history_consistent"])
        self.assertFalse(result["trusted_first_seen_proven"])
        self.assertFalse(result["formal_approved"])

    def test_missing_history(self):
        c, r, _ = self.fixture()
        with self.assertRaises(InvalidCandidate):
            inspect_git_history(c, r, [])

    def test_receipt_mismatched_first_commit(self):
        c, r, h = self.fixture()
        r["artifact_commit_sha"] = "b" * 40
        with self.assertRaises(InvalidCandidate):
            inspect_git_history(c, r, h)

    def test_later_modification_rejected(self):
        c, r, h = self.fixture()
        h.insert(0, {"sha": "b" * 40, "action": "modified",
                     "path": r["artifact_path"]})
        with self.assertRaises(InvalidCandidate):
            inspect_git_history(c, r, h)

    def test_partial_history_rejected(self):
        c, r, h = self.fixture()
        h[0]["action"] = "modified"
        with self.assertRaises(InvalidCandidate):
            inspect_git_history(c, r, h)

    def test_wrong_race_path(self):
        c, r, h = self.fixture()
        r["artifact_path"] = "data/formal_predictions/20261028-02-01.json"
        with self.assertRaises(InvalidCandidate):
            inspect_git_history(c, r, h)


if __name__ == "__main__":
    unittest.main()
