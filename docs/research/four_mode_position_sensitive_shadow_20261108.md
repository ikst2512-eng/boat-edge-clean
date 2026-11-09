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
