import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {auditLocalFirstAddEvidence,computeLocalBlobHashes,FIRST_ADD_LAB_SCHEMA} from '../cloudflare/local_first_add_evidence_lab.mjs';
import {verifyRealGithubFirstAdd,REMOTE_GITHUB_SCHEMA} from '../cloudflare/remote_github_first_add_audit.mjs';
import {auditNativePublisherPair,auditNativePublisherPostPush} from '../cloudflare/native_publication_receipt_lab.mjs';
import cloudflareWorker from '../cloudflare/independent_capture_wakeup.mjs';
import observerWorker from '../cloudflare/independent_capture_observer.mjs';
import * as observerExports from '../cloudflare/independent_capture_observer.mjs';
import * as workerEntrypointExports from '../cloudflare/independent_capture_wakeup.mjs';
import {plannedSlots, eligibleSlot, execute, observe, WORKFLOWS} from '../cloudflare/independent_capture_policy.mjs';
const JST=9*60*60*1000;
const jst=(h,m,d=5)=>new Date(Date.UTC(2026,10,d,h,m)-JST);
const tick=(h,m,d=5)=>jst(h,m,d).getTime();
const fakeRun=(event,when,rest={})=>({id:101,event,head_branch:'main',status:'completed',conclusion:'success',created_at:when.toISOString(),...rest});
function mock({schedule=[],manual=[],failAt=0,failPost=false,postStatus=200}={}) {
  const calls=[];
  async function fetcher(url,options) {
    calls.push({url,method:options.method,body:options.body});
    if (failAt === calls.length) throw new Error('network_failure');
    if (options.method==='POST') {
      const status=failPost?403:postStatus;
      const id=url.includes('/'+WORKFLOWS.clean+'/')?100101:100102;
      const expectedApi='https://api.github.com/repos/ikst2512-eng/boat-edge-clean/actions/runs/'+id;
      const expectedHtml='https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/'+id;
      return {status,json:async()=>({workflow_run_id:id,run_url:expectedApi,html_url:expectedHtml})};
    }
    const rows=url.includes('event=workflow_dispatch')?manual:schedule;
    return {status:200,json:async()=>({total_count:rows.length,workflow_runs:rows})};
  }
  return {calls,fetcher};
}
const run=(clock=tick(7,10),m=mock(),token='TEST_ONLY')=>execute({scheduledTime:clock,now:clock,token,fetcher:m.fetcher});
const noPosts=m=>assert.equal(m.calls.filter(c=>c.method==='POST').length,0);

test('CLEAN 63 and four-mode 56 actual daily slots',()=>{
  assert.equal(plannedSlots('clean',jst(12,0)).length,63);
  assert.equal(plannedSlots('four_mode',jst(12,0)).length,56);
  assert.equal(plannedSlots('clean',jst(12,0)).at(-1),tick(22,28));
  assert.equal(plannedSlots('four_mode',jst(12,0)).at(-1),tick(20,52));
});

test('single 5min UTC cron covers every slot once',()=>{
  const wrangler=readFileSync(new URL('../cloudflare/wrangler.toml',import.meta.url),'utf8');
  assert.match(wrangler,/required = \["GITHUB_DISPATCH_TOKEN"\]/);
  assert.match(wrangler,/crons = \["\*\/5 22-23,0-13 \* \* \*"\]/);
  for(const kind of Object.keys(WORKFLOWS))for(const slot of plannedSlots(kind,jst(12,0))){
    const ticks=[];
    for(let delta=1;delta<=8;delta++){
      const t=new Date(slot+delta*60_000); const h=t.getUTCHours();
      if(t.getUTCMinutes()%5===0&&(h>=22||h<=13)&&eligibleSlot(kind,t)===slot)ticks.push(t);
    }
    assert.equal(ticks.length,1,`${kind} ${new Date(slot).toISOString()} wakeup coverage`);
  }
});

test('source GitHub cron still matches plannedSlots and Render fallback',()=>{
  const yamlPaths={clean:'.github/workflows/clean-prospective.yml',four_mode:'.github/workflows/four-mode-prospective-capture.yml'};
  for(const [kind,path] of Object.entries(yamlPaths)){
    const y=readFileSync(new URL(`../${path}`,import.meta.url),'utf8');
    const expressions=[...y.matchAll(/^\s+- cron: '([^']+)'/gm)].map(x=>x[1]);
    assert.ok(expressions.length>0);
    const actual=new Set();
    const expand=x=>x.split(',').flatMap(t=>t.includes('-')?Array.from({length:+t.split('-')[1]-+t.split('-')[0]+1},(_,i)=>+t.split('-')[0]+i):[+t]);
    for(const expr of expressions){const [mins,hrs,day,month,dow]=expr.split(' ');assert.deepEqual([day,month,dow],['*','*','*']);
      for(const hour of expand(hrs))for(const minute of expand(mins))actual.add(`${(hour+9)%24}:${minute}`);
    }
    const expected=new Set(plannedSlots(kind,jst(12,0)).map(slot=>{const d=new Date(slot+JST);return `${d.getUTCHours()}:${d.getUTCMinutes()}`;}));
    assert.deepEqual(actual,expected);
  }
});

test('two eligible workflows dispatch only missing slots',async()=>{
  const m=mock();const out=await run(tick(7,10),m);
  assert.deepEqual(m.calls.map(x=>x.method),['GET','GET','GET','GET','POST','POST']);
  for(const name of Object.keys(WORKFLOWS)) assert.equal(out.workflows[name].action,'dispatch_run_id_returned_not_forecast_proof');
  assert.ok(m.calls.filter(x=>x.method==='POST').every(x=>JSON.parse(x.body).ref==='main' && JSON.parse(x.body).return_run_details===true));
  assert.equal(out.formal,false);assert.equal(out.new_forecast_saved_proven,false);
});

test('each verified 200 reports API run ID without claiming a completed GitHub run',async()=>{
  const m=mock(); const receipts=[]; const when=tick(7,10);
  const out=await execute({scheduledTime:when,now:when,token:'PRIVATE_TEST_TOKEN',
    fetcher:m.fetcher, onAccepted:x=>receipts.push(x)});
  assert.equal(receipts.length,2);
  assert.deepEqual(receipts.map(x=>x.workflow),['clean','four_mode']);
  for(const entry of receipts){
    assert.equal(entry.event,'workflow_dispatch_accepted');
    assert.equal(entry.github_run_id_proven,false);
    assert.ok(Number.isSafeInteger(entry.github_run_id_reported));
    assert.equal(entry.github_run_url_reported,'https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/'+entry.github_run_id_reported);
    assert.equal(entry.new_forecast_saved_proven,false);
    assert.equal(entry.formal,false);
    assert.ok(entry.slot_jst.endsWith('+09:00'));
    assert.ok(entry.request_started_at_jst.endsWith('+09:00'));
    assert.ok(!JSON.stringify(entry).includes('PRIVATE_TEST_TOKEN'));
  }
  assert.equal(out.workflows.four_mode.action,'dispatch_run_id_returned_not_forecast_proof');
});

test('first 200 run ID remains auditable when second dispatch fails',async()=>{
  const m=mock(); const receipts=[]; let posts=0;
  const guarded=async(url,options)=>{
    if(options.method==='POST' && ++posts===2)return {status:403};
    return m.fetcher(url,options);
  };
  const when=tick(7,10);
  await assert.rejects(()=>execute({scheduledTime:when,now:when,token:'TEST',
    fetcher:guarded,onAccepted:x=>receipts.push(x)}),/github_external_dispatch_not_accepted/);
  assert.equal(posts,2);
  assert.deepEqual(receipts.map(x=>x.workflow),['clean']);
  assert.equal(receipts[0].github_run_id_proven,false);
  assert.equal(receipts[0].github_run_id_reported,100101);
});

test('GET failure emits no accepted-dispatch receipts',async()=>{
  const m=mock({failAt:3}); const receipts=[]; const when=tick(7,10);
  await assert.rejects(()=>execute({scheduledTime:when,now:when,token:'TEST',
    fetcher:m.fetcher,onAccepted:x=>receipts.push(x)}),/network_failure/);
  assert.deepEqual(receipts,[]);
  noPosts(m);
});

test('invalid receipt sink fails before any network or POST',async()=>{
  const m=mock(); const when=tick(7,10);
  await assert.rejects(()=>execute({scheduledTime:when,now:when,token:'TEST',
    fetcher:m.fetcher,onAccepted:123}),/invalid_receipt_sink/);
  assert.equal(m.calls.length,0);
});

test('no network outside capture windows',async()=>{
  const m=mock();const out=await run(tick(22,55),m,undefined);assert.equal(out.action,'outside_recovery_windows_no_network');assert.equal(m.calls.length,0);
});

test('missing token is fail-closed',async()=>{const m=mock();await assert.rejects(()=>run(tick(7,10),m,''),/GITHUB_DISPATCH_TOKEN_required/);assert.equal(m.calls.length,0);});

test('four-mode ends 20:52, CLEAN continues 21:10',async()=>{
  const m=mock();const out=await run(tick(21,10),m);
  assert.equal(out.workflows.four_mode.action,'no_dispatch');assert.equal(m.calls.length,3);
});

test('special final CLEAN slot only 22:30 and never after 22:33',async()=>{
  assert.equal(eligibleSlot('clean',jst(22,30)),tick(22,28));
  assert.equal(eligibleSlot('clean',jst(22,33)),null);
  const m=mock();const out=await run(tick(22,30),m);assert.equal(out.workflows.clean.action,'dispatch_run_id_returned_not_forecast_proof');
});

test('reject cron invocation outside configured UTC, wrong minute',async()=>{
  const m=mock();await assert.rejects(()=>execute({scheduledTime:tick(7,11),now:tick(7,11),token:'TEST',fetcher:m.fetcher}),/cron_outside_allowlist/);noPosts(m);
});

test('reject delayed trigger and future controller timestamp',async()=>{
  for(const lag of [-1000,91_000,5*60_000]){
    const m=mock();await assert.rejects(()=>execute({scheduledTime:tick(7,10),now:tick(7,10)+lag,token:'TEST',fetcher:m.fetcher}),/late_or_future_cron_trigger/);assert.equal(m.calls.length,0);
  }
});

test('direct successful, queued, in_progress, unknown block dispatch',async()=>{
  for(const [status,conclusion] of [['completed','success'],['queued',null],['in_progress',null],['completed',null]]){
    const m=mock({schedule:[fakeRun('schedule',jst(7,8),{status,conclusion})]});
    const out=await run(tick(7,10),m);assert.equal(out.workflows.four_mode.action,'no_dispatch');noPosts(m);
  }
});

test('failed scheduled run is recoverable but not publication proof',async()=>{
  const m=mock({schedule:[fakeRun('schedule',jst(7,8),{conclusion:'failure'})]});
  const out=await run(tick(7,10),m);assert.equal(out.workflows.four_mode.action,'dispatch_run_id_returned_not_forecast_proof');assert.equal(out.on_time_cron_proven,false);
});

test('manual dispatch near slot blocks even when manual failed',async()=>{
  const m=mock({manual:[fakeRun('workflow_dispatch',jst(7,8),{conclusion:'failure'})]});
  const out=await run(tick(7,10),m);assert.equal(out.workflows.clean.reason,'previous_dispatch_or_active_job');noPosts(m);
});

test('an earlier active main run blocks, earlier success does not',async()=>{
  let m=mock({schedule:[fakeRun('schedule',jst(7,8),{status:'queued',conclusion:null})]});
  let out=await run(tick(7,25),m);assert.equal(out.workflows.four_mode.reason,'previous_dispatch_or_active_job');noPosts(m);
  m=mock({schedule:[fakeRun('schedule',jst(7,8))]});out=await run(tick(7,25),m);
  assert.equal(out.workflows.four_mode.action,'dispatch_run_id_returned_not_forecast_proof');
});

test('ancient native queued or running main capture blocks Cloudflare even after 120 minutes',async()=>{
  const now=tick(7,10);
  const old=jst(4,0); // 190 min before today's 07:10 JST rescue tick.
  for(const event of ['schedule','workflow_dispatch']){
    for(const status of ['queued','pending','in_progress','waiting']){
      const row=fakeRun(event,old,{status,conclusion:null});
      const m=mock({[event==='schedule'?'schedule':'manual']:[row]});
      const result=await run(now,m);
      assert.equal(result.workflows.clean.action,'no_dispatch');
      assert.equal(result.workflows.four_mode.action,'no_dispatch');
      assert.equal(result.workflows.clean.reason,'previous_dispatch_or_active_job');
      noPosts(m);
    }
  }
});

test('ancient completed native capture does not indefinitely suppress later valid recovery',async()=>{
  const now=tick(7,10);
  const m=mock({schedule:[fakeRun('schedule',jst(4,0),{status:'completed',conclusion:'success'})]});
  const result=await run(now,m);
  assert.equal(result.workflows.clean.action,'dispatch_run_id_returned_not_forecast_proof');
  assert.equal(result.workflows.four_mode.action,'dispatch_run_id_returned_not_forecast_proof');
  assert.equal(m.calls.filter(c=>c.method==='POST').length,2);
});

test('nonmain cannot masquerade as successful main run',async()=>{
  const m=mock({schedule:[fakeRun('schedule',jst(7,8),{head_branch:'feature/other'})]});const out=await run(tick(7,10),m);
  assert.equal(out.workflows.four_mode.action,'dispatch_run_id_returned_not_forecast_proof');
});

test('malformed GitHub history fails closed',async()=>{
  for(const change of [{id:'123'},{head_branch:null},{created_at:'invalid'},{event:'push'},{status:null}]){
    const m=mock({schedule:[fakeRun('schedule',jst(7,8),change)]});
    await assert.rejects(()=>run(tick(7,10),m));noPosts(m);
  }
});

test('a saturated first page with old completed main runs must never hide an even older pending native run',async()=>{
  // A page-2 queued CLEAN schedule is invisible to a first-page-only scan.
  // Previously the old row could satisfy the 120-minute boundary and permit POST.
  const now=tick(7,10);
  const rows=Array.from({length:30},(_,i)=>fakeRun('schedule',jst(4,0),{
    id:1000+i, status:'completed', conclusion:'success',
  }));
  const m=mock({schedule:rows});
  await assert.rejects(()=>run(now,m),/github_history_pagination_incomplete/);
  noPosts(m);
});

test('GitHub total_count beyond first-page rows, absent, fractional or inconsistent fails before POST',async()=>{
  for(const count of [31,undefined,1.5,-1,0]){
    const m=mock();
    const fetcher=async(url,opts)=>{
      const result=await m.fetcher(url,opts);
      if(opts.method==='GET' && url.includes('event=schedule')){
        return {status:200,json:async()=>({
          ...(count===undefined?{}:{total_count:count}),
          workflow_runs: [fakeRun('schedule',jst(4,0))],
        })};
      }
      return result;
    };
    const now=tick(7,10);
    await assert.rejects(()=>execute({scheduledTime:now,now,token:'TEST',fetcher}),
      /github_history_missing_or_malformed|github_history_pagination_incomplete/);
    noPosts(m);
  }
});

test('complete short GitHub history with exact count remains eligible in the absence of native runs',async()=>{
  const m=mock();
  const out=await run(tick(7,10),m);
  assert.equal(m.calls.filter(x=>x.method==='POST').length,2);
  assert.equal(out.formal,false);
  assert.equal(out.new_forecast_saved_proven,false);
});

test('full first page cannot hide recent main run',async()=>{
  const rows=Array.from({length:30},(_,i)=>fakeRun('schedule',jst(7,8),{id:i+1}));
  const m=mock({schedule:rows});await assert.rejects(()=>run(tick(7,10),m),/pagination_incomplete/);noPosts(m);
});

test('future-dated GitHub run cannot silently bypass duplicate guard',async()=>{
  const m=mock({schedule:[fakeRun('schedule',jst(7,11))]});
  await assert.rejects(()=>run(tick(7,10),m),/github_history_chronology_invalid/);noPosts(m);
});

test('history payload uses 30 items per page for Free CPU budget',async()=>{
  const m=mock();await run(tick(7,10),m);
  assert.equal(m.calls.filter(x=>x.method==='GET').length,4);
  assert.ok(m.calls.filter(x=>x.method==='GET').every(x=>x.url.includes('per_page=30')));
});

test('a late GET must not dispatch after the narrow original slot',async()=>{
  const now=tick(22,30);const m=mock();
  await assert.rejects(()=>execute({scheduledTime:now,now,token:'TEST',fetcher:m.fetcher,
    clock:()=>tick(22,33)}),/recovery_window_expired_before_dispatch/);
  noPosts(m);
});

test('a late second POST must stop further dispatch',async()=>{
  const now=tick(7,10);const m=mock();let first=true;
  await assert.rejects(()=>execute({scheduledTime:now,now,token:'TEST',fetcher:m.fetcher,
    clock:()=>{if(first){first=false;return now;}return tick(7,13);}}),/recovery_window_expired_before_dispatch/);
  assert.equal(m.calls.filter(x=>x.method==='POST').length,1);
});

test('second workflow GET failure prevents partial POST',async()=>{
  const m=mock({failAt:3});await assert.rejects(()=>run(tick(7,10),m),/network_failure/);noPosts(m);
});

test('non-200 history fails before POST',async()=>{
  const m=mock();m.fetcher=async (url,opts)=>{m.calls.push({url,method:opts.method});return {status:503};};
  await assert.rejects(()=>run(tick(7,10),m),/github_history_http_error/);noPosts(m);
});

test('explicit GitHub 401/403/404/429/500/503 history failures never become recoveries',async()=>{
  for(const status of [401,403,404,429,500,503]){
    for(const failAt of [1,4]){
      const m=mock();let gets=0;
      m.fetcher=async (url,options)=>{
        m.calls.push({url,method:options.method});
        assert.equal(options.method,'GET','a failed history query must block every POST');
        gets++;
        return gets===failAt?{status}:{status:200,json:async()=>({total_count:0,workflow_runs:[]})};
      };
      await assert.rejects(()=>run(tick(7,10),m),/github_history_http_error/);
      noPosts(m);
      assert.equal(m.calls.length,failAt);
    }
  }
});

test('network timeouts on any GitHub history GET never produce a 204 receipt',async()=>{
  for(const failAt of [1,2,3,4]){
    const m=mock(),receipts=[];let gets=0;
    m.fetcher=async (url,options)=>{
      m.calls.push({url,method:options.method});
      assert.equal(options.method,'GET','never POST after timeout');
      if(++gets===failAt)throw new Error('simulated_transport_timeout');
      return {status:200,json:async()=>({total_count:0,workflow_runs:[]})};
    };
    const when=tick(7,10);
    await assert.rejects(()=>execute({scheduledTime:when,now:when,token:'TEST',
      fetcher:m.fetcher,onAccepted:x=>receipts.push(x)}),/simulated_transport_timeout/);
    noPosts(m);
    assert.deepEqual(receipts,[]);
  }
});

test('a visible prior same-slot dispatch blocks a second sequential recovery',async()=>{
  const first=mock(),now=tick(7,10);
  const firstResult=await run(now,first);
  assert.equal(first.calls.filter(x=>x.method==='POST').length,2);
  assert.equal(firstResult.formal,false);
  const second=mock({manual:[fakeRun('workflow_dispatch',jst(7,10),{id:9090,status:'queued',conclusion:null})]});
  const secondResult=await run(now,second);
  noPosts(second);
  assert.equal(secondResult.workflows.clean.reason,'previous_dispatch_or_active_job');
  assert.equal(secondResult.workflows.four_mode.reason,'previous_dispatch_or_active_job');
  // This is sequential visibility only; GET->POST is not an atomic cross-provider lock.
});

test('configured Free cron rate is bounded: 192 wakeups daily and six subrequests max per eligible tick',async()=>{
  const prod=readFileSync(new URL('../cloudflare/wrangler.toml',import.meta.url),'utf8');
  const pilot=readFileSync(new URL('../cloudflare/wrangler.observer.toml',import.meta.url),'utf8');
  for(const config of [prod,pilot]){
    const matches=[...config.matchAll(/^crons = \[(.*)\]$/gm)];
    assert.equal(matches.length,1);
    assert.equal(matches[0][1],'"*/5 22-23,0-13 * * *"');
  }
  const hours=2+14; // UTC 22-23 and 00-13 inclusive.
  assert.equal(hours*12,192);
  const m=mock();
  await run(tick(7,10),m);
  assert.equal(m.calls.length,6);
  assert.equal(m.calls.filter(x=>x.method==='GET').length,4);
  assert.ok(m.calls.length<=50);
  // 192 is per configured Worker. This is configuration proof, NOT real CPU evidence.
});

test('scheduled adapter refuses foreign or missing Cron identities before any network',async()=>{
  const previousFetch=globalThis.fetch;
  const previousError=console.error;
  let attempts=0;const errors=[];
  globalThis.fetch=async()=>{attempts++;throw new Error('fetch_must_not_run');};
  console.error=message=>errors.push(String(message));
  try{
    for(const cron of ['*/5 22-23,0-13 * * * ', '*/5 * * * *', undefined]){
      await assert.rejects(()=>cloudflareWorker.scheduled({
        cron,scheduledTime:tick(7,10)
      },{GITHUB_DISPATCH_TOKEN:'PRIVATE_TEST_TOKEN'},{}),/unexpected_cron_trigger/);
    }
    assert.equal(attempts,0);
    assert.equal(errors.length,3);
    assert.ok(errors.every(x=>x.includes('unexpected_cron_trigger')&&!x.includes('PRIVATE_TEST_TOKEN')));
  }finally{
    globalThis.fetch=previousFetch;
    console.error=previousError;
  }
});

test('dormant recovery policy separately produces traceable mocked receipts without publication proof',async()=>{
  const when=tick(7,10),m=mock(),receipts=[];
  const out=await execute({scheduledTime:when,now:when,token:'PRIVATE_TEST_TOKEN',
    fetcher:m.fetcher,clock:()=>when,onAccepted:x=>receipts.push(x)});
  assert.deepEqual(m.calls.map(x=>x.method),['GET','GET','GET','GET','POST','POST']);
  assert.deepEqual(receipts.map(x=>x.workflow),['clean','four_mode']);
  assert.ok(receipts.every(x=>Number.isSafeInteger(x.github_run_id_reported) &&
    x.github_run_id_proven===false && x.new_forecast_saved_proven===false &&
    x.github_execution_slot_bound_proven===false && x.formal===false));
  assert.equal(out.formal,false);
  assert.ok(!JSON.stringify(receipts).includes('PRIVATE_TEST_TOKEN'));
});

test('hard-locked recovery Worker refuses ALL live POSTs even with the token and opt-in true',async()=>{
  const when=tick(7,10),m=mock(),errors=[];
  const oldFetch=globalThis.fetch,oldNow=Date.now,oldError=console.error;
  globalThis.fetch=m.fetcher;Date.now=()=>when;console.error=message=>errors.push(String(message));
  try{
    for(const token of [undefined,'PRIVATE_TEST_TOKEN']){
      await assert.rejects(()=>cloudflareWorker.scheduled({
        cron:'*/5 22-23,0-13 * * *',scheduledTime:when},
        {CLOUDFLARE_DISPATCH_ENABLED:'true',GITHUB_DISPATCH_TOKEN:token},{}),
        /cross_provider_recovery_hard_locked/);
    }
  }finally{globalThis.fetch=oldFetch;Date.now=oldNow;console.error=oldError;}
  assert.equal(m.calls.length,0);
  assert.equal(errors.length,2);
  assert.ok(errors.every(x=>x.includes('cross_provider_recovery_hard_locked') &&
    !x.includes('PRIVATE_TEST_TOKEN') && !x.includes('Bearer')));
  const source=readFileSync(new URL('../cloudflare/independent_capture_wakeup.mjs',import.meta.url),'utf8');
  assert.match(source,/const CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED = true;/);
});

test('scheduled adapter defaults to observer with zero GitHub requests and no secret',async()=>{
  const when=tick(7,10), logs=[],calls=[];
  const oldFetch=globalThis.fetch,oldNow=Date.now,oldLog=console.log;
  globalThis.fetch=async()=>{calls.push('unexpected_request');throw Error('network_must_not_run');};
  Date.now=()=>when;console.log=message=>logs.push(String(message));
  try{
    await cloudflareWorker.scheduled({cron:'*/5 22-23,0-13 * * *',scheduledTime:when},{},{});
  }finally{globalThis.fetch=oldFetch;Date.now=oldNow;console.log=oldLog;}
  assert.deepEqual(calls,[]);
  assert.equal(logs.length,1);
  assert.ok(logs[0].startsWith('CLOUDFLARE_CAPTURE_OBSERVER_ONLY='));
  const report=JSON.parse(logs[0].split('=')[1]);
  assert.equal(report.action,'no_network_no_dispatch');
  assert.equal(report.github_history_checked,false);
  assert.equal(report.new_forecast_saved_proven,false);
});

test('only literal true enables dispatch; all other settings remain no-network observer',async()=>{
  for(const value of ['TRUE','1',true,'false',false,null]){
    const when=tick(7,10),calls=[];
    const oldFetch=globalThis.fetch,oldNow=Date.now,oldLog=console.log;
    globalThis.fetch=async()=>{calls.push(value);throw Error('network_must_not_run');};
    Date.now=()=>when;console.log=()=>{};
    try{
      await cloudflareWorker.scheduled({cron:'*/5 22-23,0-13 * * *',scheduledTime:when},
        {CLOUDFLARE_DISPATCH_ENABLED:value,GITHUB_DISPATCH_TOKEN:'PRIVATE_TEST_TOKEN'},{});
    }finally{globalThis.fetch=oldFetch;Date.now=oldNow;console.log=oldLog;}
    assert.equal(calls.length,0);
  }
});

test('zero-credential observer pilot stays disabled and has no required PAT secret',()=>{
  const observer=readFileSync(new URL('../cloudflare/wrangler.observer.toml',import.meta.url),'utf8');
  const production=readFileSync(new URL('../cloudflare/wrangler.toml',import.meta.url),'utf8');
  assert.match(observer,/name = "boat-edge-clean-independent-observer"/);
  assert.match(observer,/main = "independent_capture_observer.mjs"/);
  assert.doesNotMatch(observer,/main = "independent_capture_wakeup.mjs"/);
  assert.match(production,/name = "boat-edge-clean-independent-wakeup"/);
  assert.match(observer,/CLOUDFLARE_DISPATCH_ENABLED = "false"/);
  assert.match(production,/CLOUDFLARE_DISPATCH_ENABLED = "false"/);
  assert.doesNotMatch(observer,/\[secrets\]/);
  assert.doesNotMatch(observer,/GITHUB_DISPATCH_TOKEN/);
  assert.match(production,/required = \["GITHUB_DISPATCH_TOKEN"\]/);
  const cronExpr='crons = ["*/5 22-23,0-13 * * *"]';
  assert.ok(observer.includes(cronExpr));
  assert.ok(production.includes(cronExpr));
});

test('legacy GitHub 204 with no run ID is fail-closed: no false confirmed receipt',async()=>{
  const m=mock({postStatus:204}), receipts=[];
  const when=tick(7,10);
  await assert.rejects(()=>execute({scheduledTime:when,now:when,token:'TEST',
    fetcher:m.fetcher,onAccepted:x=>receipts.push(x)}),/github_dispatch_accepted_without_run_details/);
  assert.equal(m.calls.filter(x=>x.method==='POST').length,1);
  assert.deepEqual(receipts,[]);
});

test('GitHub 200 with forged, absent, or unparseable run details is not success proof',async()=>{
  const valid=mock();
  for(const broken of [
    {workflow_run_id:0}, {workflow_run_id:'123'},
    {workflow_run_id:100101,run_url:'https://evil.example/actions/runs/100101'},
    {workflow_run_id:100101,run_url:'https://api.github.com/repos/other/repo/actions/runs/100101',
      html_url:'https://github.com/other/repo/actions/runs/100101'},
    {workflow_run_id:100101,run_url:'https://api.github.com/repos/ikst2512-eng/boat-edge-clean/actions/runs/100101',
      html_url:'https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/999'},
  ]){
    let posts=0; const receipts=[];const when=tick(7,10);
    const fetcher=async(url,options)=>{if(options.method==='POST'){posts++;return {status:200,json:async()=>broken};}
      return valid.fetcher(url,options);};
    await assert.rejects(()=>execute({scheduledTime:when,now:when,token:'TEST',
      fetcher,onAccepted:x=>receipts.push(x)}),/github_dispatch_run_details_missing_or_invalid/);
    assert.equal(posts,1);assert.deepEqual(receipts,[]);
  }
  const when=tick(7,10);
  const fetcher=async(url,options)=>options.method==='POST'?{status:200,json:async()=>{throw Error('invalid JSON');}}:valid.fetcher(url,options);
  await assert.rejects(()=>execute({scheduledTime:when,now:when,token:'TEST',fetcher}),/github_dispatch_run_details_missing_or_invalid/);
});

test('GitHub 401/403/404/429/500/503 POST errors never become run evidence',async()=>{
  for(const status of [401,403,404,429,500,503]){
    const m=mock({postStatus:status}), receipts=[];const when=tick(7,10);
    await assert.rejects(()=>execute({scheduledTime:when,now:when,token:'TEST',
      fetcher:m.fetcher,onAccepted:x=>receipts.push(x)}),/github_external_dispatch_not_accepted/);
    assert.deepEqual(receipts,[]);
    assert.equal(m.calls.filter(x=>x.method==='POST').length,1);
  }
});

test('dedicated observer exports only default and has no dispatch-capable handler',()=>{
  assert.deepEqual(Object.keys(observerExports),['default']);
  assert.deepEqual(Object.keys(observerWorker),['scheduled']);
  const source=readFileSync(new URL('../cloudflare/independent_capture_observer.mjs',import.meta.url),'utf8');
  // Comments describe forbidden capabilities; inspect executable source only.
  const src=source.replace(/^\s*\/\/.*$/gm,'');
  assert.doesNotMatch(src,/\bexecute\s*\(/);
  assert.doesNotMatch(src,/\bfetch\s*\(/);
  assert.doesNotMatch(src,/GITHUB_DISPATCH_TOKEN/);
  assert.doesNotMatch(src,/workflow_dispatch/);
});

test('dedicated observer cannot dispatch even if production flag is true and token is injected',async()=>{
  const oldNow=Date.now,oldFetch=globalThis.fetch,oldLog=console.log;
  const when=tick(7,10),requests=[],logs=[];
  Date.now=()=>when;
  globalThis.fetch=async (...args)=>{requests.push(args);throw Error('OBSERVER_MUST_NOT_FETCH');};
  console.log=x=>logs.push(String(x));
  try{
    await observerWorker.scheduled({cron:'*/5 22-23,0-13 * * *',scheduledTime:when},{
      CLOUDFLARE_DISPATCH_ENABLED:'true',
      GITHUB_DISPATCH_TOKEN:'FAKE_MISCONFIGURED_TOKEN',
    },{});
  }finally{Date.now=oldNow;globalThis.fetch=oldFetch;console.log=oldLog;}
  assert.deepEqual(requests,[]);
  assert.equal(logs.length,1);
  assert.ok(logs[0].startsWith('CLOUDFLARE_CAPTURE_OBSERVER_ONLY='));
  const d=JSON.parse(logs[0].split('=')[1]);
  assert.equal(d.github_history_checked,false);
  assert.equal(d.new_forecast_saved_proven,false);
  assert.ok(!logs.join(' ').includes('FAKE_MISCONFIGURED_TOKEN'));
});

test('dedicated observer rejects foreign cron before any GitHub API request',async()=>{
  const prev=globalThis.fetch,prevError=console.error;
  let requests=0; const errors=[];
  globalThis.fetch=async()=>{requests++;throw Error('OBSERVER_MUST_NOT_FETCH');};
  console.error=x=>errors.push(String(x));
  try{
    await assert.rejects(()=>observerWorker.scheduled({cron:'* * * * *',scheduledTime:tick(7,10)},{},{}),
      /unexpected_cron_trigger/);
  }finally{globalThis.fetch=prev;console.error=prevError;}
  assert.equal(requests,0);
  assert.equal(errors.length,1);
  assert.ok(errors[0].includes('CLOUDFLARE_CAPTURE_OBSERVER_ERROR='));
});

test('Worker entrypoint exports only the default scheduled handler (real workerd constraint)',()=>{
  assert.deepEqual(Object.keys(workerEntrypointExports),['default']);
  assert.equal(typeof workerEntrypointExports.default.scheduled,'function');
});

test('PR policy tests use read-only permissions and never execute under the operational write token',()=>{
  const yaml=readFileSync(new URL('../.github/workflows/four-mode-capture-watchdog.yml',import.meta.url),'utf8');
  const integration=yaml.split('\n  cloudflare-workerd-integration:\n')[1]?.split('\n  pr-policy-tests:\n')[0];
  const pr=yaml.split('\n  pr-policy-tests:\n')[1]?.split('\n  watchdog:\n')[0];
  const operational=yaml.split('\n  watchdog:\n')[1];
  assert.ok(integration && pr && operational,'all three jobs must remain present');
  for(const block of [integration,pr]){
    assert.ok(block.includes('permissions:\n      contents: read'),'PR jobs require read-only permissions');
    assert.ok(!block.includes('actions: write'),'PR jobs must never request Actions write');
    assert.ok(block.includes('persist-credentials: false'),'do not persist checkout auth');
  }
  assert.ok(pr.includes("github.event_name == 'pull_request'"));
  assert.ok(pr.includes('Test dispatch policy'));
  assert.ok(pr.includes('Run Cloudflare external wakeup safety tests'));
  assert.ok(operational.includes("github.event_name != 'pull_request'"),'privileged job cannot run on PR');
  assert.ok(operational.includes('actions: write'),'preserve operational dispatch permission');
  assert.ok(!operational.includes('Run Cloudflare external wakeup safety tests'),'no PR code under privileged job');
  assert.equal((yaml.match(/- cron:/g)||[]).length,4,'preserve four original fallback cron expressions');
});


import {AUDIT_SCHEMA, OBSERVER_NAME, expectedObserverTicks, auditObserverTelemetry}
  from '../cloudflare/audit_observer_telemetry.mjs';

function syntheticObserverDay(utc_day = '2026-11-09') {
  const ticks = expectedObserverTicks(utc_day);
  return {
    schema: AUDIT_SCHEMA, worker: OBSERVER_NAME,
    source: 'cloudflare_workers_invocation_and_custom_logs',
    complete_export: true, deployment_id: 'TEST-DEPLOY-ONLY',
    utc_day,
    samples: ticks.map((tick, index) => {
      const observed = tick + 1000;
      return {
        request_id: 'synthetic-test-' + index,
        cron: '*/5 22-23,0-13 * * *',
        scheduled_at_utc: new Date(tick).toISOString(),
        observed_at_utc: new Date(observed).toISOString(),
        cpu_time_ms: 2.5, outcome: 'ok',
        custom_report: observe({scheduledTime:tick,now:observed}),
      };
    }),
  };
}

test('observer CPU audit requires all 192 configured UTC daily Cron ticks with real CPU metadata',()=>{
  const out=auditObserverTelemetry(syntheticObserverDay());
  assert.equal(out.expected_ticks,192);
  assert.equal(out.unique_observed_ticks,192);
  assert.equal(out.missing_ticks,0);
  assert.equal(out.cpu_ms.max,2.5);
  assert.equal(out.observer_day_pass,true);
  assert.equal(out.original_cloudflare_log_authenticity_independently_proven,false);
  assert.equal(out.actual_github_dispatch_proven,false);
  assert.equal(out.formal_t_minus_12_proven,false);
});

test('observer telemetry rejects any missing UTC tick, never treating partial logs as a complete day',()=>{
  const e=syntheticObserverDay();e.samples.pop();
  const out=auditObserverTelemetry(e);
  assert.equal(out.missing_ticks,1);
  assert.equal(out.observer_day_pass,false);
  assert.ok(out.issues.some(x=>x.includes('missing_scheduled_ticks')));
});

test('observer telemetry rejects duplicate scheduled invocations even with distinct request IDs',()=>{
  const e=syntheticObserverDay();
  e.samples.push({...e.samples[1],request_id:'synthetic-extra-request'});
  const out=auditObserverTelemetry(e);
  assert.equal(out.samples_supplied,193);
  assert.equal(out.observer_day_pass,false);
  assert.ok(out.issues.some(x=>x.includes('duplicate_scheduled_tick')));
});

test('observer telemetry rejects Cloudflare CPU time over the Free per-cron 10 ms ceiling',()=>{
  const e=syntheticObserverDay();e.samples[0].cpu_time_ms=10.01;
  const out=auditObserverTelemetry(e);
  assert.equal(out.cpu_ms.max,10.01);
  assert.equal(out.observer_day_pass,false);
  assert.ok(out.issues.some(x=>x.includes('cpu_over_10ms')));
});

test('observer telemetry rejects missing CPU measurement and exceededCpu outcomes',()=>{
  const e=syntheticObserverDay();delete e.samples[0].cpu_time_ms;e.samples[1].outcome='exceededCpu';
  const out=auditObserverTelemetry(e);
  assert.equal(out.observer_day_pass,false);
  assert.ok(out.issues.some(x=>x.includes('cpu_measurement_missing_or_invalid')));
  assert.ok(out.issues.some(x=>x.includes('non_ok_invocation_outcome')));
});

test('observer telemetry rejects delayed Cron beyond the existing 90s admission window',()=>{
  const e=syntheticObserverDay();
  const tick=Date.parse(e.samples[0].scheduled_at_utc);
  e.samples[0].observed_at_utc=new Date(tick+90_001).toISOString();
  const out=auditObserverTelemetry(e);
  assert.equal(out.observer_day_pass,false);
  assert.ok(out.issues.some(x=>x.includes('late_future_or_invalid_observation')));
});

test('observer telemetry rejects a forged or mismatched no-network custom observer report',()=>{
  const e=syntheticObserverDay();
  e.samples[0].custom_report.github_history_checked=true;
  e.samples[1].custom_report.eligible_slots_jst.clean='fake';
  const out=auditObserverTelemetry(e);
  assert.equal(out.observer_day_pass,false);
  assert.ok(out.issues.some(x=>x.includes('observer_report_missing_or_mismatched')));
});

test('observer telemetry rejects wrong worker, missing provenance and incomplete export attestations',()=>{
  const e=syntheticObserverDay();
  e.worker='different-worker';e.source='manually-guessed';e.complete_export=false;e.deployment_id='';
  const out=auditObserverTelemetry(e);
  assert.equal(out.observer_day_pass,false);
  for(const reason of ['unexpected_worker','source_not_asserted','export_not_asserted_complete','deployment_identity_missing_or_invalid'])
    assert.ok(out.issues.includes(reason));
});

test('observer telemetry rejects malformed day and out-of-cron samples',()=>{
  assert.throws(()=>expectedObserverTicks('2026-11-31'),/invalid_utc_day/);
  const e=syntheticObserverDay();
  e.samples[0].scheduled_at_utc='2026-11-09T15:00:00.000Z';
  const out=auditObserverTelemetry(e);
  assert.equal(out.observer_day_pass,false);
  assert.ok(out.issues.some(x=>x.includes('unexpected_scheduled_tick')));
  assert.equal(out.missing_ticks,1);
});


import {spawnSync} from 'node:child_process';
import {mkdtempSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';

test('observer telemetry CLI returns exit 0 and nonformal JSON on full synthetic day',()=>{
  const dir=mkdtempSync(join(tmpdir(),'boat-edge-observer-audit-'));
  try{
    const path=join(dir,'normalized.json');
    writeFileSync(path,JSON.stringify(syntheticObserverDay()),'utf8');
    const cli=fileURLToPath(new URL('../scripts/audit_cloudflare_observer_telemetry.mjs',import.meta.url));
    const child=spawnSync(process.execPath,[cli,path],{encoding:'utf8',timeout:15000});
    assert.equal(child.status,0,child.stderr);
    const output=JSON.parse(child.stdout);
    assert.equal(output.expected_ticks,192);
    assert.equal(output.observer_day_pass,true);
    assert.equal(output.actual_github_dispatch_proven,false);
    assert.equal(output.formal_t_minus_12_proven,false);
  }finally{rmSync(dir,{recursive:true,force:true});}
});

test('observer telemetry CLI returns nonzero and no fake success for incomplete data',()=>{
  const dir=mkdtempSync(join(tmpdir(),'boat-edge-observer-audit-'));
  try{
    const path=join(dir,'normalized.json');
    const data=syntheticObserverDay();data.samples.pop();
    writeFileSync(path,JSON.stringify(data),'utf8');
    const cli=fileURLToPath(new URL('../scripts/audit_cloudflare_observer_telemetry.mjs',import.meta.url));
    const child=spawnSync(process.execPath,[cli,path],{encoding:'utf8',timeout:15000});
    assert.equal(child.status,1,child.stderr);
    assert.equal(JSON.parse(child.stdout).observer_day_pass,false);
    assert.equal(JSON.parse(child.stdout).missing_ticks,1);
  }finally{rmSync(dir,{recursive:true,force:true});}
});


import {auditRawWorkersLogs,RAW_LOG_SCHEMA} from '../cloudflare/audit_observer_raw_logs.mjs';

function syntheticRawWorkersDay() {
  const d=syntheticObserverDay();
  const records=d.samples.flatMap(sample=>{
    const id=sample.request_id;
    const observed=Date.parse(sample.observed_at_utc);
    const base={service:OBSERVER_NAME,requestId:id};
    return [{
      '$metadata':{...base,id:id+'-invocation',type:'cf-worker-event',message:'*/5 22-23,0-13 * * *'},
      '$workers':{scriptName:OBSERVER_NAME,eventType:'scheduled',outcome:'ok',
        cpuTimeMs:sample.cpu_time_ms,scriptVersion:{id:d.deployment_id}},
      timestamp:observed+2,source:{message:'cron'},
    },{
      '$metadata':{...base,id:id+'-console',type:'cf-worker-log',message:'CLOUDFLARE_CAPTURE_OBSERVER_ONLY='+JSON.stringify(sample.custom_report)},
      '$workers':{scriptName:OBSERVER_NAME,eventType:'scheduled',scriptVersion:{id:d.deployment_id}},
      timestamp:observed,source:{message:'CLOUDFLARE_CAPTURE_OBSERVER_ONLY='+JSON.stringify(sample.custom_report)},
    }];
  });
  return {schema:RAW_LOG_SCHEMA,worker:OBSERVER_NAME,utc_day:d.utc_day,
    deployment_id:d.deployment_id,complete_export:true,all_pages_fetched:true,
    sample_interval:1,total_matched_events:records.length,records};
}

test('raw Workers Logs audit correlates 192 invocation and 192 custom events by request ID',()=>{
  const r=auditRawWorkersLogs(syntheticRawWorkersDay());
  assert.equal(r.supplied_raw_records,384);
  assert.equal(r.correlated_invocations,192);
  assert.equal(r.cpu_ms.max,2.5);
  assert.equal(r.observer_day_pass,true);
  assert.equal(r.original_cloudflare_log_authenticity_independently_proven,false);
  assert.equal(r.actual_github_dispatch_proven,false);
});

test('raw Workers Logs audit refuses sampled or incomplete/paginated queries',()=>{
  for(const change of [x=>x.sample_interval=2,x=>x.all_pages_fetched=false,
      x=>x.complete_export=false,x=>x.total_matched_events=1000]){
    const x=syntheticRawWorkersDay();change(x);
    const r=auditRawWorkersLogs(x);
    assert.equal(r.observer_day_pass,false);
    assert.ok(r.raw_issue_count>=1);
  }
});

test('raw Workers Logs audit requires a real invocation CPU field, not custom log wall-time',()=>{
  const x=syntheticRawWorkersDay();delete x.records[0].$workers.cpuTimeMs;
  const r=auditRawWorkersLogs(x);
  assert.equal(r.observer_day_pass,false);
  assert.ok(r.issues.some(q=>q.includes('cpu_measurement_missing_or_invalid')));
});

test('raw Workers Logs audit rejects crossed deployment version IDs',()=>{
  const x=syntheticRawWorkersDay();x.records[0].$workers.scriptVersion.id='DIFFERENT-VERSION';
  const r=auditRawWorkersLogs(x);
  assert.equal(r.observer_day_pass,false);
  assert.ok(r.raw_issues.includes('invocation_version_mismatch'));
  assert.equal(r.missing_ticks,1);
});

test('raw Workers Logs audit refuses missing custom reports and duplicated invocation logs',()=>{
  for(const mutate of [x=>{x.records.splice(1,1);x.total_matched_events=x.records.length;},
      x=>{x.records.push(structuredClone(x.records[0]));x.total_matched_events=x.records.length;}]) {
    const x=syntheticRawWorkersDay();mutate(x);
    const r=auditRawWorkersLogs(x);
    assert.equal(r.observer_day_pass,false);
    assert.ok(r.raw_issues.includes('request_record_cardinality_invalid'));
  }
});

test('raw Workers Logs audit refuses conflicting cron metadata or mismatched invocation identity',()=>{
  for(const mutate of [x=>x.records[0].$metadata.message='* * * * *',
      x=>x.records[0].$workers.scriptName='untrusted-worker',
      x=>x.records[1].$metadata.requestId='different-request']) {
    const x=syntheticRawWorkersDay();mutate(x);
    const r=auditRawWorkersLogs(x);
    assert.equal(r.observer_day_pass,false);
    assert.ok(r.raw_issue_count>=1);
  }
});

test('raw Workers Logs audit rejects fake custom timestamps and fabricated observer reports',()=>{
  const x=syntheticRawWorkersDay();
  x.records[1].timestamp+=30000;
  x.records[3].$metadata.message='CLOUDFLARE_CAPTURE_OBSERVER_ONLY={"schema":"FAKE"}';
  const r=auditRawWorkersLogs(x);
  assert.equal(r.observer_day_pass,false);
  assert.ok(r.raw_issues.some(q=>q==='cloudflare_event_clock_mismatch'||q==='missing_or_malformed_observer_console_log'));
});

test('raw Workers Logs audit CLI executes locally without authentication or network',()=>{
  const dir=mkdtempSync(join(tmpdir(),'boat-edge-raw-observer-audit-'));
  try{
    const path=join(dir,'workers-logs.json');
    writeFileSync(path,JSON.stringify(syntheticRawWorkersDay()),'utf8');
    const cli=fileURLToPath(new URL('../scripts/audit_cloudflare_observer_telemetry.mjs',import.meta.url));
    const child=spawnSync(process.execPath,[cli,path],{encoding:'utf8',timeout:15000});
    assert.equal(child.status,0,child.stderr);
    const result=JSON.parse(child.stdout);
    assert.equal(result.observer_day_pass,true);
    assert.equal(result.raw_issue_count,0);
    assert.match(result.input_sha256,/^[a-f0-9]{64}$/);
    assert.equal(result.formal_t_minus_12_proven,false);
  }finally{rmSync(dir,{recursive:true,force:true});}
});


test('closed observer schema rejects extra false-positive dispatch claims',()=>{
  for(const poison of [
    x=>x.samples[0].custom_report.github_dispatch_accepted=true,
    x=>x.samples[0].custom_report.eligible_slots_jst.unexpected='fake',
    x=>x.samples[0].custom_report.extra_evidence={github_run_id:12345},
  ]){
    const x=syntheticObserverDay();poison(x);
    const result=auditObserverTelemetry(x);
    assert.equal(result.observer_day_pass,false);
    assert.ok(result.issues.some(q=>q.includes('observer_report_missing_or_mismatched')));
  }
});

test('Cloudflare raw auditor rejects repeated or missing event cursor even when request pairs look valid',()=>{
  for(const mutate of [
    x=>x.records[2].$metadata.id=x.records[0].$metadata.id,
    x=>delete x.records[2].$metadata.id,
  ]){
    const x=syntheticRawWorkersDay();mutate(x);
    const result=auditRawWorkersLogs(x);
    assert.equal(result.observer_day_pass,false);
    assert.ok(result.raw_issues.some(q=>q.includes('event_cursor')));
  }
});


test('SQLite claim lab remains completely detached from production and observer',()=>{
  const source=readFileSync(new URL('../cloudflare/claim_lab_only.mjs',import.meta.url),'utf8');
  const config=readFileSync(new URL('../cloudflare/wrangler.claim-lab.toml',import.meta.url),'utf8');
  const prod=readFileSync(new URL('../cloudflare/independent_capture_wakeup.mjs',import.meta.url),'utf8');
  const pureObserver=readFileSync(new URL('../cloudflare/independent_capture_observer.mjs',import.meta.url),'utf8');
  const prodConfig=readFileSync(new URL('../cloudflare/wrangler.toml',import.meta.url),'utf8');
  const observerConfig=readFileSync(new URL('../cloudflare/wrangler.observer.toml',import.meta.url),'utf8');
  assert.match(config,/name = "boat-edge-clean-claims-local-research-only"/);
  assert.match(config,/main = "claim_lab_only.mjs"/);
  assert.match(config,/workers_dev = false/);
  assert.match(config,/crons = \[\]/);
  assert.match(config,/new_sqlite_classes = \["CaptureClaimResearch"\]/);
  assert.doesNotMatch(config,/GITHUB_DISPATCH_TOKEN|\[secrets\]|routes?\s*=/);
  assert.doesNotMatch(prod, /claim_lab_only|CLAIMS_RESEARCH|CaptureClaimResearch/);
  assert.doesNotMatch(pureObserver, /claim_lab_only|CLAIMS_RESEARCH|CaptureClaimResearch/);
  assert.doesNotMatch(prodConfig, /CLAIMS_RESEARCH|CaptureClaimResearch/);
  assert.doesNotMatch(observerConfig, /CLAIMS_RESEARCH|CaptureClaimResearch/);
  const active=source.replace(/^\s*\/\/.*$/gm,'');
  assert.doesNotMatch(active,/api\.github\.com|GITHUB_DISPATCH_TOKEN|\/dispatches|Authorization/);
  assert.doesNotMatch(active,/\bfetch\s*\(.*github/i);
  assert.doesNotMatch(active,/\bscheduled\s*\(/);
});

test('research gate has immutable claim-key invariant, no clear/retry/release path',()=>{
  const source=readFileSync(new URL('../cloudflare/claim_lab_only.mjs',import.meta.url),'utf8');
  assert.match(source,/PRIMARY KEY\(kind,slot_ms\)/);
  assert.match(source,/ON CONFLICT DO NOTHING RETURNING slot_ms/);
  assert.doesNotMatch(source,/DELETE FROM research_claims|DROP TABLE|UPDATE research_claims SET kind|\bclearClaim\s*\(/);
});


/* CROSS_PROVIDER_QUEUE_LAB_REGRESSION — negative evidence, NOT a production fix. */
import {CURRENT_NATIVE_QUEUES, simulateGitHubConcurrency, counterexamples}
  from '../cloudflare/cross_provider_queue_lab.mjs';

test('actual native capture YAML has CLEAN default pending replacement and four-mode queue max',()=>{
  const clean=readFileSync(new URL('../.github/workflows/clean-prospective.yml',import.meta.url),'utf8');
  const four=readFileSync(new URL('../.github/workflows/four-mode-prospective-capture.yml',import.meta.url),'utf8');
  function block(yaml){
    const found=yaml.match(/^concurrency:\s*\n([\s\S]*?)^jobs:/m);
    assert.ok(found,'missing workflow concurrency group');
    return found[1].split('\n').filter(x=>!x.trim().startsWith('#')).join('\n');
  }
  const c=block(clean),f=block(four);
  assert.match(c,/group:.*clean-prospective-capture/);
  assert.match(f,/group:.*four-mode-publication/);
  assert.match(c,/cancel-in-progress:\s*false/);
  assert.match(f,/cancel-in-progress:\s*false/);
  assert.doesNotMatch(c,/^\s*queue:\s*max\s*$/m,'CLEAN still has one replaceable pending slot');
  assert.match(f,/^\s*queue:\s*max\s*$/m,'four-mode has up to 100 pending slots');
  assert.equal(CURRENT_NATIVE_QUEUES.clean.queue,'single');
  assert.equal(CURRENT_NATIVE_QUEUES.four_mode.queue,'max');
});

test('counterexample: one Cloudflare rescue can replace queued native CLEAN schedule',()=>{
  const r=simulateGitHubConcurrency({queue:'single',running:'old_capture_running',
    arrivals:['native_schedule_new_slot','cloudflare_recovery_same_slot']});
  assert.deepEqual(r.canceled,['native_schedule_new_slot']);
  assert.deepEqual(r.pending,['cloudflare_recovery_same_slot']);
  assert.equal(r.production_dispatch_safe,false);
});

test('counterexample: even one atomic Cloudflare DO claim cannot protect native CLEAN pending job',()=>{
  // Assume the perfect Cloudflare-internal deduplication outcome:
  // only one rescue can reach GitHub from Cloudflare. Native schedule is
  // outside that DO, and can still be replaced in a GitHub single queue.
  const r=simulateGitHubConcurrency({queue:'single',running:'old_capture_running',
    arrivals:['native_schedule_new_slot','single_cloudflare_DO_claim_winner']});
  assert.deepEqual(r.canceled,['native_schedule_new_slot']);
  assert.equal(r.verified_cross_provider_idempotency,false);
});

test('four-mode queue max retains duplicate requests: serial execution is not exactly once',()=>{
  const r=simulateGitHubConcurrency({queue:'max',running:'old_four_mode_running',
    arrivals:['native_schedule_new_slot','cloudflare_claim_winner_same_slot',
      'second_uncoordinated_provider_same_slot']});
  assert.deepEqual(r.canceled,[]);
  assert.equal(r.pending.length,3);
  assert.equal(r.production_dispatch_safe,false);
});

test('four-mode queue max cancels new rescue if 100 other requests are already pending',()=>{
  const arrivals=Array.from({length:100},(_,i)=>'queued_'+i);
  const r=simulateGitHubConcurrency({queue:'max',running:'old_four_mode_running',
    arrivals:[...arrivals,'cloudflare_recovery_new_slot']});
  assert.equal(r.pending.length,100);
  assert.deepEqual(r.canceled,['cloudflare_recovery_new_slot']);
  assert.equal(r.trace.at(-1).action,'queue_full_canceled');
  assert.equal(r.actual_github_run_evidence,false);
});

test('cross-provider counterexample summary keeps recovery NO-GO and no event evidence',()=>{
  const x=counterexamples();
  assert.equal(x.clean_original_schedule_displaced,true);
  assert.equal(x.four_mode_duplicate_pending.length,2);
  assert.equal(x.four_mode_saturated_recovery_canceled,true);
  assert.equal(x.github_runtime_behavior_independently_observed,false);
  assert.equal(x.cross_provider_safe,false);
  assert.equal(x.recovery_release_approved,false);
});


test('late native CLEAN schedule appears after four complete GETs but before Cloudflare POST: pending original can be displaced',async()=>{
  // Real execute() uses four complete, self-consistent GitHub history pages.
  // GitHub may create a delayed schedule run immediately AFTER those reads.
  // This models the documented concurrency queue; it does NOT perform a real dispatch.
  const now=tick(7,10),m=mock(),receipts=[];
  let sawCleanPost=false;
  const fetcher=async(url,options)=>{
    if(options.method==='POST' && url.includes('/'+WORKFLOWS.clean+'/')){
      sawCleanPost=true;
      assert.equal(m.calls.filter(x=>x.method==='GET').length,4);
      const q=simulateGitHubConcurrency({
        queue:'single',running:'previous_clean_capture_still_running',
        arrivals:['native_schedule_created_after_history_GET','cloudflare_POST_for_same_slot'],
      });
      assert.deepEqual(q.canceled,['native_schedule_created_after_history_GET']);
      assert.deepEqual(q.pending,['cloudflare_POST_for_same_slot']);
      assert.equal(q.production_dispatch_safe,false);
    }
    return m.fetcher(url,options);
  };
  const out=await execute({scheduledTime:now,now,token:'TEST_ONLY',fetcher,
    onAccepted:r=>receipts.push(r)});
  assert.equal(sawCleanPost,true);
  assert.equal(m.calls.filter(x=>x.method==='GET').length,4);
  assert.equal(m.calls.filter(x=>x.method==='POST').length,2);
  assert.equal(receipts.length,2);
  assert.equal(out.workflows.clean.github_run_id_reported,100101);
  assert.equal(out.formal,false);
  assert.equal(out.new_forecast_saved_proven,false);
  // Green test is NEGATIVE architectural evidence, NOT successful recovery.
});

test('late native four-mode schedule after complete GET produces two pending runs, not one publication',async()=>{
  const now=tick(7,10),m=mock();
  let captured=false;
  const fetcher=async(url,options)=>{
    if(options.method==='POST' && url.includes('/'+WORKFLOWS.four_mode+'/')){
      const q=simulateGitHubConcurrency({
        queue:'max',running:'prior_four_mode_capture_running',
        arrivals:['native_schedule_created_after_history_GET','cloudflare_POST_for_same_slot'],
      });
      assert.deepEqual(q.canceled,[]);
      assert.equal(q.pending.length,2);
      assert.equal(q.verified_cross_provider_idempotency,false);
      captured=true;
    }
    return m.fetcher(url,options);
  };
  const out=await execute({scheduledTime:now,now,token:'TEST_ONLY',fetcher});
  assert.equal(captured,true);
  assert.equal(out.workflows.four_mode.github_run_id_reported,100102);
  assert.equal(out.on_time_cron_proven,false);
  assert.equal(out.new_forecast_saved_proven,false);
  assert.equal(out.formal,false);
});

test('complete GitHub run history cannot be treated as a cross-provider lock after GET',async()=>{
  const now=tick(7,10),calls=[],nativeAfterRead=[];
  const mocker=mock();
  const fetcher=async(url,options)=>{
    calls.push(options.method);
    if(options.method==='GET'){
      const result=await mocker.fetcher(url,options);
      if(calls.filter(x=>x==='GET').length===4){
        nativeAfterRead.push('native_schedule_visible_only_after_GitHub_snapshot');
      }
      return result;
    }
    assert.equal(nativeAfterRead.length,1);
    return mocker.fetcher(url,options);
  };
  await execute({scheduledTime:now,now,token:'TEST_ONLY',fetcher});
  assert.deepEqual(calls,['GET','GET','GET','GET','POST','POST']);
  // No amount of first-page pagination validation can detect a future event.
  assert.equal(nativeAfterRead.length,1);
});


test('two possible CLEAN arrival orders cancel different pending runs under current single queue',()=>{
  const orders=[
    ['native_schedule_delayed','cloudflare_rescue'],
    ['cloudflare_rescue','native_schedule_delayed'],
  ];
  for(const order of orders){
    const q=simulateGitHubConcurrency({
      queue:'single',running:'old_clean_capture_running',arrivals:order,
    });
    assert.deepEqual(q.canceled,[order[0]],'new arrival replaces the other pending capture');
    assert.deepEqual(q.pending,[order[1]]);
    assert.equal(q.actual_github_run_evidence,false);
    assert.equal(q.production_dispatch_safe,false);
  }
});

test('counterfactual CLEAN queue max preserves both pending jobs, but does NOT prevent duplicates or full-queue loss',()=>{
  const both=simulateGitHubConcurrency({
    queue:'max',running:'old_clean_capture_running',
    arrivals:['native_schedule_delayed','cloudflare_rescue'],
  });
  assert.deepEqual(both.pending,['native_schedule_delayed','cloudflare_rescue']);
  assert.deepEqual(both.canceled,[]);
  assert.equal(both.verified_cross_provider_idempotency,false);
  // The 101st new pending job is still canceled by GitHub's documented limit.
  const saturated=simulateGitHubConcurrency({
    queue:'max',running:'old_clean_capture_running',
    arrivals:[...Array.from({length:100},(_,i)=>'unrelated_pending_'+i),'native_schedule_delayed'],
  });
  assert.deepEqual(saturated.canceled,['native_schedule_delayed']);
  assert.equal(saturated.production_dispatch_safe,false);
});


test('GitHub returned run IDs never attest the original slot without independent publication evidence',async()=>{
  const m=mock(),receipts=[],when=tick(7,10);
  const result=await execute({scheduledTime:when,now:when,token:'TEST_ONLY',
    fetcher:m.fetcher,onAccepted:r=>receipts.push(r)});
  assert.equal(receipts.length,2);
  for(const kind of Object.keys(WORKFLOWS)){
    assert.equal(result.workflows[kind].github_execution_slot_bound_proven,false);
    assert.equal(result.workflows[kind].new_forecast_saved_proven,undefined);
    assert.equal(typeof result.workflows[kind].github_run_id_reported,'number');
  }
  for(const receipt of receipts){
    assert.equal(receipt.github_execution_slot_bound_proven,false);
    assert.equal(receipt.github_run_id_proven,false);
    assert.equal(receipt.new_forecast_saved_proven,false);
    assert.equal(receipt.formal,false);
    // Never pass a recovery-slot claim to the native workflow unless the
    // native publisher owners introduce an independently audited protocol.
  }
  assert.ok(m.calls.filter(c=>c.method==='POST').every(c=>
    JSON.stringify(JSON.parse(c.body))===JSON.stringify({ref:'main',return_run_details:true})));
});

test('native workflow_dispatch has no capture-slot contract and current collectors use execution-time clocks',()=>{
  const clean=readFileSync(new URL('../.github/workflows/clean-prospective.yml',import.meta.url),'utf8');
  const four=readFileSync(new URL('../.github/workflows/four-mode-prospective-capture.yml',import.meta.url),'utf8');
  for(const [kind,yaml] of [['clean',clean],['four_mode',four]]){
    assert.match(yaml,/^  workflow_dispatch:\s*$/m,kind);
    // Isolate the on: trigger section rather than mistaking unrelated
    // inputs in job steps for workflow_dispatch event parameters.
    const beforePr=yaml.split(/^  pull_request:/m)[0];
    assert.doesNotMatch(beforePr,/^    inputs:\s*$/m,
      kind+': current native workflow cannot receive an explicit target slot');
  }
  const cleanCollector=readFileSync(new URL('../collect_clean_prospective.py',import.meta.url),'utf8');
  const fourCollector=readFileSync(new URL('../clean_four_mode_capture.py',import.meta.url),'utf8');
  assert.match(cleanCollector,/def collect\(day=None\):\s*\n\s*now = datetime\.now\(JST\)/);
  assert.match(fourCollector,/def collect\(root=ROOT, now=None, read=read_rows\):\s*\n\s*now_is_live = now is None\s*\n\s*now=now or datetime\.now\(JST\)/);
  const policy=readFileSync(new URL('../cloudflare/independent_capture_policy.mjs',import.meta.url),'utf8');
  assert.match(policy,/github_execution_slot_bound_proven = false/);
  assert.match(policy,/github_execution_slot_bound_proven: false/);
});


import {auditTelemetryApiPages,API_SCHEMA} from '../cloudflare/audit_observer_api_pages.mjs';

function syntheticApiTelemetryDay() {
  const raw=syntheticRawWorkersDay(),start=Date.parse(raw.utc_day+'T00:00:00Z');
  const timeframe={from:start,to:start+86400000};
  const filters={kind:'filter',key:'$metadata.service',value:OBSERVER_NAME,type:'string',operation:'eq'};
  return {schema:API_SCHEMA,utc_day:raw.utc_day,worker:raw.worker,
    deployment_id:raw.deployment_id,
    events_query:{
      request:{view:'events',timeframe:{...timeframe},limit:2000,filters:structuredClone(filters)},
      response:{status:'COMPLETED',timeframe:{...timeframe},
        events:{count:raw.records.length,events:raw.records}}},
    sampling_query:{
      request:{view:'calculations',timeframe:{...timeframe},filters:structuredClone(filters)},
      response:{status:'COMPLETED',timeframe:{...timeframe},
        calculations:[{aggregates:[{count:raw.records.length,sampleInterval:1}]}]}},
  };
}

test('Telemetry API wrapper derives complete 384 event / unsampled day from two real-shaped responses',()=>{
  const report=auditTelemetryApiPages(syntheticApiTelemetryDay());
  assert.equal(report.api_query_structure_pass,true);
  assert.equal(report.observer_day_pass,true);
  assert.equal(report.unique_observed_ticks,192);
  assert.equal(report.cpu_ms.max,2.5);
  assert.equal(report.actual_cloudflare_api_authenticity_independently_proven,false);
  assert.equal(report.actual_github_dispatch_proven,false);
  assert.equal(report.immutable_forecast_first_add_proven,false);
  assert.equal(report.formal_t_minus_12_proven,false);
});

test('Telemetry API wrapper rejects truncation, event count mismatch and sampled metrics',()=>{
  for(const poison of [
    x=>x.events_query.response.events.count=385,
    x=>x.events_query.response.events.events.pop(),
    x=>x.sampling_query.response.calculations[0].aggregates[0].sampleInterval=2,
    x=>x.sampling_query.response.calculations[0].aggregates[0].count=383,
    x=>x.sampling_query.response.calculations.push({aggregates:[{count:384,sampleInterval:1}]}),
    x=>x.sampling_query.response.calculations[0].aggregates.push({count:384,sampleInterval:1}),
  ]) {
    const input=syntheticApiTelemetryDay();poison(input);
    const result=auditTelemetryApiPages(input);
    assert.equal(result.observer_day_pass,false);
    assert.equal(result.api_query_structure_pass,false);
    assert.ok(result.api_issue_count>=1);
  }
});

test('Telemetry API wrapper rejects unsafe timeframe, query view, filters and cursor',()=>{
  for(const poison of [
    x=>x.events_query.request.timeframe.from+=60000,
    x=>x.events_query.response.timeframe.to-=60000,
    x=>x.sampling_query.request.timeframe.to+=60000,
    x=>x.sampling_query.response.timeframe.from-=60000,
    x=>x.events_query.request.limit=100,
    x=>x.events_query.request.offset='unreviewed-cursor',
    x=>x.sampling_query.request.filters.value='different-worker',
    x=>x.events_query.request.filters.kind='other-filter',
    x=>x.events_query.response.status='STARTED',
    x=>x.sampling_query.response.status='STARTED',
  ]){
    const input=syntheticApiTelemetryDay();poison(input);
    const result=auditTelemetryApiPages(input);
    assert.equal(result.observer_day_pass,false);
    assert.ok(result.api_issue_count>=1);
  }
});

test('Telemetry API must reject equally unscoped or wrong-Worker event/calculation filters',()=>{
  for(const poison of [
    x=>{x.events_query.request.filters={};x.sampling_query.request.filters={};},
    x=>{x.events_query.request.filters.value='different-worker';x.sampling_query.request.filters.value='different-worker';},
    x=>{x.events_query.request.filters.key='$metadata.message';x.sampling_query.request.filters.key='$metadata.message';},
    x=>{x.events_query.request.filters.operation='includes';x.sampling_query.request.filters.operation='includes';},
    x=>{x.events_query.request.filters.kind='group';x.sampling_query.request.filters.kind='group';},
    x=>{x.events_query.request.filters.extra='poison';x.sampling_query.request.filters.extra='poison';},
  ]){
    const input=syntheticApiTelemetryDay();poison(input);
    const out=auditTelemetryApiPages(input);
    assert.equal(out.observer_day_pass,false);
    assert.equal(out.api_query_structure_pass,false);
    assert.ok(out.api_issues.includes('api_observer_service_scope_not_proven'),JSON.stringify(out.api_issues));
    assert.equal(out.actual_cloudflare_api_authenticity_independently_proven,false);
  }
});

test('Telemetry API wrapper CLI accepts exact response envelope but never certifies genuine account',()=>{
  const dir=mkdtempSync(join(tmpdir(),'boat-edge-telemetry-query-'));
  try {
    const path=join(dir,'telemetry-api.json');
    writeFileSync(path,JSON.stringify(syntheticApiTelemetryDay()),'utf8');
    const cli=fileURLToPath(new URL('../scripts/audit_cloudflare_observer_telemetry.mjs',import.meta.url));
    const child=spawnSync(process.execPath,[cli,path],{encoding:'utf8',timeout:15000});
    assert.equal(child.status,0,child.stderr);
    const result=JSON.parse(child.stdout);
    assert.equal(result.observer_day_pass,true);
    assert.match(result.input_sha256,/^[a-f0-9]{64}$/);
    assert.equal(result.actual_cloudflare_api_authenticity_independently_proven,false);
    assert.equal(result.formal_t_minus_12_proven,false);
  }finally{rmSync(dir,{recursive:true,force:true});}
});


test('CLEAN remote main receipt gap is independently identified against actual native YAML',()=>{
  const clean=readFileSync(new URL('../.github/workflows/clean-prospective.yml',import.meta.url),'utf8');
  const mode=readFileSync(new URL('../.github/workflows/four-mode-prospective-capture.yml',import.meta.url),'utf8');
  const out=auditNativePublisherPair(clean,mode);
  assert.equal(out.clean.source_contains_main_push,true);
  assert.equal(out.clean.post_push_remote_main_ancestry_check,false);
  assert.equal(out.clean.exact_published_commit_sha_captured,false);
  assert.equal(out.clean.publication_receipt_artifact_emitted,false);
  assert.equal(out.clean.source_level_receipt_contract_present,false);
  assert.equal(out.four_mode.post_push_remote_main_ancestry_check,true);
  assert.equal(out.four_mode.exact_published_commit_sha_captured,true);
  assert.equal(out.four_mode.publication_receipt_artifact_emitted,true);
  assert.equal(out.four_mode.source_level_receipt_contract_present,true);
  assert.equal(out.both_source_contracts_present,false);
  assert.equal(out.cross_provider_recovery_release_approved,false);
  assert.equal(out.clean.publication_immutable_first_add_proven,false);
  assert.equal(out.four_mode.publication_immutable_first_add_proven,false);
});

test('static native publication evidence gate requires executable post-push checks and JSON receipt',()=>{
  const header='name: illustrative\n';
  const push='  if git push origin HEAD:main; then\n';
  const check='  git fetch origin main\n  git merge-base --is-ancestor HEAD FETCH_HEAD\n';
  const evidence=[
    "  python - <<'PY'",
    'import subprocess,json',
    'from pathlib import Path',
    'sha = subprocess.check_output(',
    '  ["git", "rev-parse", "HEAD"], text=True).strip()',
    'target = Path("clean-capture-evidence/publication.json")',
    'target.write_text(json.dumps({"commit_sha": sha}), encoding="utf-8")',
    'PY',
  ].join('\n')+'\n';
  const success='  exit 0\n  fi\n';
  const clean=header+push+check+evidence+success;
  const accepted=auditNativePublisherPostPush(clean,'clean');
  assert.equal(accepted.source_level_receipt_contract_present,true);
  assert.equal(accepted.remote_publication_independently_observed,false);
  assert.equal(accepted.cross_provider_recovery_release_approved,false);
  for(const invalid of [
    header+check+evidence+push+success,
    header+push+evidence+success+check,
    header+push+'  git merge-base --is-ancestor HEAD FETCH_HEAD\n  git fetch origin main\n'+evidence+success,
    header+push+check+success+evidence,
    header+push+check+evidence.replace('commit_sha','other')+success,
    header+push+check+evidence.replace('target.write_text','print')+success,
    header+push+check+evidence.replace('subprocess.check_output','print')+success,
    header+push+check+evidence.replace('clean-capture-evidence','wrong-output')+success,
    header+push+check+evidence.replace('target.write_text(json.dumps','echo "$(target.write_text(json.dumps')+success,
    header+push+check+'  echo "git rev-parse HEAD"\n  echo \'"commit_sha"\' > clean-capture-evidence/publication.json\n'+success,
  ]){
    const out=auditNativePublisherPostPush(invalid,'clean');
    assert.equal(out.source_level_receipt_contract_present,false);
    assert.equal(out.cross_provider_recovery_release_approved,false);
  }
});

test('source-only comments and echo statements cannot fabricate a successful native post-push receipt',()=>{
  const native='  if git push origin HEAD:main; then\n';
  const fake=[
    '  # git fetch origin main',
    '  # git merge-base --is-ancestor HEAD FETCH_HEAD',
    '  echo "git fetch origin main"',
    '  echo "git merge-base --is-ancestor HEAD FETCH_HEAD"',
    '  # sha = subprocess.check_output(["git", "rev-parse", "HEAD"])',
    '  # target = Path("clean-capture-evidence/publication.json")',
    '  # target.write_text(json.dumps({"commit_sha": sha}))',
    '  exit 0',
  ].join('\n');
  const out=auditNativePublisherPostPush(native+fake,'clean');
  assert.deepEqual(out.missing_contracts,[
    'remote_main_ancestry_after_push_not_checked',
    'exact_published_commit_sha_not_recorded_in_success_path',
    'published_commit_receipt_artifact_not_found',
  ]);
  assert.equal(out.cross_provider_recovery_release_approved,false);
  assert.throws(()=>auditNativePublisherPostPush('# '+native+fake,'clean'),/native_publisher_push_block_missing/);
});

test('native publisher receipt audit errors on missing success branch or unknown workflow',()=>{
  for(const [source,kind] of [
    ['name: no publication','clean'],
    ['if git push origin HEAD:main; then\n echo pending\n fi','four_mode'],
    ['if git push origin HEAD:main; then\n exit 0','unknown'],
  ]){
    assert.throws(()=>auditNativePublisherPostPush(source,kind),/invalid_native_publisher_source|native_publisher_push/);
  }
});


function syntheticLocalFirstAdd(kind='clean') {
  const code='202611090101',a='a'.repeat(64),b='b'.repeat(64);
  const record=kind==='clean' ? {
    race_code:code,status:'prospective_candidate',validated:false,formal:false,
    source_title_sha256:a,source_cards_sha256:b,
    input_sha256:createHash('sha256').update(a+':'+b).digest('hex'),
    source_deadline_jst:'2026-11-09T21:00:00+09:00',
    cutoff_jst:'2026-11-09T20:48:00+09:00',
    generated_at:'2026-11-09T20:20:00+09:00',
    source_title_received_jst:'2026-11-09T20:18:00+09:00',
    source_cards_received_jst:'2026-11-09T20:19:00+09:00',
  } : {
    schema:'CLEAN_FOUR_MODES_PREDEADLINE_V1',race_code:code,
    status:'provisional',validated:false,
    deadline_jst:'2026-11-09T21:00:00+09:00',
    generated_at_jst:'2026-11-09T20:20:00+09:00',
    source_title_received_jst:'2026-11-09T20:18:00+09:00',
    source_cards_received_jst:'2026-11-09T20:19:00+09:00',
    source_sha256:{title:a,race_cards:b},
    modes:{hit:[],balance:[],hole:[],narrow:[]},
  };
  const raw=JSON.stringify(record)+'\n',hash=computeLocalBlobHashes(raw);
  const path=(kind==='clean'?'prospective_predictions/':'four_mode_forecasts/')+code+'.json';
  return {
    schema:FIRST_ADD_LAB_SCHEMA,publisher:kind,
    repository:'ikst2512-eng/boat-edge-clean',branch:'main',
    github_run:{id:100123,workflow_path:'.github/workflows/'+
      (kind==='clean'?'clean-prospective.yml':'four-mode-prospective-capture.yml'),
      event:'workflow_dispatch',head_branch:'main',status:'completed',conclusion:'success'},
    reported_dispatch_run_id:100123,
    commit:{sha:'1'.repeat(40),parent_sha:'2'.repeat(40),
      committed_at_jst:'2026-11-09T20:30:00+09:00'},
    claimed_added_paths:[path],
    records:[{path,claimed_git_status:'added',original_git_blob_utf8:raw,
      claimed_git_blob_sha1:hash.git_blob_sha1,claimed_raw_sha256:hash.raw_sha256}],
  };
}
function rewriteLocalBlob(manifest, transform) {
  const row=manifest.records[0],data=JSON.parse(row.original_git_blob_utf8);
  transform(data);
  row.original_git_blob_utf8=JSON.stringify(data)+'\n';
  const hash=computeLocalBlobHashes(row.original_git_blob_utf8);
  row.claimed_git_blob_sha1=hash.git_blob_sha1;
  row.claimed_raw_sha256=hash.raw_sha256;
}

test('local first-add manifest validates CLEAN and four-mode original blob/clock contracts without certifying release',()=>{
  for(const kind of ['clean','four_mode']){
    const manifest=syntheticLocalFirstAdd(kind);
    const result=auditLocalFirstAddEvidence(manifest);
    assert.equal(result.local_content_consistency_pass,true,JSON.stringify(result.issues));
    assert.equal(result.records_checked,1);
    assert.equal(result.git_first_add_parent_tree_independently_proven,false);
    assert.equal(result.github_manifest_authenticity_independently_proven,false);
    assert.equal(result.remote_server_first_receipt_independently_proven,false);
    assert.equal(result.official_beforeinfo_six_boats_proven,false);
    assert.equal(result.odds_120_combinations_proven,false);
    assert.equal(result.official_t_minus_12_proven,false);
    assert.equal(result.cross_provider_recovery_release_approved,false);
  }
});

test('local first-add manifest fails on forged GitHub runs, altered source files, roster inconsistencies',()=>{
  const cases=[
    x=>x.github_run.id=100124,
    x=>x.github_run.event='pull_request',
    x=>x.github_run.head_branch='other',
    x=>x.github_run.status='queued',
    x=>x.github_run.workflow_path='.github/workflows/other.yml',
    x=>x.commit.parent_sha=x.commit.sha,
    x=>x.commit.committed_at_jst='2026-11-09T20:10:00+09:00',
    x=>x.commit.committed_at_jst='2026-11-09T21:00:00+09:00',
    x=>x.records[0].original_git_blob_utf8+=' ', // digest now mismatches
    x=>x.records[0].claimed_git_blob_sha1='0'.repeat(40),
    x=>x.records[0].claimed_raw_sha256='f'.repeat(64),
    x=>x.records[0].claimed_git_status='modified',
    x=>x.claimed_added_paths=[],
    x=>x.claimed_added_paths=['prospective_predictions/202611090102.json'],
    x=>x.records.push(structuredClone(x.records[0])),
    x=>x.repository='untrusted/repo',
    x=>x.reported_dispatch_run_id=123456789,
    x=>rewriteLocalBlob(x,r=>r.formal=true),
    x=>rewriteLocalBlob(x,r=>r.race_code='202611090102'),
    x=>rewriteLocalBlob(x,r=>r.cutoff_jst='2026-11-09T20:49:00+09:00'),
    x=>rewriteLocalBlob(x,r=>r.generated_at='2026-11-09T20:50:00+09:00'),
    x=>rewriteLocalBlob(x,r=>r.source_cards_received_jst='2026-11-09T20:21:00+09:00'),
    x=>rewriteLocalBlob(x,r=>r.input_sha256='f'.repeat(64)),
    x=>rewriteLocalBlob(x,r=>r.source_deadline_jst='2026-11-10T00:01:00+09:00'),
    x=>rewriteLocalBlob(x,r=>r.source_title_received_jst='2026-11-09T20:18:00Z'),
  ];
  for(const [i,mutate] of cases.entries()){
    const m=syntheticLocalFirstAdd();mutate(m);
    const result=auditLocalFirstAddEvidence(m);
    assert.equal(result.local_content_consistency_pass,false,
      'mutation '+i+' did not fail: '+JSON.stringify(result));
    assert.ok(result.issue_count>0);
    assert.equal(result.official_t_minus_12_proven,false);
  }
});

test('four-mode local first-add evidence checks T-20 generation, research schema and source digests',()=>{
  for(const mutate of [
    x=>rewriteLocalBlob(x,r=>r.generated_at_jst='2026-11-09T20:41:00+09:00'),
    x=>rewriteLocalBlob(x,r=>r.status='formal'),
    x=>rewriteLocalBlob(x,r=>r.validated=true),
    x=>rewriteLocalBlob(x,r=>delete r.modes.hole),
    x=>rewriteLocalBlob(x,r=>r.source_sha256.race_cards='12345'),
    x=>rewriteLocalBlob(x,r=>r.deadline_jst='2026-11-10T00:01:00+09:00'),
  ]){
    const x=syntheticLocalFirstAdd('four_mode');mutate(x);
    const result=auditLocalFirstAddEvidence(x);
    assert.equal(result.local_content_consistency_pass,false,JSON.stringify(result));
    assert.equal(result.official_t_minus_12_proven,false);
  }
});


test('offline first-add CLI emits exact hash, accepts local CLEAN consistency and refuses forged blob',()=>{
  const dir=mkdtempSync(join(tmpdir(),'boat-edge-first-add-'));
  const cli=fileURLToPath(new URL('../scripts/audit_cloudflare_first_add_manifest.mjs',import.meta.url));
  try{
    const path=join(dir,'first-add-manifest.json');
    const valid=syntheticLocalFirstAdd();
    writeFileSync(path,JSON.stringify(valid),'utf8');
    let result=spawnSync(process.execPath,[cli,path],{encoding:'utf8',timeout:15000});
    assert.equal(result.status,0,result.stderr);
    const passed=JSON.parse(result.stdout);
    assert.equal(passed.local_content_consistency_pass,true);
    assert.match(passed.input_sha256,/^[0-9a-f]{64}$/);
    assert.equal(passed.git_first_add_parent_tree_independently_proven,false);
    assert.equal(passed.remote_server_first_receipt_independently_proven,false);
    assert.equal(passed.official_t_minus_12_proven,false);
    valid.records[0].original_git_blob_utf8+='tampered';
    writeFileSync(path,JSON.stringify(valid),'utf8');
    result=spawnSync(process.execPath,[cli,path],{encoding:'utf8',timeout:15000});
    assert.equal(result.status,1,result.stderr);
    const failed=JSON.parse(result.stdout);
    assert.equal(failed.local_content_consistency_pass,false);
    assert.ok(failed.issue_count>0);
    writeFileSync(path,'{bad json','utf8');
    result=spawnSync(process.execPath,[cli,path],{encoding:'utf8',timeout:15000});
    assert.equal(result.status,2);
    assert.match(result.stderr,/FIRST_ADD_MANIFEST_REJECTED/);
  }finally{rmSync(dir,{recursive:true,force:true});}
});


function mockedRemoteGithubFirstAdd(kind='clean') {
  const m=syntheticLocalFirstAdd(kind);
  const row=m.records[0],path=row.path,commitSha=m.commit.sha,parent=m.commit.parent_sha;
  const ghSha=row.claimed_git_blob_sha1,body=row.original_git_blob_utf8;
  const root='https://api.github.com/repos/ikst2512-eng/boat-edge-clean/';
  const rootTreeSha='3'.repeat(40),archiveTreeSha='4'.repeat(40);
  const dirname=kind==='clean'?'prospective_predictions':'four_mode_forecasts';
  const normal={
    [root+'git/commits/'+parent]:{sha:parent,tree:{sha:rootTreeSha}},
    [root+'git/trees/'+rootTreeSha]:{sha:rootTreeSha,truncated:false,tree:[
      {path:dirname,type:'tree',mode:'040000',sha:archiveTreeSha}
    ]},
    [root+'git/trees/'+archiveTreeSha]:{sha:archiveTreeSha,truncated:false,tree:[
      {path:'202611080101.json',type:'blob',mode:'100644',sha:'a'.repeat(40)}
    ]},
    [root+'commits/'+commitSha]:{
      sha:commitSha,parents:[{sha:parent}],
      files:[{filename:path,status:'added',sha:ghSha}],
      commit:{committer:{date:'2026-11-09T11:30:00Z'}},
    },
    [root+'contents/'+path+'?ref='+commitSha]:{
      sha:ghSha,path,size:Buffer.byteLength(body,'utf8'),
      encoding:'base64',content:Buffer.from(body).toString('base64'),
    },
    [root+'git/blobs/'+ghSha]:{
      sha:ghSha,size:Buffer.byteLength(body,'utf8'),
      encoding:'base64',content:Buffer.from(body).toString('base64'),
    },
    [root+'compare/'+commitSha+'...main']:{
      status:'ahead',behind_by:0,merge_base_commit:{sha:commitSha},
    },
  };
  const parentUrl=root+'contents/'+path+'?ref='+parent;
  const calls=[];
  const fetcher=async(url,options)=>{
    calls.push({url,method:options.method,headers:options.headers});
    if(url===parentUrl)return {status:404};
    if(!Object.hasOwn(normal,url))throw Error('unexpected_unmocked_network:'+url);
    return {status:200,json:async()=>structuredClone(normal[url])};
  };
  return {manifest:m,normal,parentUrl,calls,fetcher,body,ghSha,commitSha,parent,root,rootTreeSha,archiveTreeSha};
}

test('real-GitHub read-only audit verifies added path, original blob, parent absence and main ancestry without formal T-12 claim',async()=>{
  for(const publisher of ['clean','four_mode']){
    const x=mockedRemoteGithubFirstAdd(publisher);
    const res=await verifyRealGithubFirstAdd({
      publisher,raceCode:'202611090101',commitSha:x.commitSha,fetcher:x.fetcher,
    });
    assert.equal(res.schema,REMOTE_GITHUB_SCHEMA);
    assert.equal(res.source_blob_commit_consistency_pass,true);
    assert.equal(res.git_parent_addition_checked,true);
    assert.equal(res.git_parent_tree_absence_checked,true);
    assert.equal(res.git_parent_tree_sha,x.rootTreeSha);
    assert.equal(res.git_parent_archive_directory_tree_sha,x.archiveTreeSha);
    assert.equal(res.record.deadline_jst,'2026-11-09T21:00:00+09:00');
    assert.equal(res.current_main_ancestry_checked,true);
    assert.equal(res.git_blob_sha1,x.ghSha);
    assert.equal(res.record.code,'202611090101');
    assert.equal(res.github_remote_first_seen_timestamp_proven,false);
    assert.equal(res.cloudflare_rescue_dispatch_proven,false);
    assert.equal(res.native_run_id_independently_proven,false);
    assert.equal(res.official_t_minus_12_proven,false);
    assert.equal(res.formal_recovery_proven,false);
    assert.equal(x.calls.length,8);
    assert.ok(x.calls.every(c=>c.method==='GET'&&!('Authorization' in c.headers)));
  }
});

test('remote GitHub source audit fails closed on fake additions, missing parent, bad blob and invented ancestry',async()=>{
  const scenarios=[
    x=>x.normal['https://api.github.com/repos/ikst2512-eng/boat-edge-clean/commits/'+x.commitSha].files[0].status='modified',
    x=>x.normal['https://api.github.com/repos/ikst2512-eng/boat-edge-clean/commits/'+x.commitSha].files[0].sha='f'.repeat(40),
    x=>x.normal['https://api.github.com/repos/ikst2512-eng/boat-edge-clean/commits/'+x.commitSha].parents[0].sha='not-a-sha',
    x=>x.normal['https://api.github.com/repos/ikst2512-eng/boat-edge-clean/git/blobs/'+x.ghSha].content=Buffer.from('tampered').toString('base64'),
    x=>x.normal['https://api.github.com/repos/ikst2512-eng/boat-edge-clean/compare/'+x.commitSha+'...main'].behind_by=1,
    x=>x.normal['https://api.github.com/repos/ikst2512-eng/boat-edge-clean/compare/'+x.commitSha+'...main'].merge_base_commit.sha='f'.repeat(40),
    x=>x.normal['https://api.github.com/repos/ikst2512-eng/boat-edge-clean/commits/'+x.commitSha].commit.committer.date='2026-11-09T12:00:00Z',
    x=>x.normal['https://api.github.com/repos/ikst2512-eng/boat-edge-clean/contents/prospective_predictions/202611090101.json?ref='+x.commitSha].content=Buffer.from('{"fake":1}').toString('base64'),
  ];
  for(const [i,mutate] of scenarios.entries()){
    const x=mockedRemoteGithubFirstAdd('clean');mutate(x);
    await assert.rejects(()=>verifyRealGithubFirstAdd({publisher:'clean',raceCode:'202611090101',
      commitSha:x.commitSha,fetcher:x.fetcher}),undefined,'scenario '+i);
    assert.ok(x.calls.every(c=>c.method==='GET'));
  }
  for(const denied of [200,403,429,500]){
    const x=mockedRemoteGithubFirstAdd();
    const fetcher=async(url,options)=>url===x.parentUrl?{status:denied}:x.fetcher(url,options);
    await assert.rejects(()=>verifyRealGithubFirstAdd({publisher:'clean',
      raceCode:'202611090101',commitSha:x.commitSha,fetcher}),/github_parent_file_absence_unproven/);
  }
});

test('parent Git tree must independently prove path absence; no truncated page or corrupted ancestry allowed',async()=>{
  const changes=[
    x=>x.normal[x.root+'git/commits/'+x.parent].sha='f'.repeat(40),
    x=>x.normal[x.root+'git/commits/'+x.parent].tree.sha='f'.repeat(40),
    x=>x.normal[x.root+'git/trees/'+x.rootTreeSha].truncated=true,
    x=>delete x.normal[x.root+'git/trees/'+x.rootTreeSha].tree,
    x=>x.normal[x.root+'git/trees/'+x.rootTreeSha].sha='f'.repeat(40),
    x=>x.normal[x.root+'git/trees/'+x.rootTreeSha].tree[0].mode='100644',
    x=>x.normal[x.root+'git/trees/'+x.rootTreeSha].tree.push(
      structuredClone(x.normal[x.root+'git/trees/'+x.rootTreeSha].tree[0])),
    x=>x.normal[x.root+'git/trees/'+x.archiveTreeSha].truncated=true,
    x=>x.normal[x.root+'git/trees/'+x.archiveTreeSha].sha='f'.repeat(40),
    x=>x.normal[x.root+'git/trees/'+x.archiveTreeSha].tree.push({
      path:'202611090101.json',type:'blob',mode:'100644',sha:'a'.repeat(40)}),
    x=>x.normal[x.root+'git/trees/'+x.archiveTreeSha].tree=null,
    x=>x.normal[x.root+'git/blobs/'+x.ghSha].size=999999,
    x=>x.normal[x.root+'git/blobs/'+x.ghSha].content+=' ',
  ];
  for(const [index,change] of changes.entries()){
    const x=mockedRemoteGithubFirstAdd();
    change(x);
    await assert.rejects(()=>verifyRealGithubFirstAdd({publisher:'clean',
      raceCode:'202611090101',commitSha:x.commitSha,fetcher:x.fetcher}),undefined,
      'tree mutation '+index+' must fail');
    assert.ok(x.calls.every(call=>call.method==='GET'));
  }
  // This is a valid first-add if the WHOLE archive directory was absent at
  // the parent, but not if the whole root tree response was truncated.
  const x=mockedRemoteGithubFirstAdd();
  x.normal[x.root+'git/trees/'+x.rootTreeSha].tree=[];
  const outcome=await verifyRealGithubFirstAdd({publisher:'clean',
    raceCode:'202611090101',commitSha:x.commitSha,fetcher:x.fetcher});
  assert.equal(outcome.git_parent_tree_absence_checked,true);
  assert.equal(outcome.git_parent_archive_directory_tree_sha,null);
});

test('real-GitHub source auditor rejects malformed race code and wrong publisher before any network',async()=>{
  const x=mockedRemoteGithubFirstAdd();
  for(const invalid of [
    {publisher:'clean',raceCode:'202611090199',commitSha:x.commitSha},
    {publisher:'clean',raceCode:'202611090125',commitSha:x.commitSha},
    {publisher:'clean',raceCode:'202611090101',commitSha:'bad'},
    {publisher:'other',raceCode:'202611090101',commitSha:x.commitSha},
  ]){
    await assert.rejects(()=>verifyRealGithubFirstAdd({...invalid,fetcher:x.fetcher}),
      /invalid_remote_github_sample_request/);
  }
  assert.equal(x.calls.length,0);
});
