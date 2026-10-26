import unittest
from unittest.mock import patch
from research_pair_remote_publish import push

class RemotePublishTests(unittest.TestCase):
    def test_refuses_main(self):
        with patch("research_pair_remote_publish._git",return_value="main"):
            with self.assertRaisesRegex(ValueError,"research branch"):
                push("20261028")
    def test_dry_run_no_push(self):
        def git(*args):
            if args[0]=="branch": return "research/paired-hit-evaluation-20261027"
            if args[0]=="status": return ""
            if args[0]=="rev-parse": return "a"*40
            if args[0]=="hash-object": return "a"*40
            if args[0]=="diff-tree": return "research_prospective_pairs/202610281201.json"
            raise AssertionError(args)
        with patch("research_pair_remote_publish._git",side_effect=git),patch(
             "research_pair_remote_publish.eligible_paths",return_value=["research_prospective_pairs/202610281201.json"]),patch(
             "research_pair_remote_publish.subprocess.run") as cmd:
            result=push("20261028")
            cmd.assert_not_called()
            self.assertFalse(result["remote_head_verified"])
            self.assertFalse(result["pre_cutoff_remote_receipt_verified"])
    def test_repeated_same_day_batch_only_new_head_files(self):
        fresh="research_prospective_pairs/202610281202.json"
        older="research_prospective_pairs/202610281201.json"
        def git(*args):
            if args[0]=="branch": return "research/paired-hit-evaluation-20261027"
            if args[0]=="status": return ""
            if args[0]=="rev-parse": return "a"*40
            if args[0]=="diff-tree": return fresh
            if args[0]=="hash-object": return "a"*40
            raise AssertionError(args)
        with patch("research_pair_remote_publish._git",side_effect=git),patch(
            "research_pair_remote_publish.eligible_paths",
            return_value=[older,fresh]):
            self.assertTrue(push("20261028")["dry_run"])
    def test_untracked_today_baseline_allowed(self):
        def git(*args):
            if args[0]=="branch": return "research/paired-hit-evaluation-20261027"
            if args[0]=="status": return "?? research_snapshots/202610281201.json"
            if args[0] in ("rev-parse","hash-object"): return "a"*40
            if args[0]=="diff-tree": return "research_prospective_pairs/202610281201.json"
            raise AssertionError(args)
        with patch("research_pair_remote_publish._git",side_effect=git),patch(
            "research_pair_remote_publish.eligible_paths",
            return_value=["research_prospective_pairs/202610281201.json"]):
            self.assertTrue(push("20261028")["dry_run"])
    def test_unrelated_commit_files_rejected(self):
        def git(*args):
            if args[0]=="branch": return "research/paired-hit-evaluation-20261027"
            if args[0]=="status": return ""
            if args[0]=="rev-parse": return "a"*40
            if args[0]=="diff-tree":
                return ("research_prospective_pairs/202610281201.json" if "--diff-filter=A" in args
                        else "research_prospective_pairs/202610281201.json\\npredictions.json")
            raise AssertionError(args)
        with patch("research_pair_remote_publish._git",side_effect=git),patch(
            "research_pair_remote_publish.eligible_paths",
            return_value=["research_prospective_pairs/202610281201.json"]):
            with self.assertRaisesRegex(ValueError,"unrelated changes"):
                push("20261028")
    def test_other_untracked_change_rejected(self):
        with patch("research_pair_remote_publish._git",
                   side_effect=["research/paired-hit-evaluation-20261027","?? predictions.json"]):
            with self.assertRaisesRegex(ValueError,"unrelated"):
                push("20261028")
    def test_uncommitted_pair_refused(self):
        def git(*args):
            if args[0]=="branch": return "research/paired-hit-evaluation-20261027"
            if args[0]=="status": return ""
            if args[0]=="rev-parse": return "a"*40
            if args[0]=="hash-object": return "b"*40
            if args[0]=="diff-tree": return "research_prospective_pairs/202610281201.json"
            raise AssertionError(args)
        with patch("research_pair_remote_publish._git",side_effect=git),patch(
            "research_pair_remote_publish.eligible_paths",
            return_value=["research_prospective_pairs/202610281201.json"]),patch(
            "research_pair_remote_publish.subprocess.run") as cmd:
            with self.assertRaisesRegex(ValueError,"not committed"):
                push("20261028",dry_run=False)
            cmd.assert_not_called()

if __name__=="__main__":
    unittest.main()
