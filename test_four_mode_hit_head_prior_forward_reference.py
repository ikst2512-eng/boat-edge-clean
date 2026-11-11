"""HIT-head reference-only prospective gates; outcomes only after full replay."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from test_four_mode_all_mode_same_job_shadow import make_original
from test_four_mode_top1_forward_reference import result
from four_mode_top1_head_prior_shadow import choose
from four_mode_hit_head_prior_forward_reference import (
    BATCH_SCHEMA, START, END, PILOT, CONFIRM, canonical, compare, policy,
    validate_before_results,
)


def frozen(root, day="20261109", rates=None):
    raw = make_original()
    day_iso = f"{day[:4]}-{day[4:6]}-{day[6:8]}"
    raw["race_code"] = day + "0101"
    for key in ("source_title_received_jst", "source_cards_received_jst",
                "generated_at_jst", "deadline_jst"):
        raw[key] = raw[key].replace("2026-11-07", day_iso)
    raw["input_national_win_rates"] = rates or [4.5, 7.0, 4.5, 4.5, 4.5, 4.5]
    from clean_four_modes import rank_modes
    from research_model import probabilities
    raw["modes"] = rank_modes(probabilities(raw["input_national_win_rates"]))
    forecast = root / "four_mode_forecasts" / (raw["race_code"] + ".json")
    forecast.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(raw, sort_keys=True).encode()
    forecast.write_bytes(data)
    shadow = choose(raw)
    row = {
        "status": "frozen_local_before_T_minus_12_research_only",
        "race_code": raw["race_code"],
        "original_sha256": hashlib.sha256(data).hexdigest(),
        "original_generated_at_jst": raw["generated_at_jst"],
        "deadline_jst": raw["deadline_jst"],
        "candidate_frozen_at_jst": day_iso + "T08:10:00+09:00",
        "candidate": shadow,
        "candidate_sha256": hashlib.sha256(canonical(shadow)).hexdigest(),
    }
    batch = {
        "schema": BATCH_SCHEMA,
        "status": "local_candidate_frozen_reference_only",
        "selector_git_blob_sha1": policy()["pinned_selector_git_blob_sha1"],
        "formal": False,
        "candidate_first_remote_receipt_verified": False,
        "records": [row],
    }
    return batch


class HitHeadProspectiveReferenceTests(unittest.TestCase):
    def test_policy_matches_immutable_selector_and_future_holdout(self):
        p = policy()
        self.assertEqual(p["eligible_deadline_start_jst"], START)
        self.assertEqual(p["eligible_deadline_end_jst"], END)
        self.assertEqual(p["pilot_races"], PILOT)
        self.assertEqual(p["confirmation_races"], CONFIRM)
        self.assertFalse(p["promotion_allowed"])

    def test_no_supplied_future_candidate_is_zero_not_proven(self):
        with tempfile.TemporaryDirectory() as d:
            r = compare([], Path(d))
            self.assertEqual(r["first_600_reference_slots_reserved"], 0)
            self.assertEqual(r["hit_topn_by_phase"]["pilot"]["top1"]["denominator"], 0)
            self.assertIsNone(r["hit_topn_by_phase"]["pilot"]["top1"]["candidate_pct"])
            self.assertFalse(r["formal"])
            self.assertFalse(r["model_improvement_proven"])
            self.assertFalse(r["candidate_first_remote_receipt_verified"])
            self.assertFalse(r["complete_capture_run_inventory_verified"])

    def test_missing_future_result_reserves_slot_without_false_loss(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            batch=frozen(root)
            r=compare([batch],root)
            self.assertEqual(r["pilot_slots_reserved"],1)
            self.assertEqual(r["pending_result_codes"],["202611090101"])
            self.assertEqual(r["hit_topn_by_phase"]["pilot"]["top1"]["denominator"],0)
            self.assertEqual(r["result_status_by_phase"]["pilot"],{"pending":1})

    def test_paired_wins_losses_top1_and_top10_not_assumed_preserved(self):
        for side in ("original", "candidate"):
            with self.subTest(side=side),tempfile.TemporaryDirectory() as d:
                root=Path(d)
                batch=frozen(root)
                shadow=batch["records"][0]["candidate"]
                old=shadow["original"]["hit"][0]
                new=shadow["candidate"]["hit"][0]
                self.assertNotEqual(old,new)
                self.assertNotEqual(old[0],new[0])
                result(root,"202611090101",old if side=="original" else new)
                r=compare([batch],root)
                m=r["hit_topn_by_phase"]["pilot"]["top1"]
                self.assertEqual(m["denominator"],1)
                self.assertEqual((m["original"],m["candidate"]),(
                    1,0) if side=="original" else (0,1))
                self.assertEqual((m["gained"],m["lost"]),(
                    0,1) if side=="original" else (1,0))
                for n in (3,5,10):
                    self.assertEqual(
                        r["hit_topn_by_phase"]["pilot"][f"top{n}"]["denominator"],1)
                self.assertFalse(r["formal"])

    def test_invalid_early_confirmation_is_not_counted_as_loss(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            batch=frozen(root)
            original=batch["records"][0]["candidate"]["original"]["hit"][0]
            result(root,"202611090101",original,
                   confirmed_at="2026-11-09T08:00:00+09:00")
            r=compare([batch],root)
            self.assertEqual(r["invalid_result_codes"],["202611090101"])
            self.assertEqual(r["hit_topn_by_phase"]["pilot"]["top1"]["denominator"],0)

    def test_nov8_saved_result_cannot_enter_nov9_study(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            batch=frozen(root,"20261108")
            result(root,"202611080101","2-1-3")
            with self.assertRaisesRegex(ValueError,
                                        "pre_registered_discovery_date_not_eligible"):
                compare([batch],root)

    def test_saved_ticket_tampering_rejected_before_any_result_read(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            batch=frozen(root)
            batch["records"][0]["candidate"]["candidate"]["hit"][0]="6-5-4"
            # Give a deliberately malformed result: it must not matter.
            output=root/"confirmed_results"/"202611090101.json"
            output.parent.mkdir()
            output.write_bytes(b"not even json")
            with self.assertRaisesRegex(
                    ValueError, "head_prior_saved_candidate_not_reproducible"):
                compare([batch],root)

    def test_forged_candidate_hash_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            batch=frozen(root)
            batch["records"][0]["candidate_sha256"]="0"*64
            with self.assertRaisesRegex(ValueError,
                                        "head_prior_saved_candidate_not_reproducible"):
                compare([batch],root)

    def test_candidate_timestamp_after_T12_never_scores(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            batch=frozen(root)
            batch["records"][0]["candidate_frozen_at_jst"]="2026-11-09T08:25:00+09:00"
            with self.assertRaisesRegex(ValueError,
                                        "head_prior_original_candidate_chronology"):
                compare([batch],root)

    def test_future_missing_candidate_does_not_get_backfilled(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            batch=frozen(root)
            batch["records"][0]["status"]="ineligible"
            with self.assertRaisesRegex(ValueError,
                                        "incomplete_head_prior_cohort_no_backfill"):
                compare([batch],root)

    def test_duplicate_candidate_never_inflates_denominator(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            batch=frozen(root)
            with self.assertRaisesRegex(ValueError,
                                        "duplicate_or_invalid_head_prior_race"):
                compare([batch,copy.deepcopy(batch)],root)

    def test_fake_first_remote_receipt_claim_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            batch=frozen(root)
            batch["candidate_first_remote_receipt_verified"]=True
            with self.assertRaisesRegex(ValueError,
                                        "invalid_or_forged_head_prior_batch"):
                compare([batch],root)

    def test_wrong_selector_pin_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            batch=frozen(root)
            batch["selector_git_blob_sha1"]="a"*40
            with self.assertRaisesRegex(ValueError,
                                        "invalid_or_forged_head_prior_batch"):
                compare([batch],root)


if __name__ == "__main__":
    unittest.main()
