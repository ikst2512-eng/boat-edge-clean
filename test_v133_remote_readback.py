"""Research-only GitHub server observation is never an initial receipt claim."""
import base64
import hashlib
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from capture_v133_policy import collect
from legacy_scenario_engine import JST
from test_legacy_scenario_engine import current_card
from v133_remote_readback import observe

CODE = "202611120501"
FILE = "v133_policy_forecasts/" + CODE + ".json"
SHA = "a" * 40
REPO = "ikst2512-eng/boat-edge-clean"
NOW = datetime(2026, 11, 12, 11, 44, tzinfo=JST)


class GitHubServerReadbackTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        schedule = self.root / "schedule_snapshots"
        schedule.mkdir()
        (schedule / "20261112.json").write_text(json.dumps({
            "date": "2026-11-12", "venues": [{"jcd": "05", "races": [
                {"race_no": 1, "deadline": "12:00"}
            ]}]
        }), encoding="utf-8")
        report = collect(self.root, now=NOW, card_loader=lambda *a: current_card())
        self.assertEqual(report["saved"], [CODE])
        self.raw = (self.root / FILE).read_bytes()
        self.sha = hashlib.sha1(b"blob " + str(len(self.raw)).encode() + b"\0" + self.raw).hexdigest()

    def git(self, *args):
        if args[0] == "diff-tree":
            return (FILE + "\n").encode()
        if args[0] == "show" and args[1] == SHA + ":" + FILE:
            return self.raw
        raise AssertionError(args)

    def response(self, date="Thu, 12 Nov 2026 02:45:00 GMT", edit=None):
        d = {"path": FILE, "type": "file", "encoding": "base64",
             "sha": self.sha, "content": base64.b64encode(self.raw).decode()}
        if edit:
            d.update(edit)
        return lambda path: (date, json.dumps(d).encode())

    def test_pre_tminus12_exact_remote_readback_is_nonformal(self):
        r = observe(self.root, SHA, REPO, self.response(), self.git)
        self.assertEqual(r["early_tminus12_observed"], 1)
        self.assertEqual(r["late_or_unverified"], 0)
        self.assertTrue(r["records"][0]["remote_exact_blob_match"])
        self.assertFalse(r["independent_first_remote_receipt_verified"])
        self.assertTrue(r["github_date_is_observation_not_first_receipt"])
        self.assertFalse(r["formal"])

    def test_between_tminus12_and_deadline_does_not_claim_tminus12(self):
        r = observe(self.root, SHA, REPO,
                    self.response("Thu, 12 Nov 2026 02:52:00 GMT"), self.git)
        self.assertEqual(r["early_tminus12_observed"], 0)
        self.assertEqual(r["after_tminus12_but_predeadline_observed"], 1)
        self.assertFalse(r["independent_first_remote_receipt_verified"])

    def test_late_or_forged_remote_data_rejected(self):
        for request in [
            self.response("Thu, 12 Nov 2026 03:00:00 GMT"),
            self.response(edit={"sha": "0" * 40}),
            self.response(edit={"path": "four_mode_forecasts/" + CODE + ".json"}),
            self.response(edit={"content": base64.b64encode(b"altered").decode()}),
            lambda p: (None, b"{}"),
        ]:
            with self.subTest(request=request):
                r = observe(self.root, SHA, REPO, request, self.git)
                self.assertEqual(r["early_tminus12_observed"], 0)
                self.assertEqual(r["late_or_unverified"], 1)
                self.assertFalse(r["records"][0].get("remote_exact_blob_match", False))

    def test_local_byte_mutation_and_unexpected_roster_fail_closed(self):
        p = self.root / FILE
        p.write_bytes(self.raw + b"\n")
        r = observe(self.root, SHA, REPO, self.response(), self.git)
        self.assertEqual(r["late_or_unverified"], 1)
        self.assertIn("changed", r["records"][0]["reason"])
        with self.assertRaisesRegex(ValueError, "invalid_v133_first_add_roster"):
            observe(self.root, SHA, REPO, lambda p: self.fail("request"),
                    lambda *args: b"bad-path.json\n")

    def test_no_new_receipts_has_explicit_empty_status(self):
        r = observe(self.root, SHA, REPO, request=lambda p: self.fail("request"),
                    git=lambda *args: b"")
        self.assertEqual(r["status"], "no_new_v133_forecasts")
        self.assertEqual(r["first_added_count"], 0)
        self.assertFalse(r["independent_first_remote_receipt_verified"])


if __name__ == "__main__":
    unittest.main()
