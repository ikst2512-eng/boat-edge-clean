# BOAT EDGE CLEAN: position-sensitive four-mode candidate (2026-11-08 JST)

Status: **Draft research / NOT deployed / NOT certified / no betting recommendation**.

## User concern, measured problem

The archived four-mode V2 `research_model.probabilities` applies the six national win rates to the FIRST-boat component. For any fixed first boat, all second/third probabilities are proportional to the same frozen 1,000-case ticket-count prior. Consequently `1-2-4` and `1-2-3` have virtually invariant relative order across races even when boats 3 and 4 have sharply different win rates.

Independent existing Draft [#1693](https://github.com/ikst2512-eng/boat-edge-clean/pull/1693) already audited **116** Nov-08 frozen V2 inputs and identified **109/116** top picks `1-2-4`; follow its stronger full-cohort provenance and first-head exposure safeguards. The current change is a NEW, **isolated conditional-second/third ranking candidate**, not a duplicate Top1 protocol or ledger.

## What the candidate actually does

- Read only a six-boat national win-rate vector. Recompute the unchanged frozen V2 research 120-ticket baseline.
- For a tuple (first h, second s, third t) multiply the baseline probability by:
  `exp(0.50 * (rate[s] - mean(rates except h)) + 0.25 * (rate[t] - mean(rates except h,s)))`.
- Normalize **separately within each first-boat h**, leaving all six baseline first-boat marginal probabilities unchanged. This makes the relative ranks of 2nd/3rd reflect the race-specific six-boat skill inputs. It does **not** fix first-boat (escape/wall) bias or independently establish better prediction.
- Apply the existing `rank_modes` selector. Exactly preserve the current candidate ticket budgets: narrow 5, hit 10, balance 16, hole 22. These are existing exploratory budgets, not proven best sizes.
- Coefficients 0.50/0.25 are **hypotheses**, frozen BEFORE outcome comparison, not statistically fitted or validated. No odds/returns/results/exhibition/ST/wind/motor/course are used. Missing mandatory features are not invented.

## Early input-only replay (not hit-rate evidence)

With the fixed candidate and 12 selected Nov-08 saved six-rate vectors, the **top-1 combination changed in 9/12**, while top-5 membership changed in **11/12**. These are **changes**, not improvements in accuracy, win-head coverage or ROI. Example:
- `202611080102`: baseline top1 `1-2-4`, candidate top1 `1-2-3`.
- `202611080302`: baseline top1 `1-2-4`, candidate top1 `1-3-5`.
- `202611080303`: baseline top1 `2-1-3`, candidate top1 `1-2-3` — potentially worse; do NOT select using after-result knowledge.

A repeatable full-day **input-only** diagnostic is provided:
`python four_mode_position_sensitive_shadow.py --day 20261108`.
This checks every present original saved V2 against the recomputed baseline and compares rank diversity without reading any finish or payout. The output counts cannot prove skill.

## Promotion gate / division of work

1. **Do not change main, Render/UI, live selection, T-12 pipeline or saved historical predictions.** Files in this Draft are research-only and have no production import path.
2. In the research coordinator **#1693**, retain the existing prospective 300+300 Top1 and all-mode paired validation protocols. A new candidate must be predeclared separately (exact selector SHA, coefficients, data-provenance/first-remote-receipt) BEFORE the future race. Do not slip this candidate into an already preregistered identity.
3. After a legitimate predeadline independent candidate freeze, score same-race old vs new Top1/Top3/Top5/Top10, wins/losses, venue/first-head strata, calibration and ROI with independent results, and include risk of deterioration. NO Nov-05–08 development comparisons in the prospective holdout.
4. Use the 24-venue wind/actual-course research in Draft **[#1692](https://github.com/ikst2512-eng/boat-edge-clean/pull/1692)** only when trustworthy race-specific before-deadline receipts are available. Never infer missing weather/exhibition/wall inputs.
5. UI/Render audit remains **[#1679](https://github.com/ikst2512-eng/boat-edge-clean/pull/1679)**. This PR deliberately avoids UI and server routing so it cannot compromise the already-unresolved production HTTP issue.

### Cross-chat handoff

**Shared reference: this Draft PR** (URL linked from PR itself). For any other BOAT EDGE CLEAN ChatGPT conversation:

> Main is unchanged. Inspect the position-sensitive four-mode shadow Draft and its tests. Current V2 fixes second/third ordering to one historical prior; new candidate independently tilts second/third probabilities using six national rates and preserves each first-boat mass. Its 12-race input-only replay changes Top1 in 9/12 and Top5 membership in 11/12, NOT verified accuracy. Coordinate with #1693 (forward validation), #1692 (venue/wind evidence), #1679 (UI/Render). Never overwrite old predictions or auto-merge. Do not adopt until independent future paired evidence proves gain.

**No automatic synchronization to separate ChatGPT threads exists**; the GitHub Draft is the canonical shared handoff.

## Exact-head GitHub Actions verification (2026-11-08 15:52 JST)

[Read-only CI #42456489975](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42456489975) **SUCCESS**, at Draft head `c20ce06e600cd11b8c93c42bfe4bc8129765f2f2`. Eight unit and negative tests passed. Input-only replay compared **116/116** original saved V2 files, **0 excluded**, verified exact recomputation of their original tickets and NEVER loaded confirmed results. No publication, model or runtime deployment.

| Saved Nov-08 cohort metric | Existing V2 | Position-sensitive shadow |
| --- | ---: | ---: |
| Hit/narrow/balance most common Top1 (`1-2-4`) | 109/116 | 42/116 |
| Hit/narrow/balance distinct Top1 combinations | 3 | 11 |
| Hit/narrow distinct Top5 ordered lists | 13 | 95 |
| Balance distinct Top5 ordered lists | 19 | 100 |
| Hole distinct Top1 combinations | 15 | 40 |
| Hit/narrow Top1 changed vs baseline | — | 76/116 |
| Hit/narrow Top5 membership changed vs baseline | — | 103/116 |
| Balance Top5 membership changed vs baseline | — | 106/116 |
| Hole Top1 changed vs baseline | — | 107/116 |

Although 6/116 hit/narrow/balance Top1 **first-boat numbers** changed, the candidate preserves the marginal first-boat probability exactly; this is reallocation among 2nd/3rd combinations, NOT evidence of improved first-place forecasts. **No historical outcome scoring or forward holdout was performed.** Archived original and live predictions are unchanged.

## Forward-only preregistration and result-LAST scorer (2026-11-08 JST)

[Separate locked protocol](../../research/four_mode_position_sensitive_forward_protocol_20261108.json) pins the exact Git blobs of the candidate selector, existing 1st-boat historical model and mode selector. Unlike existing #1693 Top1-pair candidate, this is a DIFFERENT candidate and NEVER overwrites #1693's original cohort or selector. Candidate coefficients remain 0.50 and 0.25.

The new [forward research module](../../four_mode_position_sensitive_forward.py) supports:
- Strictly pre-T−12 **local-only** freezing from the original exact V2 bytes (and recomputes all original rankings to detect tampering).
- Start **2026-11-09 JST**; no Nov-05–08 data admitted into prospective evaluation. A locally generated archive DOES NOT establish its independent first remote receipt, so it is **not formally eligible** until independently evidenced in a separate workflow after human integration.
- Explicit paired Top1/3/5/10 checks for all four modes, with earliest 300 pilot and next 300 confirmation by deadline/race key. Missing or invalid outcomes keep their reserved slot; do not replace or count them as misses.
- Outcome read occurs only AFTER the full supplied candidate roster/selector/original bytes pass pre-result validation; any invalid candidate fails the whole supplied comparison. Independently authenticated GitHub first remote receipt, complete capture inventory, 6-boat official predeadline evidence and 120 odds remain separate mandatory requirements.
- Current CLI without a verified original produces `preregistered_candidate_not_running` with `formal=false`. Nothing is published/scheduled or deployed from this PR; local archive output is never described as a trusted remote receipt.

Exact-head [GitHub Actions #42460952169](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42460952169) **SUCCESS** on head `77e123a86fa31d2b83fc124451f85f5438742891`. All **18** unit/negative tests passed, preregistration selector Git blobs were checked, and all 116 Nov-08 V2 input-only replays reproduced with zero exclusions. Forward captures **0**, formal evidence **0**, measured future improvement **unproven**.

### Handoff to other BOAT EDGE CLEAN workstreams

- **#1693 accuracy coordinator:** New candidate has **separate** locked policy and must not pollute the Top1-pair 300+300 study. Arrange a *genuinely predeadline* independent first remote receipt pathway for this candidate and separate prospective pairing only after manual approval.
- **#1692 venue/wind:** This candidate still uses only six national rates. Collect official 24-venue actual course, wind, motor, exhibition, wall data independently; apply only on future predeadline authentic evidence, never retrofit a favorable parameter.
- **#1679 UI/Render:** No current UI/Render/healthz modification; production HTTP incident remains separate.
- **#1698 this Draft:** Contains the immutable candidate, tests, and reference comparator; **do not merge or deploy automatically**.

## 2026-11-08 same-race TopK turnover exposure, NOT scored accuracy

Read-only [exact-head Actions #42465896933](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42465896933) succeeded: **22/22 tests**, 116/116 Nov-08 original saved boards reproduced, 0 excluded, preregistered three Git blobs unchanged. The new independent `position_sensitive_topk_exposure_audit.py` reads **only** `four_mode_forecasts`, not results, payouts, odds, or later outcomes. It uses the *same race, same fixed frozen selector*, and compares actual selected ticket membership and first/second pair effects, not artificial diversity constraints.

| Mode (fixed ticket budget) | Top1 ticket changed | Top3 membership changed | Top5 membership changed | Top10 membership changed | Mean changed slots Top5 / Top10 | Old Top1 absent from new Top5 / Top10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| narrow (5) | 76/116 | 97/116 | 103/116 | **N/A** | 1.750 / **N/A** | 28 / **N/A** |
| hit (10) | 76/116 | 97/116 | 103/116 | 108/116 | 1.750 / 2.647 | 28 / 9 |
| balance (16) | 76/116 | 96/116 | 106/116 | 112/116 | 1.750 / 3.000 | 31 / 11 |
| hole (22) | 107/116 | 113/116 | 114/116 | 115/116 | 3.500 / 5.397 | 86 / 71 |

These are **replacement/overlap counts, not acquired or lost winning outcomes**. In particular, 108/116 membership changes in hit Top10 means many opportunities for either improved or worsened results; it is **not** evidence of Top10 non-inferiority. The small `narrow` mode has only five tickets, so a distinct "Top10" does not exist. It is reported **N/A**, never padded with five imaginary losses. The primary frozen candidate model, result-last paired scorer, protocol SHA, original predictions, all collection paths and `main` remain untouched.

For this **specific preregistered candidate** (not #1693's selector), independent future pre-T−12 publication/first-remote receipts are still missing; the prospective cohort is **0**. The existing separate [pre-registration](../../research/four_mode_position_sensitive_forward_protocol_20261108.json) starts Nov 9 and reserves first 300 valid races for pilot and next 300 for confirmation. Only AFTER immutable pre-result candidate provenance and independent results are both established should its paired Top1/3/5/10 scorer calculate **baseline hits, candidate hits, gained hits, lost hits, denominators** in every mode. In the confirmation cohort, **any net Top5 or Top10 lost hits is an explicit block on promotion**; a nonnegative observed difference alone is still not a statistical demonstration of non-inferiority. If rigorous inferential support or input provenance is insufficient, retain **unproven/Draft**. Never tune the frozen coefficients using these outcomes.

### Mechanism coverage and next independent hypothesis

Current selector's **only per-race strength input** is the six national win rates. The tilt does NOT yet use verified actual entry/course, full six-boat exhibition, exhibition ST/turning/straight, motor, wind/height/direction, track condition, first/second-course wall performance or verified official 120-odds. Consequently it cannot claim to model all the race-specific effects requested. Before testing a later **new study identity**, require a typed, timestamped, independently preserved evidence vector with six named boats, actual entry, official T−12 completeness, course/ST/motor/exhibition and weather applicability; reject incomplete or late inputs rather than invent or backfill them. Distinguish pre-race historical ST from exhibition ST and do not treat wind effects learned at one venue as universally transferable. Keep first-boat probability changes separate from this frozen 2nd/3rd hypothesis and use fresh independent chronological holdout. All weather/venue source research remains owned by #1692, cross-mode general accuracy by #1693, and hole-specific hypothesis research by #1685/#1688; this PR only evaluates this selector's paired TopK exposure and prospective non-regression.

**Evidence status (2026-11-08):** data input sensitivity proven; 116 saved races audited result-blind; 22 tests pass; confirmed improvement **0**; verified independent future candidate receipts **0**; production promotion **prohibited**.

## 2026-11-08 paired loss guard (separate from frozen model and all-mode #1693)

A new **research-only** `position_sensitive_paired_guard.py` checks the **already existing**, result-last `FOUR_MODE_POSITION_SENSITIVE_REFERENCE_SCORE_V1` aggregate. This code does NOT read outcomes, does NOT edit the original candidate selector or preregistration identity and does NOT provide independent future first-remote receipts. It has no production import.

The guard validates all four modes and Top1/3/5/10 paired denominators, gained/lost partition, count bounds, phase allocation (300 pilot then 300 confirmation), duplicate/missing reserved slots and monotone nested TopK hit counts. The five-ticket **narrow Top10** is explicitly **N/A**: the original reference scorer can slice `[:10]` from a five-ticket list, which is only Top5 repeated; it must never be interpreted or published as a distinct Top10 accuracy. If the apparent narrow Top10 counters differ from Top5, the guard fails rather than hiding the discrepancy.

The guard has a synthetic test case in which the candidate's **Top1 gains 10 hits** while its **Top5 and Top10 each lose 5 net hits** in a fabricated confirmation roster. It flags those losses as disqualifying observations; a corresponding positive/zero Top5/Top10 case still cannot be promoted because reference-only aggregates do **not** prove independent pre-result provenance, official inputs, accurate outcomes, calibration, statistical noninferiority or representativeness. Missing even one of the 600 reserved verified results leaves the confirmation regression status **undetermined**.

**This is a safety test, not real performance data.** The user requirement to retain Top5/Top10 quality remains unresolved until a future result-independent predeadline receipt pipeline and prespecified confirmatory statistics are genuinely established. The guard always returns `formal=false`, `promotion_allowed=false`, `model_improvement_proven=false`.

The new CI tests also check zero prospective samples, tampering of aggregate counters, forged verification flags, inconsistent TopK hit counts and the unmodified original 116/116 result-blind replay. Do NOT merge or deploy this Draft, alter #1693's overall-accuracy cohort, borrow the hole mode's dedicated experiment or retrofit outcomes to the original selector.
