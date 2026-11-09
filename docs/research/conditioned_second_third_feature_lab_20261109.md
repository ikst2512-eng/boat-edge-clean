# Conditional 2nd/3rd feature laboratory — 2026-11-09 JST

**Branch:** Draft #1698 only. **State:** experimental design and synthetic-only negative tests; NOT the frozen #1698 candidate, NOT an approved replacement, and NOT a new prospective cohort. No official source evidence was downloaded or attested by this lab. No production, `main`, UI, Render, results, original forecasts, or schedules are touched.

## Why this study is separate

The frozen #1698 selector uses six pre-race national win rates only, and remains locked to its original 0.50 / 0.25 positional tilt and Nov-09-onward preregistered 300 pilot + 300 confirmation. The Nov-08 116/116 input-only replay and previous TopK membership turnover are **not hit-rate evidence**. Do not change the frozen selector hash or reuse its study ID for a new feature model.

## Proposed conditional likelihood, rather than forced ticket variation

For all 120 ordered combinations `(h,s,t)`, take the original baseline `P0(h,s,t)`. For each complete, independently verified race feature vector `z`:

`log q(h,s,t) = log P0(h,s,t) + sum_f theta2[f]*(z_f[s]-mean(z_f[not h])) + sum_f theta3[f]*(z_f[t]-mean(z_f[not h,s]))`.

Normalize q **within each first boat** to exactly preserve `P0(first=h)`. This is intentionally a **second/third** hypothesis, not an intervention in the first-boat model. Rank the 120 probabilities deterministically (descending, then boat tuple). The resulting experimental scores are **not calibrated odds**. No forced diversity thresholds or manual replacement of repeated combinations are applied.

Features supported *for synthetic sensitivity tests*, with all nonzero coefficients requiring explicit separate exploratory study identity:
- Racer ability: local win rate; existing baseline's national rates must not be double-counted.
- ST: average ST, exhibition ST (smaller is directionally favorable, not a proven calibrated effect).
- Exhibition: time in seconds (smaller is directionally favorable).
- Motor: pre-race motor 2-place percentage.
- Actual entry: six distinct entry courses (1–6 permutation, never infer from frame numbers).
- Wind/water: headwind × entry and wave × entry **interactions**. Headwind requires independent, properly interpreted true-north wind-FROM bearing **and** the actual start/course heading. Official water diagram PNG bytes alone do not certify bearing, and a weather main effect identical for all six racers cancels under within-head normalization.

The numeric scales merely express engineering units and do **not** determine feature effect sizes. There are **no fitted or empirically validated** second/third coefficients for these fields. Lab calls must supply hypotheses explicitly; missing active fields, invalid geometry, incomplete/duplicate six-boat entry, malformed 120 combinations, nonfinite weights, outcome/payout leakage or an unregistered study identity are rejected. Zero-weight fields are not imputed or used.

## What would constitute real evidence

1. Same-race exact official beforeinfo six, official exhibition/ST, actual entry, motor, official 120-way odds and pre-T−12 weather with source byte SHA, source event time and independent receipt. Device-local timestamps and user-supplied booleans are **not** remote first receipt proof.
2. Complete scheduled + manual/rescue attempt census, frozen original and candidate bytes, append-only first remote receipt before T−12; fail closed on holes and never substitute later races.
3. Separately preregister any feature-enhanced selector coefficients and code/blob identity **before** future races. This new feature model cannot be assessed under the already-fixed #1698 300+300 cohort without a distinct preregistered experiment. No post-result tuning.
4. On legitimate future same-race outcomes, compare original and candidate **Top1, Top3, Top5, Top10** for all supported modes; narrow Top10 is not applicable (five tickets). Record gained and lost races, first-head strata, probability calibration and net ROI only if independent odds/payout are verified. Loss at Top5 or Top10 is an explicit non-promotion check, not concealed by Top1 gains.

## Evidence status (no false certification)

- Nov-08 original baseline replay: **116/116**, zero exclusions from prior Draft CI; the new workflow independently guards this.
- Original frozen candidate coefficients/protocol unchanged; experimental coefficient identity intentionally starts `EXPLORATORY_ONLY_`.
- Verified *new* official feature six-boat snapshots for this lab: **0**. Independently witnessed first remote receipts for this feature model: **0**. Feature-enhanced real same-race accuracy comparisons: **0**.
- Frozen #1698 formal pilot: **0/300**, confirmation **0/300** at last verified audit; remaining remote proof and official evidence unresolved.
- `formal=false`, `model_improvement_proven=false`, `promotion_allowed=false`. All code paths are research-only, with no results imported.

**Division of work:** #1693 whole-model accuracy; #1692 venue/wind original evidence; #1685/#1688 hole-specific research; #1707 display only; #1698 conditional 2nd/3rd ranking evidence and hypotheses. No auto-merge.

## Structural evidence availability diagnostic

`inspect_feature_readiness(evidence)` separates `structurally_present_features` from `missing_or_invalid_features` with a failure reason per field. It checks six distinct boats and rejects any result/payout-bearing schema. A partially missing exhibition/ST feature and missing north-referenced start bearing are marked absent, not imputed; independently present motor/local-strength fields remain visible. This is only **syntactic per-race readiness**, not official authenticity, T−12 receipt, predictive usefulness or a validated coefficient. The model itself fails closed when an actively weighted field is missing.

