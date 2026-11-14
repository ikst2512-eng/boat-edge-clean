"""Pure tests: fail-closed raw official beforeinfo ST and weather provenance."""
import unittest
from decimal import Decimal
from scripts.research_official_beforeinfo_wall_witness import (
    OFFICIAL_SOURCES, parse_st, summarize_exhibition, measure_race_label,
)

def sample():
    return [
        {"cs":1,"teino":"1","st":".00"},
        {"cs":2,"teino":"2","st":".03"},
        {"cs":3,"teino":"3","st":".17"},
        {"cs":4,"teino":"4","st":".02"},
        {"cs":5,"teino":"5","st":".10"},
        {"cs":6,"teino":"6","st":".11"},
    ]

class TestBeforeInfoWallWitness(unittest.TestCase):
    def test_source_frozen_zip_digests(self):
        self.assertEqual(set(OFFICIAL_SOURCES),{"20261109","20261110"})
        self.assertEqual(
            [len(x["race_codes"]) for x in OFFICIAL_SOURCES.values()],[2,2])

    def test_exhibition_course_and_st_complete(self):
        o=summarize_exhibition(sample())
        self.assertTrue(o["complete_six_course_ST"])
        self.assertEqual(o["c2_minus_c3_ST_seconds"],"-0.14")
        self.assertEqual(o["c2_minus_c4_ST_seconds"],"0.01")
        self.assertFalse(o["wall_performance_proven"])

    def test_course_change_not_equate_boat_to_course(self):
        q=sample()
        q[1]["teino"]="3";q[2]["teino"]="2"
        o=summarize_exhibition(q)
        self.assertEqual(o["course_to_boat"]["2"],3)
        self.assertEqual(o["course_to_boat"]["3"],2)

    def test_duplicate_course_rejected(self):
        q=sample()
        q[1]["cs"]=1
        self.assertFalse(summarize_exhibition(q)["complete_six_course_ST"])

    def test_duplicate_boat_rejected(self):
        q=sample()
        q[1]["teino"]="1"
        self.assertFalse(summarize_exhibition(q)["complete_six_course_ST"])

    def test_missing_exhibition_is_unknown_not_zero(self):
        o=summarize_exhibition([])
        self.assertFalse(o["complete_six_course_ST"])
        self.assertIsNone(o["c2_minus_c3_ST_seconds"])

    def test_F_start_not_treated_as_numeric_ST(self):
        q=sample()
        q[1]["st"]="F.01"
        self.assertFalse(summarize_exhibition(q)["complete_six_course_ST"])

    def test_unparseable_ST_rejected(self):
        for raw in ("",None,".1","0.12","-0.01","1.00","F.02",0.0):
            self.assertIsNone(parse_st(raw))
        self.assertEqual(parse_st(".03"),Decimal(".03"))

    def test_prior_race_label_not_fabricated_measurement_clock(self):
        o=measure_race_label("1R時点",2)
        self.assertEqual(o["race_number_gap"],1)
        self.assertFalse(o["same_target_race"])
        self.assertIsNone(o["actual_measurement_timestamp"])
        self.assertFalse(o["measurement_timestamp_verified"])

    def test_two_race_weather_lag_label(self):
        o=measure_race_label("8R時点",10)
        self.assertEqual(o["race_number_gap"],2)

    def test_same_race_weather_label_still_has_no_timestamp(self):
        o=measure_race_label("10R時点",10)
        self.assertEqual(o["race_number_gap"],0)
        self.assertTrue(o["same_target_race"])
        self.assertIsNone(o["actual_measurement_timestamp"])

    def test_unknown_weather_label_remains_unknown(self):
        for value in ("",None,"風2m","18R時点"):
            o=measure_race_label(value,10)
            self.assertIsNone(o["race_number_gap"])
            self.assertIsNone(o["actual_measurement_timestamp"])

    def test_future_weather_label_does_not_become_negative_time(self):
        o=measure_race_label("12R時点",10)
        self.assertIsNone(o["race_number_gap"])
        self.assertIsNone(o["actual_measurement_timestamp"])

if __name__ == "__main__":
    unittest.main()
