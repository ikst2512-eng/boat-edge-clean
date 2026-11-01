import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ai_repair_agent import apply, parse_patches, propose
import json


class RepairAgentTests(unittest.TestCase):
    def test_disallow_model_or_workflow_edits(self):
        for path in ("clean_four_modes.py", ".github/workflows/deploy-pages.yml", "../server.py", "tests/site-regression.cjs"):
            with self.assertRaises(ValueError):
                parse_patches([{"path":path,"old":"x","new":"y"}])

    def test_unique_exact_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"navigation.js").write_text("alpha beta gamma")
            changed=apply(root,[{"path":"navigation.js","old":"beta","new":"delta"}])
            self.assertEqual(changed,["navigation.js"])
            self.assertEqual((root/"navigation.js").read_text(),"alpha delta gamma")

    def test_duplicate_replacement_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"navigation.js").write_text("same same")
            with self.assertRaisesRegex(ValueError,"not_unique"):
                apply(root,[{"path":"navigation.js","old":"same","new":"changed"}])

    def test_multi_file_failure_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"navigation.js").write_text("safe")
            (root/"secondary_navigation.js").write_text("xxx")
            with self.assertRaises(ValueError):
                apply(root,[{"path":"navigation.js","old":"safe","new":"changed"},
                            {"path":"secondary_navigation.js","old":"missing","new":"changed"}])
            self.assertEqual((root/"navigation.js").read_text(),"safe")

    def test_mock_ai_can_propose_exact_patch_without_paid_api(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n):
                return json.dumps({"output":[{"type":"message","content":[
                    {"type":"output_text","text":json.dumps({
                        "patches":[{"path":"navigation.js","old":"alpha","new":"beta"}],
                        "reason":"test fixture","tests":"navigation contract"})}
                ]}]}).encode()
        def fake_transport(req,timeout):
            payload=json.loads(req.data)
            self.assertFalse(payload["store"])
            self.assertIn("json_object",json.dumps(payload["text"]))
            self.assertIn("navigation.js",payload["input"])
            return FakeResponse()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"navigation.js").write_text("alpha")
            result=propose("navigation sample",root,"fake-key","gpt-4.1-mini",fake_transport)
            self.assertEqual(result["status"],"proposed")
            self.assertEqual(result["changed_files"],["navigation.js"])
            self.assertFalse(result["production_change_allowed"])
            self.assertEqual((root/"navigation.js").read_text(),"beta")

    def test_mock_ai_rejects_disallowed_workflow_edit(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self,n):
                return json.dumps({"output":[{"type":"message","content":[
                    {"type":"output_text","text":json.dumps({
                        "patches":[{"path":".github/workflows/ai-repair-proposal.yml",
                                    "old":"a","new":"b"}]})}
                ]}]}).encode()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"unsafe_path"):
                propose("change workflows",directory,"fake-key","gpt-4.1-mini",
                        lambda req,timeout:FakeResponse())

    def test_no_api_key_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            def forbidden(*args,**kwargs):
                raise AssertionError("network unexpectedly called")
            self.assertEqual(propose("fix navigation",directory,None,"test",forbidden)["status"],"disabled")


if __name__ == "__main__":
    unittest.main()
