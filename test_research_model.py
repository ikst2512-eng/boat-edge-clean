"""Regressions for exploratory nationwide win-rate predictions."""
import unittest
from unittest.mock import patch
import research_model as model
class NationalModelTests(unittest.TestCase):
    def test_120_unique_and_normalized(self):
        x=model.probabilities([6,5,4,7,3,2])
        self.assertEqual(len(x),120)
        self.assertEqual(len({t for t,p in x}),120)
        self.assertAlmostEqual(sum(p for t,p in x),1,places=10)
    def test_skill_winner_tilt(self):
        before=model.probabilities([6]*6)
        after=model.probabilities([9,6,6,6,6,6])
        self.assertGreater(sum(p for t,p in after if t[0]==1),sum(p for t,p in before if t[0]==1))
    def test_invalid_skill_fails(self):
        for rates in ([6]*5,[6]*5+[0],[6]*5+[True],[6]*5+[float("nan")]):
            with self.assertRaises(ValueError):model.probabilities(rates)
    def test_historical_training_leak_block(self):
        with self.assertRaises(ValueError):model.predict("20261021","12","1")
    def test_source_unavailable_blocks(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(model,"STORE",Path(temp)):
                with patch.object(model,"read_rows",side_effect=ValueError("not available")):
                    with self.assertRaises(ValueError):model.predict("20261023","12","1")
if __name__=="__main__":
    unittest.main()
