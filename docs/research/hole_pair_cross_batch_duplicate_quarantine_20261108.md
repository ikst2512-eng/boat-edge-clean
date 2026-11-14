# 2026-11-08 Hole mode: cross-batch duplicate / conflict quarantine (NONFORMAL)

**Draft PR #1685, research-only. No live receiver, no new candidate collection, no model, collector, main, Render, UI, schedule or deployed Cloudflare change.**

## Concrete risk

An individually consistent GitHub Actions artifact only proves membership *inside its own source-main snapshot*. If the same 12-digit race code appears in multiple overlapping manual/rerun artifacts (or different pinned main snapshots), naïvely adding counts would duplicate a race, potentially repeat a winning ticket, and incorrectly advance the planned first 300 pilot / next 300 confirmation boundaries. Distinct candidate bytes for the same race cannot be selected post hoc.

## New read-only audit contract

- `research/hole_pair_cross_batch_roster.py` accepts an explicit list of observed research artifact manifests. Each observation requires `run_id`, `artifact_id`, reported artifact observation UTC timestamp, exact canonical-JSON manifest SHA-256, and its matching frozen manifest. **This is a digest of the canonicalized manifest content, not a signature, and not automatically the ZIP or original pretty-JSON file hash.**
- Each manifest independently passes the previously implemented exact `source_forecast_codes` / `excluded_race_codes_by_reason` inventory reconciliation, including frozen policy/Top5/digest, preserved original pair coverage, and its pinned main commit. Conflicting counts, forged formal flags, missing/extra race IDs and duplicate IDs fail before aggregation.
- Sort observed artifacts by their *reported* observation timestamp, then GitHub run/artifact IDs as stable tie-breakers. Chronology remains **not independently attested**, and is never treated as evidence of true *first* remote receipt.
- Repeated race code with **identical complete candidate record bytes**: retain one nonformal candidate only; report extra identical frozen copies in `identical_frozen_repeats_not_added_to_denominator`.
- Repeated race code with **different complete candidate record bytes** (even if tickets match but freeze clock differs): quarantine the entire race from apparent improvement counts.
- First observed exclusion followed by candidate promotion: quarantine rather than retroactively replacing the excluded event. Early frozen record followed by a later excluded audit remains one **unverified reference**, never a formal eligible record. Mutually inconsistent statuses/reasons at the same reported first timestamp: quarantine, not arbitrary run-ID winner.
- Claimed artifact observation before its local candidate creation: reject as an impossible timeline. Conflicting manifests or run/artifact identifiers fail closed.
- No outcomes or official odds are read. The tool only returns nonformal race counts, conflict details, and per-race coverage. All formal pilot/confirmation counts remain **zero** by design.

## Limits and next activation gates

This is a ready-to-use **pure offline verifier**, not an operational cross-run ingestion job. The current research workflow exists on the PR branch but **not default main**, hence ordinary PR CI does not launch the result-blind future candidate freeze/upload. The artifact observation timestamp is not independently signed; existing Cloudflare D1 Worker remains an **undeployed prototype**. The independent candidate *first receipt*, official beforeinfo/exhibition six boats, 120 three-way odds, official deadline, and result certainty remain separate formal gates, all unverified. Cross-batch code does not prove scheduled race-day completeness. Do not use inspected Nov 6–8 races in the future predeclared confirmation sample.

The preregistered pilot first 300 *formally eligible*, then next untouched 300 confirmation stays unchanged. The output `unique_frozen_unverified` **must not be substituted** for `formally_eligible`, which is always 0 in this offline audit.

## Verified CI

- New cross-batch synthetic unit tests **19/19 passed**: repeated identical candidates, changed freeze bytes, first exclusion then replacement, later exclusions, different main commits, invalid timestamps, impossible artifact chronology, same-time conflicting dispositions/reasons, bad digest, forged formal flags, duplicate GitHub artifact IDs, invalid source roster, empty snapshot.
- [GitHub Actions #42479012746](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42479012746) completed **success** on research head `63983f298439c1fbef3d1c93c6a870c1ee770751`. Existing policy Python tests 49, SQLite tests 9, D1 receipt-chain 10, snapshot inventory 15 and launch-readiness 8 passed; the Node receiver suite also passed. Freeze and candidate artifact upload steps were **skipped** on this PR event. `DISPATCH_PREREQUISITE False` remains.
- This new file is documentation only after the successful code-head CI. Research PR remains Draft and unmerged; main is unchanged and automatic merge prohibited.
