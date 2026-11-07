"""Offline fail-closed checks for 3-day official K research expansion."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from scripts.research_official_k_focus_3day import (
    TARGETS, OFFICIAL_ONLY_RACES, expected_blob_sha, reconcile_day, status_compatible,
)
from scripts.research_official_k_one_day_compare import parse_k, unpack_lha


def frozen():
    days = [dt.date(2026, 8, 1) + dt.timedelta(days=i) for i in range(92)]
    return {
        "period": "2026-08-01/2026-10-31",
        "sources": [{"day": x.isoformat(), "sha": "a" * 40, "rows": 0}
                    for x in days]
    }


class FocusThreeDayTests(unittest.TestCase):
    def test_fixed_dates_cover_four_venues(self):
        self.assertEqual(set(TARGETS), {"20260802", "20260821", "20260826"})
        self.assertEqual(
            {code[8:10] for group in TARGETS.values() for code, _ in group},
            {"03", "06", "17", "23"})

    def test_freeze_92day_sha_lookup(self):
        self.assertEqual(expected_blob_sha("20260826", frozen()), "a" * 40)

    def test_bad_period_fails_before_network(self):
        x = frozen()
        x["period"] = "2026-08-01/2026-09-30"
        with self.assertRaisesRegex(ValueError, "frozen_period_wrong"):
            expected_blob_sha("20260802", x)

    def test_missing_or_duplicate_day_fails(self):
        x = frozen()
        x["sources"].append(x["sources"][0])
        with self.assertRaisesRegex(ValueError, "frozen_days_not_92"):
            expected_blob_sha("20260802", x)

    def test_wrong_sha_fails_before_official_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "secondary_20260802.csv").write_text("not frozen", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "secondary_frozen_git_sha_mismatch"):
                reconcile_day("20260802", root, root / "archives", frozen())
            self.assertFalse((root / "archives").exists())

    def test_off_cohort_day_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "day_outside_locked_test_cohort"):
                reconcile_day("20260801", Path(tmp), Path(tmp), frozen())

    def test_page_accident_and_K_liability_not_exact_symbol(self):
        self.assertTrue(status_compatible("F", "F"))
        self.assertTrue(status_compatible("転", "S0"))
        self.assertTrue(status_compatible("転", "S1"))
        self.assertTrue(status_compatible("エ", "S0"))
        self.assertTrue(status_compatible("妨", "S2"))
        self.assertFalse(status_compatible("転", "F"))
        self.assertFalse(status_compatible("転", "S2"))
        self.assertFalse(status_compatible("妨", "S0"))
        self.assertFalse(status_compatible("F", "S1"))

    def test_only_three_documented_official_only_races_allowed(self):
        self.assertEqual(OFFICIAL_ONLY_RACES, {
            "20261012": {"202610121912"},
            "20261018": {"202610181912"},
            "20261023": {"202610232012"},
        })
        self.assertTrue(all(code.endswith("12") for codes in OFFICIAL_ONLY_RACES.values() for code in codes))

    def test_dynamic_k_filename_and_count_guard(self):
        # Invalid binary fails before attempting to treat source as an official row.
        with self.assertRaises(ValueError):
            unpack_lha(b"not an LZH file", day="20260821")
        with self.assertRaisesRegex(ValueError, "official_race_count_mismatch"):
            parse_k("", day="20260821", expected_races=12)


if __name__ == "__main__":
    unittest.main()
