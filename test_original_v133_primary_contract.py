"""Contract: prefer genuine frozen legacy V127/V133 records; preserve both comparators."""
import unittest
from pathlib import Path

INDEX = Path(__file__).with_name("index.html")


class OriginalReferencePriorityTests(unittest.TestCase):
    def test_original_frozen_reference_is_checked_before_heuristic(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn("async function loadOriginalV133Frozen(", html)
        self.assertIn("if(await loadOriginalV133Frozen(key,token,status,root))return;", html)
        self.assertIn("boat-edge/main/data/site_prediction_snapshots/", html)
        self.assertIn("data.snapshot_window==='FINAL_15M'", html)
        self.assertIn("data.guards?.results_seen===false", html)
        self.assertIn("first<=saved&&saved<cutoff", html)
        self.assertIn("data.prediction_kind==='SITE_REFERENCE_V122'", html)
        self.assertIn("data.selection_policy==='V122_SCENARIO_AWARE_PROBABILITY_FIRST'", html)

    def test_original_modes_are_not_replaced_with_v2_ticket_counts(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn("const counts={narrow:3,hit:10,balance:10};", html)
        self.assertIn("[12,15,18].some(n=>validRows(modes.hole?.tickets,n))", html)
        self.assertIn("BALANCE10_WAVE12_15_18_V133_FIXED", html)
        self.assertIn("PROVISIONAL_V254_THIRD_TAIL10_FIXED_TOP7", html)
        self.assertIn("統計的優位は未証明", html)
        self.assertIn('id="v2Comparator"', html)
        self.assertIn("loadFourModeArchives(raceKey,token)", html)
        self.assertIn("後付け生成はしません", html)

    def test_model_provenance_is_labeled_as_reference_not_formal(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn("初回Git保存の独立受領・正式的中率は未認定", html)
        self.assertIn("元のV127/V133予想を優先表示中", html)
        self.assertIn("旧V127/V133の保存原本が不正です", html)
        self.assertIn("旧V127/V133の保存原本・時刻・モードを検証できません", html)


if __name__ == "__main__":
    unittest.main()
