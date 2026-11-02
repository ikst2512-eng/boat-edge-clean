"""Exercise an actual SIGKILL while a receipt is only partially staged."""
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.publish_official_receipt import publish_receipt
from scripts.audit_joint_official_receipts import audit_pair


class CrashRecoveryTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "requires POSIX signal and flock")
    def test_sigkill_during_manifest_write_does_not_publish_partial_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "observations" / "attempt" / "20261102" / "202611021512"
            source = """
import os, signal, sys
from pathlib import Path
from scripts.publish_official_receipt import publish_receipt
dest = Path(sys.argv[1])
real_write = Path.write_text
def crash_on_manifest(path, *args, **kwargs):
    if path.name == 'manifest.json':
        os.kill(os.getpid(), signal.SIGKILL)
    return real_write(path, *args, **kwargs)
Path.write_text = crash_on_manifest
publish_receipt(dest, 'original.html', b'raw-original', {'status': 'observed'})
"""
            completed = subprocess.run(
                [sys.executable, "-c", source, str(dest)],
                capture_output=True, text=True, timeout=15)
            self.assertEqual(completed.returncode, -signal.SIGKILL)
            self.assertFalse(dest.exists(), "incomplete receipt became visible")
            lock = dest.with_name(dest.name + ".publish.lock")
            self.assertTrue(lock.exists(), "crash simulation never acquired lock")
            with self.assertRaises((OSError, ValueError, KeyError, FileNotFoundError)):
                audit_pair(dest, dest)
            # The kernel has released the dead process's flock. An independent
            # retry can publish a complete pair under the same destination.
            publish_receipt(dest, "original.html", b"recovered", {"status": "observed"})
            self.assertEqual((dest / "original.html").read_bytes(), b"recovered")
            self.assertTrue((dest / "manifest.json").exists())
            with self.assertRaises(FileExistsError):
                publish_receipt(dest, "original.html", b"overwrite", {})


if __name__ == "__main__":
    unittest.main()
