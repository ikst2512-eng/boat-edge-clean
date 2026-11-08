import {afterEach, describe, expect, it, vi} from 'vitest';
import {createExecutionContext, createScheduledController, waitOnExecutionContext} from 'cloudflare:test';
import worker from '../independent_capture_wakeup.mjs';
import observerWorker from '../independent_capture_observer.mjs';

// The real Worker runs in Workerd. This suite NEVER performs an external
// network request, never loads real secrets and never deploys to Cloudflare.
const TEST_TOKEN = 'NOT_A_REAL_GITHUB_TOKEN_CLOUDFLARE_CI_ONLY';
const TEST_NOW = Date.UTC(2026, 10, 7, 22, 10, 0); // 2026-11-08 07:10 JST
const CRON = '*/5 22-23,0-13 * * *';
const GITHUB_ORIGIN = 'https://api.github.com';
const ROOT = '/repos/ikst2512-eng/boat-edge-clean/actions/workflows/';
const expectedWorkflows = ['clean-prospective.yml', 'four-mode-prospective-capture.yml'];

function scheduled(cron = CRON) {
  return createScheduledController({cron, scheduledTime: new Date(TEST_NOW)});
}

function mockGitHub({scheduledSuccess = false, failGetNumber = 0} = {}) {
  const calls = [];
  let getCount = 0;
  const fetcher = vi.fn(async (rawUrl, options = {}) => {
    const u = new URL(rawUrl);
    const method = options.method;
    // Fail closed: not one request may leave the simulated GitHub allowlist.
    if (u.origin !== GITHUB_ORIGIN || !u.pathname.startsWith(ROOT)) {
      throw new Error('BLOCKED_UNEXPECTED_REAL_NETWORK');
    }
    if (!expectedWorkflows.some(name => u.pathname.includes('/' + name + '/'))) {
      throw new Error('BLOCKED_UNEXPECTED_WORKFLOW');
    }
    if (options.headers?.Authorization !== 'Bearer ' + TEST_TOKEN) {
      throw new Error('BLOCKED_UNEXPECTED_CREDENTIAL');
    }
    calls.push({url: u.toString(), method, body: options.body});
    if (method === 'GET') {
      getCount++;
      if (getCount === failGetNumber) return new Response(null, {status: 503});
      const event = u.searchParams.get('event');
      if (!['schedule','workflow_dispatch'].includes(event) || u.searchParams.get('per_page') !== '30') {
        throw new Error('BLOCKED_UNEXPECTED_HISTORY_QUERY');
      }
      const eventRows = scheduledSuccess && event === 'schedule'
        ? [{id: 7001, event: 'schedule', head_branch: 'main', status: 'completed',
            conclusion: 'success', created_at: '2026-11-07T22:08:00Z'}]
        : [];
      return Response.json({workflow_runs: eventRows});
    }
    if (method === 'POST' && u.pathname.endsWith('/dispatches') &&
        JSON.parse(options.body).ref === 'main') {
      return new Response(null, {status: 204});
    }
    throw new Error('BLOCKED_UNEXPECTED_GITHUB_ACTION');
  });
  vi.stubGlobal('fetch', fetcher);
  return {calls, fetcher};
}

async function invoke(cron = CRON, env = {GITHUB_DISPATCH_TOKEN: TEST_TOKEN, CLOUDFLARE_DISPATCH_ENABLED: 'true'}) {
  const ctx = createExecutionContext();
  await worker.scheduled(scheduled(cron), env, ctx);
  await waitOnExecutionContext(ctx);
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('actual Workerd scheduled handler with intercepted GitHub API', () => {
  it('valid recovery window: four GETs precede two accepted dispatches, no publication proof', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls} = mockGitHub();
    const logs = [];
    vi.spyOn(console, 'log').mockImplementation(message => logs.push(String(message)));

    await invoke();
    expect(calls.map(c => c.method)).toEqual(['GET','GET','GET','GET','POST','POST']);
    for (const c of calls.filter(x => x.method === 'POST')) {
      expect(JSON.parse(c.body)).toEqual({ref: 'main'});
    }
    const receipts = logs.filter(x => x.startsWith('CLOUDFLARE_DISPATCH_RECEIPT='));
    expect(receipts).toHaveLength(2);
    expect(receipts.map(x => JSON.parse(x.split('=')[1]).workflow)).toEqual(['clean','four_mode']);
    expect(logs.join(' ')).not.toContain(TEST_TOKEN);
    const report = JSON.parse(logs.find(x => x.startsWith('CLOUDFLARE_CAPTURE_WAKEUP=' )).split('=')[1]);
    expect(report.new_forecast_saved_proven).toBe(false);
    expect(report.formal).toBe(false);
    expect(report.on_time_cron_proven).toBe(false);
  });

  it('both original schedule runs already succeeded: four GETs and zero POSTs', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls} = mockGitHub({scheduledSuccess: true});
    await invoke();
    expect(calls.map(x => x.method)).toEqual(['GET','GET','GET','GET']);
    expect(calls.filter(x => x.method === 'POST')).toHaveLength(0);
  });

  it('third GET fails: no partial recovery dispatch and no receipt', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls} = mockGitHub({failGetNumber: 3});
    const logs = [];
    vi.spyOn(console, 'log').mockImplementation(message => logs.push(String(message)));
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await expect(invoke()).rejects.toThrow('github_history_http_error');
    expect(calls.filter(x => x.method === 'POST')).toHaveLength(0);
    expect(logs.filter(x => x.startsWith('CLOUDFLARE_DISPATCH_RECEIPT='))).toHaveLength(0);
  });

  it('default observer mode runs in Workerd without PAT or GitHub network, even in active window', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls} = mockGitHub();
    const logs = [];
    vi.spyOn(console, 'log').mockImplementation(message => logs.push(String(message)));
    await invoke(CRON, {});
    expect(calls).toHaveLength(0);
    const reports=logs.filter(x=>x.startsWith('CLOUDFLARE_CAPTURE_OBSERVER_ONLY='));
    expect(reports).toHaveLength(1);
    const report=JSON.parse(reports[0].split('=')[1]);
    expect(report.mode).toBe('observe_only');
    expect(report.github_history_checked).toBe(false);
    expect(report.new_forecast_saved_proven).toBe(false);
    expect(logs.join(' ')).not.toContain(TEST_TOKEN);
  });

  it('Workerd requires an exact string opt-in, not boolean true', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls} = mockGitHub();
    await invoke(CRON, {CLOUDFLARE_DISPATCH_ENABLED: true, GITHUB_DISPATCH_TOKEN: TEST_TOKEN});
    expect(calls).toHaveLength(0);
  });

  it('isolated observer entrypoint never dispatches even with live-mode flag and injected fake token', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls} = mockGitHub();
    const logs = [];
    vi.spyOn(console, 'log').mockImplementation(message => logs.push(String(message)));
    const ctx=createExecutionContext();
    await observerWorker.scheduled(scheduled(CRON),
      {CLOUDFLARE_DISPATCH_ENABLED:'true', GITHUB_DISPATCH_TOKEN:TEST_TOKEN},ctx);
    await waitOnExecutionContext(ctx);
    expect(calls).toHaveLength(0);
    const outputs=logs.filter(x=>x.startsWith('CLOUDFLARE_CAPTURE_OBSERVER_ONLY='));
    expect(outputs).toHaveLength(1);
    const report=JSON.parse(outputs[0].split('=')[1]);
    expect(report.github_history_checked).toBe(false);
    expect(report.formal).toBe(false);
    expect(report.new_forecast_saved_proven).toBe(false);
    expect(logs.join(' ')).not.toContain(TEST_TOKEN);
  });

  it('a saturated recent schedule page fails closed in actual Workerd before any POST', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const calls = [];
    vi.stubGlobal('fetch', vi.fn(async (rawUrl, options = {}) => {
      const url = new URL(rawUrl);
      expect(url.origin).toBe(GITHUB_ORIGIN);
      calls.push({method: options.method, url: url.toString()});
      expect(options.method).toBe('GET');
      const rows = Array.from({length: 30}, (_, i) => ({
        id: 8000 + i, event: 'schedule', head_branch: 'main',
        status: 'completed', conclusion: 'success',
        created_at: '2026-11-07T22:08:00Z',
      }));
      return Response.json({workflow_runs: rows});
    }));
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await expect(invoke()).rejects.toThrow('github_history_pagination_incomplete');
    expect(calls).toHaveLength(1);
    expect(calls.every(c => c.method === 'GET')).toBe(true);
  });

  it('negative evidence: the current GET-to-POST design permits duplicate POSTs across concurrent invocations', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const calls = [];
    let historyGets = 0;
    let releaseBoth;
    const bothAtLastHistory = new Promise(resolve => { releaseBoth = resolve; });
    vi.stubGlobal('fetch', vi.fn(async (rawUrl, options = {}) => {
      const url = new URL(rawUrl);
      expect(url.origin).toBe(GITHUB_ORIGIN);
      expect(expectedWorkflows.some(name => url.pathname.includes('/' + name + '/'))).toBe(true);
      calls.push({method: options.method, path: url.pathname});
      if (options.method === 'GET') {
        historyGets += 1;
        if (historyGets === 8) releaseBoth();
        // Ensure both independently checked their GET history before either can POST.
        if (historyGets >= 7) await bothAtLastHistory;
        return Response.json({workflow_runs: []});
      }
      if (options.method === 'POST' && url.pathname.endsWith('/dispatches')) {
        return new Response(null, {status: 204});
      }
      throw Error('BLOCKED_UNEXPECTED_ACTION');
    }));
    vi.spyOn(console, 'log').mockImplementation(() => {});
    await Promise.all([invoke(), invoke()]);
    expect(calls.filter(x => x.method === 'GET')).toHaveLength(8);
    const posts = calls.filter(x => x.method === 'POST');
    expect(posts).toHaveLength(4);
    for (const workflow of expectedWorkflows) {
      expect(posts.filter(x => x.path.endsWith('/' + workflow + '/dispatches'))).toHaveLength(2);
    }
    // Deliberately captures an UNRESOLVED production blocker; two simultaneous
    // invocation histories are not a cross-provider atomic lock. Never enable
    // dual recovery schedulers or certify exactly-once based on green CI.
  });

  it('foreign cron never attempts a GitHub API request', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls} = mockGitHub();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await expect(invoke('* * * * *')).rejects.toThrow('unexpected_cron_trigger');
    expect(calls).toHaveLength(0);
  });
});
