import hashlib
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from audit_first_git_add import audit


class GitReceiptAuditTests(unittest.TestCase):
    def run_git(self, directory, *args):
        return subprocess.check_output(["git", "-C", str(directory), *args]).decode().strip()

    def test_first_add_and_tampering(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            self.run_git(root,"init","-q")
            self.run_git(root,"config","user.name","CI")
            self.run_git(root,"config","user.email","ci@example.invalid")
            (root/"seed.txt").write_text("seed",encoding="utf-8")
            self.run_git(root,"add","seed.txt")
            self.run_git(root,"commit","-qm","seed")
            blob=b'{"status":"research"}\n'
            (root/"frozen.json").write_bytes(blob)
            self.run_git(root,"add","frozen.json")
            self.run_git(root,"commit","-qm","first frozen file")
            first=self.run_git(root,"rev-parse","HEAD")
            digest=hashlib.sha256(blob).hexdigest()
            future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
            result=audit(root,first,"frozen.json",digest,future)
            self.assertEqual(result["status"],"LOCAL_GIT_FIRST_ADD_AND_BLOB_MATCH_ONLY")
            with self.assertRaises(ValueError):
                audit(root,first,"frozen.json","0"*64,future)
            (root/"frozen.json").write_text('{"status":"changed"}\n',encoding="utf-8")
            self.run_git(root,"add","frozen.json")
            self.run_git(root,"commit","-qm","changed")
            later=self.run_git(root,"rev-parse","HEAD")
            with self.assertRaises(ValueError):
                audit(root,later,"frozen.json",hashlib.sha256((root/"frozen.json").read_bytes()).hexdigest(),future)
            past=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
            with self.assertRaises(ValueError):
                audit(root,first,"frozen.json",digest,past)


if __name__=="__main__":
    unittest.main()
