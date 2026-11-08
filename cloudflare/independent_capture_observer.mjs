// Cloudflare observer-only service entrypoint. NO GitHub API, PAT, fetch,
// workflow_dispatch, or recovery policy execution lives in this handler.
// Not the production-capable independent_capture_wakeup.mjs entrypoint.
import {ALLOWED_CRON, SCHEMA, observe} from './independent_capture_policy.mjs';

const SAFE_OBSERVER_ERRORS = new Set([
  'unexpected_cron_trigger', 'invalid_trigger_clock',
  'late_or_future_cron_trigger', 'cron_outside_allowlist',
  'invalid_clock', 'unknown_workflow',
]);

export default {
  async scheduled(controller) {
    try {
      if (!controller || controller.cron !== ALLOWED_CRON) {
        throw new Error('unexpected_cron_trigger');
      }
      const report = observe({scheduledTime: controller.scheduledTime, now: Date.now()});
      console.log('CLOUDFLARE_CAPTURE_OBSERVER_ONLY=' + JSON.stringify(report));
    } catch (error) {
      console.error('CLOUDFLARE_CAPTURE_OBSERVER_ERROR=' + JSON.stringify({
        schema: SCHEMA,
        error_type: error instanceof Error && SAFE_OBSERVER_ERRORS.has(error.message)
          ? error.message : 'unexpected_error',
        github_history_checked: false, new_forecast_saved_proven: false, formal: false,
      }));
      throw error;
    }
  },
};
