"""Fail-closed publication gate for new V2 frozen forecasts only."""
import json
import subprocess
from pathlib import Path

VERSION="CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
MODES=("narrow","hit","balance","hole")
COUNTS=(5,10,16,22)

def audit(paths):
    for path in paths:
        p=Path(path)
        if not p.is_file() or p.is_symlink() or p.stat().st_size>30000:
            raise ValueError("invalid_new_archive")
        data=json.loads(p.read_text(encoding="utf-8"))
        if data.get("race_code")!=p.stem or data.get("model_version")!=VERSION:
            raise ValueError("new_capture_model_version_or_identity_not_v2")
        modes=data.get("modes")
        if not isinstance(modes,dict) or set(modes)!=set(MODES):
            raise ValueError("new_capture_v2_modes_invalid")
        for mode,count in zip(MODES,COUNTS):
            record=modes[mode]
            if not isinstance(record,dict) or record.get("count_policy")!="provisional_new_generation_v2":
                raise ValueError("new_capture_v2_policy_invalid")
            tickets=record.get("tickets")
            if not isinstance(tickets,list) or len(tickets)!=count:
                raise ValueError("new_capture_v2_counts_invalid")
            combos=[x.get("combo") for x in tickets if isinstance(x,dict)]
            for combo in combos:
                if (not isinstance(combo,str) or len(combo)!=5 or combo[1]!='-' or combo[3]!='-' or
                    any(d not in "123456" for d in combo[::2]) or len(set(combo[::2]))!=3):
                    raise ValueError("new_capture_v2_combo_invalid")
            if len(combos)!=count or len(set(combos))!=count:
                raise ValueError("new_capture_v2_tickets_invalid")
    return len(paths)

if __name__=="__main__":
    files=subprocess.check_output(["git","diff","--cached","--name-only","--diff-filter=A","--","four_mode_forecasts/"],text=True).splitlines()
    print("V2 staged release gate:",audit(files),"validated new archives")
