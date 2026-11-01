"""Regression contract for evidence-labeled four-mode historical forecast UI."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class FourModePanelTests(unittest.TestCase):
    def test_four_modes_and_provenance_are_present(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="fourModeForecastPanel"', html)
        self.assertIn("loadFourModeArchives(raceKey,token)", html)
        self.assertIn("FOUR_MODE_ARCHIVE_INVALID", html)
        self.assertIn("data.production_forecast!==false", html)
        self.assertIn("data.verified_first_git_add!==false", html)
        for text in ("本命", "バランス", "穴", "絞り"):
            self.assertIn(text, html)
        self.assertIn("後付け生成はしません", html)

if __name__ == "__main__":
    unittest.main()
