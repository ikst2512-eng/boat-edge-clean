"""Fail-closed tests for Nov 5 same-job research evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hole_nov05_original_shadow_replay as m

class Nov05OriginalShadowTest(unittest.TestCase):
    def test_server_forecast_observed_before_later_shadow_is_not_shadow_receipt(self):
        from datetime import datetime
        obs=datetime.fromisoformat("2026-11-05T02:15:17+00:00")
        cutoff=datetime.fromisoformat("2026-11-05T15:08:00+09:00")
        rec={"local_freeze_at_jst":"2026-11-05T11:15:42+09:00"}
        result=m.shadow_vs_source_clock(rec,obs,cutoff)
        self.assertTrue(result["source_observed_before_shadow_freeze"])
        self.assertEqual(result["source_observation_to_shadow_freeze_seconds"],25.0)
        rec["local_freeze_at_jst"]="2026-11-05T15:08:00+09:00"
        with self.assertRaisesRegex(ValueError,"shadow_local_freeze_not_before_t12"):
            m.shadow_vs_source_clock(rec,obs,cutoff)

    def test_empty_capture_fails_not_empty_success(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,"missing_or_unsafe_artifact"):
                m.inspect(".",t)

    def test_false_remote_early_claim_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);e=root/"four-mode-evidence";e.mkdir()
            shadow={"schema":"HOLE_SHADOW_PUBLISHED_SAME_JOB_V1",
                    "status":"research_only_after_confirmed_push","formal":False,
                    "independent_first_receipt_verified":False,"production_forecast_changed":False,
                    "frozen_count":1,"published_new_count":1,
                    "publication_commit_sha":m.EXPECTED_COMMIT,
                    "records":[{"race_code":"202611050101","status":"shadow_frozen_unverified"}]}
            remote={"schema":"FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1",
                    "status":"remote_observation_audited_nonformal",
                    "github_server_observation_not_first_receipt":True,
                    "formal":False,"independent_first_remote_receipt_verified":False,
                    "publication_commit_sha":m.EXPECTED_COMMIT,"publication_count":1,
                    "observed_before_t_minus_12":0,"observed_after_t_minus_12":1,
                    "unverified_count":0,
                    "records":[{"race_code":"202611050101"}]}
            publication={"outcome":"pushed_to_main","added_forecasts":1,"commit_sha":m.EXPECTED_COMMIT}
            for name,data in [("hole-shadow",shadow),
                              ("github-server-observation",remote),("publication",publication)]:
                (e/(name+".json")).write_text(json.dumps(data),encoding="utf-8")
            with patch.object(m,"EXPECTED_PUBLISHED",1):
                with self.assertRaisesRegex(ValueError,"remote_observation_not_early"):
                    m.inspect(".",root)

    def test_ledger_wont_accept_zero_or_formal_flag(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertRaises(ValueError,m.safe_json,Path(t)/"missing.json")
            path=Path(t)/"object.json"
            path.write_text("[]",encoding="utf-8")
            self.assertRaisesRegex(ValueError,"artifact_not_object",m.safe_json,path)

if __name__=="__main__":unittest.main()
