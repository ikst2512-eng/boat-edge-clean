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

**New separate `scenario_mode_specific_lens_research.py`:** imports the EXISTING `compose_scenario_research` four times instead of copying its 120-board mixing math. It requires a *separate explicitly supplied normalized scenario-weight dictionary* for each of `narrow`, `hit`, `balance`, `hole`. A mode's rankings come only from **its own explicitly evidence-supported scenario mixture** (e.g., narrow strongly supported escape, another mode genuinely supported two-sashi/third attack); the existing unchanged `rank_modes` still sets that mode's ticket budget at 5/10/16/22. The research output reports within-race Top1 and ticket overlap. **It does not subtract tickets already used by another mode, penalize duplicate Top1, invent a distinct scenario, use odds as proof or mandate a difference.** If mode weights/boards match, narrow remains nested inside hit and that is acceptable. If hypothetical race scenarios genuinely change the relative probabilities, Top1 and ticket sets can differ.

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
3. This new wrapper runs that same math once per mode, with the **identical scenario head hypotheses and identical 2/3-place coefficients across all modes**, allowing only a different **explicit, fully named scenario-weight dictionary** for each of `narrow`, `hit`, `balance`, `hole`. Before accepting results, it checks every scenario's 120-board digest is identical across modes. Different boards within one scenario would be an **error**, not a way to hide diversification.
4. Each mode's **own** normalized scenario mixture is handed to the existing `rank_modes`, selecting exactly its original 5, 10, 16 or 22 tickets; cross-mode overlap is an independent reported diagnostic, not a selection constraint. The adapter never edits current archived forecasts or `main`.

**Real independent GitHub CI executed pinned #1698 code from SHA** `e152b57033f825e02343b004a9c013a8998f9954`, exact verified Git blob `0019978a4e27a1235d0b466c11f514bd7105f261`. In an expressly **SYNTHETIC** source fixture with supplied escape/two-sashi/third-attack/outer-benefit scenario weights, the resulting four-mode Top1 included **3 distinct tickets**, not four; this is correct behavior, because a genuine overlap must remain permitted. All 4 mode budgets, full 120 boards, preserved source fingerprint, ST feature sensitivity, bad digest, missing mode, nonnormalized weights, illegal outcome injection and fake formal/head-mass claims are tested. When all four mode weights are identical, narrow's top5 remains nested in hit's top10: **no artificial mode disjointness**.

Final standalone+integration CI: [#42784923721](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42784923721) **SUCCESS, 38 existing research unit tests + 21 pinned #1698 integration tests**. The first attempt [#42784767405](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42784767405) failed because a test incorrectly **required four distinct Top1** instead of accepting observed 3; the false uniqueness requirement was removed, not a change to model coefficients.

**LIMITATIONS (blocking live rollout):** The head shifts, conditional coefficients and separate per-mode scenario weights in tests are **unregistered, hypothetical and not fit to official past-only training with a prospective future holdout**. The pipeline can consume structurally checked six exhibition ST/time, but no independent same-race official beforeinfo+racelist+odds120 T−12 first original receipt, actual-source model lineage, independent *first Git remote forecast receipt*, verified entry/wind/wave/motor/wall/tide or fresh 300+300 Top1/3/5/10 outcome improvement has been demonstrated. The test fixture's hashes can be recomputed by the caller: this is **not** source authentication. No betting probability calibration, performance claim, or permission to use on the live website. It does not and cannot solve the site overlap until reviewed, independently validated forecasting weights are deployed after the display recovery. **No forced diversity, main auto-merge, source rewrite, live deployment or current predictor change.**
