"""Offline failure/acceptance tests. These tests never make a network call."""
import hashlib
import io
import tempfile
import unittest
import urllib.error
import zlib
import struct
from pathlib import Path

try:
    from scripts.research_water_diagram_http_receipt import fetch_once, write_bundle
    from scripts.research_water_diagram_byte_gate import official_diagram_url
except ModuleNotFoundError:
    from research_water_diagram_http_receipt import fetch_once, write_bundle
    from research_water_diagram_byte_gate import official_diagram_url


def chunk(name, data):
    return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)


def png():
    ihdr = struct.pack('>IIBBBBB', 2, 1, 8, 2, 0, 0, 0)
    pix = b'\0\xff\0\0\0\xff\0'
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(pix)) + chunk(b'IEND', b'')


class MockResponse:
    def __init__(self, raw=None, status=200, url=None, headers=None):
        self.raw = io.BytesIO(png() if raw is None else raw)
        self.status = status
        self.url = url or official_diagram_url('21')
        self.headers = {'Content-Type': 'image/png', 'Content-Length': str(len(self.raw.getvalue()))}
        if headers:
            self.headers.update(headers)

    def geturl(self): return self.url
    def read(self, n=-1): return self.raw.read(n)
    def __enter__(self): return self
    def __exit__(self, *_): self.raw.close()


def opener_of(**kwargs):
    def opener(request, timeout):
        assert request.full_url == official_diagram_url('21')
        assert timeout == 15
        return MockResponse(**kwargs)
    return opener


class HttpReceiptTests(unittest.TestCase):
    def setUp(self):
        self.clock = iter(['2026-11-09T10:30:00+00:00', '2026-11-09T10:30:01+00:00']).__next__

    def test_http200_records_only_direct_client_receipt(self):
        raw, r = fetch_once('21', opener=opener_of(), timestamp=self.clock)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), r['png_sha256'])
        self.assertEqual(r['png_dimensions'], [2, 1])
        self.assertFalse(r['source_attested_by_independent_service'])
        self.assertFalse(r['diagram_bearing_independently_verified'])
        self.assertFalse(r['same_race_wind_arrow_original_verified'])
        self.assertFalse(r['t12_beforeinfo_source_verified'])
        self.assertFalse(r['production_wind_use_authorized'])

    def test_non200_status_rejected(self):
        with self.assertRaisesRegex(ValueError, 'http_status_not_200'):
            fetch_once('21', opener=opener_of(status=403), timestamp=self.clock)

    def test_cross_host_or_venue_redirect_rejected(self):
        for url in ['https://thirdparty.example/a.png', official_diagram_url('02')]:
            with self.assertRaises(ValueError):
                fetch_once('21', opener=opener_of(url=url))

    def test_html_body_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unexpected_content_type'):
            fetch_once('21', opener=opener_of(raw=b'<html>error</html>',headers={'Content-Type':'text/html'}))

    def test_gzip_content_encoding_rejected(self):
        with self.assertRaisesRegex(ValueError, 'compressed_or_transformed'):
            fetch_once('21', opener=opener_of(headers={'Content-Encoding':'gzip'}))

    def test_content_length_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'oversize_or_incomplete'):
            fetch_once('21', opener=opener_of(headers={'Content-Length':'20000'}))

    def test_bad_png_crc_rejected(self):
        bad = bytearray(png());bad[-5] ^= 1
        with self.assertRaises(ValueError):
            fetch_once('21', opener=opener_of(raw=bytes(bad)))

    def test_crc_valid_png_but_invalid_zlib_rejected_over_http(self):
        ihdr = struct.pack('>IIBBBBB', 2, 1, 8, 2, 0, 0, 0)
        false_png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
                     + chunk(b'IDAT', b'not-zlib') + chunk(b'IEND', b''))
        with self.assertRaisesRegex(ValueError, 'png_invalid_zlib_stream'):
            fetch_once('21', opener=opener_of(raw=false_png))

    def test_valid_crc_fake_png_fails_bundle_before_any_write(self):
        raw, receipt = fetch_once('21', opener=opener_of())
        ihdr = struct.pack('>IIBBBBB', 2, 1, 8, 2, 0, 0, 0)
        forged = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
                  + chunk(b'IDAT', b'not-zlib') + chunk(b'IEND', b''))
        receipt['png_sha256'] = hashlib.sha256(forged).hexdigest()
        receipt['png_bytes'] = len(forged)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'png_invalid_zlib_stream'):
                write_bundle(Path(d), forged, receipt)
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_write_saved_raw_bytes_and_metadata_never_certified(self):
        raw,r = fetch_once('21',opener=opener_of(),timestamp=self.clock)
        with tempfile.TemporaryDirectory() as d:
            folder=write_bundle(Path(d),raw,r)
            self.assertTrue((folder/'COMPLETE').is_file())
            self.assertEqual((folder/'original_response.png').read_bytes(),raw)
            with self.assertRaises(FileExistsError):
                write_bundle(Path(d),raw,r)

    def test_reject_tampered_receipt_before_write(self):
        raw,r = fetch_once('21',opener=opener_of())
        r['png_sha256']='0'*64
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'receipt_not_matching'):
                write_bundle(Path(d),raw,r)
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_false_heading_and_t12_certification_rejected(self):
        raw, r = fetch_once('21', opener=opener_of())
        with tempfile.TemporaryDirectory() as d:
            for key in ('diagram_bearing_independently_verified',
                        'same_race_wind_arrow_original_verified',
                        't12_beforeinfo_source_verified',
                        'production_wind_use_authorized'):
                fake = {**r, key: True}
                with self.assertRaisesRegex(ValueError, 'false_success'):
                    write_bundle(Path(d), raw, fake)

    def test_sha_consistent_fake_png_rejected_on_write(self):
        raw, r = fetch_once('21', opener=opener_of())
        fake = b'<html>not a PNG</html>'
        r['png_sha256'] = hashlib.sha256(fake).hexdigest()
        r['png_bytes'] = len(fake)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                write_bundle(Path(d), fake, r)
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_png_metadata_substitution_rejected_on_write(self):
        raw, r = fetch_once('21', opener=opener_of())
        with tempfile.TemporaryDirectory() as d:
            for change in ({'png_bytes': 0}, {'png_dimensions': [22, 11]},
                           {'content_type': 'text/html'}, {'content_encoding': 'gzip'}):
                with self.assertRaisesRegex(ValueError, 'receipt_length_or_png_dimensions_inconsistent|receipt_content_type_or_encoding_inconsistent'):
                    write_bundle(Path(d), raw, {**r, **change})
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_untrusted_timestamp_cannot_change_directory(self):
        raw, r = fetch_once('21', opener=opener_of())
        r['response_finished_utc'] = '../forged'
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'untrusted_receipt_timestamp'):
                write_bundle(Path(d), raw, r)
            self.assertFalse(list(Path(d).iterdir()))

    def test_refuse_symlink_output_root(self):
        raw,r = fetch_once('21',opener=opener_of())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);actual=root/'real';actual.mkdir(); alias=root/'alias';alias.symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'output_root_must_be_existing'):
                write_bundle(alias,raw,r)


if __name__ == '__main__': unittest.main()
