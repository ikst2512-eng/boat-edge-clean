"""No scheduling, no network, no writes outside mocked capture."""
import unittest
from unittest.mock import patch
from run_research_pair_capture import run

class OrchestratorTests(unittest.TestCase):
    def test_delegates_and_never_claims_independent_proof(self):
        with patch("run_research_pair_capture.capture", return_value={
            "frozen": 2, "already_frozen": 1, "ineligible": 4}) as mocked:
            out = run("20261028")
        mocked.assert_called_once()
        self.assertEqual(out["frozen"], 2)
        self.assertFalse(out["scheduled"])
        self.assertFalse(out["external_timestamp_proven"])

if __name__ == "__main__":
    unittest.main()
