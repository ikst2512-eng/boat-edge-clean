# 2026-11-09 22:00 JST — source-clock provenance and green/skip evidence

This is a read-only **existing Draft #1694** audit handoff; no current-candidate model or production cron changes. Immutable GitHub main examined: `4bd080ad77778053575cf497c8a6b85b959ce173`.

## Official two-source collector schedule run creation — current Nov 9 completed window

GitHub API read-only native `GET /actions/runs?event=schedule&created=2026-11-09&per_page=100` yielded exactly **41 total schedule events across all workflows** and exactly **1 event=schedule** run whose exact `path` equals `.github/workflows/research-live-preview-evidence.yml`: [#42567310743](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567310743), created **2026-11-09 14:26:15 JST**, conclusion success. This is a count of **run creations**, not count of HTTP attempts, source snapshots or completed T−12 predictions. The configured 09:00–21:55 JST five-minute schedule is 13 hours × 12 = **156 nominal slots**. Observed **1/156** run-creation count ratio (0.64%); 155 is a count difference only, **NOT** proved 155 skipped GitHub slots, 155 source HTTP failures, or any causal diagnosis. #1699 owns trigger repair.

## A green job that captured no odds

[GitHub Actions run #42620665089](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42620665089), created 2026-11-09 **21:52:50 JST**, had conclusion **success**. Read-only inspection of the real completed `live-odds` job **129171644815** logs shows:

`LIVE_ODDS_TRIGGER_GATE {"collect": false, "source": "workflow_run", "upstream_event": "pull_request", "upstream_run_id": 42620635468, "direct_schedule_guard": "not_applicable"}`

It archived a *`live-odds-skipped`* artifact (GitHub artifact **13675347669**). No successful official odds 120-original HTTP evidence is established by this run. This is **successful intentional suppression**, not a source acquisition. Do not promote by green CI conclusion or artifact existence; no formal T−12 cert.

## A truly failed late-day CSV probe, not necessarily transport failure

[Run #42619773299](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42619773299), event schedule on Nov9 **21:46 JST**, failed its predeadline preview gate after observing **132 rows each** for `tkz`, `stt`, `sui`, with `eligible_future=0` in all three. Logged terminal `SCHEDULED_PREVIEW_NO_MATCHED_PREDEADLINE_RACES`. It is **not** valid to transform the absence of remaining future races into an HTTP transport outage or a valid archived T−12 original.

## Independent source ZIP clock versus self-recorded original receipt

In the already-existing immutable three-race proof chain, the new per-race read-only report now explicitly preserves three noninterchangeable clock tiers:

| Historical proof, three fixed races | Count |
|---|---:|
| Collector-recorded original source receipt by official T−12 | **3/3** |
| Independently observed GitHub *SOURCE ZIP* server publication by T−12 | **2/3** |
| Independently verified first remote *FORECAST Git* acceptance | **0/3** |

The Nov3 桐生12R third original is real but pre-exhibition (0/6) and has no independent GitHub SOURCE archive publication before cutoff. Nov9 宮島10R/びわこ10R have 6/6 + 120 and published pair ZIP before cutoff, but **neither has a same-race official racelist original** and both existing model forecasts predate the official source receipts. Thus the first unmet source gate per race is **exhibition complete missing 1/3**, **same-race racelist missing 2/3**. Later model/original-consumption, first remote forecast acceptance, and official final entry gates are also all unverified; first blocker is a triage label, not the complete list.

The separate model-input consumption/final entry guards remain zero, and **formal certifications 0, formal accuracy denominator undefined**. Unproved remote time is **not** zero actual latency; it is **not evidenced**. Avoid source-to-prediction stitching or retrospective replacement of frozen files. Keep Draft; no automatic merge.
