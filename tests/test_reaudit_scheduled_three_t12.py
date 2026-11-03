import io
import json
import unittest
import zipfile
from unittest.mock import Mock

from scripts.reaudit_scheduled_three_t12 import audit_artifact, review_runs, markdown

RACE = "202611030212"


def zip_bytes(content):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for path, data in content.items():
            z.writestr(path, data)
    return buf.getvalue()


def source_archive(run_id, status="research_components_incomplete"):
    prefix = lambda part: f"evidence/observations/{part}{run_id}/20261103/{RACE}/"
    source_files = {
        prefix("before") + "beforeinfo.json": "{}",
        prefix("before") + "manifest.json": "{}",
        prefix("card") + "racelist.html": "<html></html>",
        prefix("card") + "manifest.json": "{}",
        prefix("odds") + "original.html": "<html></html>",
        prefix("odds") + "manifest.json": "{}",
    }
    report = {"race_code": RACE, "status": status,
              "forecast_usable": False, "full_t12_source_certified": False,
              "audit": {"component_checks": {"exhibition_times_six": False},
                        "missing_components": ["exhibition_times_six"],
                        "cutoff_jst": "2026-11-03T15:53:00+09:00",
                        "racelist_received_jst": "2026-11-03T15:45:00+09:00",
                        "beforeinfo_received_jst": "2026-11-03T15:44:00+09:00",
                        "odds_received_jst": "2026-11-03T15:46:00+09:00"}}
    source_files["reports/three_originals.json"] = json.dumps(report)
    return zip_bytes(source_files)


def independent_result():
    return {"race_code": RACE,
            "component_checks": {"exhibition_times_six": False},
            "missing_components": ["exhibition_times_six"],
            "cutoff_jst": "2026-11-03T15:53:00+09:00",
            "racelist_received_jst": "2026-11-03T15:45:00+09:00",
            "beforeinfo_received_jst": "2026-11-03T15:44:00+09:00",
            "odds_received_jst": "2026-11-03T15:46:00+09:00",
            "all_research_components_observed_by_t12": False}


class T12ScheduledAuditTests(unittest.TestCase):
    def test_verified_originals_do_not_use_report_flag_as_proof(self):
        auditor = Mock(return_value=independent_result())
        result = audit_artifact(source_archive(123), 123, auditor=auditor)
        self.assertEqual(result["status"], "independent_originals_reaudited")
        self.assertEqual(result["missing_components"], ["exhibition_times_six"])
        self.assertFalse(result["research_complete"])
        self.assertFalse(result["forecast_usable"])
        auditor.assert_called_once()

    def test_malformed_or_missing_source_cannot_pass(self):
        result = audit_artifact(zip_bytes({"reports/three_originals.json": json.dumps({
            "race_code": RACE, "status": "research_components_complete_by_t12",
            "forecast_usable": False, "full_t12_source_certified": False})}), 123)
        self.assertEqual(result["status"], "source_original_missing")
        self.assertFalse(result["research_complete"])

    def test_fake_report_conflicting_with_reaudited_source_rejected(self):
        other = independent_result()
        other["component_checks"] = {"exhibition_times_six": True}
        with self.assertRaisesRegex(ValueError, "disagrees"):
            audit_artifact(source_archive(123), 123, auditor=lambda *args: other)

    def test_duplicate_scheduled_run_rejected(self):
        x = {"id": 99, "event": "schedule", "created_at": "2026-11-03T06:30:00Z"}
        with self.assertRaisesRegex(ValueError, "invalid scheduled run"):
            review_runs([x, x], lambda _: [], lambda _: b"")

    def test_missing_artifact_reported_unverified_not_success(self):
        x = {"id": 99, "event": "schedule", "created_at": "2026-11-03T06:30:00Z",
             "conclusion": "success"}
        result = review_runs([x], lambda _: [], lambda _: b"")
        self.assertEqual(result["observed_scheduled_runs"], 1)
        self.assertEqual(result["research_complete_by_t12"], 0)
        self.assertEqual(result["missing_or_unverified_runs"], 1)
        self.assertIn("missing_or_ambiguous_artifact", markdown(result))
        self.assertFalse(result["all_scheduled_slots_proven"])
        self.assertFalse(result["full_t12_source_certified"])

    def test_empty_inventory_does_not_invent_completion(self):
        result = review_runs([], lambda _: [], lambda _: b"")
        self.assertEqual(result["observed_scheduled_runs"], 0)
        self.assertIn("記録なし", markdown(result))

    def test_archive_traversal_and_duplicate_entries_rejected(self):
        bad = zip_bytes({"../secret": "x", "reports/three_originals.json": "{}"})
        with self.assertRaisesRegex(ValueError, "unsafe"):
            audit_artifact(bad, 123)

    def test_prior_day_run_rejected(self):
        x = {"id": 99, "event": "schedule", "created_at": "2026-11-02T06:30:00Z"}
        with self.assertRaisesRegex(ValueError, "invalid scheduled run"):
            review_runs([x], lambda _: [], lambda _: b"")


if __name__ == "__main__":
    unittest.main()
