"""Research-only, frozen 120-race stratified comparison for hole 1st/2nd pair and ranking.
Every candidate is fixed from archived forecasts BEFORE compare_race reads outcomes.
No independently observed first-Git-receipt chronology; NOT prospective or formal accuracy.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race, classify_ticket_miss
from hole_pair_third_bundle_research import bundle
from hole_pair_diversification_research import diversify

COHORT_BY_DAY = {
    "20261028": "0101 0102 0301 0302 0701 0702 0801 0802 0901 0902 1001 1002 1301 1302 1501 1601 2201 2301",
    "20261029": "0101 0102 0301 0302 0701 0702 0801 0802 1301 1302 1401 1402 1501 1502 1601 1801 2301",
    "20261030": "0101 0102 0301 0302 0601 0602 0701 0702 0801 0802 1301 1401 1501 1601 1801 2301 2401",
    "20261031": "0201 0202 0301 0302 0401 0402 0601 0602 0701 0901 1301 1401 1501 1601 1801 2301 2401",
    "20261102": "0211 0212 0311 0312 0410 0411 0611 0612 0911 0912 1501 1504 1712 1901 1902 2211 2401",
    "20261103": "0101 0102 0201 0202 0401 0402 0601 0602 0901 1001 1502 1701 1801 1901 2101 2201 2401",
    "20261104": "0101 0102 0403 0404 0603 0604 0804 0805 0904 0905 1007 1502 1704 1901 2108 2203 2401",
}
EXPECTED_COHORT_SHA256 = "92602b951b8f24d844f558485007109f1c2e7d9c74c2d3cfe5b0d3335b9f4607"
# Historical source: GitHub Actions run 41465608023 (2026-11-02),
# artifact four_mode_historical_cohort_report.json, not a separate holdout.
ORIGINAL_BY_DAY = {
    "20261028": "0101 0102 0103 0301 0302 0303 0701 0702 0801 0802 0901 0902 1001 1002 1301 1302 1501 1502 1601 1602 2201 2202 2301 2302",
    "20261029": "0101 0102 0103 0301 0302 0303 0701 0702 0703 0801 0802 0803 1301 1302 1401 1402 1501 1502 1601 1602 1801 1802 2301 2302",
    "20261030": "0101 0102 0301 0302 0601 0602 0701 0702 0801 0802 1301 1302 1401 1402 1501 1502 1601 1602 1801 1802 2301 2302 2401 2402",
    "20261031": "0201 0202 0301 0302 0401 0402 0601 0602 0701 0702 0901 0902 1301 1302 1401 1402 1501 1502 1601 1602 1801 1802 2301 2401",
    "20261102": "0211 0212 0311 0312 0410 0411 0412 0611 0612 0911 0912 1501 1504 1505 1506 1712 1901 1902 1903 2211 2212 2401 2402 2403",
}
EXPECTED_ORIGINAL_SHA256 = "bd38e07b4b509881634f799b494ae3dcac9cce34f2f6576e735f42ce34389e63"
POLICIES = ("baseline", "same_pair", "two_pairs")
TOPS = (1, 3, 5, 10)

def fixed_codes():
    codes = [day + suffix for day, suffixes in COHORT_BY_DAY.items()
             for suffix in suffixes.split()]
    digest = hashlib.sha256("\n".join(sorted(codes)).encode()).hexdigest()
    if len(codes) != 120 or len(set(codes)) != 120 or digest != EXPECTED_COHORT_SHA256:
        raise ValueError("frozen_cohort_definition_changed")
    return codes

def original_codes():
    codes = [day + suffix for day, suffixes in ORIGINAL_BY_DAY.items()
             for suffix in suffixes.split()]
    digest = hashlib.sha256("\n".join(sorted(codes)).encode()).hexdigest()
    if len(codes) != 120 or len(set(codes)) != 120 or digest != EXPECTED_ORIGINAL_SHA256:
        raise ValueError("original_historical_cohort_definition_changed")
    return codes

def pair(ticket):
    return tuple(ticket.split("-")[:2])

def frozen_proposals(archive):
    modes = archive["modes"]
    base = [x["combo"] for x in modes["hole"]["tickets"][:10]]
    if len(base) != 10 or len(set(base)) != 10:
        raise ValueError("invalid_hole_top10")
    donor = list(dict.fromkeys(x["combo"]
        for mode in ("hit", "balance") for x in modes[mode]["tickets"]))
    picks = {"baseline":base,
             "same_pair":bundle(base, donor, rank=6, width=2),
             "two_pairs":diversify(archive)}
    pairs = {pair(t) for t in base}
    for name, tickets in picks.items():
        if (len(tickets) != 10 or len(set(tickets)) != 10
                or tickets[:5] != base[:5]
                or not pairs.issubset({pair(t) for t in tickets})):
            raise ValueError("invariant_failed:" + name)
    return picks

def compare_one(code, root):
    status, archive = archived_four_modes(code, root)
    if status != 200:
        raise ValueError("invalid_archived_forecast:" + code + ":" + str(status))
    picks = frozen_proposals(archive)  # No outcome information can enter selection.
    outcome = compare_race(code, root) # Post-selection classification only.
    if outcome.get("status") != "historical_comparison_only":
        raise ValueError("invalid_confirmed_outcome:" + code + ":" + str(outcome.get("status")))
    winner = outcome["winning_ticket"]
    base_all = [x["combo"] for x in archive["modes"]["hole"]["tickets"]]
    winning_pair = pair(winner)
    hit_donor_has_pair = any(pair(x["combo"])==winning_pair
                             for x in archive["modes"]["hit"]["tickets"])
    balance_donor_has_pair = any(pair(x["combo"])==winning_pair
                                 for x in archive["modes"]["balance"]["tickets"])
    ranks = {}
    for name, tickets in picks.items():
        ranks[name] = tickets.index(winner) + 1 if winner in tickets else 0
    head = winner.split("-")[0]
    base = picks["baseline"]
    return {
        "race_code":code, "date":code[:8], "venue_code":code[8:10],
        "race_number":int(code[10:12]), "model_version":archive["model_version"],
        "winning_ticket":winner, "ranks":ranks,
        "changed":{name:picks[name]!=base for name in POLICIES},
        "top1_head_match":base[0].split("-")[0]==head,
        "head_in_top10":any(t.split("-")[0]==head for t in base),
        "baseline_miss_top10":classify_ticket_miss(base, winner),
        "baseline_miss_full_hole":classify_ticket_miss(base_all, winner),
        "hit_donor_has_winning_pair":hit_donor_has_pair,
        "balance_donor_has_winning_pair":balance_donor_has_pair,
        "full_hole_ticket_count":len(base_all),
        "file_declared_predeadline_only":True,
    }

def summarize(rows):
    n = len(rows)
    summary = {"n":n, "top1_head_matches":sum(r["top1_head_match"] for r in rows),
               "head_in_top10":sum(r["head_in_top10"] for r in rows),
               "baseline_misses_top10":dict(Counter(r["baseline_miss_top10"] for r in rows)),
               "baseline_misses_full_hole":dict(Counter(r["baseline_miss_full_hole"] for r in rows)),
               "policies":{}}
    for name in POLICIES:
        ranks = [(r["ranks"]["baseline"], r["ranks"][name]) for r in rows]
        hits = {f"top{k}":sum(0 < new <= k for _,new in ranks) for k in TOPS}
        gain = {f"top{k}":sum((not (0<old<=k)) and 0<new<=k for old,new in ranks) for k in TOPS}
        loss = {f"top{k}":sum(0<old<=k and not (0<new<=k) for old,new in ranks) for k in TOPS}
        old_hits={f"top{k}":sum(0<old<=k for old,_ in ranks) for k in TOPS}
        if any(hits[key]-old_hits[key] != gain[key]-loss[key] for key in hits):
            raise ValueError("paired_gain_loss_attribution")
        summary["policies"][name] = {
            "hits":hits,
            "topn_pct":{key:round(100*value/n,2) if n else None for key,value in hits.items()},
            "gain":gain, "loss":loss,
            "changed":sum(r["changed"][name] for r in rows),
            "existing_hits_rank_worse":sum(0<old<=10 and 0<new<=10 and new>old for old,new in ranks),
            "existing_hits_rank_better":sum(0<old<=10 and 0<new<=10 and new<old for old,new in ranks),
        }
    return summary

def run(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    codes = fixed_codes()
    historical_codes = original_codes()
    # Recompute each archived race once, including the 86 shared race IDs.
    # Missing originals FAIL CLOSED, never silently shrink either denominator.
    row_by_code = {code:compare_one(code,root)
                   for code in sorted(set(codes)|set(historical_codes))}
    rows = [row_by_code[code] for code in codes]
    original_rows = [row_by_code[code] for code in historical_codes]
    if len({r["race_code"] for r in rows}) != len(codes):
        raise ValueError("cohort_identity_collision")
    original_missing_pairs = [r for r in original_rows
              if r["baseline_miss_full_hole"]=="winner_second_pair_absent"]
    original_replay = {
        "n":len(original_rows),
        "hole_full_list_second_pair_missing":len(original_missing_pairs),
        "of_missing_pair_hit_donor_has_winning_pair":sum(
             r["hit_donor_has_winning_pair"] for r in original_missing_pairs),
        "of_missing_pair_balance_donor_has_winning_pair":sum(
             r["balance_donor_has_winning_pair"] for r in original_missing_pairs),
        "original_cohort_sha256":EXPECTED_ORIGINAL_SHA256,
        "source_run_id":41465608023,
    }
    original_replay["matches_20261102_archived_report"] = (
          original_replay["n"]==120
          and original_replay["hole_full_list_second_pair_missing"]==84
          and original_replay["of_missing_pair_hit_donor_has_winning_pair"]==67
          and original_replay["of_missing_pair_balance_donor_has_winning_pair"]==61)
    def grouped(key):
        groups = {}
        for row in rows:
            groups.setdefault(key(row),[]).append(row)
        return {group:summarize(group_rows) for group,group_rows in sorted(groups.items())}
    report = {
        "schema":"HOLE_FIXED120_STRATIFIED_RESEARCH_V1",
        "status":"historical_research_only",
        "formal":False, "prospective_validation":False,
        "independent_first_receipt_verified":False,
        "production_forecast_changed":False,
        "selection_is_result_blind_by_code_order":True,
        "cohort_sha256":EXPECTED_COHORT_SHA256,
        "cohort_count":len(rows),
        "historical_original_120":original_replay,
        "cohort_overlap":{"shared":len(set(codes)&set(historical_codes)),
                          "original_only":len(set(historical_codes)-set(codes)),
                          "current_only":len(set(codes)-set(historical_codes))},
        "overall":summarize(rows),
        "by_model_version":grouped(lambda r:r["model_version"]),
        "by_date":grouped(lambda r:r["date"]),
        "by_race_round_band":grouped(lambda r:"R1-R2" if r["race_number"]<=2 else "R3-R12"),
        "by_venue":grouped(lambda r:r["venue_code"]),
        "head_definition":"Top1 head = first boat of hole's FIRST-ranked triple, not full-trifecta Top1",
        "miss_definition":"Top10 excludes hole ranks 11+; full_hole includes every archived hole ticket",
        "prior_research_84":"In Nov 2's separate original 120-race cohort, 84 full-hole second-pair misses",
        "prior_research_67":"Subset of those 84 missing-pair races where hit-mode donor already held winning pair; NOT a separate 67-race holdout",
        "warning":"Reused outcomes and predeadline self-reported times. No independent first Git receipt, untouched test or causal boat-dynamics inference.",
        "rows":rows,
    }
    return report

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
