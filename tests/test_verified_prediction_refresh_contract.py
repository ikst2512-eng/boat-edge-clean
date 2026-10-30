"""Regression contract: verified same-race tickets survive a source refresh."""
from pathlib import Path
import unittest


class VerifiedPredictionRefreshContract(unittest.TestCase):
    def test_preserves_verified_tickets_before_network_fetch(self):
        html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
        start = html.index("async function loadPredictions(force=false)")
        end = html.index("const response=await fetchTimed(", start)
        before_fetch = html[start:end]
        self.assertIn("const key=sameRaceKey(),retain=", before_fetch)
        self.assertIn("if(!retain){predictionModes={research:", before_fetch)
        self.assertNotIn("displayedPredictionKey=key;predictionModes=", before_fetch)

    def test_failed_fetch_keeps_verified_same_race_tickets(self):
        html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
        start = html.index("async function loadPredictions(force=false)")
        end = html.index("\nasync function ", start + 10) if "\nasync function " in html[start + 10:] else len(html)
        block = html[start:end]
        self.assertIn("if(retain&&(reason===", block)
        self.assertIn("前回検証済みの予想を表示中", block)


if __name__ == "__main__":
    unittest.main()
