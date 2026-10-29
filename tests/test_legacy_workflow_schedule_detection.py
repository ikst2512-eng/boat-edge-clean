import unittest
from scripts.audit_legacy_workflow_dependencies import inspect

class LegacyWorkflowDetectionTests(unittest.TestCase):
    def test_schedule_and_manual_dispatch_recognized(self):
        a=".github/workflows/scheduled.yml"
        b=".github/workflows/manual.yml"
        rows=inspect([a,b],{a:"name: scheduled\non:\n  schedule:\n    - cron: '17 16 * * *'\n",b:"on:\n  workflow_dispatch:\n"})
        by_path={r["path"]:r for r in rows}
        self.assertTrue(by_path[a]["schedule"])
        self.assertFalse(by_path[a]["manual_dispatch"])
        self.assertTrue(by_path[b]["manual_dispatch"])
        self.assertFalse(by_path[b]["schedule"])

if __name__ == "__main__":
    unittest.main()
