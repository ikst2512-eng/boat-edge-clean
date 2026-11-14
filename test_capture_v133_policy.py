"""No results, post-deadline backfill, false first-remote claims, or altered archives."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from capture_v133_policy import (
    MODEL, POLICY, SCHEMA, candidates, collect, verify_snapshot,
)
from legacy_scenario_engine import JST
from test_legacy_scenario_engine import current_card

NOW = datetime(2026, 11, 12, 11, 50, tzinfo=JST)
CODE = "202611120501"


class NewV133ProspectiveTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "schedule_snapshots").mkdir()
        (self.root / "schedule_snapshots" / "20261112.json").write_text(
            json.dumps({"date": "2026-11-12", "venues": [{"jcd": "05", "races": [
                {"race_no": 1, "deadline": "12:00"},
                {"race_no": 2, "deadline": "11:40"},
                {"race_no": 3, "deadline": "15:00"},
            ]}]}), encoding="utf-8")
        (self.root / "four_mode_forecasts").mkdir()
        old = self.root / "four_mode_forecasts" / (CODE + ".json")
        old.write_bytes(b'{"protected":"V2 baseline"}\n')
        self.old = old
        self.original = old.read_bytes()

    def capture_once(self):
        called = []
        def load(hd, jcd, rno):
            called.append((hd,jcd,rno))
            return current_card()
        status = collect(self.root, now=NOW, card_loader=load)
        self.assertEqual(called, [("20261112", "05", "1")])
        self.assertEqual(status["saved"], [CODE])
        return self.root / "v133_policy_forecasts" / (CODE + ".json")

    def test_write_once_new_policy_and_protected_v2(self):
        target = self.capture_once()
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(verify_snapshot(target, now=NOW), CODE)
        self.assertEqual(data["schema"], SCHEMA)
        self.assertEqual(data["model_version"], MODEL)
        self.assertEqual(data["selection_policy"], POLICY)
        self.assertEqual({k: len(v["tickets"]) for k,v in data["modes"].items()
                          if k not in ("hole", "tail")},
                         {"narrow": 3, "hit": 10, "balance": 12})
        self.assertIn(len(data["modes"]["hole"]["tickets"]), (15,18,20))
        self.assertFalse(data["formal"])
        self.assertFalse(data["calibrated"])
        self.assertFalse(data["production_buy_approved"])
        self.assertFalse(data["accuracy_improvement_proven"])
        self.assertFalse(data["first_remote_add_verified"])
        self.assertFalse(data["historical_predictions_reconstructed"])
        self.assertEqual(self.old.read_bytes(), self.original)
        saved = target.read_bytes()
        next_try = collect(self.root, now=NOW, card_loader=lambda *args: self.fail("called"))
        self.assertEqual(next_try["saved"], [])
        self.assertEqual(target.read_bytes(), saved)

    def test_no_closed_or_fabricated_races(self):
        past = datetime(2026, 11, 12, 12, 2, tzinfo=JST)
        self.assertEqual(candidates(self.root, past), [])
        self.assertEqual(collect(self.root, past, lambda *args: self.fail("called"))["saved"], [])
        self.assertEqual(collect(self.root, datetime(2026,11,11,11,50,tzinfo=JST),
                                 lambda *args: self.fail("called"))["saved"], [])

    def test_missing_exhibition_never_writes(self):
        data = current_card(with_before=False)
        result = collect(self.root, NOW, lambda *args: data)
        self.assertEqual(result["saved"], [])
        self.assertFalse((self.root/"v133_policy_forecasts"/(CODE+".json")).exists())
        self.assertIn("verified_six_exhibition_required", result["rejected"])

    def test_wrong_race_card_or_result_guard_rejects(self):
        data = current_card()
        data["race_key"] = "20261112-05-02"
        result = collect(self.root,NOW,lambda *args:data)
        self.assertEqual(result["saved"], [])
        self.assertIn("v133_wrong_race_card", result["rejected"])
        data = current_card()
        data["meta"]["results_seen"] = True
        result = collect(self.root,NOW,lambda *args:data)
        self.assertEqual(result["saved"], [])
        self.assertFalse((self.root/"v133_policy_forecasts"/(CODE+".json")).exists())

    def test_bad_receipt_or_changed_mode_fails_verify(self):
        target = self.capture_once()
        original = json.loads(target.read_text(encoding="utf-8"))
        for changed, failure in [
            ({"first_remote_add_verified": True}, "invalid_v133_research_identity"),
            ({"calibrated": True}, "invalid_v133_research_identity"),
            ({"selection_policy": "WRONG"}, "invalid_v133_research_identity"),
            ({"source_racecard_sha256": "0"*64}, "v133_racecard_sha_mismatch"),
        ]:
            record = dict(original, **changed)
            target.write_text(json.dumps(record), encoding="utf-8")
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, failure):
                verify_snapshot(target, NOW)
        original["modes"]["balance"]["tickets"].pop()
        target.write_text(json.dumps(original), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "v133_wrong_ticket_count_balance"):
            verify_snapshot(target, NOW)

    def test_cutoff_checks_after_local_capture(self):
        target = self.capture_once()
        with self.assertRaisesRegex(ValueError, "v133_publication_window_closed"):
            verify_snapshot(target, now=datetime(2026,11,12,11,59,tzinfo=JST))


if __name__ == "__main__":
    unittest.main()
