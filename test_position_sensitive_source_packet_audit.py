"""Isolated synthetic-only provenance inventory tests; no network."""
import copy
from hashlib import sha256
import unittest

from position_sensitive_source_packet_audit import audit_packet, KINDS, ENDPOINTS

CODE = "202611090101"
DAY = "2026-11-09"
DEADLINE = DAY + "T18:00:00+09:00"
SEEN = DAY + "T17:30:00+09:00"


def item(kind):
    raw = f"UNTRUSTED SYNTHETIC {kind} {CODE}".encode()
    return {
        "url": ("https://www.boatrace.jp" + ENDPOINTS[kind] +
                "?hd=20261109&jcd=01&rno=01"),
        "raw_bytes": raw,
        "sha256": sha256(raw).hexdigest(),
        "received_at_jst": SEEN,
        "race_code": CODE,
    }


def packet(full=True):
    return {"race_code": CODE, "deadline_jst": DEADLINE,
            "snapshots": {k: item(k) for k in KINDS} if full else {}}


class PacketAuditTests(unittest.TestCase):
    def test_missing_all_sources_no_backfill(self):
        p = audit_packet(packet(False))
        self.assertEqual(p["self_consistent_kind_count"], 0)
        self.assertEqual(set(p["missing_or_invalid_kinds"]), set(KINDS))
        self.assertFalse(p["independently_eligible_candidate"])
        self.assertFalse(p["promotion_allowed"])

    def test_locally_self_consistent_four_source_claims_still_not_verified(self):
        p = audit_packet(packet())
        self.assertTrue(p["all_raw_source_kinds_locally_self_consistent"])
        self.assertEqual(p["self_consistent_kind_count"], 4)
        for key in ("parsed_six_boats_verified", "parsed_odds120_verified",
                    "parsed_official_weather_verified",
                    "independent_official_origin_verified",
                    "independent_first_remote_receipt_verified",
                    "complete_run_attempt_inventory_verified",
                    "independently_eligible_candidate",
                    "formal", "model_improvement_proven",
                    "promotion_allowed", "production_changed"):
            self.assertFalse(p[key], key)

    def test_source_checksum_tamper_fails_closed(self):
        data = packet()
        data["snapshots"]["odds3t"]["raw_bytes"] += b"tampered"
        p = audit_packet(data)
        self.assertEqual(p["self_consistent_kind_count"], 3)
        self.assertEqual(p["missing_or_invalid_kinds"]["odds3t"], "raw_body_sha256_mismatch")

    def test_url_name_does_not_prove_origin_and_wrong_host_rejected(self):
        data = packet()
        data["snapshots"]["beforeinfo"]["url"] = (
            "https://www.boatrace.jp.evil.example" + ENDPOINTS["beforeinfo"] +
            "?hd=20261109&jcd=01&rno=01")
        self.assertEqual(audit_packet(data)["missing_or_invalid_kinds"]["beforeinfo"],
                         "unapproved_source_url_or_endpoint")
        data = packet()
        data["snapshots"]["beforeinfo"]["url"] = (
            "http://www.boatrace.jp" + ENDPOINTS["beforeinfo"] +
            "?hd=20261109&jcd=01&rno=01")
        self.assertIn("beforeinfo", audit_packet(data)["missing_or_invalid_kinds"])

    def test_cross_race_url_fails(self):
        data = packet()
        data["snapshots"]["beforeinfo"]["url"] = data["snapshots"]["beforeinfo"]["url"].replace("rno=01", "rno=02")
        self.assertEqual(audit_packet(data)["missing_or_invalid_kinds"]["beforeinfo"],
                         "source_race_mismatch")

    def test_cross_race_payload_metadata_fails(self):
        data = packet()
        data["snapshots"]["beforeinfo"]["race_code"] = "202611090102"
        self.assertIn("beforeinfo", audit_packet(data)["missing_or_invalid_kinds"])

    def test_t12_late_local_time_cannot_certify(self):
        data = packet()
        data["snapshots"]["beforeinfo"]["received_at_jst"] = DAY + "T17:48:00+09:00"
        self.assertEqual(audit_packet(data)["missing_or_invalid_kinds"]["beforeinfo"],
                         "source_not_pre_t12_or_wrong_day")

    def test_non_jst_or_previous_day_rejected(self):
        data = packet()
        data["snapshots"]["odds3t"]["received_at_jst"] = "2026-11-09T08:30:00+00:00"
        self.assertIn("odds3t", audit_packet(data)["missing_or_invalid_kinds"])
        data["snapshots"]["odds3t"]["received_at_jst"] = "2026-11-08T23:00:00+09:00"
        self.assertIn("odds3t", audit_packet(data)["missing_or_invalid_kinds"])

    def test_unexpected_source_kind_and_results_leakage_fail(self):
        data = packet()
        data["snapshots"]["race_result"] = item("beforeinfo")
        with self.assertRaisesRegex(ValueError, "invalid_source_kinds"):
            audit_packet(data)
        data = packet()
        data["confirmed_finish"] = "1-2-3"
        with self.assertRaisesRegex(ValueError, "outcome_contaminated"):
            audit_packet(data)

    def test_duplicate_query_or_bad_endpoint(self):
        data = packet()
        data["snapshots"]["beforeinfo"]["url"] += "&rno=01"
        self.assertEqual(audit_packet(data)["missing_or_invalid_kinds"]["beforeinfo"],
                         "invalid_source_race_query")
        data = packet()
        data["snapshots"]["beforeinfo"]["url"] = data["snapshots"]["beforeinfo"]["url"].replace(
            "/beforeinfo", "/result")
        self.assertIn("beforeinfo", audit_packet(data)["missing_or_invalid_kinds"])

    def test_invalid_race_day_or_deadline(self):
        data = packet()
        data["deadline_jst"] = "2026-11-10T18:00:00+09:00"
        with self.assertRaisesRegex(ValueError, "deadline_race_day_mismatch"):
            audit_packet(data)
        data = packet()
        data["race_code"] = "202611319999"
        with self.assertRaises(ValueError):
            audit_packet(data)

    def test_reject_unsafe_or_empty_source_body(self):
        data = packet()
        data["snapshots"]["racecard"]["raw_bytes"] = b""
        self.assertEqual(audit_packet(data)["missing_or_invalid_kinds"]["racecard"],
                         "unsafe_source_body")
        data["snapshots"]["racecard"]["raw_bytes"] = "not bytes"
        self.assertEqual(audit_packet(data)["missing_or_invalid_kinds"]["racecard"],
                         "unsafe_source_body")


if __name__ == "__main__":
    unittest.main()
