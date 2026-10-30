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

    def test_topn_hit_boundaries_use_exact_saved_order(self):
        html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
        expected = ("function classifyPredictionMatch(tickets,combo){"
                    "const index=Array.isArray(tickets)?tickets.indexOf(combo):-1;"
                    "return {rank:index+1,top3:index>=0&&index<3,"
                    "top5:index>=0&&index<5,top10:index>=0&&index<10}}")
        self.assertIn(expected, html)
        # Boundary expectations: indices 0..2, 3..4, 5..9, and absent.
        for index, expected_hits in ((0, (True, True, True)),
                                     (2, (True, True, True)),
                                     (3, (False, True, True)),
                                     (4, (False, True, True)),
                                     (5, (False, False, True)),
                                     (9, (False, False, True)),
                                     (-1, (False, False, False))):
            actual = (index >= 0 and index < 3,
                      index >= 0 and index < 5,
                      index >= 0 and index < 10)
            self.assertEqual(actual, expected_hits)


if __name__ == "__main__":
    unittest.main()
