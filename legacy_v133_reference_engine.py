"""Read-only, input-guarded V127 scoring + V133 3/10/10/wave-mode reference.

Ported without formula edits from the user's original old repository:
  ikst2512-eng/boat-edge, scripts/site_final_history_v133.py
  source Git blob 7b2916df307fcb2783cfc6ddc38ff73903d56da5

No cross-repository fetch or result loading. Never a formal CURRENT or a
verified stronger model. Old site venue-course history is NOT present here,
so its separate calibration component is unavailable and must be disclosed.
Existing CLEAN V2 and archived prediction originals remain untouched.
"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Intentionally empty until authenticated original venue stats are imported.
COURSE = ROOT / "legacy_v133_course_stats_not_imported"
SOURCE_BLOB = "7b2916df307fcb2783cfc6ddc38ff73903d56da5"


def read_json(p:Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def num(v):
    if v is None or (isinstance(v,str) and not v.strip()):
        return None
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def lane_no(r,i):
    try:return int(r.get("lane") or (i+1))
    except:return i+1


def normalize_combo(v):
    if isinstance(v,list):
        return "-".join(str(x) for x in v[:3])
    s=str(v or "")
    m=re.search(r"([1-6])\D+([1-6])\D+([1-6])",s)
    return "-".join(m.groups()) if m else None


def get_before_maps(d):
    bf=d.get("beforeinfo") or {}
    starts={}
    for i,x in enumerate(bf.get("start_exhibition") or []):
        lane=int(x.get("lane") or i+1)
        starts[lane]=num(x.get("st"))
    racers={}
    for i,x in enumerate(bf.get("racers") or []):
        lane=int(x.get("lane") or i+1)
        racers[lane]=x
    actual={}
    for i,x in enumerate(d.get("actual_entry") or []):
        lane=int(x.get("lane") or i+1)
        c=x.get("course",x.get("actual_course",x.get("entry_course")))
        try:c=int(c)
        except:continue
        actual[lane]=c
    return bf,starts,racers,actual


def normalize_exhibition(rows):
    vals=[num(x.get("exhibition_time")) for x in rows]
    vals=[x for x in vals if x is not None]
    if not vals:return {}
    lo,hi=min(vals),max(vals)
    rng=max(hi-lo,.01)
    out={}
    for x in rows:
        t=num(x.get("exhibition_time"))
        lane=x.get("lane")
        if t is not None and lane is not None:
            out[int(lane)]=max(0,1-((t-lo)/rng))
    return out


def compute_scores(d):
    bf,starts,bf_racers,actual=get_before_maps(d)
    ex_norm=normalize_exhibition(bf.get("racers") or [])
    out=[]
    for i,r in enumerate(d.get("racers") or []):
        lane=lane_no(r,i)
        nat=r.get("national") or {}
        loc=r.get("local") or {}
        mot=r.get("motor") or {}
        boat=r.get("boat") or {}
        avg_st=num(r.get("avg_st"))
        nat_win=num(nat.get("win_rate")) or 0
        nat_q=num(nat.get("quinella_rate")) or 0
        loc_win=num(loc.get("win_rate")) or 0
        loc_q=num(loc.get("quinella_rate")) or 0
        mot_q=num(mot.get("quinella_rate")) or 0
        boat_q=num(boat.get("quinella_rate")) or 0
        before=bf_racers.get(lane) or {}
        ex_score=(ex_norm.get(lane,0))*8 if lane in ex_norm else 0
        st_ex=starts.get(lane)
        ex_start_score=0 if st_ex is None else max(0,(.25-st_ex)*28)
        avg_st_score=0 if avg_st is None else max(0,(.24-avg_st)*42)
        lane_base={1:9.5,2:7.0,3:5.8,4:5.2,5:3.2,6:2.2}.get(lane,0)
        tilt=num(before.get("tilt"))
        tilt_score=0 if tilt is None else max(-1,min(2.5,tilt))
        actual_course=actual.get(lane)
        attack_base=0 if actual_course is None else {1:.5,2:5.4,3:6.2,4:6.8,5:4.0,6:3.0}.get(actual_course,0)
        inside_base=8 if lane==1 else (0 if actual_course is None else max(0,5-abs(actual_course-2)))
        machine=mot_q*.11+boat_q*.07
        klass=str(r.get("class") or "")
        class_bonus=2.4 if "A1" in klass else 1.4 if "A2" in klass else .5 if "B1" in klass else 0
        base=nat_win*2.8+nat_q*.18+loc_win*1.9+loc_q*.12+machine+avg_st_score+ex_score+ex_start_score+lane_base+class_bonus+tilt_score
        out.append({
            "lane":lane,"actualCourse":actual_course,"baseScore":base,
            "insideScore":base+inside_base+(6 if lane==1 else 0),
            "attackScore":base+attack_base+(2.5 if actual_course in (3,4) else 0)
        })
    return sorted(out,key=lambda x:x["lane"])


def grade_from_spread(x):
    return "A" if x>=9 else "B+" if x>=6 else "B" if x>=4 else "C+" if x>=2.5 else "C"


def top_unique(rows,n):
    out=[];seen=set()
    for x in rows:
        if x["combo"] in seen:continue
        seen.add(x["combo"]);out.append(x)
        if len(out)>=n:break
    return out


def build_fallback(d):
    scores=compute_scores(d)
    if not scores:return None
    one=next((x for x in scores if x["lane"]==1),scores[0])
    challengers=sorted([x for x in scores if x["lane"]!=1],key=lambda x:x["attackScore"],reverse=True)
    supporters=sorted(scores,key=lambda x:x["baseScore"],reverse=True)
    strongest=challengers[0] if challengers else (supporters[1] if len(supporters)>1 else one)
    diff=one["insideScore"]-strongest["attackScore"]
    pa=max(35,min(78,55+diff*2.2)); pb=100-pa

    ac=[]
    seconds=[x for x in supporters if x["lane"]!=1]
    for i,s in enumerate(seconds):
        for j,t in enumerate(seconds):
            if i==j:continue
            w=one["insideScore"]*1.2+s["baseScore"]+t["baseScore"]+(.5 if s["lane"]<t["lane"] else 0)
            ac.append({"combo":f'1-{s["lane"]}-{t["lane"]}',"weight":w})
    atop=top_unique(sorted(ac,key=lambda x:x["weight"],reverse=True),5)
    asum=sum(x["weight"] for x in atop) or 1
    at=[{"rank":i+1,"combo":x["combo"],"probability":x["weight"]/asum*pa} for i,x in enumerate(atop)]

    bc=[]
    for h in challengers[:3]:
        others=[x for x in supporters if x["lane"]!=h["lane"]]
        pref=next((x for x in others if x["lane"]==1),None)
        rest=[x for x in others if x["lane"]!=1]
        for s in others[:5]:
            for t in others[:5]:
                if t["lane"]==s["lane"]:continue
                prefer_in=(1.2 if s["lane"]==1 else 0)+(.8 if t["lane"]==1 else 0)
                w=h["attackScore"]*1.25+s["baseScore"]+t["baseScore"]+prefer_in+(1.5 if (h["actualCourse"] or 0)>=3 else 0)
                bc.append({"combo":f'{h["lane"]}-{s["lane"]}-{t["lane"]}',"weight":w})
        if pref:
            for r in rest[:3]:
                bc.append({"combo":f'{h["lane"]}-1-{r["lane"]}',"weight":h["attackScore"]*1.35+pref["baseScore"]+r["baseScore"]+3})
                bc.append({"combo":f'{h["lane"]}-{r["lane"]}-1',"weight":h["attackScore"]*1.2+pref["baseScore"]+r["baseScore"]+2.2})
    btop=top_unique(sorted(bc,key=lambda x:x["weight"],reverse=True),5)
    bsum=sum(x["weight"] for x in btop) or 1
    bt=[{"rank":i+1,"combo":x["combo"],"probability":x["weight"]/bsum*pb} for i,x in enumerate(btop)]
    return {"mode":"temp","grade":grade_from_spread(abs(diff)),"worlds":[
        {"key":"A","probability":pa,"tickets":at},
        {"key":"B","probability":pb,"tickets":bt}
    ]}


def build_fallback_expanded(d,base_pred=None):
    scores=compute_scores(d)
    if not scores:return base_pred
    one=next((x for x in scores if x["lane"]==1),scores[0])
    challengers=sorted([x for x in scores if x["lane"]!=1],key=lambda x:x["attackScore"],reverse=True)
    supporters=sorted(scores,key=lambda x:x["baseScore"],reverse=True)

    worlds=(base_pred or {}).get("worlds") or []
    wa=next((x for x in worlds if x.get("key")=="A"),worlds[0] if worlds else {})
    wb=next((x for x in worlds if x.get("key")=="B"),worlds[1] if len(worlds)>1 else {})
    pa=num(wa.get("probability"))
    pb=num(wb.get("probability"))
    pa=50 if pa is None else pa
    pb=(100-pa) if pb is None else pb

    ac=[]
    seconds=[x for x in supporters if x["lane"]!=1]
    for i,sec in enumerate(seconds):
        for j,third in enumerate(seconds):
            if i==j:continue
            weight=one["insideScore"]*1.2+sec["baseScore"]+third["baseScore"]+(.5 if sec["lane"]<third["lane"] else 0)
            ac.append({"combo":f'1-{sec["lane"]}-{third["lane"]}',"weight":weight})
    atop=top_unique(sorted(ac,key=lambda x:x["weight"],reverse=True),10)
    asum=sum(x["weight"] for x in atop) or 1
    at=[{"rank":i+1,"combo":x["combo"],"probability":x["weight"]/asum*pa} for i,x in enumerate(atop)]

    bc=[]
    for h in challengers[:3]:
        others=[x for x in supporters if x["lane"]!=h["lane"]]
        pref=next((x for x in others if x["lane"]==1),None)
        rest=[x for x in others if x["lane"]!=1]
        for sec in others[:5]:
            for third in others[:5]:
                if third["lane"]==sec["lane"]:continue
                prefer_in=(1.2 if sec["lane"]==1 else 0)+(.8 if third["lane"]==1 else 0)
                weight=h["attackScore"]*1.25+sec["baseScore"]+third["baseScore"]+prefer_in+(1.5 if (h["actualCourse"] or 0)>=3 else 0)
                bc.append({"combo":f'{h["lane"]}-{sec["lane"]}-{third["lane"]}',"weight":weight})
        if pref:
            for r in rest[:3]:
                bc.append({"combo":f'{h["lane"]}-1-{r["lane"]}',"weight":h["attackScore"]*1.35+pref["baseScore"]+r["baseScore"]+3})
                bc.append({"combo":f'{h["lane"]}-{r["lane"]}-1',"weight":h["attackScore"]*1.2+pref["baseScore"]+r["baseScore"]+2.2})
    btop=top_unique(sorted(bc,key=lambda x:x["weight"],reverse=True),10)
    bsum=sum(x["weight"] for x in btop) or 1
    bt=[{"rank":i+1,"combo":x["combo"],"probability":x["weight"]/bsum*pb} for i,x in enumerate(btop)]

    return {
        "mode":"temp",
        "grade":(base_pred or {}).get("grade"),
        "worlds":[
            {"key":"A","probability":pa,"tickets":at},
            {"key":"B","probability":pb,"tickets":bt}
        ]
    }


def all_tickets(pred):
    out=[];seen=set()
    for wi,w in enumerate(pred.get("worlds") or []):
        key=w.get("key") or ("A" if wi==0 else "B")
        for i,t in enumerate(w.get("tickets") or []):
            combo=normalize_combo(t.get("combo") or t.get("trifecta") or t.get("order"))
            if not combo or combo in seen:continue
            seen.add(combo)
            raw=num(t.get("probability",t.get("confidence",t.get("prob",t.get("p")))))
            p=0 if raw is None else (raw*100 if raw<=1 else raw)
            out.append({"combo":combo,"p":p,"world":key,"rank":i+1})
    return sorted(out,key=lambda x:x["p"],reverse=True)


def mean(vals):
    vals=[float(x) for x in vals if x is not None and math.isfinite(float(x))]
    return sum(vals)/len(vals) if vals else None


def clamp(v,a,b):return max(a,min(b,v))


def scenario_adjust(race,pred):
    allrows=all_tickets(pred)
    if pred.get("mode")=="formal":
        return {"tickets":allrows,"used":["正式CURRENT"],"applied":False}
    key=race.get("race_key") or ""
    jcd=str((race.get("meta") or {}).get("venue_code") or (key.split("-")[1] if "-" in key else "")).zfill(2)
    stats=read_json(COURSE/f"{jcd}.json") or {}
    actual={}
    for x in race.get("actual_entry") or []:
        try:
            lane=int(x.get("lane")); course=int(x.get("course",x.get("actual_course",x.get("entry_course"))))
            if 1<=lane<=6 and 1<=course<=6:actual[lane]=course
        except:pass
    use_actual=len(actual)==6

    exst={}
    for x in race.get("actual_entry") or []:
        try:
            lane=int(x.get("lane")); v=num(x.get("exhibition_st"))
            if v is not None:exst[lane]=v
        except:pass
    for x in (race.get("beforeinfo") or {}).get("start_exhibition") or []:
        try:
            lane=int(x.get("lane")); v=num(x.get("st"))
            if v is not None and lane not in exst:exst[lane]=v
        except:pass

    extime={}
    for x in (race.get("beforeinfo") or {}).get("racers") or []:
        try:
            lane=int(x.get("lane")); v=num(x.get("exhibition_time"))
            if v is not None:extime[lane]=v
        except:pass

    labels=[str(x or "") for x in ((race.get("original_exhibition") or {}).get("labels") or [])]
    orig={}
    for b in (race.get("original_exhibition") or {}).get("boats") or []:
        try:lane=int(b.get("lane"))
        except:continue
        row={}
        for i,v in enumerate(b.get("values") or []):
            x=num(v)
            if x is not None:row[labels[i] if i<len(labels) else f"metric_{i}"]=x
        orig[lane]=row

    racers={lane_no(r,i):r for i,r in enumerate(race.get("racers") or [])}
    avg_st_mean=mean([num(r.get("avg_st")) for r in racers.values()])
    ex_st_mean=mean(list(exst.values()))
    ex_time_vals=list(extime.values())
    ex_time_mean=mean(ex_time_vals)
    ex_time_range=(max(ex_time_vals)-min(ex_time_vals)) if len(ex_time_vals)>=2 else 0

    orig_scores={}
    for lab in labels:
        vals=[(lane,num(row.get(lab))) for lane,row in orig.items()]
        vals=[x for x in vals if x[1] is not None]
        if len(vals)<2:continue
        lo=min(v for _,v in vals); hi=max(v for _,v in vals); rng=max(hi-lo,.001)
        for lane,v in vals:
            orig_scores.setdefault(lane,[]).append(1-((v-lo)/rng))

    courses=(stats.get("courses") or {})
    course_to_lane={}
    for lane in range(1,7):
        course_to_lane[actual[lane] if use_actual else lane]=lane

    used=[]
    if courses:used.append("当地3か月コース")
    if use_actual:used.append("実進入")
    if len(exst)>=4:used.append("展示ST")
    if len(extime)>=4:used.append("展示タイム")
    if len(orig)>=4:used.append("オリ展")

    def method_fit(c,course):
        if not c:return None
        if course==1:return num(c.get("escape"))
        if course==2:return max(num(c.get("sashi")) or 0,num(c.get("makuri")) or 0)
        if course in (3,4):return max(num(c.get("makuri")) or 0,num(c.get("makuri_sashi")) or 0)
        return num(c.get("makuri_sashi"))

    def lane_factor(lane):
        r=racers.get(lane) or {}
        course=actual.get(lane) if use_actual else lane
        c=courses.get(str(course)) or {}
        f=1.0
        first=num(c.get("first_rate"))
        if first is not None:
            rs=[num(x.get("first_rate")) for x in courses.values()]
            m=mean(rs)
            if m is not None:f*=1+clamp(((first-m)/100)*.45,-.10,.18)
        fit=method_fit(c,course)
        if fit is not None:
            f*=1+clamp(((fit/100)-.45)*.15,-.05,.08)
            if course==4 and max(num(c.get("makuri")) or 0,num(c.get("makuri_sashi")) or 0)>=50:f*=1.035
        ast=num(r.get("avg_st"))
        if ast is not None and avg_st_mean is not None:f*=1+clamp((avg_st_mean-ast)*.90,-.06,.06)
        est=exst.get(lane)
        if est is not None and ex_st_mean is not None:
            f*=1+clamp((ex_st_mean-est)*.65,-.08,.08)
            neigh=[]
            for cc in (course-1,course+1):
                other=course_to_lane.get(cc)
                if other in exst:neigh.append(exst[other])
            nm=mean(neigh)
            if nm is not None:f*=1+clamp((nm-est)*.45,-.04,.05)
        et=extime.get(lane)
        if et is not None and ex_time_mean is not None and ex_time_range>.001:
            f*=1+clamp(((ex_time_mean-et)/ex_time_range)*.07,-.05,.07)
        os=orig_scores.get(lane) or []
        om=mean(os)
        if om is not None:f*=1+clamp((om-.5)*.12,-.06,.06)
        return clamp(f,.78,1.30)

    enriched=[]
    for x in allrows:
        p=[int(z) for z in x["combo"].split("-")]
        factor=(lane_factor(p[0])**.70)*(lane_factor(p[1])**.19)*(lane_factor(p[2])**.11)
        y=dict(x);y["raw"]=max(.001,x["p"])*factor
        enriched.append(y)
    old_sum=sum(x["p"] for x in allrows) or 100
    raw_sum=sum(x["raw"] for x in enriched) or 1
    for x in enriched:x["p"]=x["raw"]/raw_sum*old_sum
    enriched.sort(key=lambda x:x["p"],reverse=True)
    return {"tickets":enriched,"used":used,"applied":True}


def modes_from_tickets(allrows,odds,wave_rows=None,adopt_tail=False):
    def od(x):
        v=num(odds.get(x["combo"]))
        return v if v is not None and v>0 else None

    source=list(wave_rows if wave_rows is not None else allrows)
    total=sum(float(x.get("p") or 0) for x in source) or 1
    head_mass={}
    for x in source:
        head=x["combo"].split("-")[0]
        head_mass[head]=head_mass.get(head,0)+float(x.get("p") or 0)
    shares=sorted(
        ({"head":h,"mass":m,"share":m/total} for h,m in head_mass.items()),
        key=lambda x:x["mass"],reverse=True
    )
    primary=shares[0]["head"] if shares else (source[0]["combo"].split("-")[0] if source else None)
    primary_share=shares[0]["share"] if shares else 1
    meaningful=sum(1 for x in shares if x["share"]>=.10)

    target=12
    if meaningful>=4 or primary_share<=.42:
        target=18
    elif meaningful>=3 or primary_share<=.58:
        target=15

    alt=[x for x in source if x["combo"].split("-")[0]!=primary] if primary else []
    primary_rows=[x for x in source if x["combo"].split("-")[0]==primary] if primary else source
    wave=[];seen=set()
    for x in alt+primary_rows:
        if x["combo"] in seen:continue
        seen.add(x["combo"]);wave.append(x)
        if len(wave)>=min(target,len(source)):break

    balance=[];balance_seen=set()
    def add_balance(x):
        if not x or x["combo"] in balance_seen or len(balance)>=10:return
        balance_seen.add(x["combo"]);balance.append(x)

    balance_primary=(allrows[0]["combo"].split("-")[0] if allrows else primary)
    for x in allrows[:7]:
        add_balance(x)
    alt_balance=[x for x in source if x["combo"].split("-")[0]!=balance_primary] if balance_primary else []
    for x in alt_balance:
        add_balance(x)
        if len(balance)>=10:break
    for x in allrows:
        add_balance(x)
        if len(balance)>=10:break
    for x in source:
        add_balance(x)
        if len(balance)>=10:break

    modes={
        "hit":allrows[:10],
        "balance":balance,
        "hole":wave,
        "narrow":allrows[:3]
    }
    if adopt_tail:
        # The real first-Git-frozen V254 shadow was the top-performing
        # *same-ten-point* third-tail candidate at the user's 2026-10-14
        # provisional selection (37/89 vs 34/89, not statistically proven).
        # Apply its PREDECLARED construction only to NEW site snapshots;
        # older first-saved selections are never re-ranked.
        from boat_edge_v254_third_tail import third_tail_candidate
        combo_order=third_tail_candidate(
            [r["combo"] for r in modes["hit"]],
            [r["combo"] for r in modes["hole"]])
        if combo_order is not None:
            by_combo={r["combo"]:r for r in modes["hole"]+modes["hit"]}
            modes["tail"]=[by_combo[c] for c in combo_order]
    return {k:[dict(x,odds=od(x)) for x in v] for k,v in modes.items()}



def v133_reference_preview(card, now=None):
    """Use V133 ticket construction after CLEAN's existing pre-result guards."""
    from legacy_scenario_engine import restored_scenario_preview
    guard = restored_scenario_preview(card, now=now)
    if guard.get("formal") is not False or guard.get("production_buy_approved") is not False:
        raise ValueError("unsafe_reference_source")
    # Do not imply boat 1 escaped from course 1 when verified exhibition
    # puts it elsewhere. Actual final entry is not authenticated here.
    audit = card.get("source_audit") if isinstance(card, dict) else None
    before_audit = audit.get("beforeinfo") if isinstance(audit, dict) else None
    before = card.get("beforeinfo") if isinstance(card, dict) else None
    starts = before.get("start_exhibition") if isinstance(before, dict) else None
    if (not isinstance(before_audit, dict) or before_audit.get("status") != "ok"
            or not isinstance(starts, list) or len(starts) != 6):
        raise ValueError("verified_six_exhibition_required")
    by_lane = {s.get("lane"): s.get("course") for s in starts
               if isinstance(s, dict) and type(s.get("lane")) is int}
    if (set(by_lane) != set(range(1, 7)) or
            any(type(v) not in (int, float) or not math.isfinite(v) or v != int(v)
                for v in by_lane.values()) or
            sorted(by_lane.values()) != list(range(1, 7))):
        raise ValueError("verified_six_exhibition_courses_required")
    if by_lane[1] != 1:
        raise ValueError("legacy_escape_world_requires_boat1_exhibition_course1")
    racers = card.get("racers") if type(card) is dict else None
    if not isinstance(racers, list) or len(racers) != 6:
        raise ValueError("six_racers_unavailable")
    # Historic V133 scores missing national rates as zero. Do not create that
    # ungrounded fallback here: require genuine six-racer observations.
    if any(not isinstance(r, dict) or not isinstance(r.get("national"), dict) or
           (num(r["national"].get("win_rate")) or 0) <= 0 for r in racers):
        raise ValueError("national_win_rate_missing")
    base = build_fallback(card)
    wave = build_fallback_expanded(card, base)
    if not base or not wave:
        raise ValueError("no_scenario_candidates")
    adjusted = scenario_adjust(card, base)
    expanded = scenario_adjust(card, wave)
    modes = modes_from_tickets(adjusted["tickets"], {}, expanded["tickets"], adopt_tail=True)
    sizes = {name: len(rows) for name, rows in modes.items()}
    if (sizes.get("narrow") != 3 or sizes.get("hit") != 10 or
            sizes.get("balance") != 10 or sizes.get("hole") not in (12, 15, 18)):
        raise ValueError("reference_mode_count_unavailable")
    out = {}
    for name, rows in modes.items():
        tickets = [{"combo": item["combo"], "p": round(float(item["p"]), 5)}
                   for item in rows]
        if len({item["combo"] for item in tickets}) != len(tickets):
            raise ValueError("reference_duplicates")
        out[name] = {"count": len(tickets), "tickets": tickets}
    return {
        "ok": True, "status": "live_old_v127_v133_reference_not_formal",
        "model_version": "V127_V133_SOURCE_PORT_INPUT_GUARDED_REFERENCE_V1",
        "source_model_git_blob": SOURCE_BLOB,
        "race_code": guard["race_code"],
        "deadline_jst": guard.get("deadline_jst"),
        "source_racecard_sha256": guard.get("source_racecard_sha256"),
        "source_audit": (card.get("source_audit") if isinstance(card, dict) else None),
        "grade": base.get("grade"),
        "worlds": base.get("worlds"),
        "modes": out,
        "v254_tail_is_optional_unproven_reference": "tail" in out,
        "used_features": sorted(set((guard.get("used_features") or []) +
                                    (adjusted.get("used") or []) +
                                    (expanded.get("used") or []))),
        "missing_or_unverified": sorted(set((guard.get("missing_or_unverified") or []) +
             ["old_site_three_month_course_stats_not_imported"])),
        "formal": False, "calibrated": False,
        "accuracy_improvement_proven": False,
        "first_remote_add_verified": False,
        "production_buy_approved": False,
        "historical_predictions_reconstructed": False,
    }
