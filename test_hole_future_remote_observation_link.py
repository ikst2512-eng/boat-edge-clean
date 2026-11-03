import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from hole_future_remote_observation_link import match

CODE="202611040101"
SHA="a"*40
CONTENT=json.dumps({
    "race_code":CODE,"deadline_jst":"2026-11-04T12:00:00+09:00"}).encode()
DIGEST=hashlib.sha256(CONTENT).hexdigest()


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.forecasts=self.root/"four_mode_forecasts"
        self.forecasts.mkdir()
        (self.forecasts/(CODE+".json")).write_bytes(CONTENT)
        self.ledger=self.root/"ledger"
        self.location=self.ledger/"github_server"/"20261104"/"run-123-attempt-1.json"
        self.location.parent.mkdir(parents=True)
        self.future={"formal":False,
                     "independent_first_receipt_verified":False,
                     "race_codes":[CODE]}
        self.local={"formal":False,
                    "independent_remote_first_receipt_verified":False,
                    "records":[{"race_code":CODE,
                                "status":"local_git_first_add_clock_before_t12_unverified",
                                "first_add_commit":SHA,"source_sha256":DIGEST}]}
        self.row={"race_code":CODE,"status":"github_server_observed_before_t_minus_12",
                  "first_add_commit":SHA,
                  "first_add_blob_matches_remote":True,
                  "original_sha256":DIGEST,
                  "github_api_server_date_utc":"2026-11-04T02:40:00+00:00",
                  "deadline_minus_12_jst":"2026-11-04T11:48:00+09:00"}
    def save(self):
        self.location.write_text(json.dumps({
            "schema":"FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1",
            "formal":False,"independent_first_remote_receipt_verified":False,
            "github_server_observation_not_first_receipt":True,
            "publication_count":1,"publication_commit_sha":SHA,
            "records":[self.row]}))
    def evaluate(self):
        return match(self.future,self.local,self.ledger,self.root)

    def test_exact_early_remote_observation_is_only_nonformal(self):
        self.save()
        output=self.evaluate()
        self.assertEqual(output["remote_observed_before_t12_count"],1)
        self.assertEqual(output["race_status"][CODE],"observed_before_t12")
        self.assertFalse(output["formal"])
        self.assertFalse(output["independent_first_remote_receipt_verified"])

    def test_no_record_is_not_zero_early_as_proof(self):
        self.assertEqual(self.evaluate()["race_status"][CODE],"missing_observation")
        self.assertEqual(self.evaluate()["remote_observed_before_t12_count"],0)

    def test_observation_at_cutoff_is_late(self):
        self.row["github_api_server_date_utc"]="2026-11-04T02:48:00+00:00"
        self.row["status"]="github_server_observed_after_t_minus_12"
        self.save()
        self.assertEqual(self.evaluate()["race_status"][CODE],"observed_after_t12")

    def test_mismatched_commit_or_bytes_cannot_pass(self):
        self.row["first_add_commit"]="b"*40
        self.save()
        self.assertEqual(self.evaluate()["race_status"][CODE],"conflicting_observations")
        self.row["first_add_commit"]=SHA
        self.row["original_sha256"]="0"*64
        self.save()
        self.assertEqual(self.evaluate()["race_status"][CODE],"conflicting_observations")

    def test_false_early_timestamp_is_rejected(self):
        self.row["github_api_server_date_utc"]="2026-11-04T02:48:00+00:00"
        self.save()
        self.assertEqual(self.evaluate()["race_status"][CODE],"conflicting_observations")

    def test_first_add_unverified_cannot_use_server_date(self):
        self.local["records"][0]["status"]="git_history_unavailable"
        self.save()
        self.assertEqual(self.evaluate()["race_status"][CODE],
                         "local_git_first_add_unverified")

    def test_two_different_records_for_same_race_fail_closed(self):
        self.save()
        second=self.ledger/"github_server"/"20261104"/"run-234-attempt-1.json"
        clone=json.loads(self.location.read_text())
        clone["records"][0]["original_sha256"]="0"*64
        second.write_text(json.dumps(clone))
        self.assertEqual(self.evaluate()["race_status"][CODE],
                         "conflicting_observations")

    def test_prior_dates_not_allowed_in_new_cohort(self):
        self.future["race_codes"]=["202611030101"]
        with self.assertRaisesRegex(ValueError,"invalid_comparable_race_codes"):
            self.evaluate()

if __name__=="__main__":unittest.main()
