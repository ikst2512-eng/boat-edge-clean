# Old-site 17 workflow trigger verification — 2026-10-29

Scope: immutable reading of `ikst2512-eng/boat-edge` main workflow definitions, following merged CLEAN PRs #199, #200 and #202.

**Finding: All 17 of the earlier 'no matching trigger' review-queue workflows actually declare both `on.push` and `on.pull_request`.** The preceding reference audit checked only literal `workflow_dispatch:`, `schedule:`, and `workflow_run:`, and therefore its zero-trigger subgroup cannot be used to infer inactivity.

| Legacy workflow | Actual configured triggers | Disposition |
|---|---|---|
| `.github/workflows/v278-guarded-ui-queue.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v279-relative-weights.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v281-selected-race.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v282-exhibition-evidence.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v283-claim-safety.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v284-results-states.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v286-retire-legacy-bootstrap.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v287-six-boat-beforeinfo.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v288-official-start-html.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v289-official-source-visibility.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v290-missing-freeze-funnel.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v291-freeze-funnel-mobile.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v292-source-wake-safety.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v295-retry-evidence.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v296-retry-pair-integrity.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v302-v254-regression.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |
| `.github/workflows/v307-ui-integration-gate.yml` | `push`, `pull_request` (path filters) | KEEP pending replacement/runtime check |

All sampled definitions include path filters. Some gates explicitly check formal lock, immutable source evidence, original-source visibility, parser correctness, pre-result constraints, or UI regression. They must not be removed solely because they are not called by other workflow files.

## Verification coverage and limitations

- Source YAML fetched directly for each of the 17 files from old repository main: 17/17.
- Configured triggers: `push` and `pull_request` for 17/17.
- Verified execution history for each workflow: **not established**. An available recent-run collection did not contain matching names in its returned page; that does not prove lack of historical runs.
- Equivalent CLEAN protections/test coverage: **not yet established**. Naming similarity alone is insufficient.
- Deletions permitted: **zero**.
- Old repository changes: **none**.

## Next per-file gate

1. Match workflow ID to history (latest successful/failed run and whether source path still changes).
2. Read all `run`, `uses`, test names, produced artifacts and referenced files.
3. Identify explicit CLEAN code/test equivalent and demonstrate equivalent guard or data checks.
4. Ensure archival evidence, checksums, rollback and no risk to official Fresh or independent CLEAN forecast/results.
5. Only then propose a retirement PR with a separate approval review.

This report supersedes any interpretation that the 17 files were inactive simply because they lacked three scanned trigger strings.
