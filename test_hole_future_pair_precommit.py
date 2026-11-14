"""Fail-closed regression gates for research-only hole pair precommit."""
import json
import hashlib
import sys
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
import hole_future_pair_precommit as s

JST=timezone(timedelta(hours=9))
CODE="202611060101"
CUTOFF=datetime(2026,11,6,10,0,tzinfo=JST)
START=CUTOFF-timedelta(minutes=5)
FINISH=CUTOFF-timedelta(minutes=4)
BASE=["1-2-3","1-2-4","1-3-2","1-3-4","2-1-3",
      "2-1-4","1-4-2","1-4-3","2-3-1","2-3-4"]

def archive():
    tickets=lambda xs:[{"combo":x,"p":3.0} for x in xs]
    return {"deadline_jst":(CUTOFF+timedelta(minutes=12)).isoformat(),
            "generated_at_jst":(START-timedelta(minutes=1)).isoformat(),
            "model_version":"CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
            "modes":{"hole":{"tickets":tickets(BASE)},
                     "hit":{"tickets":tickets(["1-5-2","1-5-3","2-4-1","2-5-1"]+BASE)},
                     "balance":{"tickets":tickets(["1-5-2","1-5-3","2-4-1","2-5-1"]+BASE)}}}

class PairPrecommitTest(unittest.TestCase):
    def test_nov05_not_eligible_without_archive_or_result(self):
        with patch.object(s,"archived_four_modes",side_effect=AssertionError("opened archive")):
            r=s.freeze("202611050101",".")
        self.assertEqual(r["status"],"not_yet_eligible_or_invalid_code")
        self.assertFalse(r["formal"])

    def test_t12_start_and_end_boundaries(self):
        with patch.object(s,"archived_four_modes",return_value=(200,archive())):
            r=s.freeze(CODE,".",started_at=CUTOFF)
        self.assertEqual(r["status"],"after_t_minus_12")
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"four_mode_forecasts").mkdir()
            (root/"four_mode_forecasts"/(CODE+".json")).write_text("archived",encoding="utf-8")
            with patch.object(s,"archived_four_modes",return_value=(200,archive())), \
                 patch.object(s,"verify_locked_selection",return_value={"pinned":"sha"}):
                r=s.freeze(CODE,root,started_at=START,completed_at=CUTOFF)
            self.assertEqual(r["status"],"calculation_crossed_t_minus_12")
            self.assertFalse(r["formal"])

    def test_fixed_policies_and_result_blind_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"four_mode_forecasts").mkdir()
            (root/"four_mode_forecasts"/(CODE+".json")).write_text("archived",encoding="utf-8")
            events=[]
            actual_select = s.select
            def choosing(arc):
                events.append("choose")
                return actual_select(arc)
            def reading(code,root):
                events.append("result")
                return {"status":"historical_comparison_only","winning_ticket":"1-5-2"}
            with patch.object(s,"archived_four_modes",return_value=(200,archive())), \
                 patch.object(s,"verify_locked_selection",return_value={"pinned":"sha"}):
                r=s.freeze(CODE,root,started_at=START,completed_at=FINISH)
                self.assertEqual(r["status"],"locally_frozen_unverified")
                self.assertEqual(r["candidates"]["baseline"][:5],
                                 r["candidates"]["same_pair_two_thirds"][:5])
                self.assertEqual(r["candidates"]["baseline"][:5],
                                 r["candidates"]["two_pairs_one_third"][:5])
                self.assertNotEqual(r["candidates"]["baseline"],r["candidates"]["same_pair_two_thirds"])
                self.assertNotEqual(r["candidates"]["baseline"],r["candidates"]["two_pairs_one_third"])
                with patch.object(s,"select",side_effect=choosing), \
                     patch.object(s,"compare_race",side_effect=reading):
                    reviewed=s.review(r,root)
            self.assertEqual(events,["choose","result"])
            self.assertEqual(reviewed["status"],"reference_scored_without_independent_receipt")
            self.assertFalse(reviewed["formal"])
            self.assertEqual(reviewed["ranks"]["baseline"],0)
            self.assertEqual(reviewed["ranks"]["same_pair_two_thirds"],6)
            self.assertEqual(reviewed["ranks"]["two_pairs_one_third"],6)
            self.assertEqual(reviewed["gain_loss"]["same_pair_two_thirds"]["top10"]["gained"],1)
            self.assertEqual(reviewed["gain_loss"]["two_pairs_one_third"]["top10"]["gained"],1)
            self.assertEqual(reviewed["gain_loss"]["two_pairs_one_third"]["top5"]["gained"],0)
            self.assertIsNone(reviewed["top10_loss_diagnostics"]["same_pair_two_thirds"])
            self.assertIsNone(reviewed["top10_loss_diagnostics"]["two_pairs_one_third"])

    def test_top10_loss_diagnostic_distinguishes_dropped_third_from_dropped_pair(self):
        # Synthetic, outcome-independent regression: original 2-3 pair has two
        # third choices; replacing just one can lose a hit despite pair coverage.
        original=BASE[:]
        candidate=original[:9]+["1-5-2"]
        d=s.top10_loss_diagnostic(original,candidate,"2-3-4")
        self.assertEqual(d["original_rank"],10)
        self.assertEqual(d["lost_ticket"],"2-3-4")
        self.assertTrue(d["first_second_pair_still_covered"])
        self.assertEqual(d["cause"],"third_choice_removed_despite_pair_coverage")
        self.assertEqual(d["removed_tickets"],["2-3-4"])
        self.assertEqual(d["added_tickets"],["1-5-2"])
        self.assertIsNone(s.top10_loss_diagnostic(original,candidate,"1-2-3"))
        candidate2=original[:8]+["1-5-2","1-5-3"]
        d2=s.top10_loss_diagnostic(original,candidate2,"2-3-4")
        self.assertFalse(d2["first_second_pair_still_covered"])
        self.assertEqual(d2["cause"],"winning_first_second_pair_removed")

    def test_source_must_exist_before_freeze_starts(self):
        # No candidate can be labelled frozen before its source forecast exists.
        future=archive()
        future["generated_at_jst"]=(START+timedelta(seconds=1)).isoformat()
        with patch.object(s,"archived_four_modes",return_value=(200,future)), \
             patch.object(s,"select",side_effect=AssertionError("opened selector")):
            r=s.freeze(CODE,".",started_at=START,completed_at=FINISH)
        self.assertEqual(r["status"],"source_not_generated_before_freeze")
        self.assertFalse(r["formal"])
        missing=archive()
        missing.pop("generated_at_jst")
        with patch.object(s,"archived_four_modes",return_value=(200,missing)), \
             patch.object(s,"select",side_effect=AssertionError("opened selector")):
            r=s.freeze(CODE,".",started_at=START,completed_at=FINISH)
        self.assertEqual(r["status"],"source_not_generated_before_freeze")

    def test_replay_refuses_impossible_source_chronology_and_false_formal(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"four_mode_forecasts").mkdir()
            (root/"four_mode_forecasts"/(CODE+".json")).write_text("archived",encoding="utf-8")
            with patch.object(s,"archived_four_modes",return_value=(200,archive())), \
                 patch.object(s,"verify_locked_selection",return_value={"pinned":"sha"}):
                record=s.freeze(CODE,root,started_at=START,completed_at=FINISH)
                self.assertEqual(record["status"],"locally_frozen_unverified")
                impossible=archive()
                impossible["generated_at_jst"]=(START+timedelta(seconds=1)).isoformat()
                with patch.object(s,"archived_four_modes",return_value=(200,impossible)), \
                     patch.object(s,"compare_race",side_effect=AssertionError("opened result")):
                    result=s.review(record,root)
                self.assertEqual(result["status"],"timing_mismatch")
                record["formal"]=True
                with patch.object(s,"compare_race",side_effect=AssertionError("opened result")):
                    result=s.review(record,root)
                self.assertEqual(result["status"],"invalid_method_or_claim")


    def test_cli_writes_complete_candidates_once_without_overwriting(self):
        # Captured stdout intentionally omits picks; only immutable output holds
        # the full exact tickets and checksums needed for later result-blind audit.
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"frozen-hole-pair.json"
            picks={
                "baseline":BASE[:],
                "same_pair_two_thirds":BASE[:5]+["1-5-2","1-5-3"]+BASE[5:8],
                "two_pairs_one_third":BASE[:5]+["1-5-2","2-4-1"]+BASE[5:8],
            }
            record={
                "schema":"HOLE_PAIR_FUTURE_FREEZE_V1",
                "status":"locally_frozen_unverified",
                "race_code":CODE,
                "candidates":picks,
                "candidates_sha256":s.canonical_digest(picks),
                "locked_selector_git_blobs":{"selector":"original-hash"},
                "source_sha256":"0"*64,
                "formal":False,
                "prospective_validation":False,
                "independent_first_receipt_verified":False,
                "production_forecast_changed":False,
            }
            argv=["hole_future_pair_precommit.py",CODE,"--root",temp,
                  "--output",str(output)]
            with patch.object(sys,"argv",argv), \
                 patch.object(s,"freeze",return_value=record):
                s.main()
                self.assertTrue(output.exists())
                saved=json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(saved,record)
                self.assertEqual(saved["candidates_sha256"],
                                 s.canonical_digest(saved["candidates"]))
                self.assertEqual(saved["candidates"]["baseline"][:5],
                                 saved["candidates"]["same_pair_two_thirds"][:5])
                with self.assertRaisesRegex(ValueError,"already_exists"):
                    s.main()
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")),record)

    def test_corrupt_or_false_attestation_prevents_outcome_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"four_mode_forecasts").mkdir()
            (root/"four_mode_forecasts"/(CODE+".json")).write_text("archived",encoding="utf-8")
            with patch.object(s,"archived_four_modes",return_value=(200,archive())), \
                 patch.object(s,"verify_locked_selection",return_value={"pinned":"sha"}):
                record=s.freeze(CODE,root,started_at=START,completed_at=FINISH)
                record["independent_first_receipt_verified"]=True
                with patch.object(s,"compare_race",side_effect=AssertionError("opened result")):
                    a=s.review(record,root)
                self.assertEqual(a["status"],"invalid_method_or_claim")
                record["independent_first_receipt_verified"]=False
                record["candidates"]["baseline"][0]="9-9-9"
                with patch.object(s,"compare_race",side_effect=AssertionError("opened result")):
                    b=s.review(record,root)
                self.assertEqual(b["status"],"candidate_replay_mismatch")


    def test_future_holdout_protocol_starts_after_inspected_days(self):
        protocol = Path(__file__).resolve().parent / "research" / "hole_pair_future_holdout_protocol_20261109.json"
        raw = protocol.read_bytes()
        # First registered Git blob is immutable: protocol edits require a new
        # future-only protocol/version, never an in-place holdout definition.
        git_blob = hashlib.sha1(("blob " + str(len(raw)) + "\0").encode() + raw).hexdigest()
        self.assertEqual(git_blob, "e1acf640a099ab6f9a3c7a10f85062f472be3667")
        p = json.loads(protocol.read_text(encoding="utf-8"))
        self.assertEqual(p["schema"], "HOLE_PAIR_FUTURE_HOLDOUT_PROTOCOL_V1")
        self.assertEqual(p["protocol_effective_day_jst"], "20261109")
        self.assertGreater(p["protocol_effective_day_jst"], p["historical_exclusion"]["days_through"])
        self.assertEqual(p["method"]["selector_method"], s.METHOD)
        self.assertEqual(p["method"]["arms"], list(s.POLICIES))
        self.assertEqual(p["method"]["count_per_arm"], 10)
        self.assertTrue(p["method"]["protected_top5"])
        self.assertTrue(p["method"]["preserve_original_first_second_pair_coverage"])
        self.assertEqual(p["sequential_cohorts"]["pilot"]["first_eligible_records"], 300)
        self.assertEqual(p["sequential_cohorts"]["confirmation"]["next_eligible_records"], 300)
        self.assertTrue(p["event_universe"]["separate_remote_receipt_required"])

    def test_future_holdout_protocol_cannot_claim_formal_on_local_artifact_only(self):
        p = json.loads((Path(__file__).resolve().parent / "research" /
                        "hole_pair_future_holdout_protocol_20261109.json").read_text(encoding="utf-8"))
        g = p["production_gates"]
        self.assertFalse(g["formal"])
        self.assertFalse(g["prospective_improvement_proven"])
        self.assertFalse(g["production_promotion_allowed"])
        self.assertFalse(g["automatic_merge_allowed"])
        self.assertTrue(g["no_new_cron_or_main_or_render_or_prediction_changes"])
        self.assertIn("server-controlled timestamp", p["event_universe"]["remote_receipt_definition"])
        self.assertIn("120-way odds", p["event_universe"]["official_inputs_required"])
        self.assertIn("Holm", p["metrics"]["significance"])
        self.assertIn("confirmation cohort only", p["metrics"]["significance"])

if __name__=="__main__":unittest.main()
