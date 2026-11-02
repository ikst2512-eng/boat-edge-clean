import json
import tempfile
import unittest
from pathlib import Path
from scripts.capture_official_beforeinfo_json import capture


def payload(extime=""):
    return json.dumps({"maindata": {
        "hd": "20261102", "jcd": "15", "rno": "11", "deadline": "20:06",
        "teiinfolist": [{"teino": str(i), "extime": extime} for i in range(1, 7)],
        "sttenjiinfolist": []
    }}).encode()


class OfficialJSONCaptureTests(unittest.TestCase):
    def test_six_racecards_without_exhibition_saved_as_noneligible(self):
        with tempfile.TemporaryDirectory() as root:
            out=capture("202611021511",root,"attempt1",fetch=lambda url:payload())
            self.assertEqual(out["status"],"official_json_observed_not_t12_certified")
            self.assertFalse(out["exhibition_time_nonempty_six"])
            self.assertFalse(out["forecast_usable"])
            self.assertFalse(out["t12_eligible"])
            saved=Path(root)/"observations/attempt1/20261102/202611021511"
            self.assertEqual((saved/"beforeinfo.json").read_bytes(),payload())
            again=capture("202611021511",root,"attempt1",fetch=lambda url:payload())
            self.assertEqual(again["status"],"official_json_probe_failed")
            self.assertEqual(again["error"],"FileExistsError")
            self.assertEqual((saved/"beforeinfo.json").read_bytes(),payload())

    def test_invalid_source_identity_not_archived(self):
        with tempfile.TemporaryDirectory() as root:
            bad=json.loads(payload())
            bad["maindata"]["rno"]="12"
            out=capture("202611021511",root,"attempt2",
                        fetch=lambda url:json.dumps(bad).encode())
            self.assertEqual(out["status"],"official_json_probe_failed")
            self.assertFalse(list(Path(root).rglob("beforeinfo.json")))

    def test_malformed_json_and_bad_race_code_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            out=capture("202611021511",root,"attempt1",fetch=lambda url:b"<html>not JSON</html>")
            self.assertEqual(out["status"],"official_json_probe_failed")
            self.assertFalse(out["forecast_usable"])
            with self.assertRaises(ValueError):
                capture("202611029911",root,"attempt2",fetch=lambda url:payload())

if __name__=="__main__":
    unittest.main()
