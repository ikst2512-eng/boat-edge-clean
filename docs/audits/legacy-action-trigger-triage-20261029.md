# Legacy Actions: preliminary trigger/reference triage (2026-10-29)

Input: successful PR #199 audit, GitHub Actions run [40752272665](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/40752272665), artifact 12843463776, legacy tree `8ab7a7ae6c466059f98a1cdcca0195ffe7b1e6b8`.

**This classification is preliminary, not a deletion list.** The current scanner searches literal strings within workflow YAML; it does **not** parse the full `on` trigger tree, and in particular does not detect `push`, `pull_request`, `repository_dispatch`, reusable call semantics or external users. `no literal trigger matches` cannot be called inactive.

| Inbound textual reference | `workflow_dispatch` | `schedule` | `workflow_run` | Count |
|---|---|---|---|---:|
| Yes | Yes | Yes | No | 6 |
| Yes | Yes | No | No | 5 |
| Yes | Yes | Yes | Yes | 4 |
| No | Yes | No | No | 44 |
| No | Yes | Yes | No | 23 |
| No | No | No | No | 17 |
| No | Yes | Yes | Yes | 4 |
| No | Yes | No | Yes | 2 |
| **Total** | | | | **105** |

## First-pass review queue (17)
These files have no inbound filename substring match and no literal `workflow_dispatch:`, `schedule:`, or `workflow_run:` match. This **does not** mean they are unused, untriggered or removable.

```text
.github/workflows/v278-guarded-ui-queue.yml
.github/workflows/v279-relative-weights.yml
.github/workflows/v281-selected-race.yml
.github/workflows/v282-exhibition-evidence.yml
.github/workflows/v283-claim-safety.yml
.github/workflows/v284-results-states.yml
.github/workflows/v286-retire-legacy-bootstrap.yml
.github/workflows/v287-six-boat-beforeinfo.yml
.github/workflows/v288-official-start-html.yml
.github/workflows/v289-official-source-visibility.yml
.github/workflows/v290-missing-freeze-funnel.yml
.github/workflows/v291-freeze-funnel-mobile.yml
.github/workflows/v292-source-wake-safety.yml
.github/workflows/v295-retry-evidence.yml
.github/workflows/v296-retry-pair-integrity.yml
.github/workflows/v302-v254-regression.yml
.github/workflows/v307-ui-integration-gate.yml
```

## Review gates per workflow
- Confirm full YAML trigger set, including `push`, `pull_request`, `workflow_call`, `repository_dispatch`, `workflow_dispatch` and cron.
- Search scripts, documentation, external integrations, and API dispatch consumers for invocation and generated artifact dependencies.
- Inspect actual recent and historical run activity, not just source text.
- Establish exact CLEAN replacement and independent evidence/data parity; retain immutable original source, inputs and outputs.
- Explicitly record disposition (keep / migrate / candidate for retirement), rollback, reviewer, and validation. Never delete on automated counts alone.

No legacy repository modification or deletion is included.
