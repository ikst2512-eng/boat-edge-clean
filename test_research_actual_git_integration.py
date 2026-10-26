"""Integration tests for real Git index and commit isolation (not mocked Git)."""
import os
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from research_model import JST
from research_pair_git_prepare import BRANCH, prepare

def git(*args):
    return subprocess.check_output(["git",*args],text=True).strip()

class ActualGitFreezeTests(unittest.TestCase):
    def setUp(self):
        self.root=tempfile.TemporaryDirectory()
        self.original=os.getcwd()
        os.chdir(self.root.name)
        subprocess.run(["git","init","-q","-b",BRANCH],check=True)
        Path("README.md").write_text("research test fixture\n")
        subprocess.run(["git","add","README.md"],check=True)
        subprocess.run(["git","-c","user.name=test","-c","user.email=test@example.invalid",
                        "commit","-qm","fixture"],check=True)
        Path("research_prospective_pairs").mkdir()
    def tearDown(self):
        os.chdir(self.original)
        self.root.cleanup()
    def test_commits_only_new_pair_file(self):
        pair=Path("research_prospective_pairs/202610281201.json")
        pair.write_text("{}")
        Path("research_snapshots").mkdir()
        Path("research_snapshots/202610281201.json").write_text("untouched")
        with patch("research_pair_git_prepare.eligible_paths",return_value=[pair.as_posix()]):
            x=prepare("20261028",now=datetime(2026,10,28,8,0,tzinfo=JST))
        self.assertTrue(x["commit_created"])
        self.assertEqual(git("diff-tree","--no-commit-id","--name-only","-r","HEAD"),pair.as_posix())
        self.assertTrue(Path("research_snapshots/202610281201.json").exists())
        self.assertEqual(git("ls-files","research_snapshots"),"")
    def test_unrelated_index_change_blocks_commit(self):
        Path("predictions.json").write_text("{}")
        subprocess.run(["git","add","predictions.json"],check=True)
        before=git("rev-parse","HEAD")
        with self.assertRaisesRegex(ValueError,"pre-existing staged"):
            prepare("20261028")
        self.assertEqual(git("rev-parse","HEAD"),before)

if __name__=="__main__":
    unittest.main()
