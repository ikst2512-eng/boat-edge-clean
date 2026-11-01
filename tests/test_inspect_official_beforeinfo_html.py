import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.inspect_official_beforeinfo_html import inspect

class OfficialHTMLInventoryTests(unittest.TestCase):
    def test_labels_are_diagnostic_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            raw="<html><body>展示タイム 6.89 <script>ST fake</script>スタート展示 ST チルト</body></html>".encode()
            (d/"beforeinfo.html").write_bytes(raw)
            (d/"manifest.json").write_text(json.dumps({"source":"official_beforeinfo_html","race_code":"202611010708","forecast_usable":False,"sha256":hashlib.sha256(raw).hexdigest()}))
            result=inspect(d)
            self.assertTrue(result["label_positions"]["展示タイム"])
            self.assertFalse(result["t12_eligible"])
            self.assertEqual(result["six_lane_values"],"unverified")
            (d/"beforeinfo.html").write_bytes(b"tampered")
            with self.assertRaises(ValueError):inspect(d)

if __name__=="__main__":unittest.main()
