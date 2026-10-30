"""Regression contract for cross-origin forecast preview data access."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ForecastPreviewOriginTests(unittest.TestCase):
    def test_preview_fetches_same_render_api_as_racecard(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        preview = page.split("async function loadForecastPreview()", 1)[1].split("async function loadRaceData(", 1)[0]
        racecard = page.split("async function loadRaceData(", 1)[1].split("async function ", 1)[0]
        endpoint = "https://boat-edge-clean.onrender.com/api/clean-racecard?hd="
        self.assertIn(endpoint, preview)
        self.assertIn(endpoint, racecard)
        self.assertNotIn("const url='/api/clean-racecard", preview)

    def test_render_allows_pages_origin_for_racecard(self):
        server = (ROOT / "server.py").read_text(encoding="utf-8")
        self.assertIn('"/api/clean-racecard"', server)
        self.assertIn('"Access-Control-Allow-Origin", "https://ikst2512-eng.github.io"', server)

    def test_preview_is_gated_on_predeadline_evidence(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        preview = page.split("async function loadForecastPreview()", 1)[1].split("async function loadRaceData(", 1)[0]
        self.assertIn("observed>=deadline", preview)
        self.assertIn("raw.beforeinfo.racers.length!==6", preview)
        self.assertIn("raw.beforeinfo.start_exhibition.length!==6", preview)
        self.assertIn("推測表示しません", preview)


if __name__ == "__main__":
    unittest.main()
