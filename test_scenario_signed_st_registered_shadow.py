"""Frozen signed-F 4-mode study: validate local identities before any math.

No official archive is fabricated as a new prospective candidate. Real
original-source tests belong only in the pinned historical CI ZIP replay.
"""
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import scenario_signed_st_registered_shadow as subject
from scenario_future_local_candidate_handoff import _git_blob_sha1


class RegisteredProtocolSafetyTests(unittest.TestCase):
    def test_registered_protocol_byte_and_method_source_hashes_are_stable(self):
        raw=subject.PROTOCOL.read_bytes()
        self.assertEqual(_git_blob_sha1(raw),subject.PROTOCOL_BLOB)
        self.assertEqual(_git_blob_sha1(subject.PARENT_PROTOCOL.read_bytes()),
                         subject.PARENT_BLOB)
        protocol=__import__("json").loads(raw)
        self.assertEqual(protocol["study_id"],
                         "EXPLORATORY_ONLY_SIGNED_F_ST_4MODE_SHADOW_V1")
        self.assertEqual(protocol["eligible_new_race_deadline_start_jst"],
                         "2026-11-12T00:00:00+09:00")
        self.assertFalse(protocol["deployment"]["collector_installed"])
        self.assertFalse(protocol["deployment"]["prospective_candidate_publisher_installed"])
        self.assertFalse(protocol["deployment"]["production_enabled"])
        self.assertEqual(protocol["deployment"]["formal_scored_races"],0)
        self.assertTrue(protocol["original_1693_1710_future_600_unchanged"])
        for path, sha in protocol["method_git_blob_sha1"].items():
            self.assertEqual(_git_blob_sha1((subject.ROOT/path).read_bytes()),sha,path)

    def test_modified_protocol_is_rejected_before_math_and_no_write(self):
        with tempfile.TemporaryDirectory() as d:
            altered=Path(d)/"study.json"
            altered.write_bytes(subject.PROTOCOL.read_bytes()+b" ")
            with patch.object(subject,"PROTOCOL",altered):
                with self.assertRaisesRegex(ValueError,"protocol_blob_drift"):
                    subject.require_registered_signed_F_method(None)

    def test_unpinned_external_callback_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"exact_1698_callback_required"):
            subject.require_registered_signed_F_method(lambda *args:None)


class SignedFReviewedConditionalIdentityTests(unittest.TestCase):
    def setUp(self):
        if os.getenv("RESEARCH_1698_PIN_REQUIRED")!="1":
            self.skipTest("frozen reviewed #1698 external blob required")
        m=importlib.import_module("position_sensitive_conditioned_lab")
        self.callback=m.experimental_conditional_board

    def test_registered_1698_exact_function_accepts_existing_pinned_code(self):
        protocol=subject.require_registered_signed_F_method(self.callback)
        self.assertEqual(protocol["study_id"],subject.STUDY_ID)

    def test_unpinned_callback_still_rejected_even_when_module_claims_same_name(self):
        def forged(*args):
            return self.callback(*args)
        forged.__module__="position_sensitive_conditioned_lab"
        with self.assertRaisesRegex(ValueError,"1698_executable_git_blob_mismatch"):
            subject.require_registered_signed_F_method(forged)


if __name__=="__main__":
    unittest.main()
