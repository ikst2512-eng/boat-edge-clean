import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.inspect_official_beforeinfo_html import inspect

class OfficialHTMLInventoryTests(unittest.TestCase):
    def test_labels_are_diagnostic_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/"20261101"/"202611010708"
            d.mkdir(parents=True)
            raw="<html><body>展示タイム 6.89 <script>ST fake</script>スタート展示 ST チルト</body></html>".encode()
            (d/"beforeinfo.html").write_bytes(raw)
            (d/"manifest.json").write_text(json.dumps({"source":"official_beforeinfo_html","race_code":"202611010708","forecast_usable":False,"sha256":hashlib.sha256(raw).hexdigest(),"request_started_at_jst":"2026-11-01T11:59:59+09:00","received_at_jst":"2026-11-01T12:00:00+09:00","http_status":200,"status":"raw_http_observed_not_t12_certified","t12_eligible":False,"complete_six_lanes":"unverified","url":"https://www.boatrace.jp/owsp/sp/race/beforeinfo?hd=20261101&jcd=07&rno=8","response_url":"https://www.boatrace.jp/owsp/sp/race/beforeinfo?hd=20261101&jcd=07&rno=8"}))
            result=inspect(d)
            self.assertTrue(result["label_positions"]["展示タイム"])
            self.assertEqual(result["request_started_at_jst"],"2026-11-01T11:59:59+09:00")
            self.assertEqual(result["received_at_jst"],"2026-11-01T12:00:00+09:00")
            self.assertEqual(result["http_elapsed_seconds"],1.0)
            self.assertTrue(result["label_context"]["展示タイム"])
            self.assertIn("展示タイム 6.89", result["label_context"]["展示タイム"][0]["nearby"][0])
            self.assertNotIn("ST fake", str(result["label_context"]))
            self.assertFalse(result["t12_eligible"])
            self.assertEqual(result["six_lane_values"],"unverified")
            manifest=json.loads((d/"manifest.json").read_text())
            manifest["request_started_at_jst"]="2026-11-01T12:00:01+09:00"
            (d/"manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"chronology"):inspect(d)
            manifest["request_started_at_jst"]="2026-11-01T11:59:59+09:00"
            manifest["response_url"]="https://www.boatrace.jp/owsp/sp/race/beforeinfo?hd=20261101&jcd=07&rno=9"
            (d/"manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"source URL race identity"):inspect(d)
            manifest["response_url"]=manifest["url"]
            manifest["received_at_jst"]="2026-11-01T12:00:00+00:00"
            (d/"manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"receipt metadata"):inspect(d)
            manifest["received_at_jst"]="2026-11-01T12:00:00+09:00"
            manifest["t12_eligible"]=True
            (d/"manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"non-certified"):inspect(d)
            manifest["t12_eligible"]=False
            manifest["race_code"]="202611010709"
            (d/"manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"race identity"):inspect(d)
            manifest["race_code"]="202611010708"
            manifest["bytes"]=len(raw)+1
            (d/"manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"byte length"):inspect(d)
            manifest["bytes"]=len(raw)
            (d/"manifest.json").write_text(json.dumps(manifest))
            (d/"beforeinfo.html").write_bytes(b"tampered")
            with self.assertRaises(ValueError):inspect(d)

    def test_inert_markup_cannot_forge_official_labels(self):
        from scripts.inspect_official_beforeinfo_html import VisibleText, LABELS
        html = """<html><head><title>展示タイム fake</title></head>
        <body><template>進入 fake</template><noscript>ST fake</noscript>
        <svg><text>風速 fake</text></svg><iframe>波高 fake</iframe>
        <style>チルト fake</style><script>スタート展示 fake</script>
        <p>展示タイム 6.89</p></body></html>"""
        parser = VisibleText()
        parser.feed(html)
        text = " ".join(parser.fragments)
        self.assertIn("展示タイム 6.89", text)
        self.assertNotIn("fake", text)
        self.assertEqual(sum("展示タイム" in item for item in parser.fragments), 1)

if __name__=="__main__":unittest.main()
