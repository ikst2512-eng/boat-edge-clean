import json
import tempfile
import unittest
from pathlib import Path
from scripts.summarize_three_t12_venues import aggregate, markdown

def make(root, name, race, complete, *, malformed=False):
    p = Path(root) / name / "reports" / "three_originals.json"
    p.parent.mkdir(parents=True)
    checked = {"racecard_six_registrations": True, "exhibition_times_six": complete}
    audit = {
        "race_code": race,
        "official_deadline_jst": "2026-11-03T16:12:00+09:00",
        "cutoff_jst": "2026-11-03T16:00:00+09:00",
        "racelist_received_jst": "2026-11-03T15:53:00+09:00",
        "beforeinfo_received_jst": "2026-11-03T15:52:00+09:00",
        "odds_received_jst": "2026-11-03T15:54:00+09:00",
        "component_checks": checked,
        "missing_components": [] if complete else ["exhibition_times_six"],
        "all_research_components_observed_by_t12": complete,
        "full_t12_source_certified": False,
        "forecast_usable": False,
    }
    if malformed:
        audit["missing_components"] = []
    p.write_text(json.dumps({
        "race_code": race, "status": (
            "research_components_complete_by_t12" if complete
            else "research_components_incomplete"),
        "forecast_usable": False, "full_t12_source_certified": False,
        "audit": audit,
    }))


class CrossVenueTests(unittest.TestCase):
    def test_realistic_two_venues_plus_failed_cutoff(self):
        with tempfile.TemporaryDirectory() as d:
            make(d, "one", "202611030612", True)
            make(d, "two", "202611030412", False)
            path = Path(d) / "three" / "reports" / "three_originals.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "race_code": "202611030212", "status": "t12_preflight_expired",
                "forecast_usable": False, "full_t12_source_certified": False}))
            result = aggregate(d)
            self.assertEqual(result["observation_reports"], 3)
            self.assertEqual(result["research_complete_count"], 1)
            self.assertEqual(result["incomplete_or_unresolved_count"], 2)
            self.assertEqual(result["races"][2]["t12_margin_seconds"], 360)
            self.assertIn("exhibition_times_six", markdown(result))
            self.assertFalse(result["forecast_usable"])

    def test_contradictory_missing_data_refused(self):
        with tempfile.TemporaryDirectory() as d:
            make(d, "bad", "202611030612", False, malformed=True)
            with self.assertRaisesRegex(ValueError, "contradictory"):
                aggregate(d)

    def test_duplicate_race_disallowed(self):
        with tempfile.TemporaryDirectory() as d:
            make(d, "one", "202611030612", True)
            make(d, "two", "202611030612", True)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                aggregate(d)

    def test_no_reports_not_a_proven_zero_fail_rate(self):
        with tempfile.TemporaryDirectory() as d:
            result = aggregate(d)
            self.assertEqual(result["observation_reports"], 0)
            self.assertEqual(result["research_complete_count"], 0)
            self.assertFalse(result["full_t12_source_certified"])


if __name__ == "__main__":
    unittest.main()
