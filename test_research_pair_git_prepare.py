import unittest
from unittest.mock import patch
from research_pair_git_prepare import prepare

class GitPrepareTests(unittest.TestCase):
    def test_refuses_main(self):
        with patch("research_pair_git_prepare._git",return_value="main"):
            with self.assertRaisesRegex(ValueError,"non-research"):
                prepare("20261028")
    def test_no_eligible_no_commit(self):
        with patch("research_pair_git_prepare._git",side_effect=lambda *a: "research/paired-hit-evaluation-20261027" if a[0]=="branch" else ""), patch(
            "research_pair_git_prepare.eligible_paths",return_value=[]):
            self.assertEqual(prepare("20261028")["commit_created"],False)
    def test_refuses_pre_staged_files(self):
        def git(*args):
            if args[0]=="branch": return "research/paired-hit-evaluation-20261027"
            if args[:3]==("diff","--cached","--name-only"): return "predictions.json"
            raise AssertionError(args)
        with patch("research_pair_git_prepare._git",side_effect=git),patch(
            "research_pair_git_prepare.subprocess.run") as command:
            with self.assertRaisesRegex(ValueError,"pre-existing staged"):
                prepare("20261028")
            command.assert_not_called()
    def test_refuses_mutation_of_existing_pair(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/"research_prospective_pairs"
            folder.mkdir()
            pair=folder/"202610281201.json"
            pair.write_text("{}")
            calls=[0]
            def git(*args):
                if args[0]=="branch": return "research/paired-hit-evaluation-20261027"
                if args[:3]==("diff","--cached","--name-only"):
                    if "--diff-filter=A" in args: return ""
                    calls[0]+=1
                    return "" if calls[0]==1 else str(pair)
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
