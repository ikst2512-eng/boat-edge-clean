"""Synthetic-only tests for frozen local research candidate handoff.

No official source, real race result, remote Git write, or independent
first receipt is claimed. The pinned #1698 integration case lives in the
existing future-three-original-gateway test suite.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from itertools import permutations
from unittest.mock import patch

import scenario_future_local_candidate_handoff as handoff

from scenario_future_local_candidate_handoff import (
    prepare_local_candidate, SCHEMA, MIN_REMAINING_SECONDS,
)
from test_scenario_future_protocol_freeze import read_protocol

CODE="202611111710"
GENERATED="2026-11-11T15:07:00+09:00"
FROZEN="2026-11-11T15:08:00+09:00"
MODES={"narrow":5,"hit":10,"balance":16,"hole":22}
ALL=["-".join(map(str,x)) for x in permutations(range(1,7),3)]


def fake_gateway(p):
    signature=hashlib.sha256(json.dumps({
        "scenarios":p["scenario_hypotheses"],
        "weights":{mode:{world:float(v) for world,v in ws.items()}
                   for mode,ws in p["mode_weights"].items()},
    },sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    source={key:ch*64 for key,ch in [
        ("racelist","a"),("beforeinfo","b"),("odds120","c")]}
    modes={}
    for name,count in MODES.items():
        modes[name]={
            "top1":ALL[0],
            "research_board_sha256":"f"*64,
            "tickets":[{"combo":combo,"p":1.0} for combo in ALL[:count]],
        }
    return {
        "schema":"FUTURE_THREE_ORIGINAL_FOUR_MODE_RESEARCH_GATEWAY_V1",
        "study_id":p["study_id"],
        "race_code":CODE,
        "source_lineage_preflight":{
            "race_code":CODE,
            "cutoff_jst":"2026-11-11T15:18:00+09:00",
            "latest_three_original_receipt_claim_jst":"2026-11-11T15:03:00+09:00",
            "auditor_component_count":12,
            "registrations_matched_six":True,
            "exhibition_entry_permutation_matched":True,
            "initial_remote_candidate_receipt_verified":False,
            "source_sha256_claims":source,
            "formal":False,
        },
        "six_national_win_rates_from_same_original_html":[5.3,5.9,6.1,4.6,6.0,5.1],
        "model_input_content_sha256_research_only":"d"*64,
        "four_mode_ranked_output_content_sha256_research_only":"e"*64,
        "hypothesis_signature_sha256":signature,
        "research_mode_tickets":modes,
        "official_triple_source_auditor_reported_complete":True,
        "candidate_source_consumption_structurally_replayed":True,
        "national_win_rate_from_official_original_structurally_verified":True,
        **{key:False for key in (
            "formal","forecast_usable","calibrated_probabilities",
            "accuracy_improvement_proven","production_changed",
            "promotion_allowed","results_read",
            "candidate_remote_first_receipt_verified",
            "eligible_for_existing_1693_600_races",
            "eligible_for_new_300_plus_300_races",
            "hypotheses_frozen_in_prospective_registration",
            "official_data_real_or_independently_authenticated",
            "official_racelist_HTTP_authenticity_independently_verified",
            "source_to_candidate_remote_receipt_proven",
        )}
    }


class FutureLocalCandidateHandoffTests(unittest.TestCase):
    def setUp(self):
        self.p=read_protocol()
        self.g=fake_gateway(self.p)

    def prepared(self,g=None,p=None,generated=GENERATED,frozen=FROZEN):
        return prepare_local_candidate(
            self.g if g is None else g,self.p if p is None else p,
            generated,frozen)

    def test_synthetic_bytes_exact_stable_without_remote_claim(self):
        first,second=self.prepared(),self.prepared()
        self.assertEqual(first,second)
        self.assertEqual(first["path"],f"scenario_four_mode_research/{CODE}.json")
        self.assertEqual(len(first["sha256"]),64)
        self.assertEqual(len(first["git_blob_sha1"]),40)
        self.assertEqual(first["sha256"],hashlib.sha256(first["bytes"]).hexdigest())
        self.assertEqual(first["git_blob_sha1"],hashlib.sha1(
            b"blob "+str(len(first["bytes"])).encode()+b"\0"+first["bytes"]).hexdigest())
        row=json.loads(first["bytes"])
        self.assertEqual(row["schema"],SCHEMA)
        self.assertEqual([len(row["ranked_mode_tickets"][name]["tickets"])
                          for name in MODES],[5,10,16,22])
        self.assertTrue(first["no_remote_write_performed"])
        for flag in ("formal","promotion_allowed","candidate_first_remote_receipt_verified"):
            self.assertFalse(first[flag])
        self.assertFalse(row["first_remote_candidate_receipt_verified"])
        self.assertFalse(row["eligible_for_300_plus_300"])
        self.assertEqual(
            row["distinct_new_study_primary_metric"],
            "paired_top1_exact_trifecta_by_mode")
        self.assertEqual(
            row["prospective_metric_applicability_not_results"]["narrow"],
            {"top1":True,"top3":True,"top5":True,"top10":False})
        for mode in ("hit","balance","hole"):
            self.assertTrue(
                row["prospective_metric_applicability_not_results"][mode]["top10"])
        self.assertTrue(row["top10_for_narrow_must_never_mean_top5"])

    def test_hypothesis_or_method_or_blob_drift_is_rejected(self):
        g=copy.deepcopy(self.g)
        g["hypothesis_signature_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"coefficients"):
            self.prepared(g=g)
        p=copy.deepcopy(self.p)
        p["scenario_hypotheses"]["escape_wall"]["head_log_shifts"][0]=3.6
        with self.assertRaisesRegex(ValueError,"preregistered_protocol_argument_modified"):
            self.prepared(p=p)
        p=copy.deepcopy(self.p)
        del p["method_git_blob_sha1"]["research_model.py"]
        with self.assertRaisesRegex(ValueError,"preregistered_protocol_argument_modified"):
            self.prepared(p=p)

    def test_colluding_caller_cannot_replace_both_scenario_and_signature(self):
        # Before the fix this passed: attacker replaced both the supplied
        # protocol and its matching gateway signature. That would effectively
        # register a hindsight coefficient without a prior Git commit.
        changed=copy.deepcopy(self.p)
        changed["scenario_hypotheses"]["escape_wall"]["head_log_shifts"][0]=3.6
        gateway=fake_gateway(changed)
        with self.assertRaisesRegex(ValueError,"preregistered_protocol_argument_modified"):
            self.prepared(g=gateway,p=changed)
        changed=copy.deepcopy(self.p)
        changed["method_git_blob_sha1"]["research_model.py"]="a"*40
        with self.assertRaisesRegex(ValueError,"preregistered_protocol_argument_modified"):
            self.prepared(p=changed)
        changed=copy.deepcopy(self.p)
        changed["new_pilot_admitted"]=1
        with self.assertRaisesRegex(ValueError,"unregistered_or_postresult_candidate"):
            self.prepared(p=changed)

    def test_precommitted_protocol_bytes_are_not_silently_replaceable(self):
        original=handoff.PROTOCOL_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=root/"research"/handoff.PROTOCOL_PATH.name
            path.parent.mkdir(parents=True)
            path.write_bytes(original.replace(
                b'"registered_on_date_jst": "2026-11-10"',
                b'"registered_on_date_jst": "2026-11-11"'))
            with patch.object(handoff,"PROTOCOL_PATH",path):
                with self.assertRaisesRegex(ValueError,"preregistered_protocol_file_git_blob_mismatch"):
                    self.prepared()

    def test_unchanged_protocol_but_modified_model_code_is_rejected(self):
        # Completely isolated temp checkout, without touching actual repo.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            archive=root/"research"/handoff.PROTOCOL_PATH.name
            archive.parent.mkdir(parents=True)
            shutil.copy2(handoff.PROTOCOL_PATH,archive)
            for relative in self.p["method_git_blob_sha1"]:
                dest=root/relative
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(handoff.PROTOCOL_PATH.parent.parent/relative,dest)
            with patch.object(handoff,"PROTOCOL_PATH",archive):
                self.assertTrue(handoff.require_registered_study_and_unchanged_model(self.p))
                model=root/"research_model.py"
                model.write_bytes(model.read_bytes()+b"\\n# unregistered drift\\n")
                with self.assertRaisesRegex(ValueError,"preregistered_method_source_changed:research_model.py"):
                    self.prepared()

    def test_candidate_freeze_clock_strict_boundaries(self):
        for frozen in (
            "2026-11-11T15:06:59+09:00",
            "2026-11-11T15:17:00+09:00",
            "2026-11-11T15:17:59+09:00",
            "2026-11-11T15:19:00+09:00",
            "2026-11-11T15:08:00+00:00"):
            with self.subTest(frozen=frozen),self.assertRaises(ValueError):
                self.prepared(frozen=frozen)
        with self.assertRaises(ValueError):
            self.prepared(generated="2026-11-11T15:01:00+09:00")
        with self.assertRaises(ValueError):
            self.prepared(generated="2026-11-11T15:18:00+09:00")
        self.assertGreaterEqual(MIN_REMAINING_SECONDS,60)

    def test_outcome_nested_in_source_or_protocol_is_rejected(self):
        g=copy.deepcopy(self.g)
        g["source_lineage_preflight"]["aux"]=[{"winner":"1-2-3"}]
        with self.assertRaisesRegex(ValueError,"postresult"):
            self.prepared(g=g)
        p=copy.deepcopy(self.p)
        p["confirmed_result"]={"finish":[1,2,3]}
        with self.assertRaisesRegex(ValueError,"postresult"):
            self.prepared(p=p)

    def test_old_race_and_wrong_mode_budgets_are_rejected(self):
        g=copy.deepcopy(self.g)
        g["race_code"]="202611091710"
        g["source_lineage_preflight"]["race_code"]="202611091710"
        with self.assertRaisesRegex(ValueError,"source_lineage"):
            self.prepared(g=g)
        for mutation in ("one_missing","duplicate","top1_other","bad_combo","nan"):
            g=copy.deepcopy(self.g)
            tickets=g["research_mode_tickets"]["narrow"]["tickets"]
            if mutation=="one_missing":
                tickets.pop()
            elif mutation=="duplicate":
                tickets[1]["combo"]=tickets[0]["combo"]
            elif mutation=="top1_other":
                g["research_mode_tickets"]["narrow"]["top1"]="6-5-4"
            elif mutation=="bad_combo":
                tickets[0]["combo"]="1-1-2"
            else:
                tickets[0]["p"]=float("nan")
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                self.prepared(g=g)

    def test_fake_formal_or_remote_proof_blocks_export(self):
        for field in ("formal","results_read","production_changed",
                      "candidate_remote_first_receipt_verified",
                      "eligible_for_new_300_plus_300_races"):
            g=copy.deepcopy(self.g)
            g[field]=True
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,"promotion"):
                self.prepared(g=g)
        g=copy.deepcopy(self.g)
        g["source_lineage_preflight"]["source_sha256_claims"]["racelist"]="garbled"
        with self.assertRaisesRegex(ValueError,"digest"):
            self.prepared(g=g)


if __name__=="__main__":
    unittest.main()
