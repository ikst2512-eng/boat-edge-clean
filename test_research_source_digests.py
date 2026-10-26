"""Synthetic source payload only: proves byte-level digest recording, not accuracy."""
import hashlib
import unittest
from unittest.mock import patch
import research_model as model


class SourceResponse:
    status = 200
    def __init__(self, raw):
        self.raw = raw
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, _limit):
        return self.raw


class SourceDigestTests(unittest.TestCase):
    def test_hash_is_of_original_response_bytes(self):
        raw = b"\xef\xbb\xbfa,b\r\n1,2\r\n"
        with patch.object(model, "urlopen", return_value=SourceResponse(raw)):
            rows, received_at, digest = model.read_rows(model.BASE + "title/2026/10/27.csv")
        self.assertEqual(rows, [{"a": "1", "b": "2"}])
        self.assertIsNotNone(received_at.tzinfo)
        self.assertEqual(digest, hashlib.sha256(raw).hexdigest())

    def test_rejects_untrusted_source(self):
        with self.assertRaises(ValueError):
            model.read_rows("https://example.invalid/data.csv")


if __name__ == "__main__":
    unittest.main()
