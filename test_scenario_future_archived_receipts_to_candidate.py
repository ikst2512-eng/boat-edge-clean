"""No remote write. Test the archived source -> #1710 gateway bridge.

The happy-case originals are synthetic, with injected parser/auditor stubs.
A pinned real parser must be used by the CLI; mock-only success is NOT a
real official forecast, T12 proof, or independent prospective credit.
"""
import base64
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from scenario_future_archived_receipts_to_candidate import (
    FILES, RECEIPT_URL_KEYS, build_archive_bundle, run_observed_archives,
    _pinned_imports,
)
from test_scenario_future_three_original_gateway import (
    future_synthetic, triple_fixture,
)


class ArchivedTripleSourceOperatorTests(unittest.TestCase):
    def setUp(self):
        self.source,self.candidate=future_synthetic()
        self.audit=triple_fixture(self.source)
        self.d=tempfile.TemporaryDirectory()
        root=Path(self.d.name)
        self.dirs={key:root/key for key in FILES}
        originals=self.source["originals"]
        for kind,folder in self.dirs.items():
            folder.mkdir()
            raw=base64.b64decode(originals[kind]["raw_base64"],validate=True)
            manifest={
                "race_code":self.source["race_code"],
                RECEIPT_URL_KEYS[kind]:originals[kind]["source_url"],
                "received_at_jst":originals[kind]["received_at_jst"],
                "sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),
            }
            (folder/FILES[kind]).write_bytes(raw)
            (folder/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
        self.calls=[]
        self.clock_times=[
            datetime.fromisoformat("2026-11-11T15:07:00+09:00"),
            datetime.fromisoformat("2026-11-11T15:08:00+09:00"),
        ]

    def tearDown(self):
        self.d.cleanup()

    def audit_fake(self,*args):
        self.calls.append("audit")
        return self.audit

    def parse_before_fake(self,raw,code):
        self.calls.append("before")
        features=self.source["normalized_source_claim"]
        return {key:features[key] for key in (
            "beforeinfo_registration_ids","exhibition_courses",
            "exhibition_times","exhibition_st","exhibition_tilts")} | {
                "deadline_display":"15:30"}

    def parse_card_fake(self,raw):
        self.calls.append("card")
        ids=self.source["normalized_source_claim"]["racelist_registration_ids"]
        return {"six_racers_verified":True,
                "registrations_by_lane":{str(i):x for i,x in enumerate(ids,1)}}

    def parse_odds_fake(self,html):
        self.calls.append("odds")
        return self.source["normalized_source_claim"]["odds_3t"]

    def run_bundle(self, **kwargs):
        return build_archive_bundle(
            self.dirs["racelist"],self.dirs["beforeinfo"],self.dirs["odds120"],
            self.candidate["generated_at_jst"],
            auditor=kwargs.get("auditor",self.audit_fake),
            before_parser=kwargs.get("before_parser",self.parse_before_fake),
            card_parser=kwargs.get("card_parser",self.parse_card_fake),
            odds_parser=kwargs.get("odds_parser",self.parse_odds_fake),
        )

    def test_archived_three_source_adapter_preserves_original_bytes_and_clock(self):
        audit,source,candidate=self.run_bundle()
        self.assertEqual(audit,self.audit)
        self.assertEqual(source,self.source)
        self.assertEqual(candidate,self.candidate)
        self.assertEqual(self.calls,["audit","before","card","odds"])

    def test_incomplete_triple_never_calls_parsers(self):
        bad=dict(self.audit)
        bad["all_research_components_observed_by_t12"]=False
        bad["missing_components"]=["start_exhibition_six"]
        with self.assertRaisesRegex(ValueError,"three_official_T12_originals_incomplete"):
            self.run_bundle(auditor=lambda *args:bad)
        self.assertEqual(self.calls,[])

    def test_source_manifest_modified_or_cross_race_fails(self):
        manifest_path=self.dirs["racelist"]/"manifest.json"
        meta=json.loads(manifest_path.read_text())
        meta["sha256"]="0"*64
        manifest_path.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError,"official_receipt_raw_hash"):
            self.run_bundle()
        meta["sha256"]=self.source["originals"]["racelist"]["sha256"]
        meta["race_code"]="202611111711"
        manifest_path.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError,"cross_race_archived_manifest"):
            self.run_bundle()

    def test_wrong_registrations_fails_before_math(self):
        def wrong_card(raw):
            value=self.parse_card_fake(raw)
            value["registrations_by_lane"]["3"]="9999"
            return value
        with self.assertRaisesRegex(ValueError,"registration_ids_differ"):
            self.run_bundle(card_parser=wrong_card)

    def test_missing_start_ST6_is_not_imputed(self):
        def parser(raw,code):
            obj=self.parse_before_fake(raw,code)
            obj["exhibition_st"]=obj["exhibition_st"][:-1]
            return obj
        with self.assertRaises(ValueError):
            # An independent official parser must reject incomplete ST6; the
            # source replay is expected to fail once it rechecks the bytes.
            audit,source,candidate=self.run_bundle(before_parser=parser)
            from scenario_official_exhibition_projection import project_exhibition_research
            from test_scenario_official_exhibition_projection import replay_stub
            project_exhibition_research(source,candidate,replay_stub)

    def test_early_or_prior_race_is_never_accepted(self):
        with self.assertRaisesRegex(ValueError,"wrong_day"):
            build_archive_bundle(
                *self.dirs.values(),"2026-11-10T15:07:00+09:00",
                auditor=self.audit_fake,before_parser=self.parse_before_fake,
                card_parser=self.parse_card_fake,odds_parser=self.parse_odds_fake)

    def test_real_pinned_1693_1698_math_receipts_to_four_mode_digest(self):
        if os.environ.get("RESEARCH_1698_PIN_REQUIRED")!="1":
            self.skipTest("only run after exact #1698 model has been fetched by CI")
        import position_sensitive_conditioned_lab
        from test_scenario_official_exhibition_projection import replay_stub
        ticks=iter(self.clock_times)
        summary=run_observed_archives(
            *self.dirs.values(),lambda:next(ticks),
            replay_stub,self.parse_before_fake,
            position_sensitive_conditioned_lab.experimental_conditional_board,
            auditor=self.audit_fake,card_parser=self.parse_card_fake,
            odds_parser=self.parse_odds_fake)
        self.assertEqual(summary["status"],"complete_source_model_handoff_local_only")
        self.assertEqual(summary["race_code"],"202611111710")
        self.assertEqual(summary["four_mode_ticket_budgets"],
                         {"narrow":5,"hit":10,"balance":16,"hole":22})
        self.assertEqual(len(summary["candidate_sha256"]),64)
        self.assertEqual(len(summary["candidate_git_blob_sha1"]),40)
        self.assertFalse(summary["github_create_attempted"])
        for key in ("candidate_first_remote_receipt_verified",
                    "official_source_first_remote_receipts_independently_verified",
                    "formal","eligible_for_300_plus_300",
                    "model_improvement_proven","production_changed"):
            self.assertIs(summary[key],False)

    def test_external_parser_import_requires_exact_source_blobs(self):
        if os.environ.get("RESEARCH_1698_PIN_REQUIRED")!="1":
            self.skipTest("requires both pinned #1693 and #1698 fetched in CI")
        from scenario_future_local_candidate_handoff import PROTOCOL_PATH
        p=json.loads(PROTOCOL_PATH.read_text())
        path1693=os.environ["RUNNER_TEMP"]+"/semantic1693"
        path1698=os.environ["RUNNER_TEMP"]+"/position1698"
        from unittest.mock import patch
        import sys
        # Do not run this in same interpreter after 1698 integration tests
        # have already imported the model under the original module name.
        for name in ("four_mode_official_future_lineage_preflight",
                     "four_mode_official_raw_semantic_replay",
                     "position_sensitive_conditioned_lab"):
            sys.modules.pop(name,None)
        replay,before,conditional=_pinned_imports(path1693,path1698,p)
        self.assertTrue(callable(replay))
        self.assertTrue(callable(before))
        self.assertTrue(callable(conditional))


if __name__=="__main__":
    unittest.main()
