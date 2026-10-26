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
            raise AssertionError(args)
        with patch("research_pair_remote_publish._git",side_effect=git),patch(
             "research_pair_remote_publish.eligible_paths",return_value=[]),patch(
             "research_pair_remote_publish.subprocess.run") as cmd:
            result=push("20261028")
            cmd.assert_not_called()
            self.assertFalse(result["remote_head_verified"])
            self.assertFalse(result["pre_cutoff_remote_receipt_verified"])
if __name__=="__main__":
    unittest.main()
