"""Fail-closed tests for the remote 4-mode candidate evidence-branch inventory."""
import copy
import hashlib
import json
import unittest

from four_mode_candidate_ledger_readiness import (
    BRANCH, SCHEMA, NOTE_SCHEMA, git_blob_sha, review,
)

DAY = "20261109"
RUN = "42546585986"
ATTEMPT = "1"
PATH = f"four_mode_all/{DAY}/run-{RUN}-attempt-{ATTEMPT}.json"
NOTE = f"four_mode_all_observation/{DAY}/run-{RUN}-attempt-{ATTEMPT}.json"


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def original():
    return {
        "schema": SCHEMA,
        "formal": False,
        "candidate_first_remote_receipt_verified": False,
        "production_forecast_changed": False,
        "frozen_count": 1,
        "records": [{"status": "frozen_local_before_T_minus_12_research_only"}],
    }


def observation(digest):
    return {
        "schema": NOTE_SCHEMA, "formal": False,
        "candidate_first_remote_receipt_verified": False,
        "candidate_github_server_observation_not_first_receipt": True,
        "branch": BRANCH, "path": PATH,
        "capture_run_id": RUN, "capture_run_attempt": ATTEMPT,
        "candidate_sha256": digest, "locally_frozen_count": 1,
        "observed_before_t_minus_12": 1,
        "observed_late_or_ambiguous": 0,
    }


def setup(with_candidate=True, with_note=True):
    tree = {"sha": "a" * 40, "truncated": False, "tree": []}
    blobs = {}
    if with_candidate:
        raw = encoded(original())
        sha = git_blob_sha(raw)
        blobs[sha] = raw
        tree["tree"].append({"path": PATH, "type": "blob",
                             "mode": "100644", "sha": sha, "size": len(raw)})
    if with_note:
        raw = encoded(observation(hashlib.sha256(blobs.get(
            tree["tree"][0]["sha"], b"missing")).hexdigest()))
        sha = git_blob_sha(raw)
        blobs[sha] = raw
        tree["tree"].append({"path": NOTE, "type": "blob",
                             "mode": "100644", "sha": sha, "size": len(raw)})
    return tree, blobs


class CandidateLedgerReadinessTests(unittest.TestCase):
    def test_no_candidate_path_is_unadmitted_not_a_pass(self):
        tree, blobs = setup(False, False)
        r = review(tree, blobs.__getitem__)
        self.assertEqual(r["durable_candidate_records"], 0)
        self.assertEqual(r["future_paired_races_admitted"], 0)
        self.assertEqual(r["status"],
                         "no_durable_all_mode_candidates_in_inspected_branch")
        self.assertFalse(r["formal"])
        self.assertFalse(r["model_promotion_allowed"])

    def test_matching_realistic_ledger_is_still_not_first_receipt(self):
        tree, blobs = setup()
        r = review(tree, blobs.__getitem__)
        self.assertEqual(r["durable_candidate_run_artifacts"], 1)
        self.assertEqual(r["matching_observation_notes"], 1)
        self.assertEqual(r["github_observed_before_t12_not_first_receipt"], 1)
        self.assertFalse(r["independent_first_remote_candidate_receipt_verified"])
        self.assertFalse(r["official_three_originals_verified"])
        self.assertEqual(r["future_paired_races_admitted"], 0)

    def test_candidate_without_note_is_explicitly_incomplete(self):
        tree, blobs = setup(True, False)
        r = review(tree, blobs.__getitem__)
        self.assertEqual(r["candidate_without_observation_note"], 1)
        self.assertEqual(r["matching_observation_notes"], 0)
        self.assertFalse(r["formal"])

    def test_orphan_note_rejected(self):
        tree, blobs = setup()
        tree["tree"].pop(0)
        with self.assertRaisesRegex(ValueError, "observation_note_without"):
            review(tree, blobs.__getitem__)

    def test_mismatched_observation_sha_rejected(self):
        tree, blobs = setup()
        note_entry = tree["tree"][1]
        note_obj = json.loads(blobs[note_entry["sha"]])
        note_obj["candidate_sha256"] = "f" * 64
        changed = encoded(note_obj)
        del blobs[note_entry["sha"]]
        note_entry["sha"] = git_blob_sha(changed)
        note_entry["size"] = len(changed)
        blobs[note_entry["sha"]] = changed
        with self.assertRaisesRegex(ValueError, "candidate_and_observation"):
            review(tree, blobs.__getitem__)

    def test_forged_formal_and_first_receipt_fail(self):
        for field, value, target in (
                ("formal", True, 0),
                ("candidate_first_remote_receipt_verified", True, 0),
                ("formal", True, 1),
                ("candidate_first_remote_receipt_verified", True, 1)):
            with self.subTest(field=field, target=target):
                tree, blobs = setup()
                entry = tree["tree"][target]
                obj = json.loads(blobs[entry["sha"]])
                obj[field] = value
                raw = encoded(obj)
                blobs[git_blob_sha(raw)] = raw
                entry["sha"] = git_blob_sha(raw)
                entry["size"] = len(raw)
                with self.assertRaises(ValueError):
                    review(tree, blobs.__getitem__)

    def test_tampered_blob_rejected_even_with_consistent_json(self):
        tree, blobs = setup(True, False)
        blob = tree["tree"][0]["sha"]
        blobs[blob] += b" "
        with self.assertRaisesRegex(ValueError, "git_blob_mismatch"):
            review(tree, blobs.__getitem__)

    def test_partial_tree_and_invalid_candidate_path_rejected(self):
        tree, blobs = setup()
        for mutate in ("truncated", "empty_sha", "bad_path", "duplicate"):
            with self.subTest(mutate=mutate):
                altered = copy.deepcopy(tree)
                if mutate == "truncated":
                    altered["truncated"] = True
                elif mutate == "empty_sha":
                    altered["sha"] = "not-a-real-commit"
                elif mutate == "bad_path":
                    altered["tree"][0]["path"] = "four_mode_all/20261109/foo.json"
                else:
                    altered["tree"].append(copy.deepcopy(altered["tree"][0]))
                with self.assertRaises(ValueError):
                    review(altered, blobs.__getitem__)

    def test_expected_recursive_git_tree_directories_are_allowed(self):
        tree, blobs = setup()
        tree["tree"].insert(0, {
            "path": "four_mode_all/20261109", "type": "tree",
            "mode": "040000", "sha": "a"*40,
        })
        tree["tree"].insert(1, {
            "path": "four_mode_all_observation/20261109", "type": "tree",
            "mode": "040000", "sha": "b"*40,
        })
        self.assertEqual(review(tree, blobs.__getitem__)["matching_observation_notes"], 1)
        tree["tree"][0]["path"] = "four_mode_all/20261109/fake-extra-directory"
        with self.assertRaisesRegex(ValueError, "unsafe_candidate_ledger_directory"):
            review(tree, blobs.__getitem__)

    def test_observation_count_and_identity_rejected(self):
        for field, value in (("locally_frozen_count", 2),
                             ("observed_before_t_minus_12", 2),
                             ("capture_run_id", "not-run"),
                             ("branch", "main")):
            with self.subTest(field=field):
                tree, blobs = setup()
                entry = tree["tree"][1]
                obj = json.loads(blobs[entry["sha"]])
                obj[field] = value
                raw = encoded(obj)
                blobs[git_blob_sha(raw)] = raw
                entry["sha"] = git_blob_sha(raw)
                entry["size"] = len(raw)
                with self.assertRaises(ValueError):
                    review(tree, blobs.__getitem__)

    def test_unrelated_evidence_files_do_not_become_candidates(self):
        tree, blobs = setup(False, False)
        tree["tree"] = [
            {"path": "github_server/20261109/observed.json",
             "type": "blob", "mode": "100644", "sha": "b" * 40,
             "size": 10},
            {"path": "third_rate/20261109/other.json",
             "type": "blob", "mode": "100644", "sha": "c" * 40,
             "size": 10},
        ]
        self.assertEqual(review(tree, blobs.__getitem__)["durable_candidate_records"], 0)


if __name__ == "__main__":
    unittest.main()
