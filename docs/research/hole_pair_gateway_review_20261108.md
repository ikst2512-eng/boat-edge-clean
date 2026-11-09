# Hole-pair manual research gateway — REVIEW ONLY (2026-11-08 JST)

**NOT DEPLOYED. This is a separate Draft PR and is NOT on main. Do not merge automatically.**

## Purpose and separation

The large research-only Draft PR [#1685](https://github.com/ikst2512-eng/boat-edge-clean/pull/1685) has an otherwise reviewed nonformal candidate freezer, manual-only driver, evidence validators and offline tests, but its `.github/workflows/hole-future-pair-precommit.yml` is not registered on the default branch. GitHub's `workflow_dispatch` requires default-branch registration. Merging the whole multi-file study solely to enable a trigger would unnecessarily widen the main change surface.

This **standalone, single-workflow entry point** is proposed for manual review as a *possible future* read-only Actions gateway. It does not itself deploy anything while Draft/unmerged. It is not a new periodic job, does not modify the production predictor or existing collector, does not touch Render/Cloudflare, does not create a repository commit and does not enable promotion to formal accuracy.

## Exact security boundaries

- `on: workflow_dispatch` **only**. No `schedule`, `push` or `pull_request` capture. Job checks `github.ref == 'refs/heads/main'`; branch-selection cannot bypass.
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
