import {afterEach, describe, expect, it, vi} from 'vitest';
import {createExecutionContext, createScheduledController, waitOnExecutionContext} from 'cloudflare:test';
import worker from '../independent_capture_wakeup.mjs';
import observerWorker from '../independent_capture_observer.mjs';
import {execute} from '../independent_capture_policy.mjs';

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

function mockGitHub({scheduledSuccess = false, olderQueued = false, failGetNumber = 0} = {}) {
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
        : olderQueued && event === 'schedule'
        ? [{id:7002,event:'schedule',head_branch:'main',status:'queued',
            conclusion:null,created_at:'2026-11-07T19:00:00Z'}]
        : [];
      return Response.json({total_count:eventRows.length,workflow_runs: eventRows});
    }
    if (method === 'POST' && u.pathname.endsWith('/dispatches') &&
        JSON.parse(options.body).ref === 'main' &&
        JSON.parse(options.body).return_run_details === true) {
      const id = u.pathname.includes('/clean-prospective.yml/') ? 500001 : 500002;
      return Response.json({
        workflow_run_id:id,
        run_url:'https://api.github.com/repos/ikst2512-eng/boat-edge-clean/actions/runs/'+id,
        html_url:'https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/'+id,
      }, {status:200});
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

// The research policy remains exercised inside real local Workerd with ALL
// outbound GitHub operations intercepted. This helper is intentionally not
// the locked, deployment-facing scheduled() entrypoint.
async function invokePolicy() {
  const result=await execute({scheduledTime:TEST_NOW,now:TEST_NOW,token:TEST_TOKEN,
    fetcher:fetch,clock:Date.now,
    onAccepted:receipt=>console.log('CLOUDFLARE_DISPATCH_RECEIPT='+JSON.stringify(receipt))});
  console.log('CLOUDFLARE_CAPTURE_WAKEUP='+JSON.stringify(result));
  return result;
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

    await invokePolicy();
    expect(calls.map(c => c.method)).toEqual(['GET','GET','GET','GET','POST','POST']);
    for (const c of calls.filter(x => x.method === 'POST')) {
      expect(JSON.parse(c.body)).toEqual({ref: 'main',return_run_details:true});
    }
    const receipts = logs.filter(x => x.startsWith('CLOUDFLARE_DISPATCH_RECEIPT='));
    expect(receipts).toHaveLength(2);
    expect(receipts.map(x => JSON.parse(x.split('=')[1]).workflow)).toEqual(['clean','four_mode']);
    expect(receipts.map(x => JSON.parse(x.split('=')[1]).github_run_id_reported)).toEqual([500001,500002]);
    expect(receipts.every(x => JSON.parse(x.split('=')[1]).github_run_id_proven === false)).toBe(true);
    expect(receipts.every(x => JSON.parse(x.split('=')[1]).github_execution_slot_bound_proven === false)).toBe(true);
    expect(logs.join(' ')).not.toContain(TEST_TOKEN);
    const report = JSON.parse(logs.find(x => x.startsWith('CLOUDFLARE_CAPTURE_WAKEUP=' )).split('=')[1]);
    expect(report.new_forecast_saved_proven).toBe(false);
    expect(report.formal).toBe(false);
    expect(report.on_time_cron_proven).toBe(false);
  });

  it('legacy 204 response has no run ID and never becomes a confirmed receipt or retry', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls,fetcher} = mockGitHub();
    const logs = [];
    vi.spyOn(console, 'log').mockImplementation(message => logs.push(String(message)));
    vi.spyOn(console, 'error').mockImplementation(message => logs.push(String(message)));
    vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
      if (options.method === 'POST') {
        calls.push({method: 'POST', url:String(url), body: options.body});
        return new Response(null, {status: 204});
      }
      return fetcher(url, options);
    }));
    await expect(invokePolicy()).rejects.toThrow('github_dispatch_accepted_without_run_details');
    expect(calls.filter(x => x.method === 'POST')).toHaveLength(1);
    expect(logs.filter(x => x.startsWith('CLOUDFLARE_DISPATCH_RECEIPT='))).toHaveLength(0);
    expect(logs.join(' ')).not.toContain(TEST_TOKEN);
  });

  it('200 with wrong GitHub run URL is rejected even in actual Workerd', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls,fetcher} = mockGitHub();
    const logs = [];
    vi.spyOn(console, 'log').mockImplementation(message => logs.push(String(message)));
    vi.spyOn(console, 'error').mockImplementation(message => logs.push(String(message)));
    vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
      if (options.method === 'POST') {
        calls.push({method: 'POST', url:String(url), body: options.body});
        return Response.json({workflow_run_id:100100,run_url:'https://api.github.com/repos/other/repo/actions/runs/100100',
          html_url:'https://github.com/other/repo/actions/runs/100100'}, {status:200});
      }
      return fetcher(url, options);
    }));
    await expect(invokePolicy()).rejects.toThrow('github_dispatch_run_details_missing_or_invalid');
    expect(calls.filter(x => x.method === 'POST')).toHaveLength(1);
    expect(logs.filter(x => x.startsWith('CLOUDFLARE_DISPATCH_RECEIPT='))).toHaveLength(0);
    expect(logs.join(' ')).not.toContain(TEST_TOKEN);
  });

  it('both original schedule runs already succeeded: four GETs and zero POSTs', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls} = mockGitHub({scheduledSuccess: true});
    await invokePolicy();
    expect(calls.map(x => x.method)).toEqual(['GET','GET','GET','GET']);
    expect(calls.filter(x => x.method === 'POST')).toHaveLength(0);
  });

  it('older-than-120m native queued main schedule suppresses both Cloudflare rescues in actual Workerd', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls} = mockGitHub({olderQueued:true});
    await invokePolicy();
    expect(calls.map(x=>x.method)).toEqual(['GET','GET','GET','GET']);
    expect(calls.filter(x=>x.method==='POST')).toHaveLength(0);
  });

  it('third GET fails: no partial recovery dispatch and no receipt', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(TEST_NOW);
    const {calls} = mockGitHub({failGetNumber: 3});
    const logs = [];
    vi.spyOn(console, 'log').mockImplementation(message => logs.push(String(message)));
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await expect(invokePolicy()).rejects.toThrow('github_history_http_error');
    expect(calls.filter(x => x.method === 'POST')).toHaveLength(0);
    expect(logs.filter(x => x.startsWith('CLOUDFLARE_DISPATCH_RECEIPT='))).toHaveLength(0);
  });

  it('deployment-facing scheduled Worker hard-locks even with true flag and valid token',async()=>{
    vi.spyOn(Date,'now').mockReturnValue(TEST_NOW);
    const {calls}=mockGitHub();
    const errors=[];
    vi.spyOn(console,'error').mockImplementation(message=>errors.push(String(message)));
    await expect(invoke(CRON,{CLOUDFLARE_DISPATCH_ENABLED:'true',
      GITHUB_DISPATCH_TOKEN:TEST_TOKEN})).rejects.toThrow('cross_provider_recovery_hard_locked');
    expect(calls).toHaveLength(0);
    expect(errors.join(' ')).toContain('cross_provider_recovery_hard_locked');
    expect(errors.join(' ')).not.toContain(TEST_TOKEN);
  });

  it('16 parallel deployment-facing scheduled handlers remain locked with zero GET and POST',async()=>{
    vi.spyOn(Date,'now').mockReturnValue(TEST_NOW);
    const {calls}=mockGitHub();
    const errors=[];
    vi.spyOn(console,'error').mockImplementation(message=>errors.push(String(message)));
    const outcomes=await Promise.allSettled(Array.from({length:16},()=>invoke(CRON,{
      CLOUDFLARE_DISPATCH_ENABLED:'true',GITHUB_DISPATCH_TOKEN:TEST_TOKEN,
    })));
    expect(outcomes).toHaveLength(16);
    expect(outcomes.every(x=>x.status==='rejected' &&
      x.reason instanceof Error &&
      x.reason.message==='cross_provider_recovery_hard_locked')).toBe(true);
    expect(calls).toHaveLength(0);
    expect(errors).toHaveLength(16);
    expect(errors.every(x=>x.includes('cross_provider_recovery_hard_locked') &&
      !x.includes(TEST_TOKEN) && !x.includes('Bearer '))).toBe(true);
    // Do NOT confuse this with dormant execute() research: two unlocked
    // concurrent invocations still reproduce 4 POSTs across two workflows.
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
      return Response.json({total_count:rows.length,workflow_runs: rows});
    }));
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await expect(invokePolicy()).rejects.toThrow('github_history_pagination_incomplete');
    // execute() reads BOTH schedule and manual history before validating the full page.
    // The fail-closed verdict must still produce zero POSTs.
    expect(calls).toHaveLength(2);
    expect(calls.every(c => c.method === 'GET')).toBe(true);
  });

  it('old completed runs on a full history page cannot hide page-2 pending native schedule',async()=>{
    vi.spyOn(Date,'now').mockReturnValue(TEST_NOW);
    const calls=[];
    vi.stubGlobal('fetch',vi.fn(async(rawUrl,opts={})=>{
      const url=new URL(rawUrl);
      expect(url.origin).toBe(GITHUB_ORIGIN);
      calls.push(opts.method);
      expect(opts.method).toBe('GET');
      const event=url.searchParams.get('event');
      if(event==='schedule') {
        const rows=Array.from({length:30},(_,i)=>({
          id:40000+i,event:'schedule',head_branch:'main',status:'completed',
          conclusion:'success',created_at:'2026-11-07T19:00:00Z',
        }));
        return Response.json({total_count:31,workflow_runs:rows});
      }
      return Response.json({total_count:0,workflow_runs:[]});
    }));
    vi.spyOn(console,'error').mockImplementation(()=>{});
    await expect(invokePolicy()).rejects.toThrow('github_history_pagination_incomplete');
    expect(calls.every(x=>x==='GET')).toBe(true);
    expect(calls).toHaveLength(1);
  });

  it('missing total_count must fail before a GitHub recovery POST',async()=>{
    vi.spyOn(Date,'now').mockReturnValue(TEST_NOW);
    const calls=[];
    vi.stubGlobal('fetch',vi.fn(async(rawUrl,opts={})=>{
      const url=new URL(rawUrl);
      expect(url.origin).toBe(GITHUB_ORIGIN);
      calls.push(opts.method);
      expect(opts.method).toBe('GET');
      return Response.json({workflow_runs:[]});
    }));
    vi.spyOn(console,'error').mockImplementation(()=>{});
    await expect(invokePolicy()).rejects.toThrow('github_history_missing_or_malformed');
    expect(calls).toEqual(['GET']);
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
        return Response.json({total_count:0,workflow_runs: []});
      }
      if (options.method === 'POST' && url.pathname.endsWith('/dispatches')) {
        const id = url.pathname.includes('/clean-prospective.yml/') ? 600001 : 600002;
        return Response.json({
          workflow_run_id:id,
          run_url:'https://api.github.com/repos/ikst2512-eng/boat-edge-clean/actions/runs/'+id,
          html_url:'https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/'+id,
        }, {status:200});
      }
      throw Error('BLOCKED_UNEXPECTED_ACTION');
    }));
    vi.spyOn(console, 'log').mockImplementation(() => {});
    await Promise.all([invokePolicy(), invokePolicy()]);
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
