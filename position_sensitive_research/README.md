# Position-sensitive forward research candidate ledger

**Research-only, empty bootstrap.** This separate branch was created on 2026-11-08 JST from the existing main history to prepare candidate-only append-only evidence for Draft PR #1698. It is NOT main, not a production feature, and not a backfill of the Nov-05–08 development samples.

## Candidate namespace and immutable policy

Each predeclared future race may have exactly one candidate file at `position_sensitive_research/YYYYMMDDJJRR.json` (race code), using the already-frozen selector and `FOUR_MODE_POSITION_SENSITIVE_LOCAL_FREEZE_V1` JSON from Draft PR #1698. This README is **not** a candidate receipt, and does not establish a candidate record.

- Allowed dates: future race deadlines **2026-11-09 to 2026-12-31 JST**; never include 2026-11-05–08.
- Original unmodified V2 `four_mode_forecasts/<race>.json` must be validated independently, including the unchanged model dependency blob IDs. The candidate must be calculated **before** T−12 and never use results or retrospective payouts.
- Create each file **once only**. Missing file -> atomic create-only GitHub Contents API call with no existing-file SHA; existing file with identical bytes -> no-op/readback; mismatch -> fail. Never force-push, update, delete, rewrite, rebase or retroactively backfill a candidate.
- Obtain a **separate independently witnessed remote first-receipt** of the exact candidate bytes before T−12. Git commit timestamp, local freeze timestamp, GitHub API Contents GET/server Date of an already existing object and successful readback **do not alone prove first remote receipt**.
- Record complete schedule/dispatch/rescue run inventory and authenticate official beforeinfo, 6 exhibition entries and all 120 odds before any formal-eligibility claims. Missing results reserve the original ordered race slot.
- All captured records remain provisional. No model promotion without independently verified future 300 pilot + 300 confirmation same-race Top1/3/5/10 and manual review. Narrow Top10 is N/A (only five candidate tickets).

## Current status

No candidate files added at bootstrap. This branch is only a storage namespace, **not** a running capture system. No GitHub Actions schedule is installed, no independent first remote receipt has been collected, and formal eligible candidate races = **0**. Do not use this README or a branch creation event as prediction evidence.

Owner: isolated position-sensitive 2nd/3rd conditional-order research, Draft PR #1698. Do not mix with all-mode accuracy PR #1693, hole-mode work or official T−12 collection work.
