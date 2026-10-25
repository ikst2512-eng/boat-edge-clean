import sys,unittest,tempfile,json,hashlib,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verified_receipt_adapter import verify

class ReceiptTests(unittest.TestCase):
    def test_fail_closed_even_valid_looking_receipt(self):
        body=b"<html><table><tr><td>exhibition</td></tr></table></html>"
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            root.joinpath("source.html").write_bytes(body)
            meta={
                "race_id":"202610250512",
                "url":"https://www.boatrace.jp/owpc/pc/race/beforeinfo?jcd=05&hd=20261025&rno=12",
                "source_sha256":hashlib.sha256(body).hexdigest(),
                "source_bytes":len(body),"http_status":200,"content_type":"text/html",
                "utc_start":"2026-10-25T06:44:00+00:00",
                "utc_end":"2026-10-25T06:44:02+00:00",
                "clock_attestation":"runner_local_only","scoring":"NOT_RUN"
            }
            root.joinpath("metadata.json").write_text(json.dumps(meta))
            # 15:00 JST cutoff: receipt at 15:44 JST is too late.
            with self.assertRaisesRegex(ValueError,"outside"):
                verify(root,"2026-10-25T15:00:00+09:00")
            # 16:00 JST cutoff: receipt 15:44, 16 minutes earlier, but
            # token safety alone is not a proven result-free attestation.
            with self.assertRaisesRegex(ValueError,"ATTESTATION_MISSING"):
                verify(root,"2026-10-25T16:00:00+09:00")
            root.joinpath("source.html").write_bytes(body+b"tampered")
            with self.assertRaisesRegex(ValueError,"hash"):
                verify(root,"2026-10-25T16:00:00+09:00")
            root.joinpath("source.html").write_bytes(body)
            meta["url"]="https://www.boatrace.jp/owpc/pc/race/beforeinfo?jcd=06&hd=20261025&rno=12"
            root.joinpath("metadata.json").write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError,"identity"):
                verify(root,"2026-10-25T16:00:00+09:00")

if __name__=="__main__": unittest.main()
