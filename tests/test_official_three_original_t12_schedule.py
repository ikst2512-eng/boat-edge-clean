"""Contract: one calendar-day near-cutoff observation, never production prediction."""
import unittest
from pathlib import Path


class NearCutoffScheduleTests(unittest.TestCase):
    def test_cron_is_narrow_and_targets_same_exact_race(self):
        workflow = Path(".github/workflows/official-three-original-t12-observation.yml").read_text()
        observer = Path("scripts/observe_three_official_t12_originals.py").read_text()
        self.assertIn("schedule:", workflow)
        self.assertIn("cron: '20,25,30,40,48,50,51 6 3 11 *'", workflow)
        self.assertIn('|| \'["202611030212"]\'', workflow)
        self.assertIn("format('-{0}', matrix.race_code)", workflow)
        self.assertIn("202611030212", workflow)
        for race in ("202611030612", "202611030412", "202611030104"):
            self.assertIn(race, workflow)
        self.assertIn("github.event_name == 'pull_request'", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("matrix.race_code", workflow)
        self.assertIn("strategy:", workflow)
        self.assertIn("fail-fast: false", workflow)
        for audited_path in (
            "scripts/audit_official_racelist_receipt.py",
            "scripts/audit_three_official_t12_originals.py",
            "scripts/audit_joint_official_receipts.py",
            "scripts/inspect_official_racelist_registrations.py",
            "scripts/inspect_official_beforeinfo_json.py",
        ):
            self.assertIn(audited_path, workflow)
        self.assertIn("cron: '8,14,18 7 3 11 *'", workflow)
        self.assertIn("github.event.schedule", workflow)
        self.assertIn('202611030104', workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("datetime.now(JST)", observer)
        self.assertIn('if now().strftime("%Y%m%d") != day:', observer)
        self.assertIn("now() + timedelta(seconds=60) >= cutoff", observer)
        self.assertIn('"full_t12_source_certified": False', observer)
        self.assertIn('"forecast_usable": False', observer)
        self.assertNotIn("git push", workflow)


if __name__ == "__main__":
    unittest.main()
