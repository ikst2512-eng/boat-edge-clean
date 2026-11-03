"""Integration test: frozen research artifact and long-lived ledger scores agree."""
import copy
import json
import unittest
import zipfile
from unittest.mock import patch
from four_mode_v2_frozen_third_nightly import summarize as capture_score
from four_mode_v2_third_rate_ledger_rollup import evaluate as ledger_score
from four_mode_v2_third_ledger_reconcile import reconcile
from test_four_mode_v2_frozen_third_artifact_score import FrozenArtifactScoreTests, CODE


class CrossSourceProofTests(unittest.TestCase):
    def setUp(self):
        self.fixture = FrozenArtifactScoreTests("test_missing_result_is_pending_not_loss")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.original = self.fixture.evidence
        self.root = self.fixture.root

    def _capture(self, evidence):
        def download(run_id, path):
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("four-mode-evidence/third-rate-shadow.json",
                           json.dumps(evidence))
        run = {"databaseId": 12345, "headBranch": "main",
               "event": "schedule", "createdAt": "2026-11-04T01:00:00Z",
               "conclusion": "success"}
        return capture_score([run], self.root, download, self.root / "downloads")

    def _ledger(self, evidence):
        def git(root, *args):
            if args[0] == "ls-tree":
                return b"third_rate/20261104/run-12345-attempt-1.json\n"
            if args[0] == "show":
                return json.dumps(evidence).encode()
            raise AssertionError(args)
        return ledger_score(self.root, git)

    def test_exact_tickets_match_and_reordered_lower_tickets_fail(self):
        winner = self.original["records"][0]["candidate_top10"][0]
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "historical_comparison_only",
                                 "winning_ticket": winner}):
            capture = self._capture(self.original)
            ledger = self._ledger(self.original)
            self.assertEqual(reconcile(capture, ledger)["status"],
                             "bounded_frozen_roster_matched")
            modified = copy.deepcopy(self.original)
            picks = modified["records"][0]["candidate_top10"]
            picks[8], picks[9] = picks[9], picks[8]
            altered = self._ledger(modified)
        self.assertEqual(capture["paired_race_scores"],
                         altered["paired_race_scores"])
        self.assertEqual(reconcile(capture, altered)["status"],
                         "frozen_ticket_digest_mismatch")
        self.assertFalse(reconcile(capture, ledger)["production_promotion_allowed"])

    def test_pending_results_still_reconcile_ticket_identity(self):
        with patch("four_mode_v2_frozen_third_artifact_score.compare_race",
                   return_value={"status": "result_unavailable"}):
            capture = self._capture(self.original)
            ledger = self._ledger(self.original)
        self.assertEqual(capture["paired"], 0)
        self.assertEqual(reconcile(capture, ledger)["status"],
                         "bounded_frozen_roster_matched")


if __name__ == "__main__":
    unittest.main()
