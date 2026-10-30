"""Check model mass invariants independently of external race feeds."""
import unittest
from research_model import probabilities


class TopNMassContract(unittest.TestCase):
    def test_mass_is_ordered_and_bounded(self):
        ranked = probabilities([7.36, 5.66, 4.93, 5.87, 6.46, 4.76])
        self.assertEqual(len(ranked), 120)
        masses = [round(100 * sum(p for _, p in ranked[:n]), 4) for n in (3, 5, 10)]
        self.assertTrue(0 < masses[0] < masses[1] < masses[2] < 100)
        self.assertAlmostEqual(sum(p for _, p in ranked), 1.0, places=10)

    def test_future_snapshot_schema_uses_raw_mass_not_calibrated_confidence(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "research_model.py").read_text(encoding="utf-8")
        self.assertIn("topn_model_mass_pct=topn_model_mass_pct", source)
        self.assertIn("confidence_calibrated=False", source)
        self.assertIn("with _record_path(code).open(\"x\"", source)


if __name__ == "__main__":
    unittest.main()
