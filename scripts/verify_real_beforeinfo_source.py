"""Read actual BoatraceCSV source files, never fixture data, and report schema/evidence."""
import json
import sys
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clean_racecard import _preview_rows

def main(day=None):
    day=day or (datetime.now(ZoneInfo("Asia/Tokyo"))-timedelta(days=1)).strftime("%Y/%m/%d.csv")
    evidence={}
    for kind in ("tkz","stt","sui"):
        rows,sha=_preview_rows(kind,day)
        if not rows:
            raise RuntimeError(kind+": no source rows")
        keys=rows[0].keys()
        expected={"レースコード","締切時刻","取得日時"}
        if kind=="tkz":
            expected|={"艇1_展示タイム","艇1_チルト"}
        if kind=="stt":
            expected|={"艇1_コース","艇1_スタート展示"}
        if not expected.issubset(keys):
            raise RuntimeError(kind+": unexpected columns "+str(sorted(expected-set(keys))))
        evidence[kind]={"rows":len(rows),"sha256":sha,"first_race":rows[0]["レースコード"],
                        "columns_verified":sorted(expected)}
    print(json.dumps({"source":"BoatraceCSV real HTTPS","day":day,"evidence":evidence},ensure_ascii=False))
if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else None)
