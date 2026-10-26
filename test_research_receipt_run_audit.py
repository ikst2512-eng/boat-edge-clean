import unittest
from research_receipt_run_audit import run_audit

class ReceiptRunAuditTests(unittest.TestCase):
    def test_invalid_id_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid"):
            run_audit("bogus","a"*40)
    def test_invalid_sha_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid"):
            run_audit("123","unsafe")
if __name__=="__main__":
    unittest.main()
