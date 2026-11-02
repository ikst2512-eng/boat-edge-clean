import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from four_mode_paired_all_version_topn import paired_audit

class PairedAuditTests(unittest.TestCase):
    def test_same_race_only_and_version_separation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "four_mode_forecasts"
            folder.mkdir()
            codes = ["202610280101", "202610280102", "202611020101"]
            versions = ["CLEAN_FOUR_MODES_V1_UNCALIBRATED"]*2 + ["CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"]
            for code, v in zip(codes, versions):
                (folder / (code + ".json")).write_text(json.dumps({"race_code": code, "model_version": v}))
            def compare(code, root):
                left = code != codes[1]
                right = code != codes[0]
                return {"status": "historical_comparison_only",
                        "modes": {m: {f"top{n}": (left if m in ("hit", "narrow") else right)
                                     for n in (3,5,10)}
                                  for m in ("hit", "balance", "narrow", "hole")}}
            with patch("four_mode_paired_all_version_topn.compare_race", side_effect=compare):
                result = paired_audit(root)
            first = result["groups"][versions[0]]["20261028"]["paired"]["hit_vs_balance"]["top3"]
            self.assertEqual((first["left_only"], first["right_only"], first["both"]), (1,1,0))
            self.assertEqual(result["groups"][versions[2]]["20261102"]["evaluated"],1)
            self.assertFalse(result["formal"])

if __name__ == "__main__":
    unittest.main()
