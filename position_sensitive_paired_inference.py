"""Read-only exact paired hypothesis diagnostic for Draft #1698.

Consumes the same non-formal aggregate reference scorer as the existing paired
guard. Never collects results or authorizes adoption. The underlying selector,
frozen registration, and prospective original archive are not changed.

One-sided exact McNemar / sign-tail tests are exploratory *superiority* screens.
A nonsignificant result does not demonstrate non-inferiority; independence of
race-level discordances is not established by the reference report.
"""
import json
from math import comb
from pathlib import Path

from position_sensitive_paired_guard import assess_reference_score
from four_mode_position_sensitive_forward import MODES

SCHEMA = "FOUR_MODE_POSITION_SENSITIVE_PAIRED_INFERENCE_V1"
ALPHA = 0.05
TOP_PRIMARY = "1"
SECONDARY = ("5", "10")


def exact_one_sided_gain_p(gained, lost):
    """P[Binomial(gained + lost, 1/2) >= gained] under equal paired hit chance.

    Use integer arithmetic for exact tail numerator (only final ratio floats).
    This DOES NOT certify source independence or prospective validity.
    """
    if (type(gained) is not int or type(lost) is not int
            or gained < 0 or lost < 0 or gained + lost > 300):
        raise ValueError("invalid_paired_discordance")
    n = gained + lost
    if not n:
        return 1.0
    return sum(comb(n, k) for k in range(gained, n + 1)) / (1 << n)


def holm_adjust(pvalues):
    """Familywise p-adjustment for a fixed set of hypothesis identities."""
    if not pvalues:
        raise ValueError("empty_family")
    for p in pvalues.values():
        if type(p) not in (float, int) or not 0 <= p <= 1:
            raise ValueError("invalid_pvalue")
    ordered = sorted(pvalues, key=lambda k: (pvalues[k], k))
    out = {}
    running = 0.0
    n = len(ordered)
    for rank, name in enumerate(ordered):
        running = min(1.0, max(running, (n - rank) * pvalues[name]))
        out[name] = running
    return out


def inference_reference_only(score):
    """Conditional exploratory tests ONLY on complete confirmation 300.

    Even 300/300 + all p-values significant cannot promote because remote
    receipts, official six/120, independence, and outcome provenance are absent.
    """
    guarded = assess_reference_score(score)
    complete = guarded["all_600_reference_results_present"]
    output = {
        "schema": SCHEMA,
        "status": "reference_only_no_formal_statistics",
        "formal": False,
        "promotion_allowed": False,
        "model_improvement_proven": False,
        "first_remote_candidate_receipts_verified": False,
        "source_independence_verified": False,
        "official_six_and_120_predeadline_verified": False,
        "reference_confirmation_complete": complete,
        "alpha_reference_only": ALPHA,
        "primary_family": "four_modes_top1_one_sided_exact_McNemar_Holm",
        "secondary_safety_family": "all_applicable_modes_Top5_Top10_one_sided_exact_McNemar_Holm",
        "primary": {},
        "secondary_safety": {},
        "primary_reference_screen": "not_evaluated",
        "secondary_reference_screen": "not_evaluated",
        "reason": None,
    }
    if not complete:
        output["reason"] = "incomplete_confirmation_or_missing_earlier_phase_result"
        return output

    rows = guarded["by_phase_mode_topn"]["confirmation"]
    primary_p = {}
    secondary_p = {}
    for mode, budget in MODES.items():
        primary = rows[mode][TOP_PRIMARY]
        primary_p[mode] = exact_one_sided_gain_p(
            primary["gained_hits"], primary["lost_hits"])
        for k in SECONDARY:
            if int(k) > budget:
                continue
            result = rows[mode][k]
            secondary_p[f"{mode}_top{k}"] = exact_one_sided_gain_p(
                result["gained_hits"], result["lost_hits"])

    adj_primary = holm_adjust(primary_p)
    adj_secondary = holm_adjust(secondary_p)
    for mode in MODES:
        r = rows[mode][TOP_PRIMARY]
        output["primary"][mode] = {
            "gained_hits": r["gained_hits"],
            "lost_hits": r["lost_hits"],
            "net_hit_difference": r["net_hit_difference"],
            "discordant_pairs": r["gained_hits"] + r["lost_hits"],
            "exact_one_sided_superiority_p": primary_p[mode],
            "holm_adjusted_p": adj_primary[mode],
            "reference_superiority_screen": (
                r["net_hit_difference"] > 0 and adj_primary[mode] <= ALPHA
            ),
        }
        for k in SECONDARY:
            if int(k) > MODES[mode]:
                output["secondary_safety"][f"{mode}_top{k}"] = {
                    "applicable": False, "reason": "five_ticket_budget"
                }
                continue
            key = f"{mode}_top{k}"
            r = rows[mode][k]
            output["secondary_safety"][key] = {
                "applicable": True,
                "gained_hits": r["gained_hits"],
                "lost_hits": r["lost_hits"],
                "net_hit_difference": r["net_hit_difference"],
                "discordant_pairs": r["gained_hits"] + r["lost_hits"],
                "exact_one_sided_superiority_p": secondary_p[key],
                "holm_adjusted_p": adj_secondary[key],
                "observed_net_loss": r["net_hit_difference"] < 0,
                "reference_superiority_screen": (
                    r["net_hit_difference"] > 0 and adj_secondary[key] <= ALPHA
                ),
            }
    if any(v["net_hit_difference"] < 0 for v in output["primary"].values()):
        output["primary_reference_screen"] = "observed_top1_net_loss"
    elif all(v["reference_superiority_screen"] for v in output["primary"].values()):
        output["primary_reference_screen"] = "exploratory_superiority_signal_only"
    else:
        output["primary_reference_screen"] = "inconclusive_not_proven"
    applicable_safety = [
        v for v in output["secondary_safety"].values() if v["applicable"]
    ]
    if any(v["observed_net_loss"] for v in applicable_safety):
        output["secondary_reference_screen"] = "observed_top5_top10_net_loss"
    elif all(v["reference_superiority_screen"] for v in applicable_safety):
        output["secondary_reference_screen"] = "exploratory_superiority_signal_only"
    else:
        output["secondary_reference_screen"] = "inconclusive_not_proven"
    output["reason"] = (
        "This is not a preregistered confirmatory inference amendment. "
        "Holm-adjusted one-sided tests here demand superiority, NOT non-inferiority. "
        "Nonsignificance cannot establish safety. Reference aggregate cannot prove "
        "independent race sampling, complete schedule/run inventory, official "
        "pre-T12 data, first remote receipt or independently certified results. "
        "Do not reuse historical selection data, change frozen coefficient/model, "
        "or promote even if exploratory screens are significant."
    )
    return output


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--reference", type=Path, default=None)
    args = p.parse_args()
    if args.reference is None:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "no_independent_forward_cohort",
            "formal": False, "promotion_allowed": False,
            "model_improvement_proven": False,
            "reference_confirmed_confirmation_races": 0,
        }, sort_keys=True))
        return
    if args.reference.is_symlink() or not args.reference.is_file():
        raise ValueError("invalid_reference_path")
    if args.reference.stat().st_size > 100000:
        raise ValueError("oversize_reference")
    score = json.loads(args.reference.read_text(encoding="utf-8"))
    print(json.dumps(inference_reference_only(score), sort_keys=True))


if __name__ == "__main__":
    main()
