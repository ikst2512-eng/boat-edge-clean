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

    def test_schedule_success_does_not_call_deleted_home_cards(self):
        self.assertNotIn("loadHomeRaceCards", self.index)
        self.assertIn("todayVenueRaces=data;renderDeadlines(data);", self.index)

    def test_pages_schedule_snapshot_is_local_first_with_clean_fallback(self):
        """Archived schedules should survive Raw outages without old-site data."""
        pages = (ROOT / ".github" / "workflows" / "deploy-pages.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("'schedule_snapshots/**'", pages)
        self.assertIn("cp -R schedule_snapshots public/schedule_snapshots", pages)
        self.assertIn('SNAPSHOT_URL="${PAGE_URL%/}/schedule_snapshots/${SNAPSHOT_KEY}.json"', pages)
        self.assertIn("location.hostname==='ikst2512-eng.github.io'", self.index)
        self.assertIn("for(const endpoint of [pagesSchedule,rawSchedule].filter(Boolean))", self.index)
        self.assertIn("if(response.ok){archive=response;break;}", self.index)
        self.assertIn("'https://boat-edge-clean.onrender.com/api/clean-schedule?date='+dayCode", self.index)
        self.assertNotIn("ikst2512-eng/boat-edge/main/today.json", self.index)

    def test_navigation_initialization_waits_for_nav_element(self):
        probe = self.nav.index("const nav=document.querySelector('.site-global-nav');")
        guard = self.nav.index("if(!nav)return;", probe)
        initialized = self.nav.index("document.documentElement.dataset.cleanNavigationInit='1';")
        self.assertLess(probe, guard)
        self.assertLess(guard, initialized)

    def test_nested_forecast_nav_is_hidden_not_deleted(self):
        self.assertIn('#forecast>.forecast-detail-tabs,#forecast .forecast-result-first{display:none!important}', self.index)
        self.assertIn('function setForecastPane(pane)', self.index)
        self.assertIn('class="forecast-combined-race"', self.index)

    def test_deadline_heading_and_status_contrast_override(self):
        self.assertIn('#deadlineSection h2{color:#193958!important}', self.index)
        self.assertIn('#deadlineStatus{color:#355675!important}', self.index)

    def test_hidden_forecast_race_list_does_not_prefetch_results(self):
        self.assertIn('class="forecast-race-list" hidden', self.index)
        start = self.index.index('async function loadResultList(){')
        pane = self.index.index("const pane=document.querySelector('#forecast > .forecast-race-list');", start)
        guard = self.index.index("if(activeView!=='forecast'||!pane||pane.hidden)return;", pane)
        fanout = self.index.index('const entries=await Promise.all', start)
        self.assertLess(pane, guard)
        self.assertLess(guard, fanout)

    def test_four_mode_archive_cors_allows_only_pages_origin(self):
        """The real read-only endpoint must be usable from GitHub Pages."""
        from http.client import HTTPConnection
        from http.server import ThreadingHTTPServer
        from threading import Thread
        from server import Handler

        origin = "https://ikst2512-eng.github.io"
        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as httpd:
            thread = Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                for race_code, status in (("202611061006", 200), ("invalid", 422)):
                    for request_origin in (origin, "https://not-the-clean-site.example"):
                        conn = HTTPConnection("127.0.0.1", httpd.server_port, timeout=10)
                        try:
                            conn.request(
                                "GET", "/api/four-mode-archive?code=" + race_code,
                                headers={"Origin": request_origin}
                            )
                            response = conn.getresponse()
                            response.read()
                            self.assertEqual(response.status, status)
                            self.assertEqual(response.getheader("Access-Control-Allow-Origin"), origin)
                            if request_origin != origin:
                                self.assertNotEqual(response.getheader("Access-Control-Allow-Origin"), request_origin)
                        finally:
                            conn.close()
            finally:
                httpd.shutdown()
                thread.join(timeout=10)

    def test_duplicate_forecast_picker_never_reappears(self):
        self.assertIn("document.getElementById('forecastQuick').hidden=true", self.index)
        self.assertNotIn("document.getElementById('forecastQuick').hidden=view!=='forecast'", self.index)

    def test_main_navigation_keeps_only_requested_pages(self):
        match = re.search(r'<nav class="site-global-nav[^"]*"[^>]*>(.*?)</nav>', self.index)
        self.assertIsNotNone(match)
        self.assertEqual(re.findall(r'href="([^"]+)"', match.group(1)),
                         ["/review"])
        self.assertEqual(len(re.findall(r'class="header-candidate-tab"', self.index)), 1)
        self.assertIn('class="header-candidate-tab" href="/selection"', self.index)
        self.assertNotIn("nav.innerHTML=", self.nav)

    def test_detail_views_and_prediction_entry_still_exist(self):
        for view in ("forecast", "card", "exhibit", "result"):
            self.assertIn("['" + {"forecast": "予想", "card": "出走表",
                                   "exhibit": "展示・直前", "result": "結果"}[view]
                          + "','" + view + "']", self.nav)
        self.assertIn("async function loadPredictions", self.index)
        self.assertIn("function openCleanListTab", self.index)

    def test_prediction_shortcut_resets_nested_forecast_tab(self):
        self.assertIn("view==='forecast'&&typeof setForecastPane==='function'", self.nav)
        self.assertIn("setForecastPane('prediction')", self.nav)

    def test_history_and_direct_link_restore_are_present(self):
        for snippet in ("history.pushState(", "addEventListener('popstate'",
                        "history.back()", "requestedScreen",
                        "history.replaceState(", "scheduleSync()"):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.nav)

    def test_navigation_files_are_served_and_injected(self):
        for snippet in ('"/navigation.js"', '"/secondary_navigation.js"',
                        'script src="/secondary_navigation.js"'):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.server)
        # The HTML bootstrap owns the main navigation loader. Injecting it
        # again server-side would double-load the same script on Render.
        self.assertIn("navScript.src='navigation.js'", self.index)
        self.assertNotIn('script src="/navigation.js"', self.server)
        self.assertIn("history.back()", self.secondary)
        self.assertIn("レース選択へ", self.secondary)
        self.assertIn(".site-head .header-candidate-tab", self.nav)

    def test_pages_candidate_route_is_render_and_keeps_origin(self):
        self.assertIn("selection.href='https://boat-edge-clean.onrender.com/selection'",self.nav)
        self.assertIn("document.querySelector('.site-head .header-candidate-tab[href=", self.nav)
        self.assertIn("destination.origin===location.origin?destination.pathname+destination.search:destination.href",self.nav)

    def test_github_pages_logo_does_not_leave_clean_site(self):
        self.assertIn("location.hostname.endsWith('.github.io')", self.nav)
        self.assertIn("?'/boat-edge-clean/':'/'", self.nav)

    def test_standalone_navigation_skips_race_history_without_state(self):
        guard = "if(typeof s==='undefined'||typeof activeView==='undefined')return;"
        self.assertIn(guard, self.nav)
        self.assertLess(self.nav.index("document.querySelectorAll('.site-global-nav a, .site-head .header-candidate-tab').forEach"), self.nav.index(guard))
        self.assertLess(self.nav.index(guard), self.nav.index("const initial=snapshot();"))

    def test_navigation_link_click_handles_missing_race_state(self):
        self.assertIn("typeof s==='undefined'?null:s", self.nav)
        self.assertIn("const date=state?.date,venue=state?.venue,race=state?.race;", self.nav)
        self.assertNotIn("const date=s?.date,venue=s?.venue,race=s?.race;", self.nav)

    def test_race_context_passes_to_review_and_candidate_pages(self):
        for snippet in ("destination.searchParams.set('date'",
                        "destination.searchParams.set('venue'",
                        "destination.searchParams.set('race'"):
            self.assertIn(snippet, self.nav)


if __name__ == "__main__":
    unittest.main()
