"""Boundary checks: non-first receipt, incomplete server observation, missing source."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import hole_nov05_frozen_observation_audit as m

def fake_records():
    original=m.EXPECTED_FROZEN
    a=[];b=[]
    for i in range(original):
        code=f"20261105{(i//12)+1:02d}{(i%12)+1:02d}"
        a.append({"race_code":code,"status":"shadow_frozen_unverified",
                  "independent_first_receipt_verified":False,
                  "source_sha256":"abcdef",
                  "t_minus_12_jst":"2026-11-05T17:00:00+09:00",
                  "local_freeze_at_jst":"2026-11-05T11:15:40+09:00"})
        b.append({"race_code":code,"status":"github_server_observed_before_t_minus_12",
                  "first_add_blob_matches_remote":True,
                  "first_add_commit":m.PUBLICATION_SHA,
                  "original_sha256":"abcdef",
                  "github_api_server_date_utc":"2026-11-05T02:15:17+00:00"})
    shadow={"status":"research_only_after_confirmed_push",
            "schema":"HOLE_SHADOW_PUBLISHED_SAME_JOB_V1",
            "publication_commit_sha":m.PUBLICATION_SHA,"formal":False,
            "independent_first_receipt_verified":False,"frozen_count":original,
            "validation_error_count":0,"records":a}
    observed={"status":"remote_observation_audited_nonformal",
              "github_server_observation_not_first_receipt":True,
              "independent_first_remote_receipt_verified":False,
              "publication_commit_sha":m.PUBLICATION_SHA,
              "publication_count":original,
              "observed_before_t_minus_12":original,
              "observed_after_t_minus_12":0,
              "unverified_count":0,"records":b}
    return shadow,observed

class EvidenceGateTest(unittest.TestCase):
    def test_valid_gated_sets_reject_missing_original_file(self):
        shadow,obs=fake_records()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"published_source_bytes_differ"):
                m.validate_early_server_observation(shadow,obs,d)
    def test_missing_observation_fails_before_file_access(self):
        shadow,obs=fake_records()
        obs["records"].pop()
        with self.assertRaisesRegex(ValueError,"evidence_count_mismatch"):
            m.validate_early_server_observation(shadow,obs,".")
    def test_false_formal_proof_is_rejected(self):
        shadow,obs=fake_records()
        obs["independent_first_remote_receipt_verified"]=True
        with self.assertRaisesRegex(ValueError,"shadow_or_observation_contract_mismatch"):
            m.validate_early_server_observation(shadow,obs,".")
    def test_late_server_observation_rejected(self):
        shadow,obs=fake_records()
        obs["records"][0]["github_api_server_date_utc"]="2026-11-05T09:00:00+00:00"
        with self.assertRaisesRegex(ValueError,"not_observed_and_frozen_before_t_minus_12"):
            m.validate_early_server_observation(shadow,obs,".")

if __name__=="__main__":
    unittest.main()
