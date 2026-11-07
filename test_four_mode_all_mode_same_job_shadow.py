"""Research-only frozen all-mode shadow tests. Never uses confirmed results."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_all_mode_same_job_shadow import (
    candidate_modes, top1_pair_candidate, capture, audit_historical_input_day,
    SIZES, PROTECTED, TOP1_PAIR_RULE,
)

JST = timezone(timedelta(hours=9))
SHA = "a" * 40
CODE = "202611070101"
FILE = "four_mode_forecasts/" + CODE + ".json"


def make_original():
    rates = [6.0, 5.2, 5.0, 4.6, 4.2, 3.7]
    return {
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
        "validated": False,
        "race_code": CODE,
        "input_national_win_rates": rates,
        "source_title_received_jst": "2026-11-07T08:05:00+09:00",
        "source_cards_received_jst": "2026-11-07T08:06:00+09:00",
        "generated_at_jst": "2026-11-07T08:07:00+09:00",
        "deadline_jst": "2026-11-07T08:35:00+09:00",
        "modes": rank_modes(probabilities(rates)),
    }


def fixture(root, original=None, include_obs=True):
    original = original or make_original()
    code=original["race_code"]
    filename="four_mode_forecasts/" + code + ".json"
    path = root / filename
    path.parent.mkdir(parents=True,exist_ok=True)
    raw = json.dumps(original,sort_keys=True).encode("utf-8")
    path.write_bytes(raw)
    digest=hashlib.sha256(raw).hexdigest()
    publication=root/"publication.json"
    observation=root/"observation.json"
    publication.write_text(json.dumps({"outcome":"pushed_to_main",
        "commit_sha":SHA,"added_forecasts":1}),encoding="utf-8")
    if include_obs:
        observation.write_text(json.dumps({
            "schema":"FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1",
            "publication_commit_sha":SHA,
            "records":[{"race_code":code,"status":"github_server_observed_before_t_minus_12",
                "first_add_blob_matches_remote":True,
                "first_add_commit":SHA,"original_sha256":digest,
                "github_api_server_date_utc":"2026-11-06T23:09:00+00:00"}],
        }),encoding="utf-8")
    def git(args):
        if args[:2]==["rev-parse","HEAD"]:
            return (SHA+"\n").encode()
        if args[0]=="diff-tree":
            return (filename+"\n").encode()
        if args==["show",SHA+":"+filename]:
            return raw
        raise AssertionError(args)
    return publication,observation,git


class FrozenAllModeTests(unittest.TestCase):
    def test_all_modes_result_blind_candidate_budgets_and_protected_prefix(self):
        original=make_original()
        base,chosen=candidate_modes(original)
        self.assertEqual(set(base),set(SIZES))
        self.assertEqual(set(chosen),set(SIZES))
        for mode,n in SIZES.items():
            self.assertEqual(len(base[mode]),n)
            self.assertEqual(len(chosen[mode]),n)
            self.assertEqual(len(set(chosen[mode])),n)
            self.assertEqual(base[mode][:PROTECTED[mode]],chosen[mode][:PROTECTED[mode]])
        self.assertEqual((base,chosen),candidate_modes(original))

    def test_top1_only_pair_rule_changes_rank_not_any_topn_membership(self):
        raw=make_original()
        old,_=candidate_modes(raw)
        new=top1_pair_candidate(raw,old)
        self.assertEqual(old["hit"][0],"1-2-4")
        self.assertEqual(new["hit"][0],"1-2-3")
        self.assertEqual(new,top1_pair_candidate(raw,old))
        for mode in SIZES:
            self.assertEqual(set(new[mode][:2]),set(old[mode][:2]))
            self.assertEqual(new[mode][2:],old[mode][2:])
            for n in (3,5,10):
                self.assertEqual(set(new[mode][:n]),set(old[mode][:n]))

    def test_top1_pair_keeps_old_first_when_third_boat_is_stronger(self):
        raw=make_original()
        raw["input_national_win_rates"]=[6.0,5.2,3.0,7.0,4.2,3.7]
        raw["modes"]=rank_modes(probabilities(raw["input_national_win_rates"]))
        old,_=candidate_modes(raw)
        new=top1_pair_candidate(raw,old)
        self.assertEqual(old["hit"][0],"1-2-4")
        self.assertEqual(new["hit"][0],old["hit"][0])

    def test_pre_result_frozen_github_original_not_shadow_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p,o,git=fixture(root)
            report=capture(root,p,o,now=datetime(2026,11,7,8,10,tzinfo=JST),git=git,clock=lambda: datetime(2026,11,7,8,10,1,tzinfo=JST))
            self.assertEqual(report["frozen_count"],1)
            self.assertEqual(report["validation_error_count"],0)
            self.assertFalse(report["formal"])
            self.assertFalse(report["candidate_first_remote_receipt_verified"])
            row=report["records"][0]
            self.assertEqual(row["status"],"frozen_local_before_T_minus_12_research_only")
            self.assertFalse(row["remote_first_receipt_of_candidate"])
            self.assertFalse(row["official_beforeinfo_six_verified"])
            self.assertFalse(row["official_odds_120_verified"])
            self.assertEqual(set(row["candidate"]),set(SIZES))
            self.assertEqual(row["top1_pair_rule"],TOP1_PAIR_RULE)
            self.assertEqual(set(row["top1_pair_candidate"]),set(SIZES))
            self.assertEqual(row["top1_selector_sha256"],report["candidate_method_sha256"])

    def test_after_cutoff_never_freezes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p,o,git=fixture(root)
            report=capture(root,p,o,now=datetime(2026,11,7,8,24,tzinfo=JST),git=git,clock=lambda: datetime(2026,11,7,8,24,1,tzinfo=JST))
            self.assertEqual(report["ineligible_count"],1)
            self.assertEqual(report["frozen_count"],0)
            self.assertEqual(report["records"][0]["reason"],"not_frozen_strictly_before_T_minus_12")

    def test_missing_or_bad_remote_observation_cannot_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p,o,git=fixture(root)
            o.unlink()
            self.assertEqual(capture(root,p,o,now=datetime(2026,11,7,8,10,tzinfo=JST),git=git,clock=lambda: datetime(2026,11,7,8,10,1,tzinfo=JST))["status"],
                             "no_original_remote_observation")
            _,o,git=fixture(root)
            obj=json.loads(o.read_text())
            obj["records"][0]["original_sha256"]="b"*64
            o.write_text(json.dumps(obj))
            report=capture(root,p,o,now=datetime(2026,11,7,8,10,tzinfo=JST),git=git,clock=lambda: datetime(2026,11,7,8,10,1,tzinfo=JST))
            self.assertEqual(report["frozen_count"],0)
            self.assertEqual(report["records"][0]["reason"],"original_remote_observation_not_verified")

    def test_original_observation_cannot_precede_forecast_generation(self):
        for observed in ("2026-11-06T23:06:00+00:00",
                         "2026-11-06T23:07:00.500000+00:00"):
            with self.subTest(observed=observed), tempfile.TemporaryDirectory() as d:
                root=Path(d)
                p,o,git=fixture(root)
                receipt=json.loads(o.read_text(encoding="utf-8"))
                receipt["records"][0]["github_api_server_date_utc"]=observed
                o.write_text(json.dumps(receipt),encoding="utf-8")
                report=capture(root,p,o,now=datetime(2026,11,7,8,10,tzinfo=JST),
                               git=git,clock=lambda:datetime(2026,11,7,8,10,1,tzinfo=JST))
                self.assertEqual(report["frozen_count"],0)
                self.assertEqual(report["ineligible_count"],1)
                self.assertEqual(report["records"][0]["reason"],
                                 "original_observation_candidate_chronology_not_proven")

    def test_unreproduced_saved_probabilities_rejected(self):
        row=make_original()
        row["modes"]["hit"]["tickets"][0]["p"]=987.0
        with self.assertRaisesRegex(ValueError,"original_not_exactly_reproducible"):
            candidate_modes(row)

    def test_old_discovery_date_does_not_enter_future_cohort(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            row=make_original()
            row["race_code"]="202611050101"
            row["deadline_jst"]="2026-11-05T08:35:00+09:00"
            p,o,git=fixture(root,row)
            report=capture(root,p,o,now=datetime(2026,11,5,8,10,tzinfo=JST),git=git,clock=lambda: datetime(2026,11,5,8,10,1,tzinfo=JST))
            self.assertEqual(report["frozen_count"],0)
            self.assertEqual(report["records"][0]["reason"],"discovery_period_or_before_registration")

    def test_postrace_field_rejected_even_if_selector_would_ignore_it(self):
        raw=make_original()
        raw["finish_order"]=[1,2,3]
        with self.assertRaisesRegex(ValueError,"postrace_content_in_forecast"):
            candidate_modes(raw)

    def test_historical_input_replay_does_not_require_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            fixture(root)
            report=audit_historical_input_day(root,"20261107")
            self.assertEqual(report["original_v2_races"],1)
            self.assertFalse(report["result_files_read"])
            self.assertFalse(report["formal"])
            self.assertEqual(report["excluded"],{})
            self.assertEqual(report["changes"]["hole"]["changed_top1"],0)
            self.assertEqual(report["top1_pair_changes"]["hit"]["changed_top1"],1)
            self.assertEqual(report["top1_pair_changes"]["hit"]["preserved_top3_5_10"],1)

    def test_corrupt_pub_addition_roster_is_hard_error(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p,o,git=fixture(root)
            pub=json.loads(p.read_text())
            pub["added_forecasts"]=2
            p.write_text(json.dumps(pub))
            with self.assertRaisesRegex(ValueError,"first_add_and_observation_roster_disagree"):
                capture(root,p,o,now=datetime(2026,11,7,8,10,tzinfo=JST),git=git,clock=lambda: datetime(2026,11,7,8,10,1,tzinfo=JST))


if __name__=="__main__":
    unittest.main()
