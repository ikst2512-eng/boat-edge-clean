"""Research-only trifecta model trained on frozen 1,000-race boat-index outcomes."""
import csv, io, math, json, os, hashlib, subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from itertools import permutations
from urllib.request import Request, urlopen
JST=timezone(timedelta(hours=9))
TICKETS=tuple(permutations(range(1,7),3))
COUNTS=tuple(map(int,"59,60,36,28,51,31,48,24,34,29,21,15,24,19,19,12,3,4,10,9,21,17,11,8,12,11,9,3,9,5,4,7,4,5,1,4,1,1,1,2,13,19,12,12,11,8,2,2,8,4,4,3,6,7,4,2,2,2,2,1,7,8,8,6,2,10,1,5,7,4,5,5,7,3,6,4,6,4,2,6,4,1,6,7,6,3,2,1,6,1,0,5,7,5,3,1,4,5,1,0,2,4,1,2,3,1,1,0,2,0,1,2,1,3,1,2,3,0,1,0".split(",")))
assert len(COUNTS)==120 and sum(COUNTS)==1000
WIN=[sum(c for t,c in zip(TICKETS,COUNTS) if t[0]==i) for i in range(1,7)]
BASE="https://boatracecsv.github.io/data/programs/"
def probabilities(rates,beta=0.4):
    if len(rates)!=6 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<v<20 for v in rates):
        raise ValueError("invalid six national win rates")
    avg=sum(rates)/6
    weights=[(WIN[i]+12)*math.exp(beta*(rates[i]-avg)) for i in range(6)]
    total=sum(weights)
    result=[(t,weights[t[0]-1]/total*(c+0.5)/(WIN[t[0]-1]+10)) for t,c in zip(TICKETS,COUNTS)]
    result.sort(key=lambda x:(-x[1],x[0]))
    if abs(sum(p for _,p in result)-1)>1e-10:raise ValueError("probabilities not normalized")
    return result
def read_rows(url):
    if not url.startswith(BASE):raise ValueError("untrusted URL")
    with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=8) as response:
        if response.status!=200:raise ValueError("source unavailable")
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError("source too large")
    return (list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))),
            datetime.now(JST), hashlib.sha256(raw).hexdigest())
STORE=Path(__file__).resolve().parent/"research_snapshots"
def model_provenance():
    root=Path(__file__).resolve().parent
    sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    if len(sha)!=40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("invalid model Git SHA")
    committed=subprocess.check_output(["git","show",sha+":research_model.py"],cwd=root)
    if committed!=(root/"research_model.py").read_bytes():
        raise ValueError("research model differs from Git HEAD")
    return {"model_git_sha":sha,"model_source_sha256":hashlib.sha256(committed).hexdigest(),
            "model_dependency_scope":"research_model.py_only_not_complete_environment"}

def _record_path(code):
    if len(code)!=12 or not code.isascii() or not code.isdigit():raise ValueError("invalid race code")
    return STORE/(code+".json")
def _saved(code):
    path=_record_path(code)
    if path.is_symlink() or not path.is_file():return None
    if path.stat().st_size>20000:raise ValueError("oversize forecast")
    record=json.loads(path.read_text(encoding="utf-8"))
    if record.get("race_code")!=code or record.get("status")!="research" or record.get("validated") is not False:
        raise ValueError("invalid saved forecast")
    tickets=record.get("predictions")
    if not isinstance(tickets,list) or len(tickets)!=10 or len(set(tickets))!=10:
        raise ValueError("invalid prediction list")
    valid={"-".join(map(str,t)) for t in TICKETS}
    if any(t not in valid for t in tickets):raise ValueError("invalid ticket")
    return {key:record[key] for key in ("ok","status","predictions","model_version","generated_at","message","validated")}
def predict(hd,jcd,rno):
    day=datetime.strptime(hd,"%Y%m%d").date()
    if day<=datetime(2026,10,21).date():raise ValueError("training date excluded")
    code=f"{hd}{int(jcd):02d}{int(rno):02d}"
    old=_saved(code)
    if old is not None:return old
    path=f"{hd[:4]}/{hd[4:6]}/{hd[6:8]}.csv"
    titles,t1,title_sha256=read_rows(BASE+"title/"+path)
    cards,t2,cards_sha256=read_rows(BASE+"race_cards/"+path)
    matching_t=[r for r in titles if r.get("レースコード")==code]
    matching_c=[r for r in cards if r.get("レースコード")==code]
    if len(matching_t)!=1 or len(matching_c)!=1:raise ValueError("race missing")
    deadline=datetime.strptime(hd+matching_t[0]["電話投票締切予定"],"%Y%m%d%H:%M").replace(tzinfo=JST)
    cutoff=deadline-timedelta(minutes=12)
    now=datetime.now(JST)
    if max(t1,t2,now)>cutoff:raise ValueError("not received before 12-minute cutoff")
    rates=[float(matching_c[0][f"艇{i}_全国勝率"]) for i in range(1,7)]
    predictions=["-".join(map(str,t)) for t,p in probabilities(rates)[:10]]
    result={"ok":True,"status":"research","predictions":predictions,
            "model_version":"national-beta0.4-exploratory-v1","generated_at":now.isoformat(),
            "message":"研究予想（未検証・回収率未確認）","validated":False}
    STORE.mkdir(parents=True,exist_ok=True)
    record=dict(result,race_code=code,cutoff_jst=cutoff.isoformat(),source_title_received_jst=t1.isoformat(),
                source_cards_received_jst=t2.isoformat(),national_win_rates=rates,source_title_sha256=title_sha256,
                source_cards_sha256=cards_sha256, input_sha256=hashlib.sha256(
                    (title_sha256+":"+cards_sha256).encode("ascii")
                ).hexdigest(), input_hash_scope="source_csv_byte_hashes_ordered_title_cards",
                **model_provenance())
    data=json.dumps(record,ensure_ascii=False,sort_keys=True)
    # SHA calculation and model provenance checks also consume time. Refuse a
    # record if the deadline safety margin elapsed before the actual write.
    if datetime.now(JST) > cutoff:
        raise ValueError("research snapshot write missed 12-minute cutoff")
    # Exclusive create: never silently replace a previously saved forecast.
    with _record_path(code).open("x",encoding="utf-8") as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    return result
