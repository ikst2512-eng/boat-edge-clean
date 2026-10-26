"""Offline, research-only paired comparison; no result fetching or production imports.

Input: JSON list of race objects. The operator must independently audit receipts
and outcome-access permission BEFORE setting verified flags. A flag alone is not proof.
Never load Formal Fresh locked records or reconstruct historical predictions.
"""
import argparse
import re
import json
import math
import random
from datetime import datetime, timedelta, timezone
from collections import Counter
from itertools import permutations
from pathlib import Path

TICKETS = {"-".join(map(str, t)) for t in permutations(range(1, 7), 3)}
TOPS = (1, 3, 5, 10)

def timestamp(x):
    dt = datetime.fromisoformat(x.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone required")
    return dt

def validate_forecast(f, race):
    """Fail closed on missing or ambiguous first-save provenance."""
    required = ("model_id", "model_sha", "input_sha256", "first_git_commit",
                "first_git_saved_at", "generated_at", "source_received_at", "probabilities")
    if any(not f.get(k) for k in required):
        raise ValueError("missing model or freeze provenance")
    if f["model_id"] != race["_expected_model_id"]:
        raise ValueError("model identifier mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", f["model_sha"]):
        raise ValueError("invalid model git SHA")
    if not re.fullmatch(r"[0-9a-f]{40}", f["first_git_commit"]):
        raise ValueError("invalid first Git commit SHA")
    if not re.fullmatch(r"[0-9a-f]{64}", f["input_sha256"]):
        raise ValueError("invalid input SHA256")
    if f.get("independently_verified") is not True:
        raise ValueError("first Git addition and byte identity not independently verified")
    if f["input_sha256"] != race["input_sha256"]:
        raise ValueError("nonidentical race input")
    cutoff = timestamp(race["deadline"])
    if timestamp(f["source_received_at"]) > timestamp(f["generated_at"]):
        raise ValueError("source received after forecast generation")
    if timestamp(f["source_received_at"]) >= cutoff:
        raise ValueError("source received after deadline")
    if timestamp(f["generated_at"]) > timestamp(f["first_git_saved_at"]):
        raise ValueError("generated after initial freeze")
    if timestamp(f["generated_at"]) >= cutoff or timestamp(f["first_git_saved_at"]) >= cutoff:
        raise ValueError("forecast not frozen before deadline")
    p = f["probabilities"]
    if not isinstance(p, dict) or set(p) != TICKETS:
        raise ValueError("not exactly 120 trifectas")
    if any(type(v) not in (float, int) or not math.isfinite(v) or v <= 0 for v in p.values()):
        raise ValueError("invalid probability")
    if abs(sum(p.values()) - 1) > 1e-7:
        raise ValueError("probabilities not normalized")
    return p

def rank(p):
    return sorted(TICKETS, key=lambda t: (-p[t], t))

def collect(rows, baseline, candidate):
    pairs, excluded = [], {}
    excluded_details = []
    key_counts = Counter(row.get('race_key') for row in rows if isinstance(row, dict) and isinstance(row.get('race_key'), str))
    model_identity = {}
    registered_cohort = None
    for r in rows:
        try:
            key = r["race_key"]
            if not isinstance(key, str) or not re.fullmatch(r"20[0-9]{6}-[0-9]{2}-[0-9]{1,2}", key):
                raise ValueError("invalid canonical race key")
            date_text, venue_text, race_text = key.split("-")
            try:
                datetime.strptime(date_text, "%Y%m%d")
            except ValueError as exc:
                raise ValueError("invalid race date") from exc
            if not (1 <= int(venue_text) <= 24 and 1 <= int(race_text) <= 12):
                raise ValueError("race venue or number out of range")
            jst = timezone(timedelta(hours=9))
            if timestamp(r["deadline"]).astimezone(jst).strftime("%Y%m%d") != date_text:
                raise ValueError("race date differs from deadline JST date")
            if key_counts[key] > 1:
                raise ValueError("ambiguous duplicate race")
            if r.get("research_outcome_access_approved") is not True:
                raise ValueError("outcome access not approved")
            if r.get("outcome_independently_verified") is not True:
                raise ValueError("outcome not verified")
            y = r["result"]
            if y not in TICKETS:
                raise ValueError("invalid result")
            f = r["forecasts"]
            a = validate_forecast(f[baseline], dict(r, _expected_model_id=baseline))
            b = validate_forecast(f[candidate], dict(r, _expected_model_id=candidate))
            # Models must be fixed before outcome availability, not selected after evaluation.
            # A Boolean is not proof of preregistration; require an explicit,
            # dated model pair and fail closed when either identity differs.
            reg = r.get("pre_registration")
            if not isinstance(reg, dict):
                raise ValueError("missing pre-registration record")
            if reg.get("baseline_model_sha") != f[baseline]["model_sha"] or reg.get("candidate_model_sha") != f[candidate]["model_sha"]:
                raise ValueError("pre-registered model SHA mismatch")
            if reg.get("baseline_model_id") != baseline or reg.get("candidate_model_id") != candidate:
                raise ValueError("pre-registered model ID mismatch")
            if not reg.get("receipt_verified_independently", False):
                raise ValueError("pre-registration receipt not independently verified")
            identity = (reg["baseline_model_id"], reg["candidate_model_id"],
                        reg["baseline_model_sha"], reg["candidate_model_sha"],
                        reg["registered_at"])
            if registered_cohort is not None and identity != registered_cohort:
                raise ValueError("pre-registration drift across evaluation races")
            registered = timestamp(reg["registered_at"])
            if registered >= timestamp(r["deadline"]):
                raise ValueError("pre-registration after deadline")
            if registered > min(timestamp(f[baseline]["generated_at"]), timestamp(f[candidate]["generated_at"])):
                raise ValueError("pre-registration after forecast generation")
            if f[baseline]["input_sha256"] != f[candidate]["input_sha256"]:
                raise ValueError("different input")
            for name in (baseline, candidate):
                model_sha = f[name]["model_sha"]
                if name in model_identity and model_identity[name] != model_sha:
                    raise ValueError("model SHA drift across evaluation races")
            for name in (baseline, candidate):
                model_identity.setdefault(name, f[name]["model_sha"])
            if registered_cohort is None:
                registered_cohort = identity
            ra, rb = rank(a), rank(b)
            pairs.append({"race_key":key, "a":[int(y in ra[:k]) for k in TOPS],
                          "b":[int(y in rb[:k]) for k in TOPS],
                          "logloss_a":-math.log(a[y]), "logloss_b":-math.log(b[y]),
                          "brier_a":sum((p-int(t==y))**2 for t,p in a.items()),
                          "brier_b":sum((p-int(t==y))**2 for t,p in b.items()),
                          "confidence_a":a[ra[0]], "confidence_b":b[rb[0]],
                          "correct_a":int(y == ra[0]), "correct_b":int(y == rb[0])})
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            reason = str(e) or type(e).__name__
            excluded[reason] = excluded.get(reason, 0) + 1
            raw_key = r.get("race_key") if isinstance(r, dict) else None
            safe_key = raw_key if isinstance(raw_key, str) and re.fullmatch(r"20[0-9]{6}-[0-9]{2}-[0-9]{1,2}", raw_key) else None
            excluded_details.append({"race_key": safe_key, "reason": reason})
    return pairs, excluded, excluded_details

def mean(xs):
    return sum(xs)/len(xs)

def interval(delta, seed=20261027, nboot=4000):
    rng = random.Random(seed)
    n = len(delta)
    boots = sorted(mean([delta[rng.randrange(n)] for _ in range(n)]) for _ in range(nboot))
    return [boots[int(nboot*.025)], boots[min(nboot-1, int(nboot*.975))]]

def paired_p(delta, seed=20261028, reps=9999):
    rng = random.Random(seed)
    observed = abs(mean(delta))
    extreme = 0
    for _ in range(reps):
        trial = abs(sum(d * (1 if rng.randrange(2) else -1) for d in delta)/len(delta))
        extreme += trial >= observed - 1e-14
    return (extreme+1)/(reps+1)

def ece(pairs, prefix, bins=10):
    """Top-ranked exact ticket: bin confidence against observed top-1 hit."""
    total = 0.
    for i in range(bins):
        items = [(x["confidence_"+prefix], x["correct_"+prefix]) for x in pairs
                 if min(bins-1, int(x["confidence_"+prefix]*bins)) == i]
        if items:
            total += len(items)/len(pairs)*abs(mean([p for p,_ in items])-mean([y for _,y in items]))
    return total

def compare(rows, baseline, candidate):
    if baseline == candidate:
        raise ValueError("distinct baseline and candidate required")
    pairs, excluded, excluded_details = collect(rows, baseline, candidate)
    output = {"status":"INSUFFICIENT_EVIDENCE", "baseline":baseline, "candidate":candidate,
              "eligible_races":len(pairs), "excluded_races":sum(excluded.values()),
              "exclusion_reasons":excluded,
              "excluded_details":excluded_details,
              "warning":"Self-declared provenance flags are not independently audited by this script."}
    if not pairs:
        return output
    metrics = {}
    for j,k in enumerate(TOPS):
        d = [x["b"][j]-x["a"][j] for x in pairs]
        metrics["top"+str(k)] = {"baseline":mean([x["a"][j] for x in pairs]),
            "candidate":mean([x["b"][j] for x in pairs]), "delta":mean(d),
            "paired_bootstrap_95ci":interval(d,seed=101+j),
            "paired_signflip_p":paired_p(d,seed=201+j),
            "improved_races":sum(v>0 for v in d), "worsened_races":sum(v<0 for v in d)}
    d = [x["logloss_b"]-x["logloss_a"] for x in pairs]
    metrics["log_loss"] = {"baseline":mean([x["logloss_a"] for x in pairs]),
        "candidate":mean([x["logloss_b"] for x in pairs]), "delta":mean(d),
        "paired_bootstrap_95ci":interval(d,seed=301),
        "paired_signflip_p":paired_p(d,seed=401),
        "lower_is_better":True}
    bd = [x["brier_b"]-x["brier_a"] for x in pairs]
    metrics["multiclass_brier"] = {
        "baseline":mean([x["brier_a"] for x in pairs]),
        "candidate":mean([x["brier_b"] for x in pairs]),
        "delta":mean(bd),
        "paired_bootstrap_95ci":interval(bd,seed=501),
        "paired_signflip_p":paired_p(bd,seed=601),
        "lower_is_better":True}
    metrics["top1_ece_10bins"] = {"baseline":ece(pairs,"a"),"candidate":ece(pairs,"b"),
        "note":"Descriptive; very low-probability top tickets require a large sample."}
    # Six confirmatory comparisons are reported, not one cherry-picked p-value.
    # Holm correction controls family-wise error under arbitrary dependence.
    names = ["top1", "top3", "top5", "top10", "log_loss", "multiclass_brier"]
    ordered = sorted(names, key=lambda name: metrics[name]["paired_signflip_p"])
    maximum = 0.0
    for index, name in enumerate(ordered):
        maximum = max(maximum, min(1.0, (len(ordered)-index) * metrics[name]["paired_signflip_p"]))
        metrics[name]["holm_adjusted_p"] = maximum
    output["multiple_comparison_method"] = "Holm step-down across six paired endpoints; ECE descriptive"
    output["metrics"] = metrics
    output["status"] = "RESEARCH_ONLY_NOT_PROMOTED" if len(pairs) >= 30 else "INSUFFICIENT_EVIDENCE"
    output["minimum_exploratory_sample"] = 30
    output["sample_size_warning"] = ("Small paired sample: inferential intervals and p-values are exploratory only."
                                     if len(pairs) < 30 else "Sample count alone does not establish independent prospective evidence.")
    output["warning"] += " CI, p-values and ECE do not establish prospective improvement without audited pre-registration and independent receipts."
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--baseline", required=True)
    p.add_argument("--candidate", required=True)
    args=p.parse_args()
    if args.baseline == args.candidate:
        p.error("distinct model IDs required")
    rows=json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(rows,list):
        p.error("JSON array required")
    print(json.dumps(compare(rows,args.baseline,args.candidate),ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
