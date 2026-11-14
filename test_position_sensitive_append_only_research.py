"""Synthetic-only tests of candidate research branch create-only adapter.

No test network calls, branch creation or remote evidence attestations occur.
"""
from copy import deepcopy
from datetime import datetime
import json
import unittest

from test_four_mode_position_sensitive_forward import frozen
from position_sensitive_append_only_research import (
    PROPOSED_LEDGER_BRANCH, prepare_candidate, publish_write_once,
)


class FakeResearchLedger:
    def __init__(self):
        self.blobs = {}
        self.created = 0
        self.reads = 0

    def read(self, branch, path):
        self.reads += 1
        assert branch == PROPOSED_LEDGER_BRANCH
        return self.blobs.get((branch, path))

    def create(self, branch, path, body):
        assert branch == PROPOSED_LEDGER_BRANCH
        key = (branch, path)
        if key in self.blobs:
            raise ValueError("create_only_path_already_exists")
        self.created += 1
        self.blobs[key] = body


def fixture():
    snap, original = frozen()
    candidate = (json.dumps(snap, sort_keys=True, separators=(",", ":"))+"\n").encode()
    return original, candidate, snap["race_code"]


TIME = "2026-11-09T10:06:00+09:00"


class CandidateWriteOnceTests(unittest.TestCase):
    def test_valid_replay_writes_only_to_proposed_research_branch(self):
        original, candidate, code = fixture()
        fake = FakeResearchLedger()
        report = publish_write_once(
            original, candidate, TIME,
            PROPOSED_LEDGER_BRANCH, fake.read, fake.create)
        self.assertEqual(fake.created, 1)
        self.assertEqual(fake.blobs[(PROPOSED_LEDGER_BRANCH,
                                     f"position_sensitive_research/{code}.json")],
                         candidate)
        self.assertEqual(report["status"], "create_only_storage_call_returned_unattested")
        self.assertFalse(report["formal"])
        self.assertFalse(report["first_remote_candidate_receipt_verified"])
        self.assertFalse(report["official_beforeinfo_exhibition_six_odds120_verified"])
        self.assertFalse(report["model_improvement_proven"])
        self.assertFalse(report["promotion_allowed"])
        self.assertFalse(report["production_changed"])

    def test_identical_retry_never_adds_or_overwrites(self):
        original, candidate, _ = fixture()
        fake = FakeResearchLedger()
        publish_write_once(original, candidate, TIME,
                           PROPOSED_LEDGER_BRANCH, fake.read, fake.create)
        report = publish_write_once(original, candidate,
                                    "2026-11-09T10:07:00+09:00",
                                    PROPOSED_LEDGER_BRANCH, fake.read, fake.create)
        self.assertEqual(fake.created, 1)
        self.assertEqual(report["status"], "identical_candidate_already_present_unattested")
        self.assertFalse(report["first_remote_candidate_receipt_verified"])

    def test_main_or_unapproved_branch_cannot_write(self):
        original, candidate, _ = fixture()
        fake = FakeResearchLedger()
        for branch in ("main", "master", "research/position-sensitive-four-mode-shadow-20261108",
                       "v2-third-rate-evidence-ledger", ""):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                publish_write_once(original, candidate, TIME, branch, fake.read, fake.create)
        self.assertEqual(fake.created, 0)
        self.assertEqual(fake.reads, 0)

    def test_collision_with_different_bytes_fails_without_overwrite(self):
        original, candidate, code = fixture()
        fake = FakeResearchLedger()
        key = (PROPOSED_LEDGER_BRANCH, f"position_sensitive_research/{code}.json")
        fake.blobs[key] = b"old-other-snapshot"
        with self.assertRaisesRegex(ValueError, "immutable_candidate_collision"):
            publish_write_once(original, candidate, TIME,
                               PROPOSED_LEDGER_BRANCH, fake.read, fake.create)
        self.assertEqual(fake.blobs[key], b"old-other-snapshot")
        self.assertEqual(fake.created, 0)

    def test_stale_local_clock_after_T12_and_same_second_are_blocked(self):
        original, candidate, _ = fixture()
        fake = FakeResearchLedger()
        for stamp in ("2026-11-09T12:28:00+09:00",
                      "2026-11-09T12:29:00+09:00",
                      "2026-11-09T13:00:00+09:00",
                      "2026-11-09T10:05:00+09:00"):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                publish_write_once(original, candidate, stamp,
                                   PROPOSED_LEDGER_BRANCH, fake.read, fake.create)
        self.assertEqual(fake.reads, 0)
        self.assertEqual(fake.created, 0)

    def test_extra_outcome_field_and_json_duplicate_key_rejected(self):
        original, candidate, code = fixture()
        fake = FakeResearchLedger()
        value = json.loads(candidate)
        value["finish_order"] = [1, 2, 3]
        with self.assertRaises(ValueError):
            publish_write_once(original, json.dumps(value).encode(), TIME,
                               PROPOSED_LEDGER_BRANCH, fake.read, fake.create)
        original_duplicate = original[:-1]+b',"race_code":"'+code.encode()+b'"}'
        with self.assertRaises(ValueError):
            prepare_candidate(original_duplicate, candidate, TIME)
        candidate_duplicate = candidate.rstrip()[:-1]+b',"race_code":"'+code.encode()+b'"}'
        with self.assertRaises(ValueError):
            prepare_candidate(original, candidate_duplicate, TIME)
        self.assertEqual(fake.created, 0)

    def test_candidate_ticket_change_and_original_blob_change_rejected(self):
        original, candidate, _ = fixture()
        value = json.loads(candidate)
        value["candidate"]["hit"][0] = "6-5-4"
        with self.assertRaises(ValueError):
            prepare_candidate(original, json.dumps(value).encode(), TIME)
        with self.assertRaises(ValueError):
            prepare_candidate(original+b" ", candidate, TIME)

    def test_create_only_concurrent_race_error_is_not_suppressed(self):
        original, candidate, _ = fixture()
        fake = FakeResearchLedger()
        def create_race(branch, path, data):
            fake.blobs[(branch, path)] = b"other-concurrent-bytes"
            raise ValueError("concurrent_atomic_create_conflict")
        with self.assertRaisesRegex(ValueError, "concurrent_atomic_create_conflict"):
            publish_write_once(original, candidate, TIME, PROPOSED_LEDGER_BRANCH,
                               fake.read, create_race)
        self.assertEqual(fake.created, 0)

    def test_write_readback_corruption_fails_closed(self):
        original, candidate, _ = fixture()
        fake = FakeResearchLedger()
        def corrupt(branch, path, raw):
            fake.blobs[(branch, path)] = raw+b"\n"
            fake.created += 1
        with self.assertRaisesRegex(ValueError, "readback_mismatch"):
            publish_write_once(original, candidate, TIME,
                               PROPOSED_LEDGER_BRANCH, fake.read, corrupt)

    def test_prepare_only_does_not_perform_io_or_claim_remote(self):
        original, candidate, code = fixture()
        prepared = prepare_candidate(original, candidate, TIME)
        self.assertEqual(prepared["race_code"], code)
        self.assertEqual(prepared["candidate_bytes"], candidate)
        self.assertEqual(prepared["branch"], PROPOSED_LEDGER_BRANCH)
        self.assertFalse(prepared["remote_receipt_verified"])
        self.assertFalse(prepared["formal"])
        self.assertFalse(prepared["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
