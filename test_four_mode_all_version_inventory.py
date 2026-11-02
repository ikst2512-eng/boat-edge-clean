import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from four_mode_all_version_inventory import inventory

class ArchiveInventoryTests(unittest.TestCase):
    def test_separate_versions_even_when_v2_outside_first_120(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "four_mode_forecasts").mkdir()
            (root / "confirmed_results").mkdir()
            for i in range(121):
                code = f"20261028{1 + i // 12:02d}{1 + i % 12:02d}"
                version = "CLEAN_FOUR_MODES_V1_UNCALIBRATED" if i < 120 else "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
                (root / "four_mode_forecasts" / (code + ".json")).write_text(
                    json.dumps({"race_code": code, "model_version": version}), encoding="utf-8")
                (root / "confirmed_results" / (code + ".json")).write_text("{}", encoding="utf-8")
            def compare(code, root):
                return {"status": "historical_comparison_only",
                        "modes": {m: {"top3": True, "top5": True, "top10": True}
                                  for m in ("narrow", "hit", "balance", "hole")}}
            with patch("four_mode_all_version_inventory.compare_race", side_effect=compare):
                report = inventory(root)
            self.assertEqual(report["groups"]["CLEAN_FOUR_MODES_V1_UNCALIBRATED"]["20261028"]["comparable"], 120)
            self.assertEqual(report["groups"]["CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"]["20261028"]["comparable"], 1)
            self.assertFalse(report["formal"])

if __name__ == "__main__":
    unittest.main()
