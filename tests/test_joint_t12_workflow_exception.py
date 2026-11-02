"""Guard against dropping audit evidence when the odds collector raises."""
from pathlib import Path
import unittest


class WorkflowExceptionTests(unittest.TestCase):
    def test_odds_exception_recorded_before_retry_gate(self):
        source = Path(".github/workflows/official-joint-t12-dispatch.yml").read_text()
        start = source.index("              try:\n                  b=odds(")
        end = source.index("              if b.get('status')", start)
        fragment = source[start:end]
        self.assertIn("except (OSError,ValueError,KeyError,TypeError,UnicodeError,TimeoutError)", fragment)
        self.assertIn("'status':'official_odds_capture_exception'", fragment)
        self.assertIn("'forecast_usable':False", fragment)
        self.assertIn("'t12_eligible':False", fragment)
        self.assertIn("Path(f'reports/odds_{i}.json').write_text", fragment)
        self.assertLess(fragment.index("except ("), fragment.index("Path(f'reports/odds_{i}.json').write_text"))
        self.assertIn("if can_retry(", source[end:])


if __name__ == "__main__":
    unittest.main()
