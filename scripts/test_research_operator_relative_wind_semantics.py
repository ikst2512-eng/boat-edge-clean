"""Offline research-only negative tests of operator wind labeling provenance."""
import copy
import json
import unittest
from pathlib import Path

from scripts.research_operator_relative_wind_semantics import (
    audit, official_url, relative_5, operator_coarse
)

SRC = Path(__file__).resolve().parents[1] / (
    "docs/research/operator_ashiya_8wind_label_source_20261109.json"
)

class TestOperatorWindSemantics(unittest.TestCase):
    def load(self):
        return json.loads(SRC.read_text(encoding="utf-8"))

    def test_unique_east_axis_and_research_only(self):
        result = audit(self.load())
        self.assertEqual(result["consistent_candidate_angles_deg"], [90])
        self.assertEqual([x["agree"] for x in result["angle_candidates"]],
                         [2, 4, 8, 4, 2, 0, 0, 0])
        self.assertFalse(result["T12_weather_eligible"])
        self.assertFalse(result["production_wind_transform_authorized"])

    def test_geometry_preserves_oblique_and_left_right(self):
        self.assertEqual(relative_5(0, 90), "cross_left")
        self.assertEqual(relative_5(180, 90), "cross_right")
        self.assertEqual(relative_5(45, 90), "oblique_head")
        self.assertEqual(relative_5(225, 90), "oblique_tail")
        self.assertEqual(operator_coarse("oblique_head"), "向い風")
        self.assertEqual(operator_coarse("oblique_tail"), "追い風")

    def test_reject_missing_direction(self):
        x = self.load()
        x["source_rows"] = x["source_rows"][:-1]
        with self.assertRaises(ValueError):
            audit(x)

    def test_reject_duplicate_direction(self):
        x = self.load()
        x["source_rows"][0] = copy.deepcopy(x["source_rows"][1])
        with self.assertRaises(ValueError):
            audit(x)

    def test_reject_contradictory_operator_label(self):
        x = self.load()
        next(r for r in x["source_rows"] if r["wind_from"] == "東")["operator_label"] = "右横風"
        with self.assertRaises(ValueError):
            audit(x)

    def test_reject_untrusted_url_and_subdomain_trick(self):
        for url in ("http://www.boatrace-ashiya.com/sp/", 
                    "https://www.boatrace-ashiya.com.attacker.test/sp/",
                    "https://example.com/sp/"):
            x = self.load()
            x["source_rows"][0]["source_url"] = url
            with self.assertRaises(ValueError):
                audit(x)
        self.assertTrue(official_url("https://boatrace-ashiya.com/sp/?motor_no=23"))

    def test_reject_spoofed_raw_receipt(self):
        for flag in ("source_document_sha256", "water_diagram_original_png_sha256",
                     "original_same_race_wind_arrow_sha256", "t12_beforeinfo_original_sha256"):
            x = self.load()
            x[flag] = "0" * 64
            with self.assertRaises(ValueError):
                audit(x)

    def test_reject_spoofed_certification(self):
        for flag in ("official_diagram_second_reader_signed_off", "formal_heading_certified",
                     "t12_eligible", "production_authorized", "main_modified"):
            x = self.load()
            x[flag] = True
            with self.assertRaises(ValueError):
                audit(x)

    def test_calm_is_not_2nd_direction(self):
        x = self.load()
        x["calm_row"]["operator_label"] = "向い風"
        with self.assertRaises(ValueError):
            audit(x)

if __name__ == "__main__":
    unittest.main()
