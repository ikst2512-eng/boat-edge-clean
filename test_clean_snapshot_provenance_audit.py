import hashlib
import unittest
import json
import tempfile
from pathlib import Path
from clean_snapshot_provenance_audit import audit_snapshot, audit_saved_directory

def fixture():
    title = "a" * 64
    cards = "b" * 64
    return {"race_code": "202610260101", "generated_at": "2026-10-26T15:00:00+09:00",
            "cutoff_jst": "2026-10-26T15:10:00+09:00",
            "source_deadline_jst": "2026-10-26T15:22:00+09:00",
            "source_title_received_jst": "2026-10-26T14:59:00+09:00",
            "source_cards_received_jst": "2026-10-26T14:59:30+09:00",
            "source_title_sha256": title, "source_cards_sha256": cards,
            "input_sha256": hashlib.sha256((title + ":" + cards).encode()).hexdigest(),
            "input_hash_scope": "source_csv_byte_hashes_ordered_title_cards"}

class SnapshotAuditTests(unittest.TestCase):
    def test_self_consistency_does_not_authorize_publication(self):
        result = audit_snapshot(fixture())
        self.assertEqual(result["status"], "metadata_self_consistent_unverified")
        self.assertFalse(result["verified"])
        self.assertFalse(result["prediction_snapshot_proven"])
    def test_missing_old_hash_is_blocked(self):
        x = fixture(); x.pop("input_sha256")
        self.assertEqual(audit_snapshot(x)["status"], "blocked_missing_source_hash")
    def test_changed_hash_is_blocked(self):
        x = fixture(); x["input_sha256"] = "0"*64
        self.assertEqual(audit_snapshot(x)["status"], "blocked_input_hash_mismatch")
    def test_postcutoff_generation_is_blocked(self):
        x = fixture(); x["generated_at"] = "2026-10-26T15:11:00+09:00"
        self.assertEqual(audit_snapshot(x)["status"], "blocked_temporal_order")
    def test_wrong_race_day_is_blocked(self):
        x = fixture(); x["race_code"] = "202610250101"
        self.assertEqual(audit_snapshot(x)["status"], "blocked_race_date_mismatch")
    def test_non_jst_timestamp_is_blocked(self):
        x = fixture(); x["generated_at"] = "2026-10-26T06:00:00+00:00"
        self.assertEqual(audit_snapshot(x)["status"], "blocked_non_jst_timestamp")
    def test_saved_filename_race_identity_mismatch_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "202610260102.json"
            path.write_text(json.dumps(fixture()), encoding="utf-8")
            result = audit_saved_directory(directory)
            self.assertEqual(result["statuses"], {"blocked_filename_race_identity": 1})
            self.assertFalse(result["all_verified"])

    def test_missing_deadline_is_blocked(self):
        x = fixture(); x.pop("source_deadline_jst")
        self.assertEqual(audit_snapshot(x)["status"], "blocked_time_evidence_incomplete")

if __name__ == "__main__":
    unittest.main()
