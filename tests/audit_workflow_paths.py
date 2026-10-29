"""Fail on dangling local workflow path filters. Only literal file paths checked."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
WORKFLOWS=ROOT/".github/workflows"
missing=[]
for workflow in sorted(WORKFLOWS.glob("*.yml")):
    text=workflow.read_text(encoding="utf-8")
    for raw in text.splitlines():
        m=re.match(r"^\s*-\s+['\"]?((?:scripts/|tests/|\.github/workflows/)[\w./-]+\.(?:py|cjs|yml|yaml))['\"]?\s*$",raw)
        if m and not (ROOT/m.group(1)).is_file():
            missing.append(f"{workflow.relative_to(ROOT)} -> {m.group(1)}")
if missing:
    raise SystemExit("DANGLING_WORKFLOW_REFERENCES:\n"+"\n".join(missing))
print(f"PASS: {len(list(WORKFLOWS.glob('*.yml')))} CLEAN workflows have no dangling literal path filters")
