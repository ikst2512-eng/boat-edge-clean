"""Ensure daily capture and single-race prediction use identical uncalibrated TopN mass."""
import ast
from pathlib import Path
import unittest


class DailyMassContract(unittest.TestCase):
    def test_daily_capture_uses_full_ranked_probabilities(self):
        source = (Path(__file__).resolve().parents[1] / "collect_research_daily.py").read_text()
        tree = ast.parse(source)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "collect")
        text = ast.unparse(fn)
        self.assertIn("ranked = probabilities(rates)", text)
        self.assertIn("ranked[:n]", text)
        self.assertIn("(3, 5, 10)", text)
        self.assertIn("'topn_model_mass_pct': topn_model_mass_pct", text)
        self.assertIn("'confidence_calibrated': False", text)


if __name__ == "__main__":
    unittest.main()
