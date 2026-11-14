"""The official-original bridge never infers that a frozen forecast used a source."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.audit_three_official_t12_originals import audit_three_originals
from scripts.audit_official_forecast_consumption import audit_batch, jst, snapshot_timing
from test_audit_three_official_t12_originals import ThreeOriginalAuditTests, RACE, DEADLINE


class OfficialForecastConsumptionTests(unittest.TestCase):
    def setup_sources(self, root):
        root = Path(root)
        card, before, odds = ThreeOriginalAuditTests().make(root)
        target = root / "observations" / "racelist_demo"
        card.parents[1].rename(target)
        card = target / RACE[:8] / RACE
        before_target = root / "observations" / "before_demo" / RACE[:8] / RACE
        odds_target = root / "observations" / "odds_demo" / RACE[:8] / RACE
        before_target.parent.mkdir(parents=True)
        odds_target.parent.mkdir(parents=True)
        before.rename(before_target)
        odds.rename(odds_target)
        return card, before_target, odds_target

    @staticmethod
    def write_forecast(root, generated="2026-11-02T21:20:40+09:00"):
        folder = Path(root) / "prospective_predictions"
        folder.mkdir(exist_ok=True)
        path = folder / (RACE + ".json")
        forecast = {
            "race_code": RACE, "status": "prospective_candidate",
            "formal": False, "scoring": False, "validated": False,
            "generated_at": generated,
            "source_title_received_jst": "2026-11-02T21:19:00+09:00",
            "source_cards_received_jst": "2026-11-02T21:19:00+09:00",
            "source_deadline_jst": DEADLINE,
            "cutoff_jst": "2026-11-02T21:39:00+09:00",
            "predictions": ["1-2-3"],
        }
        path.write_text(json.dumps(forecast), encoding="utf-8")
        return path

    @staticmethod
    def make_report(root, official, *, race=RACE):
        location = Path(root) / "official_joint_evidence"
        location.mkdir(exist_ok=True)
        report = {
            "formal": False, "forecast_usable": False,
            "observations": [{
                "race_code": race,
                "racecard_followup": "three_originals_research_complete",
                "three_original_audit": official
            }]
        }
        (location / "batch_report.json").write_text(json.dumps(report), encoding="utf-8")
        return location

    @staticmethod
    def simulated_official():
        return {
            "race_code": RACE, "official_deadline_jst": DEADLINE,
            "cutoff_jst": "2026-11-02T21:39:00+09:00",
            "latest_original_received_jst": "2026-11-02T21:20:05+09:00",
        }


    def test_official_six_lane_shadow_uses_raw_features_only_before_t12(self):
        from scripts.audit_official_forecast_consumption import (
            generate_official_research_shadow, verified_official_input_manifest,
        )
        with tempfile.TemporaryDirectory() as tmp:
            card, before, odds = ThreeOriginalAuditTests().make(tmp)
            with patch("scripts.audit_joint_official_receipts.parse_official_odds_table",
                       return_value={"fixture": 1}), patch(
                    "scripts.audit_joint_official_receipts.inspect_odds_receipt",
                    return_value={"valid_120_combinations": True,
                                  "complete_odds_observed_before_t12": True}):
                official = audit_three_originals(card, before, odds)
                m = verified_official_input_manifest((card, before, odds), official)
                valid_time = "2026-11-02T21:20:40+09:00"
                output = generate_official_research_shadow(m, valid_time)
                self.assertTrue(output["generated"])
                self.assertTrue(output["model_consumed_official_exhibition_fields"])
                self.assertFalse(output["model_consumed_official_odds_prices"])
                self.assertFalse(output["formal_t12_certified"])
                self.assertFalse(output["purchase_approved"])
                self.assertEqual(len(output["top_probability_order"]), 10)
                self.assertEqual(set(output["predictions"]),
                                 {"narrow", "hit", "balance", "hole"})
                self.assertEqual(
                    generate_official_research_shadow(m, valid_time)["top_probability_order"],
                    output["top_probability_order"])
                late = generate_official_research_shadow(
                    m, "2026-11-02T21:39:00+09:00")
                self.assertFalse(late["generated"])
                self.assertEqual(late["status"], "t12_window_closed_no_shadow_generation")
                too_early = generate_official_research_shadow(
                    m, "2026-11-02T21:19:00+09:00")
                self.assertFalse(too_early["generated"])
                self.assertEqual(too_early["status"], "source_receipt_after_requested_generation")

                from scripts.audit_official_forecast_consumption import (
                    generate_timed_official_research_shadow,
                )
                early = "2026-11-02T21:20:40+09:00"
                completed = "2026-11-02T21:20:45+09:00"
                clock_iter = iter((early, completed))
                timed = generate_timed_official_research_shadow(
                    m, clock=lambda: jst(next(clock_iter)))
                self.assertTrue(timed["generated"])
                self.assertEqual(timed["generated_at_jst"], completed)
                self.assertEqual(
                    timed, generate_official_research_shadow(m, completed))
                # Started with enough time, but completed at the cutoff.
                # No forecast may be labeled as created before T-12.
                close_iter = iter(("2026-11-02T21:38:59+09:00",
                                   "2026-11-02T21:39:00+09:00"))
                closed = generate_timed_official_research_shadow(
                    m, clock=lambda: jst(next(close_iter)))
                self.assertFalse(closed["generated"])
                self.assertEqual(
                    closed["status"], "t12_window_closed_during_shadow_generation")
                self.assertNotIn("predictions", closed)
                backwards = iter((completed, early))
                with self.assertRaisesRegex(
                        ValueError, "invalid_research_shadow_completion_clock"):
                    generate_timed_official_research_shadow(
                        m, clock=lambda: jst(next(backwards)))

                forged = json.loads(json.dumps(m))
                forged["six_boat_inputs"][0]["exhibition_time"] += 0.2
                with self.assertRaisesRegex(ValueError, "unverified_official_shadow_manifest"):
                    generate_official_research_shadow(forged, valid_time)


    def test_official_exhibition_f_start_is_not_treated_as_unflagged_start(self):
        """Real beforeinfo can contain F.01/F.05; do not reward those as .01/.05."""
        from scripts.audit_official_forecast_consumption import generate_official_research_shadow

        received = "2026-11-02T21:19:00+09:00"
        sources = {kind: {"received_at_jst": received,
                          "sha256": hashlib.sha256(kind.encode()).hexdigest()}
                   for kind in ("racelist", "beforeinfo", "odds")}
        boat_rows = [
            {"lane": lane, "registration": str(4290 + lane),
             "exhibition_time": 6.90 + lane * .01,
             "tilt": 0.0, "exhibition_course": lane,
             "exhibition_st": ".01"}
            for lane in range(1, 7)
        ]
        def build(st_for_lane_three):
            rows = json.loads(json.dumps(boat_rows))
            rows[2]["exhibition_st"] = st_for_lane_three
            fields = {
                "race_code": "202611022010",
                "cutoff_jst": "2026-11-02T21:39:00+09:00",
                "official_sources": sources, "six_boat_inputs": rows,
            }
            digest = hashlib.sha256(json.dumps(
                fields, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")).hexdigest()
            return {"schema": "OFFICIAL_REAUDITED_INPUT_MANIFEST_V1",
                    **fields, "input_sha256": digest,
                    "official_source_fields_reconstructed": True,
                    "formal_t12_certified": False}
        generated = "2026-11-02T21:20:40+09:00"
        ordinary = generate_official_research_shadow(build(".01"), generated)
        flagged = generate_official_research_shadow(build("F.01"), generated)
        self.assertTrue(ordinary["generated"])
        self.assertTrue(flagged["generated"])
        self.assertFalse(flagged["model_consumed_official_odds_prices"])
        self.assertFalse(flagged["formal_t12_certified"])
        self.assertNotEqual(flagged["predictions"], ordinary["predictions"])
        self.assertTrue(all(flagged["predictions"][key]["tickets"]
                            for key in ("narrow", "hit", "balance", "hole")))
        for invalid in ("F0.01", "F.001", "F-0.01"):
            with self.subTest(st=invalid):
                with self.assertRaisesRegex(
                        ValueError, "unverified_official_shadow_exhibition"):
                    generate_official_research_shadow(build(invalid), generated)

    def test_snapshot_rejects_unproven_consumption_both_clock_directions(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = self.write_forecast(tmp)
            verified = self.simulated_official()
            audit = snapshot_timing(Path(tmp) / "prospective_predictions", RACE, verified)
            self.assertEqual(audit["status"], "official_model_input_consumption_unverified")
            self.assertIs(audit["formal_attested"], False)
            self.write_forecast(tmp, "2026-11-02T21:19:30+09:00")
            audit = snapshot_timing(Path(tmp) / "prospective_predictions", RACE, verified)
            self.assertEqual(audit["status"], "official_originals_arrived_after_forecast")
            self.assertIs(audit["formal_attested"], False)

            forecast = json.loads(original.read_text())
            forecast["source_deadline_jst"] = "2026-11-02T21:50:00+09:00"
            original.write_text(json.dumps(forecast))
            self.assertEqual(snapshot_timing(Path(tmp) / "prospective_predictions",
                                             RACE, verified)["status"], "official_deadline_mismatch")
            forecast["source_deadline_jst"] = DEADLINE
            forecast["generated_at"] = "2026-11-02T21:40:00+09:00"
            original.write_text(json.dumps(forecast))
            self.assertEqual(snapshot_timing(Path(tmp) / "prospective_predictions",
                                             RACE, verified)["status"], "forecast_timing_invalid")
            self.assertEqual(snapshot_timing(Path(tmp) / "four_mode_forecasts",
                                             RACE, verified)["status"], "forecast_not_saved")

    def test_actual_three_original_bytes_are_reaudited_before_timing(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch = Path(tmp) / "official_joint_evidence"
            card, before, odds = self.setup_sources(batch)
            self.write_forecast(tmp)
            with patch("scripts.audit_joint_official_receipts.parse_official_odds_table",
                       return_value={"fixture": 1}), patch(
                    "scripts.audit_joint_official_receipts.inspect_odds_receipt",
                    return_value={"valid_120_combinations": True,
                                  "complete_odds_observed_before_t12": True}):
                official = audit_three_originals(card, before, odds)
                self.make_report(tmp, official)
                result = audit_batch(batch, tmp)
                self.assertEqual(result["research_three_originals_reaudited"], 1)
                self.assertEqual(result["official_consumed_forecasts"], 0)
                self.assertEqual(result["formal_t12_certified"], 0)
                row = result["rows"][0]
                self.assertEqual(row["official_original_status"],
                                 "three_originals_reaudited_research_only")

                manifest = row["official_input_manifest"]
                self.assertTrue(manifest["official_source_fields_reconstructed"])
                self.assertEqual(len(manifest["six_boat_inputs"]), 6)
                self.assertEqual(set(manifest["official_sources"]), {"racelist","beforeinfo","odds"})
                self.assertEqual(len(manifest["input_sha256"]), 64)
                self.assertEqual(manifest["six_boat_inputs"][0]["registration"], "4180")
                self.assertEqual(manifest["six_boat_inputs"][0]["exhibition_course"], 6)
                self.assertFalse(manifest["model_actually_consumed_fields"])
                self.assertFalse(manifest["formal_t12_certified"])

                self.assertEqual(row["forecast_statuses"]["prospective_predictions"]["status"],
                                 "official_model_input_consumption_unverified")
                self.assertEqual(row["forecast_statuses"]["four_mode_forecasts"]["status"],
                                 "forecast_not_saved")

                # An original modified after collection must fail independent
                # digest recheck, even if the report still asserts success.
                before_file = before / "beforeinfo.json"
                before_file.write_bytes(before_file.read_bytes() + b"\n")
                changed = audit_batch(batch, tmp)
                self.assertEqual(changed["research_three_originals_reaudited"], 0)
                self.assertNotIn("official_input_manifest", changed["rows"][0])
                self.assertEqual(changed["rows"][0]["official_original_status"],
                                 "official_original_reaudit_failed")
                self.assertEqual(changed["official_consumed_forecasts"], 0)

    def test_partial_official_pair_is_still_independently_joined_to_forecast_clock(self):
        from scripts.audit_joint_official_receipts import audit_pair
        with tempfile.TemporaryDirectory() as tmp:
            batch = Path(tmp) / "official_joint_evidence"
            card, before, odds = self.setup_sources(batch)
            self.write_forecast(tmp, "2026-11-02T21:19:30+09:00")
            # Turn an otherwise valid raw beforeinfo into an independently
            # hash-verified but exhibition-incomplete official receipt.
            before_file = before / "beforeinfo.json"
            raw = json.loads(before_file.read_text())
            raw["maindata"]["sttenjiinfolist"] = []
            edited = json.dumps(raw).encode()
            before_file.write_bytes(edited)
            manifest_path = before / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["sha256"] = hashlib.sha256(edited).hexdigest()
            manifest["bytes"] = len(edited)
            manifest_path.write_text(json.dumps(manifest))

            with patch("scripts.audit_joint_official_receipts.parse_official_odds_table",
                       return_value={"fixture": 1}), patch(
                    "scripts.audit_joint_official_receipts.inspect_odds_receipt",
                    return_value={"valid_120_combinations": True,
                                  "complete_odds_observed_before_t12": True}):
                pair = audit_pair(before, odds)
                self.assertFalse(pair["both_complete_before_t12"])
                report = {
                    "formal": False, "forecast_usable": False,
                    "observations": [{
                        "race_code": RACE, "status": "pair_not_ready",
                        "joint_audit": pair,
                    }]
                }
                (batch / "batch_report.json").write_text(json.dumps(report))
                result = audit_batch(batch, tmp)
                self.assertEqual(result["official_pairs_reaudited"], 1)
                row = result["rows"][0]
                self.assertEqual(row["official_original_status"],
                                 "two_official_originals_reaudited_incomplete")
                self.assertEqual(row["source_scope"],
                                 "official_beforeinfo_odds_only")
                self.assertEqual(row["forecast_statuses"]["prospective_predictions"]["status"],
                                 "official_originals_arrived_after_forecast")
                self.assertEqual(result["official_consumed_forecasts"], 0)
                self.assertEqual(result["formal_t12_certified"], 0)

                before_file.write_bytes(edited + b"tampered")
                changed = audit_batch(batch, tmp)
                self.assertEqual(changed["official_pairs_reaudited"], 0)
                self.assertEqual(changed["rows"][0]["official_original_status"],
                                 "official_pair_reaudit_failed")

    def test_forged_report_cannot_approve_official_source_without_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_forecast(tmp)
            batch = self.make_report(tmp, {
                **self.simulated_official(),
                "component_checks": {}, "missing_components": [],
                "all_research_components_observed_by_t12": True
            })
            result = audit_batch(batch, tmp)
            self.assertEqual(result["rows"][0]["official_original_status"],
                             "official_original_reaudit_failed")
            self.assertEqual(result["official_consumed_forecasts"], 0)
            self.assertEqual(result["formal_t12_certified"], 0)
            self.assertFalse(result["purchase_approved"])

    def test_invalid_identity_duplicate_and_missing_batch_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch = Path(tmp) / "official_joint_evidence"
            self.assertEqual(audit_batch(batch, tmp)["status"], "batch_unverified")
            self.make_report(tmp, self.simulated_official(), race="202611020000")
            self.assertEqual(audit_batch(batch, tmp)["status"], "batch_unverified")
            report = json.loads((batch / "batch_report.json").read_text())
            report["observations"] = [{
                "race_code": RACE, "racecard_followup": "no_source"
            }] * 2
            (batch / "batch_report.json").write_text(json.dumps(report))
            self.assertEqual(audit_batch(batch, tmp)["status"], "batch_unverified")
            report["observations"] = [{"race_code": RACE}]
            (batch / "batch_report.json").write_text(json.dumps(report))
            result = audit_batch(batch, tmp)
            self.assertEqual(result["rows"][0]["official_original_status"], "not_complete")
            self.assertEqual(result["formal_t12_certified"], 0)

    def test_real_archives_cannot_retroactively_consume_afternoon_official_sources(self):
        root = Path(__file__).resolve().parent.parent
        race = "202611110706"
        official = {
            "official_deadline_jst": "2026-11-11T17:28:00+09:00",
            "cutoff_jst": "2026-11-11T17:16:00+09:00",
            # This is only a test reference, not independent raw-source
            # evidence from this test run.
            "latest_original_received_jst": "2026-11-11T17:13:42+09:00"
        }
        for kind in ("prospective_predictions", "four_mode_forecasts"):
            item = snapshot_timing(root / kind, race, official)
            self.assertEqual(item["status"], "official_originals_arrived_after_forecast")


if __name__ == "__main__":
    unittest.main()
