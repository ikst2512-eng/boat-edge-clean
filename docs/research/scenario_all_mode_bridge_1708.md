# Issue #1708: all-mode scenario bridge (research only)

**State:** Draft research, no deployment, no original forecast edits, no model
promotion. This bridge demonstrates a reproducible **common 120-ticket
scenario mixture** feeding **all four existing modes**, plus a separate
**attack/benefit-supported hole hypothesis**. It is not yet a fully trained
weather/tide/exhibition model.

## Why this is new rather than reimplementing prior PRs

- Existing main `research_model.probabilities()` uses six national win rates
  and a frozen 1,000-race board. Main `clean_four_modes.rank_modes()` uses
  the same base probabilities for narrow=5, hit=10, balance=16, hole=22.
- Draft #1698 owns **conditional second/third evidence-aware likelihoods**.
  We do not copy its coefficients/selector or rewrite its fixed 300+300 cohort.
- Draft #1692 owns venue/wind/tide/wave evidence and official orientation gaps.
- Draft #1694 owns same-race official six-boat beforeinfo, official 120 odds,
  source timestamps and independent first-receipt provenance.
- Draft #1693 owns full-mode prospective Top1/3/5/10 results evaluation.
- Draft #1685 owns hole-pair safeguards. Draft #1706 owns recovery; #1707 UI.
- This PR introduces the **missing reusable join**: accept scenario-specific
  probability boards after upstream models have consumed reliable inputs,
  mix them with explicit weights and pass one resulting board to the existing
  mode selector. Outputs identify which scenario contributed to each pick.

## API contract

`compose_scenario_research(scenario_boards, scenario_weights)` takes:

- Keys: `escape_wall`, `two_sashi`, `third_attack`, `fourth_cado`,
  `outer_benefit`, `deep_entry` (any nonempty subset).
- Each supplied board: exactly 120 **unique** 3-tuple tickets covering
  six boats in finishing order; real nonnegative probabilities summing to 1.
- Each scenario's weight: **explicit** finite number between zero and one,
  with total exactly 1. The function provides no default or inferred weights.
- Caller must construct its boards separately from **pre-result** features;
  this bridge does not infer evidence from input names or fabricate
  wind/course/tide effects. A scenario weight is a **hypothesis**, not a
  measured likelihood, unless validated in a separate future study.

Outputs: `existing_four_mode_selector_on_mixture` for all existing
budgets; `top10_reference`; `separate_scenario_hole_research` choosing
up to 22 non-top-10 tickets ranked by conditional mass contributed by
third attack, fourth attack or outer benefit. When none of those scenarios
has positive weight, hole scenario output is **unavailable**, not
invented. This separate hole comparator **does not** change the original
hole mode's rank-11..32 policy or any saved prediction.

The bridge computes per-scenario **board fingerprints**, but those fingerprints
are NOT source HTTP receipts or verified first-remote publication. All
formal/calibration/deployment/ROI flags remain false. No results or payout files
are read. Internal `model_score_pct` is **not** a calibrated betting probability.

## Required next interfaces — do not fake missing source data

1. **Evidence adapter (owned by #1694 and #1692):** pass race ID, six
   registration IDs, title/cards SHA, exhibition six, observed entry (distinguish
   exhibition from final entry), six ST, motor age/parts, actual venue,
   measured weather time/wind FROM bearing, water/heading primary evidence,
   wave height, and tide station + observed/predicted tide phase/rate.
   Every applicable field needs source bytes + hash + valid receipt before T−12,
   else mark `unknown`; don't silently turn unknown into zero. Tide is NOT a
   uniform sea-water multiplier and wind FROM requires geometry validation.
2. **Scenario emitter (new research identity, #1698 owner for conditional
   ranking):** compute separate 120-way conditional boards for 1-escape with
   two wall, 2-sashi, 3-attack, 4-kado attack and 5/6 beneficiaries.
   Clearly separate attacker's survival from an outer beneficiary's finish.
   Estimate scenario weights from independently held-out future data; no
   result/post-cutoff values in a prediction run. Do **not** overwrite frozen
   #1698's six-rate 0.50/0.25 candidate or its preregistration.
3. **Paired formal evaluation (#1693):** new **distinct** selector identity,
   preregister before genuine first future prediction. Independently retain
   full first remote receipt + official T−12 six/120 evidence and all scheduled
   attempt inventory. Compare fixed same-race Top1/3/5/10, calibration,
   gained/lost hits and optional ROI only with verified 120 odds and payouts;
   pilot 300 + confirmation 300. No promotion if Top5/10 regression is hidden.
4. **Display (#1706 then #1707):** only after site recovery and model
   approval, show selected modes, top scenario, attack/benefit grounds, used
   features and their timestamp, plus missing/unverified features. Never label
   a hypothetical score as a verified prediction.

## Run tests

```bash
python -m unittest -v test_scenario_four_mode_bridge
```

CI is PR-only; no cron, dispatch, source collection, Git publication,
Render/CORS/WebKit/UI modification or main merge.

**Important:** A green unit test proves only this mathematical integration's
input guards and deterministic behavior. It does not prove better hit rate,
official wind/tide receipt or deployment.


## Follow-up 2026-11-09 — separately test first-head probability and actual feature sensitivity

This Draft now includes two **research-only** pieces in addition to the original scenario mixture.

1. `scenario_first_head_research.py` accepts an existing 120-way
   baseline and six **explicit uncalibrated head log-shift hypotheses**.
   It alters `P(first=h)` with stable normalization but preserves each
   `P(second,third | first)` exactly. It exposes the separate first-head
   mass to resolve a limitation of the locked #1698 second/third research,
   while **never changing #1698's registered SHA or candidate**.
2. `scenario_feature_effect_probe.py` runs an explicitly supplied
   result-blind research emitter twice, once per caller-supplied alternate
   feature value, and compares the **entire mixed 120-way digest** and
   Top1/5/10 picks. Fields can include six national rates, local rate,
   ST/exhibition, motor, exhibition entry, wall/escape assist, wind speed
   and bearing, wave height, tide height/phase/station and venue. This
   checks **numerical sensitivity only**, NOT predictive importance or
   causal validity.
3. A fixture **supplies both wind and tide values**, but the hypothesis
   emitter uses only wind. The unit test must report that wind changed
   the board while tide did **not** change it. Tide being present in the
   input does not mean it was consumed by the model.
4. Any supplied result, payout, final post-race entry, post-race wind,
   non-finite feature, forged formal result, unsupported field or invalid
   complete-board hash is rejected. Research outputs remain
   `formal=false`, `production_changed=false`, with no source
   authentication or independently witnessed first receipt.
5. The new research first-head shifts are caller-supplied hypotheses,
   **not** coefficients derived from official wind or tide. Neither
   the model nor the tests automatically predict the weather or fit
   oceanographic relationships. Real conversion from course/venue,
   wind and tide to scenario/head likelihoods still requires
   #1692/#1694 source semantics, a separately preregistered identity
   and #1693's forward 300+300 results.

### Extended test command

```bash
python -m unittest -v test_scenario_four_mode_bridge test_scenario_first_head_research test_scenario_feature_effect_probe
```

**Important restriction:** `prestart_entry_course_observed` is **not**
the final result's actual entry course; no post-race entry can be fed
into a pre-race forecast. Exhibition entry may differ from live entry.
Unverified absolute wind FROM bearing or undocumented tide station
relationship must be marked missing, not guessed and not reported as
a verified effect. This feature-effect inspector cannot itself certify
any remote official input, time-of-measurement or output publication.

## 2026-11-09 continuation — actual official-parser integration seam (no parser copy)

New `scenario_official_exhibition_projection.py` accepts the **exact
existing** #1693 lineage bundle and candidate and an *injected*
`four_mode_official_raw_semantic_replay.replay` callback. #1693 is still
a separate Draft PR, so this research branch does not copy its official
parsers, rewrite their tests, or silently treat them as deployed.

- Requires same 12-digit race identity, 24 venues/12 rounds, JST deadline
  and generation before T−12, all three claimed source raw bytes with
  matching SHA-256 and source receipt clocks before generation/T−12.
- Requires matching claimed normalized source hash, matching six unique
  racer registrations, six complete exhibition times, start-exhibition ST,
  tilts, six unique **exhibition** courses and exactly 120 finite positive
  3連単 odds entries. Rejects result, payout and final entry keys.
- Only after these **structural** checks, invokes the existing #1693 raw
  semantic reparser. It demands the existing five actual-parser stage names
  and its specifically nonformal result. Does **not** itself parse official
  source content or prove authenticated HTTP origin/time.
- Output: `exhibition_features_by_boat` + exact three source fingerprints
  and normalized-claim fingerprint. These are **research input candidates**
  only; **actual final race entry is not exhibition entry**, and it is
  **not** renamed as such.
- Output marks venue relative wind direction, wave, tide height/phase/station,
  motor, wall/escape-assist and actual entry as missing. They are not
  imputed from stadium articles or historical results.
- Even a successful injected callback does **not** authorize
  `formal=true`, live forecast, odds-based ROI, calibrated probability,
  accepted first Git receipt, actual model use, or model promotion.
- Synthetic unit fixtures use mock bytes and a callback stub; passing the
  tests proves the interface/negative checks, **not** successful capture or
  real official-source replay. Genuine #1693 raw parser can be wired
  only after separately reviewing its changes and authenticating real
  predeadline first-remote receipts via #1694.

Extended PR-only CI:

```bash
python -m unittest -v test_scenario_four_mode_bridge test_scenario_first_head_research test_scenario_feature_effect_probe test_scenario_official_exhibition_projection
```

This is a **read-only research adapter**, no changes to #1693/#1694/#1698
frozen code, result collector, action schedule, historical forecasts,
main, Render or UI. It should never be directly exposed to users as
production predictions.


## 2026-11-09 follow-up: pinned #1698 actual conditional math wired into all modes

The new `scenario_exhibition_all_mode_runner.py` is a **read-only,
unregistered research orchestrator**. It accepts an output from the
nonformal `scenario_official_exhibition_projection.py`, six caller-supplied
national win rates, explicit per-scenario first-place log shifts and
conditional-second/third coefficients, explicit scenario mixture weights,
and the *existing* #1698
`experimental_conditional_board` passed as a callback.

### Actual data path (research-only)

1. The official-exhibition *projection* must identify **one** race and
   six unique registration numbers, preserve all three source-claim SHA-256s,
   and include its newly added `exhibition_features_sha256`, which binds
   the full six-boat projected exhibition vector to the orchestration input.
   An altered vector with unchanged SHA is rejected.
2. `research_model.probabilities()` supplies the **unchanged** original
   national-win-rate baseline. **Its six supplied rates are not independently
   bound to the same official first-receipt chain** by this runner.
3. For each scenario, `hypothetical_head_board` applies the
   **caller-provided and uncalibrated** six-boat first-place shift. It
   preserves conditional second/third distributions. Those head shifts
   are **not learned from official ST, wind, tide, motor, entry or water**.
4. #1698's existing conditional lab (no copied implementation) then
   reweights second/third given the head using **six supplied exhibition
   ST values**. The integration enforces the actual lab response contract,
   checks 120 unique normalized ordered tickets and verifies exactly
   conserved mass for each first boat.
5. The original #1710 mixed-scenario bridge combines those six-place
   probability boards into one common board for **all four existing
   5/10/16/22-count modes**, plus separate attack/benefit supported hole
   hypotheses. All coefficients/weights are explicit unregistered
   numeric *hypotheses*, not empirically supported effects.
6. Output fingerprints include original source SHA, normalized claim SHA,
   full six-exhibition-vector SHA and combined 120-way board SHA.
   **None of these alone constitutes independently attested HTTP source
   origin or remote-first prediction acceptance.** Live model is unchanged.

### Real integration defect detected; safe restriction (do not conceal CI failure)

A first cross-PR CI attempt,
[Actions #42623798530](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42623798530),
ran 28 local checks successfully and fetched exactly pinned
#1698 commit `6de21c9d1584f354161fde47293af72cca8d0100`,
file blob `1e58fd62134a3aa4121b636e12005d04b5026748`.
But 4/8 integrated tests **failed** due to
`ValueError: invalid_exhibition_time_s`. The **unregistered #1698 lab**
declares `exhibition_time_s` valid 40–90 seconds, while official raw
beforeinfo and #1693 fixtures use exhibition times **around 6–7 seconds**;
the #1698 synthetic fixture itself uses 47s. It is a unit-schema bug,
not a valid excuse to multiply real exhibition times by 10.

The #1698 owner was notified in its existing Draft review comments.
Until that lab's units/tests are fixed and separately reviewed:
- **Only exhibition ST** is allowed to influence #1710's live research
  integration; exhibition time/course/tilt are retained in projected
  metadata **but not scored**.
- The runner rejects any attempt to activate `exhibition_time_s`
  coefficients or to feed missing unverified actual entry, wind, wave,
  tide, wall or motor data. No fake values, 10x time transformation,
  wind bearing or tide phase inference.
- A unit test changes exhibition time (with the synthetic projection
  checksum recomputed) and confirms the research 120-board **does not**
  change; another changes ST and confirms it **does** change.
- **Fixing the #1698 lab must not alter its frozen 0.50/0.25 candidate,
  registered method SHA or 300+300 cohort.** This PR does not commit
  to its branch or implement a duplicate conditional ranking method.

After blocking unsupported time inputs, the exact-code integration
[Actions #42624423181](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42624423181)
**passed all 37 tests (28 isolation + 9 using the actual pinned #1698
conditional-likelihood implementation)**. These use **synthetic**
projected exhibition and explicit coefficients. Not authentic official
capture, not validated wind/tide, not real T−12 evidence, not prospective
Top1/3/5/10 improvement. `formal=false`, `forecast_usable=false`,
`production_changed=false`, `promotion_allowed=false`.

Next: #1698 repairs the exhibition-second bound in its *unregistered*
lab, #1694 supplies **independently first-remote-attested** three-source
official raw originals captured before T−12 for the same race, #1692
validates any specific wind-bearing/tide-station semantics, #1693
evaluates a *separately registered* future hypothesis 300+300 without
outcome leakage, and #1706/#1707 independently recover and render
only an approved model. This Draft cannot be merged automatically.


## 2026-11-10 update — restore authentic exhibition-second units in the unregistered lab

The 40–90s exhibition-time unit mismatch was fixed **only** in
#1698's `position_sensitive_conditioned_lab.py` (unregistered
experimental lab), changing its range to **5–10s**, alongside a
6.7s synthetic fixture and a test that rejects the old 47s input.
No production selector, preregistered method SHA or 300+300 candidate
was changed. The owner PR's two Actions workflows passed:
[isolated conditional lab #42776115254](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42776115254) and
[position research checks #42776115160](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42776115160).

This #1710 integration now reads the **immutable corrected #1698**
commit `e152b57033f825e02343b004a9c013a8998f9954`, validates
module blob SHA `0019978a4e27a1235d0b466c11f514bd7105f261`,
then uses real-second `exhibition_st_s` and
`exhibition_time_s` as *explicit uncalibrated research inputs*.
No artificial ×10 conversion and no wind/tide/motor/wall/final-entry
imputation. Exhibition course/tilt are still metadata only, not scored.

The added positive/negative tests prove:
- True-second exhibition time changes the 120 score board if its
  hypothetical coefficient is nonzero;
- A zero time coefficient preserves the board under time variation;
- Exhibition ST changes the board under a positive hypothesis;
- Missing or unauthenticated other features cannot be silently supplied;
- All 4 existing modes remain available with 5/10/16/22 comparative
  budgets, plus an isolated scenario-supported hole comparator.

Latest exact-head [research CI #42776275920](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42776275920)
**passed 38/38 tests (28 independent + 10 real-code cross-PR integration)**.
This is structural/synthetic validation and does **not** verify real
official HTTP T−12 source receipt, independent first remote Git save,
forecast accuracy/calibration, live model promotion or site rendering.
The old failure and temporary ST-only workaround remain recorded
above as historical change context, NOT the current effective input
policy.

Both #1698 and #1710 remain Drafts. The existing frozen candidate
and raw prediction archives remain untouched; do not auto-merge main.

## 2026-11-10: Same-race four-mode overlap cause and NON-forced scenario-lens prototype

**Actual production root cause, not only visual duplication:** `research_model.probabilities` uses national win rates only to reweight *1st-place mass* over a fixed historical 120-way conditional joint prior; `clean_four_modes.rank_modes` selects `narrow=ranked[:5]`, `hit=ranked[:10]`, `balance` via a mild same-board diversity heuristic, and `hole=ranked[10:32]`. The current site reads original archives produced by that code. Therefore narrow is **always exactly contained in hit** on the same race, no matter what the six rates are. The #1698 fixed conditional second/third shadow changes ranked tickets **across races** but still sends both modes the **same new 120 board**, so it also cannot resolve this within-race overlap.

**Real Nov10 main original replay**, read only, never results: [#1698 150-race source-anchored CI #42781587238](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42781587238) verified 150/150 actual saved V2 tickets against original national rates; narrow top5 was a subset of hit top10 in **150/150 both original AND frozen #1698 candidate**. Narrow and hit Top1 were identical in **150/150** for both. Across all four modes the same-race number of distinct Top1 tickets was **exactly two in every one of 150 races** in both versions. This is **within-race structural redundancy**, not the same question as the earlier across-race `1-2-4` frequency drop. The 150 records are **not** accepted independent prospective tests, and their original stored fields did not include verified official six exhibition/odds120, independent Git first receipt, final entry or wind/tide.

**Former standalone prototype (deleted during consolidation): `scenario_mode_specific_lens_research.py`:** imports the EXISTING `compose_scenario_research` four times instead of copying its 120-board mixing math. It requires a *separate explicitly supplied normalized scenario-weight dictionary* for each of `narrow`, `hit`, `balance`, `hole`. A mode's rankings come only from **its own explicitly evidence-supported scenario mixture** (e.g., narrow strongly supported escape, another mode genuinely supported two-sashi/third attack); the existing unchanged `rank_modes` still sets that mode's ticket budget at 5/10/16/22. The research output reports within-race Top1 and ticket overlap. **It does not subtract tickets already used by another mode, penalize duplicate Top1, invent a distinct scenario, use odds as proof or mandate a difference.** If mode weights/boards match, narrow remains nested inside hit and that is acceptable. If hypothetical race scenarios genuinely change the relative probabilities, Top1 and ticket sets can differ.

**CRITICAL**: No authenticated source-derived, race-by-race mode-specific scenario weights are yet available or statistically calibrated; therefore this is deliberately an **unregistered, synthetic-only design proof** with no live display, forecast production, source publishing, hit-rate/ROI proof or approval for betting. Do not hand-set a per-mode weight just to move tickets. Before deployment, the collector/replay owner must supply **same-race, pre-T−12 raw official racelist, exhibition/ST six, odds120, verified entry/conditional wall/weather when available**, independent first source and forecast remote receipts; #1692/#1694/#1693 must preregister and prospectively demonstrate each hypothesized weight and Top1/3/5/10 no-degradation. Results must be reserved out of coefficient fitting. No main auto-merge, no UI or production modification, no manual live selector override.


## 2026-11-10: Exhibition-course proxy to existing #1698 conditional 2nd/3rd lab

The complete six-boat **exhibition** course permutation already survives the
#1693-compatible raw feature projection (by boat / racer identity), but
#1710's runner previously passed only exhibition ST and time. This update
passes each boat's `exhibition_course_only` to the **existing pinned**
#1698 `experimental_conditional_board` as `entry_course`, available
for explicitly nonzero *research* coefficients. No #1698 model is copied or
changed. `actual_entry_course` and `two_course_wall_rate` remain missing,
not inferred from boat numbers. Race-time final entry must never be treated
as a legitimate pre-T12 input, and boat 2 is not inherently the entrant in
course 2 (see #1692 official K event-entry discrepancy).

The runner records `feature_fields_actually_activated_by_scenario`, separates
nonzero coefficient consumption from merely supplied data, marks
`entry_course_input_semantics=synthetic_projection_exhibition_only_not_final_actual_entry`,
and explicitly reports
`two_course_wall_feature_or_final_entry_used=false`. Zero course
coefficients leave the probability board invariant under an exhibition-course
swap; explicit nonzero coefficients can alter conditional 2nd/3rd ordering.
Invalid duplicate courses, altered source-vector SHA and false provenance
are rejected. Any such numeric sensitivity is *not* empirical evidence
that the course proxy improves forecast hit rates.

All inputs in tests are synthetic; the pipeline still requires authenticated,
pre-T12 three-original source receipts, correct official source matching,
independent first-remote forecast receipt, calibrated coefficient estimates,
separate preregistration and 300+300 forward paired evaluation. Present
status remains `formal=false`, `forecast_usable=false`,
`promotion_allowed=false`; no new live picks, archive rewrites, main merge,
Render/GitHub Pages change, collection job, or forecast scoring.


## 2026-11-10 — Actual 6-exhibition → conditional 2/3 → FOUR DIFFERENT MODE LENSES connected

New module `scenario_mode_specific_exhibition_end_to_end.py` (this Draft only) joins the **already reviewed separate functions**, with no copied collector or 2/3-place math:

1. The existing #1710 `scenario_official_exhibition_projection.project_exhibition_research` validates exactly six racer registrations and exhibition ST/time/tilt/course from caller-supplied raw original bundles. Its real HTTP source, first-remote timestamps and true consumption remain **unverified**; exhibition course is not final entry.
2. `scenario_exhibition_all_mode_runner.run_exhibition_scenario_lab` already invokes #1698's **pinned actual `experimental_conditional_board` callback** against six exhibition ST/time, plus #1710 scenario head-mass hypotheses, and returns the exact 120 probability board per scenario.
3. This wrapper now computes each scenario's first-place and conditional 2nd/3rd board **once per race**, sharing identical scenario hypotheses and conditional coefficients across all modes, then applies the **explicit per-mode weight dictionary** only in the inexpensive mixture stage. No repeated scenario-model calls or hidden mode-specific coefficient overrides.
4. Each mode's **own** normalized scenario mixture is handed to the existing `rank_modes`, selecting exactly its original 5, 10, 16 or 22 tickets; cross-mode overlap is an independent reported diagnostic, not a selection constraint. The adapter never edits current archived forecasts or `main`.

**Real independent GitHub CI executed pinned #1698 code from SHA** `e152b57033f825e02343b004a9c013a8998f9954`, exact verified Git blob `0019978a4e27a1235d0b466c11f514bd7105f261`. In an expressly **SYNTHETIC** source fixture with supplied escape/two-sashi/third-attack/outer-benefit scenario weights, the resulting four-mode Top1 included **3 distinct tickets**, not four; this is correct behavior, because a genuine overlap must remain permitted. All 4 mode budgets, full 120 boards, preserved source fingerprint, ST feature sensitivity, bad digest, missing mode, nonnormalized weights, illegal outcome injection and fake formal/head-mass claims are tested. When all four mode weights are identical, narrow's top5 remains nested in hit's top10: **no artificial mode disjointness**.

Final standalone+integration CI: [#42784923721](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42784923721) **SUCCESS, 38 existing research unit tests + 21 pinned #1698 integration tests**. The first attempt [#42784767405](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42784767405) failed because a test incorrectly **required four distinct Top1** instead of accepting observed 3; the false uniqueness requirement was removed, not a change to model coefficients.

**LIMITATIONS (blocking live rollout):** The head shifts, conditional coefficients and separate per-mode scenario weights in tests are **unregistered, hypothetical and not fit to official past-only training with a prospective future holdout**. The pipeline can consume structurally checked six exhibition ST/time, but no independent same-race official beforeinfo+racelist+odds120 T−12 first original receipt, actual-source model lineage, independent *first Git remote forecast receipt*, verified entry/wind/wave/motor/wall/tide or fresh 300+300 Top1/3/5/10 outcome improvement has been demonstrated. The test fixture's hashes can be recomputed by the caller: this is **not** source authentication. No betting probability calibration, performance claim, or permission to use on the live website. It does not and cannot solve the site overlap until reviewed, independently validated forecasting weights are deployed after the display recovery. **No forced diversity, main auto-merge, source rewrite, live deployment or current predictor change.**

## 2026-11-10 — Code cleanup and exact-ticket regression at latest Draft HEAD

To eliminate genuinely unused research code rather than merely add another proof-of-concept, **deleted two superseded files**: `scenario_mode_specific_lens_research.py` (103-line isolated prototype) and `test_scenario_mode_specific_lens_research.py` (143-line duplicate prototype tests). The real 6-boat end-to-end pipeline now owns the needed functional coverage. Canonical `MODES` / `BUDGETS` constants live only in `scenario_four_mode_bridge.py`; the end-to-end module imports those instead of a competing duplicate source.

Removed redundant expensive calculations: previously each of four mode lenses reconstructed the **same four scenario 1st-place hypotheses + #1698 conditional 2nd/3rd callbacks**, totaling **16 conditional callback invocations per race**. The shared `_compute_exhibition_scenario_boards` runs the **four scenario callbacks once**; four mode-specific weight mixtures are still calculated separately. **12/16 = 75%** of conditional callback invocations are eliminated for the four-scenario test case (the 4-mode 120-board output, weights, and budgets are not changed). No claim of a measured end-to-end latency speedup is made.

Added full exact-ticket equality regression: the optimized 4-call path is compared against all four outputs of the previous existing `run_exhibition_scenario_lab` method on exactly the same pinned #1698 callback. Checks all 5/10/16/22 output tickets, each mixed-board SHA, and per-scenario board hashes. Negative tests still reject unnormalized weights, false formal provenance, missing/inconsistent official six features, and false final entry. Existing synthetic 3-distinct-Top1 result remains a *demonstration of model structure*, not live accuracy or a requirement for four separate picks.

**Final research CI** [#42786647565](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42786647565) **SUCCESS: 28 core research tests + 22 pinned #1698 integration tests = 50 PASS**, including exact output parity. The lower raw test count reflects **intentional deletion of redundant prototype tests**, not skipped end-to-end validation. No changes to live predictor, main, Render, archived model forecasts, preregistered coefficients, source collector or independent 300+300 accreditation.


## 2026-11-10 ②担当：実保存6艇勝率×既存公式展示の2種類入力感度比較（非正式）

**目的**: 先行の実HTTP展示3/4レース再演で使った「全艇全国勝率5.0」の中立仮説を、**mainに実在していた凍結V2全国勝率6艇ベクトル**に置換して、4モードの順位が本当に動くかを結果を読まずに測る。#1710 の既存 `scenario_actual_pair_four_mode_replay.py` / #1698のハッシュ固定条件付き数学を再利用、既存予想と原本は変更しない。

- 既存の研究Draft #1710 へ `scenario_archived_rates_ablation.py` と拒否テスト `test_scenario_archived_rates_ablation.py` を追加。既存の一度きり実原本検証 workflow `scenario-official-pair-real-inject-once.yml` **だけ**に、凍結main `1e8b6b86e4c700bcf10b5dfcb4cdaa981799bb78` から4ファイルを `git show` で展開し**各Git blob SHAを照合**する工程を追加。新cron/本番収集/保存予想変更はなし。
- 4原本：`202611091110` blob `492f9d73`、`202611091710` blob `75252b29`、`202611101202` blob `d7801a87`、`202611102211` blob `f6f20088`。すべて保存時の `beforeinfo=optional_not_in_snapshot`。**公式racelistに由来する確証はなく、既存CSV系V2原本から抽出した数字**。予想自己申告生成時刻と既存公式原本受領自己申告時計の順序は検査するが、独立初回遠隔受領を証明しない。
- 既存実公式beforeinfo＋odds ZIP 2本、#1698 fixed Git blob、#1710シナリオ重み・2/3着条件付き係数・展示ST/展示タイム/展示進入を固定し、①「中立全国勝率5×6」対「V2保存全国勝率6艇」の入力だけ変更、②「保存全国勝率6艇」を固定したまま**未検証の各世界の1着log-shift [3.5]だけ全艇0へ**変更。②の除去は正式採用ではなく研究用の単一因子アブレーションであり、確率の再学習ではない。
- **完走証拠**：CI [#42797077372](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42797077372) `completed/success`、実行HEAD `04e4a84c996a8c7487c2327c39a252ff64ccd86c`。PR-only bridge regression [#42797090440](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42797090440) `success`。生成成果物 [#13753901951](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42797077372/artifacts/13753901951) ZIP SHA256 `7238ffe171c0549e13a61cb8d9bfc161a6c0dfcbc07a0c2e6060c70706e58690`、ZIP全CRC正常。公式展示STが揃った3レースのみ研究演算、福岡11Rは欠測で拒否。
- **実際に12ボードで変わった数**（3完全レース×4モード。モデル入力感度、結果照合ではない）：
  - 6艇勝率 中立5→保存V2実数値：120票SHA変化 **12/12**、Top1券変更 **1/12**、選出券集合変更 **4/12**。内訳：絞り0/3・本命0/3・バランス1/3・穴3/3で券集合変更。Top1は穴モード住之江2Rのみ。
  - 6艇保存勝率を固定して**未校正の1着シナリオlog-shiftを除去**：120票SHA変化 **12/12**、Top1券変更 **7/12**、選出券集合変更 **10/12**。これは「仮説の強さ」への感度であり、正解や有効性の証拠ではない。
- **解釈**：この3レースの *特定の* 仮説シナリオ強度・重みでは、全国勝率入力より**未校正の頭仮説によって上位買い目が左右されやすい**。モード間の見かけ上の差を的中精度改善とみなさない。これらの3レースで係数をチューニングしない。#1710に追加した研究コードと #1698固定済み事前登録0.50/0.25は別ID、既存コホートを変更しない。
- 依存/次段階：#1713/#1694の**同一将来レース公式racelist＋beforeinfo展示/ST6艇＋オッズ120＋T−12源受信時刻**と、実モデル消費fingerprint及び独立FIRST候補遠隔保存が必要。①③の責任分界を守る。別IDでシナリオ係数を事前凍結し、#1693の300予備+300独立確認で既存と同予算Top1/3/5/10・lost/gained・確率校正を評価。Top5/10を悪化させる場合や証拠欠落時は本番禁止。**本件は formal=0/600、forecast_usable=false、improvement_proven=false、本番配備なし。**


## 2026-11-10 ②担当：保存済み旧V2 vs 実展示条件付き4モードのTopN同レース対照

**本件は精度実績ではなく、実レースの保存済み予想と数理研究の同一レース・同じ点数比較を実行したもの。結果・払戻を一度も読み込まず、候補を後付け生成して正式採点へ入れることはない。**

### 既存研究を再利用して実行した内容
- 前回追加した `scenario_archived_rates_ablation.py` と既存 `#1710` の実公式beforeinfo/odds ZIP 2本、`#1698` のハッシュ固定 `experimental_conditional_board` を再使用。凍結main `1e8b6b86e4c700bcf10b5dfcb4cdaa981799bb78` に保存された11/9・10のV2予想原本4ファイルのGit blob SHAを独立照合し、予想原本の当時の5/10/16/22券を**そのまま**ベースラインとした。
- 各モードの `Top1/3/5/10`（絞りTop10は**不適用**）について、旧V2原本 vs 既存の未校正3.5頭log-shift研究と、旧V2原本 vs 全シナリオ頭log-shiftゼロの対照研究の**買い目集合の一致数**を出力した。研究モデルの係数/場×シナリオ重みは一切調整しない。今後の正式候補は別ID・事前固定が必要。
- 元V2原本の四モード欠落、非合法券、重複券、点数不一致、変更されたGit blob、結果フィールド混入、未来同時刻/締切遅延、仮説Top1と券の不一致を拒否するテストを既存 `test_scenario_archived_rates_ablation.py` に追加。旧原本の変更/欠損は後のレースで代替せず失敗する。

### Actions完走・成果物の実確認（2026-11-10 JST）
- [exact-head 実ZIP研究CI #42798571262](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42798571262) **completed/success**、head `a721e94c4437a3fbfea06d97f7abbce44bbd0d20`。[PR安全回帰 #42798582330](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42798582330) **success**。
- [Artifact #13755423409](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42798571262/artifacts/13755423409) ZIP SHA256 `2bb88930c1e766f7d62f7c062c8622fcd0bf0a6acad6d1f9cf335e1b7bd19201`、**ZIP全CRC検査成功**、内部 `research-archived-rates-vs-neutral.json` を展開/確認。過去実レース3件（びわこ10R `202611091110`、宮島10R `202611091710`、住之江2R `202611101202`）×4モード=12対照。福岡11R `202611102211` は展示ST不完全につき一切計算せず拒否。
- 元V2→**未校正頭3.5研究**：Top1買い目 **10/12変更**、Top1の1着号艇 **6/12変更**、Top3集合 **11/12変更**、Top5集合 **12/12変更**、Top10集合 **9/9変更**（絞り3件はTop10不適用）。
- 元V2→**頭shiftゼロ対照研究**：Top1買い目 **9/12変更**、1着号艇 **2/12変更**、Top3集合 **10/12変更**、Top5集合 **9/12変更**、Top10集合 **9/9変更**。
- 同じ3レースでも `1-2-4` を残す場合がある（住之江2R、絞り/バランスでTop1維持）。**モードを必ず別買い目にする処理なし**。変更が多いことは改善や多様性を目的にした正しさではない。未知の差し/攻め/壁や実績を「検証済み」と表示しない。

### 対照設計と正式600件へ進める条件
1. 同一レースで「公式racelist原本／beforeinfoの展示・ST全6艇／公式3連単オッズ120／T−12前source受信／6艇ID一致」の独立証拠を③/#1713・#1694が提供するまでは、新予想が公式直前情報を正式消費したと認めない。今回の旧V2生成時刻は公式展示ソース受領より**前**であり、旧V2が展示を使った事実はない。出走表の全国勝率を実公式原本と突合した証拠も欠落。
2. ②は既存 `#1710` を使い、同一ソースの6艇勝率・展示タイム/展示ST/展示進入・先頭艇条件付き2/3着・すべてのmode scenario weightsを**単一研究ID＋コード/入力/重みのハッシュ**で固定。人手設定の `3.5` を効果確認なしに「正しい係数」へ昇格しない。風・潮・実最終進入/2コース壁は独立証拠がない限り unknown、非適用。
3. `#1693` の既存登録600件へこの新研究を紛れ込ませない。`four_mode_forward_paired_score.py` はすでに **unregistered scenario bridge拒否**と結果LASTを実装済みであり、採点器を複製しない。**別IDでの将来のみ事前登録**と完全な無人run/救済run監査、候補の初回遠隔独立受領がそろって初めて予備300+確認300で同一レース・同点数Top1/3/5/10を評価。欠損/不適格を「外れ」に算入・補充禁止。Top5/10が不利であれば昇格しない。
4. シナリオ重みの条件を現行の「モードごとの手指定」から「そのレースで事前に得た実データによる推定」へ移行するには、**独立登録の別研究**が必要。今回の3レースに合わせて係数や重みを調整してから同じ結果で有利と主張しない。

**結論：シナリオ数理が保存V2原本と異なる候補を生成することは検証済み。的中率・校正・購入推奨・正式T−12/候補初回remote証明は0。** `formal=false`、`accuracy_improvement_proven=false`、`promotion_allowed=false`。main/Render/Pages/予想原本・結果・既存Cron/既存#1698 0.50/0.25登録・#1693登録母集団は変更なし。


## 2026-11-10 ②担当：既存#1713公式3原本監査→#1710四モードの将来レース受入ゲート

**実装場所**：既存Draft PR #1710の `scenario_future_three_original_gateway.py` + `test_scenario_future_three_original_gateway.py`。新PR/収集者/Cron/採点器を作らず、既存 #1713 `scripts.audit_three_official_t12_originals.audit_three_originals`、既存 #1693 `scenario_official_exhibition_projection.project_exhibition_research` の raw-byte semantic replay callback、固定 #1698 `experimental_conditional_board`、既存 #1710 `evaluate_exhibition_mode_lenses` を連結。**取得済み元原本は不変更、候補のGit遠隔保存・定期起動は未実装**。このゲートは候補の正式証明そのものではない。

### 検証対象とfail closed条件
- 研究対象は**2026-11-11 JST以降に締切を迎える将来レース**に限定。11/9・10の既存研究3レースを登録済み独立600件へ誤算入しない。
- 公式3原本監査器がチェックする**12 component checksすべてTrue**、同一レースの出走表6人とbeforeinfo6人の登録番号一致、展示進入コース→艇番1対1、展示タイム6艇・ST6艇、公式3連単オッズ120、原本SHA、3原本すべてT−12より前に受信、公式締切・cutoff・各受信時刻・余裕秒数の完全一致を検査。元原本にある自己申告受信時刻と研究側raw sourceの受信時刻を相互照合する。候補自己申告生成が原本3つの受信より後かつT−12前であることも検査。
- 要求inputの実際の`source_bundle.originals`3つと、`project_exhibition_research`が既存raw意味再パースと一致させた `source_sha256` を検査し、レース・艇番・登録番号・展示進入が4モード計算へ渡すprojectionと一致しなければ拒否。架空の2コース逃がし率/風向/水面/最終本番進入/モーター率は補完しない。
- synthetic fixture陽性でも `formal=false`, `forecast_usable=false`, `promotion_allowed=false`, `eligible_for_existing_1693_600_races=false`, `eligible_for_new_300_plus_300_races=false`を固定。監査器の独立コードSHA、HTTP真正性、実候補初回遠隔Git受領、シナリオ係数/モード重みの別ID事前凍結は**未達**。発行時刻・結果・出力の偽証を許可しない。合成正例は原本を捏造した成功実測ではない。

### 実原本を再取得して独立リプレイした負例
- [実元ZIP #13749433042（#1713のPR event）](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42786724704/artifacts/13749433042) を別runで再ダウンロードし、SHA256 `7eddf4704635613f7d8cb18a03f07bcc1f9037efafb52ee26a3723b333a30354` / 28件全CRC一致を確認。既存 `audit_three_originals` を**ZIP内の出走表・beforeinfo・オッズ120の原本そのもの**へ再実行。
- **住之江7R `202611101207` と蒲郡8R `202611100708`**：いずれも公式原本SHA・6選手登録照合・オッズ120はOK。しかし `exhibition_six_courses`, `exhibition_times_six`, `start_exhibition_six` が不足。入力完全性は0/2で、今回の`validate_audited_source_pairing`は**2/2厳格拒否**。買い目生成・正式600枠算入は0。
- [修正済み実際のGitHub Actions #42802543098](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42802543098) `completed/success`、コードhead `af0138f9704ea6f067907536289dbec55f8d2867`。[同一head PR安全性CI #42802256345](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42802256345) は先行ゲート実装に対してsuccess（後続docs/headでは再確認）。実run成果物 [#13756018727](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42802543098/artifacts/13756018727) ZIP SHA256 `a19b0c52dd99d4f2b4dfc1fabba49eebb3a974f1057c53537df5a079ae6eb04f`、3件のJSONファイル全てを別途厳格に再parseして正常、ZIP全CRC正常。監査原本に偽のpositivesはなし。
- 最初の実run #42802245137ではモデル・拒否処理は成功したが、新しい負例レポートの末尾を文字列`\\n`として出力したため、ZIP検査時にJSONデコード不備を検出。**GitHubにその結果を成功実績として採用せず**、既存workflowのwrite_textを修正し、書き出したJSONを即再parseするCIチェックを追加。上記 #42802543098 が修正後の成果物。

### 次の担当横断の単一依存
1. ③/#1713・#1694が将来レースの正式な3原本を**同じジョブ**で完全に採り、T−12前の全6艇展示とオッズ120及び実原本SHA/受信時刻/保存runの独立証拠を残す。既存Cron/collectorで行い、今回の②gatewayへ raw bundle + 既存 auditor report を渡す。
2. ②は新候補の既存#1698 exact code SHAと研究シナリオ仮説・モード重みを**別IDで事前凍結**し、source SHA→計算した120ボードSHA→全4モードチケットSHA→初回独立Git遠隔受領を順次監査する。今回のgatewayは source→数理の**研究用構造照合**のみであり、First remote証明/候補発行者の権限確認は未実装。
3. ④/#1693の登録済み独立600枠へ混入しない。別研究として次の将来300+300件を**結果LAST**で採点し、Top1/3/5/10、gain/loss、頭の的中/欠落、Brier/logloss、場別・実進入の欠損、オッズ/ROI可用性を事前に決めて比較。未証明/欠損は外れにも成功にも算入しない。正式0/600、未検証係数の本番利用なし。

**本変更も Draft #1710 のみ。#1713/#1694/#1693/#1698の実装、main/Render/Pages/既存予想・結果原本、本番稼働ジョブ、保存された確定結果を変更していない。**


## 2026-11-10 ②担当：実公式racelistの6艇全国・当地・平均STを4モード研究へ源一致連結

**当日ユーザー指示「進めて」に従った実装範囲**：既存Draft PR #1710のみ。既存#1713の出走表原文監査・公式3原本監査、既存#1693原文意味replay、既存#1698固定条件付き数理、#1710の研究4モード計算を再利用し、元コード/既存候補を変更しない。公式出走表国別勝率が旧V2 CSVや中立5.0の借用に依存していた不足を解消する**同レース原文依存ゲート**を実装。

### 追加した実装
1. `scenario_official_racelist_rates.py`：既存`scripts.inspect_official_racelist_registrations.ROW`と`inspect_six_registrations`をそのまま使う。公式出走表XHTML内の「**全国／当地／モーター／ボート**」ヘッダー順・1〜6号艇の4行結合選手行・登録番号・平均STと全国/当地各3数値の列を検証し、6艇の全国勝率/全国2連率/全国3連率、当地勝率/2連率/3連率、平均STを原文から抽出。クラス/列順変更、ヘッダー欠損重複、登録番号不一致、6艇未満、非有限・範囲外数値、推測補完を拒否。外部依存なし・HTTP取得なし。場別の公式情報が欠ける場合にデフォルト値で埋めない。
2. `scenario_future_three_original_gateway.run_future_triple_experiment`：既存#1693 raw semantic replayer→既存#1713三原本監査結果を照合した**後に**、同じ原本SHAに一致する`racelist`生バイトから6全国勝率を再抽出。借用した旧V2勝率・全艇5.0・異なるレースの国別勝率・6登録番号対応不一致なら計算前に`ValueError`で拒否。元の研究`evaluate_exhibition_mode_lenses`へは検証済みの原文抽出勝率そのものを渡す。平均STと当地勝率はレコードに残すが、**モデル計算にはまだ使わない**（別研究の校正が必要）。
3. 出力に`model_input_content_sha256_research_only`、`four_mode_ranked_output_content_sha256_research_only`を追加。同一レース原本3SHA・正規化source/展示vector SHA・6全国勝率・未校正展開係数/モード重み・候補自己申告生成時刻・4モード券順位/確率/120票盤面SHAを**canonical JSON**で連結。入力と重みを固定した再計算は同じSHA、重みを変えると両SHAが変わることを本物の固定#1698コードを使用して試験。**独立Git first remote receiptの証拠ではない**。証拠/候補正式認定は常時false。

### 既存実原本を使用した陽性パーサ検証（新候補/正式予想ではない）
- [既存#1713実ZIP artifact #13749433042](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42786724704/artifacts/13749433042)、ZIP原本 SHA256 `7eddf4704635613f7d8cb18a03f07bcc1f9037efafb52ee26a3723b333a30354`。原文SHA/登録番号/120オッズを既存3原本監査で再検証してから、**本当の公式racelist HTMLだけ**に新パーサを適用。
- **蒲郡8R `202611100708`**：1〜6号艇の全国勝率 `[6.77, 5.65, 3.16, 6.76, 6.48, 2.65]`。**住之江7R `202611101207`**：`[7.19, 6.83, 6.87, 7.24, 7.03, 6.99]`。12艇の公式出走表登録番号と既存監査の登録番号を**12/12一致**、当地勝率と平均STも6艇×2レースを抽出。
- ただし両レースの`beforeinfo`には展示タイム/展示進入/ST6艇が未完成。既存3原本監査が不足、②将来計算gatewayは引き続き**2/2拒否**（新4モード候補0）。一部の公式値を読めたことを将来のT−12三原本認定・モデル性能改善と混同しない。
- [実HTTP原文・SHA/CRC/値照合GitHub Actions #42804552216](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42804552216) **completed/success**。生成成果物 [artifact #13758211017](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42804552216/artifacts/13758211017) ZIP SHA256 `799bff25144b663a8bcd3a22436aff10fbd34757b90e0d3cdfae3575c046e06b`（GitHub広告digestと独立ダウンロードSHA一致、全CRC正常、**3件JSON厳格parse成功**）。
- [最新の#1710 PR安全+固定#1698数理連結回帰 #42804851328](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42804851328) **completed/success**、実行head `aa2542803c215416cf19e1b6f3fb050c7f890a95`。旧数理条件・結果原本・本番モデル・収集Cronは不変更。

### 正式予想へ進めるための残りゲート
- #1713 / #1694 が別の将来レースで公式racelist＋beforeinfo展示6艇/ST6艇＋オッズ120の**同レースT−12完備**と独立source/初回Git受領を実証すること。新#1710 gatewayでsource→rate→exhibition→確率盤面→全モード券を計算できる構造は準備済みだが、**実際に完備した将来レースをまだ通したわけではない**。
- ②側の`3.5`頭log-shiftとモード別重みはあくまで**人手の未校正研究仮説**。今の3レースの結果を見た後に重みを調整しない。別研究ID・採用モデル/係数/コードSHAを将来検証開始より前に登録する必要あり。
- 新候補の初回Git遠隔保存、全起動run証拠、厳密な結果LASTと既存/別研究300+300、Top5/10非悪化、確率校正、70%候補の実際の将来結果との照合は未成立。**formal0/600、本番採用0**。#1693既存凍結プロトコル・#1698旧候補のfirst_remote/0.50/0.25は不変。研究CIと本番予想は別物。


## 2026-11-10 ②担当：最新main収集実行実績と研究候補ローカル不変化（遠隔未保存）

**事実確認（GitHub実行原本）**
- main `f29453d24d2dbb9dea2af52f99df8f3534ec34f7` 時点で実行された [4モード収集Actions #42807090850](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42807090850) 成果物 [#13757594714](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42807090850/artifacts/13757594714) を再ダウンロードし、ZIP全16ファイルのCRC正常。内部 `four_mode_forecasts/capture_status.json` は当日既存保存 **150**、`last_run_new_count=0`、`cutoff_skipped=6`、対象出走表156、`production_success_proven=false`。`four-mode-evidence/stages.json` は`publication=no_eligible_candidates`。`source-links.json` は `checked=0, hashes_present=0, remote_first_seen_verified=false`。**研究予想150件が公式展示6艇/ST6艇・オッズ120の正式T−12原文を消費したとは解釈しない**。新たにGit候補を初回受領した証拠0。
- PR #1710は調査開始時 `mergeable=true` へ変化（GitHubの動的判定であり、将来の統合を約束しない）。**研究Draftのため強制merge禁止**。旧#1693/#1698の正式登録母集団および本番のモデル/収集者に変更なし。

**実装（既存#1710 Draftのみ、既存#1698のremote observer/write-onceの理念に合わせ新収集者は追加しない）**
- `scenario_future_local_candidate_handoff.py` ＋ `test_scenario_future_local_candidate_handoff.py` を追加。既存`scenario_future_three_original_gateway.run_future_triple_experiment`が同一レースの公式3原本の構造監査、6艇公式出走表勝率、全6艇展示/STとT−12前原本、#1698固定数理と#1710凍結仮説の全4モード計算を実行済みの**研究レポート**を入力とする。
- [GitHub事前登録commit #947f9d6f](https://github.com/ikst2512-eng/boat-edge-clean/commit/947f9d6fe213f01f68ae0efd9c2c71b0a50e56ac) の別研究manifestと未校正世界係数/4モード重み/モデルSHAを照合。先頭艇3.5とゼロ対照や標本300+300の境界は変更禁止。6艇勝率、source→board/券のハッシュ、順位と点数5/10/16/22、全4モードTop1、結果混入、シナリオ係数変更、ギットハッシュ失敗、締切/日付逸脱を拒否。候補は可逆的なcanonical JSONバイトと SHA256/Git blob SHA1を生成するが**GitHubへ一切書き込まない**。ローカルfreeze時刻は自己申告・source受信後・T−12の60秒以上前。自己申告を初回遠隔受領と詐称しない。
- 初回 [CI #42808629529](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42808629529) ではプロトコルの0/1と実モデルPythonの0.0/1.0による**数値が同じでもJSONハッシュが異なる不具合**を検出。2026-11-10事前登録済みmanifestを改変せず、handoff側でPythonモデルの数値の型へ重みを正規化する修正を実施。
- [修正後のPR Actions #42808817155](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42808817155) **completed/success**、通常単体テスト82本（固定#1698依存1本skip）＋**固定#1698の実コードで4モード生成を含む34本成功**。synthetic未来レースの同一入力/時刻→同じ候補bytes SHA、重み変更・後付けレース・欠損/違法/重複券・結果漏えい・時計逸脱・遠隔受領偽装の拒否を確認。**これは人工原本であり正式予想ではない**。

**残る依存**：③/#1713の同一将来レース公式3原本T−12全項目の実初回受領が先。次に②候補を**create-onlyの研究専用Git受領先**へ、コードSHA/時刻/衝突規則を保ったまま受け渡す（既存#1698の保存方法を再利用、二重Cron・本番保存への書込みをしない）。別系統の認証済みGitHub API初回受領と全Actions run台帳を独立監査しなければ、formal0/600、評価や本番採用なし。今の候補生成機能は出力規則の**準備・synthetic検証のみ**であり、実際の原本から新候補0件。


## 2026-11-10 ②実原本6レースのT−12公開タイミング監査（研究単発Actionsで検証）

【ユーザーの「進めて」対応。新Cron・新PR・新データ取得器・予想原本や結果の変更なし】前回の未完備公式3原本を補完して採点したのではない。**実際の3つの既存GitHub Actions ZIPを別runでSHA固定再取得**し、beforeinfo+3連単120オッズ（6件）、racelist（うち2件）の元原文・manifestで締切とsource受領JST、展示ST6艇件数を再計算した。

- [検査実行GitHub Actions #42810300028](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42810300028)：`completed/success`、head `de396ccd585c47eaf39673ded607f6cb3819516b`。
- [検証ZIP artifact #13761308309](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42810300028/artifacts/13761308309)、ZIP SHA256 `53739a4a35c365e19984a0bc4058f8c25f6565c96e48d82a2d99d982b1319fea`。GitHub広告digestと独立ダウンロードが一致、ZIP全CRC正常。内4つのJSON成果物を全てstrict `json.loads` に通した。新規 `research-real-six-source-T12-timing.json` に6レース×締切／T−12／beforeinfo受領自己申告／オッズ受領自己申告／展示6件／第三原本有無が揃う。
- 原ソース ZIPとSHA：11/9 `13652131213` / `99f02ff3…`、11/10前半 `13740574410` / `cdfdeae5…`、11/10後半 `13749433042` / `7eddf470…`。元source SHAを新しいforecastや結果と称して再保存しない。

| 実レース | beforeinfo受領がT−12より何分早いか | ST6艇 | 同一ZIPにracelist原文 |
| --- | ---: | --- | --- |
| `202611091110` びわこ10R | 3.16分 | **6/6** | × |
| `202611091710` 宮島10R | 1.45分 | **6/6** | × |
| `202611101202` 住之江2R | 2.09分 | **6/6** | × |
| `202611102211` 福岡11R | 7.75分 | **0/6** | × |
| `202611101207` 住之江7R | 2.94分 | **0/6** | ○ |
| `202611100708` 蒲郡8R | 12.44分 | **0/6** | ○ |

**観測**：T−12基準の4分以内に受領した4例は3/4が展示ST6艇、7分以上早い2例は0/2。同じ2.94分前でも欠測があり、事例は偏りがあるため「4分以内なら必ず揃う」や「早期受領が欠測の唯一原因」と断定しない。展示STの実公開がその時点で未完了の場合は、T−12前の候補へ補間・後付けすることを禁止。6件中**公式racelist+beforeinfo ST6艇+odds120が同一受信セットで全部揃ったレース=0**（前半は出走表原本なし、後半はSTなし）。出走表・オッズだけの正式結果採点なし。これは研究の入力可用性診断で、**independent FIRST Git receipt 0、formal=0/600、production=不変更**。

**③への短期是正点**：既存の**単一T−12収集ワークフロー**で、締切時刻に対してbeforeinfoがどの時刻に6件揃ったかを、collector-run ID・原文SHA・受領時刻・T−12 marginで記録する。出走表は古い時刻でも良いかを公式源/選手番号更新の性質で吟味する一方、展示STは実公開時刻が必要。早い段階で取得した0/6を同レースのT−12完備と誤認しない。「予想生成13:21 JSTの旧原本を20時台にGit初追加した事実」をT−12の新規直前情報取得と混同しない。完全例が出るまでは既存#1710の`scenario_future_three_original_gateway`がfail closedのまま。翌11/11 08時台の実Cronと初回Git受領はまだ監査未完了であり、完了の先取りをしない。


## 2026-11-10 ②実測：全6原本の欠落原因を排他的分類し、T−12／展示後の判定を分離

### 今回の実行証拠
- 新たなスクレイパ・Cron・候補・研究IDを作らず、既存 `.github/workflows/scenario-official-pair-real-inject-once.yml` に**全6レースの観測原本の欠落理由を排他的に集計する断言**を追加。原本に無いSTを0埋め/後からT−12入力へ移送せず、実 source ZIP（artifact `13652131213/13740574410/13749433042`）の固定SHA照合を継続。
- [実GitHub Actions #42811768897](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42811768897) **completed/success**、commit `3722742780a2a280ba1b9bb715391087147d3ec0`。成果物 [#13763050282](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42811768897/artifacts/13763050282)、ZIP SHA256 `31f0f99204ef0cb60c18ca6504723d25eaedfb764fe0e4c55b657fa95f29fa5a`。GitHub digestと別ダウンロードSHA一致、ZIP CRC OK、4 JSON全件parse成功。レース別 source-state は `research-real-six-source-T12-timing.json`。
- **6/6全サンプルを分類し、成功レースだけ抜き出していない**：
  - `MISSING_RACELIST`（ST6艇あり/出走表原文なし）**3件**：`202611091110`、`202611091710`、`202611101202`。
  - `MISSING_ST6`（出走表原文あり/ST6艇なし）**2件**：`202611100708`、`202611101207`。
  - `MISSING_RACELIST_AND_ST6` **1件**：`202611102211`。
  - `COMPLETE_3_ORIGINALS` **0件**。これらを正式的中/不的中や成績向上に算入しない。
- **注意**：source原本にST6艇が記録されていない理由は、公式側未公開・取得タイミング・API応答差・収集実装側の欠測のどれか未確定。記録がない事実だけで「公式未公開」と断定しない。beforeinfo 受領時刻も収集者自己申告、GitHubの**初回独立remote受付証明ではない**。

### 次の評価ゲート：同一レースで混ぜない2つの時点
- **T−12基準の早期予想**：この時点までに実際に保存・受領証明された公式原本でのみ候補を固定する。ST6艇が欠測なら、**ST依存の#1710候補は不適格**。STが後に公開されてもT−12の空欄を補完しない。既存#1693の凍結旧母集団・採点器とは混ぜない。
- **展示公開後の直前研究**：T−12後に6艇展示/STが揃ったなら、同じレースでも**異なる情報時点の新規研究**として扱う。既存の `research-live-preview-evidence` / T−2研究経路を収集責任者③が運用し、別の研究ID・事前登録・独立初回Git受領・T−2截止前のsource clockがそろうまでは**形式的な的中率評価はしない**。既存11/10凍結 `EXPLORATORY_ONLY_FUTURE_TRIPLE_SCENARIO_RESEARCH` の600枠へ遅延入力を混入しない。新しいCronや2重収集者は作らない。
- **受入れ/母集団の定義**：①全attempt（schedule/dispatch/watchdog/欠落）をレース×対象時点別に台帳化、②同一レース公式racelist 6選手+beforeinfo ST6+odds120の原文SHA/受領JSTと候補自己申告時計、③独立 Git first-add（create-only）とGitHub上の初回受領時刻、④結果LASTで既存 paired Top1/3/5/10 を判定。**eligible/全対象レース・ST欠測割合・場所別/時間帯別欠測率**を結果と同時に報告し、完備したレースだけの選択バイアスを可視化する。未取得を当たり/外れに算入しない。
- [実研究プレビュー #42810989409](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42810989409) は成功だが、保存した `collection_summary.json`・`batch_report.json`・`late_research_archive_report.json`・`late_research_topn_report.json` を直接確認すると、**新規原本/候補0件、paired0件**。ジョブ成功＝実候補保存ではない。
- [既存本番の独立予想証拠監査 #42808744551](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42808744551) は失敗扱いで正しい。既存V2原本724件のうち613件はローカル証跡チェック通過、111件は`first_commit_same_second_unverified`で拒否、**全件の独立 Git first remote 受領は別未証明**。この613件を#1710の新研究600へ加算しない。

**結論**：GitHub上の今回の改善は「全6件の実ソース欠落の排他的分類と正式採点拒否の証拠を保存」したもので、公式3原本の新取得/候補の初回Git遠隔保存/実測精度改善は依然0。#1710 Draft、既存モデル・原本・main/Pages/Render・所有者③のCronは変更していない。


## 2026-11-10 ②担当：実着順を結果LASTで読んだ3レースの探索的TopN比較（本命モードの後退）

### 何を本当に実行したか
- **同じ既存Draft #1710の単発ワークフロー内**で、歴史的V2の各モード5/10/16/22票と既存#1710未校正head log-shift=3.5／head=0対照のフル順位を、**一切結果を読まずに**`research-archived-rates-vs-neutral.json`として先に生成。数理`scenario_mode_specific_exhibition_end_to_end.py`・固定#1698`experimental_conditional_board`・11/10事前登録manifestの3.5/モード重み等の数値は**変更しない**。
- すべての研究盤面と券を生成した**後の別LAST STEPだけ**で、凍結main `8a674590d645a693dbd9f6fe7f79e8829b878452`から3件の実確定着順ファイルを`git show`・Git blob SHA一致を確認して取得し、同じ3レース/同じ点数のTop1/3/5/10包含の**参考記述統計**を作成。古い研究を意図的に正式prospectiveとして採点せず、結果は`research-historical-three-race-result-last-DESCRIPTIVE.json`へ隔離。候補ソースに着順を与えず、結果で仮説/重みを学習・変更しない。
- [実GitHub Actions #42813358925](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42813358925) `completed/success`、head `44b1f91dd3c80e22204c66e2f4103056c68a5ce2`。結果 [artifact #13763551778](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42813358925/artifacts/13763551778) ZIP SHA256 `284b46ab4371036969d32fa55d5e6d36449169d4780ff391729b3e3bc5983ab8`、GitHub digestと独立ダウンロードSHA一致、全CRC正常、**5 JSON全件strict parse成功**。3件は`202611091110` 着順1-2-5、`202611091710` 着順3-4-2、`202611101202` 着順1-2-6。実際の結果原本は`confirmed_results/`の公開済みBoatraceCSV取得データで、公式による裁定時刻の証明とは異なる。

### 歴史的3Rの参考TopN実測（各モードで3件が分母）
| Mode | 比較TopN | 旧V2保存票 | 未校正head log-shift 3.5 | head shift 0対照 |
| --- | --- | ---: | ---: | ---: |
| 絞り 5票 | Top5 | **1/3** | 1/3 | 1/3 |
| 本命 10票 | Top5 | **1/3** | **0/3** | 1/3 |
| 本命 10票 | Top10 | **2/3** | **0/3** | 1/3 |
| バランス 16票 | Top10 | **2/3** | 1/3 | 1/3 |
| 穴 22票 | Top10 | 0/3 | **1/3** | 0/3 |

- 4モードともTop1とTop3は、旧V2/head3.5/head0の**全3R×各モードで的中0**。絞り5票のTop10は**対象外**であり5票を「Top10的中」と表現しない。
- びわこ10Rの1-2-5、住之江2Rの1-2-6は、保存済み旧V2の**本命Top10に含まれた**が、未校正のhead3.5候補本命Top10からは外れた。穴の宮島10Rの3-4-2は逆に未校正head3.5の穴Top10で拾えた。現行3レースでは**モード間に勝ち/負け混在し、本命・バランスの既存V2に対する非悪化要件を満たしたとは言えない**。
- **最重要の制約**：#1710の新仮説は事後的に構想・計算した研究であり、これら3レースの締切前に新モデルをGitHubへ発行したわけではない。全国勝率は当時保存済V2由来で、同レース公式racelistの真正原文がそろっていない。統計のn=3は極小で選択した古い事例に過ぎず、一般化可能な的中率の推定、確率校正、原因の確定、利益/ROI、採用判定には使えない。**本物の独立将来600件のうち認定0件**、`formal=false`、`promotion_allowed=false`、本番main/予想原本/結果/cronを不変更。
- 次は**研究条件を後付け変更せず**、#1713/#1694から将来の公式T−12/展示ST6が完備した実レースと独立候補first remote証拠を受け、別研究IDの300+独立300を準備。今回の歴史的3Rは将来確認母集団へ一切入れない。別のT−2展示後予想はさらに別ID・情報時点で前登録するまで比較しない。


## 2026-11-10 ②担当：事前登録protocolと実行コードの共謀差替え拒否＋絞りTop10不適用の固定

**調査で見つけた実装上の欠陥**：将来研究の`scenario_future_local_candidate_handoff.prepare_local_candidate`は、呼出者が`registered_protocol`内の`scenario_hypotheses`と一緒に`gateway.hypothesis_signature_sha256`を計算し直せば一致検査を通過できた。メソッドSHAの値もリスト長10と16進形式しか見ておらず、実ファイル内容と改ざんされたSHAを直接照合していなかった。これは**結果を見てから係数・モデルコードを変えても研究と誤って受理される危険性**がある。実際に偽証された予想が遠隔保存された証拠はない。

### 対策（既存Draft #1710内。事前登録済み研究条件そのものは変更禁止）
1. 凍結済み研究manifest `research/four_mode_triple_source_forward_protocol_20261110.json`の**事前Git blob SHA1 `bf60d2879065d1f9ecbd6b442db17fcb8fbcb8b7`**を実行時に直接再計算。任意の呼出し辞書は実原本のJSONと完全一致させ、改ざん/NaN/重複key/別ファイルを拒否。
2. 研究コード10ファイルの実バイトからGit blob SHA1をその場で計算し、原本manifestの各記録SHAと完全一致しなければ**候補をローカル生成しない**。試験ではprotocolとgatewayのハッシュを共謀差し替えしたケース、保存manifestを置き換えたケース、実行コード1ファイルだけを変更したケースを隔離temp checkoutで再現して拒否。モデルのhead3.5/世界重み/登録年月日や候補原本は**一切調整・上書きしない**。
3. 別研究の`scientific_protocol.primary_endpoint`を`paired_top1_exact_trifecta_by_mode_with_multiplicity_correction`として照合。絞り5票のTop10は**厳密にN/A（不適用）**と結果ブラインドのcandidate payloadへ記録。#1693既存スコアラーがTop10を予算点数に切り詰めて表示するのは当時の旧数理参考実装であり、新研究の10券Top10へ**誤って読み替えない**。hit/balance/holeのTop10のみ適用、Top5/Top10非悪化は将来の同一レース比較でしか判定しない。

### 実行済みの安全検証
- [GitHub CI #42816571420](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42816571420)：protocol/モデルハッシュ実照合＋共謀差替え等の**追加回帰成功**（head `a9d50b4d247bd22ff6526f4401eb4638256d7af4`）。
- [GitHub CI #42816963410](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42816963410)：head `1ac82df5095cdc380288a4042cf700d03d730fd2`。研究単体テスト**85本（依存1skip）**、固定#1698条件付き数理を動かした統合テスト**34本すべてPASS**。絞りTop10 N/A/本研究Top1 primaryを出力契約とテストに固定。
- 本件の`local_handoff`は**未接続の研究専用create-only受け渡し準備**。候補初回GitHub遠隔保存、公式T−12三原本/ST6艇同時完備、Git初回受付時刻の独立受信、全attempt観測、300＋独立300件の成立を偽証・代用しない。**formal=0/600、model改善未実証**。未校正head3.5が過去3Rで本命Top10 旧V2 2/3→研究0/3となった事実は消さず、見た後で係数を変更しない。#1710 Draftのみ、main/Render/Pages/旧#1693 600/既存#1698候補/公式原本・確定結果は不変更。


## 2026-11-10 ②担当：旧#1698 create-only研究候補の受け渡しを#1710へ接続（模擬遠隔のみ）

**ユーザー継続指示で行った具体的な実装**：既存Draft PR #1710 の`scenario_future_local_candidate_handoff.py`に`publish_local_candidate_write_once`を追加。旧#1698 `position_sensitive_append_only_research.publish_write_once`の**既存の安全な実行契約**（受け渡し元とbyte単位一致・create-only・同一原本再利用・競合時書換え拒否・読み戻し一致・遅延は失敗・結果read無し）を、別研究#1710の凍結候補へ適用した。元の#1698と#1693の研究用コード/母集団は**一切変更なし**、新規Cron/collector/本番アダプタは作らず、研究用副作用は呼出側が明示注入した処理のみ。作成した新しいGitHubブランチは**0**で、候補実リモート保存も**0**。

- 追加した固定 branch `scenario-four-mode-triple-source-evidence-ledger` は**今後の別途審査用の名称指定だけであり、GitHub上で作成済みと主張しない**。既存main、master、旧#1698の`position-sensitive-forward-evidence-ledger`、その他ブランチへ誤保存しようとすれば、**最初のremote callbackを呼ぶ前**に拒否。
- 実行時、11/10事前登録Git blob SHA原文＋研究用モデル10 blob SHAの検査、および将来公式3原本→6登録番号→全国6勝率→展示ST6艇→固定4モード票の計算済み`gateway`から、候補の**完全な同一JSONバイト**を再生成して`prepared`の内容一致を検証。偽のローカル候補・終了後の改変を弾く。
- `clock()`は明示注入のaware JST。研究候補生成後で、T−12の30秒以上前の時刻でなければremote read/createを**開始しない**。研究専用`remote_read(branch,path)`→（未保存なら）`remote_create(branch,path,exact_bytes)`→`remote_read`を要求。同じバイトの再試行は新規writeしないが、異なる既存候補は`research_immutable_candidate_collision`で拒否。readbackのバイト不一致、readback後のT−12超過も拒否し、成功と誤記しない。
- 成功戻り値の`status`は`create_only_storage_call_returned_unattested`あるいは`identical_candidate_already_present_unattested`で、**independent first remote Git receipt、書込アダプタ真正性、Git first-add履歴、公式原本HTTP真正性、全Actions起動、正式600算入、精度改善・本番採用をすべてfalse**とする。注入callbackが偽の場合は**ローカルテストしか保証しない**。
- [GitHub Actions PR回帰 #42819481249](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42819481249) **completed/success**、commit `db9a4fbd8b204995dad0d8681c2b4b58ee397ccf`。既存テスト群＋新たに`test_scenario_future_local_candidate_handoff.py`で模擬メモリ遠隔を使い、正常初回保存・同一再実行でwrite数1・main/別研究ブランチ拒否・候補バイト改変拒否・早すぎる/遅い時計拒否・異なる原本の上書き拒否・readback破損・並行create時競合・readback後cutoff超過を再現。テストは成功するが、**本物のGitHubへの保存・独立受領証明ではない**。

### 同日夜の最新収集実測（モデルの保存成功とは別）
- 2026-11-10 21:52 JSTの[既存プレビューschedule run #42819433184](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42819433184)は成功。[成果物 #13765184593](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42819433184/artifacts/13765184593) のZIP SHA256 `a8e94fa23d9af82114b18463b01622724cb6f7ae977413c8116822880e021b68`はGitHub digestと独立再ダウンロードSHA一致・CRC正常・内部2 JSON parse成功。既存CSVの全日`156`行には**後から**stt 155/156、tkz 154/156に6艇項目が揃っている一方、**取得時刻21:52に当日156レースすべて締切済み**であり、T−2/T−12前として**新規保存0件・valid paired0件**。これは`STが後から揃う`ことの参考証拠にはなり得るが、**締切前に保存できた証拠には絶対にしない**。同日現在の他runの証拠を先取りしない。

**次の明確な実行依存**：③/#1713・#1694の研究用単一収集経路が、同一将来レースについて公式racelist/beforeinfo ST6/odds120をT−12前に保存して初回遠隔受領を出したら、②の研究用入力を#1710 `run_future_triple_experiment`→`prepare_local_candidate`→本create-onlyアダプタへ渡す。ただしCIの固定model10 SHAが実コードと一致し、実際のGitHub**初回受信サーバ時計**、Git first-add系譜、完全Actions attempt台帳を別途独立検証しない限り**研究の正式0/600・モデル未採用は変えない**。本番予想への研究Draft強制統合、過去原本の後付け上書きなし。
