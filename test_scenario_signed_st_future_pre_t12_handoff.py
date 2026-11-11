"""Synthetic future-only, UNPUBLISHED signed-F T-12 gating tests.

None of these fixtures are an official first receipt, new Git commit,
qualified prospective prediction, or claim of predictive performance.
"""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
from itertools import permutations
import json
import unittest
from unittest.mock import patch

import scenario_signed_st_future_pre_t12_handoff as s
from scenario_signed_st_registered_shadow import PROTOCOL, PROTOCOL_BLOB, STUDY_ID

JST=timezone(timedelta(hours=9))


def audit_fixture():
    return {
        "race_code":"202611120711",
        "official_deadline_jst":"2026-11-12T20:00:00+09:00",
        "cutoff_jst":"2026-11-12T19:48:00+09:00",
        "racelist_received_jst":"2026-11-12T19:43:55+09:00",
        "beforeinfo_received_jst":"2026-11-12T19:43:56+09:00",
        "odds_received_jst":"2026-11-12T19:44:00+09:00",
        "latest_original_received_jst":"2026-11-12T19:44:00+09:00",
        "component_checks":{"condition_"+str(i):True for i in range(12)},
        "missing_components":[],
        "three_originals_hash_verified":True,
        "all_research_components_observed_by_t12":True,
        "t12_eligible":False,
        "forecast_usable":False,
    }


def hypothetical_math(code="202611120711"):
    combos=["-".join(map(str,p)) for p in permutations(range(1,7),3)]
    counts={"narrow":5,"hit":10,"balance":16,"hole":22}
    def modes():
        return {mode:{
            "tickets":[{"combo":c,"p":round(1.0/(i+1),5)}
                       for i,c in enumerate(combos[:count])],
            "top1":combos[0],
            "full_120_mixture_sha256":hashlib.sha256(mode.encode()).hexdigest(),
        } for mode,count in counts.items()}
    return {
        "schema":"REGISTERED_SIGNED_F_FOUR_MODE_ARCHIVED_MATH_ONLY_V1",
        "registered_study_protocol_git_blob_sha1":PROTOCOL_BLOB,
        "registered_method_sources_checked_locally":True,
        "actual_original_source_race_card_beforeinfo_odds120_reparsed":True,
        "study_id":STUDY_ID,
        "race_code":code,
        "F_boats":1,
        "historical_archive_replay_not_predeadline_forecast":True,
        "prospective_candidate_generated":False,
        "results_or_payouts_read":False,
        "formal":False,
        "same_4_mode_ticket_budgets":counts,
        "source_original_sha256":{key:hashlib.sha256(key.encode()).hexdigest()
                                  for key in ("racelist","beforeinfo","odds120")},
        "signed_feature_vector_sha256":hashlib.sha256(b"signed").hexdigest(),
        "math_4_modes_signed_F":modes(),
        "math_4_modes_ST_zero_control":modes(),
    }


class FutureSignedFGateTests(unittest.TestCase):
    def setUp(self):
        self.audit=audit_fixture()
        self.protocol=json.loads(PROTOCOL.read_text())
        self.before=datetime.fromisoformat("2026-11-12T19:45:00+09:00")
        self.after=datetime.fromisoformat("2026-11-12T19:45:04+09:00")
        self.temporal=s.require_future_source_before_math(
            self.audit,self.protocol,self.before)

    def test_future_boundaries_require_90_seconds_before_math(self):
        self.assertEqual(self.temporal["cutoff"].isoformat(),
                         "2026-11-12T19:48:00+09:00")
        too_late=datetime.fromisoformat("2026-11-12T19:46:30+09:00")
        with self.assertRaisesRegex(ValueError,"cutoff_or_current_clock"):
            s.require_future_source_before_math(self.audit,self.protocol,too_late)

    def test_past_11nov_cannot_be_new_study_even_if_clock_backdated(self):
        a=copy.deepcopy(self.audit)
        a["race_code"]="202611111911"
        for k in ("official_deadline_jst","cutoff_jst","racelist_received_jst",
                  "beforeinfo_received_jst","odds_received_jst",
                  "latest_original_received_jst"):
            a[k]=a[k].replace("2026-11-12","2026-11-11")
        with self.assertRaisesRegex(ValueError,"cutoff_or_current_clock"):
            s.require_future_source_before_math(
                a,self.protocol,
                datetime.fromisoformat("2026-11-11T19:45:00+09:00"))

    def test_stale_clock_today_cannot_be_used_for_tomorrow(self):
        with self.assertRaisesRegex(ValueError,"cutoff_or_current_clock"):
            s.require_future_source_before_math(
                self.audit,self.protocol,
                datetime.fromisoformat("2026-11-11T19:45:00+09:00"))

    def test_all_three_real_components_must_pass_before_math(self):
        a=copy.deepcopy(self.audit)
        a["component_checks"]["condition_5"]=False
        with self.assertRaisesRegex(ValueError,"three_originals_incomplete"):
            s.require_future_source_before_math(a,self.protocol,self.before)
        a=copy.deepcopy(self.audit)
        a["three_originals_hash_verified"]=False
        with self.assertRaisesRegex(ValueError,"three_originals_incomplete"):
            s.require_future_source_before_math(a,self.protocol,self.before)

    def test_numeric_UTC_or_naive_clock_cannot_replace_JST(self):
        with self.assertRaisesRegex(ValueError,"clock_must_be_JST"):
            s.require_future_source_before_math(
                self.audit,self.protocol,self.before.astimezone(timezone.utc))
        with self.assertRaisesRegex(ValueError,"clock_must_be_JST"):
            s.require_future_source_before_math(
                self.audit,self.protocol,self.before.replace(tzinfo=None))

    def test_latest_receipt_must_be_strictly_before_model_clock(self):
        a=copy.deepcopy(self.audit)
        a["latest_original_received_jst"]=self.before.isoformat()
        with self.assertRaisesRegex(ValueError,"cutoff_or_current_clock"):
            s.require_future_source_before_math(a,self.protocol,self.before)

    def test_returns_canonical_same_race_bytes_but_never_publication_claims(self):
        m=hypothetical_math()
        one=s.package_time_guarded_research_result(
            self.audit,self.protocol,m,self.temporal,self.after)
        again=s.package_time_guarded_research_result(
            self.audit,self.protocol,m,self.temporal,self.after)
        self.assertEqual(one,again)
        self.assertTrue(one["bytes"].endswith(b"\n"))
        self.assertEqual(one["sha256"],hashlib.sha256(one["bytes"]).hexdigest())
        self.assertEqual(one["path"],"signed_f_four_mode_research/202611120711.json")
        data=json.loads(one["bytes"])
        self.assertEqual(data["T_minus_12_cutoff_jst"],"2026-11-12T19:48:00+09:00")
        self.assertEqual(data["protocol_git_blob_sha1"],PROTOCOL_BLOB)
        self.assertEqual(data["ticket_count_by_mode"],self.protocol["mode_ticket_budgets"])
        self.assertFalse(data["candidate_first_remote_receipt_independently_proven"])
        self.assertFalse(data["future_cohort_admitted"])
        self.assertFalse(data["formal"])
        self.assertFalse(one["publish_implemented_here"])
        self.assertFalse(one["has_independent_first_receipt"])

    def test_candidate_contains_two_arms_but_no_result_key(self):
        prepared=s.package_time_guarded_research_result(
            self.audit,self.protocol,hypothetical_math(),self.temporal,self.after)
        content=json.loads(prepared["bytes"])
        self.assertEqual(set(content["arm_signed_F"]),set(self.protocol["mode_ticket_budgets"]))
        self.assertEqual(set(content["arm_ST_zero_control"]),set(self.protocol["mode_ticket_budgets"]))
        for forbidden in ("finish_order","result","payout","confirmed_result","winning_ticket"):
            self.assertNotIn('"'+forbidden+'"',prepared["bytes"].decode())

    def test_after_math_clock_out_of_order_or_too_late(self):
        for now in (
            self.before-timedelta(microseconds=1),
            datetime.fromisoformat("2026-11-12T19:47:00+09:00"),
            datetime.fromisoformat("2026-11-13T00:00:00+09:00"),
        ):
            with self.subTest(time=now.isoformat()):
                with self.assertRaisesRegex(ValueError,"finished_too_late"):
                    s.package_time_guarded_research_result(
                        self.audit,self.protocol,hypothetical_math(),self.temporal,now)

    def test_rejects_forged_formal_or_historical_mode_artifact(self):
        for field,value in (
            ("formal",True),("prospective_candidate_generated",True),
            ("results_or_payouts_read",True),
            ("registered_study_protocol_git_blob_sha1","0"*40),
            ("F_boats",0),("F_boats",True),
        ):
            m=hypothetical_math()
            m[field]=value
            with self.subTest(field=field,value=value):
                with self.assertRaisesRegex(ValueError,"not_pinned_and_result_blind"):
                    s.package_time_guarded_research_result(
                        self.audit,self.protocol,m,self.temporal,self.after)

    def test_invalid_120_board_ticket_row_duplicate_nonpermutation(self):
        for bad in ("1-1-2","1-2-7","junk","1-2"):
            m=hypothetical_math()
            m["math_4_modes_signed_F"]["hit"]["tickets"][0]["combo"]=bad
            m["math_4_modes_signed_F"]["hit"]["top1"]=bad
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError,"unranked_or_invalid_ticket"):
                    s.package_time_guarded_research_result(
                        self.audit,self.protocol,m,self.temporal,self.after)

    def test_rejects_invented_source_hash_or_missing_mode(self):
        m=hypothetical_math()
        m["source_original_sha256"]["odds120"]="not_hex"
        with self.assertRaisesRegex(ValueError,"unverifiable_original"):
            s.package_time_guarded_research_result(
                self.audit,self.protocol,m,self.temporal,self.after)
        m=hypothetical_math()
        del m["math_4_modes_signed_F"]["balance"]
        with self.assertRaisesRegex(ValueError,"four_modes_missing"):
            s.package_time_guarded_research_result(
                self.audit,self.protocol,m,self.temporal,self.after)

    def test_actual_runner_rejects_past_before_math_never_calls_ranker(self):
        older=copy.deepcopy(self.audit)
        older["race_code"]="202611111911"
        for k in ("official_deadline_jst","cutoff_jst","racelist_received_jst",
                  "beforeinfo_received_jst","odds_received_jst",
                  "latest_original_received_jst"):
            older[k]=older[k].replace("2026-11-12","2026-11-11")
        with patch.object(s,"require_registered_signed_F_method",return_value=self.protocol):
            with patch.object(s,"audit_three_originals",return_value=older):
                with patch.object(s,"archived_signed_F_four_mode_math_only") as math_method:
                    with self.assertRaisesRegex(ValueError,"cutoff_or_current_clock"):
                        s.run_one_shot_unpublished(
                            "card","before","odds",lambda:None,
                            lambda:datetime.fromisoformat("2026-11-11T19:45:00+09:00"))
                    math_method.assert_not_called()

    def test_actual_runner_never_remote_writes_even_future_mock(self):
        m=hypothetical_math()
        with patch.object(s,"require_registered_signed_F_method",return_value=self.protocol):
            with patch.object(s,"audit_three_originals",return_value=self.audit):
                with patch.object(s,"archived_signed_F_four_mode_math_only",return_value=m) as cb:
                    observations=iter([self.before,self.after])
                    prepared=s.run_one_shot_unpublished(
                        "card","before","odds",lambda:None,lambda:next(observations))
                    self.assertEqual(prepared["status"],"locally_prepared_unpublished_UNVERIFIED")
                    self.assertEqual(cb.call_count,1)
                    self.assertFalse(prepared["future_cohort_admitted"])


if __name__=="__main__":
    unittest.main()
