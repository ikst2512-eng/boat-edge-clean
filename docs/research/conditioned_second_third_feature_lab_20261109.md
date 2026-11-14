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


## Exact sequential probability decomposition, no forced ticket choices

The pure `position_sensitive_conditional_decomposition.py` now reconstructs every valid three-boat probability as

`P(h,s,t) = P(h) × P(s | h) × P(t | h,s)`,

and checks the reconstruction of all **120** tickets. For each of six first boats it lists `P(second=s | h)` before and after the experimental layer. For all 30 legal first/second pairs it lists `P(third=t | h,s)`, with separate absolute probability changes, Top2 boat choice changes, and Top3 boat choice changes. Each six-boat head mass must be exactly preserved: if a feature edit shifts any `P(h)`, the comparison rejects it. All conditionals are mathematical decompositions of the same frozen-head joint board; they are **not separately fitted**, and there is **no claim** that the displayed probabilities are statistically calibrated.

This decomposition is included alongside the four-mode Top1/3/5/10 rank/membership and leave-one-feature-out inspection. Equal boards yield zero conditional differences and no forced ranking diversity. It remains entirely outcome-blind, unregistered, synthetic/manual-input research. The head/second/third explanation is **not** used in production or UI, and must not be presented as a confirmed mechanism without official source receipts and future outcome validation.


## Independent #1694 T−12 report compatibility — read-only blocker bridge

The scope is now coordinated with [the shared all-four-mode acceptance Issue #1708](https://github.com/ikst2512-eng/boat-edge-clean/issues/1708), without taking over #1694's official source or first remote receipt auditing.

`position_sensitive_cross_pr_t12_bridge.py` consumes, **when explicitly supplied**, the pre-existing #1694 schema `T12_SAME_RACE_INDEPENDENT_PROOF_CHAIN_V1`, plus an untrusted optional list of candidate race codes. It **does not implement a new collector, parser, source-origin verifier, remote receipt tool, or confidence scorer**; it only checks report/race identity and component consistency, keeps unreported races absent, and produces a per-race unresolved-blocker map. Supplying the original #1694 report as an ordinary caller JSON does not prove that it is the authenticated report emitted by #1694's real CI. It cannot graduate any candidate or create a formal cohort.

**Existing real historical #1694 conclusion as of Nov 9** (source report documented in [official same-race proof-chain audit](https://github.com/ikst2512-eng/boat-edge-clean/blob/audit/t12-nov06-day-isolation-20261106/docs/audits/t12-independent-nov09-1936-same-race-proof-chain.md)):
- `202611030112` (桐生12R, Nov 3): all three original filenames, but six-boat exhibition/ST/tilt absent; no qualifying same-race official source triad.
- `202611091110` (びわこ10R) and `202611091710` (宮島10R): six-boat exhibition/odds pair before T−12, but no same-race racelist original in that artifact, and frozen CLEAN/V2 predictions were generated **before** the official sources. GitHub source ZIP remote publication before T−12 is not a forecast candidate's first remote publication.
- Therefore among these three inspected races, fully qualified same-race triads **0/3**, official-input-consumption-certified forecasts **0**, formally qualified accuracy samples **0**. These three selected historical examples are not the forward study denominator and cannot be stitched across races. This new bridge does not make new independent verification of their original bytes.

The bridge rejects mixed/duplicated race IDs, crossed days, inconsistent triad counts, future-result claims or forged `formal` flags and never substitutes an official component from another race to fill a missing component. All its per-race "present" entries are `self_reported_present_not_reauthenticated`; no external or first-remote proof is inferred. Even a hypothetical locally complete row is **blocked** pending independently authenticated source/candidate receipts. This is **a nonpromoting compatibility gate, not a new research model**. Existing frozen #1698 conditional selector, registered coefficients and 300+300 identity remain unchanged.


## 2026-11-09 real ledger-to-#1694 historical-source race-code intersection

Real connected GitHub CI logs, not a synthetic mock: [#1698 research CI run #42620562720](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42620562720) emitted `POSITION_SENSITIVE_WHOLE_LEDGER_ROWS_NONFORMAL` for exactly **16** saved candidate race codes:

- `202611090708` to `202611090712` (5)
- `202611091207` to `202611091212` (6)
- `202611091908` to `202611091912` (5)

All 16 logged `status=deadline_cutoff_elapsed_no_new_observation_attempt` and `observed_at_utc=null`; independent first remote receipt certification remains **0/16**, consistent with the ledger provenance auditor. This status reflects this run's observation method and cannot prove remote files never existed or were never observed by a different trusted system.

The independently audited **three** historical same-race examples in [#1694's verified historical source report](https://github.com/ikst2512-eng/boat-edge-clean/blob/audit/t12-nov06-day-isolation-20261106/docs/audits/t12-independent-nov09-1936-same-race-proof-chain.md) are `202611030112`, `202611091110`, `202611091710`. **Exact race-code intersection: 0/16** among current candidate ledger records and those three specifically inspected sources. This is NOT evidence that official source data was never collected for any of the 16 candidate races; it means this bounded set of three upstream historical witnesses supplies no same-race triad for those 16 candidates. Cross-race stitching is forbidden, and the historical official pair races cannot be relabeled as post-source candidate forecasts.

This demonstrates two distinct remaining bottlenecks:
1. **Same-race source coverage/chronology:** #1694/collector owner must obtain independently replayed racelist, fully populated six exhibition/ST, and 120 odds together for a *future same race*, and publish the model-suitable source snapshot before T−12.
2. **Prediction-independent publication:** #1698 needs a separately authorized create-once frozen candidate strictly after actual input receipt and before T−12 with independently witnessed first remote acceptance, full scheduled/manual/rescue run roster, no snapshot substitution. A supplied GitHub Contents GET or local timestamp is not initial receipt evidence.

The new bridge's **offline handoff CLI**, without networking or publication, is:

`python position_sensitive_cross_pr_t12_bridge.py --t12-report /path/to/independently-obtained-1694-report.json --candidate-codes /path/to/1698-race-code-array.json`

Both paths are caller-controlled and treated as untrusted. Validate and pin the source report independently **outside the bridge**, because JSON fields and source-code comments are not provenance. Output remains `formal=false` and no result files are opened; it lists matched/unmatched race codes and nonexclusive missing evidence per race. Historical replay and real source-row identity must be independently confirmed by #1694; this tool cannot upgrade any candidate to a 300+300 slot by itself. No main/UI/Render/collector/forecast file changed.


## 2026-11-09 — Actual pinned #1694 Actions artifact consumed in #1698 CI

**New #1698-only consumer:** `position_sensitive_pinned_1694_artifact_handoff.py` (no production imports). It reads the **actual GitHub Actions artifact** emitted by #1694's already-successful independent official source audit, plus the **existing** full-ledger `position_sensitive_live_roster_audit.py` result generated against the fetched candidate Git ref. No new official HTTP fetch, alternate T−12 source parser, code-triggered publication, result lookup, UI change, or new cron was added.

Pinned evidence for replay and reproducibility:

| Exact item | Immutable expected identity |
|---|---|
| #1694 independent source CI run | `42620400791`, `conclusion=success` |
| #1694 source Git head | `e46094a1cdccf8faa3661c401188d9bb746a0ab6` |
| #1694 Actions artifact ID | `13676360800` (`official-pair-schedule-audit-42620400791`) |
| Artifact original ZIP SHA256 | `acffef2d77d754df6ebf90db42d1301d10ac2bffe55241b4eff5d2618be32e73` |
| Inside-ZIP report original SHA256 | `cc7e94e16ecb9535d5dfaac81f0f6248a8ec7bb375efbe0030cdd799386d638d` |
| Source report | `official_t12_same_race_proof_chain.json` |
| #1698 fetched candidate research ledger Git tip at successful join | `fdf1eb6c77f275fc7fd18d5b039e5f41ec8b5462` |

The full 27,985-byte GitHub source Actions artifact ZIP was **independently downloaded and SHA256-checked** against the GitHub artifact digest; ZIP CRC reported no corrupt entries; the 5,914-byte exact source report SHA256 was also independently computed. This checks archival byte consistency, **not** the official HTTP origins reaudited by the #1694 workflow. The new CLI also now rejects any report whose raw SHA256 differs, including an otherwise structurally valid swapped report. The downloaded report's listed 3 races were confirmed directly.

Real isolated GitHub [#1698 pinned handoff run #42622318287](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42622318287) succeeded: 61/61 synthetic unit tests, fixed blob guard unchanged, Nov08 original 116/116, Nov09 saved original 104/104, **actual same-race join 0/16** against the 3 historically audited #1694 races. A separate [read-only join output ZIP artifact](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42622318287) records the per-race missing-source reasons and GitHub run/artifact metadata. A source audit ZIP published before T−12 does **not** demonstrate a subsequent forecast first Git remote acceptance.

Source report's actual bounded five-gate audit: beforeinfo exhibition **2/3**, official odds 120 **3/3**, deadline-source cutoff **3/3**, **post-official-source frozen forecasts 0/3**, **independent first forecast Git acceptance 0/3**. The extra racelist gate was **1/3**, actual model original consumption **0/3**, final entry independently verified **0/3**. Thus no fully qualified triad, no prospective eligible sample, no post-hoc filling.

**Important artifact retention limitation:** GitHub's selected Actions artifacts were uploaded with finite retention (the source workflow says 30 days). The pinned live handoff deliberately **fails closed** if the source artifact expires or is replaced. A future audit may require the #1694 owner to preserve a newly verified immutable source witness and its exact SHA, and then explicitly review/re-pin the consumer. Do not silently switch to `latest`, cherry-pick unrelated #1694 validation into #1698, or treat an expired artifact as an indication that official races did not exist. No auto-merge.

