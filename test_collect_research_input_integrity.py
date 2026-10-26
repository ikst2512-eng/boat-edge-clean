"""Input integrity tests for the daily research-only collector (no network)."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import collect_research_daily as collector
from research_model import JST


class InputIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name)
        self.day = (datetime.now(JST) + timedelta(days=2)).strftime("%Y%m%d")
        self.code = self.day + "1201"
        self.title = {"レースコード": self.code, "電話投票締切予定": "23:59"}
        self.card = {"レースコード": self.code, **{f"艇{i}_全国勝率": "6.0" for i in range(1, 7)}}
        self.received = datetime.strptime(self.day + "23:59", "%Y%m%d%H:%M").replace(tzinfo=JST) - timedelta(hours=3)

    def collect_rows(self, titles=None, cards=None):
        with patch.object(collector, "model_provenance",return_value={"model_git_sha":"a"*40,"model_source_sha256":"b"*64}), patch.object(collector, "STORE", self.store), patch("research_model.STORE", self.store), patch.object(
            collector, "read_rows", side_effect=[(titles if titles is not None else [self.title], self.received, "a"*64), (cards if cards is not None else [self.card], self.received,"b"*64)]
        ):
            return collector.collect(self.day)

    def assert_rejected(self, titles=None, cards=None):
        result = self.collect_rows(titles, cards)
        self.assertEqual(result["saved"], 0)
        self.assertEqual(result["invalid"], 1)
        self.assertEqual(list(self.store.glob("*.json")), [])

    def test_valid_data_saved(self):
        self.assertEqual(self.collect_rows()["saved"], 1)
        stored = list(self.store.glob("*.json"))
        self.assertEqual(len(stored), 1)
        self.assertFalse(json.loads(stored[0].read_text())["validated"])

    def test_nonfinite_and_out_of_range(self):
        for value in ["NaN", "Infinity", "-Infinity", "-1", "11", ""]:
            with self.subTest(value=value):
                altered = dict(self.card, 艇1_全国勝率=value)
                self.assert_rejected(cards=[altered])

    def test_duplicate_cards(self):
        self.assert_rejected(cards=[self.card, dict(self.card)])

    def test_duplicate_titles(self):
        self.assert_rejected(titles=[self.title, dict(self.title)])

    def test_missing_rate(self):
        card = dict(self.card)
        del card["艇6_全国勝率"]
        self.assert_rejected(cards=[card])

    def test_non_dict_row_is_safe(self):
        self.assertEqual(self.collect_rows(titles=[None, self.title], cards=[None, self.card])["saved"], 1)


if __name__ == "__main__":
    unittest.main()
