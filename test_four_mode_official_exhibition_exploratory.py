"""Synthetic-only prototype tests. No real official forecast or accuracy claims."""
import base64
import copy
import hashlib
import json
import math
import unittest

from clean_four_modes import rank_modes
from four_mode_official_exhibition_exploratory import (
    COEFF, SCHEMA, board, explore,
)
from four_mode_official_future_lineage_preflight import _canonical
from research_model import probabilities
from test_four_mode_official_raw_semantic_replay import (
    official_shaped_fixture, odds_table, replace_original,
)


def old_original(code="202611100101"):
    rates=[6.0,5.5,5.0,4.5,4.0,3.5]
    return {
        "schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code":code,
        "model_version":"CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
        "validated":False,
        "beforeinfo":"optional_not_in_snapshot",
        "source_sha256":{"race_cards":"a"*64,"title":"b"*64},
        "input_national_win_rates":rates,
        "modes":rank_modes(probabilities(rates)),
    }


def perturb_before(source, field, index, value):
    original=base64.b64decode(source["originals"]["beforeinfo"]["raw_base64"])
    data=json.loads(original)
    if field in ("extime","tilt"):
        data["maindata"]["teiinfolist"][index][field]=str(value)
    else:
        data["maindata"]["sttenjiinfolist"][index][field]=str(value)
    source["normalized_source_claim"][
        {"extime":"exhibition_times","tilt":"exhibition_tilts",
         "st":"exhibition_st","cs":"exhibition_courses"}[field]][index]=value
    candidate={"consumed_source_sha256":{}}
    replace_original(source,candidate,"beforeinfo",json.dumps(data).encode())


class OfficialExhibitionExplorationTests(unittest.TestCase):
    def sample(self):
        source, candidate=official_shaped_fixture()
        return source, candidate["generated_at_jst"], old_original()

    def test_official_shaped_synthetic_raw_generates_nonformal_mode_lists(self):
        s,when,original=self.sample()
        r=explore(s,original,generated_at_jst=when)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual({k:len(v) for k,v in r["mode_tickets"].items()},
                         {"narrow":5,"hit":10,"balance":16,"hole":22})
        self.assertFalse(r["model_scores_calibrated"])
        self.assertFalse(r["official_odds_used_for_rank"])
        self.assertTrue(r["official_exhibition_features_used_for_rank"])
        self.assertTrue(r["source_bytes_reparsed_before_computation"])
        self.assertFalse(r["selector_preregistered_for_formal_cohort"])
        self.assertFalse(r["candidate_frozen_remotely"])
        self.assertFalse(r["formal"])
        self.assertEqual(r["future_pairs_admitted"],0)

    def test_repeat_is_deterministic_and_changes_no_source_original(self):
        s,when,original=self.sample()
        before=copy.deepcopy((s,original))
        a=explore(s,original,generated_at_jst=when)
        b=explore(s,original,generated_at_jst=when)
        self.assertEqual(a,b)
        self.assertEqual((s,original),before)

    def test_exhibition_time_changes_the_recomputed_board(self):
        s,when,old=self.sample()
        baseline=board(s["normalized_source_claim"],old)
        perturb_before(s,"extime",0,7.55)
        modified=board(s["normalized_source_claim"],old)
        self.assertNotEqual(baseline,modified)
        # Must pass actual raw parsers, not a forged normalized claim.
        self.assertTrue(explore(s,old,generated_at_jst=when)[
            "source_bytes_reparsed_before_computation"])

    def test_exhibition_st_changes_the_recomputed_board(self):
        s,when,old=self.sample()
        original_board=board(s["normalized_source_claim"],old)
        perturb_before(s,"st",0,0.95)
        self.assertNotEqual(original_board,board(s["normalized_source_claim"],old))
        self.assertFalse(explore(s,old,generated_at_jst=when)["formal"])

    def test_exhibition_course_changes_board_without_final_entry_claim(self):
        s,when,old=self.sample()
        base=board(s["normalized_source_claim"],old)
        perturb_before(s,"cs",0,2)
        perturb_before(s,"cs",1,1)
        changed=board(s["normalized_source_claim"],old)
        self.assertNotEqual(base,changed)
        self.assertFalse(explore(s,old,generated_at_jst=when)[
            "real_official_http_origin_independently_proven"])

    def test_odds_bytes_and_values_never_reorder_ticket_scores(self):
        s,when,old=self.sample()
        one=explore(s,old,generated_at_jst=when)
        raw_odds=odds_table("42.7")
        record={"consumed_source_sha256":{}}
        replace_original(s,record,"odds120",raw_odds)
        s["normalized_source_claim"]["odds_3t"]={
            k:42.7 for k in s["normalized_source_claim"]["odds_3t"]}
        two=explore(s,old,generated_at_jst=when)
        self.assertEqual(one["mode_tickets"],two["mode_tickets"])
        self.assertNotEqual(one["consumed_source_sha256"],two["consumed_source_sha256"])

    def test_fake_official_claim_without_matching_raw_is_rejected(self):
        s,when,old=self.sample()
        s["normalized_source_claim"]["exhibition_times"][0]=7.55
        with self.assertRaisesRegex(ValueError,"normalized_exhibition_times"):
            explore(s,old,generated_at_jst=when)

    def test_unverified_original_result_leak_and_wrong_race_rejected(self):
        s,when,old=self.sample()
        old["finish_order"]=[1,2,3]
        with self.assertRaisesRegex(ValueError,"wrong_unverified_original"):
            explore(s,old,generated_at_jst=when)
        s,when,old=self.sample()
        old["race_code"]="202611100102"
        with self.assertRaisesRegex(ValueError,"wrong_unverified_original"):
            explore(s,old,generated_at_jst=when)

    def test_changed_old_v2_ranks_rejected_before_source_computation(self):
        s,when,old=self.sample()
        old["modes"]["hit"]["tickets"][0]["combo"]="6-5-4"
        with self.assertRaisesRegex(ValueError,"original_not_exactly_reproducible"):
            explore(s,old,generated_at_jst=when)

    def test_late_generation_or_no_real_original_raw_rejected(self):
        s,when,old=self.sample()
        with self.assertRaisesRegex(ValueError,"source_to_candidate_time_order"):
            explore(s,old,generated_at_jst="2026-11-10T14:28:01+09:00")
        s,when,old=self.sample()
        s["originals"]["odds120"]["raw_base64"]="YWJj"
        with self.assertRaisesRegex(ValueError,"original_byte_hash"):
            explore(s,old,generated_at_jst=when)

    def test_board_probability_scores_normalized_but_not_calibrated(self):
        s,_,old=self.sample()
        rows=board(s["normalized_source_claim"],old)
        self.assertEqual(len(rows),120)
        self.assertTrue(math.isclose(sum(p for _,p in rows),1,abs_tol=1e-10))
        self.assertEqual(len({ticket for ticket,_ in rows}),120)
        self.assertEqual(COEFF["place_weights"],(1.0,0.6,0.35))
        self.assertEqual(set(rank_modes(rows)),{"narrow","hit","balance","hole"})


if __name__=="__main__":
    unittest.main()
