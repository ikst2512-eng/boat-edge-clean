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

## New read-only original-byte packet gate (same-day claims only)

`position_sensitive_source_packet_audit.py` independently inspects **caller-supplied original bytes** for four categories (`beforeinfo`, `odds3t`, `weather`, `racecard`): checksum recomputation, exact race URL identity with `hd/jcd/rno`, approved official-domain URL syntax, pre-T−12 claimed receipt clock in JST, zero-size/oversize rejection and missing/late/invalid category reasons. Test scenarios intentionally include a fabricated payload labelled with an official URL to prove that **even all four locally consistent categories DO NOT establish a real official fetch or formal evidence**.

No network request, source parser, semantic verification of official six-boat/120-odds values, independent trusted timestamp or candidate first-remote publication exists in this module. No content from arbitrary HTML or JSON is auto-promoted into selected feature vectors. The `all_raw_source_kinds_locally_self_consistent` value is a **byte/claim-consistency diagnostic only**; `independently_eligible_candidate`, `parsed_six_boats_verified`, `parsed_odds120_verified`, `first_remote_receipt_verified`, `formal` and `promotion_allowed` remain false even for a syntactically perfect mock packet. Source packet URL strings and locally supplied timestamps are untrusted and do not provide attestation. Any missing category is listed explicitly, and no historical 116-race original archive is edited or filled. This is a prerequisite for an eventual independently trusted ingestion adapter, not that adapter itself.

The source packet lab intentionally accepts only same-race-day received-at-JST claims and rejects anything earlier. This conservative requirement can exclude legitimate prior-day sources; any future change needs separate source-specific documentation and tests. It cannot be used to judge the actual production archive's first remote receipt.

**Existing measured missingness:** GitHub research CI for saved Nov-08 116 V2 original files observed `national_win_rates_six=116/116`, `public_title_card_digests_recorded=116/116`, while `actual_entry_six_structured=0`, `exhibition_ST_six_structured=0`, `exhibition_six_structured=0`, `motor_six_structured=0`, `wind_structured=0`, `wave_height=0`, `odds_120_structured=0`. This audits **recorded original-file fields**, NOT proof that no other archive/source contains the features. None are authenticated as official T−12.

## Nov-09 original-file result-blind feature audit (exact CI)

The separate research-only CI at [#42617013458](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42617013458) **passed 23/23 synthetic negative/consistency tests**, Nov-08 original V2 116/116 replay and frozen preregistration source blob pins. It also audited all **104 Nov-09** archived original V2 files (104/104, excluded 0) as available to that exact-head checkout, without reading finish results:
- six national win rates: **104/104**, public title/card SHA records: **104/104**;
- structured six-boat official beforeinfo / actual entry / exhibition / exhibition ST / motor: **0/104**;
- structured wind / wave height / official 120-way odds: **0/104**.

This is **absence of fields within the 104 original forecast JSONs**, not a universal claim that other official data sources contain no information or that raw original bytes are independently authenticated. The frozen #1698 selector continues to use **only six national win rates**; no inferred missing features were fed to the new model. The four-kind packet integrity test reports even a fully synthetic packet as untrusted and not formally eligible.

The legacy shadow suite at [#42617013414](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42617013414) also succeeded on the same exact head. The source-packet and feature-lab changes are not imported by production.


## New exact same-race 4-mode feature ablation (unregistered experimental laboratory)

`position_sensitive_feature_ablation.py` compares **three** calculations on one supplied race: original V2 six-rate board, the **unchanged frozen #1698 selector** (six-rate conditional 0.50/0.25), and a **separately unregistered** extra-feature conditional layer. The feature layer is a hypothetical sensitivity exercise, NOT the registered #1698 300+300 selector and NOT evidence of forecast skill. It uses `rank_modes` unchanged on all three boards, preserving each mode's fixed research ticket budget: narrow 5, hit 10, balance 16, hole 22.

For every mode it reports Top1/3/5/10 ordered changes, membership turnover, retained/replaced tickets and whether the Top1 first boat changed. **Narrow Top10 is explicitly inapplicable** (budget five). It also computes leave-one-active-feature-out comparisons to isolate which inputs mechanically move 2nd/3rd ranks; these effects are nonadditive and are **not** causal importance or evidence of higher hit rates. A zero-weight/unknown feature is not marked as used and cannot quietly change ticket membership. All supplied features are untrusted synthetic/manual lab inputs, not official pre-T−12 verified six-boat evidence.

The output carries a SHA256 fingerprint of precisely supplied race-rate/feature/coefficient/study inputs; this is **local content identity only**, not evidence of source authenticity, a GitHub first add or a remotely witnessed publication. Missing active feature values, duplicate or invalid boats, nonfinite parameters, outcomes/payout leakage and incorrect 120-way boards fail closed; the code reads no result, odds or payment archives. `topk_hit_rate_measured=false`, `roi_measured=false`, `formal=false` and `promotion_allowed=false` unconditionally.

The current synthetic ablation does not update 1st-place win masses or replace the broader all-mode scenario model tracked in [Issue #1708](https://github.com/ikst2512-eng/boat-edge-clean/issues/1708). Pre-event signed source provenance, fitted feature coefficients, prospective distinct registration and independent 300+300 confirmed future races must precede any performance or UI claim. Live model and the archived 116/104 forecasts remain unmodified.

