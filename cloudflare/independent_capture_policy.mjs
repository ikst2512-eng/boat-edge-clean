// Pure independent wakeup admission policy. No Worker entrypoint, forecasts or IO without explicit fetcher.
// Refuses ambiguous GitHub history and never calls GitHub outside actual slots.
export const REPO = 'ikst2512-eng/boat-edge-clean';
export const WORKFLOWS = Object.freeze({
  clean: 'clean-prospective.yml',
  four_mode: 'four-mode-prospective-capture.yml',
});
export const SCHEMA = 'CLOUDFLARE_CAPTURE_WAKEUP_DECISION_V1';
const MINUTE = 60_000;
const JST = 9 * 60 * MINUTE;
const API = `https://api.github.com/repos/${REPO}/actions/workflows/`;
// Keep JSON payloads small: Cloudflare Workers Free cron has a 10 ms CPU cap.
const HISTORY_PAGE_SIZE = 30;
export const ALLOWED_CRON = '*/5 22-23,0-13 * * *';

function jstParts(instant) {
  const x = new Date(instant.getTime() + JST);
  return { dayStart: Date.UTC(x.getUTCFullYear(), x.getUTCMonth(), x.getUTCDate()) - JST,
    hour: x.getUTCHours(), minute: x.getUTCMinutes() };
}

export function plannedSlots(kind, instant) {
  if (!(instant instanceof Date) || !Number.isFinite(instant.getTime())) throw new Error('invalid_clock');
  const {dayStart} = jstParts(instant);
  const slots = [];
  if (kind === 'four_mode') {
    for (let h = 7; h <= 20; h++) for (const m of [7, 22, 37, 52]) slots.push(dayStart + (h * 60 + m) * MINUTE);
  } else if (kind === 'clean') {
    for (let h = 7; h <= 21; h++) for (const m of [4, 19, 34, 49]) slots.push(dayStart + (h * 60 + m) * MINUTE);
    for (const m of [4, 19, 28]) slots.push(dayStart + (22 * 60 + m) * MINUTE);
  } else throw new Error('unknown_workflow');
  return slots;
}

export function eligibleSlot(kind, now) {
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) throw new Error('invalid_clock');
  const slots = plannedSlots(kind, now);
  let slot = null;
  for (const candidate of slots) if (candidate <= now.getTime()) slot = candidate;
  if (slot === null) return null;
  const age = (now.getTime() - slot) / MINUTE;
  const {hour, minute} = jstParts(new Date(slot));
  if (kind === 'clean' && hour === 22 && minute === 28) return age >= 1 && age < 4 ? slot : null;
  const [minAge, maxAge] = kind === 'four_mode' ? [2, 5] : [5, 8];
  return age >= minAge && age < maxAge ? slot : null;
}

function validateCronTick(scheduledTime, now) {
  if (!Number.isInteger(scheduledTime) || !Number.isFinite(now)) throw new Error('invalid_trigger_clock');
  const delay = now - scheduledTime;
  if (delay < 0 || delay > 90_000) throw new Error('late_or_future_cron_trigger');
  const stamp = new Date(scheduledTime);
  const h = stamp.getUTCHours();
  if (stamp.getUTCMinutes() % 5 !== 0 || stamp.getUTCSeconds() !== 0 || stamp.getUTCMilliseconds() !== 0 || !(h >= 22 || h <= 13)) {
    throw new Error('cron_outside_allowlist');
  }
}

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
  const olderActive = [...s, ...m].some(x => x.created >= now - 120 * MINUTE && x.created < slot && x.row.status !== 'completed');
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
    const response = await fetcher(`${root}/dispatches`, {method: 'POST', headers: {...headers(token), 'Content-Type': 'application/json'},
      body: JSON.stringify({ref: 'main'})});
    if (!response || response.status !== 204) throw new Error('github_external_dispatch_not_accepted');
    result.workflows[kind].action = 'dispatch_accepted_not_forecast_proof';
    // GitHub returns only HTTP 204, not the run ID. Record each accepted POST
    // independently so a later failure cannot erase a partial-success receipt.
    // No token, request headers or forecast data is written to this log.
    onAccepted({schema: SCHEMA, event: 'workflow_dispatch_accepted',
      workflow: kind, slot_jst: result.workflows[kind].slot_jst,
      request_started_at_jst: new Date(current + JST).toISOString().replace('Z', '+09:00'),
      github_run_id_proven: false, new_forecast_saved_proven: false, formal: false});
  }
  result.action = 'checked_not_publication_proof';
  return result;
}

