"""Synthetic tests of nonformal, cross-surface public checkpoint.

These tests fabricate GitHub API responses and DO NOT certify an actual
GitHub first receipt. Live CI independently fetches real comment metadata.
"""
from copy import deepcopy
import hashlib
import json
import unittest

from test_four_mode_position_sensitive_forward import archive, frozen
from position_sensitive_public_comment_witness import (
    ID, REPO, RACE, SCHEMA, audit_public_comment,
)
from position_sensitive_receipt_intake import git_blob_sha


FIRST_ADD = "3665b15b36c617c042f0c93685e6bcdd4ba1e31a"


def fixture():
    candidate, original = frozen(
        archive(RACE, deadline="2026-11-09T20:38:00+09:00"),
        "2026-11-09T14:25:53+09:00")
    exact = (json.dumps(candidate, ensure_ascii=False, sort_keys=True,
                        indent=2) + "\n").encode()
    hash_value = hashlib.sha256(exact).hexdigest()
    original_hash = hashlib.sha256(original).hexdigest()
    body = (
        "#1698 independent existence checkpoint\n\n" +
        "- Race: " + chr(96) + RACE + chr(96) +
        " (deadline " + chr(96) + "2026-11-09T20:38:00+09:00" +
        chr(96) + "; strict T−12 cutoff " + chr(96) +
        "2026-11-09T20:26:00+09:00" + chr(96) + ").\n" +
        "- Candidate path (SEPARATE research-only ledger): " +
        chr(96) + "position_sensitive_research/" + RACE + ".json" +
        chr(96) + " at research-only ledger.\n" +
        "- Candidate first-add commit visible on GitHub: " +
        chr(96) + FIRST_ADD + chr(96) + ". Its clock is not first receipt.\n" +
        "- Exact candidate Git blob SHA-1: " +
        chr(96) + git_blob_sha(exact) + chr(96) + ".\n" +
        "- Exact candidate bytes SHA-256 (independent Actions replay/observation): " +
        chr(96) + hash_value + chr(96) + ".\n" +
        "- Original " + chr(96) + "main:four_mode_forecasts/" + RACE +
        ".json" + chr(96) + " embedded SHA-256: " + chr(96) +
        original_hash + chr(96) + ".\n"
    )
    comment = {
        "id": ID,
        "html_url": "https://github.com/" + REPO +
                    "/pull/1698#issuecomment-" + str(ID),
        "user": {"login": "ikst2512-eng"},
        "created_at": "2026-11-09T08:12:02Z",
        "updated_at": "2026-11-09T08:12:02Z",
        "body": body,
    }
    return original, exact, comment


class PublicCommentCheckpointTests(unittest.TestCase):
    def test_matching_claim_is_public_server_checkpoint_not_first_receipt(self):
        original, exact, comment = fixture()
        out = audit_public_comment(original, exact, FIRST_ADD, comment)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["comment_created_at_utc"],
                         "2026-11-09T08:12:02+00:00")
        self.assertTrue(out["comment_currently_unedited"])
        self.assertFalse(out["comment_is_immutable"])
        self.assertFalse(out["comment_is_independently_first_remote_candidate_receipt"])
        self.assertEqual(out["independent_candidate_first_remote_receipts_verified"], 0)
        self.assertFalse(out["complete_capture_run_inventory_verified"])
        self.assertFalse(out["official_beforeinfo_six_boats_odds120_verified"])
        self.assertFalse(out["formal"])
        self.assertFalse(out["model_improvement_proven"])
        self.assertFalse(out["promotion_allowed"])

    def test_after_T12_and_at_cutoff_comments_are_never_attested(self):
        original, exact, comment = fixture()
        for stamp in ("2026-11-09T11:26:00Z", "2026-11-09T11:26:01Z",
                      "2026-11-09T12:30:00Z"):
            c = deepcopy(comment)
            c["created_at"] = c["updated_at"] = stamp
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                audit_public_comment(original, exact, FIRST_ADD, c)

    def test_comment_edited_after_creation_does_not_pass(self):
        original, exact, comment = fixture()
        comment["updated_at"] = "2026-11-09T08:30:00Z"
        with self.assertRaisesRegex(ValueError, "edited"):
            audit_public_comment(original, exact, FIRST_ADD, comment)

    def test_wrong_author_comment_id_or_url_cannot_pass(self):
        original, exact, comment = fixture()
        for key, value in (("id", ID + 1), ("html_url", "https://example.com"),
                           ("user", {"login": "attacker"})):
            c = deepcopy(comment)
            c[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "identity"):
                audit_public_comment(original, exact, FIRST_ADD, c)

    def test_modified_first_add_or_candidate_digest_fails(self):
        original, exact, comment = fixture()
        with self.assertRaisesRegex(ValueError, "mismatch"):
            audit_public_comment(original, exact, "a"*40, comment)
        tampered = deepcopy(comment)
        tampered["body"] = tampered["body"].replace(
            hashlib.sha256(exact).hexdigest(), "f"*64)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            audit_public_comment(original, exact, FIRST_ADD, tampered)

    def test_original_exact_bytes_and_ticket_mismatch_fail(self):
        original, exact, comment = fixture()
        with self.assertRaisesRegex(ValueError, "replayed"):
            audit_public_comment(original + b" ", exact, FIRST_ADD, comment)
        data = json.loads(exact)
        data["candidate"]["hit"][0] = "6-5-4"
        with self.assertRaisesRegex(ValueError, "replayed"):
            audit_public_comment(
                original, json.dumps(data).encode(), FIRST_ADD, comment)

    def test_duplicate_candidate_claim_detected(self):
        original, exact, comment = fixture()
        line = [l for l in comment["body"].splitlines()
                if l.startswith("- Exact candidate Git blob SHA-1:")][0]
        comment["body"] += line + "\n"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit_public_comment(original, exact, FIRST_ADD, comment)

    def test_missing_original_path_cutoff_or_comment_claim_rejected(self):
        original, exact, comment = fixture()
        for phrase in ("position_sensitive_research/" + RACE + ".json",
                       "2026-11-09T20:26:00+09:00",
                       "Original "):
            tampered = deepcopy(comment)
            tampered["body"] = tampered["body"].replace(phrase, "GONE")
            with self.subTest(phrase=phrase), self.assertRaises(ValueError):
                audit_public_comment(original, exact, FIRST_ADD, tampered)

    def test_comment_before_candidate_local_freeze_or_invalid_offset_rejected(self):
        original, exact, comment = fixture()
        for stamp in ("2026-11-09T05:25:53Z", "2026-11-09T08:12:02+09:00"):
            tampered = deepcopy(comment)
            tampered["created_at"] = tampered["updated_at"] = stamp
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                audit_public_comment(original, exact, FIRST_ADD, tampered)


if __name__ == "__main__":
    unittest.main()
