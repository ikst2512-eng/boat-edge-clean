"""Generate verified four-mode performance summary from immutable pre-race archives.

No archived forecast or verified first Git add => not eligible. Real confirmed
results and official 100-yen trifecta payout are mandatory.
"""
import json
from pathlib import Path
from four_mode_performance import evaluate,summary
from verification_pipeline import attest_first_git_add,read_json,validate_result,payout_for,save_atomic

ROOT=Path(__file__).resolve().parent

def run(root=ROOT,budget_yen=5000,payout_loader=payout_for,proof_checker=attest_first_git_add):
    archive_dir=root/"four_mode_forecasts"
    result_dir=root/"confirmed_results"
    records=[]
    counts={"archived":0,"awaiting_result":0,"awaiting_payout":0,"unverified":0,"complete":0}
    if archive_dir.exists():
        for path in sorted(archive_dir.glob("*.json")):
            if not path.stem.isdigit() or len(path.stem)!=12:continue
            counts["archived"]+=1
            try:
                archive=read_json(path)
                if archive.get("race_code")!=path.stem:raise ValueError("race_mismatch")
                # Original first Git add and exact on-disk bytes must both be unchanged.
                proof_checker(path,archive["deadline_jst"])
            except (ValueError,TypeError,KeyError,OSError,RuntimeError,Exception) as exc:
                counts["unverified"]+=1
                continue
            result_path=result_dir/(path.stem+".json")
            if not result_path.is_file():
                counts["awaiting_result"]+=1
                continue
            try:
                result=read_json(result_path)
                winner=validate_result(result,path.stem)
            except (ValueError,TypeError,KeyError,OSError):
                counts["awaiting_result"]+=1
                continue
            try:
                payout=payout_loader(path.stem,winner)
                entry=evaluate(archive,result,payout,budget_yen,first_add_verified=True)
            except Exception:
                counts["awaiting_payout"]+=1
                continue
            records.append(entry)
            counts["complete"]+=1
    output={"schema":"CLEAN_FOUR_MODE_PERFORMANCE_V1","simulated_only":True,
            "budget_yen":budget_yen,"counts":counts,"modes":summary(records)}
    save_atomic(root/"four_mode_performance"/"summary.json",output)
    return output

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--budget-yen",type=int,default=5000)
    args=ap.parse_args()
    print(json.dumps(run(budget_yen=args.budget_yen),ensure_ascii=False))
