import unittest
from datetime import datetime
from unittest.mock import Mock

from scripts.observe_three_official_t12_originals import observe

RACE = "202611030212"
def instant(h, m=0):
    return datetime.fromisoformat(f"2026-11-03T{h:02d}:{m:02d}:00+09:00")

def beforeinfo():
    return {"status": "official_json_observed_not_t12_certified",
            "deadline_display": "16:05",
            "received_at_jst": instant(14).isoformat()}

class ThreeOriginalObserverTests(unittest.TestCase):
    def test_same_race_three_sources_joined_but_never_authorized(self):
        before = Mock(return_value=beforeinfo())
        card = Mock(return_value={"status": "official_racelist_html_observed_research_only",
                                  "received_at_jst": instant(14).isoformat()})
        odds = Mock(return_value={"status": "official_odds_observed_research_only"})
        auditor = Mock(return_value={"all_research_components_observed_by_t12": False,
                                     "missing_components": ["exhibition_times_six"]})
        result = observe(RACE, "/tmp/research", "a1", now=lambda: instant(14),
                         before=before, card=card, odds=odds, auditor=auditor)
        self.assertEqual(result["status"], "research_components_incomplete")
        self.assertEqual(result["audit"]["missing_components"], ["exhibition_times_six"])
        self.assertFalse(result["forecast_usable"])
        self.assertFalse(result["full_t12_source_certified"])
        self.assertEqual(odds.call_args.args[1], "2026-11-03T16:05:00+09:00")
        auditor.assert_called_once()

    def test_cutoff_preflight_prevents_all_followup_requests(self):
        card = Mock()
        odds = Mock()
        result = observe(RACE, "/tmp/research", "a2", now=lambda: instant(15, 52),
                         before=lambda *args: beforeinfo(), card=card, odds=odds)
        self.assertEqual(result["status"], "t12_preflight_expired")
        card.assert_not_called()
        odds.assert_not_called()

    def test_wrong_race_day_does_not_request(self):
        before = Mock()
        result = observe(RACE, "/tmp/research", "a3",
                         now=lambda: datetime.fromisoformat("2026-11-04T10:00:00+09:00"),
                         before=before)
        self.assertEqual(result["status"], "not_current_jst_race_day")
        before.assert_not_called()

    def test_source_failures_are_non_certifying(self):
        card = Mock()
        result = observe(RACE, "/tmp/research", "a4", now=lambda: instant(14),
                         before=lambda *args: {"status": "official_json_probe_failed"},
                         card=card)
        self.assertEqual(result["status"], "beforeinfo_source_unavailable")
        self.assertFalse(result["forecast_usable"])
        card.assert_not_called()

if __name__ == "__main__":
    unittest.main()
