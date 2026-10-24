"""Staging-only validation; intentionally never calls an external network or results API."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
receipt = root / ".github/workflows/research-pre-race-receipt.yml"
smoke = root / ".github/workflows/research-staging-smoke.yml"
notes = root / "research-capture/README.md"
for path in (receipt, smoke, notes):
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        raise SystemExit(f"MISSING_OR_EMPTY: {path}")
source = receipt.read_text(encoding="utf-8")
checks = {
    "manual_dispatch": "workflow_dispatch:" in source,
    "cutoff_12_min": "720 < remaining <=1200" in source,
    "completion_cutoff": "total_seconds()>720" in source,
    "source_hash": "source_sha256" in source,
    "results_block": "results content detected" in source,
    "local_clock_disclosure": '"runner_local_only"' in source,
    "no_forecast": '"forecast_generated":False' in source,
}
for name, ok in checks.items():
    print(f"{name}: {'PASS' if ok else 'FAIL'}")
if not all(checks.values()):
    raise SystemExit("STAGING_AUDIT_FAILED")
print("STAGING_AUDIT_PASS: No race captured; no result read; no forecast generated.")
