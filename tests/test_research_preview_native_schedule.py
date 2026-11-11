"""Contract: retime ONE existing research-only Cron, preserve 5-min coverage.

This validates configuration only. Actual GitHub schedule launches remain
independent runtime evidence and may be delayed or dropped by GitHub.
"""
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / ".github/workflows/research-live-preview-evidence.yml"
JST = timezone(timedelta(hours=9))


class ResearchPreviewNativeScheduleTests(unittest.TestCase):
    def test_exactly_one_five_minute_offpeak_cron_preserves_daylight_coverage(self):
        workflow = PATH.read_text(encoding="utf-8")
        crons = re.findall(r"(?m)^\s*- cron: ['\"]([^'\"]+)['\"]\s*$", workflow)
        self.assertEqual(crons, ["1-56/5 0-12 * * *"])
        minutes = list(range(1, 57, 5))
        self.assertEqual(len(minutes), 12)
        self.assertNotIn(0, minutes)
        self.assertEqual(minutes[-1], 56)
        hours = range(0, 13)
        local = [datetime(2026, 11, 11, h, m, tzinfo=timezone.utc).astimezone(JST)
                 for h in hours for m in minutes]
        self.assertEqual(len(local), 13 * 12)
        self.assertEqual((local[0].hour, local[0].minute), (9, 1))
        self.assertEqual((local[-1].hour, local[-1].minute), (21, 56))
        self.assertTrue(all(9 <= at.hour < 22 for at in local))
        self.assertTrue(all(after - before == timedelta(minutes=5)
                            for before, after in zip(local, local[1:])))

    def test_offpeak_shift_never_changes_receipt_gate_or_adds_dispatch(self):
        workflow = PATH.read_text(encoding="utf-8")
        self.assertIn("  workflow_dispatch:\n", workflow)
        self.assertIn("  schedule:\n", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("  contents: read", workflow)
        self.assertIn("python -m scripts.capture_joint_preview_batch", workflow)
        self.assertIn("python -m scripts.audit_official_forecast_consumption", workflow)
        self.assertIn("python scripts/collect_live_preview_evidence.py", workflow)
        self.assertNotIn("git push", workflow)
        self.assertNotIn("formal_t12_certified=true", workflow)
        self.assertIn("test_research_preview_native_schedule.py", workflow)


if __name__ == "__main__":
    unittest.main()
