import io
import json
import unittest
import zipfile
from unittest.mock import patch
from scripts.reaudit_joint_t12_archive import reaudit_archive


def pack(items):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in items.items():
            archive.writestr(name, json.dumps(data) if isinstance(data, dict) else data)
    return stream.getvalue()


class T12ArchiveReauditTests(unittest.TestCase):
    def test_report_only_is_never_source_proof(self):
        raw = pack({"reports/joint_1.json": {"attempt":1, "race_code":"202611031501",
                                             "both_complete_before_t12":True}})
        result = reaudit_archive(raw, 123)
        self.assertEqual(result["independently_verified_complete_pairs"], 0)
        self.assertEqual(result["attempts"][0]["status"], "source_originals_missing")

    def test_audit_originals_reused_instead_of_report_flag(self):
        race = "202611031501"
        root = f"evidence/observations/"
        files = {"reports/joint_1.json":{"attempt":1,"race_code":race,
                                           "both_complete_before_t12":False}}
        for kind, source in (("before", "beforeinfo.json"), ("odds", "original.html")):
            base = root + f"{kind}123_1/{race[:8]}/{race}/"
            files[base + source] = "{}"
            files[base + "manifest.json"] = "{}"
        with patch("scripts.reaudit_joint_t12_archive.audit_pair",
                   return_value={"race_code":race,"both_complete_before_t12":True}) as audit:
            result = reaudit_archive(pack(files), 123)
        self.assertEqual(result["independently_verified_complete_pairs"], 1)
        self.assertFalse(result["attempts"][0]["reported_success"])
        self.assertTrue(audit.called)

    def test_duplicate_archive_entries_rejected(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream,"w") as archive:
            with __import__("warnings").catch_warnings():
                __import__("warnings").simplefilter("ignore")
                archive.writestr("reports/joint_1.json", "{}")
                archive.writestr("reports/joint_1.json", "{}")
        with self.assertRaises(ValueError):
            reaudit_archive(stream.getvalue(), 123)


if __name__ == "__main__":
    unittest.main()
