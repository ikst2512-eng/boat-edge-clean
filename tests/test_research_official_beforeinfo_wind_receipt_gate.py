"""Synthetic official beforeinfo weather original: fail-closed SHA, clock, identity."""
import datetime as dt
import hashlib
import json
import unittest

from scripts.research_official_beforeinfo_wind_receipt_gate import verify


def fixture():
    payload = {
        "maindata": {
            "hd": "20261104", "jcd": "01", "rno": 11, "deadline": "20:03",
            "teiinfolist": [{"teino": str(x)} for x in range(1, 7)],
            "sttenjiinfolist": [{"teino": str(x), "cs": x} for x in range(1, 7)],
            "weatherinfo": {
                "wind": "2m", "wave": "1cm", "measuretime": "10R時点",
                "winddirec": "02", "northdirec": "14",
            },
        },
    }
    raw = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    meta = {
        "race_code": "202611040111",
        "url": "https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&hd=20261104&jcd=01&rno=11",
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        "request_started_at_jst": "2026-11-04T19:39:13+09:00",
        "received_at_jst": "2026-11-04T19:39:21+09:00",
    }
    return payload, raw, meta


class BeforeinfoWindReceiptTests(unittest.TestCase):
    def test_sha_verified_pre_t12_raw_weather_does_not_certify_forecast(self):
        _, raw, meta = fixture()
        out = verify(raw, meta, "202611040111")
        self.assertTrue(out["received_at_or_before_t12"])
        self.assertEqual(out["wind_speed_raw"], "2m")
        self.assertEqual(out["measurement_label_raw"], "10R時点")
        self.assertFalse(out["absolute_wind_compass_verified"])
        self.assertFalse(out["exact_weather_measurement_timestamp_verified"])
        self.assertFalse(out["T12_forecast_certified"])
        self.assertFalse(out["can_join_20261106_08_forecast_cohort"])

    def test_tampered_original_rejected(self):
        _, raw, meta = fixture()
        with self.assertRaisesRegex(ValueError, "sha_or_bytes_mismatch"):
            verify(raw+b"x", meta, "202611040111")

    def test_forecast_received_after_t12_not_passed(self):
        _, raw, meta = fixture()
        meta["received_at_jst"] = "2026-11-04T19:55:00+09:00"
        out = verify(raw, meta, "202611040111")
        self.assertFalse(out["received_at_or_before_t12"])

    def test_source_receipt_timezone_must_be_explicit_jst(self):
        _, raw, meta = fixture()
        meta["received_at_jst"] = "2026-11-04T10:39:21+00:00"
        with self.assertRaisesRegex(ValueError, "must_be_JST"):
            verify(raw, meta, "202611040111")

    def test_wrong_original_race_identity_rejected(self):
        payload, _, meta = fixture()
        payload["maindata"]["rno"] = 10
        bad = (json.dumps(payload, ensure_ascii=False)+"\n").encode()
        meta["sha256"] = hashlib.sha256(bad).hexdigest()
        meta["bytes"] = len(bad)
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            verify(bad, meta, "202611040111")

    def test_missing_one_boat_in_start_exhibition_rejected(self):
        payload, _, meta = fixture()
        payload["maindata"]["sttenjiinfolist"].pop()
        bad = (json.dumps(payload, ensure_ascii=False)+"\n").encode()
        meta["sha256"] = hashlib.sha256(bad).hexdigest()
        meta["bytes"] = len(bad)
        with self.assertRaisesRegex(ValueError, "six_boat"):
            verify(bad, meta, "202611040111")

    def test_weather_units_required(self):
        payload, _, meta = fixture()
        payload["maindata"]["weatherinfo"]["wind"] = "2.0"
        bad = (json.dumps(payload, ensure_ascii=False)+"\n").encode()
        meta["sha256"] = hashlib.sha256(bad).hexdigest()
        meta["bytes"] = len(bad)
        with self.assertRaisesRegex(ValueError, "weather_units_invalid"):
            verify(bad, meta, "202611040111")

    def test_reversed_request_clock_rejected(self):
        _, raw, meta = fixture()
        meta["request_started_at_jst"] = "2026-11-04T19:39:30+09:00"
        with self.assertRaisesRegex(ValueError, "chronology"):
            verify(raw, meta, "202611040111")


if __name__ == "__main__":
    unittest.main()
