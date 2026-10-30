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

    def test_topn_controls_and_rendering_stay_in_sync(self):
        html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
        for top in (3, 5, 10):
            self.assertIn(f'data-prediction-top="{top}"', html)
        self.assertIn("selectedTop=Number(button.dataset.predictionTop)", html)
        self.assertIn("predictionTickets.slice(0,selectedTop).forEach", html)
        self.assertIn("b.setAttribute('aria-pressed',String(b===button))", html)
        self.assertNotIn("selectedTop=predictionTickets.length;drawPredictions()", html)


if __name__ == "__main__":
    unittest.main()
