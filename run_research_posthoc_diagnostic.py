"""Historical diagnostic only; candidate was designed after these events."""
import json
from pathlib import Path
from research_posthoc_diagnostic import paired_diagnostic
from research_results_scorecard import _results

def main():
    records=[json.loads(p.read_text(encoding="utf-8"))
             for p in sorted(Path("research_snapshots").glob("*.json"))]
    result={}
    errors={}
    for day in sorted({row["race_code"][:8] for row in records}):
        try:
            result.update({key:value["ticket"] for key,value in _results(day).items() if value["ticket"]})
        except (OSError, ValueError, TimeoutError) as exc:
            errors[day]=str(type(exc).__name__)
    output=paired_diagnostic(records,result)
    output["result_errors"]=errors
    print(json.dumps(output,ensure_ascii=False))

if __name__=="__main__":
    main()
