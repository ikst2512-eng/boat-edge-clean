"""Safety/regression tests for local no-network capture artifact replay."""
import csv
import hashlib
import io
import json
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from scripts.audit_four_mode_source_artifact import audit_zip

DAY = "20261108"


def make_archive(*, openapi=False, corrupt_raw=False, bad_status=False,
                 change_title=False, missing_saved=False):
    source = {}
    if openapi:
        obj = {"programs": {"stadiums": {"1": {"races": {}}}}}
        for num, rate in [(1, 5.1), (2, 0.0)]:
            racers = {str(i): {"national_win_rate": rate if i == 6 else 5.0}
                      for i in range(1, 7)}
            obj["programs"]["stadiums"]["1"]["races"][str(num)] = {
                "date": "2026-11-08", "closed_at": f"2026-11-08 08:{(num-1)*20:02d}:00",
                "racers": racers,
            }
        source["https://boatraceopenapi.github.io/api/v1/2026/20261108.json"] = json.dumps(obj).encode()
        saved = [DAY + "0101"]
        excluded = []
        cutoff = 0
    else:
        title = io.StringIO()
        t = csv.DictWriter(title, fieldnames=["レースコード", "電話投票締切予定"])
        t.writeheader()
        cards = io.StringIO()
        keys = ["レースコード"] + [f"艇{i}_全国勝率" for i in range(1, 7)]
        c = csv.DictWriter(cards, fieldnames=keys)
        c.writeheader()
        for num, time, rate in [(1, "08:00", 5.1), (2, "08:20", 0.0), (3, "07:10", 5.1)]:
            code = DAY + f"01{num:02d}"
            if change_title and num == 3:
                code = DAY + "0104"
            t.writerow({"レースコード": code, "電話投票締切予定": time})
            c.writerow({"レースコード": DAY + f"01{num:02d}",
                        **{f"艇{i}_全国勝率": (rate if i == 6 else 5.0)
                           for i in range(1, 7)}})
        source["https://boatracecsv.github.io/data/programs/title/2026/11/08.csv"] = title.getvalue().encode()
        source["https://boatracecsv.github.io/data/programs/race_cards/2026/11/08.csv"] = cards.getvalue().encode()
        saved = [] if missing_saved else [DAY + "0101"]
        excluded = [{"race_code": DAY + "0102", "reason": "invalid six national win rates"}]
        cutoff = 1
    log = {"date_jst": DAY, "new_saved": saved,
           "excluded_races": excluded,
           "excluded": {"invalid six national win rates": len(excluded)} if excluded else {},
           "cutoff_skipped": cutoff}
    status = {"day_jst": DAY, "source_status": "available", "already_saved": 0,
              "last_run_new_count": len(saved), "cutoff_skipped": cutoff,
              "excluded_races": excluded,
              "source_probes": {"openapi_direct": {"valid": 1, "rejected": 2 if bad_status else 1}}}
    b = io.BytesIO()
    with ZipFile(b, "w", ZIP_DEFLATED) as z:
        z.writestr("four-mode-evidence/capture.log", json.dumps(log))
        z.writestr("four_mode_forecasts/capture_status.json", json.dumps(status))
        for url, raw in source.items():
            stem = hashlib.sha256(url.encode()).hexdigest()
            prefix = f"four-mode-evidence/raw-sources/{stem}"
            meta = {"schema": "FOUR_MODE_LOCAL_RAW_HTTP_RECEIPT_V1",
                    "url": url, "byte_count": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "received_at_jst": "2026-11-08T07:00:00+09:00"}
            z.writestr(prefix + ".json", json.dumps(meta))
            z.writestr(prefix + ".bin", raw + (b"corrupt" if corrupt_raw else b""))
    raw_zip = b.getvalue()
    return raw_zip, hashlib.sha256(raw_zip).hexdigest()


class CaptureArtifactReplayTests(unittest.TestCase):
    def test_csv_raw_reconstructs_saved_zero_rate_and_cutoff(self):
        data, sha = make_archive()
        r = audit_zip(data, sha)
        self.assertEqual(r["raw_source_races"], 3)
        self.assertEqual(r["locally_generated"], 1)
        self.assertEqual(r["cutoff_20m_reconstructed"], 1)
        self.assertEqual(r["source_zero_rate_races"], 1)
        self.assertEqual(r["model_zero_rate_exclusions"], 1)
        self.assertTrue(r["source_receipts_sha256_checked"])
        self.assertFalse(r["independent_remote_first_seen_verified"])
        self.assertFalse(r["official_t12_certified"])

    def test_openapi_rejection_is_not_model_exclusion(self):
        data, sha = make_archive(openapi=True)
        result = audit_zip(data, sha)
        self.assertEqual(result["openapi_zero_rate_prefilter_rejections"], 1)
        self.assertEqual(result["model_zero_rate_exclusions"], 0)
        self.assertEqual(result["cutoff_20m_reconstructed"], 0)

    def test_expected_zip_digest_must_match(self):
        raw, sha = make_archive()
        with self.assertRaisesRegex(ValueError, "artifact_digest_mismatch"):
            audit_zip(raw, "0" * 64)

    def test_receipt_raw_bytes_tampering_rejected(self):
        raw, sha = make_archive(corrupt_raw=True)
        with self.assertRaisesRegex(ValueError, "raw_http_receipt_mismatch"):
            audit_zip(raw, sha)

    def test_title_card_roster_conflict_fail_closed(self):
        raw, sha = make_archive(change_title=True)
        with self.assertRaisesRegex(ValueError, "title_card_roster_mismatch"):
            audit_zip(raw, sha)

    def test_unexplained_save_gap_rejected(self):
        raw, sha = make_archive(missing_saved=True)
        with self.assertRaisesRegex(ValueError, "unexplained_source_missing_races"):
            audit_zip(raw, sha)

    def test_openapi_parser_rejection_disagreement_rejected(self):
        raw, sha = make_archive(openapi=True, bad_status=True)
        with self.assertRaisesRegex(ValueError, "openapi_rejected_count_mismatch"):
            audit_zip(raw, sha)

    def test_artifact_oversize_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_or_oversize_artifact"):
            audit_zip(b"x" * 4_000_001, "0" * 64)


if __name__ == "__main__":
    unittest.main()
