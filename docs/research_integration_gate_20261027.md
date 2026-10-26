# Research-only integration gate — 2026-10-27

Scope: draft PR #35 is based on draft PR #20, and includes source/provenance changes from draft PR #23. This is **not a production release** and is **not official Fresh**.

## Verified

- PR #35 head: `90bacd2d1d18debb7e5c35d2085e516cea30b3ae`
- GitHub Actions run `40382282070` (`Research forecast checks`) completed **success** for that head.
- This run's `research-tests` job reported success for both the research model/persistence/daily collection step and the isolated audit regression step.
- PR #35 targets `research/audit-prospective-score-20261027`, **not** `main`.

## Not verified / blocking

- No independent authenticated remote receipt for pre-cutoff forecast submission.
- No independently authenticated official-results dataset and reviewer approval of an exact attestation manifest.
- No validated real-race Top1/Top3/Top5/Top10 performance. Synthetic tests cannot establish prediction accuracy.
- Research model provenance covers `research_model.py` bytes only; runtime dependencies and remote CSV response authenticity are not fully attested.
- Both PR #20 and PR #23 remain separate Draft proposals. Do **not** merge them independently into `main` and assume the integration was tested.

## Safe sequencing

1. Review this integration branch against both constituent Draft PRs and confirm all research-test steps remain present.
2. If changes are made, rerun CI on the resulting **new** head SHA; the run above proves only its recorded SHA.
3. Independently verify external receipt, source provenance and official outcome evidence before publishing scored results.
4. Keep research output labelled unvalidated and isolated from production/formal Fresh until a separately reviewed release explicitly authorizes a merge.
5. Never backfill missing evidence into the historical snapshot collection to declare retrospective accuracy.

No changes to the old `boat-edge` repository.
