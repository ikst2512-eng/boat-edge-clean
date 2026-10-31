"""Exercise the daily collector's actual new-file write, not only source inspection."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import collect_research_daily as daily
from research_model import JST


class DailyResearchWriteContract(unittest.TestCase):
    def test_new_snapshot_has_raw_topn_mass_and_never_overwrites(self):
        now = datetime.now(JST)
        day = now.strftime("%Y%m%d")
        code = day + "2401"
        deadline = (now + timedelta(hours=5)).strftime("%H:%M")
        titles = [{"レースコード": code, "電話投票締切予定": deadline}]
        card = {"レースコード": code}
        card.update({f"艇{i}_全国勝率": str(4 + i / 10) for i in range(1, 7)})
        with tempfile.TemporaryDirectory() as folder:
            store = Path(folder)
            def path_for(race_code):
                return store / (race_code + ".json")
            with patch.object(daily, "read_rows", side_effect=[
                (titles, now, "a" * 64), ([card], now, "b" * 64),
                (titles, now, "a" * 64), ([card], now, "b" * 64),
            ]), patch.object(daily, "STORE", store), patch.object(daily, "_record_path", side_effect=path_for), patch.object(daily, "_saved", side_effect=lambda c: json.loads(path_for(c).read_text()) if path_for(c).exists() else None), patch.object(daily, "model_provenance", return_value={"model_git_sha": "a" * 40}):
                result = daily.collect(day)
                self.assertEqual(result["saved"], 1)
                target = path_for(code)
                original = target.read_bytes()
                record = json.loads(original)
                self.assertEqual(sorted(record["topn_model_mass_pct"]), ["10", "3", "5"])
                self.assertFalse(record["confidence_calibrated"])
                self.assertTrue(0 < record["topn_model_mass_pct"]["3"] < record["topn_model_mass_pct"]["5"] < record["topn_model_mass_pct"]["10"] < 100)
                again = daily.collect(day)
                self.assertEqual(again["already_saved"], 1)
                self.assertEqual(target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
