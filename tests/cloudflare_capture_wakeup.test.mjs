import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import cloudflareWorker from '../cloudflare/independent_capture_wakeup.mjs';
import observerWorker from '../cloudflare/independent_capture_observer.mjs';
import * as observerExports from '../cloudflare/independent_capture_observer.mjs';
import * as workerEntrypointExports from '../cloudflare/independent_capture_wakeup.mjs';
import {plannedSlots, eligibleSlot, execute, observe, WORKFLOWS} from '../cloudflare/independent_capture_policy.mjs';
const JST=9*60*60*1000;
const jst=(h,m,d=5)=>new Date(Date.UTC(2026,10,d,h,m)-JST);
const tick=(h,m,d=5)=>jst(h,m,d).getTime();
const fakeRun=(event,when,rest={})=>({id:101,event,head_branch:'main',status:'completed',conclusion:'success',created_at:when.toISOString(),...rest});
function mock({schedule=[],manual=[],failAt=0,failPost=false,postStatus=204}={}) {
  const calls=[];
  async function fetcher(url,options) {
    calls.push({url,method:options.method,body:options.body});
    if (failAt === calls.length) throw new Error('network_failure');
    if (options.method==='POST') return {status:failPost?403:postStatus};
    const rows=url.includes('event=workflow_dispatch')?manual:schedule;
    return {status:200,json:async()=>({workflow_runs:rows})};
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
  for(const name of Object.keys(WORKFLOWS)) assert.equal(out.workflows[name].action,'dispatch_accepted_not_forecast_proof');
  assert.ok(m.calls.filter(x=>x.method==='POST').every(x=>JSON.parse(x.body).ref==='main'));
  assert.equal(out.formal,false);assert.equal(out.new_forecast_saved_proven,false);
});

test('each accepted 204 emits a safe auditable receipt without token or GitHub run claim',async()=>{
  const m=mock(); const receipts=[]; const when=tick(7,10);
  const out=await execute({scheduledTime:when,now:when,token:'PRIVATE_TEST_TOKEN',
    fetcher:m.fetcher, onAccepted:x=>receipts.push(x)});
  assert.equal(receipts.length,2);
  assert.deepEqual(receipts.map(x=>x.workflow),['clean','four_mode']);
  for(const entry of receipts){
    assert.equal(entry.event,'workflow_dispatch_accepted');
    assert.equal(entry.github_run_id_proven,false);
    assert.equal(entry.new_forecast_saved_proven,false);
    assert.equal(entry.formal,false);
    assert.ok(entry.slot_jst.endsWith('+09:00'));
    assert.ok(entry.request_started_at_jst.endsWith('+09:00'));
    assert.ok(!JSON.stringify(entry).includes('PRIVATE_TEST_TOKEN'));
  }
  assert.equal(out.workflows.four_mode.action,'dispatch_accepted_not_forecast_proof');
});

test('first 204 remains auditable when second dispatch fails',async()=>{
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
  const m=mock();const out=await run(tick(22,30),m);assert.equal(out.workflows.clean.action,'dispatch_accepted_not_forecast_proof');
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
  const out=await run(tick(7,10),m);assert.equal(out.workflows.four_mode.action,'dispatch_accepted_not_forecast_proof');assert.equal(out.on_time_cron_proven,false);
});

test('manual dispatch near slot blocks even when manual failed',async()=>{
  const m=mock({manual:[fakeRun('workflow_dispatch',jst(7,8),{conclusion:'failure'})]});
  const out=await run(tick(7,10),m);assert.equal(out.workflows.clean.reason,'previous_dispatch_or_active_job');noPosts(m);
});

test('an earlier active main run blocks, earlier success does not',async()=>{
  let m=mock({schedule:[fakeRun('schedule',jst(7,8),{status:'queued',conclusion:null})]});
  let out=await run(tick(7,25),m);assert.equal(out.workflows.four_mode.reason,'previous_dispatch_or_active_job');noPosts(m);
  m=mock({schedule:[fakeRun('schedule',jst(7,8))]});out=await run(tick(7,25),m);
  assert.equal(out.workflows.four_mode.action,'dispatch_accepted_not_forecast_proof');
});

test('nonmain cannot masquerade as successful main run',async()=>{
  const m=mock({schedule:[fakeRun('schedule',jst(7,8),{head_branch:'feature/other'})]});const out=await run(tick(7,10),m);
  assert.equal(out.workflows.four_mode.action,'dispatch_accepted_not_forecast_proof');
});

test('malformed GitHub history fails closed',async()=>{
  for(const change of [{id:'123'},{head_branch:null},{created_at:'invalid'},{event:'push'},{status:null}]){
    const m=mock({schedule:[fakeRun('schedule',jst(7,8),change)]});
    await assert.rejects(()=>run(tick(7,10),m));noPosts(m);
  }
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
        return gets===failAt?{status}:{status:200,json:async()=>({workflow_runs:[]})};
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
      return {status:200,json:async()=>({workflow_runs:[]})};
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

test('real scheduled adapter runs both mocked recoveries and emits scrubbed receipts',async()=>{
  const when=tick(7,10),m=mock(),logs=[],errors=[];
  const oldFetch=globalThis.fetch,oldNow=Date.now,oldLog=console.log,oldError=console.error;
  globalThis.fetch=m.fetcher;
  Date.now=()=>when;
  console.log=message=>logs.push(String(message));
  console.error=message=>errors.push(String(message));
  try{
    await cloudflareWorker.scheduled({cron:'*/5 22-23,0-13 * * *',type:'scheduled',scheduledTime:when},
      {GITHUB_DISPATCH_TOKEN:'PRIVATE_TEST_TOKEN',CLOUDFLARE_DISPATCH_ENABLED:'true'}, {});
  }finally{
    globalThis.fetch=oldFetch;Date.now=oldNow;console.log=oldLog;console.error=oldError;
  }
  assert.deepEqual(m.calls.map(x=>x.method),['GET','GET','GET','GET','POST','POST']);
  const receipts=logs.filter(x=>x.startsWith('CLOUDFLARE_DISPATCH_RECEIPT='));
  const reports=logs.filter(x=>x.startsWith('CLOUDFLARE_CAPTURE_WAKEUP='));
  assert.equal(receipts.length,2);
  assert.equal(reports.length,1);
  assert.deepEqual(receipts.map(x=>JSON.parse(x.split('=')[1]).workflow),['clean','four_mode']);
  assert.equal(JSON.parse(reports[0].slice(reports[0].indexOf('=')+1)).new_forecast_saved_proven,false);
  assert.deepEqual(errors,[]);
  assert.ok(logs.every(x=>!x.includes('PRIVATE_TEST_TOKEN')));
});

test('scheduled adapter missing Secret fails before network with redacted error',async()=>{
  const m=mock(),errors=[];
  const oldFetch=globalThis.fetch,oldNow=Date.now,oldError=console.error;
  globalThis.fetch=m.fetcher;Date.now=()=>tick(7,10);console.error=message=>errors.push(String(message));
  try{
    await assert.rejects(()=>cloudflareWorker.scheduled({cron:'*/5 22-23,0-13 * * *',scheduledTime:tick(7,10)},
      {CLOUDFLARE_DISPATCH_ENABLED:'true'},{}),/GITHUB_DISPATCH_TOKEN_required/);
  }finally{globalThis.fetch=oldFetch;Date.now=oldNow;console.error=oldError;}
  assert.equal(m.calls.length,0);
  assert.equal(errors.length,1);
  assert.ok(errors[0].includes('GITHUB_DISPATCH_TOKEN_required'));
  assert.ok(!errors[0].includes('Bearer'));
});

test('observer-only pure report computes recovery slots without credentials or GitHub calls',()=>{
  const out=observe({scheduledTime:tick(7,10),now:tick(7,10)});
  assert.equal(out.action,'no_network_no_dispatch');
  assert.equal(out.mode,'observe_only');
  assert.equal(out.github_history_checked,false);
  assert.equal(out.github_run_id_proven,false);
  assert.equal(out.formal,false);
  assert.ok(out.eligible_slots_jst.clean);
  assert.ok(out.eligible_slots_jst.four_mode);
  assert.equal(typeof out.eligible_slots_jst.clean,'string');
});

test('observer-only rejects expired Cron time before reporting',()=>{
  assert.throws(()=>observe({scheduledTime:tick(7,10)-120000,now:tick(7,10)}),/late_or_future_cron_trigger/);
});

test('Wrangler config makes non-dispatch observer the default',()=>{
  const config=readFileSync(new URL('../cloudflare/wrangler.toml',import.meta.url),'utf8');
  assert.match(config,/CLOUDFLARE_DISPATCH_ENABLED = "false"/);
  assert.match(config,/required = \["GITHUB_DISPATCH_TOKEN"\]/);
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

test('POST must return 204; no false success',async()=>{
  const m=mock({postStatus:200});await assert.rejects(()=>run(tick(7,10),m),/dispatch_not_accepted/);
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
