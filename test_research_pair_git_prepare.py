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
    def test_refuses_mutation_of_existing_pair(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/"research_prospective_pairs"
            folder.mkdir()
            pair=folder/"202610281201.json"
            pair.write_text("{}")
            def git(*args):
                if args[0]=="branch": return "research/paired-hit-evaluation-20261027"
                if args[:3]==("diff","--cached","--name-only"):
                    return str(pair)
                raise AssertionError(args)
            with patch("research_pair_git_prepare._git",side_effect=git),patch(
                "research_pair_git_prepare.eligible_paths",return_value=[str(pair)]),patch(
                "research_pair_git_prepare.subprocess.run") as command:
                with self.assertRaisesRegex(ValueError,"overwrite"):
                    prepare("20261028",str(folder))
                self.assertEqual(command.call_count,2)
                self.assertEqual(command.call_args.args[0][1],"reset")

if __name__=="__main__":
    unittest.main()
