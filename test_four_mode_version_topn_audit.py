"""Regression tests for version-scoped historical research only."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from four_mode_version_topn_audit import analyze


class VersionTopNTests(unittest.TestCase):
    def test_versions_and_days_never_pool(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "four_mode_forecasts"
            folder.mkdir()
            codes = ["202610280101", "202611020101", "202611020102"]
            versions = ["CLEAN_FOUR_MODES_V1_UNCALIBRATED",
                        "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
                        "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"]
            for code, version in zip(codes, versions):
                (folder / (code + ".json")).write_text(
                    json.dumps({"model_version": version}), encoding="utf-8")
            def compare(code, root):
                hit = code != codes[2]
                return {"status": "historical_comparison_only",
                        "modes": {m: {"top3": hit, "top5": hit, "top10": hit}
                                  for m in ("narrow", "hit", "balance", "hole")}}
            with patch("four_mode_version_topn_audit.run",
                       return_value={"status": "historical_research_only",
                                     "cohort_codes": codes, "requested": 3}), \
                 patch("four_mode_version_topn_audit.compare_race",
                       side_effect=compare):
                result = analyze(root, limit=3)
            self.assertFalse(result["formal"])
            self.assertFalse(result["independent_predeadline_proof"])
            self.assertEqual(result["evaluated"], 3)
            self.assertEqual(result["groups"][versions[0]]["20261028"]["evaluated"], 1)
            self.assertEqual(result["groups"][versions[1]]["20261102"]["evaluated"], 2)
            self.assertEqual(result["groups"][versions[1]]["20261102"]["topn_hits"]["hit"]["top3"], 1)


if __name__ == "__main__":
    unittest.main()
