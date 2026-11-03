import io
import json
import unittest
import zipfile
from scripts.inspect_joint_t12_archive import inspect_zip


def archive(items):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as output:
        for name, payload in items:
            output.writestr(name, json.dumps(payload) if not isinstance(payload, str) else payload)
    return data.getvalue()


class ArchiveInspectionTests(unittest.TestCase):
    def test_candidate_never_converts_to_independent_source_proof(self):
        raw = archive([("reports/joint_1.json", {
            "attempt": 1, "race_code": "202611031501", "both_complete_before_t12": True})])
        result = inspect_zip(raw, 456)
        self.assertEqual(result["attempt_reports"], 1)
        self.assertEqual(result["reported_complete_candidates"], 1)
        self.assertIsNone(result["verified_source_pairs"])

    def test_report_filename_mismatch_is_rejected(self):
        raw = archive([("reports/joint_1.json", {
            "attempt": 2, "race_code": "202611031501"})])
        with self.assertRaises(ValueError):
            inspect_zip(raw, 456)

    def test_duplicate_reports_are_rejected(self):
        raw = archive([("reports/joint_1.json", {
            "attempt": 1, "race_code": "202611031501"})] * 2)
        with self.assertRaises(ValueError):
            inspect_zip(raw, 456)


if __name__ == "__main__":
    unittest.main()
