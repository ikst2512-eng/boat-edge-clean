"""Independent forward capture must be source-verified, immutable and predeadline."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from capture_restored_scenario import SCHEMA, collect
from legacy_scenario_engine import JST, MODEL_VERSION
from test_legacy_scenario_engine import current_card

NOW = datetime(2026, 11, 12, 11, 50, tzinfo=JST)
CODE = "202611120501"


class ScenarioForwardCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        folder = self.root / "four_mode_forecasts"
        folder.mkdir()
        (folder / (CODE + ".json")).write_text(json.dumps({
            "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
            "race_code": CODE,
            "deadline_jst": "2026-11-12T12:00:00+09:00",
            "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
        }), encoding="utf-8")
        self.original = (folder / (CODE + ".json")).read_bytes()

    def test_forward_source_eligible_creates_separate_immutable_four_modes(self):
        calls = []
        def load(hd, jcd, rno):
            calls.append((hd, jcd, rno))
            return current_card()
        result = collect(root=self.root, now=NOW, card_loader=load)
        self.assertEqual(result["new_saved"], [CODE])
        self.assertEqual(calls, [("20261112", "05", "1")])
        target = self.root / "scenario_forecasts" / (CODE + ".json")
        frozen = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(frozen["schema"], SCHEMA)
        self.assertEqual(frozen["model_version"], MODEL_VERSION)
        self.assertEqual(frozen["status"], "predeadline_frozen_scenario_research")
        self.assertEqual(frozen["source_racecard_sha256"], "a"*64)
        self.assertTrue(frozen["observed_exhibition_only"])
        self.assertEqual({k: len(v["tickets"]) for k,v in frozen["modes"].items()},
                         {"narrow": 5, "hit": 10, "balance": 16, "hole": 22})
        self.assertFalse(frozen["formal"])
        self.assertFalse(frozen["calibrated"])
        self.assertFalse(frozen["production_buy_approved"])
        self.assertFalse(frozen["first_remote_add_verified"])
        self.assertEqual(self.original, (self.root/"four_mode_forecasts"/(CODE+".json")).read_bytes())
        old = target.read_bytes()
        self.assertEqual(collect(root=self.root, now=NOW, card_loader=load)["new_saved"], [])
        self.assertEqual(target.read_bytes(), old)
        self.assertEqual(len(calls), 1)

    def test_historical_race_cannot_be_regenerated(self):
        after = datetime(2026, 11, 12, 12, 1, tzinfo=JST)
        self.assertEqual(collect(root=self.root, now=after, card_loader=lambda *args: self.fail("loaded"))["new_saved"], [])
        self.assertFalse((self.root/"scenario_forecasts").exists())

    def test_exhibition_missing_or_wrong_race_fails_closed(self):
        no_before = current_card(with_before=False)
        result = collect(root=self.root, now=NOW, card_loader=lambda *args: no_before)
        self.assertEqual(result["new_saved"], [])
        self.assertIn("verified_six_exhibition_required", result["excluded"])
        other = current_card()
        other["race_key"] = "20261112-05-02"
        result = collect(root=self.root, now=NOW, card_loader=lambda *args: other)
        self.assertEqual(result["new_saved"], [])
        self.assertIn("wrong_race_card_identity", result["excluded"])

    def test_past_only_or_non_jst_clock_rejected(self):
        with self.assertRaisesRegex(ValueError,"jst_clock_required"):
            collect(root=self.root, now=datetime(2026, 11, 12, 11, 50))
        early = datetime(2026, 11, 12, 7, 0, tzinfo=JST)
        self.assertEqual(collect(root=self.root, now=early, card_loader=lambda *args: self.fail("loaded"))["attempted"], 0)


if __name__ == "__main__":
    unittest.main()
