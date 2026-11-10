"""Fail-closed original rate input contracts. Synthetic JSON only; no finish files."""
import copy
from datetime import datetime, timedelta
import json
import tempfile
import unittest
from pathlib import Path

from scenario_archived_rates_ablation import (
    ARCHIVED_BLOBS, MAIN_PIN, git_blob_sha,
    validate_original_rates, load_original_rates, read_archived_mode_tickets,
    compare_original_to_experiment,
)

CODE = "202611101202"


def record():
    return {
        "race_code": CODE,
        "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "validated": False,
        "target_rates_not_proven": True,
        "beforeinfo": "optional_not_in_snapshot",
        "input_national_win_rates": [7.46, 7.15, 6.66, 7.04, 7.28, 7.24],
        "source_sha256": {"race_cards": "a"*64, "title": "b"*64},
        "generated_at_jst": "2026-11-10T01:39:35.127800+09:00",
        "deadline_jst": "2026-11-10T15:52:00+09:00",
    }


def encode(x):
    return (json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n").encode()


class ArchivedOriginalRateGuardTests(unittest.TestCase):
    def test_parse_six_saved_rates_without_claiming_official_source(self):
        rates, clock = validate_original_rates(encode(record()), CODE)
        self.assertEqual(rates, [7.46, 7.15, 6.66, 7.04, 7.28, 7.24])
        self.assertEqual(clock.utcoffset(), timedelta(hours=9))
        self.assertEqual(len(ARCHIVED_BLOBS), 4)
        self.assertEqual(len(MAIN_PIN), 40)

    def test_record_cannot_be_reassigned_to_another_race(self):
        with self.assertRaisesRegex(ValueError, "wrong_contract"):
            validate_original_rates(encode(record()), "202611091110")

    def test_missing_or_fabricated_rates_rejected(self):
        for rates in ([7]*5, [7]*7, [7, 7, 0, 7, 7, 7],
                      [7, 7, 99, 7, 7, 7], [7, 7, "6", 7, 7, 7],
                      [7, 7, float("nan"), 7, 7, 7]):
            x=record()
            x["input_national_win_rates"]=rates
            with self.subTest(rates=rates), self.assertRaisesRegex(ValueError, "six_rates_invalid"):
                validate_original_rates(encode(x), CODE)

    def test_not_eligible_if_beforeinfo_falsely_claimed(self):
        x=record()
        x["beforeinfo"]={"official": True}
        with self.assertRaisesRegex(ValueError, "wrong_contract"):
            validate_original_rates(encode(x), CODE)

    def test_no_postrace_outcome_may_be_in_input(self):
        for key in ("finish_order", "winning_ticket", "payout"):
            x=record()
            x[key]="1-2-3"
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "wrong_contract"):
                validate_original_rates(encode(x), CODE)

    def test_late_or_same_second_candidate_clock_rejected(self):
        for when in ("2026-11-10T15:40:00+09:00",
                     "2026-11-10T15:40:01+09:00",
                     "2026-11-10T16:00:00+09:00",
                     "2026-11-10T01:39:35+00:00"):
            x=record()
            x["generated_at_jst"]=when
            with self.subTest(when=when), self.assertRaisesRegex(ValueError, "clock|not_pre"):
                validate_original_rates(encode(x), CODE)

    def test_source_digests_must_be_distinct_provenance_fields(self):
        x=record()
        x["source_sha256"]={"one":"a"*64}
        with self.assertRaisesRegex(ValueError, "source_digests_invalid"):
            validate_original_rates(encode(x), CODE)

    def test_git_blob_guard_denies_modified_original(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/(CODE+".json")
            path.write_bytes(encode(record()))
            self.assertEqual(len(git_blob_sha(path.read_bytes())), 40)
            with self.assertRaisesRegex(ValueError, "immutable_original_git_blob_mismatch"):
                load_original_rates(CODE, temp)

    def test_unknown_race_not_registered_and_no_missing_original_success(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "missing_pinned_original"):
                load_original_rates(CODE, temp)
            with self.assertRaisesRegex(ValueError, "not_on_pinned_original_roster"):
                load_original_rates("202601010101", temp)



class RealSavedTicketExposureContract(unittest.TestCase):
    @staticmethod
    def modes():
        from itertools import permutations
        combos=["-".join(map(str,p)) for p in permutations(range(1,7),3)]
        return {
            mode: {"tickets": [{"combo":x,"p":float(100/120)}
                               for x in combos[:count]]}
            for mode,count in (("narrow",5),("hit",10),("balance",16),("hole",22))
        }

    def test_original_has_four_modes_and_exact_budgets(self):
        x=record()
        x["modes"]=self.modes()
        ranked=read_archived_mode_tickets(encode(x), CODE)
        self.assertEqual({k:len(v) for k,v in ranked.items()},
                         {"narrow":5,"hit":10,"balance":16,"hole":22})
        self.assertEqual(ranked["hit"][:5], ranked["narrow"])

    def test_topn_membership_counts_without_result(self):
        original=["1-2-3","1-2-4","1-2-5","1-2-6","1-3-2"]
        changed=["1-2-4","1-2-3","1-2-5","1-4-2","1-3-2"]
        result=compare_original_to_experiment(
            original, {"top1":changed[0],
                       "tickets":[{"combo":x} for x in changed]})
        self.assertTrue(result["top1_exact_ticket_changed"])
        self.assertFalse(result["top1_first_boat_changed"])
        self.assertTrue(result["by_topn"]["top1"]["membership_changed"])
        self.assertFalse(result["by_topn"]["top3"]["membership_changed"])
        self.assertTrue(result["by_topn"]["top5"]["membership_changed"])
        self.assertEqual(result["by_topn"]["top5"]["shared_ticket_count"],4)
        self.assertFalse(result["by_topn"]["top10"]["applicable"])
        self.assertFalse(result["gain_or_loss_in_actual_hit_rate_computed"])
        self.assertFalse(result["confirmed_result_read"])

    def test_same_original_tickets_not_forced_to_change(self):
        original=["1-2-3","1-2-4","1-2-5","1-2-6","1-3-2"]
        result=compare_original_to_experiment(original,{
            "top1":original[0],"tickets":[{"combo":x} for x in original]})
        self.assertFalse(result["top1_exact_ticket_changed"])
        self.assertFalse(result["by_topn"]["top5"]["membership_changed"])

    def test_original_mode_invalid_is_rejected(self):
        clean=self.modes()
        cases=[]
        x=record();x["modes"]=dict(clean)
        x["modes"].pop("hole");cases.append(x)
        x=record();x["modes"]=self.modes()
        x["modes"]["narrow"]["tickets"].pop();cases.append(x)
        x=record();x["modes"]=self.modes()
        x["modes"]["narrow"]["tickets"][1]["combo"]=x["modes"]["narrow"]["tickets"][0]["combo"]
        cases.append(x)
        x=record();x["modes"]=self.modes()
        x["modes"]["hit"]["tickets"][0]["combo"]="1-1-2";cases.append(x)
        x=record();x["modes"]=self.modes()
        x["modes"]["balance"]["tickets"][0]["p"]=float("nan");cases.append(x)
        for item in cases:
            with self.subTest(item=str(item["modes"])[:85]), self.assertRaises(ValueError):
                read_archived_mode_tickets(encode(item), CODE)

    def test_no_results_and_invalid_research_tickets(self):
        original=["1-2-3","1-2-4","1-2-5","1-2-6","1-3-2"]
        for bad in (["1-2-3"]*5,
                    ["1-2-3","1-2-4","1-2-5","1-2-6","1-1-2"],
                    ["1-2-3","1-2-4","1-2-5"]):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                compare_original_to_experiment(
                    original,{"top1":bad[0],
                              "tickets":[{"combo":x} for x in bad]})
        with self.assertRaisesRegex(ValueError,"changed_mode_budget_or_order"):
            compare_original_to_experiment(
                original,{"top1":"6-5-4",
                          "tickets":[{"combo":x} for x in original]})

if __name__ == "__main__":
    unittest.main()
