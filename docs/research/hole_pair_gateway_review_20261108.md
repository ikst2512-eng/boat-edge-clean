# Hole-pair manual research gateway — REVIEW ONLY (2026-11-08 JST)

**NOT DEPLOYED. This is a separate Draft PR and is NOT on main. Do not merge automatically.**

## Purpose and separation

The large research-only Draft PR [#1685](https://github.com/ikst2512-eng/boat-edge-clean/pull/1685) has an otherwise reviewed nonformal candidate freezer, manual-only driver, evidence validators and offline tests, but its `.github/workflows/hole-future-pair-precommit.yml` is not registered on the default branch. GitHub's `workflow_dispatch` requires default-branch registration. Merging the whole multi-file study solely to enable a trigger would unnecessarily widen the main change surface.

This **standalone, single-workflow entry point** is proposed for manual review as a *possible future* read-only Actions gateway. It does not itself deploy anything while Draft/unmerged. It is not a new periodic job, does not modify the production predictor or existing collector, does not touch Render/Cloudflare, does not create a repository commit and does not enable promotion to formal accuracy.

## Exact security boundaries

- **Capture only through `workflow_dispatch`; `pull_request` runs a separate `review_only` self-audit and never collects candidates.** No `schedule`, `push` or `pull_request` capture. The capture job checks `github.ref == 'refs/heads/main'`; branch-selection cannot bypass.
- Requires two explicit manual inputs: `capture_day_jst` and literal `CAPTURE_UNVERIFIED_RESEARCH` acknowledgment. The underlying reviewed driver checks the date against the actual *current Japan date*, requires 2026-11-09 or later, and rejects PR, cron, stale/backdated or future-day calls.
- Checks out **exact pinned research commit** `464d1641a5c7b981248ab17ba5bdc42b7bfa698b` (a verified 2026-11-08 Draft #1685 CI head), not a mutable research branch or an arbitrary user-supplied ref.
- `contents: read` is the only repository permission. It fetches the `origin/main` commit and original `four_mode_forecasts/` files to inspect the current-day snapshot, never pushes or writes any branch. No secret/token to Cloudflare or another server. The temporary GitHub runtime token only has read access to repository contents.
- The driver verifies raw source bytes against the Git blob SHA1 and each locally frozen candidate's original source SHA256, the fixed selector/method contract and every source-snapshot race ID. For exclusion statuses, it writes specific race ID/reason evidence. It never opens the results directory to compute new tickets.
- One manually triggered run serializes per named JST day (`concurrency`, cancellation disabled); **this is not global first-receipt locking**, and separate later manual runs for the same day could still overlap. Cross-batch dedup/quarantine in #1685 must be separately applied before any scoring.
- Uploads its **nonformal** candidate and exclusion manifest to an Actions artifact with `if-no-files-found: error`. If no candidate is frozen, uploads the empty/exception roster first, then fails the job rather than falsely reporting candidate success. Artifacts and their upload time are NOT independent candidate first-receipt proof.
- Candidate/batch fields are explicitly `formal=false`, `prospective_validation=false`, `independent_first_receipt_verified=false`, `production_forecast_changed=false`. This gateway never updates status to eligible or proven.

## No-go and required external approvals

**Even after hypothetical manual merge, do not claim independent T−12 or a formally eligible pilot.** An official timing/retention and complete beforeinfo/exhibition for all six boats plus full 120-way odds (all pre-T−12) are absent; the separate Cloudflare D1 proposal is not deployed and the source still has no independently signed *first external receipt*. Independent confirmed results and the prespecified 300 pilot / following 300 untouched confirmation are additional gates.

Before any manual merge/run, a human reviewer must confirm:
1. #1685's exact pinned commit remains present, code/selector SHA remains unchanged, CI and candidate/roster fail-closed tests still pass, and no GitHub secret exposure or excessive token permissions exists.
2. This exact workflow is the **only** new default-branch change; no unreviewed additional cron, software deployment or whole research PR merge.
3. The owner understands it will create **research-only, nonformal candidate artifacts** on manual action, with no independent T−12 evidence, and a day's missing early forecasts cannot be filled after their cutoff.
4. A separate independent first-acceptance witness, official-source completeness checker and cross-run missingness/chronology ledger are required *before* any formal metrics. No old Nov 6–8 samples may enter the Nov9+ confirmatory cohort.

**Current status: main unchanged by this Draft, no dispatch, no artifacts, no cloud deploy, no formally certified candidates.**

## November 9 review comparison: overlapping Draft gateway #1701 versus #1702

**Do not merge both gateway PRs.** Both are unmerged drafts proposing default-branch manual workflow registration, but differ in their exact pinned driver:

- [Gateway #1701](https://github.com/ikst2512-eng/boat-edge-clean/pull/1701) checks out research SHA `ec83d7254b8703a49a34ce10b343390e6da74f84`. Its actual `research/hole_pair_manual_capture.py` does **not** contain the subsequently added full original Git blob bytes check (`immutable_main_source_blob_content_mismatch`) or frozen source SHA check (`frozen_candidate_original_source_sha256_mismatch`).
- [Gateway #1702](https://github.com/ikst2512-eng/boat-edge-clean/pull/1702) checks out later reviewed SHA `464d1641a5c7b981248ab17ba5bdc42b7bfa698b`, whose manual driver **does** contain both checks, plus an exact-ID universe reconciliation, manual authorization and original future date restrictions. This offers a stronger fixed input-provenance gate for the same research objective.
- Added a **PR-only review job**, explicitly separate from the `workflow_dispatch` capture job. On [CI #42567225027](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567225027), `review_only` passed and **`capture` was skipped**. Also added current-JST/day/typed-ack checks *before checkout*, a main-only dispatch job guard, and disabled persistence of checkout credentials. The repository is public, so this does not require a read-write GitHub token to fetch `origin/main`.

**Manual recommendation, NOT permission to deploy:** review one isolated gateway (prefer #1702's more recent pinned source), mark #1701 superseded only with the reviewers' agreement, and keep both unmerged until the required operator/security decision. Future merging of a single manual dispatcher would still be a change to default main requiring explicit review; this chat has NOT merged, enabled, or executed a gateway. Every output stays nonformal, and real signed independent first receipt, official T−12 original six-boat/120-odds evidence, cross-run deduplication and pilot/confirmation eligibility remain separate blocked gates.

## November 9 follow-up — live competing-gateway guard and launch audit path mismatch

**Status remains HOLD / Draft / unmerged.** [#1702](https://github.com/ikst2512-eng/boat-edge-clean/pull/1702) is still the preferred single manually reviewed proposal. As observed on 2026-11-09, the default `main` tree contained none of these three gateway files:
- `.github/workflows/hole-pair-manual-gateway.yml` (this #1702 proposal)
- `.github/workflows/hole-pair-manual-research-gateway.yml` (competing #1701 proposal)
- `.github/workflows/hole-future-pair-precommit.yml` (larger #1685 research workflow)

**Readiness-audit mismatch (not a live failure):** the pinned #1685 `research/hole_pair_capture_launch_audit.py` checks only `.github/workflows/hole-future-pair-precommit.yml`. If #1702 alone were subsequently manually merged, that older script would continue reporting `default_branch_dispatch_prerequisite_satisfied=false` because it checks a different path. This false negative is *not* proof that #1702 cannot dispatch, and a green old audit would not prove that #1702 safely ran. Before any activation, a separately reviewed gateway-specific audit must inspect the actual default-branch `hole-pair-manual-gateway.yml` and the registered workflow in GitHub Actions. Do not edit the locked #1685 source or silently widen this PR to repair the mismatch.

**New fail-closed duplicate-gateway safeguard on #1702 only:** the PR-only review verifies neither competing file exists in its checked-out merge tree. The manual capture job, if separately authorized in the future, also checks both competing workflow paths in the freshly fetched immutable `origin/main` tree **before calling the research capture driver** and fails if either exists. This mitigates accidental dual capture initiated through #1702; it cannot prevent someone from separately executing #1701 or repeating #1702 later in the day. Cross-run exact race-ID/bytes deduplication and independent first-write evidence remain mandatory.

### Formal per-race admissibility (all required, no shortcuts)

For each race code, the future reviewer must independently bind **the same race ID** across all of the following, and quarantine or exclude when any item is missing:
1. Original immutable source forecast bytes, Git blob SHA1, SHA256, candidate bytes/selector+method hashes and fixed tickets; an independently authenticated *first* remote receipt of the exact candidate bytes with tamper-evident trusted server time **before the official T−12 cutoff**, not a later GET or Actions artifact.
2. Official race identity and official deadline, raw original official race-card/beforeinfo and exhibition values for **all six boats**, each with provenance and authenticated receipt before T−12.
3. Raw official three-way odds covering **all 120 distinct combinations** (not inferred from a count alone), with exact content digest, source and independently defensible receipt time before T−12.
4. Complete across-run source/race-ID census, missingness/exclusion reasons, cross-batch conflict quarantine and verified independent confirmed result **opened only after fixed candidate validation**.
5. Fixed study method/cohort boundaries: 300 pilot observations followed by an untouched separate 300 confirmation, with race ID unique across both; historic Nov 6–8 study data never imported as future confirmatory observations.

The D1 Worker/SQLite prototype on #1685 is **undeployed**. Its self-reported database receipt and simulated SQL tests do not establish an externally signed or independently authenticated first acceptance, official cutoff or full six-boat/120-odds T−12 chain. The only permitted status until each gate is independently established is `formal=false`, `pilot_formally_eligible=0`, `confirmation_formally_eligible=0`, `production_promotion_allowed=false`.

**Manual decision still required:** one gateway only, permission scope, usage/retention budgets, idempotency, independent witness design, official-source acquisition, and a new exact-path default-branch registration audit. No manual dispatch, real remote capture, Cloudflare deploy, model, Render, UI or main change is authorized by a passing review CI.

## November 9 reproducible chain-of-custody enhancement (still NONFORMAL)

The proposed manual gateway now rejects a drifted Git main source: immediately after fetching `origin/main`, it compares that commit against GitHub's immutable `GITHUB_SHA` from the selected `main` workflow-dispatch event. If main moved while the runner queued, the run **fails before selecting candidates**, rather than silently consuming a newer source snapshot. The existing exact research-code SHA pin remains unchanged.

After creating and validating the nonformal candidate manifest, a new **local provenance sidecar** `research_capture_provenance.json` is derived from the exact original manifest bytes and local Git refs. It records:
- GitHub workflow run ID, attempt and workflow ref, dispatch-time main SHA, source main SHA and pinned research SHA.
- Date, original manifest filename, exact byte length and SHA256.
- Explicit `formal=false`, `independent_first_receipt_verified=false`, `official_t12_complete_verified=false` and `production_promotion_allowed=false`.

The upload now requires **both nonempty files** and stores both in the same 30-day `hole-pair-manual-unverified-YYYYMMDD` Actions artifact. The original candidate manifest bytes are not rewritten. This makes a future manual run easier to audit by run and input commit, but does **not** provide durable independent first-acceptance evidence. Thirty-day GitHub artifact retention is insufficient as the sole archive for the intended 600-race longitudinal study; external immutable archival/retention must be separately reviewed before formal certification.

**Simulated test evidence:** the PR-only review job extracts the exact embedded sidecar generator and executes it with synthetic manifest bytes and stubbed Git refs; it checks SHA256, byte size, run ID and false proof flags. Wrong dispatch main SHA or a forged `formal=true` manifest must fail without creating a sidecar. These tests have **no outcome data, external network, Cloudflare, candidate collection, or production integration**. [CI #42588574527](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42588574527) passed: `review_only` success, real `capture` skipped.

**Still blocked:** first independently authenticated remote acceptance with trusted time; original official T−12 cutoff and per-race six-boat beforeinfo/exhibition + 120 distinct odds; actual manual execution proof; cross-run durable first-write/dedup/quarantine; storage/retention decisions; distinct fixed 300 pilot and 300 confirmatory cohorts. No main merge or actual dispatch is authorized by the sidecar or CI results.

## November 9 — Actions run rerun fail-closed proof (Draft only)

**New behavior if this gateway is ever separately approved and registered:** `capture` now checks the immutable GitHub Actions execution identity **before any source checkout**. It only proceeds if `GITHUB_RUN_ATTEMPT == 1` and `GITHUB_RUN_ID` is a positive decimal integer. A GitHub "Re-run jobs" attempt on the same original workflow run fails immediately, even after a failed/empty first attempt. It cannot retroactively refresh a previous source snapshot or produce a second candidate artifact from the same run. The pre-existing acknowledgment, exact current JST day and main-only branch guards stay in place.

**PR-only executable regression:** [CI #42601842246](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42601842246) returned **success**. The `review_only` job extracted the actual pre-checkout bash guards and executed them under synthetic environment values. The first attempt with a valid current-JST day and typed acknowledgment passed; simulated attempt 2, missing/malformed attempt, missing/zero run ID, wrong acknowledgment and stale day were rejected. The real `capture` job was **skipped**; no actual candidate or external receipt was created. This proves the local bash input boundary, not that any future live manual collection works.

**Hard limitation:** Every new `workflow_dispatch` creates a **different** run ID with attempt 1, and remains capable of overlapping an earlier manual capture on the same JST date. The existing daily concurrency setting serializes simultaneous runs only; it is not a durable uniqueness constraint or signed first-receipt lock. A first attempt failing after writing some unverified artifact cannot be assumed to leave the race universe untouched. Recovery must inspect past manifests and recorded race IDs, then apply the separate research `hole_pair_cross_batch_roster.py` audit, quarantine conflicts, and preserve provenance. A server-side atomic first-write constraint with independent authenticated receipt, retention and official T−12 originals is **still mandatory** before any 300+300 formally eligible observation is counted.

**Approval remains on HOLD:** no main merge, manual dispatch, Cloudflare D1 deployment, production prediction, Render or UI changes. No latest green CI may be presented as an authenticated first receipt or a formal forecast accuracy improvement.

## November 9 — distinct-run same-JST-day history guard (NONFORMAL, review only)

**Fail-closed advisory prevention, not an independent atomic lock.** In addition to rejecting Actions *rerun attempts* for the same run ID, Draft #1702 now proposes an extra step **before checkout and before candidate computation**. It reads the **public, read-only GitHub REST API** for runs of exactly `hole-pair-manual-gateway.yml`, filtered to `workflow_dispatch`, branch `main`, and the selected JST date converted into an exact UTC creation window. No workflow secret is required and no new Actions write permission or storage is introduced.

The gate requires the current run to be present in the returned history, a complete and unambiguous count **between 1 and 100**, unique positive run IDs, correct event/branch and in-window timestamps, and the current ID to be the **lowest/earliest ID** among that day's returned runs. Any earlier run (even a failed or canceled first attempt), missing self run, duplicate/malformed row, history beyond the checked limit, non-200/error/rate-limit/timeout or inconsistent count **fails the job without checkout**. It cannot bypass an earlier same-day run simply by supplying a fresh run ID. A new dispatch after a failed first attempt may therefore be blocked by design and requires manual evidence review rather than silent backfill.

**Offline test evidence:** [CI #42606109816](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42606109816) **SUCCESS**. The PR-only test executes the actual embedded guard with mocked HTTP responses: first current run succeeds; prior run, missing self, duplicate IDs, zero rows, more than 100 runs, out-of-day timestamps, incorrect run ID/attempt/repository and HTTP failure all fail closed. The real `capture` job is **SKIPPED**; no real network query of the new default-branch workflow, candidate collection or remote receipt was executed.

**Residual risk:** GitHub's workflow-run list is an eventually visible read API, **not** a transactional cross-run first-write lock. The list can be delayed or incomplete even with HTTP 200; a 30-day local artifact cannot prove an independently accepted first candidate. Workflow history may eventually be deleted or unavailable. Until an independently authenticated immutable receipt/lock, full official T−12 six-boat/120-odds originals, stable retention and per-race cross-batch quarantine are demonstrated, **formal pilot and confirmation eligibility remain zero**. Any approval to merge the gateway into main remains a separate manual security/operations decision; no merge, dispatch, Render or Cloudflare changes occurred in this Draft work.

Reference: GitHub REST documentation for workflow-specific runs, `event`/`created` filters, pagination and read-only public access: https://docs.github.com/en/rest/actions/workflow-runs

## November 9 — completeness-versus-idempotency decision (do NOT promote)

The manual capture driver frozen at #1685 commit `464d1641a5c7b981248ab17ba5bdc42b7bfa698b` enumerates **only `four_mode_forecasts/YYYYMMDD*.json` files already present in the fetched main commit at the instant of manual dispatch**. Its internally reconciled source-snapshot race-ID census is **not** a complete official schedule/day census. The same-JST-day subsequent-dispatch refusal intentionally prevents repeated source snapshots, even if forecasts for new races land in main **after** the first and only allowed run.

**Illustrative failure mode, not observed live:** If the first manual run sees race A at 10:00 JST, and race B's forecast appears at 12:00 JST, race B is not in that saved snapshot. A second dispatch would be rejected even though B has no candidate receipt. **Never turn a green capture job into a claim of complete-day capture, missingness-free data, or a formal 300-race denominator.** Missing later sources stay missing/unknown with an audit reason, never backfilled from outcome-known data.

**Mitigation in this Draft:** A local run provenance sidecar explicitly sets `entire_day_or_official_schedule_complete_verified=false`, separately from the true statement that the snapshot's **observed** race-ID census was internally reconciled. It also records `source_snapshot_forecasts_examined`. The sidecar generator now rejects a forged `entire_day_or_official_schedule_complete_verified=true` or inconsistency between the observed snapshot total and the internal census. PR synthetic tests execute those negative cases. No existing driver method, source file, candidate ticket or formal status is changed.

**History visibility hardening:** A newly queued workflow run may not yet appear in GitHub's run-list API. Before treating the current-run absence as final, the proposed gate now makes **at most three read-only requests** with up to two short pauses. It still rejects on missing current run after the bound, conflicting earlier runs, invalid records, rate limits or API failures. A successful GitHub list is **not** a server-side atomic unique constraint, tamper-evident first-acceptance witness or proof of official T−12.

**Reviewed simulation:** [CI #42607221962](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42607221962) **SUCCESS**: PR-only actual embedded sidecar and run-history gate simulations passed; the `capture` job was skipped. Tests include visibility on the second/third history read, rejection of malformed/missing/earlier runs, rejection of a false full-day flag and census-count mismatch. No live research capture, candidate artifact, official-source validation or remote first receipt occurred.

**Do not attempt to solve coverage by removing the duplicate guard unreviewed.** Before formal research, a separately reviewed design must use durable **per-race** first-write/receipt with independent, trustworthy time, repeated pre-cutoff observation windows as appropriate, a reliable official race-schedule universe and missingness accounting. Such a design may replace this deliberately restrictive one-dispatch-per-day safety proposal; it requires an explicit architecture/security review and would not retroactively validate today's Draft.

Current release decision: **HOLD**; #1701 and #1702 are Draft/unmerged; formal pilot 0/300, confirmation 0/300; no main/Render/Cloudflare/production changes.

## November 9 — per-race atomicity research test handoff (not an activation)

**Separate research Draft #1685** now includes two new *real SQLite WAL concurrency* checks in `research/test_hole_pair_first_receipt_sql.py`. [CI #42608065163](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42608065163) passed the research-only Cloudflare receiver offline validation; the prospective candidate-capture job was skipped. Changes were limited to test code; the candidate method, locked selector SHA, research Worker SQL, D1 schema and production code were unchanged.

The tests run the exact Worker-exported `INSERT_SQL` using **two independent SQLite connections** at the same time. They verify that conflicting candidate SHA256 values for the **same 12-digit race code** produce exactly one new receipt, while **two different race codes** each preserve their first write. The deterministic test clock simulates a valid pre-cutoff window. This is stronger evidence about SQLite per-race uniqueness under concurrent writes than an in-memory mock, but **NOT** a Cloudflare D1 deployment or authenticated independent first-acceptance proof.

**Architecture boundary:** The undeployed `research/hole_pair_first_receipt_worker.mjs` on #1685 is a per-race first-write *proposal*. This #1702 gateway still performs a separate one-manual-dispatch-per-JST-day check and **does not send candidate records to that Worker**; it is not a complete per-race capture service. Do not delete the daily gate or claim higher coverage without a separately reviewed end-to-end receipt path. If an operator later approves a per-race transport, it must be tested on real D1 under duplicate/conflicting concurrent HTTP requests, outage/retry, before/after true official T−12, retention and administrator independence before any formal admission.

**SHA pin separation:** #1685 now has test-only head `a7983f74bd80da57fc3460f48f63ab7667c1d71c`. The #1702 gateway intentionally continues to pin the already reviewed **unchanged runtime implementation** SHA `464d1641a5c7b981248ab17ba5bdc42b7bfa698b`. Do not silently repin a manually reviewed gateway because research tests changed; future repinning requires explicit security and reproducibility review.

**Evidence owners without duplicate modifications:** Official beforeinfo/exhibition six-boat originals, 120 distinct odds, race deadline and original T−12 chronology belong to separate read-only T−12 audit [#1694](https://github.com/ikst2512-eng/boat-edge-clean/pull/1694); #1685 owns hole-pair first-write prototype and research candidate validation; #1702 owns only the isolated manual gateway security review. A green CI in any one Draft is not a substitute for a single-race cross-system evidence chain.

### Gate-by-gate status (2026-11-09 JST)

| Gate | Evidence | Status |
| --- | --- | --- |
| SQLite same-race concurrent uniqueness | Real WAL threaded inserts, #1685 CI #42608065163 | Offline verified |
| SQLite distinct-race independent writes | Two independent race IDs, same CI | Offline verified |
| Cloudflare D1 deployed, live concurrent first-write | No deployed receiver or signed external witness | **Unverified** |
| Official same-race T−12 beforeinfo/exhibition six boats | Original-source independent chain not certified | **Unverified** |
| Official same-race T−12 all 120 trifecta odds | Original-source independent chain not certified | **Unverified** |
| Full day race universe / missingness | #1702 one-snapshot workflow not a complete official schedule | **Unverified** |
| 300 pilot + disjoint 300 confirmation | No formally eligible independent receipts | **0/300 + 0/300** |

**Decision remains HOLD.** Drafts #1685, #1694, #1701 and #1702 stay unmerged; no workflow dispatch, main change, production predictor/UI, Render or Cloudflare activation. Do not count simulator tests toward formal prediction accuracy.

## November 9 — tighten earliest manual dispatch to BOTH run ID and actual creation time (Draft, NONFORMAL)

**Problem found and fixed on #1702:** the previous duplicate-run guard identified the first same-JST-day manual dispatch solely via `min(GitHub run IDs)`. GitHub's workflow-run records also provide `created_at`, but the code was not cross-checking that time. An inconsistent/misordered run history could therefore give a misleading "first" decision. The revised guard requires **both** the current run to have the smallest observed run ID **and** its creation timestamp to be **strictly earlier** than every other run in the bounded same-day history. An equal-second/tied timestamp or an earlier timestamp attached to a higher ID is now fail-closed; neither a later attempt nor a conflicting observation can silently authorize collection.

The original bounded three-read visibility retry, 100-run cap, event/branch/date checks, explicit JST current-day acknowledgment, rerun prohibition, read-only permissions and GitHub Actions concurrency serialization remain intact. The PR-only tests execute the actual embedded checker with synthetic histories: a current first run with a later run is allowed by the local checker, whereas older run ID, higher-ID-but-earlier-time and same-second ties are rejected. **This remains advisory:** GitHub's eventually consistent list is not a transactional first-write lock or an authenticated independent candidate receipt.

**Actual CI:** [#42620373512](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42620373512) **SUCCESS** at #1702 code commit `6bcc9297da6a0ea9966767852c825f33a4f9fc2f`; `review_only` passed and `capture` was **SKIPPED**. No real manual dispatch, candidate freeze, independent receipt or source/original collector run occurred.

## November 9 — independently check the ACTUAL #1702 default-main workflow path

The old #1685 launcher checks a **different** workflow name (`.github/workflows/hole-future-pair-precommit.yml`) and therefore cannot answer whether this standalone #1702 manual gateway is installed. A new #1702 **PR-only read-only audit step** fetches the default `main` Git ref and inspects its immutable Git tree for:
- the **exact** target `.github/workflows/hole-pair-manual-gateway.yml`;
- competing `.github/workflows/hole-pair-manual-research-gateway.yml` (#1701) and `.github/workflows/hole-future-pair-precommit.yml` (#1685).

It emits a JSON status including the main SHA, exact path presence and competing paths. It fails closed if a competing gateway is already on main. It never runs any capture, changes main, supplies or requests secrets, or claims workflow-dispatch availability from a mere Git file presence; `github_actions_registration_or_manual_dispatch_verified=false` by construction. Checking actual enabled registration and permission through GitHub Actions would be a separate operator action **after** a separately approved main-only gateway change; it is not proven here.

**Actual latest head at audit:** [CI #42620490808](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42620490808) **SUCCESS**, `review_only` success and real `capture` skipped. Default main Git SHA `4bd080ad77778053575cf497c8a6b85b959ce173` had:
- `exact_gateway_file_in_default_git_tree=false`;
- `competing_gateway_files_in_default_git_tree=[]`;
- `registration_prerequisite_path_satisfied=false`;
- `github_actions_registration_or_manual_dispatch_verified=false`;
- `independent_first_remote_receipt_verified=false`, `official_t12_complete_verified=false`, `formal=false`.

**Decision still HOLD.** The new tests only tighten *theoretical* manual dispatch protections and show the precise default-main registration blocker. They do not change the pinned #1685 freezer commit `464d1641a5c7b981248ab17ba5bdc42b7bfa698b`, do not repair the one-manual-snapshot/day coverage limitation, and do not replace a real per-race atomic independent-first-receipt service. The #1694 owner handles original official beforeinfo/exhibition (all six boats), racelist and 120-way odds. The #1685 owner handles locked hole-pair selector and future 300 pilot + 300 untouched confirmation design. Both formal cohorts remain **0/300**. Do not merge either #1701 or #1702 automatically; no main, production, Render, Cloudflare, UI or model changes occurred.
