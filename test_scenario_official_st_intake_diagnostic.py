"""Synthetic fail-closed tests for research intake classification only.

Never creates a prospective prediction, touches a result or writes an archive.
"""
import hashlib
import json
import unittest

from scenario_official_st_intake_diagnostic import (
    CHECKS, diagnose_verified_source,
)


def fixture(st=None):
    st = st or [".03", ".11", ".09", ".08", ".17", ".20"]
    code = "202611111911"
    raw = json.dumps({"maindata": {
        "hd": "20261111", "jcd": "19", "rno": "11",
        "sttenjiinfolist": [
            {"teino": str(i), "cs": str(i), "st": v}
            for i, v in enumerate(st, 1)
        ],
    }}, separators=(",", ":")).encode("utf-8")
    audit = {
        "race_code": code,
        "official_deadline_jst": "2026-11-11T20:07:00+09:00",
        "cutoff_jst": "2026-11-11T19:55:00+09:00",
        "beforeinfo_received_jst": "2026-11-11T19:52:21.349790+09:00",
        "latest_original_received_jst": "2026-11-11T19:52:40.832892+09:00",
        "three_originals_hash_verified": True,
        "component_checks": {c: True for c in CHECKS},
        "missing_components": [],
        "all_research_components_observed_by_t12": True,
        "exhibition_course_to_boat": {str(i): str(i) for i in range(1, 7)},
        "final_race_entry_verified": False,
        "t12_eligible": False,
        "forecast_usable": False,
    }
    meta = {
        "race_code": code,
        "received_at_jst": audit["beforeinfo_received_jst"],
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    return audit, raw, meta


class OfficialSTIntakeTests(unittest.TestCase):
    def test_all_six_numeric_means_lexical_only_not_prediction(self):
        a, raw, meta = fixture()
        report = diagnose_verified_source(a, raw, meta)
        self.assertEqual(report["classification"], "all_six_numeric_ST_lexically_compatible_only")
        self.assertTrue(report["frozen_st_lexically_compatible"])
        self.assertEqual(report["flagged_st_count"], 0)
        for k in ("formal", "model_executed", "candidate_created",
                  "eligible_for_300_plus_300", "accuracy_improvement_proven"):
            self.assertFalse(report[k])

    def test_one_real_shape_F_flag_is_separate_source_complete_rejection(self):
        a, raw, meta = fixture([".25", ".15", ".09", ".06", ".06", "F.03"])
        report = diagnose_verified_source(a, raw, meta)
        self.assertTrue(report["source_complete_12_of_12"])
        self.assertEqual(report["classification"],
                         "complete_three_originals_F_L_ST_rejected_by_frozen_parser")
        self.assertEqual(report["flagged_st_by_boat"], {"6": "F.03"})
        self.assertFalse(report["frozen_st_lexically_compatible"])
        self.assertFalse(report["model_executed"])

    def test_five_flags_and_L_are_preserved_not_flipped(self):
        a, raw, meta = fixture(["F.05", "F.11", ".10", "F.02", "F.04", "F.03"])
        r = diagnose_verified_source(a, raw, meta)
        self.assertEqual(r["flagged_st_count"], 5)
        self.assertEqual(r["flagged_st_by_boat"]["1"], "F.05")
        a, raw, meta = fixture(["L.01", ".02", ".03", ".04", ".05", ".06"])
        self.assertEqual(diagnose_verified_source(a, raw, meta)["flagged_st_by_boat"], {"1": "L.01"})

    def test_incomplete_audit_never_calls_model_or_classifies_ST(self):
        a, raw, meta = fixture()
        a["component_checks"]["start_exhibition_six"] = False
        a["all_research_components_observed_by_t12"] = False
        a["missing_components"] = ["start_exhibition_six"]
        r = diagnose_verified_source(a, raw, meta)
        self.assertEqual(r["classification"], "three_originals_incomplete")
        self.assertIsNone(r["frozen_st_lexically_compatible"])
        self.assertEqual(r["missing_components"], ["start_exhibition_six"])

    def test_forged_full_source_or_component_key_rejected(self):
        a, raw, meta = fixture()
        a["component_checks"]["start_exhibition_six"] = False
        with self.assertRaisesRegex(ValueError, "inconsistent_official_source_completeness"):
            diagnose_verified_source(a, raw, meta)
        a, raw, meta = fixture()
        a["component_checks"]["made_up_key"] = True
        with self.assertRaisesRegex(ValueError, "invalid_official_12_check_contract"):
            diagnose_verified_source(a, raw, meta)

    def test_raw_sha_size_received_at_race_and_cutoff_must_agree(self):
        for field, bad in [
            ("sha256", "0"*64), ("bytes", 5),
            ("received_at_jst", "2026-11-11T19:56:00+09:00"),
            ("race_code", "202611111912"),
        ]:
            with self.subTest(field=field):
                a, raw, meta = fixture()
                meta[field] = bad
                with self.assertRaisesRegex(ValueError, "manifest_not_identical"):
                    diagnose_verified_source(a, raw, meta)
        a, raw, meta = fixture()
        a["cutoff_jst"] = "2026-11-11T19:52:00+09:00"
        with self.assertRaisesRegex(ValueError, "chronology"):
            diagnose_verified_source(a, raw, meta)

    def test_start_course_and_race_identity_must_match(self):
        a, raw, meta = fixture()
        a["exhibition_course_to_boat"]["1"] = "2"
        with self.assertRaisesRegex(ValueError, "course_mismatch"):
            diagnose_verified_source(a, raw, meta)
        a, raw, meta = fixture()
        meta["sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "manifest_not_identical"):
            diagnose_verified_source(a, raw, meta)

    def test_ambiguous_ST_rejected_not_assumed_numeric(self):
        for invalid in ("F", "F0.03", "0", "++0.02", "F.123", "unknown", ""):
            with self.subTest(invalid=invalid):
                a, raw, meta = fixture([invalid, ".02", ".03", ".04", ".05", ".06"])
                with self.assertRaisesRegex(ValueError, "unsupported_start_syntax"):
                    diagnose_verified_source(a, raw, meta)

    def test_duplicate_raw_json_key_rejected(self):
        a, raw, meta = fixture()
        raw = b'{"maindata":{}, "maindata":{}}'
        meta["bytes"] = len(raw)
        meta["sha256"] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, "official_beforeinfo_raw_invalid"):
            diagnose_verified_source(a, raw, meta)


if __name__ == "__main__":
    unittest.main()
