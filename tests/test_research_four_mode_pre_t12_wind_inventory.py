"""Offline tests: source timing is not official wind proof or T-12 forecast clearance."""
import datetime as dt
import unittest

from scripts.research_four_mode_pre_t12_wind_inventory import (
    analyze_records, has_weather_field, timestamp
)


def sample(code="202611070301"):
    date = code[:4]+"-"+code[4:6]+"-"+code[6:8]
    return {
        "race_code": code, "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "deadline_jst": date+"T11:12:00+09:00",
        "generated_at_jst": date+"T10:52:00+09:00",
        "source_title_received_jst": date+"T10:51:00+09:00",
        "source_cards_received_jst": date+"T10:51:30+09:00",
        "beforeinfo": "optional_not_in_snapshot",
        "status": "provisional", "validated": False,
        "source_sha256": {"title": "a"*64, "race_cards": "b"*64},
    }


class FrozenFourModeT12WindInventoryTests(unittest.TestCase):
    def setUp(self):
        self.start = dt.date(2026, 11, 7)
        self.end = dt.date(2026, 11, 8)

    def analyze(self, obj):
        return analyze_records(
            [("four_mode_forecasts/"+obj["race_code"]+".json", obj, "c"*64)],
            self.start, self.end)

    def test_source_cards_pre_t12_does_not_certify_wind(self):
        report = self.analyze(sample())
        self.assertEqual(report["forecast_records"], 1)
        self.assertEqual(report["forecast_and_title_cards_before_T12"], 1)
        self.assertEqual(report["official_weather_T12_eligible_races"], 0)
        self.assertEqual(report["beforeinfo_absent_or_placeholder"], 1)
        self.assertTrue(report["missing_metadata_does_not_prove_external_source_absence"])

    def test_weather_key_alone_does_not_become_verified_receipt(self):
        x = sample()
        x["wind_speed"] = 4
        report = self.analyze(x)
        self.assertEqual(report["weather_field_key_present"], 1)
        self.assertEqual(report["source_original_official_wind_bytes_verified"], 0)
        self.assertFalse(report["records"][0]["T12_wind_eligible"])

    def test_late_source_and_forecast_not_marked_pre_cutoff(self):
        x = sample()
        x["source_cards_received_jst"] = "2026-11-07T11:01:00+09:00"
        report = self.analyze(x)
        self.assertEqual(report["title_cards_received_before_T12"], 0)
        self.assertEqual(report["forecast_and_title_cards_before_T12"], 0)

    def test_mismatched_race_identity_rejected(self):
        x = sample()
        x["race_code"] = "202611070302"
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            analyze_records(
                [("four_mode_forecasts/202611070301.json", x, "c"*64)],
                self.start, self.end)

    def test_naive_clock_and_untrusted_timezone_rejected(self):
        x = sample()
        x["generated_at_jst"] = "2026-11-07T10:52:00"
        with self.assertRaisesRegex(ValueError, "timestamp_not_explicit_JST"):
            self.analyze(x)
        x["generated_at_jst"] = "2026-11-07T01:52:00+00:00"
        with self.assertRaisesRegex(ValueError, "timestamp_not_explicit_JST"):
            self.analyze(x)

    def test_duplicate_codes_and_empty_cohort_rejected(self):
        x = sample()
        item = ("four_mode_forecasts/202611070301.json", x, "c"*64)
        with self.assertRaisesRegex(ValueError, "duplicate_or_out_of_period"):
            analyze_records([item, item], self.start, self.end)
        with self.assertRaisesRegex(ValueError, "empty_frozen_prospective_cohort"):
            analyze_records([], self.start, self.end)

    def test_freeze_study_bounds(self):
        with self.assertRaisesRegex(ValueError, "outside_frozen_study_cohort"):
            analyze_records([], dt.date(2026, 10, 1), self.end)

    def test_field_detects_metadata_in_nested_objects_not_proof(self):
        self.assertTrue(has_weather_field({"conditions": {"wind_direction": "北"}}))
        self.assertFalse(has_weather_field({"source_sha256": {"race_cards": "a"*64}}))
        self.assertEqual(timestamp("2026-11-07T10:50:00+09:00").utcoffset(),
                         dt.timedelta(hours=9))


if __name__ == "__main__":
    unittest.main()
