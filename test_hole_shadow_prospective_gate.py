import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from hole_shadow_prospective_gate import freeze, evaluate, JST


class ProspectiveGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "four_mode_forecasts").mkdir()
        self.code = "202611030101"
        self.bytes = b'{"immutable":"example"}'
        (self.root / "four_mode_forecasts" / (self.code + ".json")).write_bytes(self.bytes)
        self.cutoff = datetime(2026, 11, 3, 15, 0, tzinfo=JST)
        self.archive = {"deadline_jst": self.cutoff.isoformat(),
                        "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
                        "modes": {name: {"tickets": [{"combo": t} for t in picks]} for name, picks in {
                            "hole": ["1-2-3", "1-2-4", "1-3-2", "2-3-1", "2-3-4",
                                     "3-4-1", "3-4-2", "1-2-5", "2-3-5", "3-4-5"],
                            "hit": ["1-4-2"],
                            "balance": ["1-4-2"]
                        }.items()}}

    def test_result_blind_freeze_and_hash(self):
        with patch("hole_shadow_prospective_gate.archived_four_modes", return_value=(200, self.archive)):
            output = freeze(self.code, self.root, self.cutoff - timedelta(minutes=15))
        self.assertEqual(output["status"], "shadow_frozen_unverified")
        self.assertFalse(output["prospective_verified"])
        self.assertEqual(output["shadow"][2], "1-4-2")
        self.assertEqual(output["source_sha256"], hashlib.sha256(self.bytes).hexdigest())
        self.assertEqual(len(output["baseline"]), len(output["shadow"]))

    def test_bundle_shadow_is_result_blind_and_budget_preserving(self):
        archive = json.loads(json.dumps(self.archive))
        archive["modes"]["hit"]["tickets"] = [
            {"combo":"1-4-2"}, {"combo":"1-4-3"}]
        with patch("hole_shadow_prospective_gate.archived_four_modes", return_value=(200, archive)):
            output = freeze(self.code, self.root, self.cutoff - timedelta(minutes=15))
        self.assertEqual(output["shadow_bundle2"][2:4], ["1-4-2", "1-4-3"])
        self.assertEqual(len(output["shadow_bundle2"]), len(output["baseline"]))
        self.assertEqual(len(set(output["shadow_bundle2"])), len(output["baseline"]))
        self.assertFalse(output["independent_first_receipt_verified"])
        self.assertFalse(output["production_forecast"])

    def test_deadline_is_strict(self):
        with patch("hole_shadow_prospective_gate.archived_four_modes", return_value=(200, self.archive)):
            self.assertEqual(freeze(self.code, self.root, self.cutoff)["status"], "past_deadline")
            self.assertEqual(freeze(self.code, self.root, self.cutoff + timedelta(seconds=1))["status"], "past_deadline")

    def test_missing_archive(self):
        with patch("hole_shadow_prospective_gate.archived_four_modes", return_value=(404, {})):
            self.assertEqual(freeze(self.code, self.root)["status"], "archive_unavailable")

    def test_self_asserted_independent_proof_not_accepted(self):
        frozen = {"status": "shadow_frozen_unverified"}
        self.assertFalse(evaluate(frozen, {}, {"verified_by_independent_process": True})["formal"])
        self.assertEqual(evaluate(frozen, {}, {})["status"], "awaiting_independent_receipt_proof")


if __name__ == "__main__":
    unittest.main()
