"""Offline research-only tests: never certify a postrace wind label as T-12."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from research_relative_wind_official_anchor_gate import audit, _relative  # noqa: E402

LEDGER = HERE.parent / "docs/research/relative_wind_official_editorial_anchor_24venue_20261109.json"


class TestOfficialWindAnchorGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_result_does_not_certify_any_venue(self):
        result = audit(copy.deepcopy(self.data))
        self.assertEqual((result["venues_total"], result["official_historical_editorial_specific_wind_anchors"],
                          result["no_direct_text_anchor"]), (24, 8, 16))
        self.assertEqual(result["secondary_A_anchor_agreements"], 8)
        self.assertEqual(result["secondary_B_anchor_agreements"], 2)
        self.assertEqual(result["full_independent_diagram_and_same_race_arrow_certified_venues"], 0)
        self.assertEqual(result["T12_eligible_venues"], 0)
        self.assertIs(result["production_wind_transform_authorized"], False)

    def test_observed_official_articles_are_not_production_approval(self):
        for row in self.data["venues"]:
            self.assertFalse(row["production_approved"])
            self.assertIsNone(row["official_diagram_original_sha256"])
            self.assertIsNone(row["same_race_official_wind_arrow_sha256"])
            self.assertIsNone(row["t12_weather_source_sha256"])

    def test_expected_two_coordinate_bearings(self):
        self.assertEqual(_relative(0, 20), "head")  # Edogawa secondary B 200° stand+180
        self.assertEqual(_relative(0, 180), "tail")
        self.assertEqual(_relative(90, 270), "tail")
        self.assertEqual(_relative(45, 90), "oblique_head")

    def test_fake_diagram_sha_fails_closed(self):
        d = copy.deepcopy(self.data)
        d["venues"][1]["official_diagram_original_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "false_completed_primary_receipt"):
            audit(d)

    def test_fake_arrow_verified_fails_closed(self):
        d = copy.deepcopy(self.data)
        d["venues"][2]["same_race_wind_arrow_checked"] = True
        with self.assertRaisesRegex(ValueError, "false_primary_visual_verification"):
            audit(d)

    def test_fake_t12_source_fails_closed(self):
        d = copy.deepcopy(self.data)
        d["venues"][3]["t12_weather_source_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "misleading_predeadline_or_production_status"):
            audit(d)

    def test_url_injection_fails_closed(self):
        d = copy.deepcopy(self.data)
        d["venues"][1]["official_editorial_source_url"] = "https://www.boatrace.jp.evil.example/claim"
        with self.assertRaisesRegex(ValueError, "source_is_not_explicit_official_host"):
            audit(d)

    def test_one_missing_or_duplicate_venue_fails_closed(self):
        d = copy.deepcopy(self.data)
        d["venues"][0]["jcd"] = d["venues"][1]["jcd"]
        with self.assertRaisesRegex(ValueError, "missing_duplicate_or_unknown_venue"):
            audit(d)

    def test_unknown_direction_fails_closed(self):
        d = copy.deepcopy(self.data)
        d["venues"][1]["official_editorial_anchor"]["wind_from"] = "北北東"
        with self.assertRaisesRegex(ValueError, "ambiguous_directional_text"):
            audit(d)


if __name__ == "__main__":
    unittest.main()
