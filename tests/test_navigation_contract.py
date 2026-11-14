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
        cls.css = (ROOT / "styles.css").read_text(encoding="utf-8")
        cls.secondary = cls.nav

    def test_schedule_success_does_not_call_deleted_home_cards(self):
        self.assertNotIn("loadHomeRaceCards", self.index)
        self.assertIn("todayVenueRaces=data;renderDeadlines(data);", self.index)
        self.assertNotIn(".view-tabs", self.index, "retired CSS selector must not return")

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
        guard = self.nav.index("if(!nav){", probe)
        initialized = self.nav.index("document.documentElement.dataset.cleanNavigationInit='1';")
        self.assertLess(probe, guard)
        self.assertLess(guard, initialized)

    def test_nested_forecast_nav_is_hidden_not_deleted(self):
        self.assertIn('#forecast>.forecast-detail-tabs,#forecast .forecast-result-first{display:none!important}', self.css)
        self.assertIn('<link rel="stylesheet" href="styles.css">', self.index)
        self.assertIn('function setForecastPane(pane)', self.index)
        self.assertIn('class="forecast-combined-race"', self.index)

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
        self.assertNotIn("['連対率','stats']", self.nav)
        self.assertIn("view==='card'&&typeof setRaceCardPane==='function'", self.nav)
        self.assertIn("['出走表','card']", self.nav)
        self.assertIn("async function loadPredictions", self.index)
        self.assertIn("function openCleanListTab", self.index)

    def test_forecast_tickets_and_racecard_stats_are_separate(self):
        """The four main tabs remain; rates are a subtab of the race card."""
        card_start = self.index.index('<section class="box" id="raceDataSection"')
        card_end = self.index.index('<section class="box forecast-quick"', card_start)
        stats_start = self.index.index('<section class="race-card-stats-pane"', card_start)
        forecast_start = self.index.index('<section class="box" id="forecast"')
        card_stats = self.index[stats_start:card_end]
        forecast = self.index[forecast_start:]
        self.assertLess(card_start, stats_start)
        self.assertLess(stats_start, card_end)
        self.assertLess(card_end, forecast_start)
        self.assertIn('id="raceCardCore"', self.index[card_start:stats_start])
        self.assertIn('data-race-card-pane="card"', self.index[card_start:stats_start])
        self.assertIn('data-race-card-pane="rates"', self.index[card_start:stats_start])
        for required in ('forecast-statistics', 'forecastLeaderRows',
                         'entryScenarioPanel', 'legacyTopnResearch',
                         'forecast-inline-evidence', 'forecastQuinellaRows'):
            self.assertIn(required, card_stats)
            self.assertNotIn('id="' + required + '"', forecast)
        self.assertIn('id="fourModeForecastRows"', forecast)
        self.assertIn("function setRaceCardPane(pane)", self.index)
        self.assertIn("view==='card'&&raceCardPane==='rates'", self.index)
        self.assertIn("v.pane==='rates'?'rates':'card'", self.nav)
        self.assertIn("if(next.view==='card'&&next.pane==='rates')", self.nav)
        self.assertIn("restoreNavigationLocation(url,state)", self.nav)
        self.assertIn('全国・当地・モーター・ボートの2連対率', card_stats)
        self.assertIn("const raceCardValid=raw.race_key===key", self.index)
        self.assertIn("value.toFixed(1)+'%':'未取得'", self.index)

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
                        'script src="/navigation.js"'):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.server)
        # The HTML bootstrap owns the main navigation loader. Injecting it
        # again server-side would double-load the same script on Render.
        self.assertIn("navScript.src='navigation.js'", self.index)
        self.assertIn('script src="/navigation.js"', self.server)
        self.assertFalse((ROOT / "secondary_navigation.js").exists(), "duplicate standalone navigation code must not return")
        self.assertIn("history.back()", self.secondary)
        self.assertIn("レース選択へ", self.secondary)
        self.assertIn(".site-head .header-candidate-tab", self.nav)
        self.assertIn("document.documentElement.dataset.cleanStandaloneNavigationInit", self.nav)

    def test_pages_candidate_history_stays_on_pages(self):
        self.assertIn("selection.href='/boat-edge-clean/candidates.html'",self.nav)
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
