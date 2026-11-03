"""Scheduled predeadline proof is not green merely because CSV requests worked."""
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from scripts.probe_today_beforeinfo import run

JST=ZoneInfo("Asia/Tokyo")
NOW=datetime(2026,11,4,17,30,tzinfo=JST)
CODE="202611041911"


def row(code=CODE, clock="18:00", observed="2026-11-04T17:20:00+09:00"):
    return {"レースコード":code,"締切時刻":clock,"取得日時":observed}


class TodayBeforeinfoProbeVerdictTests(unittest.TestCase):
    def test_scheduled_zero_matching_future_is_failure_not_green(self):
        # Three real HTTP CSV responses, but no future predeadline race.
        with patch("scripts.probe_today_beforeinfo._preview_rows",
                   side_effect=lambda kind,day: ([row(clock="17:00")],"a"*64)):
            with self.assertRaisesRegex(RuntimeError,"SCHEDULED_PREVIEW_NO_MATCHED_PREDEADLINE_RACES"):
                run(now=NOW,event_name="schedule",clock=lambda:NOW)

    def test_scheduled_zero_six_lane_verification_fails(self):
        with patch("scripts.probe_today_beforeinfo._preview_rows",
                   side_effect=lambda kind,day: ([row()],"a"*64)),patch(
                   "scripts.probe_today_beforeinfo._fetch_preview",
                   return_value=(None,{"status":"invalid_or_incomplete_exhibition"})):
            with self.assertRaisesRegex(RuntimeError,"SCHEDULED_PREVIEW_NO_VERIFIED_SIX_LANE"):
                run(now=NOW,event_name="schedule",clock=lambda:NOW)

    def test_scheduled_verified_six_lane_passes(self):
        preview={"racers":[{"lane":i} for i in range(1,7)],
                 "start_exhibition":[{"lane":i} for i in range(1,7)]}
        with patch("scripts.probe_today_beforeinfo._preview_rows",
                   side_effect=lambda kind,day: ([row()],"a"*64)),patch(
                   "scripts.probe_today_beforeinfo._fetch_preview",
                   return_value=(preview,{"status":"ok"})):
            result=run(now=NOW,event_name="schedule",clock=lambda:NOW)
        self.assertEqual(result["eligible_count"],1)
        self.assertEqual(result["verified_count"],1)
        self.assertEqual(result["verified_races"],[CODE])

    def test_adapter_completes_after_cutoff_and_cannot_verify_live(self):
        preview={"racers":[{"lane":i} for i in range(1,7)],
                 "start_exhibition":[{"lane":i} for i in range(1,7)]}
        after_cutoff=datetime(2026,11,4,18,0,tzinfo=JST)
        with patch("scripts.probe_today_beforeinfo._preview_rows",
                   side_effect=lambda kind,day: ([row()],"a"*64)),patch(
                   "scripts.probe_today_beforeinfo._fetch_preview",
                   return_value=(preview,{"status":"ok"})):
            with self.assertRaisesRegex(RuntimeError,"SCHEDULED_PREVIEW_NO_VERIFIED_SIX_LANE"):
                run(now=NOW,event_name="schedule",clock=iter([NOW,NOW,NOW,after_cutoff]).__next__)

    def test_predeadline_adapter_receipt_is_accepted(self):
        preview={"racers":[{"lane":i} for i in range(1,7)],
                 "start_exhibition":[{"lane":i} for i in range(1,7)]}
        just_before=datetime(2026,11,4,17,59,59,tzinfo=JST)
        with patch("scripts.probe_today_beforeinfo._preview_rows",
                   side_effect=lambda kind,day: ([row()],"a"*64)),patch(
                   "scripts.probe_today_beforeinfo._fetch_preview",
                   return_value=(preview,{"status":"ok"})):
            result=run(now=NOW,event_name="schedule",clock=lambda:just_before)
        self.assertEqual(result["verified_count"],1)

    def test_new_snapshot_during_http_fetch_is_not_falsely_future(self):
        # Scan started at 17:30, source HTTP returned at 17:31. A 17:30:30
        # source snapshot is valid by source receipt, though newer than start.
        received=datetime(2026,11,4,17,31,tzinfo=JST)
        source_row=row(observed="2026-11-04T17:30:30+09:00")
        preview={"racers":[{"lane":i} for i in range(1,7)],
                 "start_exhibition":[{"lane":i} for i in range(1,7)]}
        with patch("scripts.probe_today_beforeinfo._preview_rows",
                   side_effect=lambda kind,day: ([source_row],"a"*64)),patch(
                   "scripts.probe_today_beforeinfo._fetch_preview",
                   return_value=(preview,{"status":"ok"})):
            result=run(now=NOW,event_name="schedule",clock=lambda:received)
        self.assertEqual(result["eligible_count"],1)
        self.assertEqual(result["verified_count"],1)

    def test_source_snapshot_newer_than_http_receipt_rejected(self):
        received=datetime(2026,11,4,17,31,tzinfo=JST)
        source_row=row(observed="2026-11-04T17:31:01+09:00")
        with patch("scripts.probe_today_beforeinfo._preview_rows",
                   side_effect=lambda kind,day: ([source_row],"a"*64)):
            with self.assertRaisesRegex(RuntimeError,"SCHEDULED_PREVIEW_NO_MATCHED_PREDEADLINE_RACES"):
                run(now=NOW,event_name="schedule",clock=lambda:received)

    def test_source_receipt_at_cutoff_cannot_count_as_live(self):
        received=datetime(2026,11,4,18,0,tzinfo=JST)
        with patch("scripts.probe_today_beforeinfo._preview_rows",
                   side_effect=lambda kind,day: ([row()],"a"*64)):
            with self.assertRaisesRegex(RuntimeError,"SCHEDULED_PREVIEW_NO_MATCHED_PREDEADLINE_RACES"):
                run(now=NOW,event_name="schedule",clock=lambda:received)

    def test_no_source_is_explicit_failure_on_schedule(self):
        with patch("scripts.probe_today_beforeinfo._preview_rows",
                   side_effect=OSError("source down")):
            with self.assertRaisesRegex(RuntimeError,"SCHEDULED_PREVIEW_ALL_SOURCES_UNAVAILABLE"):
                run(now=NOW,event_name="schedule",clock=lambda:NOW)

    def test_manual_diagnostics_can_report_no_evidence_without_fake_success(self):
        with patch("scripts.probe_today_beforeinfo._preview_rows",
                   side_effect=lambda kind,day: ([row(clock="17:00")],"a"*64)):
            result=run(now=NOW,event_name="workflow_dispatch",clock=lambda:NOW)
        self.assertEqual(result["verified_count"],0)
        self.assertEqual(result["eligible_count"],0)


if __name__ == "__main__":
    unittest.main()
