import unittest
from unittest.mock import patch
from research_pair_git_prepare import prepare

class GitPrepareTests(unittest.TestCase):
    def test_refuses_main(self):
        with patch("research_pair_git_prepare._git",return_value="main"):
            with self.assertRaisesRegex(ValueError,"non-research"):
                prepare("20261028")
    def test_no_eligible_no_commit(self):
        with patch("research_pair_git_prepare._git",return_value="research/paired-hit-evaluation-20261027"), patch(
            "research_pair_git_prepare.eligible_paths",return_value=[]):
            self.assertEqual(prepare("20261028")["commit_created"],False)
if __name__=="__main__":
    unittest.main()
