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

## 2026-11-08 20:24 JST: independent exact-paired statistical screen + input coverage

**Exact-head research CI** [#42475577778](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42475577778) **SUCCESS**, with **39/39 tests** and old saved Nov-08 V2 predictions reproduced **116/116**, 0 excluded. The registered frozen selector and its dependencies were verified unchanged.

### Distinguish observed net difference from statistical evidence

New independent `position_sensitive_paired_inference.py` consumes the existing reference-only paired aggregate and the already independent structural guard. Only if **all 600 original slots have outcomes** (pilot 300 and confirmation 300) will it run an **exploratory** one-sided exact McNemar/sign-tail test on paired gained/lost outcomes for confirmation Top1 across all four modes (Holm family correction), and separately Top5/Top10 across **seven applicable mode×TopK comparisons** (Holm correction; narrow Top10 is N/A, not a ten-ticket result). There is no outcome access, network access, collection or candidate revision in this diagnostic.

This tests a **superiority** signal, *not statistical non-inferiority*. A positive/zero observed delta **does not** demonstrate that Top5/10 cannot be worse; lack of significance is **inconclusive**. Even extreme favorable synthetic 300+300 test counters leave `formal=false`, `promotion_allowed=false`, `model_improvement_proven=false`. The analysis code adds no confirmatory statistical specification to the frozen forward protocol, and **cannot** verify between-race independence, T−12 candidate first-remote publication, complete workflow inventory, official six/120, payout provenance or authenticated official results. Formal promotion remains blocked. The Top1/Top5/Top10 synthetic counterexamples and negative tests are unit fixtures, not observed racing performance.

### What actually exists in original Nov-08 archived V2 inputs

Independent read-only `position_sensitive_feature_inventory.py` authenticated **same archived original model board reproduction** before inventory. Its count reports top-level structured field **presence only** (not authenticity or official T−12 completeness).

| Field recorded in the original 116 archived forecasts | Original records with field |
| --- | ---: |
| Six national win rates | 116/116 |
| Public title/race-card source SHA-256 digests | 116/116 |
| Structured official beforeinfo object | 0/116 |
| Structured six-boat exhibition board | 0/116 |
| Structured actual entry, motor and exhibition-ST six-vectors | 0/116 each |
| Structured wind or wave height | 0/116 each |
| Structured 120-odds board | 0/116 |

These are **top-level archive schema presence** counts; source data might exist elsewhere in independently maintained collection services, but this Draft has not authenticated or used it. Even a structured nonempty value would not prove official source, clock or identity. The frozen shadow continues to consume **only six national win rates**, and the unchanged research model preserves first-boat probability mass. The requested actual entry, exhibition, ST, motor, wall, wind and venue-specific effects require **a later separately registered hypothesis** with independently verifiable complete pre-result feature receipts; do not retrofit into the existing frozen candidate or step into #1692/#1693/official T−12 collector ownership.

**Decision now:** structural repetition exposed and ticket turnover measured; true paired future precision, statistical non-inferiority, official feature eligibility and ROI **unproven**. No main/Render/live/UI/archive/collector change; Draft/manual approval only.

## 2026-11-08 20:36 JST — future candidate receipt readiness, no publication

**Exact-head CI** [#42476481806](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42476481806) **SUCCESS**: **52/52** research-only unit/negative tests, 116/116 saved original V2 input replays, no exclusions, and unchanged registered selector/model SHA checks. This is **not** a live forward cohort. All outputs explicitly block formal/proven/adoption.

### Distinguish candidate's remote existence from its FIRST remote receipt

Existing main `four_mode_github_server_observation.py` reads GitHub Contents API and authenticates a server `Date` against the *original* main forecast, but that observation explicitly disclaims first-receipt proof and does not publish or remotely observe the **position-sensitive candidate**. Never borrow original Git first-add or observer status as candidate provenance.

New isolated `position_sensitive_receipt_intake.py` **does not make any HTTP calls**, collect a candidate, schedule a job, commit, publish or read confirmed results. It offers a future evidence consistency *preflight* for caller-supplied exact original and frozen candidate bytes:
- Replay the exact frozen selector and prove all original/candidate same-race tickets, protocol SHA, source SHA-256, deadlines and **local** pre-T−12 chronology still agree.
- Require separately supplied **HTTP 200** GitHub Contents payloads, matching canonical exact bytes, Git blob SHA-1, repository and research-only candidate path, uncached response and parseable UTC GitHub `Date` within strict original/candidate windows. Fail closed for 403, 404, timeout-status, cached or mismatched/late bytes, forged path and post-cutoff/same-second date.
- Even two seemingly valid supplied HTTP observations always produce **`observations_are_externally_authenticated=false`**, **`first_remote_candidate_receipt_verified=false`**, **`formal=false`**, **`promotion_allowed=false`**. Supplied JSON and response dates are not an independently authenticated remote first-receipt; a Contents GET can at most attest existence at an independently verified observation time. No actual candidate remote observation was supplied or generated.
- `position_sensitive_research/<race>.json` is a **proposed hypothetical research-only candidate storage path** for testing, not an actual ledger branch or a claim that an archive exists. An independent future publisher would require distinct advance review and must be kept off main/live capture.

### Nov-08 original timing feasibility (retrospective, input-only)

New `position_sensitive_t12_window_audit.py` recomputes the original exact V2 forecast boards from six stored national rates and checks their *recorded* received/generation/deadline chronology before measuring: `deadline - 12 minutes - original.generated_at_jst`. **116/116** original Nov-08 records passed; **0** excluded, **0** locally generated at/after T−12. All **116/116** had more than **90 seconds of theoretical time** between recorded original generation and T−12. Window distribution:
- minimum **827.6 seconds** (13m47.6s);
- p25 **6,887.7 seconds**;
- median **13,907.6 seconds** (3h51m47.6s);
- p75 **20,747.4 seconds**;
- maximum **36,947.5 seconds**.

Those figures are **not** production capture durations, evidence of Git first-add, or verified independent remote publication. They only show that if a separately approved research candidate publication had occurred promptly after original generation on that historical day, its time window might have permitted a pre-T−12 observation. **Nov 8 is a development-only sample and is forbidden as the Nov 9 onward pilot/confirmation cohort.**

### Remaining independent evidence to unlock real comparison

A candidate-specific **append-only, independently observed remote receipt** must actually be generated **before T−12**, and cross-checked against the exact original first-add, all scheduled and rescue runs, the immutable candidate blob, official beforeinfo/exhibition six and 120 odds, and after-finish independent results. Even then this Draft's test harness cannot itself confer formal approval. The 300+300 candidate cohort remains **0**, Top1/3/5/10 future gains and losses **unmeasured**, and statistical non-inferiority **unproven**. The active capture/official T−12 workers own collection, while #1698 is limited to receipt intake and second/third-place candidate evaluation.

**Safety boundary:** No main merge, auto-merge, Render/UI change, workflow-dispatch of production collectors, live schedule change, original overwrite or cross-PR model substitution.

## 2026-11-08 20:45 JST — create-only candidate ledger contract, NOT activated

Added `position_sensitive_append_only_research.py` and its synthetic-only unit tests on **Draft PR #1698**. The module is an **optional dependency-injected adapter** rather than an installed collector or active GitHub publisher. It has no GitHub HTTP client, credentials, cron, `workflow_run`, production imports, or automatic execution. The module's direct CLI prints an explicit `adapter_uninstalled_no_live_publisher` non-formal status.

- `prepare_candidate(original_bytes, candidate_bytes, local_now_jst)`: refuses the wrong cohort/late local time (strict original generation, local candidate freeze, current local preflight and T−12 order), modified original bytes, changed ticket rankings, unexpected fields including result/payout, and duplicate JSON keys. It demands the original pinned V2 baseline and #1698's fixed second/third-order shadow. It returns exact candidate bytes plus a deterministic SHA-256/Git blob SHA-1 and path only for `position_sensitive_research/<race_code>.json`.
- `publish_write_once(..., branch, remote_read, remote_create)`: **rechecks original and candidate** before any callback, permits only the exact proposed `position-sensitive-forward-evidence-ledger` branch, rejects `main`, the PR branch, other evidence branches and different-byte collisions; identical retries are idempotent. Its external adapter contract requires **atomic GitHub create-only, NO existing-file SHA/upsert/update/force push**, followed by exact readback. A concurrency conflict must fail rather than overwrite.
- A successful mocked create/readback is **not** proof a real GitHub write happened, nor proof of first remote receipt. The returned record always has `first_remote_candidate_receipt_verified=false`, `official_beforeinfo_exhibition_six_odds120_verified=false`, `actions_run_inventory_complete=false`, `formal=false`, `model_improvement_proven=false`, `promotion_allowed=false`.
- CI tests reject same-second or after-T−12 attempts, stale original bytes, ticket tampering, duplicated JSON keys, hidden result fields, simulated concurrent writes, bad branch, failed readback, altered candidate bytes and attempted overwrites.

**Verified actual GitHub state:** the proposed `position-sensitive-forward-evidence-ledger` branch returned **404 / Branch not found**; `position_sensitive_research/` returned **404 / Not Found** on both main and the PR head. Therefore **no ledger has been created or populated** and **no Nov-09+ candidate first-remote receipt has been observed**. The branch name/path are *design-only* at this stage.

The next genuine forward research step needs an independent approved publisher on a **separate research branch**, a fresh future candidate frozen pre-T−12, an external independently verified immutable remote first-receipt and whole-run inventory, and official six/120 evidence. Research-only synthetic CI cannot do these things. Do not borrow the original main forecast's GitHub server-Date observer as first remote proof; a Contents GET proves at most observed existence. No changes to the collection, UI, Render, main, other research PRs or frozen protocol.

## 2026-11-08 21:00 JST — isolated research ledger exists; independent Git-history audit

**Correction to the earlier 404:** the previously proposed separate research ledger branch has now **actually been created**, from main bootstrap commit `6b371040fd2fc4398bfa882e6557c333cc0800c8`, under name `position-sensitive-forward-evidence-ledger`. First ledger commit `6fbc4990f7d2b0836a6516d129c1f533f771468a` adds **only** `position_sensitive_research/README.md` with the append-only/no-backfill rules. GitHub branch metadata and Contents API readback both matched this branch head and the directory contained **only README.md**. Neither main nor the existing live capture pipeline was modified to create this branch.

New `position_sensitive_ledger_history_audit.py` performs a *read-only Git ref/history verification* of the actual ledger:
- Resolve the exact branch ref and pinned bootstrap base; require descendant ancestry and strictly **linear single-parent** commits, not a merge/rebase-style conflicting lineage.
- Permit only added `position_sensitive_research/README.md` and valid `position_sensitive_research/YYYYMMDDJJRR.json` paths, after the declared 2026-11-09 cutoff. Reject file modifications/deletions/renames, result/payout files, repeated paths, missing/deleted candidate blobs and changed bytes since first Git add.
- Inspect future candidate JSON for fixed registration identity, no result fields, and optional exact original V2 read-only reproduction. If separately authenticated original bytes are unavailable, records are **not** called verified.
- Explicitly **do not** claim that a current Git history view proves the branch was never force-pushed before observation. An independently pinned append-only remote witness, candidate-specific *first* remote receipt, complete run inventory, official six/120 and independent confirmed results are still absent.

CI uses `actions/checkout@v4` with **fetch-depth: 0, persist-credentials: false** and read-only branch fetch; no GitHub contents write permission, dispatch, background scheduler or candidate publisher. It invokes the audit on `refs/remotes/origin/position-sensitive-forward-evidence-ledger`. The suite also uses temporary *local synthetic Git repositories* to test first-add, candidate original replay, mutation, deletion, disallowed result path and missing history.

**Verified exact-head CI** [#42478213417](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42478213417): **73/73 tests passed**, branch tip matched `6fbc4990f7d2b0836a6516d129c1f533f771468a`, **1 approved README first-add**, **candidate files = 0**, **candidate independently witnessed receipts = 0**, **formal = false**, and 116/116 original Nov08 shadow replays remain result-blind. An initial test-only CI attempt failed 3 altered-history cases because negative tests expected a different failure label and a missing Git blob escaped as a raw subprocess error. The code now fails closed with the correct immutable-blob error, and the final exact-head run passed. No real candidate file was lost or altered.

**Next real-world gate is still unresolved:** enable a separately reviewed external candidate-only pre-T−12 publisher and independent first-remote witness before future 2026-11-09+ races; this Draft has neither writer activation nor published candidate data. The candidate selector and predeclared 300+300 pilot/confirmation remain frozen; prior 116 historical races cannot become the forward cohort. Strict Draft-only work, no main merge, Render/UI/collector or other PR modification.

## 2026-11-08 night — actual GitHub branch exists; independent candidate server witness still blocked

A read-only GitHub branch/contents API recheck showed that `position-sensitive-forward-evidence-ledger` **exists**, at commit `6fbc4990f7d2b0836a6516d129c1f533f771468a`, and the `position_sensitive_research/` namespace contains **README.md only**. The earlier 404/missing branch state is outdated. GitHub branch metadata reports `protected=false`; a current tip alone cannot establish immutable remote history. **Stored future candidate records = 0**, independently observed first remote receipts = 0. This is not the user-visible production application or an active research publisher.

Added separate `position_sensitive_remote_observer.py` and negative tests as an **optional read-only** witness of an **already remotely published** future candidate. It is not a writer, scheduler, candidate collector or first-receipt system. It can, when explicitly invoked with exact pre-result original V2 bytes and a valid future race code:

1. Fetch the **existing research branch ref** via GitHub's REST Git ref endpoint and bind a fixed 40-hex commit SHA; fetch the candidate Contents JSON at that **pinned SHA** rather than an unpinned moving branch name.
2. Require HTTP **200**, no `Age` header, a parseable UTC GitHub **server `Date`**, exact research path, base64 payload, Git blob SHA-1 and the original/candidate SHA binding. Recompute the unchanged registered selector, all four modes, ticket order and pre-T−12 chronology; reject a missing candidate, 403, 404, 408, 429, 5xx, cached or forged response, altered ticket, bad branch SHA, improper race identity, same-second cutoff, pre-freeze response or post-T−12 response.
3. If and only if a **real** GitHub candidate were already present before the cutoff and the HTTP witness ran in time, report `github_candidate_existing_preT12_observation_not_first_receipt` plus the observed server time and exact byte digest. **Even then the output always says `independent_candidate_first_remote_receipt_verified=false`, `branch_history_rewrite_excluded=false`, `formal=false`, `promotion_allowed=false`.** A Contents GET proves *observed existence* at its response timestamp, not original first arrival nor unaltered historical ancestry.

`github_get` allows only exact repository-bound GitHub API read endpoints, never GitHub write, external URLs or result locations. CI uses mock HTTP fixtures solely for negative contract checks and invokes the CLI **without race/code**, intentionally returning a non-formal unstarted state without any network request. The **first CI** for this new adapter failed a **test-fixture-only** unexpected URL `KeyError` when a forged branch SHA changed the Contents URL; fixed mock routing to simulate HTTP 404 so the witness properly fails closed. [Successful CI #42479633438](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42479633438): **80/80 tests**, 116/116 original Nov08 replay, unchanged selector protocol SHA; no real candidate capture.

**Remaining external requirements** have not been met: independent durable FIRST remote receipt on the exact candidate (not a later GET), a protectable/independently pinned ledger history, full future schedule/rescue run denominator, official T−12 beforeinfo plus complete six-boat exhibition and 120 odds, confirmed results, and same-race 300 pilot/300 confirmation. The fixed beta (2nd: 0.50, 3rd: 0.25) and first-boat mass are unchanged. None of these observations demonstrate improved hit rates, Top5/Top10 non-inferiority or ROI. Continue on Draft, no main/Render/UI/live capture modification, no model promotion, no auto-merge.

## 2026-11-08 evening — manual future research-only candidate publication adapter (NOT activated)

Added `position_sensitive_manual_publisher.py` plus **12 synthetic-only unit cases** to Draft #1698. The previous read-only observation and ledger-history audits remain independent. The new script is **strictly opt-in**; without `--publish --race-code <future-race>` it exits with `manual_publisher_disabled_no_network` and **never makes a network request**. The PR workflow calls this default disabled mode only; it never runs a real candidate writer, schedules a job, registers a background service or copies the script to main. The registered selector, V2 baseline, 300+300 future protocol and main production model remain unchanged.

In an *explicitly reviewed future manual execution* with a valid GitHub API token, the script is designed to:

1. GET an authentic **current main Git ref** then pin its exact 40-hex commit for the original V2 forecast. Fetch `four_mode_forecasts/<code>.json` at that commit, verify HTTP 200, GitHub UTC server `Date`, uncached response, exact blob SHA and internally replayable V2 source. Never accept a 403/404/429/timeout as original data success.
2. Freeze a new #1698 candidate using **only that original bytes** and the unchanged fixed-position selector, validate every same-race original and proposed ticket, reject forbidden result fields, and require the candidate local preflight to be **at least 90 seconds before T−12**. This is an operational safety margin, *not* independent external timestamp provenance.
3. GET only `position_sensitive_research/<code>.json` on the distinct `position-sensitive-forward-evidence-ledger`. A 404 is a **temporary absence check**, not publication success. Any existing candidate, whether identical or different, stops the operation with no rewrite. 403/429/500 fail closed.
4. If and only if all gates remain open, issue a GitHub Contents API `PUT` targeting only that candidate research namespace and exact branch, using a **create-only payload without existing-file `sha`**; require HTTP **201** with an exact returned Git blob SHA and commit identity. A 409/422 failure must never be retried as an update or silently treated as success.
5. GET the **exact new commit SHA**, verify returned candidate bytes/digest and GitHub server `Date` strictly **before T−12**. A late response is rejected. Even a real successful 201+readback returns `candidate_first_remote_receipt_independently_verified=false`, `all_official_T12...verified=false`, `formal=false`, `promotion_allowed=false`, because these API interactions do not independently authenticate the first remote arrival or complete schedule and official source evidence.

The permitted network endpoints are hard-scoped to GitHub's selected repository and candidate research path. The only authorized `PUT` is a create-only candidate on the separate research ledger; there are **no writes to main, original four-mode forecasts, production/UI, official collectors or other experimental PRs**. Secrets/tokens are neither serialized in reports nor written to the repository. No live authorization or actual `--publish` execution occurred in this Draft, and an operator must separately review branch permission/scope and arrange an independent first-remote witness before claiming future evaluation eligibility.

Mock tests include future-only clock, no retroactive freeze, original-source HTTP failures, duplicate-path rejection, malformed candidate preflight, blocked main mutation, absence 403/500, create 200/409/422/504, late GitHub server `Date`, modified readback and exactly matching already-present retry. These are not actual races or verified candidate receipts.

**Verified exact-head test CI** [#42480400125](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42480400125): **92/92 tests passed**, original Nov08 result-blind **116/116** replay, unchanged preregistered model blobs, candidate writer disabled. The GitHub research ledger remains an **empty README-only bootstrap** when last examined; no future candidate was actually published, no first remote receipt was witnessed and the prospective formal denominator remains **0**.

**Outstanding gate**: an actual **2026-11-09-or-later** independent candidate publication before each T−12, external first-remote witness or immutable timestamp, complete capture/run inventory, authenticated official beforeinfo six/exhibition six/120 trifecta odds, independent confirmed outcomes, and preregistered separate 300+300 model comparisons. The manual writer by itself cannot satisfy these requirements. Continue Draft-only; never merge or deploy automatically.

## 2026-11-08 22:17 JST — manual candidate write server-order & first-add ancestry safety

The separate **manual-only**, `--publish`-opt-in `position_sensitive_manual_publisher.py` is NOT connected to any GitHub Actions publication job, cron, workflow dispatch, Render service or current live model. The source archive must be an already-published future original V2, pulled read-only from a pinned main commit, with exact immutable bytes verified against the frozen selector. No 2026-11-08 race can be added to future enrollment.

Two additional fail-closed safety enhancements to **research-only** code were completed:

1. **Full server-Date order:** the candidate-missing HTTP 404 observation must follow the original remote source observation, candidate local freeze and independently fetched ledger ref; HTTP 201 create-response must be **strictly later** than the 404 server Date; Git commit metadata HTTP 200 must be **strictly later** than 201; final exact-commit Contents GET must be **strictly later** than that metadata response. Equal-second timestamps and reversed order are not sufficient proof. Strict < T−12 remains required on all remote timestamps; 403/404/408/429/5xx never count as successful capture. The synthetic fixtures explicitly test these boundaries.
2. **Git first-add parent binding:** immediately before checking absence/create, request `GET /git/ref/heads/position-sensitive-forward-evidence-ledger` and pin a valid branch-head commit ID. After an allowed HTTP 201 CREATE (no `sha` update parameter), request `GET /git/commits/<created_sha>`; verify the returned commit has the exact newly created SHA, **one parent only**, and that parent matches the saved pre-create branch head. Missing ref, forged branch/commit identity, merge commit, orphan, unexpected parent, missing metadata and late/same-second server responses **all reject a successful proof label**. Finally read exact candidate bytes by the new commit SHA, not a mutable branch name.

**Important partial-write hazard:** GitHub may have accepted HTTP 201 even when a later GET/metadata/readback fails. A post-create exception does *not* undo that remote candidate. Do not blindly retry with a different local freeze timestamp or overwrite. Inspect the research ledger via independent read-only audit, use the first-added exact blob where present, and mark its eligibility unknown until independently witnessed first remote receipt. Create-only operation itself does not prove independent first receipt or prevent remote history rewrites on an unprotected branch. Returned successful research output keeps `created_commit_parent_externally_attested=false`, `candidate_first_remote_receipt_independently_verified=false`, `formal=false`, `model_improvement_proven=false` and `promotion_allowed=false`.

New tests: `test_position_sensitive_manual_server_chronology.py` and `test_position_sensitive_manual_ancestry.py` with synthetic HTTP fixtures. **CI [#42484254805](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42484254805) SUCCESS**: **102/102 unit tests**, old frozen Nov08 V2 input replay 116/116, unchanged preregistered selector/model SHA. No actual future candidate publication or independent witness was created by these tests.

**Outstanding:** ledger is separate and currently unprotected; independent remote first-arrival timestamp witness is absent; complete per-run inventory and official T−12 six/120 source validation remain outside this PR. Formal future candidate cohort remains zero. PR remains Draft, without main/deploy/production collector changes or automatic merge.

## 2026-11-09 JST — first real create-only candidate in separate ledger; still not certified

**Actual research-only forward candidate stored, not a simulation.** On Nov 9 at local frozen timestamp **14:25:53.259000 JST**, the exact original V2 forecast for `202611091912` (**venue code 19, race 12**) was read from pinned main commit `d0176b671363bed275045a0d454732f7cabff1a8`. Source original Git blob SHA-1: `6b108e8d97c8f6b682e667df10f94148fa77567b`; original exact SHA-256: `9375c44f8795ba8ced90450ace5f82e1a3e88efdd7ec3b95c1af931c71a3b401`. Recorded original creation `10:38:08.248023 JST`, race deadline **20:38 JST** and local T−12 cutoff **20:26 JST**. The archived original existed in main's history in Git first-add commit `ebe9b8ee18c34acda480a6d498c930c6c3b8b8be`, whose **Git committer** field is `2026-11-09T01:38:10Z` (not an independently attested remote receipt).

Before writing, a separate local implementation reproduced **all four original mode's saved exact ticket combinations and five-decimal probabilities**, computed the fixed `SECOND_BETA=0.50`/`THIRD_BETA=0.25` conditional re-ranking, preserved first-place mass, bound the same-race original SHA-256, and required current local freeze strictly earlier than T−12. It committed **only one new candidate JSON file**, at `position_sensitive_research/202611091912.json` in existing separate `position-sensitive-forward-evidence-ledger` using create-only GitHub API semantics, never touching main. Exact new commit **`3665b15b36c617c042f0c93685e6bcdd4ba1e31a`**, with direct parent **`6fbc4990f7d2b0836a6516d129c1f533f771468a`**; created candidate Git blob SHA-1 **`054eaad2c770c308f1dd53f54a2ed7fbf8db13dc`** and SHA-256 **`29f8e94800b9a904538b8d0e7a9fbad02baf94b296e1a2bc2dc5e999cbf2cf41`**. The Git commit metadata reports **`2026-11-09T05:25:54Z`**. **Git commit times are not first remote receipts**. The candidate's historical branch remains **unprotected** and cannot independently rule out force-rewrite. The snapshot intentionally retains `formal=false`, `candidate_first_remote_receipt_verified=false`, `production_forecast_changed=false`, and `local_only_unpublished` as a *frozen snapshot schema status*, even though this exact immutable snapshot has now actually been stored in the research ledger.

**Independent Python replay of actual stored bytes** (not just fixture tests): extended `position_sensitive_ledger_history_audit.py` to accept **`--original-ref refs/remotes/origin/main`** and read each stored candidate's exact original V2 bytes from Git history. This path recomputes the registered selector and all four same-race original/candidate ticket lists; fails the CI if any candidate fails replay, was tampered with, or is missing its exact original. The read-only PR workflow uses this flag and asserts `candidate_original_exact_replays == candidate_files`. [Exact-head CI #42567427975](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567427975) **SUCCESS: 102/102 tests**, 116/116 historical Nov08 archived input-only replays, and **actual research ledger 1 candidate file / 1 exact original replay**, no model blob drift or production write. The ledger shows exactly two first-add commits after the pinned bootstrap: README plus candidate file. The saved comparison's initial **Top1 `1-2-4` happens to match the original**; do not force Top1 turnover merely for diversity.

**Evidence boundary remains strict:** actual research candidate file count **1**; candidate-specific separately authenticated independent **FIRST remote receipt 0**, complete capture/rescue run inventory 0, official T−12 beforeinfo + six-boat exhibition + 120 odds 0, independently confirmed outcomes eligible **0**. The GitHub create response and later Git readback + reported commit timestamp are durable evidence of stored bytes **now**, but **not** proof of the time of FIRST remote arrival. Therefore the preregistered 300+300 experiment's **formal paired performance sample is still 0**, hit-rate gain and Top5/10 non-inferiority remain unproven. Do not confuse "stored candidate" with "formally eligible". This was a single manual research-only storage action, not an active automatic publisher or a change to the production collector/schedule. Never retroactively include finished races or the Nov 5–8 development set. No main deployment, PR merge or auto-merge.

## 2026-11-09 — real pre-T−12 GitHub HTTP server observation of stored candidate (existence, not first arrival)

On **2026-11-09 14:31:10 JST** (GitHub REST `Date: 2026-11-09T05:31:10+00:00`), [PR-only CI #42567753710](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567753710) performed **actual read-only authenticated GitHub API GET** of the research ledger ref and the exact candidate at the pinned commit. It loaded exact original V2 bytes from main commit `d0176b671363bed275045a0d454732f7cabff1a8`, checked its independently recomputed SHA-256 `9375c44f8795ba8ced90450ace5f82e1a3e88efdd7ec3b95c1af931c71a3b401`, and used `position_sensitive_remote_observer.observe_candidate` to verify HTTP 200, uncached UTC server `Date`, research path, base64/Git blob SHA, original-to-candidate digest and pinned selector's 4-mode tickets. The candidate's SHA-256 observed via the server was exactly **`29f8e94800b9a904538b8d0e7a9fbad02baf94b296e1a2bc2dc5e999cbf2cf41`**, matched stored bytes; cutoff **20:26 JST**. Actual original deadline **20:38 JST**. This proves that **the candidate existed at GitHub by 14:31:10 JST, before T−12**. It is distinct from the Git committer time of 14:25:54 JST and is not inferred from local freeze clocks.

CI **102/102 tests SUCCESS**, live remote ledger **1 actual candidate / 1 exact Python source replay**, 116/116 historical Nov08 input-only replay, no changed frozen model code, and the actual observation diagnostic was stored as `position_candidate_nov09_live_http_observation.json` in artifact `position-sensitive-input-only-42567753710` (**artifact ID 13651932744**). No `--publish` was invoked by CI, no live forecast changed, and no results/payouts/odds were read. The PR's observation step is **one-off race scoped**, and after T−12 it records `not_observed_due_to_T12_cutoff` rather than falsely attesting a late observation.

**Do not over-certify:** the first Github API HTTP 200 on an object already stored **does not prove its FIRST remote receipt**, and Actions logs/artifacts are not independent historical WORM timestamps. The ledger branch is not protected. Candidate independently attested first-receipt **0**, formal forward-eligible sample **0**, complete 300+300 paired outcome sample **0**, official T−12 beforeinfo/exhibition six/120 odds still not verified. This is meaningful *pre-cutoff remote existence evidence* only. All research remains Draft, no main merge, auto-merge, UI/Render or production schedule change.

## 2026-11-09 16:55 JST — result-blind FULL prospective candidate-roster monitor

Confirmed a **real** research-ledger candidate exists for \`202611091912\`, committed in **create-only** separate ledger, as documented above. Unlike the prior hard-coded one-race GitHub observation, new \`position_sensitive_live_roster_audit.py\` enumerates **every** candidate file at one locally fetched and pinned immutable Git commit of \`refs/remotes/origin/position-sensitive-forward-evidence-ledger\`, checks the complete list (approved paths, unique identity, <=600 files), reads exact originals from \`refs/remotes/origin/main\`, and validates **ALL** candidates and four-mode ticket lists against the preregistered selector **before** making any remote GitHub HTTP calls.

For each candidate before its exact T−12 cutoff, the tool performs read-only GitHub ref+Contents GETs with server UTC \`Date\`, confirming the actual observed ref commit **equals the roster's fetched commit**, as well as exact original SHA-256 and candidate SHA-256. If a candidate is already past T−12, the program reports \`deadline_cutoff_elapsed_no_new_observation_attempt\` and makes **no late call**; it never relabels a post-cutoff observation as pre-cutoff proof. Any mixed/corrupt roster, failed HTTP response, forged/changed tip or incorrect bytes fails closed rather than cherry-picking surviving rows. This does not claim a comprehensive **scheduled-run** inventory or an independent source of first remote receipt.

CI's old one-off \`202611091912\` witness was replaced with a **whole-ledger** witness; there is still **NO publisher, no scheduled candidate collector and no remote write** in the PR workflow. Nine added regression tests exercise no-observer-after-cutoff, missing/bootstrap/duplicate/unapproved paths, no HTTP on local validation failure, changed tip, changed remote bytes and intentional live opt-out.

[Exact-head CI #42582397029](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42582397029) **SUCCESS**, **111/111 tests**, immutable preregistration unchanged, **116/116 historical Nov08 V2 original replays**, and actual Nov09 research ledger **1 candidate / 1 exact original replay**. GitHub server UTC \`Date\` for the new live GET was **2026-11-09 07:55:58 UTC / 16:55:58 JST**, against **20:26 JST** cutoff, and exactly matches candidate SHA-256 **\`29f8e94800b9a904538b8d0e7a9fbad02baf94b296e1a2bc2dc5e999cbf2cf41\`**. The job uploaded \`position_candidate_live_roster_observation.json\` as a **nonformal** Actions artifact, not a first-receipt certificate.

Result-blind ticket comparison on that **one** future saved candidate, using exact research-ledger bytes:

| Mode | Original Top1 | Candidate Top1 | Top5 overlap | Top10 overlap |
|---|---|---|---|---|
| narrow | 1-2-4 | 1-2-4 | 5/5 | N/A (five-ticket mode) |
| hit | 1-2-4 | 1-2-4 | 5/5 | 8/10 |
| balance | 1-2-4 | 1-2-4 | 4/5 | 9/10 |
| hole | 1-5-2 | 1-4-3 | 3/5 | 6/10 |

Top1 changes only for **hole**, not every mode; **do not optimize toward forced diversity** or infer any hit-rate improvement. Only pre-result ranks were accessed; no result or payout was included in this comparison.

**Evidence separation:** candidate physically stored **1**, independently authenticated **pre-T−12 GitHub existence observed 1**, independently verified **FIRST remote receipt 0**, official complete predeadline beforeinfo/6 exhibition/120 odds **0**, complete scheduled/rescue-run inventory **0**, formally eligible race **0**, pre-registered pilot/confirmation formally scored **0/300 + 0/300**. Unprotected candidate branch history remains vulnerable to an unseen earlier rewrite. Nothing is promoted; main, source collectors, Render/UI, fixed model, #1693 and hole-mode research stay unchanged. Draft PR only, no auto-merge.

## 2026-11-09 17:19 JST — public GitHub checkpoint and automated prospective ticket turnover (NOT a first-remote receipt)

The one real research-only candidate already published in `position-sensitive-forward-evidence-ledger` for race `202611091912` was cross-checked against a **second GitHub public record**, [PR comment #6735313191](https://github.com/ikst2512-eng/boat-edge-clean/pull/1698#issuecomment-6735313191). GitHub's Issues Comments API reports this comment `created_at = updated_at = 2026-11-09T08:12:02Z` (**17:12:02 JST**), which is before the race's **20:26 JST T−12** cutoff. The comment names the candidate SHA-256 `29f8e94800b9a904538b8d0e7a9fbad02baf94b296e1a2bc2dc5e999cbf2cf41`, Git blob SHA-1 `054eaad2c770c308f1dd53f54a2ed7fbf8db13dc`, original source SHA-256 `9375c44f8795ba8ced90450ace5f82e1a3e88efdd7ec3b95c1af931c71a3b401`, and the actual candidate first-add commit `3665b15b36c617c042f0c93685e6bcdd4ba1e31a`. A separate [GitHub Actions #42582605064](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42582605064) had independently read the candidate via authenticated Contents HTTP and server `Date = 2026-11-09T07:57:57Z` (16:57:57 JST); exact original/candidate replays passed, but **this is existence, not FIRST remote arrival**.

New read-only `position_sensitive_public_comment_witness.py` binds the current GitHub API comment's ID, owner, PR URL, server `created_at`/present `updated_at`, exact path/cutoff/original/candidate digests and **unique Git first-add commit from the fetched ledger history**. It rejects edited, spoofed, after-cutoff or mismatched comments. A test fixture has no weight as real external provenance. Critically, **a GitHub comment is EDITABLE and a dated claim inside it is NOT proof the candidate was first remotely received at that time**. The audit always sets `comment_is_immutable=false`, `independent_candidate_first_remote_receipts_verified=0`, `formal=false`, `promotion_allowed=false`. The proof is a *second corroborating GitHub-created checkpoint*, not an independent first-receipt certificate and not evidence that all capture opportunities were present.

New `position_sensitive_future_topk_exposure.py` independently enumerates **every candidate file on the frozen fetched research-branch tip**, fetches exact main V2 originals, replays all four locked candidate modes, and counts **ordered-rank changes separately from TopK membership changes** without opening any result or payout. On the **one** actual future candidate, mode-specific changed ticket *membership* is:

| Mode | Top1 changed | Top3 changed | Top5 changed | Top10 changed |
|---|---:|---:|---:|---:|
| narrow | 0 | 1 | 0 | N/A |
| hit | 0 | 1 | 0 | 1 |
| balance | 0 | 0 | 1 | 1 |
| hole | 1 | 1 | 1 | 1 |

Exact dropped/replacement ticket slots: `hit Top10=2`, `balance Top5=1 / Top10=1`, `hole Top3=2 / Top5=2 / Top10=4`; narrow/hit Top5 membership remains the same even if rank order changed. Top1 does **not** need to differ on every race: preserving the original Top1 when it is also the candidate's highest probability is valid and avoids forced diversity.

[CI #42585107968](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42585107968) **SUCCESS — 127/127 tests** after a regression-test fix that blocks the pre-registration cutoff's early Nov08 dates before any Git read. Its public checkpoint, whole-ledger live observation and TopK exposure outputs are uploaded as diagnostics, and checked against each other's exact SHA identities.

**Evidence gates remain unchanged:** candidate bytes genuinely stored **1/600 (~0.17%)**, candidate exact original matched **1**, pre-T−12 GitHub observed existence **1**, first independently verified remote receipt **0**, complete run denominator **not verified**, official beforeinfo/exhibition 6/120 **not verified**, formally eligible pilot **0/300**, confirmation **0/300**, hit-rate improvement **not measured**. No live adoption, no auto-merge, and no main/Render/collector/UI changes.

## 2026-11-09 17:38 JST — count missing *candidate* freezes among every saved original

**Why this matters:** the previously observed **one successful research candidate** was not a complete intake denominator. Counting only published candidates conceals source-to-candidate attrition. New `position_sensitive_candidate_delivery_gap.py` gives a read-only snapshot of **all currently saved original V2** forecasts for a selected forward day, enumerated from one pinned `origin/main` commit, versus **all candidate files** at one pinned independent research-ledger branch tip. It checks every original by recomputing **all four mode rankings from the frozen V2 dependencies**, requires intact pre-T−12 original chronology, and replays every saved candidate. No result, payout, performance scoring, write, scheduling or publishing.

**Actual [CI #42587377550](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42587377550): SUCCESS, 136/136 tests.** The **2026-11-09 17:38 JST** source/candidate snapshot showed:

| Stored original V2 opportunity snapshot | Count |
|---|---:|
| Original forecast files eligible for exact result-blind source replay | **104** |
| Original replay invalid/excluded | **0** |
| Matching source-bound position-sensitive candidate already on research ledger | **1** |
| Original exists, no new candidate, local T−12 freeze window elapsed | **86** |
| Original exists, no new candidate, local T−12 freeze window still open | **17** |
| Original's recorded generation later than the runner clock | **0** |
| **Candidate delivery as % of available saved original files** | **1/104 = 0.96%** |

The **103 missing candidates must NOT be retroactively created once their T−12 cutoff has passed**. In particular, **86** were already elapsed at the audit instant; **17** were still within their theoretical local publication window, but that count diminishes as deadlines pass. The one stored candidate is `202611091912` with recorded T−12 cutoff **20:26 JST**. A positive local time window is NOT evidence a candidate was ever independently received before cutoff.

For reproducibility and missing-data accounting, the diagnostic artifact `position_candidate_delivery_gap.json` now records the **complete per-race main original roster**, exact original SHA-256, any candidate SHA-256, per-race status, all exclusions, both pinned Git commit tips and an independently reproducible SHA-256 of the observed roster. Tests include all-original enumeration versus an isolated saved candidate, source tampering, mismatched candidates, absent original source, unapproved paths, forbidden Nov08 retrospective day, empty denominators, future clock and lack of outcome access.

**Denominator caveat:** This is *not* the complete roster of race opportunities nor a verifiable run/dispatch/rescue schedule inventory. It counts only originals already visible in the fetched main Git snapshot, so 104 is not 104 independent first remote receipts and not the denominator of a formally eligible 300+300 holdout. The **0.96%** is strictly candidate **delivery coverage among saved originals**, not a hit rate. Every output fixes `candidate_first_remote_receipts_independently_verified=0`, `formal_forward_eligible_races=0`, `promotion_allowed=false`.

**Operational implication:** manual-only future candidate publication is a major bottleneck. The highest-priority next step is a **separately reviewed, create-only research publisher with genuine independent predeadline first-remote receipt**, plus a complete frozen opportunity inventory. Do not change the production collector or merge #1698 into main to address this. No retrospective backfill, no forced ticket diversification, no approval to adopt or deploy.

## 2026-11-09 17:52 JST — local-only whole-day exporter + 15 actual create-only research-branch candidates

**Operational progress, NOT formal accuracy research:** A new `position_sensitive_candidate_batch_export.py` uses `position_sensitive_candidate_delivery_gap.audit_delivery_gap` over independently fetched `origin/main` and the separate research ledger Git tips. It enumerates *every saved original* for the selected day, validates the complete 4-mode V2 replay, refuses all late/already-saved/malformed candidates, freezes each new future snapshot with the preregistered second/third selector, and requires **at least 600 seconds of theoretical margin before T−12 at export**. It also validates the local snapshot and exact SHA-256/Git blob identity. It has **no GitHub write method, no scheduled production capture, no results/payouts or odds access**. Its default is to write a local report; explicit `--emit-candidate-lines` prints optional export candidates for a separately reviewed manual upload.

A dedicated PR CI step generated **15 strictly before-cutoff** candidate byte strings from the **104 saved original Nov09 V2 forecasts**; at ~17:48 JST, 1 candidate was already stored, 87 original-only T−12 windows had expired and 16 original-only windows were still open (one of those had less than the 600-second batch export safety margin). [Exact generation CI #42588613656](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42588613656) **SUCCESS: 144/144 tests**, **15 locally frozen candidates**, and **0 GitHub writes in CI**. All 116 Nov08 historical replays and fixed selector/model preregistration remain intact.

**Actual off-CI manual research-only publication:** Following successful CI, 15 **new** JSON files were created through GitHub's *create-file* operation only on **`position-sensitive-forward-evidence-ledger`**, never on main or the Draft PR branch. Each individual new file was then independently fetched through the connector, and its exact UTF-8 bytes and Git blob SHA-1 agreed with the original CI-exported candidate. No existing file was updated; all 15 writes plus readbacks succeeded. Ledger now has **16 JSON candidates** (previous 1 + batch 15). Recorded research ledger head after the batch is **`fdf1eb6c77f275fc7fd18d5b039e5f41ec8b5462`**. [PR discussion checkpoint #6735991922](https://github.com/ikst2512-eng/boat-edge-clean/pull/1698#issuecomment-6735991922) itemizes all 15 race codes, exact candidate SHA-256 and their T−12 cutoffs. The batch was processed in ascending cutoff order, not based on race results. GitHub API confirmed current ledger namespace contains **16 JSON files + README.md**.

**Numerical intake change:** among 104 *currently stored original V2s*, research candidate delivery advanced from **1/104 = 0.96%** to **16/104 = 15.38%**. This **is not** a formally eligible cohort denominator: the full scheduled opportunity/run inventory is still unverified; selection is by the presence of source records and surviving time windows. Candidates that were already past T−12 were **not backfilled**. Frozen local timestamps and a GitHub create/readback response are **not independently witnessed FIRST remote arrival**, and PR comments are editable (so a GitHub-created timestamped comment is only a second public assertion). The ledger branch remains unprotected; its full historical immutability is not attested.

**Missing scientific gates remain:** candidate first-remote *independent* receipts **0**, complete official T−12 beforeinfo/exhibition 6/120 odds **0**, complete scheduled and rescue run inventory not verified, no independently certified forward paired outcomes, formal pilot **0/300**, confirmation **0/300**, no observed Top1/Top5/Top10/ROI improvement or formal noninferiority. **The frozen β2=0.5/β3=0.25 selector, main, production collector, UI, Render, PR #1693 and hole-mode work stay unchanged; #1698 Draft only, no merge or auto-merge.**

The next remote-history and externally observed existence CI must audit **all 16** candidates, not only the previous single race, and keep the strongest label no higher than nonformal pre-T−12 observed existence. In future, a separately approved isolated runner and durable first-remote witness, not an unreviewed PR automation, are required for reliable continuous candidate capture.

**Post-write GitHub diff check:** comparing the research-ledger bootstrap base `6b371040fd2fc4398bfa882e6557c333cc0800c8` to its batch head `fdf1eb6c77f275fc7fd18d5b039e5f41ec8b5462` returned **17 commits ahead, 0 behind; all 17 changed paths are additions under the approved `position_sensitive_research/` namespace (README + 16 candidates), with no changed/deleted original files**. This confirms the currently visible branch graph is additive, but an unprotected ref could still have been rewritten before this observation. All conclusions stay nonformal.

## 2026-11-09 17:56 JST — POST-publication full-ledger remote existence audit (16/16)

At the exact PR code head `f70cefbd381cebf6fad2b5c3af20181bdf894661`, [GitHub Actions #42589486642](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42589486642) completed **SUCCESS — 144/144 tests**, matching the previously locked preregistration and **116/116** Nov08 original historical input-only replays. Importantly, this was an actual **post-publication** read-only audit of the 15 newly written candidates plus the pre-existing 1, not a synthetic CI acceptance check.

- **16/16** candidate files in the complete separate research ledger passed exact original-V2 input/selector reproduction from the pinned main source; ledger Git history audit found **16 permitted candidate first-add files** and no unauthorized current-history mutations.
- A live whole-ledger GitHub API witness independently read **16/16** candidate Contents JSON objects at pinned Git commit SHA, checked their precise original/candidate digests, and received GitHub UTC server `Date` headers **before each race's own T−12 deadline**. `status_counts.remote_existence_observed_preT12_not_first_receipt = 16`, `deadline_cutoff_elapsed_no_new_observation_attempt = 0`, **candidate_first_remote_receipts_independently_verified = 0**. This existence verification happened around **17:56 JST**, before the earliest newly stored candidate's T−12 cutoff (**18:01 JST**). Later reruns must not retroactively relabel late GETs as early.
- The full-day frozen original-to-candidate intake counts **16/104 saved originals = 15.38% delivery**, **88 source originals already elapsed with no candidate**, **0 currently open original-only local freeze windows**, **0 invalid original replays** at the ~17:56 JST audit time. The batch exporter itself now plans **0** new local freezes, because the 16 available records have been saved and the others expired.
- Separately, the public GitHub [batch checkpoint comment #6735991922](https://github.com/ikst2512-eng/boat-edge-clean/pull/1698#issuecomment-6735991922) has independently queried GitHub Issue Comments API `created_at = updated_at = 2026-11-09T08:52:09Z` (**17:52:09 JST**). It lists all 15 new exact candidate SHA-256 values and deadlines. **This comment can still be edited later** and its timestamp attests an assertion, not a first-remote candidate arrival or external WORM receipt.

**Unchanged research distinction:** successfully **created and witnessed pre-T−12 existence = 16**, independently verified **FIRST remote receipt = 0**, independent authoritative full beforeinfo/exhibition six/120 odds **not proven**, complete capture/rescue run opportunity denominator **not proven**, formal pilot and confirmation **0/300 + 0/300**, no measured accuracy or ROI improvement. The archived diagnostic report, not a later API GET, is the recorded evidence for the first-run early server observations. **This does not justify promoting the experimental model**. main, Render, live forecasts and original production collection remain unchanged. Draft open, no auto-merge.

## 2026-11-09 19:43 JST — observed scheduled vs manual GitHub Actions run inventory (NOT exact-slot failure proof)

**Observation source:** main's unchanged `.github/workflows/four-mode-prospective-capture.yml` was checked against its three literal cron expressions `7,22,37,52 22 * * *`, `7,22,37,52 23 * * *`, `7,22,37,52 0-11 * * *` (UTC). These specify **56 scheduled slots per 2026-11-09 JST day** between **07:07 and 20:52 JST** (4×14 hours). At an **as-of 19:40 JST** snapshot, **51 cron times** had elapsed and 5 were future. A cron time is only a scheduled opportunity: it is neither proof that GitHub created a run nor proof that a forecast was captured.

Read-only GitHub Actions REST list queries, both fully returned on page 1, with `created=2026-11-08T21:00:00Z..2026-11-09T10:40:00Z`:

| Event queried | All repository workflow runs in that time window | Matching exact four-mode workflow | Matching capture jobs |
|---|---:|---:|---|
| `schedule` | **41** | **3** | 3 inspected, all succeeded |
| `workflow_dispatch` | **17** | **1** | 1 inspected, succeeded |

The matching scheduled runs are **#42546585986** (created 01:37:58 UTC), **#42551875149** (02:36:27 UTC), and **#42571429308** (06:10:20 UTC), all on `main`. The matching manually dispatched run is **#42589898074** (08:59:08 UTC), also on `main`. These four are **GitHub-created execution records**, not four successful candidate first receipts, and an observed successful capture job does **not** imply a given race's source/candidate was published. These time-filtered results were inspected live; later-created delayed runs can change counts.

**Numerical gap:** **51 elapsed cron times − 3 observed `schedule` workflow runs = 48**, but **48 is not a verified count of specific missing, failed, delayed, cancelled or intentionally omitted executions**. No run ID is securely tied to a particular intended cron timestamp. The manual dispatch is **not** subtracted from the 51-slot schedule denominator because it cannot be assigned to the missing slot it may have rescued. This is an operational visibility problem rather than proven model-performance failure.

Added `position_sensitive_schedule_run_inventory.py` and synthetic negative tests to Draft **#1698** only. It reads the pinned local main workflow source, independently checks all three literal cron settings, enumerates the complete Actions API `total_count` pagination for **both** schedule and manual dispatch *separately*, rejects duplicate run IDs, wrong event/status, malformed time, incomplete pages, out-of-window records, unexpected workflow edits, and any attempt to treat a research-branch manual dispatch as a main-branch capture. Explicit `--live` is **read-only GitHub HTTP GET**; CI defaults to a **no-network, no-dispatch state** and verifies the live main cron source through Git read-only. Observed run creation and job outcomes are separate from exact remote candidate creation and source completeness.

**[Exact-head CI #42603008822](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42603008822): SUCCESS, 156/156 tests.** It also passed registered selector/source-blob checks, 116/116 old Nov08 input-only replay, and the candidate ledger's read-only verification. The initial schedule test attempt failed one negative test because a fixture's replacement string omitted a YAML quote (no actual mutation happened); fixed, and the exact-head CI passed.

**Forward classification unchanged:** the separate research ledger contains 16 Nov09 candidates, with previous pre-T−12 **existence** observations for all 16, but independently verified candidate **FIRST remote receipts 0**, official all-input T−12 six/120 validation 0, **complete** capture/scheduled/rescue opportunities not independently attested, formally admitted pilot **0/300**, confirmation **0/300**. There is no model improvement or ROI certification. The only mutations are to #1698's Draft research/CI/docs; **main, live collector, Render, UI, fixed beta selector, and other research PRs stay untouched**. No scheduled research publisher was activated or auto-merge requested.

## 2026-11-09 20:03 JST — live GitHub Actions job-level reconciliation in read-only PR CI

The previous monitoring could observe `schedule` and `workflow_dispatch` *run objects*, but a green workflow/run was not a reliable indicator that its actual `capture` job completed. Added **`position_sensitive_run_job_reconcile.py`** and 8 synthetic negative/positive tests. The tool accepts the full, separately paginated scheduler/dispatch run inventory already made by `position_sensitive_schedule_run_inventory.py`, then performs an independent **read-only GET** of `/actions/runs/<run_id>/jobs?per_page=100&page=N` for every matching run. It requires a complete per-run job pagination, rejects foreign/duplicate job IDs, missing or duplicate `test`/`capture` jobs, inconsistent run IDs, implausible job state and forged run identities. A manual dispatch on a non-main branch is explicitly classified separately from main capture.

The research-only PR workflow now *really performs* the live, read-only GitHub API schedule + manual run listing **and** job reconciliation. It has `contents: read` only, no dispatch/push/PUT/POST or schedule activation, stores the exact JSON reports `position_schedule_run_live.json` and `position_schedule_jobs_live.json` in its 30-day diagnostic artifact, and validates **`formal=false`, `promotion_allowed=false`** before declaring diagnostic success. GitHub 403/404/timeouts or incomplete pagination are errors, never valid zero-run results. The original production workflow and candidate collector are unmodified.

**Actual [CI #42605872198](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42605872198) SUCCESS: 164/164 tests.** At `2026-11-09T11:03Z` (**20:03 JST**) the actual GitHub API / job data yielded:

| Distinct object / test | Observed count |
|---|---:|
| Cron slots configured for Nov09 JST | **56** |
| Cron slot timestamps elapsed as of observation | **52** |
| GitHub-created original four-mode scheduled workflow runs | **3** |
| GitHub-created original four-mode manual dispatch workflow runs | **1** |
| Scheduled runs with completed-success `capture` job | **3** |
| Manually dispatched main runs with completed-success `capture` job | **1** |
| Observed research-ledger candidate files replayed from original V2 | **16/16** |
| Candidate delivery among 104 original main forecasts | **16/104 (15.38%)** |
| Original-main records already past local T−12 without candidate | **88** |
| Saved-original records still in a candidate freeze window | **0** |

The **52 − 3 = 49 numerical gap** does **not** prove 49 individual missed, failed, suppressed or delayed scheduled executions; GitHub does not reliably attach each run ID to one exact intended cron slot. The manual dispatch must not be used to artificially fill scheduled slots. A `capture` job concluding success may perform tests and staging with **no eligible file pushed**, so 3/3 + 1/1 completed capture jobs **do not certify forecast publications**, and even confirmed original publications would not prove new candidate first remote arrivals.

The new CI originally failed one negative fixture that did not return a mock jobs page 2; fixed it to return an explicitly empty page while claiming 101 results, which the code correctly rejects as incomplete. The subsequent successful CI has no test failures. No outcome, payout, other research PR or official source data was modified or used for inference.

**Remaining gates:** separate candidate independently verified *FIRST* remote receipt **0**, complete predeadline beforeinfo + six-boat exhibition + 120 odds **not authenticated**, complete Actions/schedule/rescue opportunity denominator **not proven**, valid 300 pilot + 300 confirmation eligible outcome pairs **0**, no model accuracy/ROI/noninferiority conclusion. Keep Draft unmerged, no main or Render/UI/collector changes, no changes to frozen second/third beta. A separate approved immutable witness and early scheduled candidate-only publisher are still needed for meaningful large-scale prospective verification.

## 2026-11-09 20:16 JST — verify four green capture jobs did NOT each publish forecasts

**Root-cause evidence (actual GitHub Actions capture job logs, independently re-opened):** the day had three visible scheduled original four-mode runs and one manual main-branch run. Their individual green `capture` jobs do **not** imply four separate forecast-publication events.

| Actual original-main capture run | Event | Staged new original files | Reported publication and independently checked main Git history |
|---|---|---:|---|
| [#42546585986](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42546585986) | scheduled | **104** | Log `pushed_to_main`; new commit `ebe9b8ee18c34acda480a6d498c930c6c3b8b8be`; GitHub commit API directly shows **104/104 added paths** `four_mode_forecasts/20261109JJRR.json`, no modified/deleted paths. Parent `a4e7168f8af26e989d45df76746ae24b3fa5b690`. The commit was 12 commits behind the then-current main head with `behind_by=0` when compared as the base, so it remains on main's visible history. |
| [#42551875149](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42551875149) | scheduled | **0** | Log `no_eligible_candidates`, no new forecast commit |
| [#42571429308](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42571429308) | scheduled | **0** | Log `no_eligible_candidates`, no new forecast commit |
| [#42589898074](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42589898074) | manually dispatched on main | **0** | Log `no_eligible_candidates`, no new forecast commit |

All four `capture` jobs were marked success, which is consistent with the later three jobs finding **104 already saved original forecasts** and legitimately avoiding duplicate publication. The first job's final `FOUR_MODE_EVIDENCE_VERDICT` said `published_with_durable_early_observation` with `published=104`; the other three said `no_new_forecasts`. These log assertions are supported for the first run by GitHub's separately queried **actual commit files**, but do **not** prove an independently witnessed FIRST remote receipt, official six/120 input completeness, or the candidate's new-model accuracy.

Added `position_sensitive_original_publication_audit.py` and 10 fail-closed synthetic tests to **Draft #1698**. The read-only parser accepts exact supplied GitHub Actions log bytes, extracts only actual timestamped stdout (not YAML source-code echoes), and binds one `Four-mode staging diagnostic`, one publication-or-no-new marker, the reported stage verdict and final source evidence verdict in proper chronological order. If a positive publication is claimed, it verifies the single-parent commit's **ancestry to a pinned fetched `origin/main`**, insists every first-added path is an immutable original forecast of the selected forward day, and requires the number of Git first-add files to equal both the staging count and the printed publication count. A zero-new success returns **zero** without Git writes or a fictitious publication. It rejects duplicate markers, merged/orphaned commits, result/candidate paths, modified forecast paths, missing first-adds, tampered verdicts, wrong race day and altered log order. Its default CLI intentionally audits **no externally supplied log** and certifies nothing; the current PR CI runs only synthetic contract tests, not retroactive historical admission of the four runs.

[Exact-head CI #42607583159](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42607583159) **SUCCESS: 174/174 tests**, including the new 10 tests; unchanged preregistered selector, 116/116 historical Nov08 result-blind replay, research candidate ledger **16/16** exact V2 source replays.

**Keep populations separate:** **104** genuine original V2 forecast first-adds in one past main commit; **16** different research-only position-sensitive candidate JSONs previously observed existing before their individual T−12; **0** independently verified candidate FIRST remote receipts; **0** complete all-slot/full-source official T−12 receipts; formal pilot **0/300**, confirmation **0/300**. The 16/104 research delivery percentage measures **candidate storage**, not model accuracy. Original-main commits and completed workflow jobs cannot substitute for a pre-registered immutable candidate receipt. No retrospective additions, model promotion, deployment, automatic merging or production workflow changes.
