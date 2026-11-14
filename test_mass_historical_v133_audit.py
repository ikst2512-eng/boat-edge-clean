"""Independent regression for legacy 79-sample audit + separate CLEAN baselines."""
import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.audit_frozen_models_mass_history import (
    PINNED_OLD_RESULTS_COMMIT, audit_clean_versioned, audit_legacy,
    blob_sha, checked_legacy_forecast, checked_result, classify_saved_ticket_stage,
    validate_rank_diagnostics, blank_rank_diagnostics,
)

ROOT = Path(__file__).resolve().parent
KEY = "20261008-01-04"
OFFICIAL = {
    "schema_version": "boat-edge-site-result-v109",
    "race_key": KEY,
    "status": "confirmed",
    "fetched_at": "2026-10-08T16:55:17+09:00",
    "source": "https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261008&jcd=01&rno=4",
    "finish_order": [5, 6, 4],
    "trifecta": "5-6-4",
    "trifecta_payout_yen_per_100": 3740,
}


class HistoricalMassAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        src = ROOT / "legacy_preservation" / "samples" / (KEY + ".json")
        dst = self.root / "legacy_preservation" / "samples"
        dst.mkdir(parents=True)
        shutil.copyfile(src, dst / src.name)
        (dst / "manifest.json").write_text(json.dumps({"records": [
            {"archive_path": "legacy_preservation/samples/" + src.name,
             "source_blob_sha": blob_sha(src.read_bytes())}
        ]}), encoding="utf-8")

    def test_original_old_v133_is_historical_and_not_new_12_point_version(self):
        pred = json.loads((self.root / "legacy_preservation" / "samples"
                           / (KEY + ".json")).read_text(encoding="utf-8"))
        deadline, modes = checked_legacy_forecast(pred, KEY)
        self.assertEqual(len(modes["narrow"]), 3)
        self.assertEqual(len(modes["hit"]), 10)
        self.assertEqual(len(modes["balance"]), 10)
        self.assertIn(len(modes["hole"]), (12, 15, 18))
        self.assertEqual(checked_result(OFFICIAL, KEY, deadline), "5-6-4")
        report = audit_legacy(self.root, fetch=lambda key: (dict(OFFICIAL), "1"*40))
        self.assertEqual(report["source_result_commit"], PINNED_OLD_RESULTS_COMMIT)
        self.assertFalse(report["registered_before_results_independently_proven"])
        self.assertEqual(report["overall"]["evaluated"], 1)
        self.assertEqual(report["overall"]["modes"]["hole"]["hits"], 1)
        self.assertEqual(len(report["race_audit"]), 1)
        self.assertEqual(report["race_audit"][0]["winning_ticket"], "5-6-4")
        self.assertEqual(report["saved_ticket_rank_diagnostics"]["evaluated"], 1)
        self.assertEqual(report["saved_ticket_rank_diagnostics"]["by_mode"]["hole"]["topn_stages"]["10"]["exact"], 1)
        self.assertEqual(report["race_audit"][0]["saved_ticket_stage_diagnostics"]["hit"]["topn_stages"]["10"], "third_absent_given_head_second")

    def test_frozen_ticket_stage_attribution_includes_only_ranked_selections(self):
        tickets = ["2-4-5", "1-4-5", "1-2-6", "1-2-3"]
        self.assertEqual(classify_saved_ticket_stage(tickets, "1-2-3", 1), "head_absent")
        self.assertEqual(classify_saved_ticket_stage(tickets, "1-2-3", 2), "second_absent_given_head")
        self.assertEqual(classify_saved_ticket_stage(tickets, "1-2-3", 3), "third_absent_given_head_second")
        self.assertEqual(classify_saved_ticket_stage(tickets, "1-2-3", 10), "exact")
        self.assertEqual(classify_saved_ticket_stage(["2-1-3"], "1-2-3", 10), "head_absent")

    def test_diagnostics_refuse_mismatched_existing_topn(self):
        diag = blank_rank_diagnostics()
        from scripts.audit_frozen_models_mass_history import add_rank_diagnostics, add_record, blank_group
        modes = {m: ["1-2-3"] for m in ("narrow", "hit", "balance", "hole")}
        add_rank_diagnostics(diag, modes, "1-2-3")
        group = blank_group()
        add_record(group, modes, "1-2-3")
        self.assertIs(validate_rank_diagnostics(diag, group), diag)
        diag["by_mode"]["hit"]["topn_stages"]["10"]["exact"] = 0
        with self.assertRaisesRegex(ValueError, "diagnostic_topn_mismatch"):
            validate_rank_diagnostics(diag, group)

    def test_result_after_forecast_necessary_and_bad_source_rejected(self):
        deadline, _ = checked_legacy_forecast(
            json.loads((self.root / "legacy_preservation" / "samples"
                        / (KEY+".json")).read_text(encoding="utf-8")), KEY)
        early = dict(OFFICIAL, fetched_at="2026-10-08T16:45:00+09:00")
        with self.assertRaisesRegex(ValueError, "published_before_deadline"):
            checked_result(early, KEY, deadline)
        fake = dict(OFFICIAL, source="http://example.com/forged")
        with self.assertRaisesRegex(ValueError, "invalid_official_result_record"):
            checked_result(fake, KEY, deadline)
        wrong = dict(OFFICIAL, trifecta="1-2-3")
        with self.assertRaisesRegex(ValueError, "invalid_official_result_record"):
            checked_result(wrong, KEY, deadline)

    def test_tampered_forecast_does_not_count_as_miss(self):
        src = self.root / "legacy_preservation" / "samples" / (KEY+".json")
        src.write_bytes(src.read_bytes()+b"\n")
        result = audit_legacy(self.root, fetch=lambda key: self.fail("must not fetch"))
        self.assertEqual(result["overall"]["evaluated"], 0)
        self.assertEqual(result["excluded"]["legacy_archive_changed_since_original"], 1)

    def test_clean_baseline_separate_from_old_v133(self):
        forecast = self.root/"four_mode_forecasts"
        results = self.root/"confirmed_results"
        forecast.mkdir()
        results.mkdir()
        code="202610280101"
        shutil.copyfile(ROOT/"four_mode_forecasts"/(code+".json"), forecast/(code+".json"))
        shutil.copyfile(ROOT/"confirmed_results"/(code+".json"), results/(code+".json"))
        report = audit_clean_versioned(self.root)
        self.assertEqual(report["all_forecasts_scanned"], 1)
        self.assertEqual(report["with_result_file"], 1)
        self.assertTrue(report["cannot_directly_compare_to_legacy_due_to_different_dates"])
        self.assertEqual(report["by_model_version"]["CLEAN_FOUR_MODES_V1_UNCALIBRATED"]["evaluated"], 1)


if __name__=="__main__":
    unittest.main()
