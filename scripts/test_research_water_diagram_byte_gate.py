"""Offline tests for fail-closed BOAT RACE diagram byte receipts."""
from __future__ import annotations

import hashlib
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

try:
    from scripts.research_water_diagram_byte_gate import (
        PNG_SIG, check_source_url, make_receipt, official_diagram_url,
        png_dimensions, receipt_for_file, verify_receipt_against_bytes)
except ModuleNotFoundError:
    from research_water_diagram_byte_gate import (
        PNG_SIG, check_source_url, make_receipt, official_diagram_url,
        png_dimensions, receipt_for_file, verify_receipt_against_bytes)


def chunk(name: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data) & 0xffffffff)


def valid_png() -> bytes:
    ihdr = struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0)
    raw_rgb = b"\x00\xff\x00\x00\x00\xff\x00"
    return PNG_SIG + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw_rgb)) + chunk(b"IEND", b"")


class DiagramByteGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = official_diagram_url("21")
        self.raw = valid_png()

    def test_png_receipt_is_only_local_integrity(self):
        r = make_receipt("21", self.source, self.raw, claimed_page_revision="2023-01-01")
        self.assertEqual(r["png_raw_sha256"], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(r["png_dimensions_px"], {"width": 2, "height": 1})
        self.assertTrue(r["file_integrity_verified"])
        self.assertFalse(r["source_url_claim_cryptographically_verified"])
        self.assertFalse(r["official_http_original_response_proven"])
        self.assertFalse(r["t12_weather_input_verified"])
        verify_receipt_against_bytes(r, self.raw)

    def test_all_venues_canonical(self):
        for n in range(1, 25):
            url = official_diagram_url(f"{n:02d}")
            check_source_url(f"{n:02d}", url)
        with self.assertRaises(ValueError):
            official_diagram_url("25")

    def test_wrong_venue_or_redirect_url_rejected(self):
        for url in (official_diagram_url("02"), "http://www.boatrace.jp/static_extra/pc/images/img_water1_21.png", "https://evil.example/water.png", self.source + "?modified=1"):
            with self.assertRaises(ValueError):
                make_receipt("21", url, self.raw)

    def test_html_rejected(self):
        with self.assertRaises(ValueError):
            make_receipt("21", self.source, b"<html>oops</html>")

    def test_corrupted_crc_rejected(self):
        raw = bytearray(self.raw)
        raw[16] ^= 1
        with self.assertRaises(ValueError):
            png_dimensions(bytes(raw))

    def test_missing_iend_and_trailing_data_rejected(self):
        for raw in (self.raw[:-12], self.raw + b"!", self.raw[:8]):
            with self.assertRaises(ValueError):
                png_dimensions(raw)

    def test_false_certification_receipt_rejected(self):
        r = make_receipt("21", self.source, self.raw)
        r["same_race_official_arrow_original_sha_verified"] = True
        with self.assertRaises(ValueError):
            verify_receipt_against_bytes(r, self.raw)

    def test_tampered_bytes_rejected(self):
        r = make_receipt("21", self.source, self.raw)
        with self.assertRaises(ValueError):
            verify_receipt_against_bytes(r, self.raw + b"!")

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            original = base / "real.png"
            original.write_bytes(self.raw)
            shortcut = base / "alias.png"
            shortcut.symlink_to(original)
            with self.assertRaises(ValueError):
                receipt_for_file("21", self.source, shortcut)
            r = receipt_for_file("21", self.source, original)
            self.assertEqual(r["png_raw_length"], len(self.raw))

    def test_bad_revision_rejected(self):
        with self.assertRaises(ValueError):
            make_receipt("21", self.source, self.raw, claimed_page_revision="Nov-9-2026")


if __name__ == "__main__":
    unittest.main()
