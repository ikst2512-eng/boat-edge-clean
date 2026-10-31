import unittest
from scripts.probe_official_beforeinfo import probe

class OfficialProbeTest(unittest.TestCase):
    def test_metadata_not_exhibition_inference(self):
        data=probe("20261031",23,7,fetch=lambda url:b"<html>official test</html>")
        self.assertEqual(data["race_code"],"202610312307")
        self.assertEqual(data["bytes"],26)
        self.assertFalse(data["exhibition_verified"])
        self.assertFalse(data["entry_verified"])
        self.assertIn("jcd=23",data["source_url"])

    def test_reject_invalid_and_empty(self):
        with self.assertRaises(ValueError):
            probe("20261031",25,1,fetch=lambda url:b"x")
        with self.assertRaises(ValueError):
            probe("20261031",23,1,fetch=lambda url:b"")

if __name__=="__main__":
    unittest.main()
