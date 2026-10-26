import unittest
from unittest.mock import patch
from research_remote_receipt_verify import verify

PAIR="research_prospective_pairs/202610281201.json"
SHA="a"*40

class ReceiptVerifyTests(unittest.TestCase):
    def test_refuses_remote_mismatch(self):
        def git(*args,**kwargs):
            if args[0][1]=="rev-parse": return SHA+"\n"
            return PAIR+"\n"
        with patch("research_remote_receipt_verify.subprocess.check_output",side_effect=git):
            with self.assertRaisesRegex(ValueError,"remote ref"):
                verify("20261028",fetch=lambda:({"object":{"sha":"b"*40}},
                    "Wed, 28 Oct 2026 00:05:00 GMT"))
    def test_remote_server_time_certifies_only_current_batch(self):
        def git(*args,**kwargs):
            if args[0][1]=="rev-parse": return SHA+"\n"
            return PAIR+"\n"
        with patch("research_remote_receipt_verify.subprocess.check_output",side_effect=git),patch(
            "research_remote_receipt_verify.eligible_paths",return_value=[PAIR]) as guard:
            result=verify("20261028",fetch=lambda:({"object":{"sha":SHA}},
                "Wed, 28 Oct 2026 00:05:00 GMT"))
        self.assertTrue(result["remote_observed_pre_cutoff"])
        self.assertEqual(guard.call_args.kwargs["only_paths"],{PAIR})
        self.assertFalse(result["forecast_accuracy_verified"])
if __name__=="__main__":
    unittest.main()
