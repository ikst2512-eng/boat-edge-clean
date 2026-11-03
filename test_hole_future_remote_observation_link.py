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
                     "race_codes":[CODE],
                     "race_flags":{CODE:{p:{"top3":False,"top5":False,"top10":True}
                         for p in ("baseline","donor_order","max_ticket_score","third_national_rate")}},
                     "hits":{p:{"top3":0,"top5":0,"top10":1}
                         for p in ("baseline","donor_order","max_ticket_score","third_national_rate")}}
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
            "status":"remote_observation_audited_nonformal",
            "formal":False,"independent_first_remote_receipt_verified":False,
            "github_server_observation_not_first_receipt":True,
            "production_forecast_changed":False,
            "publication_count":1,"publication_commit_sha":SHA,
            "observed_before_t_minus_12":int(self.row["status"]=="github_server_observed_before_t_minus_12"),
            "observed_after_t_minus_12":int(self.row["status"]=="github_server_observed_after_t_minus_12"),
            "unverified_count":int(self.row["status"]=="remote_observation_unverified"),
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

    def test_pre_eligible_nov3_zero_cohort(self):
        self.future={"status":"not_yet_eligible","formal":False,"comparable":0,"race_flags":{}}
        result=self.evaluate()
        self.assertEqual(result["comparable"],0)
        self.assertEqual(result["remote_observed_before_t12_count"],0)
        self.assertEqual(result["race_status"],{})
        self.assertFalse(result["formal"])

    def test_evidence_strata_reconcile_all_policy_hits(self):
        self.save()
        data=self.evaluate()
        self.assertEqual(data["topn_by_evidence_status"]["observed_before_t12"]["races"],1)
        self.assertEqual(data["topn_by_evidence_status"]["observed_before_t12"]["hits"]
                         ["third_national_rate"]["top10"],1)
        self.location.unlink()
        data=self.evaluate()
        self.assertEqual(data["topn_by_evidence_status"]["missing_observation"]["races"],1)
        self.assertEqual(data["topn_by_evidence_status"]["missing_observation"]["hits"]
                         ["third_national_rate"]["top10"],1)

    def test_mismatched_outcome_flags_fail_closed(self):
        self.future["hits"]["third_national_rate"]["top10"]=0
        with self.assertRaisesRegex(ValueError,"stratum_hit_reconciliation"):
            self.evaluate()

    def test_malformed_ledger_aggregates_are_not_accepted(self):
        self.save()
        doc=json.loads(self.location.read_text())
        doc["observed_before_t_minus_12"]=0
        self.location.write_text(json.dumps(doc))
        report=self.evaluate()
        self.assertEqual(report["race_status"][CODE],"missing_observation")
        self.assertEqual(report["excluded_ledger_files"]["invalid_ledger_file"],1)

    def test_wrong_day_or_duplicate_rows_are_not_accepted(self):
        self.save()
        doc=json.loads(self.location.read_text())
        doc["records"].append(dict(doc["records"][0]))
        doc["publication_count"]=2
        doc["observed_before_t_minus_12"]=2
        self.location.write_text(json.dumps(doc))
        self.assertEqual(self.evaluate()["race_status"][CODE],"missing_observation")
        self.row["race_code"]="202611050101"
        self.save()
        self.assertEqual(self.evaluate()["race_status"][CODE],"missing_observation")

    def test_missing_archive_status_or_production_guard_rejected(self):
        self.save()
        doc=json.loads(self.location.read_text())
        doc.pop("production_forecast_changed")
        self.location.write_text(json.dumps(doc))
        report=self.evaluate()
        self.assertEqual(report["race_status"][CODE],"missing_observation")
        self.assertEqual(report["excluded_ledger_files"]["invalid_ledger_file"],1)

    def test_prior_dates_not_allowed_in_new_cohort(self):
        self.future["race_codes"]=["202611030101"]
        with self.assertRaisesRegex(ValueError,"invalid_comparable_race_codes"):
            self.evaluate()

if __name__=="__main__":unittest.main()
