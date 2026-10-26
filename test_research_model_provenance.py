import hashlib
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
import research_model


class ModelIdentityTests(unittest.TestCase):
    def test_git_model_identity_is_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"research_model.py").write_text("VALUE=1\n")
            subprocess.run(["git","init","-q"],cwd=root,check=True)
            subprocess.run(["git","add","research_model.py"],cwd=root,check=True)
            subprocess.run(["git","-c","user.name=test","-c",
                            "user.email=test@example.invalid","commit","-qm","init"],cwd=root,check=True)
            with patch.object(research_model,"__file__",str(root/"research_model.py")):
                proof=research_model.model_provenance()
                self.assertEqual(proof["model_source_sha256"],
                                 hashlib.sha256((root/"research_model.py").read_bytes()).hexdigest())
                self.assertEqual(len(proof["model_git_sha"]),40)
                (root/"research_model.py").write_text("VALUE=2\n")
                with self.assertRaisesRegex(ValueError,"differs from Git HEAD"):
                    research_model.model_provenance()
if __name__=="__main__":
    unittest.main()
