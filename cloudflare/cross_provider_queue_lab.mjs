// RESEARCH-ONLY, OFFLINE counterexample lab for GitHub Actions concurrency.
// No import from any live Worker. No API access, dispatch, recovery or secrets.
// Models the documented queue rule only; not GitHub run-time scheduling,
// source publication, transport delays or an actual incident.
export const RISK_SCHEMA = 'BOAT_EDGE_CROSS_PROVIDER_CONCURRENCY_COUNTEREXAMPLE_V1';
const MAX_WAITING = 100;

export function simulateGitHubConcurrency({queue, running, arrivals}) {
  if (!['single', 'max'].includes(queue) || !Array.isArray(arrivals) ||
      (running !== null && (typeof running !== 'string' || !running))) {
    throw new Error('invalid_queue_simulation');
  }
  const pending = [], canceled = [], trace = [];
  let active = running;
  for (const name of arrivals) {
    if (typeof name !== 'string' || !name.trim() || name.length > 150) {
      throw new Error('invalid_arrival_identity');
    }
    if (active === null && pending.length === 0) {
      active = name;
      trace.push({event:name,action:'started'});
      continue;
    }
    if (queue === 'single') {
      if (pending.length) {
        const replaced = pending.shift();
        canceled.push(replaced);
        trace.push({event:name,action:'replaced_pending',replaced});
      } else {
        trace.push({event:name,action:'pending'});
      }
      pending.push(name);
    } else if (pending.length >= MAX_WAITING) {
      canceled.push(name);
      trace.push({event:name,action:'queue_full_canceled'});
    } else {
      pending.push(name);
      trace.push({event:name,action:'pending'});
    }
  }
  return {
    schema:RISK_SCHEMA, queue, running:active, pending, canceled, trace,
    actual_github_run_evidence:false,
    verified_cross_provider_idempotency:false,
    production_dispatch_safe:false,
  };
}

// Read-only summary of the *currently inspected* native workflow configuration.
// These strings are intended to be asserted against the repository YAML by
// tests; a future YAML change requires a new evidence-backed risk review.
export const CURRENT_NATIVE_QUEUES = Object.freeze({
  clean:Object.freeze({
    concurrency_group:'clean-prospective-capture',
    queue:'single',
    cancel_in_progress:false,
    cloudflare_joins_same_group:true,
  }),
  four_mode:Object.freeze({
    concurrency_group:'four-mode-publication',
    queue:'max',
    cancel_in_progress:false,
    cloudflare_joins_same_group:true,
  }),
});

export function counterexamples() {
  const clean = simulateGitHubConcurrency({
    queue: CURRENT_NATIVE_QUEUES.clean.queue,
    running:'existing_clean_capture_running',
    arrivals:['native_schedule_new_slot','cloudflare_recovery_for_new_slot'],
  });
  const fourModeDuplicates = simulateGitHubConcurrency({
    queue:CURRENT_NATIVE_QUEUES.four_mode.queue,
    running:'existing_four_mode_capture_running',
    arrivals:['native_schedule_new_slot','cloudflare_claim_winner_same_slot'],
  });
  const fourModeSaturated = simulateGitHubConcurrency({
    queue:CURRENT_NATIVE_QUEUES.four_mode.queue,
    running:'existing_four_mode_capture_running',
    arrivals:[...Array.from({length:MAX_WAITING},(_,i)=>'other_pending_'+i),'cloudflare_recovery_new_slot'],
  });
  return {
    schema:RISK_SCHEMA,
    clean_original_schedule_displaced:clean.canceled.includes('native_schedule_new_slot'),
    clean_trace:clean.trace,
    four_mode_duplicate_pending:fourModeDuplicates.pending,
    four_mode_saturated_recovery_canceled:fourModeSaturated.canceled.includes('cloudflare_recovery_new_slot'),
    evidence_type:'documented_queue_rule_simulation_not_real_run',
    github_runtime_behavior_independently_observed:false,
    cross_provider_safe:false,
    recovery_release_approved:false,
  };
}
