"""Fail closed on unreviewed expansion of CLEAN's legacy repository dependency.

This is a migration guard, NOT evidence that legacy data has been migrated.
The existing read-only URLs remain until equivalent CLEAN artifacts are proven.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
LEGACY_REPO = "ikst2512-eng/boat-edge"
LEGACY_PATTERN = re.compile(r"ikst2512-eng/boat-edge(?!-clean)")


class LegacyDependencyGuard(unittest.TestCase):
    def test_legacy_refs_are_limited_to_known_data_sources(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        expected = {
            "EDGE_BASE": "https://api.github.com/repos/" + LEGACY_REPO,
            "EDGE_RAW": "https://raw.githubusercontent.com/" + LEGACY_REPO,
        }
        for name, url in expected.items():
            self.assertIn("const " + name + "='" + url + "';", page)
        self.assertEqual(
            len(LEGACY_PATTERN.findall(page)), 2,
            "New or removed legacy references require data-producer and UI validation",
        )

    def test_runtime_python_and_workflows_do_not_reference_legacy(self):
        files = [*(p for p in ROOT.glob("*.py") if not p.name.startswith("test_")), *(ROOT / ".github/workflows").glob("*.yml")]
        for file in files:
            with self.subTest(file=str(file.relative_to(ROOT))):
                self.assertIsNone(
                    LEGACY_PATTERN.search(file.read_text(encoding="utf-8")),
                    "Runtime or workflow legacy dependency requires explicit review",
                )


if __name__ == "__main__":
    unittest.main()
