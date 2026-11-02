import fcntl
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.publish_official_receipt import publish_receipt


class PublishReceiptTests(unittest.TestCase):
    def test_publishes_complete_pair_and_blocks_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "observations" / "one"
            publish_receipt(dest, "beforeinfo.json", b"original", {"sha256": "abc"})
            self.assertEqual((dest / "beforeinfo.json").read_bytes(), b"original")
            self.assertTrue((dest / "manifest.json").exists())
            with self.assertRaises(FileExistsError):
                publish_receipt(dest, "beforeinfo.json", b"changed", {})
            self.assertEqual((dest / "beforeinfo.json").read_bytes(), b"original")

    def test_manifest_failure_leaves_no_partial_observation(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "observations" / "two"
            real_write_text = Path.write_text
            def broken_write_text(path, *args, **kwargs):
                if path.name == "manifest.json":
                    raise OSError("simulated disk failure")
                return real_write_text(path, *args, **kwargs)
            with patch.object(Path, "write_text", broken_write_text):
                with self.assertRaises(OSError):
                    publish_receipt(dest, "original.html", b"raw", {})
            self.assertFalse(dest.exists())
            self.assertFalse(list(dest.parent.glob(".receipt-*")))
            self.assertTrue(dest.with_name(dest.name + ".publish.lock").exists())

    def test_live_lock_rejects_second_writer(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "observation"
            lock = dest.with_name(dest.name + ".publish.lock")
            fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(FileExistsError):
                    publish_receipt(dest, "original.html", b"raw", {})
                self.assertFalse(dest.exists())
            finally:
                os.close(fd)

    def test_stale_unheld_lock_is_safe_to_reuse(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "observation"
            dest.with_name(dest.name + ".publish.lock").touch()
            publish_receipt(dest, "original.html", b"raw", {"status": "observed"})
            self.assertEqual((dest / "original.html").read_bytes(), b"raw")
            with self.assertRaises(FileExistsError):
                publish_receipt(dest, "original.html", b"changed", {})



if __name__ == "__main__":
    unittest.main()
