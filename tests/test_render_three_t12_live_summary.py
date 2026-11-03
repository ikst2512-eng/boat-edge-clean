import unittest
from scripts.render_three_t12_live_summary import summarize

RACE = "202611030212"
KEYS = ["racecard_original_hash_verified", "racecard_six_registrations",
        "racecard_received_by_t12", "beforeinfo_received_by_t12",
        "exhibition_six_courses", "exhibition_times_six", "tilt_six",
        "start_exhibition_six", "odds_120", "odds_received_by_t12"]


def observation(complete=False):
    checks = {k: True for k in KEYS}
    if not complete:
        checks["exhibition_times_six"] = False
        checks["start_exhibition_six"] = False
    return {"race_code": RACE, "status": "research_components_incomplete" if not complete else "research_components_complete_by_t12",
            "forecast_usable": False, "full_t12_source_certified": False,
            "audit": {"race_code": RACE, "full_t12_source_certified": False,
                      "official_deadline_jst": "2026-11-03T16:05:00+09:00",
                      "cutoff_jst": "2026-11-03T15:53:00+09:00",
                      "racelist_received_jst": "2026-11-03T15:40:00+09:00",
                      "beforeinfo_received_jst": "2026-11-03T15:40:01+09:00",
                      "odds_received_jst": "2026-11-03T15:40:02+09:00",
                      "component_checks": checks,
                      "missing_components": [k for k,v in checks.items() if not v],
                      "all_research_components_observed_by_t12": complete}}


class LiveT12SummaryTests(unittest.TestCase):
    def test_incomplete_summary_shows_exhibition_shortfall(self):
        out = summarize(observation())
        self.assertIn("展示タイム6艇 | 未達", out)
        self.assertIn("展示ST6艇 | 未達", out)
        self.assertIn("15:53:00+09:00", out)
        self.assertIn("未達成", out)
        self.assertIn("使用許可: **なし**", out)

    def test_research_complete_still_not_forecast_certified(self):
        out = summarize(observation(True))
        self.assertIn("充足: **達成**", out)
        self.assertIn("実進入確定・T−12完全認証: **未認証**", out)

    def test_failed_fetch_does_not_fake_completion(self):
        out = summarize({"race_code": RACE, "status": "beforeinfo_source_unavailable",
                         "forecast_usable": False, "full_t12_source_certified": False,
                         "beforeinfo_status": "official_json_probe_failed"})
        self.assertIn("独立監査は未完了", out)
        self.assertNotIn("充足: **達成**", out)

    def test_contradictory_report_rejected(self):
        bad = observation()
        bad["audit"]["missing_components"] = []
        with self.assertRaisesRegex(ValueError, "contradictory"):
            summarize(bad)
        bad = observation()
        bad["forecast_usable"] = True
        with self.assertRaisesRegex(ValueError, "certification"):
            summarize(bad)


if __name__ == "__main__":
    unittest.main()
