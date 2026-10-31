"""Guard selective Top10 study against late and invalid archived races."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.research_selective_top10_backtest import study
from research_model import probabilities


class SelectiveStudyPredeadlineTest(unittest.TestCase):
    def test_late_and_invalid_archives_do_not_enter_holdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "research_snapshots").mkdir()
            (root / "confirmed_results").mkdir()
            rates = [60, 50, 40, 30, 20, 10]
            tickets = ["-".join(map(str, t)) for t, _ in probabilities(rates)[:10]]
            items = [
                ("202610300101", "2026-10-30T10:00:00+09:00", [1, 2, 3]),
                ("202610300102", "2026-10-30T10:35:00+09:00", [1, 2, 3]),
                ("202610300103", "2026-10-30T10:00:00", [1, 2, 3]),
                ("202610300104", "2026-10-30T10:00:00+09:00", [1, 1, 2]),
            ]
            for code, generated, finish in items:
                forecast = {
                    "race_code": code, "status": "research",
                    "generated_at": generated, "cutoff_jst": "2026-10-30T10:30:00+09:00",
                    "source_deadline_jst": "2026-10-30T10:42:00+09:00",
                    "national_win_rates": rates, "predictions": tickets,
                }
                result = {"race_code": code, "status": "confirmed", "finish_order": finish}
                (root / "research_snapshots" / (code + ".json")).write_text(json.dumps(forecast))
                (root / "confirmed_results" / (code + ".json")).write_text(json.dumps(result))
            output = study(root)
            self.assertEqual(output["holdout_n"], 1)
            self.assertEqual(output["rejected"], 3)


if __name__ == "__main__":
    unittest.main()
