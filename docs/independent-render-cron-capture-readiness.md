# Independent capture wakeup readiness (not yet deployed)

Status: **code prepared only**. No Render Cron Job is created or billed by this PR. GitHub's existing cron, append-only forecast sources, original 4-mode evidence and legacy system remain unchanged.

## Why an independent scheduler is needed

On 2026-11-04 JST, six late-night GitHub Actions schedule slots (CLEAN prospective 22:04/22:19/22:28 and four-mode watchdog 22:13/22:29/22:44) were not observed in GitHub's run-history API through 22:57 JST. Triggered `workflow_dispatch` or `push` jobs did run but **do not certify the corresponding schedule slot or a new forecast**. GitHub publicly documents that `schedule` events can be delayed or dropped under load.

## Optional independent Render cron service (approval and secret required)

This plan introduces a **new paid** Render Cron Job, not a modification of the existing Free web service. Render states a **$1 per month minimum charge for each cron service**, plus any applicable runtime usage. Obtain explicit owner billing approval first. Do not create this service automatically in CI.

The source repository already contains a separate, research-only four-mode Render dispatch helper. For a **single combined** independent wakeup service, use the newly tested module:

- Repository: `https://github.com/ikst2512-eng/boat-edge-clean`
- Branch: `main`
- Runtime: Python 3.12 or another current supported Python 3
- Build command: `python -m compileall -q scripts/render_capture_wakeup.py`
- Start command: `python -m scripts.render_capture_wakeup`
- Single UTC schedule: `*/5 22-23,0-13 * * *` (the program itself permits only real eligible collection slots)
- Compute tier: minimal supported Render cron compute, subject to billing approval
- Secret environment variable: `GITHUB_DISPATCH_TOKEN`, a **dedicated fine-grained GitHub token** limited to `ikst2512-eng/boat-edge-clean` with Actions workflow read/write authorization. Create/configure it privately in Render; never put it in Git or logs.

Always keep the current GitHub schedules and watchdog running as independent secondary checks; do **not** replace them with this service.

## Safety model

The external job is a *wakeup only*. It does not download, model, score, overwrite, rewrite timestamps, or push any forecasts. It calls `workflow_dispatch` for exactly these existing main-branch workflows after checking separately filtered `event=schedule` and `event=workflow_dispatch` histories:

- `clean-prospective.yml` — normally 6 minutes after each fifteen-minute slot, plus 22:30 JST for the special 22:28 last slot;
- `four-mode-prospective-capture.yml` — normally 3 minutes after each fifteen-minute slot through 20:52 JST.

The script prevents duplicate dispatch if a previous main/manual dispatch was already made in or near the slot, or if a direct scheduled job succeeded or is still active. Unknown/ambiguous API metadata, pagination ambiguity, missing token and dispatch rejection **fail closed**. The existing Actions workflows retain their own restrictive T−12, immutable first-add, verification, 90s buffer and independent ledger gates. A "dispatch accepted" response is **not** proof of a saved prediction, third-rate ledger preservation, source age, model accuracy, or scheduled-event delivery.

## Operational acceptance before a reliability claim

Do not claim the external scheduler has solved the problem until actual Render runs show both wakeup timestamps and GitHub dispatch run IDs, followed by independent GitHub main first-add SHA, source receipt, pre-T−12 cutoff, publication and ledger replay verification on a new JST day. In the event of no published eligible race, successful execution can legitimately produce **zero** new predictions, but that still is not a first-add success.

No production service or billing change, no auto-creation, no broader GitHub token and no legacy writer shutdown is authorized by this PR. See Issue #708.
