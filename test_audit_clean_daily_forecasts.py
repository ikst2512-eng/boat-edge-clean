import json
import tempfile
import unittest
from pathlib import Path
from audit_clean_daily_forecasts import audit

class AuditFixtures(unittest.TestCase):
    def record(self):
        return {"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1","race_code":"202610290101",
          "generated_at_jst":"2026-10-29T06:00:00+09:00","deadline_jst":"2026-10-29T12:00:00+09:00",
          "source_sha256":{"title":"a"*64,"race_cards":"b"*64},
          "input_national_win_rates":[4,4.5,5,5.5,6,6.5],
          "modes":{k:{"tickets":[{"combo":"1-2-3"}]} for k in ("hit","balance","hole","narrow")}}
    def test_pending_not_counted_as_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"four_mode_forecasts"
            p.mkdir()
            (p/"202610290101.json").write_text(json.dumps(self.record()))
            x=audit(tmp,"20261029")
            self.assertEqual((x["archives"],x["structurally_valid"],x["awaiting_result_file"]),(1,1,1))
            self.assertFalse(x["git_first_add_audited"])
            self.assertFalse(x["official_result_verified"])
            self.assertFalse(x["actual_hit_rate_calculated"])
    def test_late_forecast_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"four_mode_forecasts"
            p.mkdir()
            r=self.record()
            r["generated_at_jst"]="2026-10-29T11:50:00+09:00"
            (p/"202610290101.json").write_text(json.dumps(r))
            self.assertEqual(audit(tmp,"20261029")["issues"][0]["issue"],"deadline_or_time")
    def test_missing_source_digest_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"four_mode_forecasts"
            p.mkdir()
            r=self.record()
            r["source_sha256"]["title"]=""
            (p/"202610290101.json").write_text(json.dumps(r))
            self.assertEqual(audit(tmp,"20261029")["issues"][0]["issue"],"missing_source_digest")
if __name__=="__main__":unittest.main()
