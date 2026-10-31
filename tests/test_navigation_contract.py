"""Regression guard for BOAT EDGE CLEAN's simplified navigation.

These tests verify the shipped HTML/JS/server contracts without requiring
live races, third-party APIs, or real purchases. Browser interaction still
requires an end-to-end Safari/Chromium check.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NavigationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nav = (ROOT / "navigation.js").read_text(encoding="utf-8")
        cls.server = (ROOT / "server.py").read_text(encoding="utf-8")
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.secondary = (ROOT / "secondary_navigation.js").read_text(encoding="utf-8")

    def test_main_navigation_keeps_only_requested_pages(self):
        match = re.search(r'<nav class="site-global-nav[^"]*"[^>]*>(.*?)</nav>', self.index)
        self.assertIsNotNone(match)
        self.assertEqual(re.findall(r'href="([^"]+)"', match.group(1)),
                         ["/review", "/selection"])
        self.assertNotIn("nav.innerHTML=", self.nav)

    def test_detail_views_and_prediction_entry_still_exist(self):
        for view in ("forecast", "card", "exhibit", "result"):
            self.assertIn("['" + {"forecast": "予想", "card": "出走表",
                                   "exhibit": "展示・直前", "result": "結果"}[view]
                          + "','" + view + "']", self.nav)
        self.assertIn("async function loadPredictions", self.index)
        self.assertIn("function openCleanListTab", self.index)

    def test_history_and_direct_link_restore_are_present(self):
        for snippet in ("history.pushState(", "addEventListener('popstate'",
                        "history.back()", "requestedScreen",
                        "history.replaceState(", "scheduleSync()"):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.nav)

    def test_navigation_files_are_served_and_injected(self):
        for snippet in ('"/navigation.js"', '"/secondary_navigation.js"',
                        'script src="/navigation.js"',
                        'script src="/secondary_navigation.js"'):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.server)
        self.assertIn("history.back()", self.secondary)
        self.assertIn("レース選択へ", self.secondary)

    def test_race_context_passes_to_review_and_candidate_pages(self):
        for snippet in ("destination.searchParams.set('date'",
                        "destination.searchParams.set('venue'",
                        "destination.searchParams.set('race'"):
            self.assertIn(snippet, self.nav)


if __name__ == "__main__":
    unittest.main()
