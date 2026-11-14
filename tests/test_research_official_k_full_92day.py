"""Read-only synthetic safety regression: no official K fetch or forecast imports."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.research_official_k_full_92day import (
    reconcile_one, run, validate_evidence,
)

def source_list():
    days = [dt.date(2026, 8, 1) + dt.timedelta(days=i) for i in range(92)]
    return [{"day": str(day), "sha": "a" * 40,
             "rows": 14018 if i == 0 else 1}
            for i, day in enumerate(days)]


class ResearchOfficialK92DaySafety(unittest.TestCase):
    def test_freeze_requires_92_exact_ordered_days_and_14109_rows(self):
        evidence = {"period": "2026-08-01/2026-10-31",
                    "sources": source_list()}
        self.assertEqual(len(validate_evidence(evidence)), 92)
        evidence["sources"][20]["day"] = evidence["sources"][19]["day"]
        with self.assertRaisesRegex(ValueError, "frozen_days_missing"):
            validate_evidence(evidence)

    def test_frozen_volume_change_rejected(self):
        evidence = {"period": "2026-08-01/2026-10-31", "sources": source_list()}
        evidence["sources"][1]["rows"] = 2
        with self.assertRaisesRegex(ValueError, "original_study_universe"):
            validate_evidence(evidence)

    def test_missing_secondary_never_attempts_official_fetch(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("scripts.research_official_k_full_92day.get_archive",
                       side_effect=AssertionError("should not call")):
                with self.assertRaisesRegex(FileNotFoundError, "missing_or_symlink_secondary"):
                    reconcile_one(source_list()[0], Path(root), Path(root))

    def test_changed_secondary_sha_rejected_before_fetch(self):
        with tempfile.TemporaryDirectory() as root:
            d = Path(root)
            (d / "secondary_20260801.csv").write_text("wrong")
            with patch("scripts.research_official_k_full_92day.get_archive",
                       side_effect=AssertionError("should not call")):
                with self.assertRaisesRegex(ValueError, "frozen_git_blob_mismatch"):
                    reconcile_one(source_list()[0], d, d)

    def test_only_all_92_exact_equal_counts_as_complete(self):
        with tempfile.TemporaryDirectory() as root:
            d = Path(root)
            manifest = d / "evidence.json"
            manifest.write_text(json.dumps({"period": "2026-08-01/2026-10-31",
                                            "sources": source_list()}))
            def simulated(source, _secondary, _raw):
                day = source["day"].replace("-", "")
                if day == "20261012":
                    return {"day": day, "status": "primary_extra",
                            "primary_only_race_codes": ["202610121912"],
                            "fully_compared_races": 167, "field_discrepancies": 0}
                return {"day": day, "status": "reconciled",
                        "fully_compared_races": 144, "field_discrepancies": 0}
            with patch("scripts.research_official_k_full_92day.reconcile_one",
                       side_effect=simulated):
                result = run(d, d, manifest)
            self.assertEqual(result["fully_matched_days"], 91)
            self.assertEqual(result["official_extra_days"], 1)
            self.assertFalse(result["official_source_day_complete_match"])
            self.assertFalse(result["authorized_for_production"])
            self.assertFalse(result["official_rolling_course_statistic_denominator_verified"])
            self.assertEqual(result["official_only_race_codes"], ["202610121912"])


if __name__ == "__main__":
    unittest.main()
