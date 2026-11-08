"""Safety tests for proposed, manually gated write-once pair research ledger.

No network, GitHub writes, result files, or credentials are used in CI.
"""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import hole_pair_write_once_candidate_ledger as ledger
from test_hole_pair_remote_receipt_evidence import candidate


def fixture(root):
    c = candidate()
    c["model_version"] = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
    original = {
        "race_code": c["race_code"],
        "deadline_jst": c["deadline_jst"],
        "generated_at_jst": "2026-11-09T10:40:00+09:00",
        "model_version": c["model_version"],
        "modes": {
            "hole": {"tickets": [{"combo": s} for s in c["candidates"]["baseline"]]},
            "hit": {"tickets": [{"combo": s} for s in c["candidates"]["baseline"]]},
            "balance": {"tickets": [{"combo": s} for s in c["candidates"]["baseline"]]},
        },
    }
    raw = (json.dumps(original, sort_keys=True) + "\n").encode()
    p = root / "four_mode_forecasts" / (c["race_code"] + ".json")
    p.parent.mkdir(parents=True)
    p.write_bytes(raw)
    c["source_sha256"] = hashlib.sha256(raw).hexdigest()
    c["source_git_blob_sha1"] = ledger.git_blob_sha1(raw)
    c["locked_selector_git_blobs"] = ledger.verify_locked_selection()
    return c, p


class WriteOncePairLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.record, self.source = fixture(self.root)
        self.store = {}
        self.created = []
        self.observed_at = datetime(2026, 11, 9, 1, 55, 0, tzinfo=timezone.utc)
        self.local_write_at = datetime(2026, 11, 9, 1, 53, 0, tzinfo=timezone.utc)

    def get(self, path):
        return self.store.get(path)

    def create(self, path, raw, reason):
        if path in self.store:
            raise AssertionError("overwrite prohibited")
        self.store[path] = raw
        self.created.append((path, reason))

    def observe(self, path):
        return self.observed_at, self.store[path]

    def publish(self, record=None):
        with patch("hole_future_pair_precommit.select", return_value=self.record["candidates"]):
            return ledger.publish_one(record or self.record, self.root,
                                      self.get, self.create, self.observe,
                                      now=self.local_write_at)

    def test_first_write_and_separate_observation_never_formal(self):
        r = self.publish()
        self.assertEqual(r["status"], "new_write_once_candidate")
        self.assertEqual(r["observation_status"],
                         "pre_t12_readback_consistent_not_first_receipt")
        self.assertEqual(r["observation_record_status"],
                         "new_write_once_observation")
        self.assertEqual(len(self.created), 2)
        self.assertEqual(
            r["candidate_path"],
            "hole_pair_candidates/20261109/202611090101.json")
        self.assertNotEqual(r["candidate_path"], r["observation_path"])
        self.assertFalse(r["independent_first_receipt_verified"])
        self.assertFalse(r["formal"])
        self.assertFalse(r["official_t12_complete_verified"])
        self.assertFalse(r["production_promotion_allowed"])

    def test_replay_is_idempotent_and_original_time_is_immutable(self):
        first = self.publish()
        count = len(self.created)
        self.observed_at = datetime(2026, 11, 9, 2, 5, 0, tzinfo=timezone.utc)
        second = self.publish()
        self.assertEqual(second["status"], "existing_identical_candidate")
        self.assertEqual(second["observation_record_status"],
                         "existing_identical_observation")
        self.assertEqual(second["observation_status"], first["observation_status"])
        self.assertEqual(len(self.created), count)

    def test_same_race_changed_candidate_record_cannot_overwrite(self):
        self.publish()
        altered = dict(self.record)
        altered["local_finish_jst"] = "2026-11-09T10:52:00+09:00"
        with self.assertRaisesRegex(ValueError, "immutable_candidate_collision"):
            self.publish(altered)
        self.assertEqual(len(self.created), 2)

    def test_mutated_existing_remote_candidate_refused(self):
        self.publish()
        name = "hole_pair_candidates/20261109/202611090101.json"
        self.store[name] = b"tampered"
        with self.assertRaisesRegex(ValueError, "immutable_candidate_collision"):
            self.publish()

    def test_forged_existing_early_observation_rejected(self):
        first = self.publish()
        name = first["observation_path"]
        data = json.loads(self.store[name])
        data["observation_status"] = "readback_late_or_same_second"
        self.store[name] = ledger.canonical_bytes(data)
        with self.assertRaisesRegex(ValueError, "previous_observation_time_conflict"):
            self.publish()
        data["observation_status"] = "pre_t12_readback_consistent_not_first_receipt"
        data["formal"] = True
        self.store[name] = ledger.canonical_bytes(data)
        with self.assertRaisesRegex(ValueError, "previous_observation_conflict"):
            self.publish()

    def test_late_remote_observation_is_not_early_or_formal(self):
        self.observed_at = datetime(2026, 11, 9, 2, 0, 0, tzinfo=timezone.utc)
        r = self.publish()
        self.assertEqual(r["observation_status"], "readback_late_or_same_second")
        self.assertFalse(r["independent_first_receipt_verified"])

    def test_fake_remote_bytes_fail_closed(self):
        with patch("hole_future_pair_precommit.select", return_value=self.record["candidates"]):
            with self.assertRaisesRegex(ValueError, "remote_candidate_bytes_conflict"):
                ledger.publish_one(self.record, self.root, self.get, self.create,
                                   lambda path: (self.observed_at, b"forged"),
                                   now=self.local_write_at)

    def test_original_archive_digest_and_race_must_match(self):
        self.source.write_text("changed")
        with self.assertRaisesRegex(ValueError, "original_forecast_fingerprint_mismatch"):
            self.publish()
        self.assertEqual(self.store, {})

    def test_forged_selector_replay_cannot_write(self):
        with patch("hole_future_pair_precommit.select",
                   return_value={k: ["1-2-3"] * 10 for k in self.record["candidates"]}):
            with self.assertRaisesRegex(ValueError, "frozen_selector_replay_mismatch"):
                ledger.publish_one(self.record, self.root, self.get,
                                   self.create, self.observe,
                                   now=self.local_write_at)
        self.assertEqual(self.store, {})

    def test_github_target_validation_prevents_invalid_repository(self):
        with self.assertRaisesRegex(ValueError, "invalid_remote_target"):
            ledger.github_observe("../../bad", "hole_pair_candidates/20261109/202611090101.json")
        with self.assertRaisesRegex(ValueError, "invalid_remote_target"):
            ledger.github_observe("owner/repo", "hole_pair_candidates/../file")

    def test_past_result_known_race_cannot_be_new_holdout(self):
        self.record["race_code"] = "202611080101"
        with self.assertRaisesRegex(ValueError, "not_future_protocol_eligible"):
            self.publish()
        self.assertEqual(self.store, {})


    def test_cli_dry_run_cannot_write_or_open_network(self):
        path = self.root / "candidate.json"
        path.write_bytes(ledger.canonical_bytes(self.record))
        argv = ["hole_pair_write_once_candidate_ledger.py",
                "--record", str(path), "--root", str(self.root)]
        with patch("sys.argv", argv), patch(
                "hole_future_pair_precommit.select",
                return_value=self.record["candidates"]), patch(
                "hole_pair_write_once_candidate_ledger.github_observe",
                side_effect=AssertionError("unexpected network read")):
            ledger.main()
        self.assertEqual(self.store, {})
        self.assertEqual(self.created, [])

    def test_cli_publish_cannot_run_from_pr_event(self):
        path = self.root / "candidate.json"
        path.write_bytes(ledger.canonical_bytes(self.record))
        argv = ["hole_pair_write_once_candidate_ledger.py",
                "--record", str(path), "--root", str(self.root),
                "--publish"]
        approval = {
            "GITHUB_EVENT_NAME": "pull_request",
            "HOLE_PAIR_LEDGER_MANUAL_APPROVAL": "YES",
            "GITHUB_REF": "refs/heads/research/hole-pair-future-precommit-20261105",
            "GITHUB_REPOSITORY": "ikst2512-eng/boat-edge-clean",
        }
        with patch("sys.argv", argv), patch.dict(
                "os.environ", approval, clear=True), patch(
                "hole_future_pair_precommit.select",
                return_value=self.record["candidates"]):
            with self.assertRaisesRegex(
                    ValueError, "manual_dispatch_approval_required"):
                ledger.main()
        self.assertEqual(self.store, {})
        self.assertEqual(self.created, [])


    def test_late_first_remote_create_refused_without_touching_store(self):
        self.local_write_at = datetime(
            2026, 11, 9, 2, 0, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(
                ValueError, "new_candidate_remote_write_too_late"):
            self.publish()
        self.assertEqual(self.store, {})
        self.assertEqual(self.created, [])

    def test_same_second_boundary_and_invalid_clock_refused(self):
        for instant in (
            datetime(2026, 11, 9, 1, 59, 59, tzinfo=timezone.utc),
            datetime(2026, 11, 9, 2, 0, 0, tzinfo=timezone.utc),
        ):
            self.local_write_at = instant
            with self.assertRaisesRegex(
                    ValueError, "new_candidate_remote_write_too_late"):
                self.publish()
        self.local_write_at = datetime(2026, 11, 9, 1, 50, 0)
        with self.assertRaisesRegex(ValueError, "untrusted_write_clock"):
            self.publish()
        self.assertEqual(self.store, {})

    def test_late_idempotent_replay_cannot_rewrite_original(self):
        initial = self.publish()
        copies = dict(self.store)
        self.local_write_at = datetime(
            2026, 11, 9, 3, 0, 0, tzinfo=timezone.utc)
        repeated = self.publish()
        self.assertEqual(repeated["status"], "existing_identical_candidate")
        self.assertEqual(initial["observation_status"],
                         repeated["observation_status"])
        self.assertEqual(self.store, copies)

    def test_missing_locked_selector_evidence_rejected_before_remote_io(self):
        self.record.pop("locked_selector_git_blobs")
        with self.assertRaisesRegex(
                ValueError, "locked_selector_or_method_source_mismatch"):
            self.publish()
        self.assertEqual(self.store, {})

    def test_wrong_locked_selector_blob_rejected_before_remote_io(self):
        self.record["locked_selector_git_blobs"] = {
            k: "0" * 40 for k in self.record["locked_selector_git_blobs"]
        }
        with self.assertRaisesRegex(
                ValueError, "locked_selector_or_method_source_mismatch"):
            self.publish()
        self.assertEqual(self.store, {})


if __name__ == "__main__":
    unittest.main()
