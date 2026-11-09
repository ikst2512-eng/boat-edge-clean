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
