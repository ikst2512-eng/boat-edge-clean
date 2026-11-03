import base64
import hashlib
import json
import unittest
from unittest.mock import Mock

from scripts.reaudit_external_three_t12 import (
    inspect_stored_files, read_exact_commit_blob, reaudit_published,
)

RACE = "202611030104"
OBS = "saved001"
SHA = "a" * 40
PREFIX = f"external_three_t12/20261103/{RACE}/{OBS}"


def evidence(complete=False):
    checks = {"racelist_six_registrations": True,
              "exhibition_times_six": complete}
    result = {
        "race_code": RACE,
        "cutoff_jst": "2026-11-03T16:23:00+09:00",
        "racelist_received_jst": "2026-11-03T16:19:00+09:00",
        "beforeinfo_received_jst": "2026-11-03T16:18:50+09:00",
        "odds_received_jst": "2026-11-03T16:19:15+09:00",
        "latest_original_received_jst": "2026-11-03T16:19:15+09:00",
        "t12_receipt_margin_seconds": 225,
        "component_checks": checks,
        "missing_components": [] if complete else ["exhibition_times_six"],
        "all_research_components_observed_by_t12": complete,
    }
    report = {"race_code": RACE,
              "status": "research_components_complete_by_t12" if complete
                        else "research_components_incomplete",
              "audit": result, "full_t12_source_certified": False,
              "forecast_usable": False}
    files = {f"{PREFIX}/reports/three_originals.json": json.dumps(report).encode()}
    for part, name in (("card", "racelist.html"),
                       ("before", "beforeinfo.json"),
                       ("odds", "original.html")):
        files[f"{PREFIX}/{part}/{name}"] = ("original " + part).encode()
        files[f"{PREFIX}/{part}/manifest.json"] = b"{}"
    return files, result


class ExternalRemoteReauditTests(unittest.TestCase):
    def test_replayed_originals_complete_but_never_certified(self):
        files, source = evidence(complete=True)
        auditor = Mock(return_value=source)
        got = inspect_stored_files(files, RACE, OBS, auditor=auditor)
        self.assertEqual(got["status"], "independent_originals_reaudited")
        self.assertTrue(got["research_complete"])
        self.assertEqual(got["t12_receipt_margin_seconds"], 225)
        self.assertFalse(got["forecast_usable"])
        auditor.assert_called_once()

    def test_incomplete_evidence_keeps_fail_closed(self):
        files, source = evidence()
        got = inspect_stored_files(files, RACE, OBS, auditor=lambda *args: source)
        self.assertFalse(got["research_complete"])
        self.assertEqual(got["missing_components"], ["exhibition_times_six"])

    def test_false_complete_claim_rejected(self):
        files, source = evidence(complete=True)
        source["all_research_components_observed_by_t12"] = False
        with self.assertRaisesRegex(ValueError, "declared research completion"):
            inspect_stored_files(files, RACE, OBS, auditor=lambda *args: source)

    def test_missing_original_rejected(self):
        files, source = evidence()
        del files[f"{PREFIX}/odds/original.html"]
        with self.assertRaisesRegex(ValueError, "missing one or more"):
            inspect_stored_files(files, RACE, OBS, auditor=lambda *args: source)

    def test_exact_commit_github_sha_rechecked(self):
        raw = b"stored original"
        sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        def api(repo, token, method, endpoint):
            self.assertIn("?ref=" + SHA, endpoint)
            return {"type": "file", "encoding": "base64",
                    "content": base64.b64encode(raw).decode(), "sha": sha}
        got = read_exact_commit_blob("owner/repo", "token", SHA,
                                     f"{PREFIX}/card/racelist.html", api=api)
        self.assertEqual(got, raw)

    def test_mutated_git_sha_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "blob SHA mismatch"):
            read_exact_commit_blob("owner/repo", "token", SHA,
                f"{PREFIX}/card/racelist.html",
                api=lambda *args: {"type": "file", "encoding": "base64",
                    "content": base64.b64encode(b"original").decode(),
                    "sha": "f" * 40})

    def test_reaudit_never_uses_mutable_branch_ref(self):
        files, source = evidence()
        requested = []
        def reader(repo, token, commit, key):
            requested.append((commit, key))
            return files[key]
        result = reaudit_published("owner/repo", "token", SHA, RACE, OBS,
                                   reader=reader, auditor=lambda *args: source)
        self.assertEqual(result["evidence_commit"], SHA)
        self.assertEqual(len(requested), 7)
        self.assertTrue(all(commit == SHA for commit, key in requested))
        self.assertFalse(result["forecast_usable"])

    def test_preflight_report_cannot_become_complete(self):
        report = {"race_code": RACE, "status": "t12_preflight_expired",
                  "forecast_usable": False, "full_t12_source_certified": False}
        files = {f"{PREFIX}/reports/three_originals.json": json.dumps(report).encode()}
        got = inspect_stored_files(files, RACE, OBS, auditor=Mock())
        self.assertEqual(got["status"], "observation_not_ready")
        self.assertFalse(got["research_complete"])

if __name__ == "__main__":
    unittest.main()
