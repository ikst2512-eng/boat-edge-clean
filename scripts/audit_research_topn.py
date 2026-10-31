"""Strict read-only audit of archived CLEAN research predictions against confirmed results."""
import json
from urllib.request import urlopen

BASE="https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/"
RACES=("202610310201","202610310202")
def get(path):
    with urlopen(BASE+path,timeout=25) as response:
        return json.load(response)
def audit():
    records=[]
    for code in RACES:
        prediction=get("prospective_predictions/"+code+".json")
        result=get("confirmed_results/"+code+".json")
        assert prediction["race_code"]==result["race_code"]==code
        assert prediction["formal"] is False and prediction["scoring"] is False
        assert prediction["status"]=="prospective_candidate"
        assert result["status"]=="confirmed"
        picks=prediction["predictions"]
        assert len(picks)==10 and len(set(picks))==10
        assert all(len(x.split("-"))==3 and len(set(x.split("-")))==3 for x in picks)
        finish="-".join(map(str,result["finish_order"]))
        assert len(set(result["finish_order"]))==3
        records.append((code,finish,picks))
    for n in (3,5,10):
        hits=sum(finish in picks[:n] for _,finish,picks in records)
        print(f"RESEARCH_ONLY_TOP{n}: {hits}/{len(records)} ({hits/len(records):.1%}); formal_scoring=false")
    for code,finish,picks in records:
        print(f"{code}: result={finish} rank={picks.index(finish)+1 if finish in picks else 'outside_top10'}")
if __name__=="__main__":
    audit()
