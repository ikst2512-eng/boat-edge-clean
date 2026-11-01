import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ai_repair_agent import apply, parse_patches, propose


class RepairAgentTests(unittest.TestCase):
    def test_disallow_model_or_workflow_edits(self):
        for path in ("clean_four_modes.py", ".github/workflows/deploy-pages.yml", "../server.py"):
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

    def test_no_api_key_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            def forbidden(*args,**kwargs):
                raise AssertionError("network unexpectedly called")
            self.assertEqual(propose("fix navigation",directory,None,"test",forbidden)["status"],"disabled")


if __name__ == "__main__":
    unittest.main()
