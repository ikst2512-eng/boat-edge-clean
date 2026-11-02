# Render four-mode collector wakeup (deployment checklist)

This is an **independent scheduler** for the existing GitHub Actions capture, not
a new forecaster. It does not edit saved predictions on Render.

Before provisioning a paid cron service, explicitly approve its billing and
configure a GitHub fine-grained personal access token in **Render only**:
- Repository: `ikst2512-eng/boat-edge-clean` (selected repository)
- Repository permission: **Actions: Read and write**
- Store in the Render cron service environment variable
  `GITHUB_DISPATCH_TOKEN`. Never commit, print or paste it in chat.

Suggested Render configuration:
- Name: `boat-edge-four-mode-wakeup`
- Workspace: `My Workspace`
- Repository: `https://github.com/ikst2512-eng/boat-edge-clean`
- Branch: `main`
- Runtime: Python
- Region: Singapore
- Build command: `python -m compileall -q scripts/render_four_mode_dispatch.py scripts/four_mode_watchdog_policy.py`
- Start command: `python -m scripts.render_four_mode_dispatch`
- UTC schedule: `7,22,37,52 22-23,0-11 * * *`
  (JST 07:07–20:52, four checks per hour)

Choose a paid plan only after checking the current Render price and securing approval.

After configuring the secret, verify **in Render logs** that the job produced
`dispatch_accepted_not_publication_proof` or `no_dispatch`. Then check
the target GitHub Actions run, its `publication.json`, and the new first-add
commit on remote main. A dispatch acknowledgement is **not** publication proof.

No scheduled event provider guarantees exact-minute execution. This runner
reuses the existing 27-minute healthy-run gate and 20-minute fallback cooldown.
