"""No unjustified pre-cutoff certification from Git metadata."""
import unittest
from unittest.mock import patch
from research_git_first_seen_audit import audit_one

class GitAuditTests(unittest.TestCase):
    def test_missing_history_does_not_certify(self):
        import tempfile, json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"202610271201.json"
            p.write_text(json.dumps({"race_code":"202610271201",
                "cutoff_jst":"2026-10-27T12:00:00+09:00",
                "generated_at":"2026-10-27T11:00:00+09:00"}))
            with patch("research_git_first_seen_audit._git", return_value=""):
                self.assertFalse(audit_one(p)["prospective_verified"])

if __name__=="__main__":
    unittest.main()
