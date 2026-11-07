// Cloudflare Workers module entrypoint: export default only.
// Keep named policy exports in a separate module: workerd rejects data exports
// on a Worker service entrypoint (observed in offline CI runtime smoke).
import {ALLOWED_CRON, SCHEMA, execute} from './independent_capture_policy.mjs';

const SAFE_ERRORS = new Set([
  'invalid_trigger_clock', 'late_or_future_cron_trigger', 'cron_outside_allowlist',
  'unexpected_cron_trigger',
  'invalid_clock', 'unknown_workflow', 'fetcher_required', 'invalid_receipt_sink',
  'GITHUB_DISPATCH_TOKEN_required', 'github_history_http_error',
  'github_history_missing_or_malformed', 'github_history_identity_invalid',
  'github_history_chronology_invalid', 'github_history_pagination_incomplete',
  'github_external_dispatch_not_accepted', 'recovery_window_expired_before_dispatch',
]);

export default {
  async scheduled(controller, env) {
    // No HTTP fetch handler. Additionally pin the exact declared cron identity:
    // Cloudflare supplies controller.cron verbatim, including spaces.
    try {
      if (!controller || controller.cron !== ALLOWED_CRON) {
        throw new Error('unexpected_cron_trigger');
      }
      const report = await execute({scheduledTime: controller.scheduledTime, now: Date.now(),
        token: env?.GITHUB_DISPATCH_TOKEN, fetcher: fetch, clock: Date.now,
        onAccepted: receipt => console.log('CLOUDFLARE_DISPATCH_RECEIPT=' + JSON.stringify(receipt))});
      console.log('CLOUDFLARE_CAPTURE_WAKEUP=' + JSON.stringify(report));
    } catch (error) {
      console.error('CLOUDFLARE_CAPTURE_WAKEUP_ERROR=' + JSON.stringify({schema: SCHEMA,
        error_type: error instanceof Error && SAFE_ERRORS.has(error.message) ? error.message : 'unexpected_error',
        on_time_cron_proven: false, new_forecast_saved_proven: false}));
      throw error;
    }
  },
};
