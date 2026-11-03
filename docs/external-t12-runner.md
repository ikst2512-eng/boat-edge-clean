# External T−12 three-original research runner (not production forecasts)

This is a **prepared, not provisioned** alternative to GitHub Actions scheduled
triggers. The existing 2026-11-03 GitHub scheduled observations showed zero
scheduled runs in the 16:26 JST independent API inventory, despite successful
PR-triggered evidence captures. No conclusion is drawn about the scheduler's
specific internal failure cause.

## What the runner does

`scripts/run_external_three_t12.py` calls the existing research-only
`observe()` function on an explicitly supplied **current JST race code**.
That function independently derives the official deadline from original
beforeinfo JSON and requires all three originals (official racecard,
beforeinfo and trifecta odds) to be received before T−12. The runner then
commits the research report and available raw originals to a **dedicated
non-main** evidence branch through the GitHub Git API.

The Git tree update is one non-force commit with SHA-verified blobs.
It does not alter `main`, publish official forecasts, or enable
`forecast_usable`, `full_t12_source_certified` or `t12_eligible`.
Failed evidence uploads make the runner fail, not report success.
The durable Git commit is separate from Render's ephemeral filesystem.

## Prerequisites before provisioning a Render Cron Job

1. Verify a dedicated branch named `research-t12-external-evidence` exists.
2. Provide a GitHub fine-grained token with **Contents: Read and write**
   limited to this repository, preferably through Render's secret
   environment variable `GITHUB_EVIDENCE_TOKEN`. Do not print it.
   Branch protection/restriction to the evidence branch is recommended.
3. Assign an explicit target race code and a UTC schedule sufficiently early
   before the **officially verified T−12 cutoff**, accounting for build/start
   delays and 3 official HTTP downloads. There is **no automatic race
   selection or timing inference** in this runner.
4. In Render, create a **separate Cron Job** (Python runtime, repo `main`,
   Singapore), with a one-day UTC cron expression. Example for a known
   16:35 JST race with T−12 at 16:23 JST: `0 7 3 11 *` runs at 16:00 JST,
   but **the month/day cron repeats in future years**. The `observe()`
   current-JST-race-day guard stops mismatched target dates.
5. Build command (no external Python requirements for this runner):
   `python -m compileall -q scripts`
6. Start command example, supplying a race chosen and checked by operator:
   `python -m scripts.run_external_three_t12 --race-code 202611030104 --repo ikst2512-eng/boat-edge-clean --branch research-t12-external-evidence`

**Do not create the Render Cron Job without explicit approval of recurring
charges.** Render charges for Cron Jobs, with a currently documented $1/month
minimum per service. The existing Free Web Service is not an equivalent
reliable timer: it may spin down after inactivity.

## Required acceptance tests

- GitHub Actions: `test_run_external_three_t12.py` passes with mocked Git
  blob SHA, non-force commit, guard against main writes, and missing originals.
- Render Cron Jobs Run history must show actual start time, logs and exit code.
- Dedicated evidence branch must contain a single commit with report,
  six original files and original manifests for a complete source capture.
- Independently re-audit the saved Git bytes using existing three-source
  auditors. A git commit proves durable storage, **not** official
  3-original completeness or final entry.
- Repeat on a different racing day before considering this fallback reliable.
  Do not open production forecast gate on the basis of one successful run.

This preparatory commit does not create a Render service, token, schedule, or
external Git archive. Those outcomes require separate, observed actions.
