"""Offline same-race chronology tests: bytes/SHA and time do not imply model use."""
import base64
import hashlib
import itertools
import json
import unittest

from scripts.research_t12_same_race_receipt_join import join


CODE = "202611040111"


def documents():
    weather_payload = {
        "maindata": {
            "hd": "20261104", "jcd": "01", "rno": 11,
            "deadline": "20:03",
            "teiinfolist": [{"teino": str(i)} for i in range(1, 7)],
            "sttenjiinfolist": [{"teino": str(i), "cs": i} for i in range(1, 7)],
            "weatherinfo": {"wind": "2m", "wave": "1cm",
                            "measuretime": "10R時点", "winddirec": "02",
                            "northdirec": "14"},
        }
    }
    before_raw = json.dumps(weather_payload, ensure_ascii=False).encode()
    before_manifest = {
        "race_code": CODE,
        "sha256": hashlib.sha256(before_raw).hexdigest(),
        "bytes": len(before_raw),
        "url": "https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&hd=20261104&jcd=01&rno=11",
        "request_started_at_jst": "2026-11-04T19:39:13+09:00",
        "received_at_jst": "2026-11-04T19:39:21+09:00",
    }
    forecast = {
        "race_code": CODE, "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "status": "provisional", "validated": False,
        "deadline_jst": "2026-11-04T20:03:00+09:00",
        "generated_at_jst": "2026-11-04T11:09:10+09:00",
        "source_title_received_jst": "2026-11-04T11:09:08+09:00",
        "source_cards_received_jst": "2026-11-04T11:09:09+09:00",
        "beforeinfo": "optional_not_in_snapshot",
    }
    odds_payload = {
        "ok": True, "hd": "20261104", "jcd": "01", "rno": 11,
        "odds": {"-".join(perm): 11.8 for perm in itertools.permutations("123456", 3)},
        "fetched_at": "2026-11-04T10:37:20+00:00",
    }
    odds_bytes = json.dumps(odds_payload).encode()
    attempt = {
        "http": 200, "state": "valid_200",
        "started_at_utc": "2026-11-04T10:37:16+00:00",
        "finished_at_utc": "2026-11-04T10:37:23+00:00",
        "response_base64": base64.b64encode(odds_bytes).decode(),
        "response_sha256": hashlib.sha256(odds_bytes).hexdigest(),
    }
    replay = {
        "formal": False, "formal_t12_certified": False,
        "date": "20261104", "trigger": {"event": "local_manual"},
        "samples": [{"race_code": CODE, "final_state": "valid_200",
                     "source_deadline_jst": "2026-11-04T20:03:00+09:00",
                     "attempts": [attempt]}],
    }
    return (json.dumps(forecast).encode(), before_raw, before_manifest, replay)


class RealSourceGateTests(unittest.TestCase):
    def test_realistic_timely_receipts_after_forecast_do_not_prove_usage(self):
        report = join(CODE, *documents())
        self.assertTrue(report["forecast_and_two_http_receipts_before_t12"])
        self.assertEqual(report["public_odds_api_replay"]["raw_http_response_bytes"] > 0, True)
        self.assertTrue(report["public_odds_api_replay"]["120_trifecta_combos_in_api_response_verified"])
        self.assertFalse(report["official_beforeinfo_received_before_forecast_generation"])
        self.assertFalse(report["api_odds_received_before_forecast_generation"])
        self.assertFalse(report["two_http_receipts_received_by_forecast_generation"])
        self.assertFalse(report["formal_T12_forecast_eligible"])
        self.assertFalse(report["official_odds_original_SHA_receipt_independently_verified"])

    def test_earlier_receipts_still_not_automatically_certified(self):
        forecast, before, meta, replay = documents()
        data = json.loads(forecast)
        data["generated_at_jst"] = "2026-11-04T19:45:00+09:00"
        result = join(CODE, json.dumps(data).encode(), before, meta, replay)
        self.assertTrue(result["two_http_receipts_received_by_forecast_generation"])
        self.assertFalse(result["formal_T12_forecast_eligible"])

    def test_odds_sha_tamper_rejected(self):
        forecast, before, meta, replay = documents()
        replay["samples"][0]["attempts"][0]["response_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "odds_response_SHA_mismatch"):
            join(CODE, forecast, before, meta, replay)

    def test_missing_trifecta_rejected(self):
        forecast, before, meta, replay = documents()
        sample = replay["samples"][0]["attempts"][0]
        payload = json.loads(base64.b64decode(sample["response_base64"]))
        del payload["odds"]["1-2-3"]
        raw = json.dumps(payload).encode()
        sample["response_base64"] = base64.b64encode(raw).decode()
        sample["response_sha256"] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, "odds_120_tri"):
            join(CODE, forecast, before, meta, replay)

    def test_distinct_race_rejected_even_if_clock_matches(self):
        forecast, before, meta, replay = documents()
        replay["samples"][0]["race_code"] = "202611040112"
        with self.assertRaisesRegex(ValueError, "race_not_unique"):
            join(CODE, forecast, before, meta, replay)

    def test_public_deadline_mismatch_rejected(self):
        forecast, before, meta, replay = documents()
        replay["samples"][0]["source_deadline_jst"] = "2026-11-04T20:07:00+09:00"
        with self.assertRaisesRegex(ValueError, "deadline_disagrees"):
            join(CODE, forecast, before, meta, replay)

    def test_odds_received_after_cutoff_is_not_claimed_in_time(self):
        forecast, before, meta, replay = documents()
        replay["samples"][0]["attempts"][0]["finished_at_utc"] = "2026-11-04T10:55:00+00:00"
        report = join(CODE, forecast, before, meta, replay)
        self.assertFalse(report["api_odds_received_by_t12"])
        self.assertFalse(report["forecast_and_two_http_receipts_before_t12"])

    def test_forecast_generation_cannot_precede_own_saved_sources(self):
        forecast, before, meta, replay = documents()
        data = json.loads(forecast)
        data["generated_at_jst"] = "2026-11-04T11:00:00+09:00"
        with self.assertRaisesRegex(ValueError, "forecast_generated_before_own"):
            join(CODE, json.dumps(data).encode(), before, meta, replay)

    def test_forecast_identity_or_provenance_not_permissive(self):
        forecast, before, meta, replay = documents()
        data = json.loads(forecast)
        data["status"] = "certified"
        with self.assertRaisesRegex(ValueError, "identity_or_provenance_invalid"):
            join(CODE, json.dumps(data).encode(), before, meta, replay)


if __name__ == "__main__":
    unittest.main()
