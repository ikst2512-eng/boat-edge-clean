"""Synthetic ZIP/manifest failure modes; no network and no formal certificates."""
import hashlib
import io
import json
import unittest
import zipfile
from copy import deepcopy
from datetime import datetime

from scripts.audit_t12_scheduled_pair_zip import replay

RUN = 42450048245
CODE = "202611080309"
DAY = CODE[:8]
BEFORE_AT = "2026-11-08T14:15:38+09:00"
ODDS_AT = "2026-11-08T14:15:48+09:00"
CUT = "2026-11-08T14:18:00+09:00"


def sources():
    data = {"maindata": {
        "hd": DAY, "jcd": "03", "rno": "9", "deadline": "14:30",
        "teiinfolist": [
            {"teino": str(i), "extime": "6.90", "tilt": "0.0"}
            for i in range(1, 7)
        ],
        "sttenjiinfolist": [
            {"teino": str(i), "cs": i, "st": ".12"}
            for i in range(1, 7)
        ],
    }}
    before = json.dumps(data).encode()
    odds = b"<!doctype html><html>independent auditor stub fixture</html>"
    def manifest(raw, *, kind):
        url = ("https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo"
               "&hd=20261108&jcd=03&rno=9" if kind == "before"
               else "https://www.boatrace.jp/owpc/pc/race/odds3t"
               "?hd=20261108&jcd=03&rno=9")
        return {
            "race_code": CODE,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "status": ("official_json_observed_not_t12_certified"
                       if kind == "before" else
                       "official_odds_observed_research_only"),
            "url" if kind == "before" else "official_url": url,
            "request_started_at_jst": "2026-11-08T14:15:15+09:00",
            "received_at_jst": BEFORE_AT if kind == "before" else ODDS_AT,
        }
    prefix = f"official_joint_evidence/observations/"
    b = prefix + f"before_run{RUN}/{DAY}/{CODE}/"
    o = prefix + f"odds_run{RUN}/{DAY}/{CODE}/"
    return {
        b + "beforeinfo.json": before,
        b + "manifest.json": json.dumps(manifest(before, kind="before")).encode(),
        o + "original.html": odds,
        o + "manifest.json": json.dumps(manifest(odds, kind="odds")).encode(),
    }


def audited(*, complete=True):
    comp = {
        "six_unique_boats": True, "exhibition_time_six": complete,
        "tilt_six": True, "start_exhibition_six": complete,
        "beforeinfo_received_by_t12": True,
        "official_odds_120": True, "odds_received_by_t12": True,
    }
    return {
        "race_code": CODE,
        "cutoff_jst": CUT,
        "before_received_jst": BEFORE_AT,
        "odds_received_jst": ODDS_AT,
        "both_complete_before_t12": complete,
        "component_checks": comp,
        "missing_components": [] if complete else [
            "exhibition_time_six", "start_exhibition_six"],
        "originals_hash_verified": True,
        "odds_120_complete": True,
        "full_t12_source_certified": False,
        "forecast_usable": False,
    }


def make_report(*, pair=True, no_odds=False, complete=True):
    if not pair:
        return {
            "event": "schedule", "date": DAY,
            "checked_at_jst": "2026-11-08T20:59:54+09:00",
            "formal": False, "forecast_usable": False,
            "full_t12_source_certified": False,
            "eligible_candidates": 0, "observations": [],
            "beforeinfo_originals_saved": 0,
            "official_odds_originals_saved": 0,
            "complete_pairs_before_t12": 0,
            "status": "no_pre_t12_candidate",
        }
    status = "odds_failed" if no_odds else (
        "pair_complete" if complete else "pair_not_ready")
    row = {"race_code": CODE, "status": status,
           "forecast_usable": False}
    if not no_odds:
        row["joint_audit"] = audited(complete=complete)
    return {
        "event": "schedule", "date": DAY,
        "checked_at_jst": "2026-11-08T14:15:20+09:00",
        "formal": False, "forecast_usable": False,
        "full_t12_source_certified": False,
        "eligible_candidates": 1, "observations": [row],
        "beforeinfo_originals_saved": 1,
        "official_odds_originals_saved": 0 if no_odds else 1,
        "complete_pairs_before_t12": 0 if no_odds or not complete else 1,
        "status": "source_capture_failed" if no_odds else
            ("complete_pairs_observed" if complete else "sources_saved_pair_not_ready"),
    }


def zip_bytes(report=None, original_files=None, *, duplicate=False):
    report = make_report() if report is None else report
    files = sources() if original_files is None else original_files
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("official_joint_evidence/batch_report.json",
                   json.dumps(report))
        for name, raw in files.items():
            z.writestr(name, raw)
        if duplicate:
            # Duplicate ZIP entry bypasses a naive dict(zip.namelist()).
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                z.writestr("official_joint_evidence/batch_report.json",
                           json.dumps(report))
    data = buffer.getvalue()
    return data, hashlib.sha256(data).hexdigest()


class ActualScheduledPairZipReplayTests(unittest.TestCase):
    def test_complete_two_originals_never_promoted_to_formal(self):
        raw, digest = zip_bytes()
        a = replay(raw, RUN, digest, auditor=lambda a, b: audited())
        self.assertEqual(a["two_original_complete_race_count"], 1)
        self.assertEqual(a["official_racelist_originals_verified"], 0)
        self.assertTrue(a["race_rows"][0]["official_odds_120_verified"])
        for key in ("formal", "t12_eligible",
                    "accuracy_scoring_allowed", "full_t12_source_certified",
                    "model_original_input_consumption_verified",
                    "independent_first_git_remote_receipt_verified"):
            self.assertIs(a[key], False)

    def test_green_no_candidate_run_counts_as_zero(self):
        raw, digest = zip_bytes(make_report(pair=False), {})
        a = replay(raw, RUN, digest, auditor=lambda x, y: self.fail("no source"))
        self.assertEqual(a["status"], "no_pre_t12_candidate")
        self.assertEqual(a["candidate_count"], 0)
        self.assertEqual(a["two_original_complete_race_count"], 0)
        self.assertFalse(a["formal"])

    def test_incomplete_pair_stays_incomplete(self):
        raw, digest = zip_bytes(make_report(complete=False))
        a = replay(raw, RUN, digest,
                   auditor=lambda x, y: audited(complete=False))
        self.assertFalse(a["race_rows"][0]["two_originals_complete_by_t12"])
        self.assertEqual(a["two_original_complete_race_count"], 0)

    def test_beforeinfo_only_does_not_mask_missing_odds(self):
        files = sources()
        files = {k: v for k, v in files.items() if "odds_run" not in k}
        raw, digest = zip_bytes(make_report(no_odds=True), files)
        a = replay(raw, RUN, digest, auditor=lambda x, y: self.fail("no odds"))
        self.assertEqual(a["original_beforeinfo_count"], 1)
        self.assertEqual(a["original_odds_count"], 0)
        self.assertEqual(a["two_original_complete_race_count"], 0)

    def test_bad_zip_sha_is_rejected(self):
        raw, digest = zip_bytes()
        with self.assertRaisesRegex(ValueError, "digest"):
            replay(raw, RUN, "a"*64, auditor=lambda x, y: audited())
        with self.assertRaisesRegex(ValueError, "identity"):
            replay(raw, 0, digest, auditor=lambda x, y: audited())

    def test_missing_or_mutated_source_manifest_is_not_success(self):
        files = sources()
        name = next(k for k in files if k.endswith("beforeinfo.json"))
        files[name] += b" "
        raw, digest = zip_bytes(original_files=files)
        with self.assertRaisesRegex(ValueError, "SHA/length"):
            replay(raw, RUN, digest, auditor=lambda x, y: audited())
        files = sources()
        name = next(k for k in files if k.endswith("manifest.json"))
        files.pop(name)
        raw, digest = zip_bytes(original_files=files)
        with self.assertRaisesRegex(ValueError, "partial"):
            replay(raw, RUN, digest, auditor=lambda x, y: audited())

    def test_report_false_success_rejected_after_independent_replay(self):
        raw, digest = zip_bytes()
        with self.assertRaisesRegex(ValueError, "disagrees"):
            replay(raw, RUN, digest,
                   auditor=lambda x, y: audited(complete=False))

    def test_true_pair_but_reported_incomplete_is_not_accepted(self):
        raw, digest = zip_bytes(make_report(complete=False))
        with self.assertRaisesRegex(ValueError, "disagrees"):
            replay(raw, RUN, digest, auditor=lambda x, y: audited())

    def test_403_404_timeout_success_metadata_is_never_reported_as_valid(self):
        for label in ("HTTPError:403", "HTTPError:404", "TimeoutError"):
            with self.subTest(label=label):
                report = make_report(no_odds=True)
                report["observations"][0]["error_type"] = label
                files = {k: v for k, v in sources().items()
                         if "odds_run" not in k}
                raw, digest = zip_bytes(report, files)
                a = replay(raw, RUN, digest,
                           auditor=lambda x, y: self.fail("unexpected"))
                self.assertEqual(a["two_original_complete_race_count"], 0)
                self.assertFalse(a["formal"])

    def test_mutated_report_counters_are_rejected(self):
        for key in ("eligible_candidates", "beforeinfo_originals_saved",
                    "official_odds_originals_saved", "complete_pairs_before_t12"):
            report = make_report()
            report[key] += 1
            raw, digest = zip_bytes(report)
            with self.subTest(key=key), self.assertRaises(ValueError):
                replay(raw, RUN, digest, auditor=lambda x, y: audited())

    def test_duplicate_zip_entries_rejected(self):
        raw, digest = zip_bytes(duplicate=True)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            replay(raw, RUN, digest, auditor=lambda x, y: audited())

    def test_report_cannot_claim_formal_certificate(self):
        for field in ("formal", "forecast_usable", "full_t12_source_certified"):
            report = make_report()
            report[field] = True
            raw, digest = zip_bytes(report)
            with self.subTest(field=field), self.assertRaises(ValueError):
                replay(raw, RUN, digest, auditor=lambda x, y: audited())

    def test_foreign_race_day_or_bad_receipt_rejected(self):
        files = sources()
        manifest_key = next(k for k in files if "/before_run" in k
                            and k.endswith("manifest.json"))
        m = json.loads(files[manifest_key])
        m["received_at_jst"] = "2026-11-09T14:15:38+09:00"
        files[manifest_key] = json.dumps(m).encode()
        raw, digest = zip_bytes(original_files=files)
        with self.assertRaisesRegex(ValueError, "receipt"):
            replay(raw, RUN, digest, auditor=lambda x, y: audited())

    def test_reported_pair_requires_original_odds(self):
        files = {k: v for k, v in sources().items()
                 if "odds_run" not in k}
        raw, digest = zip_bytes(original_files=files)
        with self.assertRaisesRegex(ValueError, "claimed pair"):
            replay(raw, RUN, digest, auditor=lambda x, y: audited())


if __name__ == "__main__":
    unittest.main()
