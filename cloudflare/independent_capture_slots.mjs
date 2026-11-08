// Shared PURE clock and planned-slot calculations only. No GitHub API URL,
// no credentials, no fetch, no workflow dispatch; safe for observer builds.
export const WORKFLOWS = Object.freeze({
  clean: 'clean-prospective.yml',
  four_mode: 'four-mode-prospective-capture.yml',
});
export const SCHEMA = 'CLOUDFLARE_CAPTURE_WAKEUP_DECISION_V1';
export const MINUTE = 60_000;
export const JST = 9 * 60 * MINUTE;

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

export function validateCronTick(scheduledTime, now) {
  if (!Number.isInteger(scheduledTime) || !Number.isFinite(now)) throw new Error('invalid_trigger_clock');
  const delay = now - scheduledTime;
  if (delay < 0 || delay > 90_000) throw new Error('late_or_future_cron_trigger');
  const stamp = new Date(scheduledTime);
  const h = stamp.getUTCHours();
  if (stamp.getUTCMinutes() % 5 !== 0 || stamp.getUTCSeconds() !== 0 || stamp.getUTCMilliseconds() !== 0 || !(h >= 22 || h <= 13)) {
    throw new Error('cron_outside_allowlist');
  }
}


// Default no-network observation path for first-time Cloudflare deployment.
// Validates the same trigger clock and computes local recovery windows without
// reading GitHub, requiring a PAT, or creating a workflow_dispatch.
export function observe({scheduledTime, now}) {
  validateCronTick(scheduledTime, now);
  const when = new Date(now);
  const eligible = Object.fromEntries(Object.keys(WORKFLOWS).map(kind => {
    const slot = eligibleSlot(kind, when);
    return [kind, slot === null ? null : new Date(slot + JST).toISOString().replace('Z', '+09:00')];
  }));
  return {
    schema: SCHEMA, mode: 'observe_only', action: 'no_network_no_dispatch',
    checked_at_jst: new Date(now + JST).toISOString().replace('Z', '+09:00'),
    scheduled_at_jst: new Date(scheduledTime + JST).toISOString().replace('Z', '+09:00'),
    eligible_slots_jst: eligible, github_history_checked: false,
    github_run_id_proven: false, new_forecast_saved_proven: false, formal: false,
  };
}

