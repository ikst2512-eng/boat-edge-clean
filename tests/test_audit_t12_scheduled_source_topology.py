"""Bounded pinned real-main T−12 wiring regression: no fake auto triad."""
import unittest
from copy import deepcopy

from scripts.audit_t12_scheduled_source_topology import (
    PATHS, PINNED_MAIN, _events, audit, inspect
)


def fixtures():
    return dict(zip(PATHS, (
        """name: Research independent late preview evidence
on:
  pull_request:
    paths:
      - 'scripts/capture_joint_preview_batch.py'
  schedule:
    - cron: '*/5 0-12 * * *'
  workflow_dispatch:
permissions:
  contents: read
jobs:
  capture:
    steps:
      - name: Preserve official preview and odds originals
        run: python -m scripts.capture_joint_preview_batch
""",
        """name: Official three-original T12 live research observation
on:
  pull_request:
    paths: ['scripts/observe_three_official_t12_originals.py']
  workflow_dispatch:
    inputs:
      race_code:
        required: true
permissions:
  contents: read
jobs:
  observe:
    if: github.event_name == 'workflow_dispatch'
    steps:
      - run: |
          python -m scripts.observe_three_official_t12_originals --race-code "$RACE_CODE"
""",
        """name: Official racelist raw source observation
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
jobs:
  observe:
    steps:
      - run: |
          from scripts.capture_official_racelist_receipt import capture
""",
        """from scripts.capture_official_beforeinfo_json import capture as capture_before
from scripts.capture_official_odds_receipt import capture as capture_odds
from scripts.audit_joint_official_receipts import audit_pair

def collect():
    return capture_before, capture_odds
""",
        """from scripts.capture_official_beforeinfo_json import capture as before_capture
from scripts.capture_official_racelist_receipt import capture as racecard_capture
from scripts.capture_official_odds_receipt import capture as odds_capture

def observe():
    return before_capture, racecard_capture, odds_capture
""",
    )))


class ScheduledRealSourceTopology(unittest.TestCase):
    def test_real_pinned_topology_never_claims_auto_three_sources(self):
        result = inspect(fixtures())
        self.assertTrue(result["official_pair_has_scheduled_activation_config"])
        self.assertFalse(result["scheduled_official_pair_directly_captures_racelist"])
        self.assertTrue(result["scheduled_official_pair_directly_captures_beforeinfo"])
        self.assertTrue(result["scheduled_official_pair_directly_captures_odds"])
        self.assertFalse(result["dedicated_triple_observation_has_schedule"])
        self.assertTrue(result["dedicated_triple_observation_dispatch_only_job"])
        self.assertFalse(result["racelist_only_workflow_has_schedule"])
        self.assertTrue(result["racelist_only_workflow_also_has_path_scoped_push"])
        self.assertFalse(result["scheduled_two_original_path_proves_complete_same_race_triad"])
        self.assertFalse(result["other_repository_workflows_exhaustively_audited"])
        self.assertFalse(result["formal"])
        self.assertIsNone(result["formal_accuracy_denominator"])
        self.assertEqual(result["new_formal_certifications"], 0)

    def test_missing_remote_original_code_is_not_a_valid_topology(self):
        for key in PATHS:
            with self.subTest(path=key), self.assertRaises(ValueError):
                inspect({k:v for k,v in fixtures().items() if k!=key})
        data=fixtures()
        data["unexpected/source.py"]="bad"
        with self.assertRaises(ValueError):
            inspect(data)

    def test_source_files_must_be_nonempty_strings(self):
        data=fixtures()
        data[PATHS[0]]=""
        with self.assertRaises(ValueError):
            inspect(data)
        data=fixtures()
        data[PATHS[0]]=None
        with self.assertRaises(ValueError):
            inspect(data)

    def test_remote_ref_must_be_an_exact_commit_identity(self):
        for ref in (None, "main", "0"*64, "not-a-sha"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                inspect(fixtures(),ref)

    def test_scheduled_pair_workflow_cannot_masquerade_as_automatic_triple(self):
        data=fixtures()
        data[PATHS[0]] += "\n      - run: python -m scripts.observe_three_official_t12_originals\n"
        with self.assertRaises(ValueError):
            inspect(data)

    def test_official_racelist_import_in_pair_module_requires_reaudit(self):
        data=fixtures()
        data[PATHS[3]] += "\nfrom scripts.capture_official_racelist_receipt import capture\n"
        with self.assertRaises(ValueError):
            inspect(data)

    def test_official_pair_schedule_removed_or_changed_requires_reaudit(self):
        for replace in ("  workflow_dispatch:", "    - cron: '*/15 0-12 * * *'"):
            data=fixtures()
            data[PATHS[0]]=data[PATHS[0]].replace(
                "    - cron: '*/5 0-12 * * *'", replace)
            with self.subTest(replace=replace), self.assertRaises(ValueError):
                inspect(data)

    def test_dedicated_three_source_schedule_is_not_hidden(self):
        data=fixtures()
        data[PATHS[1]]=data[PATHS[1]].replace(
            "  workflow_dispatch:", "  schedule:\n    - cron: '*/5 0-12 * * *'\n  workflow_dispatch:")
        with self.assertRaises(ValueError):
            inspect(data)

    def test_manual_three_source_dispatch_gate_required(self):
        data=fixtures()
        data[PATHS[1]]=data[PATHS[1]].replace(
            "if: github.event_name == 'workflow_dispatch'", "if: always()")
        with self.assertRaises(ValueError):
            inspect(data)

    def test_racelist_workflow_push_is_not_a_schedule(self):
        data=fixtures()
        data[PATHS[2]]=data[PATHS[2]].replace("  push:", "  schedule:")
        with self.assertRaises(ValueError):
            inspect(data)

    def test_actual_three_capture_script_imports_all_three_originals(self):
        data=fixtures()
        data[PATHS[4]]=data[PATHS[4]].replace(
            "from scripts.capture_official_racelist_receipt import capture as racecard_capture",
            "# from scripts.capture_official_racelist_receipt import capture as racecard_capture")
        with self.assertRaises(ValueError):
            inspect(data)

    def test_bogus_workflow_event_declarations_fail(self):
        for source in ("name: test\non:\n  schedule:\non:\n  push:\n",
                       "name: test\non:\n  schedule:\n  schedule:\n",
                       "name: test\non:\npermissions:\n  contents: read\n"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                _events(source)

    def test_source_script_with_invalid_python_never_passes(self):
        data=fixtures()
        data[PATHS[3]]="from scripts.capture_official_beforeinfo_json import"
        with self.assertRaises(ValueError):
            inspect(data)

    def test_audit_fetches_five_exact_paths_under_same_git_commit(self):
        received=[]
        fixture=fixtures()
        def get(repo,token,ref,path):
            received.append((repo,token,ref,path))
            return fixture[path],"a"*40
        out=audit("ikst2512-eng/boat-edge-clean","token",PINNED_MAIN,fetch=get)
        self.assertEqual([v[-1] for v in received],list(PATHS))
        self.assertTrue(all(v[2]==PINNED_MAIN for v in received))
        self.assertFalse(out["remote_git_file_sha1_checked"])
        self.assertEqual(len(out["remote_git_file_blob_sha1"]),5)
        self.assertFalse(out["accuracy_scoring_allowed"])

    def test_bad_auth_or_repo_fails_without_any_fetch(self):
        fetch=lambda *args:self.fail("should never fetch invalid credentials")
        for repo,token,ref in (
            ("../repo","token",PINNED_MAIN),
            ("a/..","token",PINNED_MAIN),
            ("invalid","token",PINNED_MAIN),
            ("owner/repo",None,PINNED_MAIN),
            ("owner/repo","token","main"),
        ):
            with self.subTest(repo=repo), self.assertRaises(ValueError):
                audit(repo,token,ref,fetch=fetch)

    def test_missing_remote_original_sha_rejects_substitution(self):
        def bad(repo,token,ref,path):
            return fixtures()[path],"missing"
        with self.assertRaises(ValueError):
            audit("ikst2512-eng/boat-edge-clean","token",fetch=bad)


if __name__=="__main__":
    unittest.main()
