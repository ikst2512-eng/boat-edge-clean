"""Synthetic local Git history; does not prove external receipt time."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.verify_research_git_first_add import verify_first_add

CODE = "202610270101"

def command(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).decode().strip()

class FirstAddEvidenceTests(unittest.TestCase):
    def test_added_blob_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command(root, "init", "-q")
            command(root, "config", "user.name", "Audit Test")
            command(root, "config", "user.email", "audit@example.invalid")
            path = root / "research_snapshots" / (CODE + ".json")
            path.parent.mkdir()
            path.write_text('{"research":true}', encoding="utf-8")
            command(root, "add", ".")
            command(root, "commit", "-qm", "initial")
            sha = command(root, "rev-parse", "HEAD")
            ref = "refs/heads/" + command(root, "branch", "--show-current")
            good = verify_first_add(root, CODE, sha, ref)
            self.assertTrue(good["verified"])
            self.assertFalse(good["remote_receipt_verified"])
            path.write_text('{"research":false}', encoding="utf-8")
            self.assertEqual(verify_first_add(root, CODE, sha, ref)["reason"],
                             "snapshot_differs_from_first_add")
            path.write_text('{"research":true}', encoding="utf-8")
            (root / "marker.txt").write_text("unrelated", encoding="utf-8")
            command(root, "add", ".")
            command(root, "commit", "-qm", "unrelated")
            newer = command(root, "rev-parse", "HEAD")
            self.assertEqual(verify_first_add(root, CODE, newer, ref)["reason"],
                             "not_added_in_commit")
    def test_deleted_and_readded_is_not_first_introduction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command(root, "init", "-q")
            command(root, "config", "user.name", "Audit Test")
            command(root, "config", "user.email", "audit@example.invalid")
            path = root / "research_snapshots" / (CODE + ".json")
            path.parent.mkdir()
            path.write_text('{"research":true}', encoding="utf-8")
            command(root, "add", ".")
            command(root, "commit", "-qm", "initial")
            path.unlink()
            command(root, "add", "-A")
            command(root, "commit", "-qm", "delete")
            path.write_text('{"research":true}', encoding="utf-8")
            command(root, "add", ".")
            command(root, "commit", "-qm", "re-add")
            sha = command(root, "rev-parse", "HEAD")
            ref = "refs/heads/" + command(root, "branch", "--show-current")
            self.assertEqual(verify_first_add(root, CODE, sha, ref)["reason"],
                             "path_existed_in_prior_history")

    def test_shallow_clone_cannot_claim_first_introduction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            command(root, "init", "-q")
            command(root, "config", "user.name", "Audit Test")
            command(root, "config", "user.email", "audit@example.invalid")
            path = root / "research_snapshots" / (CODE + ".json")
            path.parent.mkdir()
            path.write_text('{"research":true}', encoding="utf-8")
            command(root, "add", ".")
            command(root, "commit", "-qm", "first")
            (root / "marker.txt").write_text("later", encoding="utf-8")
            command(root, "add", ".")
            command(root, "commit", "-qm", "later")
            clone = Path(directory) / "shallow"
            subprocess.check_call(["git", "clone", "-q", "--depth", "1",
                                   root.as_uri(), str(clone)])
            sha = command(clone, "rev-parse", "HEAD")
            ref = "refs/heads/" + command(clone, "branch", "--show-current")
            self.assertEqual(
                verify_first_add(clone, CODE, sha, ref)["reason"],
                "incomplete_git_history"
            )

    def test_rejects_invalid_identifiers(self):
        with self.assertRaises(ValueError):
            verify_first_add(".", "../not-a-race", "a"*40)

if __name__ == "__main__":
    unittest.main()
