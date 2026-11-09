"""Regression tests for read-only static scheduled transitive source tracing."""
import unittest
from scripts.audit_t12_scheduled_transitive_routes import (
    inspect, job_commands, literal_links, python_links, module_path, dynamic_process_sites,
)

PREFIX = ".github/workflows/"
SCHEDULED = b"""name: periodic
on:
  schedule:
    - cron: '*/5 * * * *'
jobs:
  observe:
    runs-on: ubuntu-latest
    steps:
      - run: python -m scripts.entry
"""
MANUAL = b"""name: manual
on:
  workflow_dispatch:
jobs:
  run:
    steps:
      - run: python -m scripts.capture_official_racelist_receipt
"""


def report(files, workflows=None):
    workflows = workflows or {PREFIX+"periodic.yml": SCHEDULED,
                              PREFIX+"manual.yml": MANUAL}
    files = {**files, **workflows}
    return inspect(workflows, files, files.get, strict=False)


class TransitiveStaticSafety(unittest.TestCase):
    def test_pinned_fixture_has_only_one_schedule(self):
        result = report({"scripts/entry.py": b"import json\n"})
        self.assertEqual(result["scheduled_workflows"], 1)
        self.assertEqual(result["scheduled_with_candidate_chain"], 0)
        self.assertFalse(result["formal"])
        self.assertFalse(result["no_indirect_capture_proven"])
        self.assertIsNone(result["formal_accuracy_denominator"])

    def test_two_hop_official_racelist_module_is_flagged(self):
        result = report({
            "scripts/entry.py": b"from scripts.intermediate import go\n",
            "scripts/intermediate.py": b"from scripts.capture_official_racelist_receipt import capture\n",
            "scripts/capture_official_racelist_receipt.py": b"HOST='/owpc/pc/race/racelist'\n",
        })
        paths = result["rows"][0]["racelist_candidate_chains"]
        self.assertTrue(any(x["file"] == "scripts/capture_official_racelist_receipt.py"
                            and x["via"] == [PREFIX+"periodic.yml", "scripts/entry.py",
                                             "scripts/intermediate.py",
                                             "scripts/capture_official_racelist_receipt.py"]
                            for x in paths))

    def test_false_metadata_path_not_a_job(self):
        workflow = b"""on:
  schedule:
    - cron: '0 0 * * *'
  pull_request:
    paths:
      - scripts/capture_official_racelist_receipt.py
jobs:
  audit:
    steps:
      - run: python -m scripts.entry
"""
        result = report({"scripts/entry.py": b"print('ok')\n",
                         "scripts/capture_official_racelist_receipt.py": b"pass\n"},
                        {PREFIX+"metadata.yml": workflow})
        self.assertEqual(result["scheduled_with_candidate_chain"], 0)

    def test_manual_capture_is_not_scheduled(self):
        result = report({"scripts/entry.py": b"pass\n",
                         "scripts/capture_official_racelist_receipt.py": b"pass\n"})
        self.assertEqual(len(result["rows"]), 1)
        self.assertNotIn("manual.yml", result["rows"][0]["workflow"])

    def test_dynamic_python_import_is_unknown_not_negative_proof(self):
        result = report({"scripts/entry.py": b"import importlib\nx=input()\nimportlib.import_module(x)\n"})
        self.assertIn("dynamic_import", result["rows"][0]["unresolved"])
        self.assertFalse(result["no_indirect_capture_proven"])

    def test_literal_process_call_follows_python_script(self):
        result = report({
            "scripts/entry.py": b"import subprocess\nsubprocess.run(['python', 'scripts/other.py'])\n",
            "scripts/other.py": b"from scripts.capture_official_racelist_receipt import capture\n",
            "scripts/capture_official_racelist_receipt.py": b"pass\n",
        })
        self.assertGreaterEqual(result["scheduled_with_candidate_chain"], 1)

    def test_local_workflow_uses_followed(self):
        start = b"""on:
  schedule:
    - cron: '0 0 * * *'
jobs:
  call:
    uses: ./.github/workflows/helper.yml
"""
        helper = b"""on:
  workflow_call:
jobs:
  test:
    steps:
      - run: python scripts/other.py
"""
        result = report({"scripts/other.py": b"from scripts.capture_official_racelist_receipt import capture\n",
                         "scripts/capture_official_racelist_receipt.py": b"pass\n"},
                        {PREFIX+"start.yml": start, PREFIX+"helper.yml": helper})
        self.assertEqual(result["scheduled_with_candidate_chain"], 1)

    def test_script_without_python_ast_is_not_silent_pass(self):
        result = report({"scripts/entry.py": b"this is not python !!!!\n"})
        self.assertIn("unparseable_python", result["rows"][0]["unresolved"])

    def test_unknown_event_fails_closed(self):
        with self.assertRaises(ValueError):
            report({}, {PREFIX+"bad.yml": b"name: unknown\non: {schedule: [{cron: '* * * * *'}]}\n"})

    def test_unexpected_full_inventory_fails_closed(self):
        with self.assertRaises(ValueError):
            inspect({PREFIX+"one.yml": SCHEDULED}, {}, lambda _: None, strict=True)

    def test_command_modules_resolve_only_tracked_file(self):
        paths = {"scripts/entry.py": "hash", "scripts/other.sh": "hash"}
        self.assertEqual(literal_links("python -m scripts.entry; bash scripts/other.sh", paths),
                         {"scripts/entry.py", "scripts/other.sh"})
        self.assertIsNone(module_path("os.path", paths))

    def test_job_parser_skips_unrelated_workflow_metadata(self):
        src = """on:\n  schedule:\n    - cron: '* * * * *'\njobs:\n  t:\n    steps:\n      - run: |\n          python scripts/entry.py\n      - uses: actions/checkout@v4\n"""
        runs, uses = job_commands(src)
        self.assertEqual(len(runs), 1)
        self.assertIn("python scripts/entry.py", runs[0])
        self.assertEqual(uses, ["actions/checkout@v4"])

    def test_python_imports_dont_trust_name_only_matches(self):
        links, problems = python_links("from scripts.intermediate import go\n",
                                     {"scripts/intermediate.py": "sha"})
        self.assertEqual(links, {"scripts/intermediate.py"})
        self.assertEqual(problems, set())


    def test_setup_action_only_is_tracked_not_cleared(self):
        workflow = b"""on:
  schedule:
    - cron: '0 * * * *'
jobs:
  audit:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: python -m scripts.entry
"""
        result = report({"scripts/entry.py": b"pass\n"}, {PREFIX+"setup.yml": workflow})
        row = result["rows"][0]
        self.assertTrue(row["only_external_action_unresolved"])
        self.assertEqual(result["scheduled_with_only_external_action_unknown"], 1)
        self.assertEqual(result["scheduled_with_non_external_unknown"], 0)
        self.assertEqual(result["unresolved_reason_workflow_counts"],
                         {"external_action_unexpanded": 1})
        self.assertEqual(result["scheduled_with_runtime_or_local_unknown"], 0)
        self.assertEqual(result["scheduled_with_only_expression_or_setup_unknown"], 1)
        self.assertEqual(row["external_other_action_refs"], [])
        self.assertEqual(len(row["external_setup_action_refs"]), 2)
        self.assertTrue(row["unresolved"])
        self.assertFalse(row["absence_proven"])
        self.assertFalse(result["no_indirect_capture_proven"])

    def test_custom_external_action_remains_unknown(self):
        workflow = b"""on:
  schedule:
    - cron: '0 * * * *'
jobs:
  audit:
    steps:
      - uses: third-party/capture@v1
      - uses: actions/checkout@v4
      - run: python -m scripts.entry
"""
        result = report({"scripts/entry.py": b"pass\n"}, {PREFIX+"custom.yml": workflow})
        row = result["rows"][0]
        self.assertEqual(row["external_other_action_refs"], ["third-party/capture@v1"])
        self.assertEqual(result["scheduled_with_other_external_action_refs"], 1)
        self.assertTrue(row["only_external_action_unresolved"])
        self.assertFalse(result["official_http_capture_proven"])

    def test_dynamic_import_not_hidden_by_setup_action(self):
        workflow = b"""on:
  schedule:
    - cron: '0 * * * *'
jobs:
  audit:
    steps:
      - uses: actions/setup-python@v5
      - run: python -m scripts.entry
"""
        entry = b"import importlib\nimportlib.import_module(input())\n"
        result = report({"scripts/entry.py": entry}, {PREFIX+"dynamic.yml": workflow})
        row = result["rows"][0]
        self.assertIn("dynamic_import", row["unresolved_non_external"])
        self.assertFalse(row["only_external_action_unresolved"])
        self.assertEqual(result["scheduled_with_non_external_unknown"], 1)
        self.assertEqual(result["scheduled_with_runtime_or_local_unknown"], 1)
        self.assertIn("dynamic_import", result["unresolved_reason_workflow_counts"])
        self.assertIn(PREFIX+"dynamic.yml", result["runtime_or_local_unknown_workflow_paths"])
        self.assertFalse(result["no_indirect_capture_proven"])

    def test_external_action_nested_reusable_workflow_keeps_unknown(self):
        workflow = b"""on:
  schedule:
    - cron: '0 * * * *'
jobs:
  audit:
    uses: ./.github/workflows/helper.yml
"""
        helper = b"""on:
  workflow_call:
jobs:
  audit:
    steps:
      - uses: vendor/custom@v2
      - run: python -m scripts.entry
"""
        result = report({"scripts/entry.py": b"pass\n"},
                        {PREFIX+"start.yml": workflow, PREFIX+"helper.yml": helper})
        row = next(x for x in result["rows"] if x["workflow"] == PREFIX+"start.yml")
        self.assertIn("vendor/custom@v2", row["external_action_refs"])
        self.assertIn("external_action_unexpanded", row["unresolved"])
        self.assertFalse(result["no_indirect_capture_proven"])


    def test_expression_is_not_a_false_capture_certificate(self):
        workflow = b"""on:
  schedule:
    - cron: '0 * * * *'
jobs:
  audit:
    steps:
      - uses: actions/checkout@v4
      - run: echo "${{ github.run_id }}"
"""
        result = report({}, {PREFIX+"expressions.yml": workflow})
        self.assertEqual(result["scheduled_with_only_expression_or_setup_unknown"], 1)
        self.assertEqual(result["scheduled_with_runtime_or_local_unknown"], 0)
        self.assertEqual(result["unresolved_reason_workflow_counts"],
                         {"dynamic_workflow_expression": 1, "external_action_unexpanded": 1})
        self.assertFalse(result["no_indirect_capture_proven"])

    def test_network_shell_is_prioritized_but_no_http_capture_claim(self):
        workflow = b"""on:
  schedule:
    - cron: '0 * * * *'
jobs:
  audit:
    steps:
      - uses: actions/checkout@v4
      - run: curl https://example.invalid/check
"""
        result = report({}, {PREFIX+"network.yml": workflow})
        self.assertEqual(result["scheduled_with_runtime_or_local_unknown"], 1)
        self.assertEqual(result["scheduled_with_only_expression_or_setup_unknown"], 0)
        self.assertIn(PREFIX+"network.yml", result["runtime_or_local_unknown_workflow_paths"])
        self.assertFalse(result["official_http_capture_proven"])
        self.assertFalse(result["formal"])


    def test_dynamic_git_callsite_includes_source_path_and_line(self):
        result = report({"scripts/entry.py": (
            b"import subprocess\n"
            b"sha = 'missing'\n"
            b"subprocess.run(['git', 'show', sha])\n"
        )})
        row = result["rows"][0]
        self.assertEqual(row["dynamic_subprocess_site_count"], 1)
        site = row["dynamic_subprocess_sites"][0]
        self.assertEqual(site["file"], "scripts/entry.py")
        self.assertEqual(site["line"], 3)
        self.assertEqual(site["via"], [PREFIX+"periodic.yml", "scripts/entry.py"])
        self.assertEqual(site["bucket"], "git_with_dynamic_arguments")
        self.assertEqual(result["dynamic_subprocess_workflow_bucket_counts"]
                         ["git_with_dynamic_arguments"], 1)
        self.assertTrue(site["potential_external_effects_unverified"])
        self.assertFalse(result["no_indirect_capture_proven"])

    def test_dynamic_http_client_is_not_proven_official_receipt(self):
        result = report({"scripts/entry.py": (
            b"import subprocess\n"
            b"subprocess.run(['curl', target_url])\n"
        )})
        site = result["rows"][0]["dynamic_subprocess_sites"][0]
        self.assertEqual(site["bucket"], "http_client_with_dynamic_arguments")
        self.assertEqual(site["literal_executable"], "curl")
        self.assertFalse(result["official_http_capture_proven"])
        self.assertFalse(result["formal"])

    def test_dynamic_executable_expression_keeps_unknown(self):
        result = report({"scripts/entry.py": (
            b"import subprocess\n"
            b"subprocess.Popen(command)\n"
        )})
        site = result["rows"][0]["dynamic_subprocess_sites"][0]
        self.assertEqual(site["api"], "subprocess.Popen")
        self.assertEqual(site["bucket"], "executable_expression_unknown")
        self.assertIsNone(site["literal_executable"])
        self.assertIn("dynamic_subprocess", result["rows"][0]["unresolved"])

    def test_static_literal_process_is_not_a_dynamic_site(self):
        src = "import subprocess\nsubprocess.run(['git', 'status'])\n"
        self.assertEqual(dynamic_process_sites(src), [])
        self.assertFalse(report({"scripts/entry.py": src.encode()})["formal"])

    def test_transitive_process_site_preserves_call_chain(self):
        result = report({
            "scripts/entry.py": b"from scripts.helper import launch\n",
            "scripts/helper.py": b"import subprocess\nsubprocess.run(['python', task])\n",
        })
        site = result["rows"][0]["dynamic_subprocess_sites"][0]
        self.assertEqual(site["bucket"], "python_shell_with_dynamic_arguments")
        self.assertEqual(site["via"], [PREFIX+"periodic.yml", "scripts/entry.py",
                                        "scripts/helper.py"])
        self.assertFalse(result["new_forecast_remote_acceptance_proven"])

    def test_unparseable_script_does_not_become_verified_absence(self):
        result = report({"scripts/entry.py": b"invalid python !!!\n"})
        row = result["rows"][0]
        self.assertEqual(row["dynamic_subprocess_site_count"], 0)
        self.assertIn("unparseable_python", row["unresolved"])
        self.assertFalse(row["absence_proven"])


if __name__ == "__main__":
    unittest.main()
