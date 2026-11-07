"""Offline fixed-cohort and fail-closed tests for 34 primary K exception targets."""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from scripts.research_official_k_all_34_exceptions import frozen_targets


def synth(root: Path):
    codes = [(date(2026, 8, 1) + timedelta(days=i)).strftime("%Y%m%d")
             + "03" + "01" for i in range(28)]
    codes.extend("20260801" + "03" + f"{i:02d}" for i in range(2, 8))
    ledger = {
        "period": "2026-08-01/2026-10-31",
        "source_days_sha_verified": 92,
        "official_K_rows_reconciled": 0,
        "T12_eligible": False,
        "exceptions": [
            {"race_code": c, "first_course_f_mark": i % 2 == 0}
            for i, c in enumerate(codes)
        ],
    }
    pages = [
        f"| 03 | {c} | {'Ｆ' if i % 2 == 0 else '転'} | [公式](https://www.boatrace.jp/result) |"
        for i, c in enumerate(codes)
    ]
    p = root / "exceptions.json"
    q = root / "pages.md"
    p.write_text(json.dumps(ledger), encoding="utf-8")
    q.write_text("\n".join(pages) + "\n", encoding="utf-8")
    return p, q


class TestAll34(unittest.TestCase):
    def test_fixed_34_in_28_distinct_dates(self):
        with tempfile.TemporaryDirectory() as t:
            p, q = synth(Path(t))
            result = frozen_targets(p, q)
            self.assertEqual(len(result), 28)
            self.assertEqual(sum(map(len, result.values())), 34)

    def test_missing_page_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p, q = synth(Path(t))
            q.write_text("\n".join(q.read_text().splitlines()[:-1]) + "\n")
            with self.assertRaisesRegex(ValueError, "page_evidence_cohort_differs"):
                frozen_targets(p, q)

    def test_page_F_conflict_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p, q = synth(Path(t))
            q.write_text(q.read_text().replace(" | Ｆ | ", " | 転 | ", 1))
            with self.assertRaisesRegex(ValueError, "first_course_F_page_status_disagreement"):
                frozen_targets(p, q)

    def test_untrusted_manifest_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p, q = synth(Path(t))
            data = json.loads(p.read_text())
            data["T12_eligible"] = True
            p.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "candidate_ledger_unfrozen"):
                frozen_targets(p, q)


if __name__ == "__main__":
    unittest.main()
