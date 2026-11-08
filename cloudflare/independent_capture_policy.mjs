// GitHub-facing recovery policy: separate from pure cron/slot calculations.
// The zero-secret observer MUST NOT import this module.
import {SCHEMA, WORKFLOWS, ALLOWED_CRON, MINUTE, JST, plannedSlots, eligibleSlot, validateCronTick, observe}
  from './independent_capture_slots.mjs';
export {SCHEMA, WORKFLOWS, ALLOWED_CRON, plannedSlots, eligibleSlot, observe};

export const REPO = 'ikst2512-eng/boat-edge-clean';
const API = `https://api.github.com/repos/${REPO}/actions/workflows/`;
// Keep JSON payloads small: Cloudflare Workers Free cron has a 10 ms CPU cap.
const HISTORY_PAGE_SIZE = 30;
function validatedEvents(rows, expectedEvent, slot, now) {
  if (!Array.isArray(rows) || rows.length > HISTORY_PAGE_SIZE) throw new Error('github_history_missing_or_malformed');
  const parsed = [];
  for (const row of rows) {
    if (!row || typeof row !== 'object' || Array.isArray(row) || row.event !== expectedEvent ||
        !Number.isSafeInteger(row.id) || row.id <= 0 || typeof row.head_branch !== 'string' ||
        typeof row.status !== 'string' || typeof row.created_at !== 'string' ||
        !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(row.created_at)) {
      throw new Error('github_history_identity_invalid');
    }
    const created = Date.parse(row.created_at);
    if (!Number.isFinite(created) || created > now) throw new Error('github_history_chronology_invalid');
    if (row.head_branch === 'main') parsed.push({created, row});
  }
  // A full first page may hide an active/successful previous job: fail closed.
  if (rows.length === HISTORY_PAGE_SIZE && (!parsed.length || Math.min(...parsed.map(x => x.created)) >= slot - 120 * MINUTE)) {
    throw new Error('github_history_pagination_incomplete');
  }
  return parsed;
}

export function decide(schedule, manual, slot, now) {
  const s = validatedEvents(schedule, 'schedule', slot, now);
  const m = validatedEvents(manual, 'workflow_dispatch', slot, now);
  const direct = s.filter(x => x.created >= slot && x.created <= now);
  const recentManual = m.filter(x => x.created >= slot - 2 * MINUTE && x.created <= now);
  // Strict fail-closed native-queue protection: an old queued/running main
  // job can remain pending beyond two hours (e.g. a delayed Actions queue).
  // The former 120-minute cut-off made that pending original invisible to
  // the duplicate fence and a Cloudflare POST could displace CLEAN's
  // queue:single pending schedule. Never infer completed from age alone.
  // This only protects VISIBLE history; an as-yet-uncreated delayed
  // schedule remains a cross-provider NO-GO risk.
  const olderActive = [...s, ...m].some(x => x.created < slot && x.row.status !== 'completed');
  const base = {slot_jst: new Date(slot + JST).toISOString().replace('Z', '+09:00'),
    direct_runs_after_slot: direct.length, manual_runs_near_slot: recentManual.length};
  if (recentManual.length || olderActive) return {...base, action: 'no_dispatch', reason: 'previous_dispatch_or_active_job'};
  if (direct.some(x => x.row.status !== 'completed' || !['failure', 'cancelled', 'timed_out'].includes(x.row.conclusion))) {
    return {...base, action: 'no_dispatch', reason: 'direct_success_active_or_unknown'};
  }
  return {...base, action: 'eligible_for_dispatch', reason: 'direct_schedule_missing_or_explicitly_failed'};
}

function headers(token) {
  return {'Authorization': `Bearer ${token}`, 'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'BOAT-EDGE-CLEAN-CLOUDFLARE-WAKEUP/1.0'};
}

async function history(fetcher, root, event, token) {
  const url = `${root}/runs?event=${event}&per_page=${HISTORY_PAGE_SIZE}`;
  const response = await fetcher(url, {method: 'GET', headers: headers(token)});
  if (!response || response.status !== 200) throw new Error('github_history_http_error');
  const payload = await response.json();
  if (!payload || !Array.isArray(payload.workflow_runs)) throw new Error('github_history_missing_or_malformed');
  return payload.workflow_runs;
}

export async function execute({scheduledTime, now, token, fetcher, clock = () => now, onAccepted = () => {}}) {
  validateCronTick(scheduledTime, now);
  if (typeof fetcher !== 'function') throw new Error('fetcher_required');
  if (typeof onAccepted !== 'function') throw new Error('invalid_receipt_sink');
  const when = new Date(now);
  const eligible = Object.fromEntries(Object.keys(WORKFLOWS).map(k => [k, eligibleSlot(k, when)]));
  const result = {schema: SCHEMA, checked_at_jst: new Date(now + JST).toISOString().replace('Z', '+09:00'),
    on_time_cron_proven: false, new_forecast_saved_proven: false, formal: false, workflows: {}};
  if (Object.values(eligible).every(v => v === null)) {
    result.action = 'outside_recovery_windows_no_network';
    for (const kind of Object.keys(WORKFLOWS)) result.workflows[kind] = {action: 'no_dispatch', reason: 'outside_jst_recovery_window'};
    return result;
  }
  if (typeof token !== 'string' || !token.trim()) throw new Error('GITHUB_DISPATCH_TOKEN_required');
  const deferred = [];
  // Check BOTH eligible workflows' histories before ANY POST.
  for (const [kind, filename] of Object.entries(WORKFLOWS)) {
    const slot = eligible[kind];
    if (slot === null) {
      result.workflows[kind] = {action: 'no_dispatch', reason: 'outside_jst_recovery_window'};
      continue;
    }
    const root = `${API}${filename}`;
    const schedule = await history(fetcher, root, 'schedule', token);
    const manual = await history(fetcher, root, 'workflow_dispatch', token);
    const verdict = decide(schedule, manual, slot, now);
    result.workflows[kind] = verdict;
    if (verdict.action === 'eligible_for_dispatch') deferred.push([kind, root]);
  }
  for (const [kind, root] of deferred) {
    // Network I/O can outlive the tiny 2–3 minute recovery window. Re-check
    // the ACTUAL wall clock immediately before every dispatch (especially 22:28).
    const current = clock();
    if (!Number.isFinite(current) || eligibleSlot(kind, new Date(current)) !== eligible[kind]) {
      throw new Error('recovery_window_expired_before_dispatch');
    }
    // GitHub.com has supported return_run_details since 2026-02-19
    // (also with REST API version 2022-11-28). A 200 response is only
    // evidence that GitHub reports a created run, NOT a completed execution
    // or a new forecast. Do not poll/redispatch on ambiguous receipts.
    const response = await fetcher(`${root}/dispatches`, {method: 'POST',
      headers: {...headers(token), 'Content-Type': 'application/json'},
      body: JSON.stringify({ref: 'main', return_run_details: true})});
    // Legacy 204 can mean an actual run was created but its ID was NOT
    // returned. Fail closed without issuing another POST in this invocation.
    if (response?.status === 204) throw new Error('github_dispatch_accepted_without_run_details');
    if (!response || response.status !== 200) throw new Error('github_external_dispatch_not_accepted');
    let details;
    try { details = await response.json(); } catch {
      throw new Error('github_dispatch_run_details_missing_or_invalid');
    }
    const id=details?.workflow_run_id;
    const expectedApi=`https://api.github.com/repos/${REPO}/actions/runs/${id}`;
    const expectedHtml=`https://github.com/${REPO}/actions/runs/${id}`;
    if (!Number.isSafeInteger(id) || id <= 0 ||
        details.run_url !== expectedApi || details.html_url !== expectedHtml) {
      throw new Error('github_dispatch_run_details_missing_or_invalid');
    }
    result.workflows[kind].action = 'dispatch_run_id_returned_not_forecast_proof';
    result.workflows[kind].github_run_id_reported = id;
    // Record each validated 200 receipt independently so a later failure
    // cannot erase prior run IDs. No token, headers or source forecast data.
    // The ID has NOT been independently verified against a completed run.
    onAccepted({schema: SCHEMA, event: 'workflow_dispatch_accepted',
      workflow: kind, slot_jst: result.workflows[kind].slot_jst,
      request_started_at_jst: new Date(current + JST).toISOString().replace('Z', '+09:00'),
      github_run_id_reported: id, github_run_url_reported: expectedHtml,
      github_run_id_proven: false, new_forecast_saved_proven: false, formal: false});
  }
  result.action = 'checked_not_publication_proof';
  return result;
}

