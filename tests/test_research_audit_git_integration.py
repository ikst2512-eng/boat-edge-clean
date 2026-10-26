"""End-to-end synthetic research audit with a REAL local Git repository.
No actual races or results are used.
"""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.audit_research_outcomes import audit


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


class ResearchGitIntegration(unittest.TestCase):
    def test_real_git_first_add_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q")
            git(root, "config", "user.name", "Synthetic Audit")
            git(root, "config", "user.email", "synthetic@example.invalid")
            model_bytes = b"synthetic research model"
            (root / "research_model.py").write_bytes(model_bytes)
            git(root, "add", ".")
            git(root, "commit", "-qm", "freeze model")
            model_commit = git(root, "rev-parse", "HEAD")
            folder = root / "research_snapshots"
            folder.mkdir()
            code = "202610270101"
            first = "a" * 64
            second = "b" * 64
            combined = hashlib.sha256((first + ":" + second).encode("ascii")).hexdigest()
            snapshot = {
                "race_code": code, "status": "research", "validated": False,
                "predictions": ["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
                                "1-4-3","2-1-3","2-1-4","2-3-1","2-3-4"],
                "generated_at": "2026-10-27T09:00:00+09:00",
                "cutoff_jst": "2026-10-27T10:00:00+09:00",
                "source_title_received_jst": "2026-10-27T08:59:00+09:00",
                "source_cards_received_jst": "2026-10-27T08:59:00+09:00",
                "model_git_sha": model_commit, "model_source_sha256": hashlib.sha256(model_bytes).hexdigest(),
                "source_title_sha256": first, "source_cards_sha256": second,
                "input_sha256": combined,
                "input_hash_scope": "source_csv_byte_hashes_ordered_title_cards"
            }
            path = folder / (code + ".json")
            path.write_text(json.dumps(snapshot))
            git(root, "add", ".")
            git(root, "commit", "-qm", "first add")
            sha = git(root, "rev-parse", "HEAD")
            ref = "refs/heads/" + git(root, "branch", "--show-current")
            raw = path.read_bytes()
            att = {
                "race_code": code, "receipt_verified": True, "model_verified": True,
                "inputs_verified": True, "result_verified": True, "receipt_id": "synthetic",
                "model_git_sha": snapshot["model_git_sha"],
                "model_file_sha256": snapshot["model_source_sha256"],
                "input_sha256": combined, "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
                "first_added_commit_sha": sha,
                "first_added_blob_sha": git(root, "rev-parse", sha + ":research_snapshots/" + code + ".json"),
                "first_commit_membership_verified": True,
                "first_commit_introduction_verified": True,
                "remote_receipt_verified": True,
                "first_seen_at": "2026-10-27T09:01:00+09:00",
                "official_deadline_at": "2026-10-27T10:12:00+09:00",
                "result_source_id": "synthetic-only", "confirmed_trifecta": "1-2-3"
            }
            outcome = {
                "race_code": code, "verified": True, "trifecta": "1-2-3",
                "result_source_id": "synthetic-only",
                "result_confirmed_at": "2026-10-27T10:13:00+09:00"
            }
            pin = hashlib.sha256(json.dumps([att], ensure_ascii=False,
                        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            ok = audit(folder, [att], [outcome], pin, git_repo=root, trusted_ref=ref)
            self.assertEqual(ok["valid_count"], 1)
            self.assertEqual(ok["metrics"]["top1"]["hits"], 1)
            path.write_text(json.dumps(dict(snapshot, generated_at="2026-10-27T09:01:00+09:00")))
            blocked = audit(folder, [att], [outcome], pin, git_repo=root, trusted_ref=ref)
            self.assertEqual(blocked["valid_count"], 0)
            self.assertEqual(blocked["exclusion_reasons"]["snapshot_hash_mismatch"], 1)


if __name__ == "__main__":
    unittest.main()
