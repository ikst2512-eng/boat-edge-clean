# Cloudflare research handoff: CLEAN post-push remote receipt gap

**Status (2026-11-09 JST): SOURCE-VERIFIED GAP, NOT A LIVE DATA LOSS INCIDENT.**
This research does not modify main, Render, native GitHub capture/CI schedules, or a Cloudflare deployment. PR #1697 stays Draft; independent Cloudflare recovery remains source-hard-locked.

## Same-head source comparison

The actual `.github/workflows/clean-prospective.yml` native publisher performs:

1. Validate new immutable candidate paths, source/cutoff timing, hashes, and pre-commit/commit chronology.
2. `git fetch origin main` and `git rebase origin/main` **before push**; recheck remaining 90s cutoff buffer.
3. On `git push origin HEAD:main` success, dispatch `clean-prospective-evaluation.yml` and exit success.

**Gap:** In that immediate push success path, CLEAN does **not** re-fetch remote `main`, prove `git merge-base --is-ancestor HEAD FETCH_HEAD`, or emit a durable record linking the pushed commit SHA and newly added immutable forecast paths to a specific run. The separately dispatched evaluation workflow may independently audit those facts; its dispatch is not itself a stored first-add receipt. This finding must not be paraphrased as proof of a failed CLEAN push.

In contrast, `.github/workflows/four-mode-prospective-capture.yml` after successful push **does**: `git fetch origin main`, `git merge-base --is-ancestor HEAD FETCH_HEAD`, capture `git rev-parse HEAD` and the count of newly added forecast paths, and write `four-mode-evidence/publication.json` with `outcome:pushed_to_main` and `commit_sha`. This is stronger *local publication evidence*, **not** independent GitHub server-side first-seen provenance, not a source-file SHA certificate, and not official T−12 certification.

## Machine-verifiable safety check (Draft only)

`cloudflare/native_publication_receipt_lab.mjs` reads raw native workflow YAML as text. It identifies the success branch *after* `if git push origin HEAD:main; then` up to its `exit 0`, and separately reports whether that branch contains (a) fetch remote main followed by ancestry confirmation, (b) published HEAD SHA capture, (c) a local publication receipt artifact with `commit_sha`. The output explicitly keeps `remote_publication_independently_observed:false`, `publication_immutable_first_add_proven:false`, `formal_t_minus_12_proven:false`, and `cross_provider_recovery_release_approved:false`, even for four-mode.

Tests inspect both **real GitHub YAML files**, assert the known CLEAN-vs-four-mode difference, and reject illustrative checks placed before push, after success exit, in reverse order, or missing SHA metadata. The source audit now requires actual shell fetch/ancestry command lines, an assigned Python `sha = subprocess.check_output(["git","rev-parse","HEAD"], ...)` result, and a `target.write_text(json.dumps(...))` receipt with `"commit_sha": sha` and the expected publication path. Comment-only lines, `echo`-quoted command strings, and naked `git rev-parse HEAD` output must NOT count. This is a conservative string-based source contract check, **not** a YAML interpreter or a runtime GitHub observation. Any native workflow changes should trigger a fresh owner review and must not be counted as certification from a passing static fixture.

## Work for publisher owners in a separate reviewed Draft

**CLEAN publisher owner:** add post-success remote-main confirmation, exact new-commit SHA and per-path/hash receipt; verify the recorded commit remains reachable and is a genuine first-add after rebasing/parallel commits. Preserve existing write-once validation and the T−12 receipt window. Mark ambiguous `git push` accepted/remote verification unavailable cases `outcome:unknown`, **never automatically retry under a false assumption that no publication occurred**. Retain a permanent run→commit→new immutable forecast path→cutoff/source receipt chain. Do not edit the active publisher from Cloudflare PR #1697.

**Four-mode publisher owner:** review existing `publication.json` for a full per-path blob SHA list and independent remote source of the first-add server time. Ancestry confirmation alone does not show every file's first introduction nor rule out later cutoff expiry; require an independent post-publication audit rather than assuming any successful local JSON is formal.

**Both publisher and Render owners:** enumerate all schedules, retries, fallback writers and native `queue:single`/ `queue:max` interactions. Simulate *both orders* of delayed native schedule and Cloudflare rescue. A Cloudflare-only SQLite claim and 200 response run ID cannot coordinate native GitHub events or stop queued original CLEAN work from being displaced.

## NO-GO is unchanged

The hard-locked recovery Worker must remain unable to dispatch even if `CLOUDFLARE_DISPATCH_ENABLED="true"` and PAT are present. The sole candidate for eventual owner-approved cloud deployment is the isolated, credential-free Observer. Real 24h Cloudflare logs/Free CPU <=10ms, cross-provider idempotent publication, actual GitHub job outcome, independently verified first-add SHA, and official T−12 original evidence remain unproven. No main merge/production change/auto-merge is authorized.


**Review boundary:** This matcher is intentionally conservative, not a shell/Python control-flow interpreter. A new publisher implementation using equivalent but different commands should initially fail source-contract review, not be automatically approved. Source-level success may still be unreachable at runtime, and remote first-add remains unverified without independent GitHub evidence.
