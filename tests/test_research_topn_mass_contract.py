"""Check model mass invariants independently of external race feeds."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import research_model
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

    def test_real_snapshot_write_and_no_overwrite(self):
        # Mock only external CSV acquisition and Git metadata; exercise actual JSON file write.
        day = "20991231"
        code = day + "0101"
        titles = [{"レースコード": code, "電話投票締切予定": "2359"}]
        card = {"レースコード": code}
        card.update({f"艇{i}_全国勝率": "6.0" for i in range(1, 7)})
        from datetime import datetime
        fake_read = [
            (titles, datetime.now(research_model.JST), "a" * 64),
            ([card], datetime.now(research_model.JST), "b" * 64),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(research_model, "STORE", Path(tmp)), \
                 patch.object(research_model, "read_rows", side_effect=fake_read) as read, \
                 patch.object(research_model, "model_provenance", return_value={"model_git_sha": "test"}):
                returned = research_model.predict(day, "1", "1")
                saved = json.loads((Path(tmp) / (code + ".json")).read_text(encoding="utf-8"))
                self.assertEqual(saved["predictions"], returned["predictions"])
                self.assertEqual(set(saved["topn_model_mass_pct"]), {"3", "5", "10"})
                self.assertTrue(0 < saved["topn_model_mass_pct"]["3"] < saved["topn_model_mass_pct"]["5"] < saved["topn_model_mass_pct"]["10"] < 100)
                self.assertIs(saved["confidence_calibrated"], False)
                self.assertEqual(saved["model_version"], "national-beta0.4-exploratory-v1")
                self.assertIn("source_deadline_jst", saved)
                before = (Path(tmp) / (code + ".json")).read_bytes()
                self.assertEqual(research_model.predict(day, "1", "1")["predictions"], saved["predictions"])
                self.assertEqual((Path(tmp) / (code + ".json")).read_bytes(), before)
                self.assertEqual(read.call_count, 2)


if __name__ == "__main__":
    unittest.main()
