import unittest
import json
import hashlib
from research_model import probabilities as baseline_probabilities
from paired_compare import TICKETS
from pr16_pair_preflight import inspect_pair

class PairPreflightTests(unittest.TestCase):
    def pair(self):
        p={"-".join(map(str,t)):v for t,v in baseline_probabilities([5.0]*6)}
        return dict(status="research_unvalidated",baseline=p,candidate=dict(p),
                    race_code="202610281201",source_snapshot_sha256="b"*64,
                    baseline_model_id="national-beta0.4-exploratory-v1",
                    candidate_model_id="scenario-exploratory-20261027-unvalidated",
                    frozen_at_jst="2026-10-28T11:50:00+09:00",
                    cutoff_jst="2026-10-28T12:00:00+09:00",
                    source_snapshot_generated_at="2026-10-28T11:49:00+09:00",
                    prospective_verified=False,entry_status="assumed_identity_not_verified",
                    candidate_git_blob_sha="a"*40)
    def test_unscored_even_when_syntactically_valid(self):
        outcome=inspect_pair(self.pair())
        self.assertFalse(outcome["ready_for_scoring"])
        self.assertTrue(outcome["distribution_structure_valid"])
        self.assertFalse(outcome["source_snapshot_digest_verified_locally"])
        self.assertIn("source snapshot original bytes not supplied",outcome["reasons"])
    def test_corrupt_distribution_rejected(self):
        pair=self.pair()
        pair["candidate"]["1-2-3"]=-1
        outcome=inspect_pair(pair)
        self.assertFalse(outcome["distribution_structure_valid"])
    def test_missing_snapshot_digest_rejected(self):
        pair=self.pair()
        pair.pop("source_snapshot_sha256")
        self.assertIn("missing source snapshot digest",inspect_pair(pair)["reasons"])
    def test_invalid_race_code_rejected(self):
        pair=self.pair()
        pair["race_code"]="202610282501"
        self.assertIn("race venue or number out of range",inspect_pair(pair)["reasons"])
    def test_missing_candidate_identity_rejected(self):
        pair=self.pair()
        pair["candidate_model_id"]=""
        self.assertIn("missing candidate_model_id",inspect_pair(pair)["reasons"])
    def test_source_snapshot_bytes_match_canonical_digest(self):
        pair=self.pair()
        source={"race_code":pair["race_code"],"status":"research","validated":False,
                "generated_at":pair["source_snapshot_generated_at"],
                "source_title_received_jst":"2026-10-28T11:40:00+09:00",
                "source_cards_received_jst":"2026-10-28T11:42:00+09:00",
                "cutoff_jst":pair["cutoff_jst"],
                "national_win_rates":[5.0]*6,
                "predictions":sorted(TICKETS,key=lambda t:(-pair["baseline"][t],t))[:10]}
        raw=json.dumps(source,ensure_ascii=False).encode("utf-8")
        canonical=json.dumps(source,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
        pair["source_snapshot_sha256"]=hashlib.sha256(canonical).hexdigest()
        self.assertNotIn("source snapshot bytes mismatch",inspect_pair(pair,raw)["reasons"])
        self.assertTrue(inspect_pair(pair,raw)["source_snapshot_digest_verified_locally"])
        self.assertIn("source snapshot bytes mismatch",inspect_pair(pair,b'{"race_code":"202610281202"}')["reasons"])
    def test_nonresearch_original_not_audited(self):
        pair=self.pair()
        source={"race_code":pair["race_code"],"status":"formal","validated":True}
        raw=json.dumps(source,sort_keys=True,separators=(",",":")).encode("utf-8")
        pair["source_snapshot_sha256"]=hashlib.sha256(raw).hexdigest()
        report=inspect_pair(pair,raw)
        self.assertFalse(report["source_snapshot_digest_verified_locally"])
        self.assertIn("source snapshot not unvalidated research",report["reasons"])
    def test_invalid_envelope_reports_distribution_false(self):
        result=inspect_pair({"status":"formal"})
        self.assertFalse(result["distribution_structure_valid"])
        self.assertFalse(result["ready_for_scoring"])
    def test_source_top10_mismatch_rejected(self):
        pair=self.pair()
        source={"race_code":pair["race_code"],"status":"research","validated":False,
                "generated_at":pair["source_snapshot_generated_at"],
                "cutoff_jst":pair["cutoff_jst"],"national_win_rates":[5.0]*6,
                "predictions":list(reversed(sorted(TICKETS,key=lambda t:(-pair["baseline"][t],t))[:10]))}
        raw=json.dumps(source,sort_keys=True,separators=(",",":")).encode("utf-8")
        pair["source_snapshot_sha256"]=hashlib.sha256(raw).hexdigest()
        report=inspect_pair(pair,raw)
        self.assertFalse(report["source_snapshot_digest_verified_locally"])
        self.assertIn("source snapshot Top10 differs from baseline",report["reasons"])
    def test_source_received_after_generation_rejected(self):
        pair=self.pair()
        source={"race_code":pair["race_code"],"status":"research","validated":False,
                "generated_at":pair["source_snapshot_generated_at"],"cutoff_jst":pair["cutoff_jst"],
                "source_title_received_jst":"2026-10-28T11:51:00+09:00",
                "source_cards_received_jst":"2026-10-28T11:40:00+09:00",
                "predictions":sorted(TICKETS)[:10]}
        raw=json.dumps(source,sort_keys=True,separators=(",",":")).encode("utf-8")
        pair["source_snapshot_sha256"]=hashlib.sha256(raw).hexdigest()
        report=inspect_pair(pair,raw)
        self.assertFalse(report["source_snapshot_digest_verified_locally"])
        self.assertIn("source snapshot source receipt chronology invalid",report["reasons"])
    def test_baseline_full_distribution_mismatch_rejected(self):
        pair=self.pair()
        source={"race_code":pair["race_code"],"status":"research","validated":False,
                "generated_at":pair["source_snapshot_generated_at"],
                "cutoff_jst":pair["cutoff_jst"],
                "source_title_received_jst":"2026-10-28T11:40:00+09:00",
                "source_cards_received_jst":"2026-10-28T11:42:00+09:00",
                "national_win_rates":[6.0,5.0,5.0,5.0,5.0,5.0],
                "predictions":sorted(TICKETS,key=lambda t:(-pair["baseline"][t],t))[:10]}
        raw=json.dumps(source,sort_keys=True,separators=(",",":")).encode("utf-8")
        pair["source_snapshot_sha256"]=hashlib.sha256(raw).hexdigest()
        report=inspect_pair(pair,raw)
        self.assertFalse(report["source_snapshot_digest_verified_locally"])
        self.assertIn("source snapshot baseline full-120 replay mismatch",report["reasons"])
    def test_late_freeze_rejected(self):
        pair=self.pair()
        pair["frozen_at_jst"]=pair["cutoff_jst"]
        self.assertIn("inconsistent pre-cutoff chronology",inspect_pair(pair)["reasons"])

if __name__=="__main__":
    unittest.main()
