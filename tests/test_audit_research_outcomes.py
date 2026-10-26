"""Synthetic fixtures only; these assertions MUST NOT be described as race accuracy."""
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from scripts.audit_research_outcomes import audit

class AuditTests(unittest.TestCase):
    @patch('scripts.audit_research_outcomes.subprocess.check_call')
    @patch('scripts.audit_research_outcomes.subprocess.check_output')
    @patch('scripts.audit_research_outcomes.verify_first_add')
    def test_missing_evidence_fail_closed_and_verified_fixture(self, git_verify, git_model, git_ancestor):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"202610260101.json"
            snap={"race_code":"202610260101", "status":"research", "validated":False,
                  "predictions":["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
                                 "1-4-3","2-1-3","2-1-4","2-3-1","2-3-4"],
                  "generated_at":"2026-10-26T09:00:00+09:00",
                  "cutoff_jst":"2026-10-26T10:00:00+09:00",
                  "source_title_received_jst":"2026-10-26T08:59:00+09:00",
                  "source_cards_received_jst":"2026-10-26T08:59:00+09:00",
                  "model_git_sha":"a"*40, "model_source_sha256":"b"*64, "input_sha256":"c"*64}
            snap["source_title_sha256"] = "d"*64
            snap["source_cards_sha256"] = "e"*64
            snap["input_hash_scope"] = "source_csv_byte_hashes_ordered_title_cards"
            snap["input_sha256"] = hashlib.sha256(
                (snap["source_title_sha256"] + ":" + snap["source_cards_sha256"]).encode("ascii")
            ).hexdigest()
            p.write_text(json.dumps(snap))
            # Refuse symlinked inputs even if they point to a valid JSON file.
            link=Path(d)/"202610260102.json"
            link.symlink_to(p)
            self.assertEqual(
                audit(d,[],[])["exclusion_reasons"]["unsafe_snapshot_file"], 1
            )
            link.unlink()
            self.assertEqual(audit(d,[],[])["valid_count"],0)
            with patch.object(Path, "read_bytes", side_effect=OSError("synthetic I/O failure")):
                failure = audit(d, [], [])
            self.assertEqual(failure["valid_count"], 0)
            self.assertEqual(failure["exclusion_reasons"]["malformed_snapshot_or_manifest"], 1)

            att={"race_code":snap["race_code"],"receipt_verified":True,"model_verified":True,
                 "inputs_verified":True,"result_verified":True,
                 "receipt_id":"test-only","model_git_sha":"a"*40,
                 "result_source_id":"synthetic-fixture-only","confirmed_trifecta":"1-2-3",
                 "model_file_sha256":"b"*64,"input_sha256":snap["input_sha256"],
                 "snapshot_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                 "first_seen_at":"2026-10-26T09:01:00+09:00",
                 "official_deadline_at":"2026-10-26T10:12:00+09:00"}
            att["first_added_commit_sha"] = "1"*40
            att["first_added_blob_sha"] = hashlib.sha1(
                b"blob " + str(len(p.read_bytes())).encode("ascii") + b"\0" + p.read_bytes()
            ).hexdigest()
            att["first_commit_membership_verified"] = True
            att["first_commit_introduction_verified"] = True
            att["remote_receipt_verified"] = True
            git_model.return_value = b"synthetic model bytes"
            snap["model_source_sha256"] = hashlib.sha256(git_model.return_value).hexdigest()
            p.write_text(json.dumps(snap))
            att["model_file_sha256"] = snap["model_source_sha256"]
            att["snapshot_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            att["first_added_blob_sha"] = hashlib.sha1(b"blob " + str(len(p.read_bytes())).encode("ascii") + b"\0" + p.read_bytes()).hexdigest()
            git_verify.side_effect = lambda *_: {
                "verified": True,
                "first_added_blob_sha": att["first_added_blob_sha"],
                "snapshot_sha256": att["snapshot_sha256"],
            }
            outcome={"race_code":snap["race_code"],"verified":True,"trifecta":"1-2-3",
                     "result_source_id":"synthetic-fixture-only",
                     "result_confirmed_at":"2026-10-26T10:13:00+09:00"}
            unapproved=audit(d,[att],[outcome])
            self.assertEqual(unapproved["valid_count"],0)
            self.assertIsNone(unapproved["metrics"]["top1"]["rate"])
            self.assertIsNone(unapproved["metrics"]["top10"]["wilson95"])
            self.assertEqual(unapproved["exclusion_reasons"]["missing_independent_manifest_approval"],1)
            self.assertEqual(audit(d,[att],[outcome],"0"*64)["valid_count"],0)
            digest=lambda: hashlib.sha256(json.dumps([att],ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            self.assertEqual(audit(d,[att],[outcome],digest())["exclusion_reasons"]["git_history_not_verified"],1)
            self.assertEqual(audit(d,[att],[outcome],digest(),git_repo=d)["metrics"]["top1"]["hits"],1)
            att["remote_receipt_verified"] = False
            self.assertEqual(
                audit(d,[att],[outcome],digest(),git_repo=d)["exclusion_reasons"]["unverified_first_commit_or_remote_receipt"],1
            )
            att["remote_receipt_verified"] = True
            # The attested model hash must match the actual frozen Git source.
            git_model.return_value = b"modified model bytes"
            rejected = audit(d,[att],[outcome],digest(),git_repo=d)
            self.assertEqual(rejected["valid_count"],0)
            self.assertEqual(rejected["exclusion_reasons"]["model_git_source_mismatch"],1)
            git_model.return_value = b"synthetic model bytes"
            git_ancestor.side_effect = __import__("subprocess").CalledProcessError(1, "git")
            rejected = audit(d,[att],[outcome],digest(),git_repo=d)
            self.assertEqual(rejected["exclusion_reasons"]["model_git_source_unavailable"],1)
            git_ancestor.side_effect = None
            att["first_seen_at"] = "2026-10-26T08:58:00+09:00"
            self.assertEqual(audit(d,[att],[outcome],digest(),git_repo=d)["exclusion_reasons"]["impossible_evidence_chronology"],1)
            att["first_seen_at"] = "2026-10-26T09:01:00+09:00"
            late_source=dict(snap)
            late_source["source_cards_received_jst"]="2026-10-26T09:01:00+09:00"
            p.write_text(json.dumps(late_source))
            att["snapshot_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            att["first_added_blob_sha"] = hashlib.sha1(
                b"blob " + str(len(p.read_bytes())).encode("ascii") + b"\0" + p.read_bytes()
            ).hexdigest()
            self.assertEqual(audit(d,[att],[outcome],digest(),git_repo=d)["exclusion_reasons"]["impossible_evidence_chronology"],1)
            p.write_text(json.dumps(snap))
            att["snapshot_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            att["first_added_blob_sha"] = hashlib.sha1(
                b"blob " + str(len(p.read_bytes())).encode("ascii") + b"\0" + p.read_bytes()
            ).hexdigest()
            att["confirmed_trifecta"]="2-1-3"
            self.assertEqual(audit(d,[att],[outcome],digest(),git_repo=d)["exclusion_reasons"]["result_attestation_mismatch"],1)
            att["confirmed_trifecta"]="1-2-3"
            invalid_result=dict(outcome)
            invalid_result.pop("result_source_id")
            self.assertEqual(audit(d,[att],[invalid_result],digest(),git_repo=d)["exclusion_reasons"]["missing_result_provenance"],1)
            invalid_result=dict(outcome)
            invalid_result.pop("result_confirmed_at")
            self.assertEqual(audit(d,[att],[invalid_result],digest(),git_repo=d)["exclusion_reasons"]["missing_result_confirmation_time"],1)
            invalid_result=dict(outcome)
            invalid_result["result_confirmed_at"]="2026-10-26T10:11:00+09:00"
            self.assertEqual(audit(d,[att],[invalid_result],digest(),git_repo=d)["exclusion_reasons"]["result_confirmed_before_deadline"],1)
            att["first_added_blob_sha"]="f"*40
            self.assertEqual(audit(d,[att],[outcome],digest(),git_repo=d)["exclusion_reasons"]["first_added_blob_mismatch"],1)
            att["first_added_blob_sha"]=hashlib.sha1(
                b"blob " + str(len(p.read_bytes())).encode("ascii") + b"\0" + p.read_bytes()
            ).hexdigest()
            inconsistent=dict(snap)
            inconsistent["source_cards_sha256"] = "f"*64
            p.write_text(json.dumps(inconsistent))
            att["snapshot_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            att["first_added_blob_sha"] = hashlib.sha1(
                b"blob " + str(len(p.read_bytes())).encode("ascii") + b"\0" + p.read_bytes()
            ).hexdigest()
            self.assertEqual(audit(d,[att],[outcome],digest(),git_repo=d)["exclusion_reasons"]["input_hash_inconsistent"],1)
            p.write_text(json.dumps(snap))
            att["snapshot_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            att["first_added_blob_sha"] = hashlib.sha1(
                b"blob " + str(len(p.read_bytes())).encode("ascii") + b"\0" + p.read_bytes()
            ).hexdigest()
            missing=dict(snap)
            missing.pop("input_sha256")
            p.write_text(json.dumps(missing))
            att["snapshot_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest()
            att["first_added_blob_sha"]=hashlib.sha1(
                b"blob " + str(len(p.read_bytes())).encode("ascii") + b"\0" + p.read_bytes()
            ).hexdigest()
            self.assertEqual(audit(d,[att],[outcome],digest(),git_repo=d)["exclusion_reasons"]["missing_frozen_model_or_input_hash"],1)
            p.write_text(json.dumps(snap))
            att["snapshot_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest()
            att["first_added_blob_sha"]=hashlib.sha1(
                b"blob " + str(len(p.read_bytes())).encode("ascii") + b"\0" + p.read_bytes()
            ).hexdigest()
            att["first_seen_at"]="2026-10-26T10:01:00+09:00"
            report=audit(d,[att],[outcome],digest(),git_repo=d)
            self.assertEqual(report["valid_count"],0)
            self.assertEqual(report["exclusion_reasons"]["receipt_after_cutoff"],1)
            att["first_seen_at"]="2026-10-26T09:01:00+09:00"
            p.write_text(p.read_text()+" ")
            self.assertEqual(audit(d,[att],[outcome],digest(),git_repo=d)["exclusion_reasons"]["snapshot_hash_mismatch"],1)

if __name__=="__main__":
    unittest.main()
