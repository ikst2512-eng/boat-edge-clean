"""Read-only evaluation of independently collected CLEAN prospective candidates.

Not official formal forecast performance. Requires immutable Git first-add
audit and validated confirmed CLEAN result, never post-hoc forecast generation.
"""
import json
from pathlib import Path
from audit_clean_first_add import inspect
from clean_results import read_result

ROOT=Path(__file__).resolve().parent

def evaluate(code, root=ROOT):
    if not isinstance(code,str) or len(code)!=12 or not code.isascii() or not code.isdigit():
        raise ValueError("invalid race code")
    path="prospective_predictions/"+code+".json"
    audit=inspect(path,root)
    archive=root/path
    if archive.is_symlink() or archive.stat().st_size>20000:
        raise ValueError("invalid candidate")
    candidate=json.loads(archive.read_text(encoding="utf-8"))
    tickets=candidate.get("predictions")
    if (not isinstance(tickets,list) or len(tickets)!=10 or len(set(tickets))!=10
        or any(not isinstance(t,str) or len(t.split("-"))!=3 or
               len(set(t.split("-")))!=3 or any(ch not in "123456" for ch in t.split("-")) for t in tickets)):
        raise ValueError("invalid prospective predictions")
    status,result=read_result(code[:8],code[8:10],code[10:])
    if status!=200 or result.get("race_code")!=code or result.get("status")!="confirmed":
        return {"race_code":code,"status":"result_unavailable","formal":False,
                "scoring_kind":"prospective_research_only","audited":True}
    winning="-".join(map(str,result["finish_order"]))
    rank=tickets.index(winning)+1 if winning in tickets else None
    return {"race_code":code,"status":"evaluated","formal":False,
            "scoring_kind":"prospective_research_only","audited":True,
            "first_add_sha":audit["first_add_sha"],
            "winning_ticket":winning,"rank":rank,
            "top3":rank is not None and rank<=3,
            "top5":rank is not None and rank<=5,
            "top10":rank is not None and rank<=10}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("codes",nargs="+")
    a=p.parse_args()
    print(json.dumps([evaluate(code) for code in a.codes],ensure_ascii=False))
